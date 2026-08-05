"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import type { ModelSummary } from "@/lib/api";
import {
  formatPrice,
  formatPct,
  pctColor,
  sitColor,
  tierColor,
  capitalizeTier,
  providerInitials,
} from "@/lib/api";
import { buildRowSpark } from "@/lib/charts";

type SortKey = "name" | "provider" | "tier" | "input" | "output" | "blended" | "sit" | "c24" | "c7";
type SortDir = "asc" | "desc";

type ColKey = SortKey | "rank" | "trend";
const COLS: { key: ColKey; label: string; align: "left" | "right" }[] = [
  { key: "rank", label: "#", align: "right" },
  { key: "name", label: "Model", align: "left" },
  { key: "provider", label: "Provider", align: "left" },
  { key: "tier", label: "Tier", align: "left" },
  { key: "input", label: "Input $/M", align: "right" },
  { key: "output", label: "Output $/M", align: "right" },
  { key: "blended", label: "Blended $/M", align: "right" },
  { key: "sit", label: "SIT Score", align: "right" },
  { key: "c24", label: "24h", align: "right" },
  { key: "c7", label: "7d", align: "right" },
  { key: "trend", label: "7d trend", align: "left" },
];

const GRID = "46px minmax(160px, 1.5fr) minmax(100px, 1fr) 100px 96px 104px 108px 104px 80px 80px 104px";

interface Props {
  models: ModelSummary[];
  totalCount: number;
}

export default function ModelTable({ models, totalCount }: Props) {
  const [sort, setSort] = useState<SortKey>("sit");
  const [dir, setDir] = useState<SortDir>("asc");
  const [variant, setVariant] = useState("all");
  const [query, setQuery] = useState("");
  const [expanded, setExpanded] = useState(false);
  const [provider, setProvider] = useState<string | null>(null);

  const pills: [string, string][] = [
    ["all", "All"],
    ["frontier", "Frontier"],
    ["standard", "Standard"],
    ["budget", "Budget"],
    ["micro", "Micro"],
  ];

  const matchVariant = (m: ModelSummary): boolean => {
    if (variant === "all") return true;
    return m.tier.toLowerCase() === variant;
  };

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    let list = models.filter(matchVariant);
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
      const num = (k: string) =>
        k === "input" || k === "output" || k === "blended" || k === "c24" || k === "c7" || k === "sit";
      if (k === "sit") return ((a.sit_score ?? 0) - (b.sit_score ?? 0)) * sign;
      if (num(k)) {
        const av = (a[k as keyof ModelSummary] as number) ?? 0;
        const bv = (b[k as keyof ModelSummary] as number) ?? 0;
        return (av - bv) * sign;
      }
      return String(a[k as keyof ModelSummary] ?? "").localeCompare(String(b[k as keyof ModelSummary] ?? "")) * sign;
    });

    return list;
  }, [models, sort, dir, variant, query, provider]);

  // Compute global ranking by SIT score
  const ranked = useMemo(() => {
    return models.slice().sort((a, b) => (a.sit_score ?? 0) - (b.sit_score ?? 0));
  }, [models]);

  const rankOf = (m: ModelSummary) => {
    const idx = ranked.findIndex((r) => r.model_id === m.model_id);
    return idx >= 0 ? idx + 1 : 0;
  };

  const sortBy = (key: ColKey) => {
    if (key === "rank" || key === "trend") return;
    if (sort === key) {
      setDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSort(key);
      setDir("asc");
    }
  };

  const LIMIT = 50;
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
      {/* Filter pills + legend on same row */}
      <section style={{ maxWidth: "1320px", margin: "0 auto", padding: "30px 28px 0" }}>
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
            <span title="SIT Score = model blended price / tier average. Below 1.0 = cheaper than tier average." style={{ cursor: "help" }}>
              SIT Score = price ÷ tier avg · <span style={{ color: "#22c55e" }}>&lt;0.50</span> ·{" "}
              <span style={{ color: "#c9c9c9" }}>0.50–1.00</span> · <span style={{ color: "#C4A038" }}>&gt;1.00</span>
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
          <div role="table" aria-label="AI model inference prices" style={{ minWidth: "1180px" }}>
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
                      cursor: c.key === "rank" || c.key === "trend" ? "default" : "pointer",
                      userSelect: "none",
                      whiteSpace: "nowrap",
                      padding: "0 8px",
                      height: "34px",
                      lineHeight: "34px",
                      boxShadow: active ? "inset 0 -1px 0 #C4A038" : "none",
                    }}
                  >
                    {c.label + arrow}
                  </div>
                );
              })}
            </div>
            {/* Rows */}
            {visible.map((m) => {
              const s = m.sit_score ?? 0;
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
                  <div role="cell" style={{ padding: "0 10px", display: "flex", alignItems: "center", gap: "9px", minWidth: 0 }}>
                    <span
                      title={`${m.provider} — logo placeholder`}
                      style={{
                        width: "24px",
                        height: "24px",
                        borderRadius: "50%",
                        background: "repeating-linear-gradient(135deg, #24242a 0 2px, #1c1c21 2px 4px)",
                        border: "1px solid #33333a",
                        flex: "none",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontFamily: "var(--font-jetbrains-mono), monospace",
                        fontSize: "9.5px",
                        letterSpacing: "-0.02em",
                        color: "#8f8f96",
                        overflow: "hidden",
                      }}
                    >
                      {providerInitials(m.provider)}
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
                  <div role="cell" style={{ padding: "0 10px", minWidth: 0 }}>
                    <button
                      type="button"
                      onClick={() => setProvider(m.provider)}
                      title={`Filter to ${m.provider}`}
                      style={{
                        fontFamily: "Inter, sans-serif",
                        fontSize: "12.5px",
                        color: "#8a8a8a",
                        background: "transparent",
                        border: 0,
                        padding: 0,
                        cursor: "pointer",
                        maxWidth: "100%",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                        textAlign: "left",
                      }}
                    >
                      {m.provider}
                    </button>
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
                  <div
                    role="cell"
                    title={`${m.name}: ${formatPrice(m.blended_price_per_m)} vs ${capitalizeTier(m.tier)} tier avg`}
                    style={{
                      fontSize: "13.5px",
                      fontWeight: 600,
                      color: sitColor(s),
                      padding: "0 10px",
                      textAlign: "right",
                      fontVariantNumeric: "tabular-nums",
                      cursor: "help",
                    }}
                  >
                    {s.toFixed(2)}
                  </div>
                  <div
                    role="cell"
                    style={{
                      fontSize: "13px",
                      fontWeight: 500,
                      color: pctColor(c24),
                      padding: "0 10px",
                      textAlign: "right",
                      fontVariantNumeric: "tabular-nums",
                    }}
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
            <span
              style={{
                width: "6px",
                height: "6px",
                borderRadius: "50%",
                background: "#22c55e",
                display: "block",
              }}
            />
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
              {expanded ? "← Show top 50 only" : `Show all ${filtered.length} models →`}
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
