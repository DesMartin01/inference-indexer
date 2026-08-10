"use client";

import { useState, useCallback, useEffect } from "react";
import { getPriceCompare, PriceCompare } from "@/lib/admin-api";

type SortKey = "abs_diff" | "direct" | "openrouter" | "model" | "provider" | "pct_diff";

const SORT_OPTIONS: { key: SortKey; label: string }[] = [
  { key: "abs_diff", label: "|% Diff|" },
  { key: "pct_diff", label: "% Diff" },
  { key: "direct", label: "Direct price" },
  { key: "openrouter", label: "OpenRouter price" },
  { key: "model", label: "Model" },
  { key: "provider", label: "Provider" },
];

export function PriceCompareClient({
  initial,
  error,
}: {
  initial: PriceCompare | null;
  error: string | null;
}) {
  const [sort, setSort] = useState<SortKey>("abs_diff");
  const [order, setOrder] = useState<"asc" | "desc">("desc");
  const [minDiff, setMinDiff] = useState(0);
  const [data, setData] = useState<PriceCompare | null>(initial);
  const [err, setErr] = useState<string | null>(error || null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(
    async (s: SortKey, o: "asc" | "desc", m: number) => {
      setLoading(true);
      try {
        const d = await getPriceCompare(s, o, m);
        setData(d);
        setErr(null);
      } catch (e) {
        setErr((e as Error).message);
      } finally {
        setLoading(false);
      }
    },
    []
  );

  useEffect(() => {
    load(sort, order, minDiff);
  }, []); // run once on mount

  const applyFilter = useCallback(() => {
    load(sort, order, minDiff);
  }, [load, sort, order, minDiff]);

  return (
    <div>
      <div style={{ marginBottom: 20 }}>
        <h1 style={{ fontSize: 24, color: "var(--text-heading)", margin: 0 }}>
          OpenRouter vs Direct Price
        </h1>
        <p style={{ color: "var(--text-secondary)", fontSize: 13, marginTop: 4 }}>
          Compares what OpenRouter reports for a provider against our direct
          price for the same model+provider. A large diff is usually a price
          to spot-check, not necessarily an error: our Direct price is the
          provider&apos;s official list price, while OpenRouter often carries a
          negotiated/promotional rate. Both are kept as-is.
        </p>
      </div>

      {/* Controls */}
      <div
        style={{
          display: "flex",
          gap: 12,
          alignItems: "center",
          flexWrap: "wrap",
          padding: 16,
          background: "var(--bg-card)",
          border: "1px solid var(--border-card)",
          borderRadius: 12,
          marginBottom: 20,
        }}
      >
        <SortPicker value={sort} onChange={setSort} />
        <OrderToggle order={order} onChange={setOrder} />
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <label style={{ color: "var(--text-secondary)", fontSize: 12 }}>
            Min % diff
          </label>
          <input
            type="number"
            value={minDiff}
            min={0}
            max={1000}
            onChange={(e) => setMinDiff(Number(e.target.value))}
            style={{
              width: 70,
              padding: "6px 8px",
              background: "var(--bg)",
              border: "1px solid var(--border-card)",
              borderRadius: 6,
              color: "var(--text-heading)",
              fontSize: 13,
            }}
          />
        </div>
        <button
          onClick={applyFilter}
          style={{
            padding: "8px 16px",
            background: "var(--accent)",
            color: "var(--bg)",
            border: "none",
            borderRadius: 8,
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          {loading ? "Loading..." : "Apply"}
        </button>
      </div>

      {err && (
        <div
          style={{
            padding: 14,
            background: "rgba(239,68,68,0.1)",
            border: "1px solid var(--red)",
            borderRadius: 8,
            color: "var(--red)",
            marginBottom: 20,
            fontSize: 13,
          }}
        >
          {err}
        </div>
      )}

      {data && (
        <div
          style={{
            background: "var(--bg-card)",
            border: "1px solid var(--border-card)",
            borderRadius: 12,
            overflowX: "auto",
          }}
        >
          <div
            style={{
              padding: "10px 16px",
              borderBottom: "1px solid var(--border-card)",
              color: "var(--text-muted)",
              fontSize: 12,
            }}
          >
            {data.count} model/provider pairs
          </div>
          <table
            style={{
              width: "100%",
              borderCollapse: "collapse",
              fontSize: 13,
              minWidth: 720,
            }}
          >
            <thead>
              <tr
                style={{
                  textAlign: "left",
                  color: "var(--text-secondary)",
                  borderBottom: "1px solid var(--border-card)",
                }}
              >
                <th style={{ padding: "12px 16px" }}>Model</th>
                <th style={{ padding: "12px 16px" }}>Provider</th>
                <th style={{ padding: "12px 16px", textAlign: "right" }}>
                  Direct
                </th>
                <th style={{ padding: "12px 16px", textAlign: "right" }}>
                  OpenRouter
                </th>
                <th style={{ padding: "12px 16px", textAlign: "right" }}>
                  Diff
                </th>
              </tr>
            </thead>
            <tbody>
              {data.pairs.map((p) => {
                const diffColor =
                  Math.abs(p.pct_diff) >= 50
                    ? "var(--red)"
                    : Math.abs(p.pct_diff) >= 10
                    ? "var(--accent)"
                    : "var(--green)";
                return (
                  <tr
                    key={`${p.model_id}-${p.endpoint_provider}`}
                    style={{ borderBottom: "1px solid var(--border-row)" }}
                  >
                    <td
                      style={{
                        padding: "10px 16px",
                        fontFamily: "var(--font-jetbrains-mono)",
                        fontSize: 12,
                        color: "var(--text-heading)",
                        maxWidth: 260,
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {p.model_id}
                    </td>
                    <td style={{ padding: "10px 16px" }}>{p.endpoint_provider}</td>
                    <td style={{ padding: "10px 16px", textAlign: "right" }}>
                      ${p.direct_blended.toFixed(4)}
                    </td>
                    <td style={{ padding: "10px 16px", textAlign: "right" }}>
                      ${p.openrouter_blended.toFixed(4)}
                    </td>
                    <td
                      style={{
                        padding: "10px 16px",
                        textAlign: "right",
                        fontWeight: 600,
                        color: diffColor,
                      }}
                    >
                      {p.pct_diff > 0 ? "+" : ""}
                      {p.pct_diff.toFixed(1)}%
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function SortPicker({
  value,
  onChange,
}: {
  value: SortKey;
  onChange: (k: SortKey) => void;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value as SortKey)}
      style={{
        padding: "8px 10px",
        background: "var(--bg)",
        border: "1px solid var(--border-card)",
        borderRadius: 8,
        color: "var(--text-heading)",
        fontSize: 13,
      }}
    >
      {SORT_OPTIONS.map((o) => (
        <option key={o.key} value={o.key}>
          Sort by {o.label}
        </option>
      ))}
    </select>
  );
}

function OrderToggle({
  order,
  onChange,
}: {
  order: "asc" | "desc";
  onChange: (o: "asc" | "desc") => void;
}) {
  return (
    <div style={{ display: "flex", border: "1px solid var(--border-card)", borderRadius: 8, overflow: "hidden" }}>
      <button
        onClick={() => onChange("asc")}
        style={{
          padding: "8px 14px",
          background: order === "asc" ? "var(--border-card)" : "var(--bg)",
          color: "var(--text-body)",
          border: "none",
          cursor: "pointer",
          fontSize: 12,
        }}
      >
        ↑ Asc
      </button>
      <button
        onClick={() => onChange("desc")}
        style={{
          padding: "8px 14px",
          background: order === "desc" ? "var(--border-card)" : "var(--bg)",
          color: "var(--text-body)",
          border: "none",
          cursor: "pointer",
          fontSize: 12,
        }}
      >
        ↓ Desc
      </button>
    </div>
  );
}