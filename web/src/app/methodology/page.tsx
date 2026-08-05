import { Header, Footer } from "@/components/Header";

export const metadata = {
  title: "Methodology - SIT Standard Inference Token | InferenceIndexer.ai",
  description:
    "How the Standard Inference Token (SIT) is calculated. Blended pricing formula, quality tier definitions, index weighting, data sources, and governance. Open methodology for AI inference price tracking.",
  alternates: { canonical: "https://inferenceindexer.ai/methodology" },
  openGraph: {
    title: "SIT Methodology - How AI Inference Prices Are Calculated",
    description: "Open methodology: blended pricing, quality tiers, index calculation, data sources, and governance.",
    url: "https://inferenceindexer.ai/methodology",
    siteName: "InferenceIndexer.ai",
  },
  keywords: [
    "SIT methodology",
    "Standard Inference Token",
    "AI pricing methodology",
    "inference price calculation",
    "blended pricing formula",
    "AA Intelligence Index tiers",
    "how inference prices are calculated",
  ],
};

export default function MethodologyPage() {
  return (
    <div style={{ background: "#0a0a0a", minHeight: "100vh" }}>
      <Header activePage="methodology" />
      <div style={{ maxWidth: 800, margin: "0 auto", padding: "40px 28px" }}>
        <h1 style={{ fontSize: 32, fontWeight: 600, color: "#f2f2f2", marginBottom: 8 }}>Methodology</h1>
        <p style={{ fontSize: 13, color: "#5f5f5f", marginBottom: 32 }}>Version 0.1 - Last updated: August 3, 2026</p>

        <Section n="1" title="Overview">
          <p style={p}>The Standard Inference Token (SIT) is a standardized unit for tracking AI inference prices across providers. It functions like a commodity index: one SIT represents the cost of 1 million tokens at a defined quality standard.</p>
          <p style={p}>InferenceIndexer is independent. We are not owned by any inference provider, and we publish our methodology openly so anyone can verify or challenge our calculations.</p>
        </Section>

        <Section n="2" title="Definition">
          <p style={p}>SIT is calculated as a blended price across input and output tokens:</p>
          <pre style={codeStyle}>{`blended_price = (input_price * 0.40) + (output_price * 0.60)

# All prices normalized to per-million-token ($/M)`}</pre>
          <p style={p}>The 40/60 weighting reflects typical production usage patterns where output tokens dominate cost due to longer generation lengths. This differs from Artificial Analysis which uses a 7:2:1 ratio. We publish both blends for transparency.</p>
        </Section>

        <Section n="3" title="Quality Tiers">
          <p style={p}>Models are assigned to tiers based on their Artificial Analysis Intelligence Index score:</p>
          <table style={tableStyle}>
            <thead><tr><th style={thStyle}>Tier</th><th style={thStyle}>AA Index</th><th style={thStyle}>Example $/M</th></tr></thead>
            <tbody>
              <tr><td style={tdStyle}>Frontier</td><td style={tdStyle}>50+</td><td style={tdStyle}>$7.50 - $420</td></tr>
              <tr><td style={tdStyle}>Standard</td><td style={tdStyle}>30-49</td><td style={tdStyle}>$0.30 - $1.40</td></tr>
              <tr><td style={tdStyle}>Budget</td><td style={tdStyle}>15-29</td><td style={tdStyle}>$0.03 - $0.10</td></tr>
              <tr><td style={tdStyle}>Micro</td><td style={tdStyle}>&lt;15</td><td style={tdStyle}>$0.01 - $0.05</td></tr>
            </tbody>
          </table>
          <p style={p}>Models without AA scores are assigned to tiers using a price-based fallback: blended price &gt; $10/M = Frontier, &gt; $1/M = Standard, &gt; $0.10/M = Budget, otherwise Micro.</p>
        </Section>

        <Section n="4" title="SIT Score">
          <p style={p}>The SIT Score is a per-model metric that indicates whether a model is cheap or expensive for its tier:</p>
          <pre style={codeStyle}>{`SIT Score = model_blended_price / tier_average_blended_price

# Below 0.50 = cheaper than tier average (good value)
# 0.50 - 1.00 = near tier average
# Above 1.00 = more expensive than tier average`}</pre>
          <p style={p}>The homepage table defaults to sorting by SIT Score ascending, surfacing models that offer the best inference value for their quality tier.</p>
        </Section>

        <Section n="5" title="Index Calculation">
          <p style={p}>Each tier index (SIT-Frontier, SIT-Standard, etc.) is calculated as the equal-weighted average of blended prices for all models in that tier. The SIT-Composite is the equal-weighted average across all models regardless of tier.</p>
          <p style={p}>The SIT-Spread is the difference between SIT-Frontier and SIT-Budget, representing the quality premium. A narrowing spread indicates that high-quality inference is becoming more accessible.</p>
          <p style={p}>Index points are set to 1000.00 at the base date (August 3, 2026). Future values track percentage change from this base.</p>
        </Section>

        <Section n="6" title="Data Sources">
          <p style={p}>Primary: OpenRouter /api/v1/models API (316+ models, 57 providers, hourly refresh).</p>
          <p style={p}>Supplementary (planned): Direct provider APIs from OpenAI, Anthropic, Google, DeepSeek, and others, fetched independently to cross-check OpenRouter pricing.</p>
          <p style={p}>Quality scores: Artificial Analysis Intelligence Index, accessed via OpenRouter benchmark data (169 of 316 models have AA scores).</p>
        </Section>

        <Section n="7" title="Governance">
          <p style={p}>Methodology changes are published with a 14-day comment period before taking effect. Any conflict of interest (e.g., a provider offering pricing data) is disclosed on this page.</p>
        </Section>

        <Section n="8" title="Limitations">
          <ul style={{ ...p, paddingLeft: 20 }}>
            <li style={{ marginBottom: 6 }}>Cached prompt pricing is not yet separately tracked</li>
            <li style={{ marginBottom: 6 }}>EU-Sovereign and Open Weights variants require manual provider tagging</li>
            <li style={{ marginBottom: 6 }}>Volume-weighted indexing is planned but not yet implemented (currently equal-weighted)</li>
            <li style={{ marginBottom: 6 }}>Some providers have region-specific pricing not captured by OpenRouter</li>
            <li style={{ marginBottom: 6 }}>AA Intelligence Index scores may lag behind model updates</li>
          </ul>
        </Section>

        <Section n="9" title="Citing the SIT">
          <pre style={codeStyle}>{`# Text citation
InferenceIndexer.ai SIT-Composite, August 2026.
https://inferenceindexer.ai/methodology

# BibTeX
@misc{inferenceindexer2026,
  title={SIT: Standard Inference Token Price Index},
  author={Martin, Des and Drebin, Frank},
  year={2026},
  url={https://inferenceindexer.ai/methodology}
}`}</pre>
        </Section>
      </div>
    </div>
  );
}

const p: React.CSSProperties = { fontSize: 14, color: "#8a8a8a", lineHeight: 1.7, marginBottom: 12 };
const codeStyle: React.CSSProperties = { background: "#0d0d0d", border: "1px solid #2a2a2a", borderRadius: 4, padding: "14px 18px", fontFamily: "'JetBrains Mono', monospace", fontSize: 12.5, color: "#c9c9c9", overflowX: "auto", lineHeight: 1.5, marginBottom: 12 };
const tableStyle: React.CSSProperties = { width: "100%", borderCollapse: "collapse", fontSize: 13, marginBottom: 12 };
const thStyle: React.CSSProperties = { textAlign: "left", padding: "8px 12px", borderBottom: "1px solid #2a2a2a", color: "#8a8a8a", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.08em" };
const tdStyle: React.CSSProperties = { padding: "8px 12px", borderBottom: "1px solid #1a1a1a", color: "#e5e5e5" };

function Section({ n, title, children }: { n: string; title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 32 }}>
      <h2 style={{ fontSize: 18, fontWeight: 600, color: "#C4A038", marginBottom: 12 }}>{n}. {title}</h2>
      {children}
    </div>
  );
}
