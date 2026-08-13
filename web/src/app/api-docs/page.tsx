import Link from "next/link";
import { Header } from "@/components/Header";
import { getModelCount } from "@/lib/api";
import { CURRENT_MODEL_COUNT } from "@/lib/counts";

export async function generateMetadata() {
  const count = (await getModelCount().catch(() => 0)) || CURRENT_MODEL_COUNT;
  return {
  title: "API Documentation - Free Inference Pricing API | InferenceIndexer.ai",
  description:
    `Free API for AI inference pricing data. Access SIT-Composite index, model pricing, price history, and SIT scores for ${count}+ models. 100 requests/day free, no credit card required.`,
  alternates: { canonical: "https://www.inferenceindexer.ai/api-docs" },
  openGraph: {
    title: "InferenceIndexer API - Free AI Pricing Data",
    description: `Access live inference pricing for ${count}+ models via free API. SIT scores, price history, tier rankings.`,
    url: "https://www.inferenceindexer.ai/api-docs",
    siteName: "InferenceIndexer.ai",
    images: [{ url: "/og-image.png", width: 1200, height: 630, alt: "InferenceIndexer.ai - API Documentation" }],
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
}

const MONO = "'JetBrains Mono', ui-monospace, monospace";
const SANS = "Inter, -apple-system, BlinkMacSystemFont, sans-serif";

export default function ApiDocsPage() {
  const apiSchema = {
    "@context": "https://schema.org",
    "@type": "WebAPI",
    name: "InferenceIndexer API",
    description:
      "Free API for AI inference pricing data. Live and historical prices by model, provider comparison, and the SIT-Composite index.",
    url: "https://www.inferenceindexer.ai/api-docs",
    termsOfService: "https://www.inferenceindexer.ai/terms",
    provider: {
      "@type": "Organization",
      name: "InferenceIndexer.ai",
      url: "https://www.inferenceindexer.ai/",
    },
    documentation:
      "https://www.inferenceindexer.ai/api-docs",
  };
  return (
    <div style={{ background: "#0a0a0a", minHeight: "100vh", fontFamily: SANS }}>
      <Header activePage="api" />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(apiSchema) }}
      />

      <div style={{ maxWidth: "1320px", margin: "0 auto", padding: "40px 28px 80px" }}>
        {/* Page title */}
        <div style={{ marginBottom: 40 }}>
          <h1 style={{ fontSize: 28, fontWeight: 700, color: "#ffffff", margin: "0 0 8px" }}>
            API Documentation
          </h1>
          <p style={{ fontSize: 14, color: "#8a8a8a", margin: "0 0 20px" }}>
            Free inference pricing data. 1,000 requests/day with a free API key.
          </p>
          <Link
            href="/#signup"
            style={{
              display: "inline-block",
              fontSize: 14,
              fontWeight: 600,
              color: "#0a0a0a",
              background: "#C4A038",
              padding: "8px 16px",
              borderRadius: 6,
              textDecoration: "none",
            }}
          >
            Get API Key
          </Link>
        </div>

        {/* Two-column layout */}
        <div style={{ display: "flex", gap: 0, alignItems: "flex-start" }}>
          <Sidebar />
          <main style={{ flex: 1, minWidth: 0, paddingLeft: 40 }}>
            <AuthSection />
            <EndpointsSection />
            <RateLimitsSection />
            <ResponseFormatSection />
            <ErrorsSection />
          </main>
        </div>
      </div>
    </div>
  );
}

/* ---------- Sidebar ---------- */

