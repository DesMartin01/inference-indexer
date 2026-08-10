"use client";

import { useState } from "react";
import { submitProvider, ProviderSubmission, SubmissionResult } from "@/lib/api";

const FIELD_STYLE: React.CSSProperties = {
  width: "100%",
  padding: "10px 12px",
  background: "var(--bg)",
  border: "1px solid var(--border-card)",
  borderRadius: 8,
  color: "var(--text-body)",
  fontSize: 13.5,
  outline: "none",
  boxSizing: "border-box",
};

const LABEL_STYLE: React.CSSProperties = {
  display: "block",
  fontSize: 12,
  fontWeight: 600,
  color: "var(--text-secondary)",
  marginBottom: 6,
  textTransform: "uppercase",
  letterSpacing: "0.05em",
};

const HINT_STYLE: React.CSSProperties = {
  fontSize: 12,
  color: "var(--text-muted)",
  marginTop: 5,
};

export function SubmitClient() {
  const [form, setForm] = useState({
    provider_name: "",
    api_base_url: "",
    website: "",
    country: "",
    contact_email: "",
    notes: "",
  });
  const [flags, setFlags] = useState({ is_eu_sovereign: false, is_zdr: false });
  const [submitErr, setSubmitErr] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<SubmissionResult | null>(null);

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitErr(null);
    setSubmitting(true);
    try {
      const payload: ProviderSubmission = {
        ...form,
        is_eu_sovereign: flags.is_eu_sovereign,
        is_zdr: flags.is_zdr,
      };
      const r = await submitProvider(payload);
      setResult(r);
    } catch (err) {
      setSubmitErr((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      style={{
        background: "var(--bg-card)",
        border: "1px solid var(--border-card)",
        borderRadius: 12,
        padding: 28,
      }}
    >
      {result ? (
        <div>
          <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 14 }}>
            <span
              style={{
                width: 10,
                height: 10,
                borderRadius: "50%",
                background:
                  result.endpoint_probe?.ok ? "var(--green)" : "var(--accent)",
                display: "inline-block",
              }}
            />
            <h2 style={{ fontSize: 20, color: "var(--text-heading)", margin: 0 }}>
              Submission received
            </h2>
          </div>
          <p style={{ color: "var(--text-body)", fontSize: 14, lineHeight: 1.6 }}>
            {result.message}
          </p>
          {result.endpoint_probe && (
            <div
              style={{
                marginTop: 18,
                padding: 14,
                background: "var(--bg)",
                border: "1px solid var(--border-card)",
                borderRadius: 8,
                fontSize: 13,
                color: "var(--text-secondary)",
                fontFamily: "var(--font-jetbrains-mono)",
              }}
            >
              Probe: {result.endpoint_probe.detail}
            </div>
          )}
        </div>
      ) : (
        <form onSubmit={onSubmit}>
          <div style={{ display: "grid", gap: 20 }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18 }}>
              <div>
                <label style={LABEL_STYLE}>Provider name *</label>
                <input
                  style={FIELD_STYLE}
                  required
                  value={form.provider_name}
                  onChange={set("provider_name")}
                  placeholder="e.g. Engy"
                />
              </div>
              <div>
                <label style={LABEL_STYLE}>Country</label>
                <input
                  style={FIELD_STYLE}
                  value={form.country}
                  onChange={set("country")}
                  placeholder="e.g. Ireland"
                />
              </div>
            </div>

            <div>
              <label style={LABEL_STYLE}>API base URL *</label>
              <input
                style={FIELD_STYLE}
                required
                value={form.api_base_url}
                onChange={set("api_base_url")}
                placeholder="https://api.example.com"
              />
              <div style={HINT_STYLE}>
                Your OpenAI-compatible endpoint. We probe{" "}
                <code>{"{base}/v1/models"}</code> live to verify it and count models.
              </div>
            </div>

            <div>
              <label style={LABEL_STYLE}>Website</label>
              <input
                style={FIELD_STYLE}
                value={form.website}
                onChange={set("website")}
                placeholder="https://example.com"
              />
            </div>

            <div>
              <label style={LABEL_STYLE}>Contact email</label>
              <input
                style={FIELD_STYLE}
                type="email"
                value={form.contact_email}
                onChange={set("contact_email")}
                placeholder="For verification only, never shown publicly"
              />
            </div>

            <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
              <label
                style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13.5, cursor: "pointer" }}
              >
                <input
                  type="checkbox"
                  checked={flags.is_eu_sovereign}
                  onChange={(e) => setFlags((f) => ({ ...f, is_eu_sovereign: e.target.checked }))}
                />
                EU-sovereign infrastructure
              </label>
              <label
                style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13.5, cursor: "pointer" }}
              >
                <input
                  type="checkbox"
                  checked={flags.is_zdr}
                  onChange={(e) => setFlags((f) => ({ ...f, is_zdr: e.target.checked }))}
                />
                Zero-data-retention (ZDR) by default
              </label>
            </div>

            <div>
              <label style={LABEL_STYLE}>Notes (optional)</label>
              <textarea
                style={{ ...FIELD_STYLE, minHeight: 80, resize: "vertical" }}
                value={form.notes}
                onChange={set("notes")}
                placeholder="Anything about your pricing model, cache, or special features."
              />
            </div>

            {submitErr && (
              <div
                style={{
                  padding: 12,
                  background: "rgba(239,68,68,0.1)",
                  border: "1px solid var(--red)",
                  borderRadius: 8,
                  color: "var(--red)",
                  fontSize: 13,
                }}
              >
                {submitErr}
              </div>
            )}

            <button
              type="submit"
              disabled={submitting}
              style={{
                padding: "12px 20px",
                background: "var(--accent)",
                color: "#fff",
                border: "none",
                borderRadius: 8,
                fontSize: 14,
                fontWeight: 600,
                cursor: submitting ? "wait" : "pointer",
                opacity: submitting ? 0.6 : 1,
              }}
            >
              {submitting ? "Submitting…" : "Submit for review"}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}