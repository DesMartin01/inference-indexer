"use client";

import { useEffect, useState, useCallback } from "react";
import { getApiUsage, ApiUsage } from "@/lib/admin-api";

const ACCENT = "#C4A038";
const GREEN = "#22c55e";
const MUTED = "#5f5f5f";
const BORDER = "#2a2a2a";

export function ApiUsageClient({
  initial,
  error,
}: {
  initial: ApiUsage | null;
  error: string | null;
}) {
  const [data, setData] = useState<ApiUsage | null>(initial);
  const [err, setErr] = useState<string | null>(error || null);
  const [lastRefreshed, setLastRefreshed] = useState(new Date());

  const load = useCallback(async () => {
    try {
      const d = await getApiUsage();
      setData(d);
      setErr(null);
      setLastRefreshed(new Date());
    } catch (e) {
      setErr((e as Error).message);
    }
  }, []);

  useEffect(() => {
    const id = setInterval(load, 60000); // refresh every 60s
    return () => clearInterval(id);
  }, [load]);

  const today = data?.today;
  const maxRequests = Math.max(
    1,
    ...(data?.daily.map((p) => p.requests) || [1])
  );
  const maxHourly = Math.max(1, ...(data?.hourly.map((p) => p.requests) || [1]));

  const card: React.CSSProperties = {
    background: "#16161a",
    border: `1px solid ${BORDER}`,
    borderRadius: 8,
    padding: "20px 24px",
    marginBottom: 20,
  };

  return (
    <div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 20,
        }}
      >
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 600, color: "#f2f2f2", margin: 0 }}>
            API Usage
          </h1>
          <div style={{ fontSize: 12, color: MUTED, marginTop: 4 }}>
            External people/agent traffic (excludes frontend SSR). Future pro-API
            revenue signal.
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontSize: 12, color: MUTED }}>
            Refreshed {lastRefreshed.toLocaleTimeString()}
          </span>
          <button
            onClick={load}
            style={{
              background: "transparent",
              border: `1px solid ${BORDER}`,
              color: "#e5e5e5",
              padding: "6px 14px",
              borderRadius: 6,
              fontSize: 13,
              cursor: "pointer",
            }}
          >
            Refresh
          </button>
        </div>
      </div>

      {err && (
        <div
          style={{
            padding: "14px 18px",
            background: "rgba(239,68,68,0.08)",
            border: "1px solid rgba(239,68,68,0.4)",
            borderRadius: 8,
            color: "#ef4444",
            fontSize: 13,
            marginBottom: 20,
          }}
        >
          {err}
        </div>
      )}

      {/* Headline metrics */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: 16,
          marginBottom: 20,
        }}
      >
        <MetricCard
          label="Registered-Key Requests Today"
          value={today ? String(today.requests) : "—"}
        />
        <MetricCard
          label="Unique API-Key Users"
          value={today ? String(today.unique_users) : "—"}
          accent
        />
        <MetricCard
          label="Free-Key Requests"
          value={today ? `${today.free_requests} (${today.free_users} users)` : "—"}
        />
        <MetricCard
          label="Anonymous (public, no key)"
          value={today ? String(today.public_requests) : "—"}
        />
      </div>

      {/* Daily trend */}
      <div style={card}>
        <div style={{ fontSize: 14, fontWeight: 600, color: "#e5e5e5", marginBottom: 16 }}>
          Requests · last 14 days
        </div>
        {data && data.daily.length > 0 ? (
          <div style={{ display: "flex", alignItems: "flex-end", gap: 8, height: 140 }}>
            {data.daily.map((p) => (
              <div
                key={p.date}
                style={{
                  flex: 1,
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: 6,
                }}
              >
                <div
                  style={{
                    width: "100%",
                    background: ACCENT,
                    borderRadius: 3,
                    minHeight: 2,
                    height: `${Math.round((p.requests / maxRequests) * 100)}%`,
                  }}
                  title={`${p.date}: ${p.requests} requests`}
                />
                <span style={{ fontSize: 10, color: MUTED }}>
                  {p.date.slice(5)}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ color: MUTED, fontSize: 13, padding: "20px 0" }}>
            No external usage recorded yet. Data appears once the API is called.
          </div>
        )}
      </div>

      {/* Row: plan mix + top endpoints */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 2fr",
          gap: 20,
        }}
      >
        <div style={card}>
          <div style={{ fontSize: 14, fontWeight: 600, color: "#e5e5e5", marginBottom: 16 }}>
            Plan Mix · 30 days
          </div>
          {data && data.plan_mix.length > 0 ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {data.plan_mix.map((p) => (
                <div key={p.plan}>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      fontSize: 13,
                      color: "#c9c9c9",
                      marginBottom: 4,
                    }}
                  >
                    <span>{p.plan}</span>
                    <span>
                      {p.requests.toLocaleString()}
                      {typeof p.users === "number" && p.users > 0 && (
                        <span style={{ color: MUTED, fontSize: 11 }}> · {p.users} users</span>
                      )}
                    </span>
                  </div>
                  <div style={{ height: 6, background: "#1a1a1a", borderRadius: 3 }}>
                    <div
                      style={{
                        width: `${Math.min(
                          100,
                          Math.round(
                            (p.requests /
                              Math.max(1, ...data.plan_mix.map((x) => x.requests))) *
                              100
                          )
                        )}%`,
                        height: "100%",
                        background: ACCENT,
                        borderRadius: 3,
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ color: MUTED, fontSize: 13 }}>No data yet.</div>
          )}
        </div>

        <div style={card}>
          <div style={{ fontSize: 14, fontWeight: 600, color: "#e5e5e5", marginBottom: 16 }}>
            Top Endpoints · 7 days
          </div>
          {data && data.top_endpoints.length > 0 ? (
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <tbody>
                {data.top_endpoints.map((e, i) => (
                  <tr key={i} style={{ borderBottom: "1px solid #1c1c20" }}>
                    <td
                      style={{
                        padding: "9px 8px",
                        fontFamily: "'JetBrains Mono', monospace",
                        fontSize: 12,
                        color: "#c9c9c9",
                      }}
                    >
                      {e.endpoint}
                    </td>
                    <td
                      style={{
                        padding: "9px 8px",
                        textAlign: "right",
                        fontFamily: "'JetBrains Mono', monospace",
                        fontSize: 12,
                        color: "#e5e5e5",
                        fontVariantNumeric: "tabular-nums",
                      }}
                    >
                      {e.requests}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div style={{ color: MUTED, fontSize: 13 }}>No data yet.</div>
          )}
        </div>
      </div>

      {/* Hourly today */}
      <div style={card}>
        <div style={{ fontSize: 14, fontWeight: 600, color: "#e5e5e5", marginBottom: 16 }}>
          Requests by hour · today
        </div>
        {data && data.hourly.length > 0 ? (
          <div style={{ display: "flex", alignItems: "flex-end", gap: 8, height: 120 }}>
            {data.hourly.map((p) => (
              <div
                key={p.hour}
                style={{
                  flex: 1,
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: 6,
                }}
              >
                <div
                  style={{
                    width: "100%",
                    background: GREEN,
                    borderRadius: 3,
                    minHeight: 2,
                    height: `${Math.round((p.requests / maxHourly) * 100)}%`,
                  }}
                  title={`${p.hour}: ${p.requests} requests`}
                />
              </div>
            ))}
          </div>
        ) : (
          <div style={{ color: MUTED, fontSize: 13, padding: "20px 0" }}>
            No hourly data yet.
          </div>
        )}
        <div style={{ marginTop: 10, fontSize: 11, color: MUTED }}>
          Unique users = distinct registered/anonymous API keys seen today ·
          public no-key calls count toward requests but aren&apos;t individually
          attributable.
        </div>
      </div>

      {/* Free key traction: signups + activity */}
      <div style={card}>
        <div style={{ fontSize: 14, fontWeight: 600, color: "#e5e5e5", marginBottom: 4 }}>
          Free-Key Users · traction
        </div>
        <div style={{ fontSize: 12, color: MUTED, marginBottom: 16 }}>
          New free signups (30d): <strong style={{ color: ACCENT }}>{data ? data.new_free_signups_30d : "—"}</strong>
        </div>
        {data && data.free_key_activity.length > 0 ? (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ textAlign: "left" }}>
                <th style={{ padding: "6px 8px", fontSize: 11, textTransform: "uppercase", color: MUTED, letterSpacing: "0.06em" }}>User</th>
                <th style={{ padding: "6px 8px", fontSize: 11, textTransform: "uppercase", color: MUTED, letterSpacing: "0.06em" }}>Endpoint</th>
                <th style={{ padding: "6px 8px", fontSize: 11, textTransform: "uppercase", color: MUTED, letterSpacing: "0.06em", textAlign: "right" }}>Req</th>
                <th style={{ padding: "6px 8px", fontSize: 11, textTransform: "uppercase", color: MUTED, letterSpacing: "0.06em", textAlign: "right" }}>Last</th>
              </tr>
            </thead>
            <tbody>
              {data.free_key_activity.map((a, i) => (
                <tr key={i} style={{ borderBottom: "1px solid #1c1c20" }}>
                  <td style={{ padding: "8px", fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "#c9c9c9" }}>{a.user}</td>
                  <td style={{ padding: "8px", fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: "#e5e5e5" }}>{a.endpoint}</td>
                  <td style={{ padding: "8px", textAlign: "right", fontVariantNumeric: "tabular-nums", color: "#e5e5e5" }}>{a.requests}</td>
                  <td style={{ padding: "8px", textAlign: "right", fontSize: 11, color: MUTED }}>
                    {a.last ? new Date(a.last).toISOString().replace("T", " ").slice(0, 16) + "Z" : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div style={{ color: MUTED, fontSize: 13 }}>
            No free-key API usage yet. This is where a real user (agent or
            developer) shows up once they sign up and call the API with their
            key.
          </div>
        )}
      </div>
    </div>
  );
}

function MetricCard({
  label,
  value,
  accent = false,
}: {
  label: string;
  value: string;
  accent?: boolean;
}) {
  return (
    <div
      style={{
        background: "#16161a",
        border: `1px solid ${BORDER}`,
        borderRadius: 8,
        padding: "18px 20px",
      }}
    >
      <div
        style={{
          fontSize: 11,
          textTransform: "uppercase",
          letterSpacing: "0.08em",
          color: MUTED,
          marginBottom: 8,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 30,
          fontWeight: 600,
          color: accent ? ACCENT : "#e5e5e5",
        }}
      >
        {value}
      </div>
    </div>
  );
}