"use client";

import { useState, useMemo } from "react";
import Link from "next/link";

const ACCENT = "#C4A038";
const GREEN = "#22c55e";

const TIER_COLOR: Record<string, string> = {
  frontier: ACCENT,
  standard: "#5b8def",
  budget: GREEN,
  micro: "#7a7a7a",
};

type SortKey = "name" | "model_owner" | "tier" | "hosting_type" | "quantization" | "input_price_per_m" | "output_price_per_m" | "blended_price_per_m" | "sit_adjusted_price" | "sit_score";
type SortDir = "asc" | "desc";

interface ProviderModel {
  model_id: string;
  name: string;
  model_owner: string;
  tier: string;
  context_length: number | null;
  aa_index_score: number | null;
  modality: string | null;
  is_reasoning: boolean;
  input_price_per_m: number;
  output_price_per_m: number;
  blended_price_per_m: number;
  sit_score: number | null;
  sit_adjusted_price: number | null;
  fetched_at: string;
  source: string;
  hosting_type: string;
  quantization: string;
  is_zdr: boolean;
  is_eu_sovereign: boolean;
}

function formatPrice(n: number): string {
  if (n === 0) return "$0";
  if (n < 0.01) return "$" + n.toFixed(4);
  if (n < 1) return "$" + n.toFixed(3);
  return "$" + n.toFixed(2);
}

function capitalizeTier(t: string): string {
  return t.charAt(0).toUpperCase() + t.slice(1);
}

const COLUMNS: { key: SortKey; label: string; align: "left" | "right" }[] = [
  { key: "name", label: "Model", align: "left" },
  { key: "model_owner", label: "Owner", align: "left" },
  { key: "tier", label: "Tier", align: "left" },
  { key: "hosting_type", label: "Host", align: "left" },
  { key: "quantization", label: "Quant", align: "left" },
  { key: "input_price_per_m", label: "Input $/M", align: "right" },
  { key: "output_price_per_m", label: "Output $/M", align: "right" },
  { key: "blended_price_per_m", label: "Blended $/M", align: "right" },
  { key: "sit_adjusted_price", label: "Cost / IQ", align: "right" },
  { key: "sit_score", label: "SIT Score", align: "right" },
];

