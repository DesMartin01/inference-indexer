"use client";

// Homepage recommendation engine panel (V6-Homepage-PRD item 2).
//
// Deterministic parse -> visible echo chips -> live /v1/recommend results with
// trust badges and a funnel line. NO LLM anywhere: parsing is keyword rules,
// results come from the API's deterministic ranking, and everything the engine
// "understood" is shown to the user before any result. Queries are never
// stored server-side (recommendation_stats holds constraint tuples only).

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

// ---------- types ----------

interface Constraints {
  budget_max_usd_per_m: number | null;
  aa_min: number | null;
  context_min: number | null;
  zdr: boolean;
  eu_sovereign: boolean;
  reasoning: boolean | null;
  use_case: string | null;
}

interface EchoChip {
  label: string;
  gold: boolean; // gold = constraint matched; grey = preference/context note
}

const CREATOR_COUNTRY: Record<string, string> = {
  "OpenAI": "us", "Anthropic": "us", "Google": "us", "Google DeepMind": "us",
  "Meta": "us", "Microsoft": "us", "xAI": "us", "Amazon": "us", "NVIDIA": "us",
  "DeepSeek": "cn", "Z.ai": "cn", "Qwen": "cn", "Alibaba": "cn",
  "Moonshot AI": "cn", "ByteDance": "cn", "Tencent": "cn", "Baidu": "cn",
  "Mistral AI": "fr", "Cohere": "ca", "AI21": "il", "Ai2": "us",
};

const FLAG_EMOJI: Record<string, string> = {
  us: "🇺🇸", cn: "🇨🇳", fr: "🇫🇷", de: "🇩🇪", ca: "🇨🇦", jp: "🇯🇵", kr: "🇰🇷",
  in: "🇮🇳", sg: "🇸🇬", ae: "🇦🇪", il: "🇮🇱", ch: "🇨🇭", nl: "🇳🇱", se: "🇸🇪",
  ie: "🇮🇪", au: "🇦🇺", tw: "🇹🇼", hk: "🇭🇰", ru: "🇷🇺", br: "🇧🇷", za: "🇿🇦",
  it: "🇮🇹", es: "🇪🇸", fi: "🇫🇮", no: "🇳🇴", dk: "🇩🇰", pl: "🇵🇱", tr: "🇹🇷",
};

function creatorFlag(name: string | undefined): { flag: string; code: string } | null {
  if (!name) return null;
  const code = CREATOR_COUNTRY[name];
  if (!code) return null;
  return { flag: FLAG_EMOJI[code] ?? "", code: code.toUpperCase() };
}

interface Rec {
  rank: number;
  model_id: string;
  name: string;
  creator?: string;
  provider?: string;
  tier: string;
  aa_index_score: number | null;
  blended_price_per_m: number;
  cost_per_iq: number;
  input_price_per_m?: number;
  output_price_per_m?: number;
  context_length?: number;
  is_reasoning?: boolean;
  callability?: string;
  why?: string;
  caveats?: string[];
}

interface ProviderRow {
  name: string;
  is_zdr: boolean;
  is_eu_sovereign: boolean;
  model_count: number;
  min_price: number | null;
  avg_price: number | null;
  provider_type: string;
}

interface EndpointRow {
  provider: string;
  input_price_per_m: number;
  output_price_per_m: number;
  blended_price_per_m: number;
  context_length: number | null;
}

interface RecommendResponse {
  recommendations?: Rec[];
  alternatives_considered?: { count?: number; runner_ups?: Rec[] };
  ranking_basis?: { description?: string };
  error?: { code?: string; message?: string };
  detail?: string | { error?: { message?: string } };
}

// ---------- deterministic parser ----------

const USE_CASES = ["support", "volume", "extraction", "summarization", "coding", "research"] as const;

// Short display nouns for the "Understood as" echo (Des: crisp, not verbose)
const UC_LABEL: Record<(typeof USE_CASES)[number], string> = {
  support: "Support",
  volume: "High volume",
  extraction: "Extraction",
  summarization: "Summarisation",
  coding: "Coding",
  research: "Research",
};

