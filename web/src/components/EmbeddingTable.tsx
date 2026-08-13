"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import type { EmbeddingModel } from "@/lib/api";
import {
  formatPrice,
  providerInitials,
  providerFaviconUrl,
} from "@/lib/api";

// ISO 3166-1 alpha-2 -> flag emoji and full name (same pattern as ModelTable)
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

type SortKey = "name" | "provider" | "dims" | "context" | "price" | "sources";
type SortDir = "asc" | "desc";

const COLS: { key: SortKey; label: string; align: "left" | "right" | "center" }[] = [
  { key: "name", label: "Model", align: "left" },
  { key: "provider", label: "Creator", align: "left" },
  { key: "dims", label: "Dims", align: "right" },
  { key: "context", label: "Max Context", align: "right" },
  { key: "price", label: "$/M tokens", align: "right" },
  { key: "sources", label: "Sources", align: "right" },
];

// 8 columns total (incl. ZDR and EU Infra): name | provider | dims | context | price | sources | zdr | eu
const GRID =
  "minmax(130px, 1fr) 110px 70px 90px 92px 70px 50px 50px";

interface Props {
  models: EmbeddingModel[];
  totalCount: number;
}

export default function EmbeddingTable({ models, totalCount }: Props) {
  const [sort, setSort] = useState<SortKey>("price");
  const [dir, setDir] = useState<SortDir>("asc");
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    let list = models;
    if (q) {
      list = list.filter(
        (m) =>
          m.name.toLowerCase().includes(q) ||
          m.provider.toLowerCase().includes(q) ||
          m.model_id.toLowerCase().includes(q),
      );
    }

    list = list.slice().sort((a, b) => {
      const sign = dir === "asc" ? 1 : -1;
      switch (sort) {
        case "name":
          return a.name.localeCompare(b.name) * sign;
        case "provider":
          return a.provider.localeCompare(b.provider) * sign;
        case "dims":
          return (a.embedding_dimensions - b.embedding_dimensions) * sign;
        case "context":
          return (a.context_length - b.context_length) * sign;
        case "price":
          return (a.input_price_per_m - b.input_price_per_m) * sign;
        case "sources":
          return ((a.source_count ?? 1) - (b.source_count ?? 1)) * sign;
        default:
          return 0;
      }
    });

    return list;
  }, [models, sort, dir, query]);

  const sortBy = (key: SortKey) => {
    if (sort === key) {
      setDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSort(key);
      setDir("asc");
    }
  };

  return (
    <>
      {/* Search bar */}
      <section style={{ maxWidth: "1320px", margin: "0 auto", padding: "0 28px" }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "16px",
            flexWrap: "wrap",
            marginBottom: "16px",
          }}
        >
          <span style={{ fontSize: "13px", color: "#9a9a9a", fontVariantNumeric: "tabular-nums" }}>
            Showing {filtered.length} of {totalCount} embedding models
          </span>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              height: "30px",
              padding: "0 10px",
              border: "1px solid #262626",
              borderRadius: "4px",
              background: "#111112",
            }}
          >
            <span
              style={{
                fontFamily: "var(--font-jetbrains-mono), monospace",
                fontSize: "12px",
                color: "#6a6a6a",
              }}
            >
              /
            </span>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search embeddings..."
              style={{
                flex: 1,
                color: "#c9c9c9",
                fontFamily: "Inter, sans-serif",
                fontSize: "12.5px",
                background: "transparent",
                border: "none",
                outline: "none",
                width: "200px",
              }}
            />
          </div>
        </div>
      </section>

      {/* Table */}
      <section style={{ maxWidth: "1320px", margin: "0 auto", padding: "0 28px" }}>
        <div style={{ overflowX: "auto" }}>
          <div role="table" aria-label="AI embedding model prices" style={{ minWidth: "auto" }}>
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
                      cursor: "pointer",
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
                    {c.label + arrow}
                  </div>
                );
              })}
              <div
                role="columnheader"
                style={{
                  fontSize: "11px",
                  fontWeight: 500,
                  textTransform: "uppercase",
                  letterSpacing: "0.08em",
                  color: "#8a8a8a",
                  textAlign: "center",
                  whiteSpace: "nowrap",
                  padding: "0 8px",
                  height: "34px",
                  lineHeight: "34px",
                }}
              >
                ZDR
              </div>
              <div
                role="columnheader"
                style={{
                  fontSize: "11px",
                  fontWeight: 500,
                  textTransform: "uppercase",
                  letterSpacing: "0.08em",
                  color: "#8a8a8a",
                  textAlign: "center",
                  whiteSpace: "nowrap",
                  padding: "0 8px",
                  height: "34px",
                  lineHeight: "34px",
                }}
              >
                EU Infra
              </div>
            </div>

            {/* Rows */}
            {filtered.map((m) => {
              return (
                <div
                  key={m.model_id}
                  role="row"
                  style={{
                    display: "grid",
                    gridTemplateColumns: GRID,
                    alignItems: "center",
                    height: "56px",
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
                  {/* Model name with favicon */}
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
                          // eslint-disable-next-line @next/next/no-img-element
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
                      <span
                        style={{
                          fontSize: "13.5px",
                          color: "#f2f2f2",
                          whiteSpace: "nowrap",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                        }}
                      >
                        {m.name}
                      </span>
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

                  {/* Creator */}
                  <div role="cell" style={{ padding: "0 6px", minWidth: 0, display: "flex", alignItems: "center", gap: "4px" }}>
                    {m.creator_country && (
                      <span style={{ fontSize: "12px", lineHeight: 1, flexShrink: 0 }} title={COUNTRY_NAMES[m.creator_country] || m.creator_country}>
                        {COUNTRY_FLAG_EMOJI[m.creator_country] || ""}
                      </span>
                    )}
                    <span
                      style={{
                        fontFamily: "Inter, sans-serif",
                        fontSize: "12.5px",
                        color: "#8a8a8a",
                        display: "inline-block",
                        maxWidth: "100%",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {m.provider}
                    </span>
                  </div>

                  {/* Dims */}
                  <div
                    role="cell"
                    style={{
                      fontSize: "13px",
                      fontWeight: 500,
                      color: "#c9c9c9",
                      padding: "0 10px",
                      textAlign: "right",
                      fontVariantNumeric: "tabular-nums",
                      fontFamily: "var(--font-jetbrains-mono), monospace",
                    }}
                  >
                    {m.embedding_dimensions.toLocaleString()}
                  </div>

                  {/* Max Context */}
                  <div
                    role="cell"
                    style={{
                      fontSize: "13px",
                      fontWeight: 500,
                      color: "#c9c9c9",
                      padding: "0 10px",
                      textAlign: "right",
                      fontVariantNumeric: "tabular-nums",
                      fontFamily: "var(--font-jetbrains-mono), monospace",
                    }}
                  >
                    {m.context_length.toLocaleString()}
                  </div>

                  {/* $/M tokens */}
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

                  {/* Sources */}
                  <div
                    role="cell"
                    title={`${m.source_count ?? 1} provider${(m.source_count ?? 1) > 1 ? "s" : ""} offer this model`}
                    style={{
                      fontSize: "13px",
                      fontWeight: 500,
                      color: (m.source_count ?? 1) > 1 ? "#c9c9c9" : "#5f5f5f",
                      padding: "0 10px",
                      textAlign: "right",
                      fontVariantNumeric: "tabular-nums",
                    }}
                  >
                    {m.source_count ?? 1}
                  </div>

                  {/* ZDR */}
                  <div role="cell" style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <span
                      title={m.is_zdr ? "Zero Data Retention: provider guarantees no training on inputs or logging" : "No ZDR guarantee"}
                      style={{
                        fontSize: "12px",
                        fontWeight: 600,
                        color: m.is_zdr ? "#22c55e" : "#3a3a3a",
                      }}
                    >
                      {m.is_zdr ? "✓" : "—"}
                    </span>
                  </div>

                  {/* EU Infra */}
                  <div role="cell" style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <span
                      title={m.is_eu_sovereign ? "EU-domiciled: provider is not subject to US CLOUD Act" : "Not EU-sovereign"}
                      style={{
                        fontSize: "12px",
                        fontWeight: 600,
                        color: m.is_eu_sovereign ? "#5b8def" : "#3a3a3a",
                      }}
                    >
                      {m.is_eu_sovereign ? "✓" : "—"}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Footer note */}
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
              {filtered.length} of {totalCount} embedding models shown
            </span>
          </div>
          <Link
            href="/model-type"
            style={{
              fontFamily: "Inter, sans-serif",
              fontSize: "13px",
              color: "#C4A038",
              textDecoration: "none",
            }}
          >
            ← Back to Model Types
          </Link>
        </div>
      </section>
    </>
  );
}
