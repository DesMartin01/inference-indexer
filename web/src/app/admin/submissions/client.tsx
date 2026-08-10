"use client";

import { useCallback, useEffect, useState } from "react";
import {
  getSubmissions,
  reviewSubmission,
  PendingSubmission,
} from "@/lib/admin-api";

const STATUS_COLOR: Record<string, string> = {
  pending: "var(--accent)",
  approved: "var(--green)",
  rejected: "var(--red)",
};

export function SubmissionsClient() {
  const [subs, setSubs] = useState<PendingSubmission[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const d = await getSubmissions();
      setSubs(d.submissions);
      setErr(null);
    } catch (e) {
      setErr((e as Error).message);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const decide = async (id: number, status: "approved" | "rejected") => {
    await reviewSubmission(id, { status });
    await load();
  };

  if (err) {
    return (
      <div
        style={{
          padding: 16,
          background: "rgba(239,68,68,0.1)",
          border: "1px solid var(--red)",
          borderRadius: 8,
          color: "var(--red)",
          fontSize: 13,
        }}
      >
        {err}
      </div>
    );
  }

  if (subs === null) return <p style={{ color: "var(--text-muted)" }}>Loading…</p>;

  if (subs.length === 0) {
    return (
      <div
        style={{
          padding: 32,
          background: "var(--bg-card)",
          border: "1px solid var(--border-card)",
          borderRadius: 12,
          textAlign: "center",
          color: "var(--text-muted)",
          fontSize: 14,
        }}
      >
        No provider submissions yet.
      </div>
    );
  }

  return (
    <div style={{ display: "grid", gap: 16 }}>
      {subs.map((s) => (
        <div
          key={s.id}
          style={{
            background: "var(--bg-card)",
            border: "1px solid var(--border-card)",
            borderRadius: 12,
            padding: 20,
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              marginBottom: 12,
            }}
          >
            <div>
              <span style={{ fontWeight: 600, fontSize: 16, color: "var(--text-heading)" }}>
                {s.provider_name}
              </span>
              <span
                style={{
                  marginLeft: 12,
                  fontSize: 11,
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                  color: STATUS_COLOR[s.status] || "var(--text-muted)",
                  border: `1px solid ${STATUS_COLOR[s.status] || "var(--border-card)"}`,
                  padding: "2px 8px",
                  borderRadius: 4,
                }}
              >
                {s.status}
              </span>
            </div>
            <span style={{ color: "var(--text-muted)", fontSize: 12 }}>
              {new Date(s.created_at).toLocaleString()}
            </span>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "6px 24px",
              fontSize: 13,
              color: "var(--text-secondary)",
              fontFamily: "var(--font-jetbrains-mono)",
              marginBottom: 8,
            }}
          >
            <div>
              API:{" "}
              <a
                href={s.api_base_url}
                target="_blank"
                rel="noopener noreferrer"
                style={{ color: "var(--accent)", textDecoration: "none" }}
              >
                {s.api_base_url}
              </a>
            </div>
            {s.website && <div>Site: {s.website}</div>}
            <div>Country: {s.country || "—"}</div>
            <div>Contact: {s.contact_email || "—"}</div>
            <div>EU: {s.is_eu_sovereign ? "Yes" : "No"}</div>
            <div>ZDR: {s.is_zdr ? "Yes" : "No"}</div>
          </div>

          {s.notes && (
            <p
              style={{
                fontSize: 13,
                color: "var(--text-body)",
                fontStyle: "italic",
                margin: "8px 0 12px",
              }}
            >
              {s.notes}
            </p>
          )}

          {s.status === "pending" && (
            <div style={{ display: "flex", gap: 10, marginTop: 12 }}>
              <button
                onClick={() => decide(s.id, "approved")}
                style={{
                  padding: "8px 18px",
                  background: "var(--green)",
                  color: "#fff",
                  border: "none",
                  borderRadius: 8,
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                Approve
              </button>
              <button
                onClick={() => decide(s.id, "rejected")}
                style={{
                  padding: "8px 18px",
                  background: "var(--bg)",
                  color: "var(--red)",
                  border: "1px solid var(--red)",
                  borderRadius: 8,
                  fontSize: 13,
                  cursor: "pointer",
                }}
              >
                Reject
              </button>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}