export function parseConstraints(text: string): { constraints: Constraints; chips: EchoChip[] } {
  const t = text.toLowerCase();
  const chips: EchoChip[] = [];
  const c: Constraints = {
    budget_max_usd_per_m: null,
    aa_min: null,
    context_min: null,
    zdr: false,
    eu_sovereign: false,
    reasoning: null,
    use_case: null,
  };

  // ZDR / data retention
  if (/zero[\s-]?data[\s-]?retention|\bzdr\b|no[\s-]?(data[\s-]?)?(retention|logging|training)/.test(t)) {
    c.zdr = true;
    chips.push({ label: "ZDR", gold: true });
  }
  // EU
  if (/\beu\b|european|eu[\s-]?(infra|sovereign|domicile)|gdpr/.test(t)) {
    c.eu_sovereign = true;
    chips.push({ label: "EU infra", gold: true });
  }
  // AA quality floor: "above AA index 50", "AA score above 60", "AA 45+"
  const aaFloor = t.match(/aa(?:\s|intelligence)?(?:\s+(?:index|score))?\s*(?:above|over|>|of at least|at least)\s*([0-9]+(?:\.[0-9]+)?)/)
    || t.match(/(?:above|over|>|of at least|at least)\s*(?:an\s+)?aa(?:\s+(?:index|score))?\s*(?:of\s*)?([0-9]+(?:\.[0-9]+)?)/)
    || t.match(/aa\s*(?:index|score)?\s*([0-9]+(?:\.[0-9]+)?)\s*\+/);
  if (aaFloor) {
    const v = parseFloat(aaFloor[1]);
    if (v > 0 && v <= 100) {
      c.aa_min = v;
      chips.push({ label: `AA ≥ ${v}`, gold: true });
    }
  }
  // Budget: "$2", "under $1.5/M", "below $0.50 per million"
  const budget = t.match(/(?:under|below|less than|max|up to|<)\s*\$?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:\/\s*m|per\s*m(?:illion)?|\/m\b)?/) || t.match(/\$\s*([0-9]+(?:\.[0-9]+)?)\s*(?:\/\s*m|per\s*m(?:illion)?)/);
  if (budget) {
    const v = parseFloat(budget[1]);
    if (v > 0 && v < 1000) {
      c.budget_max_usd_per_m = v;
      chips.push({ label: `Best price under $${v}/M`, gold: true });
    }
  }
  // Context window: "100k context", "large context", "128k+"
  const ctxK = t.match(/([0-9]+)\s*k?\s*(?:token)?\s*context/) || t.match(/context[^0-9]{0,10}([0-9]+)\s*k/);
  if (ctxK) {
    const k = parseInt(ctxK[1], 10);
    if (k >= 4 && k <= 2000) {
      c.context_min = k * 1000;
      chips.push({ label: `Context ${k}k+`, gold: true });
    }
  } else if (/large context|long context|big context/.test(t)) {
    c.context_min = 128000;
    chips.push({ label: "Context 128k+", gold: true });
  }
  // Reasoning preference
  if (/non[\s-]?reasoning|no[\s-]reasoning|without reasoning|precise[- ]not[- ]smart|deterministic output/.test(t)) {
    c.reasoning = false;
    chips.push({ label: "Non-reasoning", gold: true });
  } else if (/reasoning|thinking|chain of thought|\bcot\b/.test(t)) {
    c.reasoning = true;
    chips.push({ label: "Reasoning", gold: true });
  }
  // Use case: synonyms first, then earliest occurrence in the text wins (not list order).
  const ucSynonyms: [RegExp, (typeof USE_CASES)[number]][] = [
    [/\brag\b|retrieval[\s-]augmented/, "summarization"],
    [/\bcod(?:e|ing)\b|programming|\bdeveloper\b/i, "coding"],
    [/customer (?:service|support)|helpdesk|\bticket/, "support"],
    [/high[\s-]volume|\bbulk\b|batch processing/, "volume"],
    [/extract|parse documents|\binvoices?\b|\breceipts?\b/, "extraction"],
    [/summariz|\bdigest\b|briefing|report writing/, "summarization"],
  ];
  let bestUC: (typeof USE_CASES)[number] | null = null;
  let bestPos = Infinity;
  for (const [re, uc] of ucSynonyms) {
    const m = re.exec(t);
    if (m && m.index < bestPos) {
      bestPos = m.index;
      bestUC = uc;
    }
  }
  for (const uc of USE_CASES) {
    const i = t.indexOf(uc);
    if (i !== -1 && i < bestPos) {
      bestPos = i;
      bestUC = uc;
    }
  }
  if (bestUC) {
    c.use_case = bestUC;
    chips.push({ label: UC_LABEL[bestUC], gold: true });
  }

  // Grey chips: things we recognised but did NOT turn into constraints
  if (/security|prompt injection|router interference/.test(t)) {
    chips.push({ label: "Security: not scored yet", gold: false });
  }
  if (/\bagents?\b|\bhermes\b|autonomous|workflow automation/.test(t)) {
    chips.push({ label: "Agent workload", gold: false });
  }
  if (/legal|law firm|compliance|gdpr|hipaa|regulat|solicitor/.test(t)) {
    chips.push({ label: "Legal/compliance: noted", gold: false });
  }
  if (/sme|london|finance|accounts receivable|agency|startup/.test(t)) {
    chips.push({ label: "Workload context: noted", gold: false });
  }

  return { constraints: c, chips };
}

