"use client";

import { useMemo, useState, useEffect } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import type { ModelSummary } from "@/lib/api";
import {
  formatPrice,
  formatPct,
  pctColor,
  sitColor,
  tierColor,
  capitalizeTier,
  providerInitials,
  providerFaviconUrl,
} from "@/lib/api";
import { buildRowSpark } from "@/lib/charts";

// ISO 3166-1 alpha-2 -> flag emoji and full name
const COUNTRY_FLAG_EMOJI: Record<string, string> = {
  us: "🇺🇸", cn: "🇨🇳", gb: "🇬🇧", uk: "🇬🇧", fr: "🇫🇷", de: "🇩🇪",
  ca: "🇨🇦", jp: "🇯🇵", kr: "🇰🇷", in: "🇮🇳", sg: "🇸🇬", ae: "🇦🇪",
  il: "🇮🇱", ch: "🇨🇭", nl: "🇳🇱", se: "🇸🇪", ie: "🇮🇪", au: "🇦🇺",
  tw: "🇹🇼", hk: "🇭🇰", ru: "🇷🇺", br: "🇧🇷", za: "🇿🇦", it: "🇮🇹",
  es: "🇪🇸", fi: "🇫🇮", no: "🇳🇴", dk: "🇩🇰", pl: "🇵🇱", tr: "🇹🇷",
};
const COUNTRY_NAMES: Record<string, string> = {
  us: "United States", cn: "China", gb: "United Kingdom", uk: "United Kingdom",
  fr: "France", de: "Germany", ca: "Canada", jp: "Japan", kr: "South Korea",
  in: "India", sg: "Singapore", ae: "UAE", il: "Israel", ch: "Switzerland",
  nl: "Netherlands", se: "Sweden", ie: "Ireland", au: "Australia",
  tw: "Taiwan", hk: "Hong Kong", ru: "Russia", br: "Brazil", za: "South Africa",
  it: "Italy", es: "Spain", fi: "Finland", no: "Norway", dk: "Denmark",
  pl: "Poland", tr: "Turkey",
};

type SortKey = "name" | "provider" | "tier" | "input" | "output" | "blended" | "sitadj" | "sit" | "sources" | "c24" | "c7";
type SortDir = "asc" | "desc";

type ColKey = SortKey | "rank" | "trend" | "medal";

const COLS_ALL: { key: ColKey; label: string; align: "left" | "right" | "center" }[] = [
  { key: "rank", label: "#", align: "right" },
  { key: "name", label: "Model", align: "left" },
  { key: "provider", label: "Provider", align: "left" },
  { key: "tier", label: "Tier", align: "left" },
  { key: "input", label: "Input $/M", align: "right" },
  { key: "output", label: "Output $/M", align: "right" },
  { key: "blended", label: "Blended $/M", align: "right" },
  { key: "sit", label: "SIT Score", align: "right" },
  { key: "sources", label: "Sources", align: "right" },
  { key: "c24", label: "24h", align: "right" },
  { key: "c7", label: "7d", align: "right" },
  { key: "trend", label: "7d trend", align: "left" },
  { key: "medal", label: "Medal", align: "center" },
];

const COLS_TIER: { key: ColKey; label: string; align: "left" | "right" | "center" }[] = [
  { key: "rank", label: "#", align: "right" },
  { key: "name", label: "Model", align: "left" },
  { key: "provider", label: "Provider", align: "left" },
  { key: "tier", label: "Tier", align: "left" },
  { key: "input", label: "Input $/M", align: "right" },
  { key: "output", label: "Output $/M", align: "right" },
  { key: "blended", label: "Blended $/M", align: "right" },
  { key: "sitadj", label: "Cost / IQ", align: "right" },
  { key: "sit", label: "SIT Score", align: "right" },
  { key: "sources", label: "Sources", align: "right" },
  { key: "c24", label: "24h", align: "right" },
  { key: "c7", label: "7d", align: "right" },
  { key: "trend", label: "7d trend", align: "left" },
  { key: "medal", label: "Medal", align: "center" },
];

const GRID_ALL = "30px minmax(130px, 275px) 84px 76px 82px 82px 108px 100px 104px 56px 64px 64px 84px 48px";
const GRID_TIER = "30px minmax(130px, 275px) 84px 76px 82px 82px 108px 100px 104px 56px 64px 64px 84px 48px";

