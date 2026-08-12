"use client";

import { useEffect, useState } from "react";
import type React from "react";

interface SourceStatus {
  source: string;
  cadence: string;
  model_count: number;
  priced_count: number;
  endpoint_count: number;
  last_fetch: string | null;
  age_minutes: number | null;
  status: string;
  stale: boolean;
}

interface HealthSummary {
  total_models_tracked: number;
  total_sources: number;
  price_snapshots_7d: {
    total: number;
    direct: number;
    aggregator: number;
    blended: number;
  };
}

interface HealthResponse {
  generated_at: string;
  health: string;
  source_count: number;
  total_models_indexed: number;
  anomaly_count_24h: number;
  summary: HealthSummary;
  sources: SourceStatus[];
  problem_count: number;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function sourceDisplayName(source: string): string {
  const names: Record<string, string> = {
    openrouter: "OpenRouter",
    venice_direct: "Venice",
    deepinfra_direct: "DeepInfra",
    novita_direct: "Novita",
    sambanova_direct: "SambaNova",
    jina_direct: "Jina",
    together_direct: "Together",
    groq_direct: "Groq",
    fireworks_direct: "Fireworks",
    siliconflow_direct: "SiliconFlow",
    tensorx_direct: "TensorX",
    engy_direct: "Engy",
    openrelay_direct: "OpenRelay",
    sarvam_direct: "Sarvam",
  };
  return names[source] || source;
}

function sourceType(source: string): "Direct" | "Aggregator" {
  return source === "openrouter" ? "Aggregator" : "Direct";
}

function statusColor(status: string): string {
  switch (status) {
    case "ok": return "#4ade80";
    case "stale": return "#fbbf24";
    case "no_prices": return "#f87171";
    case "never_fetched": return "#6b7280";
    default: return "#6b7280";
  }
}

function formatAge(minutes: number | null): string {
  if (minutes === null) return "never";
  if (minutes < 60) return `${Math.round(minutes)}m ago`;
  if (minutes < 1440) return `${Math.round(minutes / 60)}h ago`;
  return `${Math.round(minutes / 1440)}d ago`;
}

export default function DataQualityClient() {
  const [data, setData] = useState<HealthResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    async function fetchHealth() {
      try {
        const resp = await fetch(`${API_BASE}/v1/health/sources`);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const json = await resp.json();
        if (alive) { setData(json); setErr(null); }
      } catch (e: any) {
        if (alive) setErr(e?.message || String(e));
      } finally {
        if (alive) setLoading(false);
      }
    }
    fetchHealth();
    const interval = setInterval(fetchHealth, 60000);
    return () => { alive = false; clearInterval(interval); };
  }, []);

  if (loading) {
    return <p style={{ fontSize: 14, color: "#8a8a8a" }}>Loading data sources...</p>;
  }
  if (err) {
    return <p style={{ fontSize: 14, color: "#f87171" }}>Failed to load data quality: {err}</p>;
  }
  if (!data) return null;

  const { summary, sources } = data;
  const snaps = summary.price_snapshots_7d;

  return (
    <>
      {/* Summary cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: "16px", marginBottom: "40px" }}>
        <StatCard label="Overall Health" value={data.health.toUpperCase()} color={data.health === "healthy" ? "#4ade80" : data.health === "degraded" ? "#fbbf24" : "#f87171"} />
        <StatCard label="Models Tracked" value={String(summary.total_models_tracked)} />
        <StatCard label="Data Sources" value={String(summary.total_sources)} />
        <StatCard label="Direct Snapshots (7d)" value={String(snaps.direct)} />
        <StatCard label="Aggregator Snapshots (7d)" value={String(snaps.aggregator)} />
        <StatCard label="Blended Snapshots (7d)" value={String(snaps.blended)} />
        <StatCard label="Anomalies (24h)" value={String(data.anomaly_count_24h)} color={data.anomaly_count_24h > 0 ? "#fbbf24" : "#4ade80"} />
      </div>

      {/* Source table */}
      <h2 style={{ fontSize: "18px", fontWeight: 600, color: "#e5e5e5", marginBottom: "16px" }}>
        Per-Source Status
      </h2>
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr>
              <th style={th}>Source</th>
              <th style={th}>Type</th>
              <th style={th}>Cadence</th>
              <th style={th}>Models</th>
              <th style={th}>Priced</th>
              <th style={th}>Endpoints</th>
              <th style={th}>Last Fetch</th>
              <th style={th}>Age</th>
              <th style={th}>Status</th>
            </tr>
          </thead>
          <tbody>
            {sources.sort((a, b) => a.source.localeCompare(b.source)).map((s) => (
              <tr key={s.source}>
                <td style={td}>{sourceDisplayName(s.source)}</td>
                <td style={{ ...td, color: sourceType(s.source) === "Direct" ? "#e5e5e5" : "#C4A038" }}>
                  {sourceType(s.source)}
                </td>
                <td style={td}>{s.cadence}</td>
                <td style={td}>{s.model_count}</td>
                <td style={td}>{s.priced_count}</td>
                <td style={td}>{s.endpoint_count}</td>
                <td style={{ ...td, fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "#8a8a8a" }}>
                  {s.last_fetch ? new Date(s.last_fetch).toISOString().slice(0, 19).replace("T", " ") + " UTC" : "never"}
                </td>
                <td style={td}>{formatAge(s.age_minutes)}</td>
                <td style={{ ...td, color: statusColor(s.status) }}>
                  {s.status}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p style={{ fontSize: 12, color: "#5f5f5f", marginTop: "24px", lineHeight: 1.5 }}>
        Data is fetched from {sources.length} sources: {snaps.direct} direct provider API snapshots and {snaps.aggregator} aggregator snapshots in the last 7 days.
        {data.anomaly_count_24h > 0
          ? ` ${data.anomaly_count_24h} price anomal${data.anomaly_count_24h !== 1 ? "ies were" : "y was"} detected in the last 24 hours.`
          : " No anomalies detected in the last 24 hours."}
        {" "}Raw data is available via the{" "}
        <a href="/api-docs#export" style={{ color: "#C4A038", textDecoration: "none" }}>export endpoint</a>.
      </p>
    </>
  );
}

const th: React.CSSProperties = {
  textAlign: "left",
  padding: "8px 12px",
  borderBottom: "1px solid #2a2a2a",
  color: "#8a8a8a",
  fontSize: 11,
  textTransform: "uppercase",
  letterSpacing: "0.08em",
  fontWeight: 500,
};

const td: React.CSSProperties = {
  padding: "8px 12px",
  borderBottom: "1px solid #1a1a1a",
  color: "#e5e5e5",
  verticalAlign: "top",
};

function StatCard({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div style={{
      background: "#141414",
      border: "1px solid #1e1e1e",
      borderRadius: 8,
      padding: "16px 20px",
    }}>
      <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.08em", color: "#6a6a6a", marginBottom: "6px" }}>
        {label}
      </div>
      <div style={{ fontSize: "24px", fontWeight: 700, color: color || "#e5e5e5" }}>
        {value}
      </div>
    </div>
  );
}
