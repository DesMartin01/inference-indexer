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

interface RecommendResponse {
  recommendations?: Rec[];
  alternatives_considered?: { count?: number; runner_ups?: Rec[] };
  ranking_basis?: { description?: string };
  error?: { code?: string; message?: string };
  detail?: string | { error?: { message?: string } };
}

// ---------- deterministic parser ----------

const USE_CASES = ["support", "volume", "extraction", "summarization", "coding", "research"] as const;

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
    chips.push({ label: "Zero data retention", gold: true });
  }
  // EU
  if (/\beu\b|european|eu[\s-]?(infra|sovereign|domicile)|gdpr/.test(t)) {
    c.eu_sovereign = true;
    chips.push({ label: "EU infrastructure", gold: true });
  }
  // AA quality floor: "above AA index 50", "AA score above 60", "AA 45+"
  const aaFloor = t.match(/aa(?:\s|intelligence)?(?:\s+(?:index|score))?\s*(?:above|over|>|of at least|at least)\s*([0-9]+(?:\.[0-9]+)?)/) || t.match(/aa\s*(?:index|score)?\s*([0-9]+(?:\.[0-9]+)?)\s*\+/);
  if (aaFloor) {
    const v = parseFloat(aaFloor[1]);
    if (v > 0 && v <= 100) {
      c.aa_min = v;
      chips.push({ label: `AA intelligence index ≥ ${v}`, gold: true });
    }
  }
  // Budget: "$2", "under $1.5/M", "below $0.50 per million"
  const budget = t.match(/(?:under|below|less than|max|up to|<)\s*\$?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:\/\s*m|per\s*m(?:illion)?|\/m\b)?/) || t.match(/\$\s*([0-9]+(?:\.[0-9]+)?)\s*(?:\/\s*m|per\s*m(?:illion)?)/);
  if (budget) {
    const v = parseFloat(budget[1]);
    if (v > 0 && v < 1000) {
      c.budget_max_usd_per_m = v;
      chips.push({ label: `Under $${v}/M tokens`, gold: true });
    }
  }
  // Context window: "100k context", "large context", "128k+"
  const ctxK = t.match(/([0-9]+)\s*k?\s*(?:token)?\s*context/) || t.match(/context[^0-9]{0,10}([0-9]+)\s*k/);
  if (ctxK) {
    const k = parseInt(ctxK[1], 10);
    if (k >= 4 && k <= 2000) {
      c.context_min = k * 1000;
      chips.push({ label: `Context ≥ ${k}k tokens`, gold: true });
    }
  } else if (/large context|long context|big context/.test(t)) {
    c.context_min = 128000;
    chips.push({ label: "Context ≥ 128k tokens (large)", gold: true });
  }
  // Reasoning preference
  if (/non[\s-]?reasoning|no[\s-]reasoning|without reasoning|precise[- ]not[- ]smart|deterministic output/.test(t)) {
    c.reasoning = false;
    chips.push({ label: "Non-reasoning models", gold: true });
  } else if (/reasoning|thinking|chain of thought|\bcot\b/.test(t)) {
    c.reasoning = true;
    chips.push({ label: "Reasoning models", gold: true });
  }
  // Use case
  for (const uc of USE_CASES) {
    if (t.includes(uc)) {
      c.use_case = uc;
      chips.push({ label: `Use case: ${uc}`, gold: true });
      break;
    }
  }
  if (/coding|code generation|programming|developer/.test(t) && !c.use_case) {
    c.use_case = "coding";
    chips.push({ label: "Use case: coding", gold: true });
  } else if (/support|customer service|helpdesk|ticket/.test(t) && !c.use_case) {
    c.use_case = "support";
    chips.push({ label: "Use case: support", gold: true });
  }

  // Grey chips: things we recognised but did NOT turn into constraints
  if (/security|prompt injection|router interference/.test(t)) {
    chips.push({ label: "Security: noted (not yet scored)", gold: false });
  }
  if (/sme|london|finance|accounts receivable|agency|startup/.test(t)) {
    chips.push({ label: "Workload context: noted", gold: false });
  }

  return { constraints: c, chips };
}

// ---------- suggestion chips ----------

const SUGGESTIONS: { text: string; fill: string }[] = [
  {
    text: "Cheapest model above AA index 50",
    fill: "Find me the cheapest model with an AA intelligence score above 50",
  },
  {
    text: "Zero data retention providers in the EU",
    fill: "Find me a provider with zero data retention and EU infrastructure",
  },
  {
    text: "Best value for coding agents under $2/M",
    fill: "Best value model for coding agents under $2 per million tokens",
  },
  {
    text: "Providers serving DeepSeek V4, price compared",
    fill: "Compare provider prices for DeepSeek V4",
  },
];

// DeepSeek-style comparison chips route to the model's /models page where the
// endpoint price table lives; the engine cannot rank a single model.
const COMPARISON_ROUTE: { match: RegExp; href: (t: string) => string }[] = [
  {
    match: /compare|price compared|providers serving/,
    href: () => "/models",
  },
];

// ---------- component ----------

