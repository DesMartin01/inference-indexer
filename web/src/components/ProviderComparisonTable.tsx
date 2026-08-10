"use client";

import { useMemo, useState } from "react";
import Link from "next/link";

const GREEN = "#22c55e";
const RED = "#ef4444";
const FLAT = "#7a7a7a";

type SortKey = "provider" | "input" | "output" | "blended";

interface Endpoint {
  provider: string;
  input_price_per_m: number;
  output_price_per_m: number;
  blended_price_per_m: number;
}

function money(n: number) {
  return "$" + n.toFixed(2);
}

function sortValue(ep: Endpoint, key: SortKey): string | number {
  switch (key) {
    case "provider":
      return ep.provider.toLowerCase();
    case "input":
      return ep.input_price_per_m;
    case "output":
      return ep.output_price_per_m;
    case "blended":
      return ep.blended_price_per_m;
  }
}

export function ProviderComparisonTable({
  endpoints,
  referenceBlended,
  count,
}: {
  endpoints: Endpoint[];
  referenceBlended: number;
  count: number;
}) {
  // Default: blended price ascending (cheapest first)
  const [sortKey, setSortKey] = useState<SortKey>("blended");
  const [asc, setAsc] = useState(true);

  const sorted = useMemo(() => {
    const copy = [...endpoints];
    copy.sort((a, b) => {
      const va = sortValue(a, sortKey);
      const vb = sortValue(b, sortKey);
      const cmp =
        typeof va === "string" && typeof vb === "string"
          ? va.localeCompare(vb)
          : ((va as number) - (vb as number));
      return asc ? cmp : -cmp;
    });
    return copy;
  }, [endpoints, sortKey, asc]);

  const toggle = (key: SortKey) => {
    if (key === sortKey) {
      setAsc((a) => !a); // same column: flip direction
    } else {
      setSortKey(key); // new column: default asc (cheapest/lowest first)
      setAsc(true);
    }
  };

  const arrow = (key: SortKey) =>
    key === sortKey ? (asc ? " \u2191" : " \u2193") : "";

  const TH: React.CSSProperties = {
    textAlign: "right",
    padding: "8px 12px",
    fontSize: 11,
    textTransform: "uppercase",
    letterSpacing: "0.08em",
    color: "#8a8a8a",
    fontWeight: 500,
    cursor: "pointer",
    userSelect: "none",
    whiteSpace: "nowrap",
  };

  return (
    <div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 16,
        }}
      >
        <div style={{ fontSize: 14, fontWeight: 500, color: "#e5e5e5" }}>
          Provider Comparison
        </div>
        <div style={{ fontSize: 12, color: "#6a6a6a" }}>
          {count} providers · click a column to sort
        </div>
      </div>
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ borderBottom: "1px solid #2a2a2a" }}>
              <th
                onClick={() => toggle("provider")}
                style={{ ...TH, textAlign: "left" }}
              >
                Provider{arrow("provider")}
              </th>
              <th onClick={() => toggle("input")} style={TH}>
                Input $/M{arrow("input")}
              </th>
              <th onClick={() => toggle("output")} style={TH}>
                Output $/M{arrow("output")}
              </th>
              <th onClick={() => toggle("blended")} style={TH}>
                Blended $/M{arrow("blended")}
              </th>
              <th style={{ ...TH, cursor: "default" }}>vs Median</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((ep, i) => {
              const diff = ep.blended_price_per_m - referenceBlended;
              const diffPct =
                referenceBlended > 0
                  ? (diff / referenceBlended) * 100
                  : 0;
              const isCheapest = i === 0 && sortKey === "blended" && asc;
              return (
                <tr key={i} style={{ borderBottom: "1px solid #1c1c20" }}>
                  <td
                    style={{
                      padding: "9px 12px",
                      color: isCheapest ? "#e5e5e5" : "#c9c9c9",
                      fontWeight: isCheapest ? 600 : 400,
                    }}
                  >
                    {isCheapest && (
                      <span style={{ color: GREEN, marginRight: 6 }}>{"\u2193"}</span>
                    )}
                    <Link
                      href={`/providers/${encodeURIComponent(ep.provider)}`}
                      style={{
                        color: isCheapest ? "#e5e5e5" : "#c9c9c9",
                        textDecoration: "none",
                      }}
                    >
                      {ep.provider}
                    </Link>
                  </td>
                  <td
                    style={{
                      padding: "9px 12px",
                      textAlign: "right",
                      color: "#c9c9c9",
                      fontVariantNumeric: "tabular-nums",
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 12,
                    }}
                  >
                    {money(ep.input_price_per_m)}
                  </td>
                  <td
                    style={{
                      padding: "9px 12px",
                      textAlign: "right",
                      color: "#c9c9c9",
                      fontVariantNumeric: "tabular-nums",
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 12,
                    }}
                  >
                    {money(ep.output_price_per_m)}
                  </td>
                  <td
                    style={{
                      padding: "9px 12px",
                      textAlign: "right",
                      color: isCheapest ? GREEN : "#c9c9c9",
                      fontWeight: isCheapest ? 600 : 400,
                      fontVariantNumeric: "tabular-nums",
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 12,
                    }}
                  >
                    {money(ep.blended_price_per_m)}
                  </td>
                  <td
                    style={{
                      padding: "9px 12px",
                      textAlign: "right",
                      fontSize: 12,
                      color: diff < 0 ? GREEN : diff > 0 ? RED : FLAT,
                      fontVariantNumeric: "tabular-nums",
                    }}
                  >
                    {diff === 0
                      ? "median"
                      : `${diff > 0 ? "+" : ""}${diffPct.toFixed(1)}%`}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div style={{ marginTop: 12, fontSize: 11, color: "#5f5f5f" }}>
        Blended price = 40% input + 60% output. Median price shown in header is
        the reference price for this model.
      </div>
    </div>
  );
}