// ---------- suggestion chips ----------

const SUGGESTIONS: { text: string; fill: string }[] = [
  {
    text: "Best model for coding agents priced under $2/M",
    fill: "Best model for coding agents priced under $2 per million tokens",
  },
  {
    text: "Best priced models above AA score 50",
    fill: "Best priced models above AA score 50",
  },
  {
    text: "Zero data retention providers in the EU",
    fill: "Zero data retention providers in the EU",
  },
  {
    text: "Compare providers serving DeepSeek V4",
    fill: "Compare providers serving DeepSeek V4",
  },
  {
    text: "Best options for Hermes Agent running ZDR in EU",
    fill: "Best options for an agent workload with zero data retention and EU infrastructure",
  },
  {
    text: "Inference options for RAG system in a UK Law Firm",
    fill: "Best inference options for a research and summarization workload handling sensitive legal documents",
  },
];

// ---------- answer-type router ----------

type AnswerType =
  | { kind: "models" }
  | { kind: "providers"; zdr: boolean; eu: boolean }
  | { kind: "model-compare"; modelText: string };

const MODEL_PATTERNS = [
  /deepseek\s*v?4/i,
  /gpt[- ]?[0-9]/i,
  /claude\s+(opus|sonnet|haiku)/i,
  /gemini/i,
  /llama\s*[0-9]/i,
  /glm[- ]?[0-9]/i,
  /grok/i,
  /mistral/i,
  /qwen/i,
  /kimi/i,
];

function classifyAnswer(text: string, c: Constraints): AnswerType {
  const t = text.toLowerCase();
  // "Providers serving <model>" / "price compared" -> per-provider price table
  if (/(providers?\s+(serving|hosting|offering))|price compared|price comparison/i.test(t)) {
    const m = MODEL_PATTERNS.find((re) => re.test(text));
    if (m) {
      const matched = text.match(m)?.[0] ?? "";
      return { kind: "model-compare", modelText: matched };
    }
  }
  // Pure provider-attribute queries (ZDR / EU) with no model/price/workload signals
  const mentionsModel = MODEL_PATTERNS.some((re) => re.test(text));
  const mentionsPriceBudget = /\$|budget|under|cheap|price|cost|\/\s*m/i.test(t);
  const mentionsWorkload = /for|workload|agent|use case|support|coding|research|extraction|summariz/i.test(t);
  if ((c.zdr || c.eu_sovereign) && !mentionsModel && !mentionsPriceBudget && !mentionsWorkload) {
    return { kind: "providers", zdr: c.zdr, eu: c.eu_sovereign };
  }
  return { kind: "models" };
}

// ---------- component ----------