function Sidebar() {
  return (
    <aside
      style={{
        width: 240,
        flexShrink: 0,
        position: "sticky",
        top: 56,
        height: "calc(100vh - 56px)",
        overflowY: "auto",
        borderRight: "1px solid #1a1a1a",
        paddingRight: 16,
      }}
    >
      <SidebarSection title="Authentication">
        <SidebarLink href="#authentication">Getting a key</SidebarLink>
      </SidebarSection>

      <SidebarSection title="Endpoints">
        <SidebarLink href="#ep-sit-composite-latest">/sit/composite/latest</SidebarLink>
        <SidebarLink href="#ep-sit-composite-history">/sit/composite/history</SidebarLink>
        <SidebarLink href="#ep-models">/models</SidebarLink>
        <SidebarLink href="#ep-models-id">/models/{`{id}`}</SidebarLink>
        <SidebarLink href="#ep-models-id-history">/models/{`{id}`}/history</SidebarLink>
      </SidebarSection>

      <SidebarSection title="Reference">
        <SidebarLink href="#rate-limits">Rate Limits</SidebarLink>
        <SidebarLink href="#response-format">Response Format</SidebarLink>
        <SidebarLink href="#errors">Errors</SidebarLink>
      </SidebarSection>
    </aside>
  );
}

function SidebarSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 24 }}>
      <div
        style={{
          fontSize: 11,
          fontWeight: 600,
          textTransform: "uppercase",
          letterSpacing: "0.08em",
          color: "#666666",
          padding: "0 0 8px",
        }}
      >
        {title}
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>{children}</div>
    </div>
  );
}

function SidebarLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <a
      href={href}
      style={{
        display: "block",
        fontSize: 13,
        fontFamily: MONO,
        color: "#8a8a8a",
        textDecoration: "none",
        padding: "4px 0 4px 12px",
        borderLeft: "2px solid transparent",
        transition: "color 0.15s, border-color 0.15s",
      }}
    >
      {children}
    </a>
  );
}

/* ---------- Section wrapper ---------- */

function Section({ id, title, children }: { id: string; title: string; children: React.ReactNode }) {
  return (
    <section id={id} style={{ marginBottom: 56, scrollMarginTop: 72 }}>
      <h2
        style={{
          fontSize: 20,
          fontWeight: 600,
          color: "#f2f2f2",
          margin: "0 0 20px",
          paddingBottom: 10,
          borderBottom: "1px solid #1a1a1a",
        }}
      >
        {title}
      </h2>
      {children}
    </section>
  );
}

/* ---------- Authentication ---------- */

function AuthSection() {
  return (
    <Section id="authentication" title="Authentication">
      <p style={pStyle}>
        API keys are required for all requests. For agents, get one instantly with no email or account:
      </p>

      <CodeBlock>
        <span style={{ color: "#4ade80" }}>$</span>
        {" curl -X POST "}
        <span style={{ color: "#4ade80" }}>https://api.inferenceindexer.ai/v1/auth/anonymous</span>
      </CodeBlock>
      <p style={{ ...pStyle, marginBottom: 8 }}>
        Returns a key valid on the free tier (10,000 requests/day, 30 days of history).
      </p>
      <p style={{ ...pStyle, margin: "20px 0 8px" }}>Or sign up with an email (usage tracking + dashboard):</p>

      <ol style={{ listStyle: "none", padding: 0, margin: "0 0 24px", display: "flex", flexDirection: "column", gap: 12 }}>
        <Step n={1}>Click &quot;Get API Key&quot; or go to the Sign Up page</Step>
        <Step n={2}>Enter your email address</Step>
        <Step n={3}>Click the magic link in the email</Step>
        <Step n={4}>Your API key is displayed on the dashboard</Step>
      </ol>

      <p style={{ ...pStyle, marginBottom: 8 }}>Pass your API key in the Authorization header:</p>
      <CodeBlock>
        <span style={{ color: "#C4A038" }}>Authorization</span>
        <span style={{ color: "#8a8a8a" }}>: </span>
        <span style={{ color: "#4ade80" }}>Bearer YOUR_API_KEY</span>
        {"\n"}
      </CodeBlock>

      <p style={{ ...pStyle, marginTop: 20, marginBottom: 8 }}>Example:</p>
      <CodeBlock>
        <span style={{ color: "#4ade80" }}>$</span>
        {" curl -H "}
        <span style={{ color: "#4ade80" }}>{`"Authorization: Bearer YOUR_API_KEY"`}</span>
        {" \\\n     https://api.inferenceindexer.ai/v1/sit/composite/latest"}
      </CodeBlock>
    </Section>
  );
}

