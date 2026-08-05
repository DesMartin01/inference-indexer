import Link from "next/link";

export const metadata = {
  title: "API Documentation - Free Inference Pricing API | InferenceIndexer.ai",
  description:
    "Free API for AI inference pricing data. Access SIT-Composite index, model pricing, price history, and SIT scores for 316+ models. 100 requests/day free, no credit card required.",
  alternates: { canonical: "https://inferenceindexer.ai/api-docs" },
  openGraph: {
    title: "InferenceIndexer API - Free AI Pricing Data",
    description: "Access live inference pricing for 316+ models via free API. SIT scores, price history, tier rankings.",
    url: "https://inferenceindexer.ai/api-docs",
    siteName: "InferenceIndexer.ai",
  },
  keywords: [
    "inference pricing API",
    "AI model pricing API",
    "LLM cost API",
    "free API for AI pricing",
    "SIT API",
    "inference price data",
  ],
};

export default function ApiDocsPage() {
  return (
    <div style={{ background: "#0a0a0a", minHeight: "100vh" }}>
      <header style={{ position: "sticky", top: 0, zIndex: 20, background: "#0a0a0a", borderBottom: "1px solid #222" }}>
        <div style={{ maxWidth: 1320, margin: "0 auto", padding: "0 28px", height: 56, display: "flex", alignItems: "center", gap: 28 }}>
          <Link href="/" style={{ fontSize: 15, fontWeight: 600, color: "#f2f2f2", textDecoration: "none" }}>InferenceIndexer<span style={{ color: "#C4A038" }}>.ai</span></Link>
          <div style={{ flex: 1 }} />
          <nav style={{ display: "flex", alignItems: "center", gap: 22 }}>
            <Link href="/api-docs" style={{ fontSize: 12.5, color: "#C4A038", textDecoration: "none" }}>API</Link>
            <Link href="/methodology" style={{ fontSize: 12.5, color: "#8a8a8a", textDecoration: "none" }}>Methodology</Link>
            <Link href="/about" style={{ fontSize: 12.5, color: "#8a8a8a", textDecoration: "none" }}>About</Link>
          </nav>
        </div>
      </header>
      <div style={{ maxWidth: 900, margin: "0 auto", padding: "40px 28px" }}>
        <h1 style={{ fontSize: 32, fontWeight: 600, color: "#f2f2f2", marginBottom: 8 }}>API Documentation</h1>
        <p style={{ fontSize: 14, color: "#8a8a8a", marginBottom: 32 }}>Independent price index for AI inference. Get live pricing data for 316+ models across 57 providers.</p>

        <Section title="Authentication">
          <p style={pStyle}>API keys are free. Sign up with your email to get a key.</p>
          <CodeBlock>{`# Sign up for a free API key
curl -X POST "https://api.inferenceindexer.ai/v1/auth/signup?email=you@example.com"

# Use the key in all requests
curl -H "Authorization: Bearer ii_sk_yourkey" \\
     https://api.inferenceindexer.ai/v1/sit/composite/latest`}</CodeBlock>
        </Section>

        <Section title="Rate Limits">
          <table style={tableStyle}>
            <thead><tr><th style={thStyle}>Plan</th><th style={thStyle}>Daily</th><th style={thStyle}>Per Minute</th><th style={thStyle}>History Access</th></tr></thead>
            <tbody>
              <tr><td style={tdStyle}>Public (no key)</td><td style={tdStyle}>100</td><td style={tdStyle}>10</td><td style={tdStyle}>7 days</td></tr>
              <tr><td style={tdStyle}>Free</td><td style={tdStyle}>1,000</td><td style={tdStyle}>30</td><td style={tdStyle}>30 days</td></tr>
              <tr><td style={tdStyle}>Paid</td><td style={tdStyle}>50,000</td><td style={tdStyle}>100</td><td style={tdStyle}>365 days</td></tr>
            </tbody>
          </table>
        </Section>

        <Section title="Endpoints">
          <Endpoint method="GET" path="/v1/sit/composite/latest" desc="Current SIT-Composite index value with tier breakdown" />
          <Endpoint method="GET" path="/v1/sit/composite/history" desc="Historical SIT values. Params: days (1-365), tier (optional)" />
          <Endpoint method="GET" path="/v1/models" desc="List all models with current pricing. Params: tier, provider, sort, limit" />
          <Endpoint method="GET" path="/v1/models/{model_id}" desc="Single model detail with SIT score, tier rank, comparisons" />
          <Endpoint method="GET" path="/v1/models/{model_id}/history" desc="Historical price data for a model. Params: days (1-365)" />
        </Section>

        <Section title="Example: Get SIT-Composite">
          <CodeBlock>{`curl https://api.inferenceindexer.ai/v1/sit/composite/latest

# Response
{
  "date": "2026-08-04",
  "composite": {
    "price_per_m": 7.06,
    "models": 316,
    "providers": 57
  },
  "tiers": {
    "frontier": { "price_per_m": 38.61, "models": 44 },
    "standard": { "price_per_m": 3.33, "models": 129 },
    "budget": { "price_per_m": 0.89, "models": 104 },
    "micro": { "price_per_m": 0.25, "models": 39 }
  },
  "spread": { "price_per_m": 37.72 }
}`}</CodeBlock>
        </Section>

        <Section title="Example: List Models by SIT Score">
          <CodeBlock>{`curl "https://api.inferenceindexer.ai/v1/models?sort=sit_score&limit=5"

# Response (truncated)
{
  "count": 316,
  "returned": 5,
  "models": [
    {
      "model_id": "openai/gpt-5.6-luna",
      "name": "OpenAI: GPT-5.6 Luna",
      "tier": "frontier",
      "blended_price_per_m": 0.40,
      "sit_score": 0.01
    }
  ]
}`}</CodeBlock>
        </Section>

        <Section title="Errors">
          <table style={tableStyle}>
            <thead><tr><th style={thStyle}>Code</th><th style={thStyle}>Meaning</th></tr></thead>
            <tbody>
              <tr><td style={tdStyle}>200</td><td style={tdStyle}>Success</td></tr>
              <tr><td style={tdStyle}>404</td><td style={tdStyle}>Model or endpoint not found</td></tr>
              <tr><td style={tdStyle}>429</td><td style={tdStyle}>Rate limit exceeded</td></tr>
              <tr><td style={tdStyle}>500</td><td style={tdStyle}>Server error</td></tr>
            </tbody>
          </table>
        </Section>

        <div style={{ marginTop: 40, padding: "16px 20px", background: "#16161a", border: "1px solid #2a2a2a", borderRadius: 8 }}>
          <Link href="/#signup" style={{ fontSize: 14, color: "#C4A038" }}>Sign up for a free API key →</Link>
        </div>
      </div>
    </div>
  );
}