interface Props {
  models: ModelSummary[];
  totalCount: number;
}

export default function ModelTable({ models, totalCount }: Props) {
  const [sort, setSort] = useState<SortKey>("sit");
  const [dir, setDir] = useState<SortDir>("asc");
  const [variant, setVariant] = useState("frontier");
  const [query, setQuery] = useState("");
  const [expanded, setExpanded] = useState(false);
  const [provider, setProvider] = useState<string | null>(null);
  const [zdrOnly, setZdrOnly] = useState(false);
  const [euOnly, setEuOnly] = useState(false);
  const searchParams = useSearchParams();

  // Dynamic columns and grid based on tier filter
  const showCostIQ = variant !== "all";
  const COLS = showCostIQ ? COLS_TIER : COLS_ALL;
  const GRID = showCostIQ ? GRID_TIER : GRID_ALL;

  // When tier filter changes, switch default sort:
  // "all" = sort by blended price (SIT Score not cross-tier comparable)
  // specific tier = sort by SIT Score (within-tier ranking)
  useEffect(() => {
    if (variant === "all") {
      setSort("blended");
      setDir("asc");
    } else {
      setSort("sit");
      setDir("asc");
    }
  }, [variant]);

  // Pick up search query from URL (set by nav search bar)
  useEffect(() => {
    const urlQ = searchParams.get("q");
    if (urlQ !== null) setQuery(urlQ);
  }, [searchParams]);

  const pills: [string, string][] = [
    ["all", "All"],
    ["frontier", "Frontier"],
    ["standard", "Standard"],
    ["budget", "Budget"],
    ["micro", "Micro"],
  ];

  // ZDR and EU Infra flags come from the providers table via the API
  const matchVariant = (m: ModelSummary): boolean => {
    if (variant === "all") return true;
    return m.tier.toLowerCase() === variant;
  };

  const matchZdr = (m: ModelSummary): boolean => {
    if (!zdrOnly) return true;
    return m.is_zdr === true;
  };

  const matchEu = (m: ModelSummary): boolean => {
    if (!euOnly) return true;
    return m.is_eu_sovereign === true;
  };

  // All models are provided server-side now (API is 82ms, no need for client fetch)
  const allModels = models;

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    let list = allModels.filter(matchVariant).filter(matchZdr).filter(matchEu);
    if (provider) list = list.filter((m) => m.provider === provider);
    if (q) {
      list = list.filter(
        (m) =>
          m.name.toLowerCase().includes(q) ||
          m.provider.toLowerCase().includes(q) ||
          m.model_id.toLowerCase().includes(q),
      );
    }

    list = list.slice().sort((a, b) => {
      const k = sort;
      const sign = dir === "asc" ? 1 : -1;
      // Map sort keys to actual model field names
      const fieldMap: Record<string, string> = {
        input: "input_price_per_m",
        output: "output_price_per_m",
        blended: "blended_price_per_m",
        sitadj: "sit_adjusted_price",
        c24: "change_24h",
        c7: "change_7d",
      };
      if (k === "sit") {
        // Null scores sort last regardless of direction
        if (a.sit_score == null && b.sit_score == null) return 0;
        if (a.sit_score == null) return 1;
        if (b.sit_score == null) return -1;
        return (a.sit_score - b.sit_score) * sign;
      }
      if (k === "sitadj") {
        // Null adjusted prices sort last regardless of direction
        const av = a.sit_adjusted_price;
        const bv = b.sit_adjusted_price;
        if (av == null && bv == null) return 0;
        if (av == null) return 1;
        if (bv == null) return -1;
        return (av - bv) * sign;
      }
      if (k === "sources") return ((a.source_count ?? 1) - (b.source_count ?? 1)) * sign;
      const fieldName = fieldMap[k];
      if (fieldName) {
        const av = (a[fieldName as keyof ModelSummary] as number) ?? 0;
        const bv = (b[fieldName as keyof ModelSummary] as number) ?? 0;
        return (av - bv) * sign;
      }
      return String(a[k as keyof ModelSummary] ?? "").localeCompare(String(b[k as keyof ModelSummary] ?? "")) * sign;
    });

    return list;
  }, [allModels, sort, dir, variant, query, provider, zdrOnly, euOnly]);

  // Compute global ranking by SIT score (nulls last)
  const ranked = useMemo(() => {
    return allModels.slice().sort((a, b) => {
      if (a.sit_score == null && b.sit_score == null) return 0;
      if (a.sit_score == null) return 1;
      if (b.sit_score == null) return -1;
      return a.sit_score - b.sit_score;
    });
  }, [allModels]);

  const rankOf = (m: ModelSummary) => {
    const idx = ranked.findIndex((r) => r.model_id === m.model_id);
    return idx >= 0 ? idx + 1 : 0;
  };

  // Per-tier SIT score rankings for medals (gold/silver/bronze = top 3 in each tier)
  const tierMedals = useMemo(() => {
    const medals: Record<string, number> = {}; // model_id -> 1|2|3
    const tiers = ["frontier", "standard", "budget", "micro"];
    for (const tier of tiers) {
      const tierModels = allModels
        .filter((m) => m.tier.toLowerCase() === tier && m.sit_score != null)
        .sort((a, b) => (a.sit_score! - b.sit_score!));
      tierModels.slice(0, 3).forEach((m, i) => {
        medals[m.model_id] = i + 1;
      });
    }
    return medals;
  }, [allModels]);

  const medalOf = (m: ModelSummary): number | null => {
    return tierMedals[m.model_id] ?? null;
  };

  const sortBy = (key: ColKey) => {
    if (key === "rank" || key === "trend" || key === "medal") return;
    if (sort === key) {
      setDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSort(key);
      setDir("asc");
    }
  };

  const LIMIT = 100;
  const visible = expanded ? filtered : filtered.slice(0, LIMIT);
  const hidden = filtered.length - visible.length;

  // Movers
  const droppers = filtered
    .filter((m) => (m.change_24h ?? 0) < 0)
    .sort((a, b) => (a.change_24h ?? 0) - (b.change_24h ?? 0))
    .slice(0, 5);
  const risers = filtered
    .filter((m) => (m.change_24h ?? 0) > 0)
    .sort((a, b) => (b.change_24h ?? 0) - (a.change_24h ?? 0))
    .slice(0, 5);

  const moversScope = provider || (variant === "all" ? "all models" : `SIT-${capitalizeTier(variant)}`);

  return (
    <>
      <style dangerouslySetInnerHTML={{ __html: `
        .ii-tip-wrap:hover .ii-tip { display: block !important; }
      `}} />
      {/* Filter pills + legend on same row */}
      <section id="model-table" style={{ maxWidth: "1320px", margin: "0 auto", padding: "30px 28px 0" }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "16px",
            flexWrap: "wrap",
            justifyContent: "space-between",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "7px", flexWrap: "wrap" }}>
            {provider && (
              <button
                type="button"
                onClick={() => setProvider(null)}
                title="Clear provider filter"
                style={{
                  fontFamily: "Inter, sans-serif",
                  fontSize: "12px",
                  padding: "5px 9px 5px 11px",
                  borderRadius: "4px",
                  cursor: "pointer",
                  background: "#26262c",
                  color: "#e5e5e5",
                  border: "1px solid #3a3a3a",
                  display: "flex",
                  alignItems: "center",
                  gap: "7px",
                }}
              >
                {provider} <span style={{ color: "#8a8a8a" }}>×</span>
              </button>
            )}
            {pills.map(([key, label]) => {
              const active = variant === key;
              return (
                <button
                  key={key}
                  type="button"
                  onClick={() => setVariant(key)}
                  aria-pressed={active}
                  style={{
                    fontFamily: "Inter, sans-serif",
                    fontSize: "12px",
                    padding: "5px 11px",
                    borderRadius: "4px",
                    cursor: "pointer",
                    background: active ? "#C4A038" : "transparent",
                    color: active ? "#0a0a0a" : "#9a9a9a",
                    border: `1px solid ${active ? "#C4A038" : "#2f2f2f"}`,
                    transition: "border-color 120ms, color 120ms",
                  }}
                >
                  {label}
                </button>
              );
            })}
            <button
              type="button"
              onClick={() => setZdrOnly((v) => !v)}
              aria-pressed={zdrOnly}
              title="Filter to providers that guarantee zero data retention (no training on inputs, no logging)"
              style={{
                fontFamily: "Inter, sans-serif",
                fontSize: "12px",
                padding: "5px 11px",
                borderRadius: "4px",
                cursor: "pointer",
                background: zdrOnly ? "#C4A038" : "transparent",
                color: zdrOnly ? "#0a0a0a" : "#9a9a9a",
                border: `1px solid ${zdrOnly ? "#C4A038" : "#2f2f2f"}`,
                transition: "border-color 120ms, color 120ms",
                marginLeft: "8px",
              }}
            >
              ZDR
            </button>
            <button
              type="button"
              onClick={() => setEuOnly((v) => !v)}
              aria-pressed={euOnly}
              title="Filter to EU-domiciled providers not subject to US CLOUD Act"
              style={{
                fontFamily: "Inter, sans-serif",
                fontSize: "12px",
                padding: "5px 11px",
                borderRadius: "4px",
                cursor: "pointer",
                background: euOnly ? "#C4A038" : "transparent",
                color: euOnly ? "#0a0a0a" : "#9a9a9a",
                border: `1px solid ${euOnly ? "#C4A038" : "#2f2f2f"}`,
                transition: "border-color 120ms, color 120ms",
                marginLeft: "8px",
              }}
            >
              EU Infra
            </button>
          </div>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "14px",
              fontSize: "11.5px",
              color: "#6f6f6f",
              flexWrap: "wrap",
            }}
          >
            <span style={{ display: "flex", alignItems: "center", gap: "5px" }}>
              <span style={{ fontFamily: "var(--font-jetbrains-mono), monospace", color: "#22c55e" }}>↓</span>
              cheaper
            </span>
            <span style={{ display: "flex", alignItems: "center", gap: "5px" }}>
              <span style={{ fontFamily: "var(--font-jetbrains-mono), monospace", color: "#ef4444" }}>↑</span>
              price up
            </span>
            <span style={{ color: "#4a4a4a" }}>|</span>
            <span style={{ display: "flex", alignItems: "center", gap: "5px" }}>
              <span style={{ color: "#C4A038" }}>●</span> Frontier
            </span>
            <span style={{ display: "flex", alignItems: "center", gap: "5px" }}>
              <span style={{ color: "#5b8def" }}>●</span> Standard
            </span>
            <span style={{ display: "flex", alignItems: "center", gap: "5px" }}>
              <span style={{ color: "#22c55e" }}>●</span> Budget
            </span>
            <span style={{ display: "flex", alignItems: "center", gap: "5px" }}>
              <span style={{ color: "#7a7a7a" }}>●</span> Micro
            </span>
          </div>
        </div>
      </section>

      {/* Table */}
      <section style={{ maxWidth: "1320px", margin: "0 auto", padding: "18px 28px 0" }}>
        <div
          style={{
            display: "flex",
            alignItems: "baseline",
            justifyContent: "space-between",
            gap: "16px",
            flexWrap: "wrap",
            padding: "0 2px 10px",
          }}
        >
          <span style={{ fontSize: "13px", color: "#9a9a9a", fontVariantNumeric: "tabular-nums" }}>
            Showing {visible.length} of {filtered.length} models{filtered.length !== totalCount ? ` (filtered from ${totalCount})` : ""}
          </span>
          <span style={{ fontSize: "12px", color: "#5f5f5f" }}>
            Sorted by {COLS.find((c) => c.key === sort)?.label} · click any column to re-sort
          </span>
        </div>
        <div style={{ overflowX: "auto" }}>
          <div role="table" aria-label="AI model inference prices" style={{ minWidth: "auto" }}>
            {/* Header */}
            <div
              role="row"
              style={{
                background: "#0a0a0a",
                display: "grid",
                gridTemplateColumns: GRID,
                alignItems: "center",
                height: "34px",
                borderBottom: "1px solid #2a2a2a",
                overflow: "visible",
                position: "relative",
                zIndex: 10,
              }}
            >
              {COLS.map((c) => {
                const active = sort === c.key;
                const arrow = active ? (dir === "asc" ? " ↑" : " ↓") : "";
                return (
                  <div
                    key={c.key}
                    role="columnheader"
                    aria-sort={active ? (dir === "asc" ? "ascending" : "descending") : "none"}
                    onClick={() => sortBy(c.key)}
                    style={{
                      fontSize: "11px",
                      fontWeight: 500,
                      textTransform: "uppercase",
                      letterSpacing: "0.08em",
                      color: active ? "#C4A038" : "#8a8a8a",
                      textAlign: c.align,
                      cursor: c.key === "rank" || c.key === "trend" || c.key === "medal" ? "default" : "pointer",
                      userSelect: "none",
                      whiteSpace: "nowrap",
                      padding: "0 8px",
                      height: "34px",
                      lineHeight: "34px",
                      boxShadow: active ? "inset 0 -1px 0 #C4A038" : "none",
                      overflow: "visible",
                      position: "relative",
                    }}
                  >
                    {c.key === "sitadj" && (
                      <span className="ii-tip-wrap" style={{ position: "relative", display: "inline-flex", cursor: "help", marginLeft: "3px" }}>
                        <span style={{ width: "11px", height: "11px", borderRadius: "50%", border: "1px solid #5f5f5f", color: "#5f5f5f", fontSize: "8px", lineHeight: "10px", textAlign: "center", fontFamily: "Inter, sans-serif" }}>i</span>
                        <span className="ii-tip" style={{
                          display: "none", position: "absolute", top: "140%", left: "50%",
                          transform: "translateX(-50%)", background: "#1a1a1a", color: "#e0e0e0",
                          border: "1px solid #C4A038", padding: "8px 12px", borderRadius: "6px",
                          fontSize: "12px", lineHeight: "1.5", whiteSpace: "normal", width: "260px",
                          zIndex: 9999, pointerEvents: "none", boxShadow: "0 4px 12px rgba(0,0,0,0.5)", textAlign: "left",
                        }}>
                          Cost / IQ = Blended Price x (40 / AA Intelligence Score). Represents the cost of producing GPT-4-Turbo-equivalent inference tokens. Lower = better value per unit of intelligence. Not a transactional price.
                        </span>
                      </span>
                    )}
                    {c.key === "sit" && (
                      <span className="ii-tip-wrap" style={{ position: "relative", display: "inline-flex", cursor: "help", marginLeft: "3px" }}>
                        <span style={{ width: "11px", height: "11px", borderRadius: "50%", border: "1px solid #5f5f5f", color: "#5f5f5f", fontSize: "8px", lineHeight: "10px", textAlign: "center", fontFamily: "Inter, sans-serif" }}>i</span>
                        <span className="ii-tip" style={{
                          display: "none", position: "absolute", top: "140%", left: "50%",
                          transform: "translateX(-50%)", background: "#1a1a1a", color: "#e0e0e0",
                          border: "1px solid #C4A038", padding: "8px 12px", borderRadius: "6px",
                          fontSize: "12px", lineHeight: "1.5", whiteSpace: "normal", width: "260px",
                          zIndex: 9999, pointerEvents: "none", boxShadow: "0 4px 12px rgba(0,0,0,0.5)", textAlign: "left",
                        }}>
                          SIT Score is tier-relative (100 = your tier's median). Lower = cheaper than your tier's median. Colors match tier: gold = Frontier, blue = Standard, green = Budget, grey = Micro. Scores are NOT comparable across tiers.
                        </span>
                      </span>
                    )}
                    {c.label + arrow}
                  </div>
                );
              })}
            </div>
            {/* Rows */}
            {visible.map((m) => {
              const s = m.sit_score;
              const c24 = m.change_24h ?? 0;
              const c7 = m.change_7d ?? 0;
              const tColor = tierColor(m.tier);
              const trendColor = c7 < 0 ? "#22c55e" : c7 > 0 ? "#ef4444" : "#4a4a4a";
              const trendPath = buildRowSpark(m.blended_price_per_m, c7);
              return (
                <div
                  key={m.model_id}
                  role="row"
                  style={{
                    display: "grid",
                    gridTemplateColumns: GRID,
                    alignItems: "center",
                    height: "60px",
                    borderBottom: "1px solid #171717",
                    transition: "background 90ms",
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = "#141414";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = "transparent";
                  }}
                >
                  <div
                    role="cell"
                    style={{
                      fontSize: "13px",
                      fontWeight: 500,
                      color: "#6a6a6a",
                      padding: "0 10px",
                      textAlign: "right",
                      fontVariantNumeric: "tabular-nums",
                    }}
                  >
                    {rankOf(m)}
                  </div>
                  <div role="cell" style={{ padding: "0 6px", display: "flex", alignItems: "center", gap: "7px", minWidth: 0 }}>
                    <span
                        style={{
                          width: "20px",
                          height: "20px",
                          borderRadius: "50%",
                          background: "#16161a",
                          border: "1px solid #33333a",
                          flex: "none",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          overflow: "hidden",
                        }}
                      >
                        {(() => {
                          const fav = providerFaviconUrl(m.provider);
                          return fav ? (
                            <img
                              src={fav}
                              alt={m.provider}
                              width={14}
                              height={14}
                              loading="lazy"
                              style={{ width: "14px", height: "14px", objectFit: "contain" }}
                            />
                          ) : (
                            <span style={{ fontFamily: "var(--font-jetbrains-mono), monospace", fontSize: "9.5px", color: "#8f8f96" }}>
                              {providerInitials(m.provider)}
                            </span>
                          );
                        })()}
                      </span>
                    <span style={{ display: "flex", flexDirection: "column", gap: "3px", minWidth: 0 }}>
                      <Link
                        href={`/models/${m.model_id}`}
                        style={{
                          fontSize: "13.5px",
                          color: "#f2f2f2",
                          textDecoration: "none",
                          whiteSpace: "nowrap",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                        }}
                      >
                        {m.name}
                      </Link>
                      <span
                        style={{
                          fontFamily: "var(--font-jetbrains-mono), monospace",
                          fontSize: "10.5px",
                          color: "#6a6a6a",
                          whiteSpace: "nowrap",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                        }}
                      >
                        {m.model_id}
                      </span>
                    </span>
                  </div>
                  <div role="cell" style={{ padding: "0 6px", minWidth: 0, display: "flex", alignItems: "center", gap: "4px" }}>
                    {m.creator_country && <span style={{ fontSize: "12px", lineHeight: 1, flexShrink: 0 }} title={COUNTRY_NAMES[m.creator_country] || m.creator_country}>{COUNTRY_FLAG_EMOJI[m.creator_country] || ""}</span>}
                    <Link
                      href={`/providers/${encodeURIComponent(m.provider)}`}
                      style={{
                        fontFamily: "Inter, sans-serif",
                        fontSize: "12.5px",
                        color: "#8a8a8a",
                        textDecoration: "none",
                        display: "inline-block",
                        maxWidth: "100%",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {m.provider}
                    </Link>
                  </div>
                  <div role="cell" style={{ padding: "0 10px" }}>
                    <span
                      style={{
                        display: "inline-block",
                        fontSize: "11px",
                        letterSpacing: "0.04em",
                        textTransform: "uppercase",
                        padding: "2px 7px",
                        borderRadius: "3px",
                        border: `1px solid ${tColor}`,
                        color: tColor,
                        background: "transparent",
                      }}
                    >
                      {capitalizeTier(m.tier)}
                    </span>
                  </div>
                  <div
                    role="cell"
                    style={{
                      fontSize: "13px",
                      fontWeight: 500,
                      color: "#c9c9c9",
                      padding: "0 10px",
                      textAlign: "right",
                      fontVariantNumeric: "tabular-nums",
                    }}
                  >
                    {formatPrice(m.input_price_per_m)}
                  </div>
                  <div
                    role="cell"
                    style={{
                      fontSize: "13px",
                      fontWeight: 500,
                      color: "#c9c9c9",
                      padding: "0 10px",
                      textAlign: "right",
                      fontVariantNumeric: "tabular-nums",
                    }}
                  >
                    {formatPrice(m.output_price_per_m)}
                  </div>
                  <div
                    role="cell"
                    style={{
                      fontSize: "13px",
                      fontWeight: 500,
                      color: "#c9c9c9",
                      padding: "0 10px",
                      textAlign: "right",
                      fontVariantNumeric: "tabular-nums",
                    }}
                  >
                    {formatPrice(m.blended_price_per_m)}
                  </div>
                  {showCostIQ && (
                    <div
                      role="cell"
                      title={m.sit_adjusted_price != null ? `${m.name}: Cost / IQ $${m.sit_adjusted_price.toFixed(4)}/M (quality-adjusted, not transactional)` : `${m.name}: no AA Intelligence Index score`}
                      style={{
                        fontSize: "13px",
                        fontWeight: 500,
                        color: m.sit_adjusted_price != null ? "#7ec47e" : "#5f5f5f",
                        padding: "0 10px",
                        textAlign: "right",
                        fontVariantNumeric: "tabular-nums",
                        cursor: "help",
                      }}
                    >
                      {m.sit_adjusted_price != null ? `$${m.sit_adjusted_price.toFixed(4)}` : "N/A"}
                    </div>
                  )}
                  <div
                    role="cell"
                    title={s != null ? `${m.name}: SIT Score ${s} (${capitalizeTier(m.tier)} tier, 100 = tier median. Lower = cheaper than median. Score is tier-relative, not comparable across tiers.)` : `${m.name}: no AA Intelligence Index score, SIT Score not available`}
                    style={{
                      fontSize: "13.5px",
                      fontWeight: 600,
                      color: s != null ? tColor : "#5f5f5f",
                      padding: "0 10px",
                      textAlign: "right",
                      fontVariantNumeric: "tabular-nums",
                      cursor: "help",
                    }}
                  >
                    {s != null ? s : "N/A"}
                  </div>
                  <div
                    role="cell"
                    title={`${m.source_count ?? 1} provider${(m.source_count ?? 1) > 1 ? "s" : ""} offer this model`}
                    style={{ fontSize: "13px", fontWeight: 500, color: (m.source_count ?? 1) > 1 ? "#c9c9c9" : "#5f5f5f", padding: "0 10px", textAlign: "right", fontVariantNumeric: "tabular-nums" }}
                  >
                    {m.source_count ?? 1}
                  </div>
                  <div
                    role="cell"
                    style={{ fontSize: "13px", fontWeight: 500, color: pctColor(c24), padding: "0 10px", textAlign: "right", fontVariantNumeric: "tabular-nums" }}
                  >
                    {formatPct(c24)}
                  </div>
                  <div
                    role="cell"
                    style={{
                      fontSize: "13px",
                      fontWeight: 500,
                      color: pctColor(c7),
                      padding: "0 10px",
                      textAlign: "right",
                      fontVariantNumeric: "tabular-nums",
                    }}
                  >
                    {formatPct(c7)}
                  </div>
                  <div role="cell" style={{ padding: "0 10px" }}>
                    <svg
                      viewBox="0 0 84 18"
                      role="img"
                      aria-label="7 day price trend"
                      style={{ display: "block", width: "84px", height: "18px" }}
                    >
                      <path
                        d={trendPath}
                        fill="none"
                        stroke={trendColor}
                        strokeWidth="1.25"
                        strokeLinejoin="round"
                        strokeLinecap="round"
                      />
                    </svg>
                  </div>
                  {/* Medal column: gold/silver/bronze for top 3 per tier */}
                  <div role="cell" style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
                    {(() => {
                      const medal = medalOf(m);
                      if (!medal) return null;
                      const colors: Record<number, { fill: string; ring: string; label: string }> = {
                        1: { fill: "#FFD700", ring: "#B8860B", label: "Gold" },
                        2: { fill: "#C0C0C0", ring: "#808080", label: "Silver" },
                        3: { fill: "#CD7F32", ring: "#8B4513", label: "Bronze" },
                      };
                      const c = colors[medal];
                      return (
                        <svg width="20" height="20" viewBox="0 0 20 20" role="img" aria-label={`${c.label} medal - #${medal} in ${capitalizeTier(m.tier)} tier`}>
                          <circle cx="10" cy="10" r="7" fill={c.fill} stroke={c.ring} strokeWidth="1.5" />
                          <text x="10" y="13" textAnchor="middle" fontSize="8" fontWeight="700" fill={c.ring} fontFamily="sans-serif">{medal}</text>
                        </svg>
                      );
                    })()}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "16px",
            flexWrap: "wrap",
            padding: "14px 10px 0",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "12px", color: "#6f6f6f" }}>
            <span>
              {visible.length} of {totalCount} models shown · updated recently
            </span>
          </div>
          {hidden > 0 && (
            <button
              type="button"
              onClick={() => setExpanded((e) => !e)}
              style={{
                fontFamily: "Inter, sans-serif",
                fontSize: "13px",
                color: "#C4A038",
                background: "transparent",
                border: 0,
                padding: 0,
                cursor: "pointer",
              }}
            >
              {expanded
                ? `← Show top ${LIMIT} only`
                : `Show all ${filtered.length} models →`}
            </button>
          )}
        </div>
      </section>

      {/* Biggest movers */}
      <section style={{ maxWidth: "1320px", margin: "0 auto", padding: "34px 28px 0" }}>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
            gap: "14px",
          }}
        >
          <div
            style={{
              background: "#16161a",
              border: "1px solid #2a2a2a",
              borderRadius: "8px",
              padding: "15px 18px 8px",
            }}
          >
            <div
              style={{
                fontSize: "12px",
                textTransform: "uppercase",
                letterSpacing: "0.1em",
                color: "#8a8a8a",
                paddingBottom: "6px",
                borderBottom: "1px solid #232327",
              }}
            >
              <span style={{ fontFamily: "var(--font-jetbrains-mono), monospace", color: "#22c55e" }}>↓</span> Biggest price drops (24h){" "}
              <span style={{ textTransform: "none", letterSpacing: 0, color: "#5f5f5f" }}>· {moversScope}</span>
            </div>
            {droppers.length === 0 ? (
              <div style={{ height: "34px", display: "flex", alignItems: "center", fontSize: "12.5px", color: "#6a6a6a" }}>
                No price drops in the last 24h
              </div>
            ) : (
              droppers.map((m) => (
                <div
                  key={m.model_id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    height: "34px",
                    borderBottom: "1px solid #1c1c20",
                  }}
                >
                  <Link
                    href={`/models/${m.model_id}`}
                    style={{ fontSize: "13px", color: "#e5e5e5", textDecoration: "none" }}
                  >
                    {m.name}
                  </Link>
                  <span
                    style={{
                      fontSize: "13px",
                      fontWeight: 500,
                      color: "#22c55e",
                      fontVariantNumeric: "tabular-nums",
                    }}
                  >
                    {formatPct(m.change_24h)}
                  </span>
                </div>
              ))
            )}
          </div>
          <div
            style={{
              background: "#16161a",
              border: "1px solid #2a2a2a",
              borderRadius: "8px",
              padding: "15px 18px 8px",
            }}
          >
            <div
              style={{
                fontSize: "12px",
                textTransform: "uppercase",
                letterSpacing: "0.1em",
                color: "#8a8a8a",
                paddingBottom: "6px",
                borderBottom: "1px solid #232327",
              }}
            >
              <span style={{ fontFamily: "var(--font-jetbrains-mono), monospace", color: "#ef4444" }}>↑</span> Biggest price increases (24h){" "}
              <span style={{ textTransform: "none", letterSpacing: 0, color: "#5f5f5f" }}>· {moversScope}</span>
            </div>
            {risers.length === 0 ? (
              <div style={{ height: "34px", display: "flex", alignItems: "center", fontSize: "12.5px", color: "#6a6a6a" }}>
                No price increases in the last 24h
              </div>
            ) : (
              risers.map((m) => (
                <div
                  key={m.model_id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    height: "34px",
                    borderBottom: "1px solid #1c1c20",
                  }}
                >
                  <Link
                    href={`/models/${m.model_id}`}
                    style={{ fontSize: "13px", color: "#e5e5e5", textDecoration: "none" }}
                  >
                    {m.name}
                  </Link>
                  <span
                    style={{
                      fontSize: "13px",
                      fontWeight: 500,
                      color: "#ef4444",
                      fontVariantNumeric: "tabular-nums",
                    }}
                  >
                    {formatPct(m.change_24h)}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      </section>
    </>
  );
}
