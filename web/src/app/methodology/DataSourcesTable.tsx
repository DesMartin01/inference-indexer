"use client";

import { useEffect, useState } from "react";
import { getProviders, ProviderSummary } from "@/lib/api";
import type React from "react";

// Aggregator sources we pull price feeds from (price data aggregated from
// multiple upstream providers). Everything else in the index is a direct
// provider feed. This set is small and stable; the provider list itself is
// fetched live so newly-added providers appear automatically.
const AGGREGATOR_SOURCES = new Set([
  "OpenRouter",
  "Together",
  "Fireworks",
  "Groq",
]);

// Frequency reflects our update cadence per source type. We deliberately do
// not use the word "scrape" here - direct feeds are refreshed on a schedule.
function freqFor(name: string): string {
  return AGGREGATOR_SOURCES.has(name) ? "Hourly" : "Daily";
}

function typeFor(name: string): string {
  return AGGREGATOR_SOURCES.has(name) ? "Aggregator" : "Direct";
}

const tableStyle: React.CSSProperties = {
  width: "100%",
  borderCollapse: "collapse",
  fontSize: 13,
  marginBottom: 16,
};
const thStyle: React.CSSProperties = {
  textAlign: "left",
  padding: "8px 12px",
  borderBottom: "1px solid #2a2a2a",
  color: "#8a8a8a",
  fontSize: 11,
  textTransform: "uppercase",
  letterSpacing: "0.08em",
  fontWeight: 500,
};
const tdStyle: React.CSSProperties = {
  padding: "8px 12px",
  borderBottom: "1px solid #1a1a1a",
  color: "#e5e5e5",
  verticalAlign: "top",
};
const gold = "#C4A038";

export default function DataSourcesTable() {
  const [providers, setProviders] = useState<ProviderSummary[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    getProviders()
      .then((d) => {
        if (alive) setProviders(d.providers);
      })
      .catch((e) => {
        if (alive) setErr(String(e?.message || e));
      });
    return () => {
      alive = false;
    };
  }, []);

  if (err) {
    return (
      <p style={{ fontSize: 13, color: "#ef4444", marginBottom: 16 }}>
        Could not load provider list. {err}
      </p>
    );
  }
  if (!providers) {
    return (
      <p style={{ fontSize: 13, color: "#8a8a8a", marginBottom: 16 }}>
        Loading data sources…
      </p>
    );
  }

  // Aggregators first (the feed backbone), then direct providers alphabetically.
  const sorted = [...providers].sort((a, b) => {
    const aa = AGGREGATOR_SOURCES.has(a.name) ? 0 : 1;
    const bb = AGGREGATOR_SOURCES.has(b.name) ? 0 : 1;
    if (aa !== bb) return aa - bb;
    return a.name.localeCompare(b.name);
  });

  return (
    <table style={tableStyle}>
      <thead>
        <tr>
          <th style={thStyle}>Source</th>
          <th style={thStyle}>Type</th>
          <th style={thStyle}>Models</th>
          <th style={thStyle}>Frequency</th>
        </tr>
      </thead>
      <tbody>
        {sorted.map((p) => (
          <tr key={p.name}>
            <td style={tdStyle}>{p.name}</td>
            <td style={{ ...tdStyle, color: typeFor(p.name) === "Aggregator" ? gold : "#e5e5e5" }}>
              {typeFor(p.name)}
            </td>
            <td style={tdStyle}>{p.model_count}</td>
            <td style={tdStyle}>{freqFor(p.name)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}