const pStyle: React.CSSProperties = { fontSize: 14, color: "#8a8a8a", lineHeight: 1.6, marginBottom: 12 };
const tableStyle: React.CSSProperties = { width: "100%", borderCollapse: "collapse", fontSize: 13 };
const thStyle: React.CSSProperties = { textAlign: "left", padding: "8px 12px", borderBottom: "1px solid #2a2a2a", color: "#8a8a8a", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.08em" };
const tdStyle: React.CSSProperties = { padding: "8px 12px", borderBottom: "1px solid #1a1a1a", color: "#e5e5e5" };

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 32 }}>
      <h2 style={{ fontSize: 18, fontWeight: 600, color: "#f2f2f2", marginBottom: 12 }}>{title}</h2>
      {children}
    </div>
  );
}

function CodeBlock({ children }: { children: string }) {
  return (
    <pre style={{ background: "#0d0d0d", border: "1px solid #2a2a2a", borderRadius: 4, padding: "14px 18px", fontFamily: "'JetBrains Mono', monospace", fontSize: 12.5, color: "#c9c9c9", overflowX: "auto", lineHeight: 1.5 }}>
      {children}
    </pre>
  );
}

function Endpoint({ method, path, desc }: { method: string; path: string; desc: string }) {
  return (
    <div style={{ display: "flex", gap: 12, padding: "10px 0", borderBottom: "1px solid #1a1a1a", alignItems: "baseline" }}>
      <span style={{ fontSize: 11, fontWeight: 600, padding: "2px 8px", borderRadius: 3, background: "#1a3a1a", color: "#22c55e", fontFamily: "'JetBrains Mono', monospace" }}>{method}</span>
      <code style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 13, color: "#C4A038" }}>{path}</code>
      <span style={{ fontSize: 13, color: "#7a7a7a", flex: 1 }}>{desc}</span>
    </div>
  );
}
