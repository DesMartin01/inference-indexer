"use client";

import { useMemo, useState } from "react";

// Copy-paste snippet builder for the /embed widget.
export default function EmbedSnippetBuilder() {
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const [preset, setPreset] = useState<string>("");

  const snippet = useMemo(() => {
    const params = new URLSearchParams();
    if (theme === "light") params.set("theme", "light");
    if (preset) params.set("default", preset);
    const qs = params.toString();
    const src = `https://www.inferenceindexer.ai/embed${qs ? `?${qs}` : ""}`;
    return `<!-- InferenceIndexer recommendation widget -->
<iframe src="${src}" width="100%" height="520" style="border:0;border-radius:8px" loading="lazy" title="InferenceIndexer AI inference recommendations"></iframe>
<p style="font-size:12px;color:#666">
  Powered by <a href="https://www.inferenceindexer.ai/?utm_source=embed" rel="noopener">InferenceIndexer</a>: AI inference recommendations on verified prices
</p>`;
  }, [theme, preset]);

  const previewSrc = useMemo(() => {
    const params = new URLSearchParams();
    if (theme === "light") params.set("theme", "light");
    if (preset) params.set("default", preset);
    const qs = params.toString();
    return `https://www.inferenceindexer.ai/embed${qs ? `?${qs}` : ""}`;
  }, [theme, preset]);

  return (
    <section style={{ maxWidth: "1320px", margin: "0 auto", padding: "8px 28px 8px" }}>
      <div style={{ display: "grid", gap: "24px", gridTemplateColumns: "minmax(280px, 380px) 1fr", alignItems: "start" }}>
        {/* Controls */}
        <div
          style={{
            border: "1px solid #222",
            borderRadius: "8px",
            padding: "22px",
            background: "#101013",
          }}
        >
          <h2 style={{ margin: "0 0 16px", fontSize: "14px", fontWeight: 600, color: "#f2f2f2" }}>
            1. Choose options
          </h2>

          <div style={{ marginBottom: "18px" }}>
            <div style={{ fontSize: "12px", color: "#8a8a8a", marginBottom: "8px" }}>Theme</div>
            <div style={{ display: "flex", gap: "8px" }}>
              {(["dark", "light"] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => setTheme(t)}
                  style={{
                    flex: 1,
                    padding: "9px 0",
                    fontSize: "13px",
                    fontWeight: 500,
                    borderRadius: "6px",
                    cursor: "pointer",
                    border: theme === t ? "1px solid #C4A038" : "1px solid #2a2a2a",
                    background: theme === t ? "rgba(196,160,56,0.08)" : "transparent",
                    color: theme === t ? "#C4A038" : "#8a8a8a",
                  }}
                >
                  {t === "dark" ? "Dark" : "Light"}
                </button>
              ))}
            </div>
          </div>

          <div style={{ marginBottom: "4px" }}>
            <div style={{ fontSize: "12px", color: "#8a8a8a", marginBottom: "8px" }}>
              Preloaded query (optional)
            </div>
            {[
              ["", "None (empty box)"],
              ["coding", "Best model for coding agents"],
              ["zdr-eu", "ZDR providers in the EU"],
            ].map(([val, label]) => (
              <label
                key={val || "none"}
                style={{ display: "flex", alignItems: "center", gap: "8px", padding: "6px 0", cursor: "pointer" }}
              >
                <input
                  type="radio"
                  name="preset"
                  checked={preset === val}
                  onChange={() => setPreset(val)}
                  style={{ accentColor: "#C4A038" }}
                />
                <span style={{ fontSize: "13px", color: "#c9c9c9" }}>{label}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Snippet + preview */}
        <div>
          <h2 style={{ margin: "0 0 12px", fontSize: "14px", fontWeight: 600, color: "#f2f2f2" }}>
            2. Copy this into your page
          </h2>
          <pre
            style={{
              margin: "0 0 10px",
              padding: "16px",
              background: "#0d0d10",
              border: "1px solid #222",
              borderRadius: "8px",
              fontSize: "12.5px",
              lineHeight: 1.6,
              color: "#c9c9c9",
              overflowX: "auto",
              whiteSpace: "pre-wrap",
              wordBreak: "break-all",
              fontFamily: "var(--font-jetbrains-mono), monospace",
            }}
          >
            {snippet}
          </pre>
          <CopyButton snippet={snippet} />

          <h2 style={{ margin: "28px 0 12px", fontSize: "14px", fontWeight: 600, color: "#f2f2f2" }}>
            3. Live preview
          </h2>
          <div style={{ border: "1px solid #222", borderRadius: "8px", overflow: "hidden" }}>
            <iframe
              src={previewSrc}
              width="100%"
              height="560"
              style={{ border: 0, background: theme === "light" ? "#fff" : "#0a0a0a" }}
              title="Widget preview"
            />
          </div>
        </div>
      </div>
    </section>
  );
}

function CopyButton({ snippet }: { snippet: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(snippet);
          setCopied(true);
          setTimeout(() => setCopied(false), 2000);
        } catch {
          // clipboard blocked: user can select the code block manually
        }
      }}
      style={{
        padding: "9px 22px",
        background: "#C4A038",
        color: "#0a0a0a",
        fontSize: "13px",
        fontWeight: 600,
        border: "none",
        borderRadius: "6px",
        cursor: "pointer",
      }}
    >
      {copied ? "Copied ✓" : "Copy code"}
    </button>
  );
}
