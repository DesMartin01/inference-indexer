"use client";

import { useEffect, useState, useCallback } from "react";
import { getFeedStatus, FeedStatus } from "@/lib/admin-api";

const STATUS_COLOR: Record<string, string> = {
  ok: "var(--green)",
  stale: "var(--red)",
  no_prices: "var(--red)",
  never_fetched: "var(--red)",
};

const HEALTH_COLOR: Record<string, string> = {
  healthy: "var(--green)",
  degraded: "var(--accent)",
  critical: "var(--red)",
};

export function FeedClient({
  initial,
  error,
}: {
  initial: FeedStatus | null;
  error: string | null;
}) {
  const [data, setData] = useState<FeedStatus | null>(initial);
  const [err, setErr] = useState<string | null>(error || null);
  const [lastRefreshed, setLastRefreshed] = useState(new Date());

  const load = useCallback(async () => {
    try {
      const d = await getFeedStatus();
      setData(d);
      setErr(null);
      setLastRefreshed(new Date());
    } catch (e) {
      setErr((e as Error).message);
    }
  }, []);

  // Auto-refresh every 60s so the dashboard stays current during a session.
  useEffect(() => {
    const t = setInterval(load, 60_000);
    return () => clearInterval(t);
  }, [load]);

  return (
    <div>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 20,
        }}
      >
        <div>
          <h1 style={{ fontSize: 24, color: "var(--text-heading)", margin: 0 }}>
            Feed Status
          </h1>
          <p style={{ color: "var(--text-secondary)", fontSize: 13, marginTop: 4 }}>
            Refreshed {lastRefreshed.toLocaleTimeString()} · auto-refreshes
            every 60s
          </p>
        </div>
        <button
          onClick={load}
          style={{
            padding: "8px 16px",
            background: "var(--bg-card)",
            border: "1px solid var(--border-card)",
            borderRadius: 8,
            color: "var(--text-body)",
            cursor: "pointer",
          }}
        >
          Refresh now
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
        <>
          {/* Health banner */}
          <div
            style={{
              display: "flex",
              gap: 24,
              padding: 20,
              background: "var(--bg-card)",
              border: "1px solid var(--border-card)",
              borderRadius: 12,
              marginBottom: 24,
              flexWrap: "wrap",
            }}
          >
            <Stat
              label="Health"
              value={data.health}
              color={HEALTH_COLOR[data.health] || "var(--text-body)"}
            />
            <Stat label="Sources" value={String(data.source_count)} />
            <Stat
              label="Models indexed"
              value={String(data.total_models_indexed)}
            />
            <Stat
              label="Problems"
              value={String(data.problem_count)}
              color={data.problem_count > 0 ? "var(--red)" : "var(--green)"}
            />
          </div>

          {/* Source table */}
          <div
            style={{
              background: "var(--bg-card)",
              border: "1px solid var(--border-card)",
              borderRadius: 12,
              overflow: "hidden",
            }}
          >
            <table
              style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}
            >
              <thead>
                <tr
                  style={{
                    textAlign: "left",
                    color: "var(--text-secondary)",
                    borderBottom: "1px solid var(--border-card)",
                  }}
                >
                  <th style={{ padding: "12px 16px" }}>Source</th>
                  <th style={{ padding: "12px 16px" }}>Status</th>
                  <th style={{ padding: "12px 16px", textAlign: "right" }}>
                    Models
                  </th>
                  <th style={{ padding: "12px 16px", textAlign: "right" }}>
                    Priced
                  </th>
                  <th style={{ padding: "12px 16px", textAlign: "right" }}>
                    Age (min)
                  </th>
                  <th style={{ padding: "12px 16px" }}>Cadence</th>
                </tr>
              </thead>
              <tbody>
                {data.sources.map((s) => (
                  <tr
                    key={s.source}
                    style={{ borderBottom: "1px solid var(--border-row)" }}
                  >
                    <td
                      style={{
                        padding: "12px 16px",
                        fontFamily: "var(--font-jetbrains-mono)",
                        fontSize: 12,
                        color: "var(--text-heading)",
                      }}
                    >
                      {s.source}
                    </td>
                    <td style={{ padding: "12px 16px" }}>
                      <span
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          gap: 6,
                          color: STATUS_COLOR[s.status] || "var(--text-body)",
                          textTransform: "capitalize",
                        }}
                      >
                        <span
                          style={{
                            width: 8,
                            height: 8,
                            borderRadius: "50%",
                            background:
                              STATUS_COLOR[s.status] || "var(--text-muted)",
                            display: "inline-block",
                          }}
                        />
                        {s.status}
                      </span>
                    </td>
                    <td style={{ padding: "12px 16px", textAlign: "right" }}>
                      {s.model_count}
                    </td>
                    <td style={{ padding: "12px 16px", textAlign: "right" }}>
                      {s.priced_count}
                    </td>
                    <td
                      style={{
                        padding: "12px 16px",
                        textAlign: "right",
                        color: s.stale ? "var(--red)" : "var(--text-body)",
                        fontWeight: s.age_minutes && s.age_minutes > 100 ? 600 : 400,
                      }}
                    >
                      {s.age_minutes != null ? s.age_minutes.toFixed(0) : "—"}
                    </td>
                    <td style={{ padding: "12px 16px" }}>{s.cadence}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <p style={{ color: "var(--text-muted)", fontSize: 12, marginTop: 14 }}>
            Hourly sources should be fresh ({"<"}85 min). Daily sources refresh
            once a day at 3 am. OpenRouter endpoints are daily-cadence, so a
            larger age there is expected.
          </p>
        </>
      )}
    </div>
  );
}

function Stat({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color?: string;
}) {
  return (
    <div>
      <div
        style={{
          fontSize: 26,
          fontWeight: 600,
          color: color || "var(--text-heading)",
          lineHeight: 1,
          textTransform: "capitalize",
        }}
      >
        {value}
      </div>
      <div style={{ color: "var(--text-muted)", fontSize: 12, marginTop: 4 }}>
        {label}
      </div>
    </div>
  );
}