export default function EnginePanel({ totalModels }: { totalModels: number }) {
  const [text, setText] = useState("");
  const [chips, setChips] = useState<EchoChip[]>([]);
  const [results, setResults] = useState<Rec[] | null>(null);
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

      // DeepSeek-style comparison queries route to the rankings page instead
      const route = COMPARISON_ROUTE.find((r) => r.match.test(trimmed.toLowerCase()));
      if (route && !/\$|budget|under|cheap|zdr|zero|eu\b/i.test(trimmed)) {
        setStatus("route");
        setTimeout(() => {
          window.location.href = route.href(trimmed);
        }, 900);
        // safety: if navigation hasn't happened in 3s, restore the button
        setTimeout(() => setStatus((s) => (s === "route" ? "idle" : s)), 3000);
        return;
      }

      const { constraints, chips: parsed } = parseConstraints(trimmed);
      setChips(parsed);

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
      <div style={{ borderTop: "1px solid #2a2a2a", paddingTop: "22px" }}>
        <label
          htmlFor="ii-engine-q"
          style={{ fontSize: "19px", fontWeight: 600, letterSpacing: "-0.015em", color: "#f2f2f2", display: "block" }}
        >
          What type of inference are you looking for?
        </label>
        <div
          style={{
            marginTop: "12px",
            background: "#101013",
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
              color: "#f2f2f2",
              fontFamily: "Inter, sans-serif",
              fontSize: "15px",
              lineHeight: 1.5,
            }}
          />
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "14px", flexWrap: "wrap" }}>
            <span style={{ fontSize: "12px", color: "#8a8a8a" }}>
              Plain language or structured constraints — both work. Queries are never stored.
            </span>
            <button
              type="button"
              onClick={() => run(text)}
              disabled={status === "loading" || gated}
              style={{
                fontSize: "13px",
                fontWeight: 500,
                color: gated ? "#8a8a8a" : "#0a0a0a",
                background: gated ? "#2a2a2a" : "#C4A038",
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
          <span style={{ fontSize: "12px", color: "#8a8a8a" }}>Or start from:</span>
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
                color: "#c9c9c9",
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
          <div style={{ marginTop: "18px", paddingLeft: "18px", borderLeft: "2px solid #2a2a2a" }}>
            <span
              style={{
                fontFamily: "var(--font-jetbrains-mono), monospace",
                fontSize: "10px",
                fontWeight: 500,
                letterSpacing: "0.12em",
                textTransform: "uppercase",
                color: "#8a8a8a",
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
                    background: chip.gold ? "rgba(196,160,56,0.08)" : "#131316",
                    border: `1px solid ${chip.gold ? "rgba(196,160,56,0.35)" : "#2a2a2a"}`,
                    color: chip.gold ? "#C4A038" : "#8a8a8a",
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
        {status === "route" && (
          <p style={{ marginTop: "14px", fontSize: "13px", color: "#c9c9c9" }}>
            Single-model price comparison lives on the <Link href="/models" style={{ color: "#C4A038" }}>rankings page</Link> — taking you there…
          </p>
        )}

        {/* Results */}
        <div ref={resultsRef}>
          {results && results.length > 0 && (
            <div style={{ borderTop: "1px solid #1d1d21", marginTop: "26px", paddingTop: "18px" }}>
              <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: "14px", flexWrap: "wrap", marginBottom: "10px" }}>
                <span style={{ fontSize: "16px", fontWeight: 600, color: "#f2f2f2" }}>Recommendations</span>
                <span style={{ fontSize: "12px", color: "#8a8a8a", fontVariantNumeric: "tabular-nums" }}>
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
                  borderBottom: "1px solid #2a2a2a",
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
                      color: "#8a8a8a",
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
                  <span style={{ fontFamily: "Inter, sans-serif", fontSize: "12.5px", color: r.rank <= 3 ? "#C4A038" : "#8a8a8a" }}>
                    {r.rank <= 3 ? ["🥇", "🥈", "🥉"][r.rank - 1] : r.rank}
                  </span>
                  <span style={{ fontSize: "13.5px", fontWeight: 500, color: "#f2f2f2", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                    {r.name}
                  </span>
                  <span style={{ fontSize: "12px", color: "#8a8a8a", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                    {creatorFlag(r.creator ?? r.provider)?.flag}{" "}
                    {r.creator ?? r.provider ?? "—"}
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
                      style={{ fontSize: "10.5px", padding: "2px 7px", background: "#131316", border: "1px solid #2a2a2a", color: "#8a8a8a" }}
                    >
                      Privacy: provider-stated
                    </span>
                  </span>
                  <span
                    title="Artificial Analysis Intelligence Index"
                    style={{ textAlign: "right", fontFamily: "Inter, sans-serif", fontSize: "12.5px", color: "#c9c9c9", fontVariantNumeric: "tabular-nums" }}
                  >
                    {r.aa_index_score != null ? r.aa_index_score.toFixed(0) : "—"}
                  </span>
                  <span
                    title="Cost/IQ: blended price × (40 / AA score). Lower is better."
                    style={{ textAlign: "right", fontFamily: "Inter, sans-serif", fontSize: "12.5px", color: "#C4A038", fontVariantNumeric: "tabular-nums" }}
                  >
                    {r.cost_per_iq != null ? r.cost_per_iq.toFixed(2) : "—"}
                  </span>
                </Link>
              ))}
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "14px", paddingTop: "10px", flexWrap: "wrap" }}>
                <span style={{ fontSize: "12px", lineHeight: 1.55, color: "#8a8a8a" }}>
                  Privacy constraints are matched on provider statements today; II has not verified them. Prices are verified hourly.
                </span>
                <Link href="/models" style={{ fontSize: "12.5px", fontWeight: 500, color: "#C4A038", whiteSpace: "nowrap" }}>
                  Full rankings →
                </Link>
              </div>
            </div>
          )}
        </div>

        {/* Receipts line */}
        <p style={{ margin: "16px 0 0", fontSize: "12px", color: "#6a6a6a", fontVariantNumeric: "tabular-nums" }}>
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