export default function EnginePanel({
  totalModels,
  initialQuery,
  showEmbedLink = true,
}: {
  totalModels: number;
  initialQuery?: string;
  showEmbedLink?: boolean;
}) {
  const [text, setText] = useState(initialQuery ?? "");
  const [chips, setChips] = useState<EchoChip[]>([]);
  const [results, setResults] = useState<Rec[] | null>(null);
  const [providerRows, setProviderRows] = useState<ProviderRow[] | null>(null);
  const [providerFilter, setProviderFilter] = useState<{ zdr: boolean; eu: boolean } | null>(null);
  const [compare, setCompare] = useState<{ modelId: string; name: string; endpoints: EndpointRow[] } | null>(null);
  const [basis, setBasis] = useState<string>("");
  const [filteredCount, setFilteredCount] = useState<number | null>(null);
  const [status, setStatus] = useState<"idle" | "loading" | "error" | "route" | "done">("idle");
  const [errMsg, setErrMsg] = useState("");
  const [receipts, setReceipts] = useState<number | null>(null);
  const [dayCount, setDayCount] = useState(0);
  const resultsRef = useRef<HTMLDivElement>(null);
  const searchParams = useSearchParams();

  // Pre-fill from ?q= when arriving from the nav search or a suggestion link
  useEffect(() => {
    const urlQ = searchParams.get("q");
    if (urlQ && urlQ.length > 3) setText(urlQ);
  }, [searchParams]);

  // Receipts counter: anonymous aggregate, no query content involved
  useEffect(() => {
    fetch("/api/recommend-stats")
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (d && typeof d.total === "number" && d.total > 0) setReceipts(d.total);
      })
      .catch(() => {});
  }, []);

  // Soft gate: 3 recommendations/day for anonymous visitors (cookie)
  useEffect(() => {
    const m = document.cookie.match(/ii_rec_count=(\d+)/);
    if (m) setDayCount(parseInt(m[1], 10));
  }, []);

  const bumpDayCount = useCallback(() => {
    const next = dayCount + 1;
    setDayCount(next);
    // cookie expires at midnight UTC
    const midnight = new Date();
    midnight.setUTCHours(24, 0, 0, 0);
    document.cookie = `ii_rec_count=${next}; expires=${midnight.toUTCString()}; path=/`;
  }, [dayCount]);

  const run = useCallback(
    async (input: string) => {
      const trimmed = input.trim();
      if (!trimmed || status === "loading") return;
      if (dayCount >= 5) {
        setStatus("error");
        setErrMsg("Anonymous limit reached (5 recommendations/day). Create a free account for unlimited recommendations.");
        return;
      }

      setStatus("loading");
      setResults(null);
      setErrMsg("");

      const { constraints, chips: parsed } = parseConstraints(trimmed);
      setChips(parsed);
      setProviderRows(null);
      setProviderFilter(null);
      setCompare(null);

      // Answer-type router: providers list vs per-provider price compare vs model ranking
      const answer = classifyAnswer(trimmed, constraints);
      if (answer.kind === "providers") {
        setStatus("loading");
        try {
          const res = await fetch("/api/providers");
          const data = await res.json();
          let rows: ProviderRow[] = data.providers ?? [];
          if (answer.zdr) rows = rows.filter((r) => r.is_zdr);
          if (answer.eu) rows = rows.filter((r) => r.is_eu_sovereign);
          setProviderRows(rows);
          setProviderFilter({ zdr: answer.zdr, eu: answer.eu });
          setStatus("done");
          bumpDayCount();
        } catch {
          setStatus("error");
          setErrMsg("Could not reach the provider service. Please try again.");
        }
        return;
      }
      if (answer.kind === "model-compare") {
        setStatus("loading");
        try {
          const res = await fetch(`/api/model-endpoints?model_id=${encodeURIComponent(answer.modelText)}`);
          const data = await res.json();
          if (!res.ok) {
            setStatus("error");
            setErrMsg(data.error || `Could not find a model matching "${answer.modelText}".`);
            return;
          }
          setCompare({ modelId: data.model_id, name: data.name, endpoints: data.endpoints ?? [] });
          setStatus("done");
          bumpDayCount();
        } catch {
          setStatus("error");
          setErrMsg("Could not reach the endpoint service. Please try again.");
        }
        return;
      }

      // Nothing usable parsed -> fail loud, never guess
      if (
        !constraints.zdr &&
        !constraints.eu_sovereign &&
        constraints.budget_max_usd_per_m == null &&
        constraints.aa_min == null &&
        constraints.context_min == null &&
        constraints.reasoning == null &&
        constraints.use_case == null
      ) {
        setStatus("error");
        setErrMsg('Could not identify any constraints. Try structured wording like "under $2 per million", "zero data retention", "EU infrastructure", or "large context".');
        return;
      }

      try {
        const res = await fetch("/api/recommend", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            budget_max_usd_per_m: constraints.budget_max_usd_per_m,
            aa_min: constraints.aa_min,
            context_min: constraints.context_min,
            zdr: constraints.zdr,
            eu_sovereign: constraints.eu_sovereign,
            reasoning: constraints.reasoning,
            use_case: constraints.use_case,
            limit: 5,
          }),
        });
        const data: RecommendResponse = await res.json();
        if (!res.ok) {
          const msg =
            (typeof data.detail === "object" && data.detail?.error?.message) ||
            (typeof data.detail === "string" ? data.detail : null) ||
            data.error?.message ||
            "Recommendation service error";
          setStatus("error");
          setErrMsg(msg);
          return;
        }
        setResults(data.recommendations ?? []);
        setBasis(data.ranking_basis?.description ?? "");
        setFilteredCount(data.alternatives_considered?.count ?? null);
        setStatus("done");
        bumpDayCount();
        setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }), 150);
      } catch {
        setStatus("error");
        setErrMsg("Could not reach the recommendation service. Prices may still be browsed below.");
      }
    },
    [status, dayCount, bumpDayCount]
  );

  const gated = dayCount >= 5;

  return (
    <section id="engine" style={{ maxWidth: "1320px", margin: "0 auto", padding: "26px 28px 0" }}>
      <div style={{ borderTop: "1px solid var(--ep-border)", paddingTop: "22px" }}>
        <label
          htmlFor="ii-engine-q"
          style={{
            fontSize: "19px",
            fontWeight: 600,
            letterSpacing: "-0.015em",
            color: "var(--ep-text)",
            display: "flex",
            alignItems: "center",
            gap: "10px",
          }}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/profile-icon.png"
            alt="InferenceIndexer"
            width={22}
            height={22}
            style={{ borderRadius: "4px", flexShrink: 0 }}
          />
          What type of AI Inference are you looking for?
        </label>
        <div
          style={{
            marginTop: "12px",
            background: "var(--ep-input)",
            border: "1px solid #33333a",
            padding: "14px 16px 12px",
            display: "flex",
            flexDirection: "column",
            gap: "10px",
          }}
        >
          <textarea
            id="ii-engine-q"
            rows={3}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) run(text);
            }}
            placeholder="Describe the workload, the constraints, and the budget"
            style={{
              width: "100%",
              background: "transparent",
              border: 0,
              outline: 0,
              resize: "vertical",
              color: "var(--ep-text)",
              fontFamily: "Inter, sans-serif",
              fontSize: "15px",
              lineHeight: 1.5,
            }}
          />
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "14px", flexWrap: "wrap" }}>
            <span style={{ fontSize: "12px", color: "var(--ep-muted)" }}>
              Enter plain language or structured constraints. Queries are never stored.
            </span>
            <button
              type="button"
              onClick={() => run(text)}
              disabled={status === "loading" || gated}
              style={{
                fontSize: "13px",
                fontWeight: 500,
                color: gated ? "var(--ep-muted)" : "var(--ep-page)",
                background: gated ? "var(--ep-border)" : "#C4A038",
                border: 0,
                padding: "9px 18px",
                cursor: status === "loading" ? "wait" : "pointer",
                whiteSpace: "nowrap",
                fontFamily: "Inter, sans-serif",
              }}
            >
              {status === "loading" ? "Ranking…" : gated ? "Daily limit reached" : "Recommend"}
            </button>
          </div>
        </div>

        {/* Or start from */}
        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", marginTop: "12px", alignItems: "center" }}>
          <span style={{ fontSize: "12px", color: "var(--ep-muted)" }}>Or start from:</span>
          {SUGGESTIONS.map((s) => (
            <button
              key={s.text}
              type="button"
              onClick={() => {
                setText(s.fill);
                run(s.fill);
              }}
              style={{
                fontSize: "12px",
                padding: "5px 11px",
                background: "transparent",
                color: "var(--ep-text-2)",
                border: "1px solid #2f2f2f",
                cursor: "pointer",
                fontFamily: "Inter, sans-serif",
              }}
            >
              {s.text}
            </button>
          ))}
        </div>

        {/* Echo chips */}
        {chips.length > 0 && status !== "idle" && (
          <div style={{ marginTop: "18px", paddingLeft: "18px", borderLeft: "2px solid var(--ep-border)" }}>
            <span
              style={{
                fontFamily: "var(--font-jetbrains-mono), monospace",
                fontSize: "10px",
                fontWeight: 500,
                letterSpacing: "0.12em",
                textTransform: "uppercase",
                color: "var(--ep-muted)",
              }}
            >
              Understood as
            </span>
            <div style={{ display: "flex", gap: "7px", flexWrap: "wrap", marginTop: "8px" }}>
              {chips.map((chip, i) => (
                <span
                  key={i}
                  title={chip.gold ? "Applied as a ranking constraint" : "Recognised but not scored yet"}
                  style={{
                    fontSize: "12px",
                    fontWeight: 500,
                    padding: "4px 10px",
                    background: chip.gold ? "rgba(196,160,56,0.08)" : "var(--ep-card)",
                    border: `1px solid ${chip.gold ? "rgba(196,160,56,0.35)" : "var(--ep-border)"}`,
                    color: chip.gold ? "#C4A038" : "var(--ep-muted)",
                  }}
                >
                  {chip.label}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Error / gate */}
        {status === "error" && errMsg && (
          <p style={{ marginTop: "14px", fontSize: "13px", color: "#ef4444", maxWidth: "60em" }}>{errMsg}</p>
        )}
        {/* Provider list results */}
        {providerRows && (
          <div ref={resultsRef} style={{ borderTop: "1px solid #1d1d21", marginTop: "26px", paddingTop: "18px" }}>
            <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: "14px", flexWrap: "wrap", marginBottom: "10px" }}>
              <span style={{ fontSize: "16px", fontWeight: 600, color: "var(--ep-text)" }}>
                {providerFilter?.zdr && providerFilter?.eu
                  ? "Providers with zero data retention on EU infrastructure"
                  : providerFilter?.zdr
                  ? "Providers with zero data retention"
                  : "EU-sovereign providers"}
              </span>
              <span style={{ fontSize: "12px", color: "var(--ep-muted)" }}>
                {providerRows.length} provider{providerRows.length === 1 ? "" : "s"} match · attributes are provider-stated
              </span>
            </div>
            {providerRows.length === 0 ? (
              <p style={{ fontSize: "13px", color: "var(--ep-muted)" }}>
                No providers match those attributes today. We add providers as we verify them.
              </p>
            ) : (
              <>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "minmax(120px, 1.4fr) minmax(0, 150px) minmax(0, 150px) 80px 90px",
                    alignItems: "center",
                    gap: "8px",
                    padding: "2px 0 7px",
                    borderBottom: "1px solid var(--ep-border)",
                  }}
                >
                  {[
                    ["Provider", "left"],
                    ["Data retention", "left"],
                    ["EU infra", "left"],
                    ["Models", "right"],
                    ["From $/M", "right"],
                  ].map(([label, align]) => (
                    <span
                      key={label}
                      style={{
                        fontFamily: "Inter, sans-serif",
                        fontSize: "10px",
                        fontWeight: 500,
                        letterSpacing: "0.11em",
                        textTransform: "uppercase",
                        color: "var(--ep-muted)",
                        textAlign: align as "left" | "right",
                      }}
                    >
                      {label}
                    </span>
                  ))}
                </div>
                {providerRows.map((pv) => (
                  <Link
                    key={pv.name}
                    href={`/providers/${encodeURIComponent(pv.name)}`}
                    style={{
                      display: "grid",
                      gridTemplateColumns: "minmax(120px, 1.4fr) minmax(0, 150px) minmax(0, 150px) 80px 90px",
                      alignItems: "center",
                      gap: "8px",
                      minHeight: "42px",
                      padding: "6px 0",
                      borderBottom: "1px solid #18181c",
                      textDecoration: "none",
                    }}
                  >
                    <span style={{ fontSize: "13.5px", fontWeight: 500, color: "var(--ep-text)" }}>{pv.name}</span>
                    <span style={{ fontSize: "11.5px", color: pv.is_zdr ? "#22c55e" : "var(--ep-muted)" }}>
                      {pv.is_zdr ? "ZDR: stated" : "-"}
                    </span>
                    <span style={{ fontSize: "11.5px", color: pv.is_eu_sovereign ? "#22c55e" : "var(--ep-muted)" }}>
                      {pv.is_eu_sovereign ? "EU: stated" : "-"}
                    </span>
                    <span style={{ textAlign: "right", fontFamily: "Inter, sans-serif", fontSize: "12.5px", color: "var(--ep-text-2)", fontVariantNumeric: "tabular-nums" }}>
                      {pv.model_count}
                    </span>
                    <span style={{ textAlign: "right", fontFamily: "Inter, sans-serif", fontSize: "12.5px", color: "var(--ep-text)", fontVariantNumeric: "tabular-nums" }}>
                      {pv.min_price != null ? `$${pv.min_price.toFixed(2)}` : "-"}
                    </span>
                  </Link>
                ))}
              </>
            )}
            <p style={{ marginTop: "10px", fontSize: "12px", lineHeight: 1.55, color: "var(--ep-muted)" }}>
              ZDR and EU attributes come from provider statements; II has not verified them. Prices verified hourly.
            </p>
          </div>
        )}

        {/* Per-provider price comparison for one model */}
        {compare && (
          <div style={{ borderTop: "1px solid #1d1d21", marginTop: "26px", paddingTop: "18px" }}>
            <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: "14px", flexWrap: "wrap", marginBottom: "10px" }}>
              <span style={{ fontSize: "16px", fontWeight: 600, color: "var(--ep-text)" }}>
                {compare.name}: providers compared
              </span>
              <span style={{ fontSize: "12px", color: "var(--ep-muted)", fontVariantNumeric: "tabular-nums" }}>
                {compare.endpoints.length} endpoint{compare.endpoints.length === 1 ? "" : "s"} · sorted by price
              </span>
            </div>
            {compare.endpoints.length === 0 ? (
              <p style={{ fontSize: "13px", color: "var(--ep-muted)" }}>No verified endpoints for this model.</p>
            ) : (
              <>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "minmax(120px, 1.4fr) 90px 90px 100px",
                    alignItems: "center",
                    gap: "8px",
                    padding: "2px 0 7px",
                    borderBottom: "1px solid var(--ep-border)",
                  }}
                >
                  {[
                    ["Provider", "left"],
                    ["Input $/M", "right"],
                    ["Output $/M", "right"],
                    ["Blended $/M", "right"],
                  ].map(([label, align]) => (
                    <span
                      key={label}
                      style={{
                        fontFamily: "Inter, sans-serif",
                        fontSize: "10px",
                        fontWeight: 500,
                        letterSpacing: "0.11em",
                        textTransform: "uppercase",
                        color: "var(--ep-muted)",
                        textAlign: align as "left" | "right",
                      }}
                    >
                      {label}
                    </span>
                  ))}
                </div>
                {compare.endpoints
                  .slice()
                  .sort((a, b) => a.blended_price_per_m - b.blended_price_per_m)
                  .slice(0, 8)
                  .map((ep, i) => (
                    <div
                      key={ep.provider}
                      style={{
                        display: "grid",
                        gridTemplateColumns: "minmax(120px, 1.4fr) 90px 90px 100px",
                        alignItems: "center",
                        gap: "8px",
                        minHeight: "40px",
                        padding: "5px 0",
                        borderBottom: "1px solid #18181c",
                      }}
                    >
                      <span style={{ fontSize: "13.5px", fontWeight: 500, color: "var(--ep-text)", display: "flex", alignItems: "center", gap: "7px" }}>
                        <span style={{ fontFamily: "Inter, sans-serif", fontSize: "11.5px", color: i === 0 ? "#C4A038" : "var(--ep-muted)" }}>{i + 1}</span>
                        {ep.provider}
                        {i === 0 && (
                          <span style={{ fontSize: "10.5px", padding: "2px 7px", background: "rgba(196,160,56,0.08)", border: "1px solid rgba(196,160,56,0.35)", color: "#C4A038" }}>
                            cheapest
                          </span>
                        )}
                      </span>
                      <span style={{ textAlign: "right", fontFamily: "Inter, sans-serif", fontSize: "12.5px", color: "var(--ep-text-2)", fontVariantNumeric: "tabular-nums" }}>
                        ${ep.input_price_per_m.toFixed(2)}
                      </span>
                      <span style={{ textAlign: "right", fontFamily: "Inter, sans-serif", fontSize: "12.5px", color: "var(--ep-text-2)", fontVariantNumeric: "tabular-nums" }}>
                        ${ep.output_price_per_m.toFixed(2)}
                      </span>
                      <span style={{ textAlign: "right", fontFamily: "Inter, sans-serif", fontSize: "12.5px", color: "var(--ep-text)", fontVariantNumeric: "tabular-nums" }}>
                        ${ep.blended_price_per_m.toFixed(2)}
                      </span>
                    </div>
                  ))}
              </>
            )}
            <p style={{ marginTop: "10px", fontSize: "12px", lineHeight: 1.55, color: "var(--ep-muted)" }}>
              Verified prices per provider endpoint, rebuilt hourly. Blended = 0.4 × input + 0.6 × output.
            </p>
          </div>
        )}

        {/* Results */}
        <div ref={resultsRef}>
          {results && results.length > 0 && (
            <div style={{ borderTop: "1px solid #1d1d21", marginTop: "26px", paddingTop: "18px" }}>
              <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: "14px", flexWrap: "wrap", marginBottom: "10px" }}>
                <span style={{ fontSize: "16px", fontWeight: 600, color: "var(--ep-text)" }}>Recommendations</span>
                <span style={{ fontSize: "12px", color: "var(--ep-muted)", fontVariantNumeric: "tabular-nums" }}>
                  {results.length} of {totalModels} models match · ranked by Cost/IQ
                  {filteredCount != null ? ` · ${filteredCount} in scope before ranking` : ""}
                </span>
              </div>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "34px minmax(140px, 1.6fr) minmax(90px, 1fr) minmax(150px, 1.2fr) 70px 84px",
                  alignItems: "center",
                  gap: "8px",
                  padding: "2px 0 7px",
                  borderBottom: "1px solid var(--ep-border)",
                }}
              >
                {[
                  ["#", "left"],
                  ["Model", "left"],
                  ["Creator", "left"],
                  ["Basis", "left"],
                  ["AA score", "right"],
                  ["Cost / IQ", "right"],
                ].map(([label, align]) => (
                  <span
                    key={label}
                    style={{
                      fontFamily: "Inter, sans-serif",
                      fontSize: "10px",
                      fontWeight: 500,
                      letterSpacing: "0.11em",
                      textTransform: "uppercase",
                      color: "var(--ep-muted)",
                      textAlign: align as "left" | "right",
                    }}
                  >
                    {label}
                  </span>
                ))}
              </div>
              {results.map((r) => (
                <Link
                  key={r.model_id}
                  href={`/models/${r.model_id}`}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "34px minmax(140px, 1.6fr) minmax(90px, 1fr) minmax(150px, 1.2fr) 70px 84px",
                    alignItems: "center",
                    gap: "8px",
                    minHeight: "44px",
                    padding: "6px 0",
                    borderBottom: "1px solid #18181c",
                    textDecoration: "none",
                  }}
                >
                  <span style={{ fontFamily: "Inter, sans-serif", fontSize: "12.5px", color: r.rank <= 3 ? "#C4A038" : "var(--ep-muted)" }}>
                    {r.rank <= 3 ? ["🥇", "🥈", "🥉"][r.rank - 1] : r.rank}
                  </span>
                  <span style={{ fontSize: "13.5px", fontWeight: 500, color: "var(--ep-text)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                    {r.name}
                  </span>
                  <span style={{ fontSize: "12px", color: "var(--ep-muted)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                    {creatorFlag(r.creator ?? r.provider)?.flag}{" "}
                    {r.creator ?? r.provider ?? "-"}
                  </span>
                  <span style={{ display: "flex", gap: "5px", flexWrap: "wrap" }}>
                    <span
                      title="Price verified hourly from provider APIs"
                      style={{ fontSize: "10.5px", padding: "2px 7px", background: "rgba(196,160,56,0.08)", border: "1px solid rgba(196,160,56,0.35)", color: "#C4A038" }}
                    >
                      Price: verified
                    </span>
                    <span
                      title="Privacy basis comes from the provider's own statements; not yet verified by II"
                      style={{ fontSize: "10.5px", padding: "2px 7px", background: "var(--ep-card)", border: "1px solid var(--ep-border)", color: "var(--ep-muted)" }}
                    >
                      Privacy: provider-stated
                    </span>
                  </span>
                  <span
                    title="Artificial Analysis Intelligence Index"
                    style={{ textAlign: "right", fontFamily: "Inter, sans-serif", fontSize: "12.5px", color: "var(--ep-text-2)", fontVariantNumeric: "tabular-nums" }}
                  >
                    {r.aa_index_score != null ? r.aa_index_score.toFixed(0) : "-"}
                  </span>
                  <span
                    title="Cost/IQ: blended price × (40 / AA score). Lower is better."
                    style={{ textAlign: "right", fontFamily: "Inter, sans-serif", fontSize: "12.5px", color: "#C4A038", fontVariantNumeric: "tabular-nums" }}
                  >
                    {r.cost_per_iq != null ? r.cost_per_iq.toFixed(2) : "-"}
                  </span>
                </Link>
              ))}
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "14px", paddingTop: "10px", flexWrap: "wrap" }}>
                <span style={{ fontSize: "12px", lineHeight: 1.55, color: "var(--ep-muted)" }}>
                  Privacy constraints are matched on provider statements today; II has not verified them. Prices are verified hourly. Ranking is based on data from Artificial Analysis; not endorsed by them.
                </span>
                <Link href="/models" style={{ fontSize: "12.5px", fontWeight: 500, color: "#C4A038", whiteSpace: "nowrap" }}>
                  Full rankings →
                </Link>
              </div>
            </div>
          )}
        </div>

        {/* Embed call-to-action: shown once an answer has been served */}
      {showEmbedLink && (results !== null || providerRows !== null || compare !== null) && (
        <p style={{ margin: "14px 0 0", fontSize: "12.5px", color: "var(--ep-muted)" }}>
          Like this engine?{" "}
          <Link href="/embed-docs" style={{ color: "#C4A038", fontWeight: 500 }}>
            Embed it in your website
          </Link>
        </p>
      )}

      {/* Receipts line */}
        <p style={{ margin: "16px 0 0", fontSize: "12px", color: "var(--ep-faint)", fontVariantNumeric: "tabular-nums" }}>
          {receipts != null && receipts > 0 ? (
            <>
              {receipts.toLocaleString()} recommendations served.{" "}
            </>
          ) : null}
          {gated ? (
            <Link href="/signup" style={{ color: "#C4A038" }}>
              Create a free account for unlimited recommendations.
            </Link>
          ) : (
            <>Queries are never stored.</>
          )}
        </p>
      </div>
    </section>
  );
}
