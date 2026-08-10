"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import {
  providerFaviconUrl,
  providerInitials,
  type ProviderSummary,
} from "@/lib/api";

type ColKey =
  | "name"
  | "provider_type"
  | "model_count"
  | "avg_price"
  | "min_price"
  | "max_price"
  | "is_zdr"
  | "is_eu_sovereign";

type SortDir = "asc" | "desc";

function formatPrice(n: number | null): string {
  if (n == null) return "N/A";
  if (n < 0.01) return "$" + n.toFixed(4);
  if (n < 1) return "$" + n.toFixed(3);
  return "$" + n.toFixed(2);
}

// Column definitions: key -> label + alignment
const COLS: { key: ColKey; label: string; align: "left" | "right" | "center" }[] = [
  { key: "name", label: "Provider", align: "left" },
  { key: "provider_type", label: "Type", align: "left" },
  { key: "model_count", label: "Models", align: "right" },
  { key: "avg_price", label: "Avg $/M", align: "right" },
  { key: "min_price", label: "Min $/M", align: "right" },
  { key: "max_price", label: "Max $/M", align: "right" },
  { key: "is_zdr", label: "ZDR", align: "center" },
  { key: "is_eu_sovereign", label: "EU", align: "center" },
];

export default function ProvidersTable({ providers }: { providers: ProviderSummary[] }) {
  const [sort, setSort] = useState<ColKey>("model_count");
  const [dir, setDir] = useState<SortDir>("desc");

  const sorted = useMemo(() => {
    const sign = dir === "asc" ? 1 : -1;
    return providers.slice().sort((a, b) => {
      const k = sort;
      // Nullable numeric prices: nulls sort last regardless of direction
      if (k === "avg_price" || k === "min_price" || k === "max_price") {
        const av = a[k] as number | null;
        const bv = b[k] as number | null;
        if (av == null && bv == null) return 0;
        if (av == null) return 1;
        if (bv == null) return -1;
        return (av - bv) * sign;
      }
      if (k === "model_count") return (a.model_count - b.model_count) * sign;
      if (k === "is_zdr") return ((a.is_zdr ? 1 : 0) - (b.is_zdr ? 1 : 0)) * sign;
      if (k === "is_eu_sovereign")
        return ((a.is_eu_sovereign ? 1 : 0) - (b.is_eu_sovereign ? 1 : 0)) * sign;
      // name / provider_type: alphabetical
      return String(a[k]).localeCompare(String(b[k])) * sign;
    });
  }, [providers, sort, dir]);

  const sortBy = (key: ColKey) => {
    if (sort === key) {
      setDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSort(key);
      setDir("asc");
    }
  };

  const thStyle = (align: "left" | "right" | "center") => ({
    textAlign: align,
    padding: "10px 12px",
    borderBottom: "1px solid #2a2a2a",
    color: "#8a8a8a",
    fontSize: 11,
    textTransform: "uppercase" as const,
    letterSpacing: "0.08em",
    cursor: "pointer",
    userSelect: "none" as const,
    whiteSpace: "nowrap" as const,
  });

  const sortIndicator = (key: ColKey) => {
    if (sort !== key) return " ⇅";
    return dir === "asc" ? " ↑" : " ↓";
  };

  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13, minWidth: 700 }}>
        <thead>
          <tr>
            {COLS.map((c) => (
              <th
                key={c.key}
                onClick={() => sortBy(c.key)}
                title={`Sort by ${c.label}`}
                style={thStyle(c.align)}
              >
                {c.label}
                <span style={{ color: sort === c.key ? "#C4A038" : "#4a4a4a" }}>
                  {sortIndicator(c.key)}
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((p) => (
            <tr key={p.name} style={{ borderBottom: "1px solid #171717", transition: "background 90ms" }}>
              <td style={{ padding: "12px" }}>
                <Link
                  href={`/providers/${encodeURIComponent(p.name)}`}
                  style={{ display: "flex", alignItems: "center", gap: 10, color: "#f2f2f2", textDecoration: "none" }}
                >
                  <span
                    style={{
                      width: 24,
                      height: 24,
                      borderRadius: "50%",
                      background: "#16161a",
                      border: "1px solid #33333a",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      overflow: "hidden",
                      flexShrink: 0,
                    }}
                  >
                    {(() => {
                      const fav = providerFaviconUrl(p.name);
                      return fav ? (
                        <img src={fav} alt={p.name} width={14} height={14} style={{ width: 14, height: 14, objectFit: "contain" }} />
                      ) : (
                        <span style={{ fontFamily: "var(--font-jetbrains-mono), monospace", fontSize: 9, color: "#8f8f96" }}>
                          {providerInitials(p.name)}
                        </span>
                      );
                    })()}
                  </span>
                  <span style={{ fontSize: 13.5, fontWeight: 500 }}>{p.name}</span>
                </Link>
              </td>
              <td style={{ padding: "12px" }}>
                <span style={{
                  fontSize: 10,
                  textTransform: "uppercase",
                  letterSpacing: "0.04em",
                  padding: "2px 7px",
                  borderRadius: 3,
                  border: `1px solid ${p.provider_type === "aggregator" ? "#C4A038" : p.provider_type === "hybrid" ? "#a855f7" : "#5b8def"}`,
                  color: p.provider_type === "aggregator" ? "#C4A038" : p.provider_type === "hybrid" ? "#a855f7" : "#5b8def",
                }}>
                  {p.provider_type === "self-host" ? "Self-Host" : p.provider_type === "hybrid" ? "Hybrid" : "Aggregator"}
                </span>
              </td>
              <td style={{ padding: "12px", textAlign: "right", color: "#c9c9c9", fontVariantNumeric: "tabular-nums" }}>
                {p.model_count > 0 ? p.model_count : `${p.endpoint_count} endpoints`}
              </td>
              <td style={{ padding: "12px", textAlign: "right", color: "#c9c9c9", fontVariantNumeric: "tabular-nums" }}>{formatPrice(p.avg_price)}</td>
              <td style={{ padding: "12px", textAlign: "right", color: "#6a6a6a", fontVariantNumeric: "tabular-nums" }}>{formatPrice(p.min_price)}</td>
              <td style={{ padding: "12px", textAlign: "right", color: "#6a6a6a", fontVariantNumeric: "tabular-nums" }}>{formatPrice(p.max_price)}</td>
              <td style={{ padding: "12px", textAlign: "center" }}>
                {p.is_zdr ? <span style={{ color: "#22c55e", fontSize: 12 }}>Yes</span> : <span style={{ color: "#3a3a3a" }}>-</span>}
              </td>
              <td style={{ padding: "12px", textAlign: "center" }}>
                {p.is_eu_sovereign ? <span style={{ color: "#5b8def", fontSize: 12 }}>Yes</span> : <span style={{ color: "#3a3a3a" }}>-</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}