function Step({ n, children }: { n: number; children: React.ReactNode }) {
  return (
    <li style={{ display: "flex", alignItems: "center", gap: 12, fontSize: 14, color: "#e5e5e5" }}>
      <span
        style={{
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          width: 20,
          height: 20,
          borderRadius: "50%",
          background: "#C4A038",
          color: "#0a0a0a",
          fontSize: 11,
          fontWeight: 700,
          flexShrink: 0,
        }}
      >
        {n}
      </span>
      <span>{children}</span>
    </li>
  );
}

/* ---------- Endpoints ---------- */

function EndpointsSection() {
  return (
    <Section id="endpoints" title="Endpoints">
      <p style={pStyle}>Each endpoint is a card. All paths are prefixed with the API base URL.</p>

      <EndpointCard
        anchor="ep-sit-composite-latest"
        method="GET"
        path="/v1/sit/composite/latest"
        desc="Returns the current SIT-Composite index value, including tier breakdowns."
        params={[]}
        request={`$ curl -H "Authorization: Bearer YOUR_API_KEY" \\\n     https://api.inferenceindexer.ai/v1/sit/composite/latest`}
        response={`{
  "date": "2026-08-03",
  "composite": {
    "price_per_m": 2.84,
    "index_points": 784.5,
    "change_24h": -1.2,
    "change_7d": -3.1,
    "change_30d": -12.4
  },
  "tiers": {
    "frontier": { "price_per_m": 35.20, "change_24h": -0.8, "models": 8 },
    "standard": { "price_per_m": 1.25, "change_24h": -1.5, "models": 156 },
    "budget": { "price_per_m": 0.42, "change_24h": -2.1, "models": 78 }
  },
  "spread": { "price_per_m": 34.78, "change_24h": -1.9 }
}`}
      />

      <EndpointCard
        anchor="ep-sit-composite-history"
        method="GET"
        path="/v1/sit/composite/history?days=30"
        desc="Returns historical SIT-Composite values."
        params={[
          { name: "days", type: "integer", required: false, desc: "Number of days to return (default: 30, max: 365)" },
          { name: "tier", type: "string", required: false, desc: "Filter to a specific tier: frontier, standard, budget" },
        ]}
        request={`$ curl -H "Authorization: Bearer YOUR_API_KEY" \\\n     "https://api.inferenceindexer.ai/v1/sit/composite/history?days=30"`}
        response={`{
  "history": [
    { "date": "2026-08-03", "price_per_m": 2.84, "index_points": 784.5 },
    { "date": "2026-08-02", "price_per_m": 2.87, "index_points": 792.8 },
    ...
  ]
}`}
      />

      <EndpointCard
        anchor="ep-models"
        method="GET"
        path="/v1/models?tier=standard&sort=blended"
        desc="Returns all tracked models with current pricing."
        params={[
          { name: "tier", type: "string", required: false, desc: "Filter by tier: frontier, standard, budget, micro" },
          { name: "provider", type: "string", required: false, desc: "Filter by provider name" },
          { name: "sort", type: "string", required: false, desc: "Sort by: blended, input, output, sit_score (default: sit_score)" },
          { name: "limit", type: "integer", required: false, desc: "Max results (default: 50, max: 500)" },
        ]}
        request={`$ curl -H "Authorization: Bearer YOUR_API_KEY" \\\n     "https://api.inferenceindexer.ai/v1/models?tier=standard&sort=blended"`}
        response={`{
  "count": 318,
  "models": [
    {
      "model_id": "deepseek/deepseek-v4-reasoner",
      "name": "DeepSeek V4 Reasoner",
      "provider": "DeepSeek",
      "tier": "frontier",
      "input_price_per_m": 0.55,
      "output_price_per_m": 2.19,
      "blended_price_per_m": 1.53,
      "sit_score": 0.04,
      "context_length": 128000,
      "change_24h": -3.0,
      "change_7d": -8.0
    },
    ...
  ]
}`}
      />

      <EndpointCard
        anchor="ep-models-id"
        method="GET"
        path="/v1/models/{model_id}"
        desc="Returns detailed pricing and metadata for a single model."
        params={[
          { name: "model_id", type: "string", required: true, desc: "The model ID (e.g. openai/gpt-5.6)" },
        ]}
        request={`$ curl -H "Authorization: Bearer YOUR_API_KEY" \\\n     https://api.inferenceindexer.ai/v1/models/openai/gpt-5.6`}
        response={`{
  "model_id": "openai/gpt-5.6",
  "name": "OpenAI: GPT-5.6",
  "provider": "OpenAI",
  "tier": "frontier",
  "input_price_per_m": 2.50,
  "output_price_per_m": 10.00,
  "blended_price_per_m": 4.75,
  "sit_score": 0.12,
  "context_length": 256000,
  "change_24h": 0.0,
  "change_7d": -2.1
}`}
      />

      <EndpointCard
        anchor="ep-models-id-history"
        method="GET"
        path="/v1/models/{model_id}/history?days=90"
        desc="Returns historical price data for a single model."
        params={[
          { name: "model_id", type: "string", required: true, desc: "The model ID" },
          { name: "days", type: "integer", required: false, desc: "Days of history (default: 30, max: 365 on free tier)" },
        ]}
        request={`$ curl -H "Authorization: Bearer YOUR_API_KEY" \\\n     "https://api.inferenceindexer.ai/v1/models/openai/gpt-5.6/history?days=90"`}
        response={`{
  "model_id": "openai/gpt-5.6",
  "history": [
    { "date": "2026-08-03", "blended_price_per_m": 4.75 },
    { "date": "2026-08-02", "blended_price_per_m": 4.80 },
    ...
  ]
}`}
      />
    </Section>
  );
}