export default function ProviderModelTable({ models, providerName }: { models: ProviderModel[]; providerName: string }) {
  const [sortKey, setSortKey] = useState<SortKey>("blended_price_per_m");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  const sorted = useMemo(() => {
    const sortedModels = [...models];
    sortedModels.sort((a, b) => {
      let av: string | number | null = a[sortKey];
      let bv: string | number | null = b[sortKey];

      // Handle nulls: treat as lowest for asc, highest for desc
      if (av == null && bv == null) return 0;
      if (av == null) return sortDir === "asc" ? 1 : -1;
      if (bv == null) return sortDir === "asc" ? -1 : 1;

      if (typeof av === "string" && typeof bv === "string") {
        return sortDir === "asc" ? av.localeCompare(bv) : bv.localeCompare(av);
      }
      av = av as number;
      bv = bv as number;
      return sortDir === "asc" ? av - bv : bv - av;
    });
    return sortedModels;
  }, [models, sortKey, sortDir]);

  function handleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  }

  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13, minWidth: 900 }}>
        <thead>
          <tr>
            {COLUMNS.map((col) => (
              <th
                key={col.key}
                onClick={() => handleSort(col.key)}
                style={{
                  textAlign: col.align,
                  padding: "8px 12px",
                  borderBottom: "1px solid #2a2a2a",
                  color: sortKey === col.key ? ACCENT : "#8a8a8a",
                  fontSize: 11,
                  textTransform: "uppercase",
                  letterSpacing: "0.08em",
                  cursor: "pointer",
                  userSelect: "none",
                  whiteSpace: "nowrap",
                  transition: "color 0.15s",
                }}
              >
                {col.label}
                {sortKey === col.key && (
                  <span style={{ marginLeft: 4, fontSize: 10 }}>
                    {sortDir === "asc" ? "\u25B2" : "\u25BC"}
                  </span>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((m) => {
            const tColor = TIER_COLOR[m.tier] || "#7a7a7a";
            const isOwn = m.model_owner === providerName;
            return (
              <tr key={m.model_id} style={{ borderBottom: "1px solid #171717" }}>
                <td style={{ padding: "10px 12px" }}>
                  <Link href={`/models/${m.model_id}`} style={{ color: "#f2f2f2", textDecoration: "none", fontSize: 13.5 }}>
                    {m.name}
                  </Link>
                  {m.is_reasoning && (
                    <span style={{ marginLeft: 8, fontSize: 10, color: "#5f5f5f", border: "1px solid #333", borderRadius: 3, padding: "1px 5px" }}>REASONING</span>
                  )}
                </td>
                <td style={{ padding: "10px 12px" }}>
                  {isOwn ? (
                    <span style={{ fontSize: 12, color: "#5f5f5f" }}>{providerName}</span>
                  ) : (
                    <Link href={`/providers/${encodeURIComponent(m.model_owner)}`} style={{ fontSize: 12, color: "#8a8a8a", textDecoration: "none" }}>
                      {m.model_owner}
                    </Link>
                  )}
                </td>
                <td style={{ padding: "10px 12px" }}>
                  <span style={{ display: "inline-block", fontSize: 11, textTransform: "uppercase", padding: "2px 7px", borderRadius: 3, border: `1px solid ${tColor}`, color: tColor }}>
                    {capitalizeTier(m.tier)}
                  </span>
                </td>
                <td style={{ padding: "10px 12px" }}>
                  {m.hosting_type === "self-hosted" ? (
                    <span style={{ display: "inline-block", fontSize: 10, textTransform: "uppercase", letterSpacing: "0.04em", padding: "2px 6px", borderRadius: 3, border: "1px solid #5b8def55", color: "#5b8def", whiteSpace: "nowrap" }}>Self</span>
                  ) : m.hosting_type === "proxied" ? (
                    <span style={{ display: "inline-block", fontSize: 10, textTransform: "uppercase", letterSpacing: "0.04em", padding: "2px 6px", borderRadius: 3, border: "1px solid #C4A03855", color: ACCENT, whiteSpace: "nowrap" }}>Proxy</span>
                  ) : (
                    <span style={{ color: "#3a3a3a" }}>-</span>
                  )}
                </td>
                <td style={{ padding: "10px 12px" }}>
                  {m.quantization && m.quantization !== "not-available" ? (
                    <span style={{ fontSize: 11, color: "#8a8a8a", fontFamily: "var(--font-jetbrains-mono), monospace" }}>{m.quantization}</span>
                  ) : (
                    <span style={{ color: "#3a3a3a" }}>-</span>
                  )}
                </td>
                <td style={{ padding: "10px 12px", textAlign: "right", color: "#c9c9c9", fontVariantNumeric: "tabular-nums" }}>{formatPrice(m.input_price_per_m)}</td>
                <td style={{ padding: "10px 12px", textAlign: "right", color: "#c9c9c9", fontVariantNumeric: "tabular-nums" }}>{formatPrice(m.output_price_per_m)}</td>
                <td style={{ padding: "10px 12px", textAlign: "right", color: "#c9c9c9", fontVariantNumeric: "tabular-nums", fontWeight: 500 }}>{formatPrice(m.blended_price_per_m)}</td>
                <td style={{ padding: "10px 12px", textAlign: "right", color: m.sit_adjusted_price != null ? "#7ec47e" : "#5f5f5f", fontVariantNumeric: "tabular-nums" }}>
                  {m.sit_adjusted_price != null ? formatPrice(m.sit_adjusted_price) : "N/A"}
                </td>
                <td style={{ padding: "10px 12px", textAlign: "right", color: m.sit_score != null ? tColor : "#5f5f5f", fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>
                  {m.sit_score != null ? m.sit_score : "N/A"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