type Param = { name: string; type: string; required: boolean; desc: string };

function EndpointCard({
  anchor,
  method,
  path,
  desc,
  params,
  request,
  response,
}: {
  anchor: string;
  method: string;
  path: string;
  desc: string;
  params: Param[];
  request: string;
  response: string;
}) {
  return (
    <div
      id={anchor}
      style={{
        background: "#1a1a1a",
        border: "1px solid #2a2a2a",
        borderRadius: 8,
        padding: 24,
        marginBottom: 20,
        scrollMarginTop: 72,
      }}
    >
      {/* Header row: method badge + path */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8, flexWrap: "wrap" }}>
        <MethodBadge method={method} />
        <code
          style={{
            fontFamily: MONO,
            fontSize: 16,
            color: "#ffffff",
            wordBreak: "break-all",
          }}
        >
          {path}
        </code>
      </div>
      <p style={{ ...pStyle, marginBottom: 20 }}>{desc}</p>

      {/* Parameters */}
      <h3 style={subLabel}>Parameters</h3>
      {params.length === 0 ? (
        <p style={{ ...pStyle, marginBottom: 20 }}>None</p>
      ) : (
        <div style={{ overflowX: "auto", marginBottom: 24 }}>
          <table style={paramTableStyle}>
            <thead>
              <tr>
                <th style={{ ...thStyle, width: "25%" }}>Parameter</th>
                <th style={{ ...thStyle, width: "15%" }}>Type</th>
                <th style={{ ...thStyle, width: "12%" }}>Required</th>
                <th style={{ ...thStyle }}>Description</th>
              </tr>
            </thead>
            <tbody>
              {params.map((p) => (
                <tr key={p.name}>
                  <td style={{ ...tdStyle, fontFamily: MONO, color: "#f2f2f2" }}>{p.name}</td>
                  <td style={{ ...tdStyle, fontFamily: MONO, color: "#8a8a8a" }}>{p.type}</td>
                  <td style={{ ...tdStyle }}>
                    <span style={{ color: p.required ? "#C4A038" : "#8a8a8a", fontSize: 13 }}>
                      {p.required ? "Yes" : "No"}
                    </span>
                  </td>
                  <td style={tdStyle}>{p.desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Example request */}
      <h3 style={subLabel}>Example Request</h3>
      <CodeBlock>{request}</CodeBlock>

      {/* Example response */}
      <h3 style={{ ...subLabel, marginTop: 20 }}>Example Response (200 OK)</h3>
      <CodeBlock>{response}</CodeBlock>
    </div>
  );
}

function MethodBadge({ method }: { method: string }) {
  const bg = method === "GET" ? "#22c55e" : "#8a8a8a";
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        fontSize: 11,
        fontWeight: 700,
        padding: "2px 8px",
        borderRadius: 4,
        background: bg,
        color: "#ffffff",
        fontFamily: MONO,
        flexShrink: 0,
      }}
    >
      {method}
    </span>
  );
}

/* ---------- Rate Limits ---------- */

function RateLimitsSection() {
  return (
    <Section id="rate-limits" title="Rate Limits">
      <div style={{ overflowX: "auto" }}>
        <table style={paramTableStyle}>
          <thead>
            <tr>
              <th style={thStyle}>Plan</th>
              <th style={thStyle}>Requests/day</th>
              <th style={thStyle}>Requests/minute</th>
              <th style={thStyle}>History access</th>
            </tr>
          </thead>
          <tbody>
            <RateRow plan="Public (no key)" day="100" min="10" history="7 days" />
            <RateRow plan="Free (email)" day="1,000" min="30" history="30 days" />
            <RateRow plan="Paid (future)" day="50,000" min="100" history="365 days" />
          </tbody>
        </table>
      </div>

      <p style={{ ...pStyle, marginTop: 20, marginBottom: 8 }}>
        Rate limit headers are included in every response:
      </p>
      <CodeBlock>
        <span style={{ color: "#C4A038" }}>X-RateLimit-Limit</span>
        <span style={{ color: "#8a8a8a" }}>: </span>
        <span style={{ color: "#ffffff" }}>1000</span>
        {"\n"}
        <span style={{ color: "#C4A038" }}>X-RateLimit-Remaining</span>
        <span style={{ color: "#8a8a8a" }}>: </span>
        <span style={{ color: "#ffffff" }}>987</span>
        {"\n"}
        <span style={{ color: "#C4A038" }}>X-RateLimit-Reset</span>
        <span style={{ color: "#8a8a8a" }}>: </span>
        <span style={{ color: "#ffffff" }}>1691078400</span>
      </CodeBlock>
    </Section>
  );
}

function RateRow({ plan, day, min, history }: { plan: string; day: string; min: string; history: string }) {
  return (
    <tr>
      <td style={{ ...tdStyle, fontFamily: MONO, color: "#f2f2f2" }}>{plan}</td>
      <td style={{ ...tdStyle, fontFamily: MONO }}>{day}</td>
      <td style={{ ...tdStyle, fontFamily: MONO }}>{min}</td>
      <td style={{ ...tdStyle, fontFamily: MONO }}>{history}</td>
    </tr>
  );
}

/* ---------- Response Format ---------- */

function ResponseFormatSection() {
  return (
    <Section id="response-format" title="Response Format">
      <p style={pStyle}>
        All responses are JSON. Timestamps are ISO 8601 UTC. Prices are in USD per million tokens.
      </p>

      <h3 style={subLabel}>Successful response (200 OK)</h3>
      <CodeBlock>{`{
  "data": { ... },
  "meta": {
    "request_id": "req_abc123",
    "timestamp": "2026-08-03T15:00:00Z"
  }
}`}</CodeBlock>

      <h3 style={{ ...subLabel, marginTop: 20 }}>Pagination (for list endpoints)</h3>
      <CodeBlock>{`{
  "count": 318,
  "page": 1,
  "per_page": 50,
  "total_pages": 7,
  "next": "/v1/models?page=2"
}`}</CodeBlock>
    </Section>
  );
}

/* ---------- Errors ---------- */

function ErrorsSection() {
  return (
    <Section id="errors" title="Errors">
      <div style={{ overflowX: "auto" }}>
        <table style={paramTableStyle}>
          <thead>
            <tr>
              <th style={{ ...thStyle, width: "30%" }}>Status Code</th>
              <th style={thStyle}>Meaning</th>
            </tr>
          </thead>
          <tbody>
            <ErrorRow code="200 OK" meaning="Success" tone="green" />
            <ErrorRow code="400 Bad Request" meaning="Invalid parameter (check the error message)" tone="amber" />
            <ErrorRow code="401 Unauthorized" meaning="Missing or invalid API key" tone="amber" />
            <ErrorRow code="404 Not Found" meaning="Model or endpoint doesn't exist" tone="amber" />
            <ErrorRow code="429 Too Many" meaning="Rate limit exceeded. Check X-RateLimit-Reset header" tone="red" />
            <ErrorRow code="500 Server Error" meaning="Something went wrong on our end. Retry after a few seconds" tone="red" />
          </tbody>
        </table>
      </div>

      <h3 style={{ ...subLabel, marginTop: 24 }}>Error response format</h3>
      <CodeBlock>{`{
  "error": {
    "code": "rate_limit_exceeded",
    "message": "Rate limit of 1000 requests/day exceeded. Resets at 2026-08-04T00:00:00Z.",
    "documentation_url": "https://www.inferenceindexer.ai/api/docs#rate-limits"
  }
}`}</CodeBlock>
    </Section>
  );
}

function ErrorRow({ code, meaning, tone }: { code: string; meaning: string; tone: "green" | "amber" | "red" }) {
  const color = tone === "green" ? "#22c55e" : tone === "amber" ? "#fbbf24" : "#ef4444";
  return (
    <tr>
      <td style={{ ...tdStyle, fontFamily: MONO, color }}>{code}</td>
      <td style={tdStyle}>{meaning}</td>
    </tr>
  );
}

/* ---------- Shared styles ---------- */

const pStyle: React.CSSProperties = { fontSize: 14, color: "#8a8a8a", lineHeight: 1.6, marginBottom: 12 };
const subLabel: React.CSSProperties = {
  fontSize: 11,
  fontWeight: 600,
  textTransform: "uppercase",
  letterSpacing: "0.08em",
  color: "#8a8a8a",
  margin: "0 0 10px",
};

const paramTableStyle: React.CSSProperties = {
  width: "100%",
  borderCollapse: "collapse",
  fontSize: 13,
  background: "#0d0d0d",
  border: "1px solid #2a2a2a",
  borderRadius: 6,
  overflow: "hidden",
};

const thStyle: React.CSSProperties = {
  textAlign: "left",
  padding: "8px 12px",
  background: "#222222",
  color: "#ffffff",
  fontSize: 12,
  textTransform: "uppercase",
  letterSpacing: "0.08em",
  fontWeight: 500,
  borderBottom: "1px solid #2a2a2a",
};

const tdStyle: React.CSSProperties = {
  padding: "8px 12px",
  borderBottom: "1px solid #1a1a1a",
  color: "#e5e5e5",
  fontSize: 13,
  verticalAlign: "top",
};

/* ---------- CodeBlock ---------- */

function CodeBlock({ children }: { children: React.ReactNode }) {
  return (
    <pre
      style={{
        background: "#0d0d0d",
        border: "1px solid #2a2a2a",
        borderRadius: 6,
        padding: "12px 16px",
        fontFamily: MONO,
        fontSize: 12,
        color: "#c9c9c9",
        overflowX: "auto",
        lineHeight: 1.6,
        margin: 0,
      }}
    >
      <code>{children}</code>
    </pre>
  );
}
