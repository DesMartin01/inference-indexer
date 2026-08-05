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

const TOC_ITEMS: { n: string; title: string; href: string }[] = [
  { n: "1", title: "Overview", href: "#overview" },
  { n: "2", title: "Definition", href: "#definition" },
  { n: "3", title: "Quality Tiers", href: "#tiers" },
  { n: "4", title: "Index Calculation", href: "#calculation" },
  { n: "5", title: "SIT Variants", href: "#variants" },
  { n: "6", title: "Data Sources", href: "#sources" },
  { n: "7", title: "Governance", href: "#governance" },
  { n: "8", title: "Limitations", href: "#limitations" },
  { n: "9", title: "Citing the SIT", href: "#citing" },
];

export default function MethodologyPage() {
  return (
    <div style={{ background: "#0a0a0a", minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <Header activePage="methodology" />
      <div
        style={{
          flex: 1,
          maxWidth: 1320,
          width: "100%",
          margin: "0 auto",
          padding: "40px 28px",
          display: "flex",
          gap: 48,
          alignItems: "flex-start",
        }}
      >
        {/* Main content (single column, max-width 800px) */}
        <main style={{ flex: 1, maxWidth: 800, minWidth: 0 }}>
          {/* Page title */}
          <h1 style={{ fontSize: 28, fontWeight: 700, color: "#ffffff", marginBottom: 8, letterSpacing: "-0.01em" }}>
            SIT Methodology
          </h1>
          <p style={{ fontSize: 14, color: "#8a8a8a", marginBottom: 8, lineHeight: 1.5 }}>
            How the Standard Inference Token is defined, calculated, and governed.
          </p>
          <p style={{ fontFamily: "var(--font-jetbrains-mono), 'JetBrains Mono', monospace", fontSize: 12, color: "#8a8a8a", marginBottom: 40 }}>
            Version 0.1 — Last updated: August 3, 2026
          </p>

          {/* 1. Overview */}
          <Section n="1" title="Overview" id="overview">
            <p style={p}>
              The Standard Inference Token (SIT) is a standardized unit of AI inference output that enables price
              comparison across models and providers. It is to AI inference what WTI is to crude oil: a single, trusted
              reference point.
            </p>
            <p style={p}>The SIT serves four purposes:</p>
            <ul style={bulletList}>
              <li style={bulletItem}>Price comparison across models on a like-for-like basis</li>
              <li style={bulletItem}>Composite indices that track inference price movements over time</li>
              <li style={bulletItem}>A reference price that futures contracts can settle against</li>
              <li style={bulletItem}>Benchmarking: &quot;am I paying above or below market rate?&quot;</li>
            </ul>
            <p style={p}>
              InferenceIndexer is an independent price reporting agency. We do not provide inference services, do not
              route API calls, and do not take positions in any inference derivatives market. All data sources are
              public and verifiable.
            </p>
          </Section>

          {/* 2. Definition */}
          <Section n="2" title="Definition" id="definition">
            <SubSection n="2.1" title="Unit">
              <p style={p}>
                <strong style={{ color: "#e5e5e5" }}>1 SIT = 1 million tokens of inference</strong> at a defined quality
                standard.
              </p>
              <p style={p}>
                &quot;Tokens&quot; refers to the standard industry unit of LLM inference, as measured by each
                provider&apos;s tokenizer. While tokenizers differ between models, the &quot;million tokens&quot;
                convention is universally adopted and provides sufficient standardization for pricing purposes.
              </p>
            </SubSection>

            <SubSection n="2.2" title="Pricing Components">
              <p style={p}>Every SIT-eligible model has three published prices:</p>
              <table style={tableStyle}>
                <thead>
                  <tr>
                    <th style={thStyle}>Component</th>
                    <th style={thStyle}>Definition</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td style={tdStyle}>Input price</td>
                    <td style={tdStyle}>Cost per million input (prompt) tokens</td>
                  </tr>
                  <tr>
                    <td style={tdStyle}>Output price</td>
                    <td style={tdStyle}>Cost per million output (completion) tokens</td>
                  </tr>
                  <tr>
                    <td style={tdStyle}>Blended price</td>
                    <td style={tdStyle}>Weighted average: 40% input + 60% output</td>
                  </tr>
                </tbody>
              </table>
              <p style={{ ...p, marginBottom: 8 }}>Blended price formula:</p>
              <pre style={formulaStyle}>{`blended_price = (0.4 × input_price) + (0.6 × output_price)`}</pre>
              <p style={p}>
                The 60% output weighting reflects production workloads where output tokens exceed input tokens
                (generation, coding, summarization). This ratio will be refined as real-world usage data becomes
                available.
              </p>
              <div style={noteCallout}>
                <em style={{ fontSize: 13, color: "#8a8a8a" }}>
                  Note: Artificial Analysis uses a different blend (70% cached input, 20% uncached input, 10% output)
                  which assumes heavy prompt caching. Our 40/60 blend assumes no caching, reflecting most production
                  workloads. We also publish a SIT-Cached variant using the 7:2:1 ratio for cached workloads.
                </em>
              </div>
            </SubSection>
          </Section>

          {/* 3. Quality Tiers */}
          <Section n="3" title="Quality Tiers" id="tiers">
            <p style={p}>
              Models are grouped into quality tiers based on demonstrated capability, using the Artificial Analysis
              Intelligence Index as an independent third-party benchmark.
            </p>
            <table style={tableStyle}>
              <thead>
                <tr>
                  <th style={thStyle}>Tier</th>
                  <th style={thStyle}>AA Index</th>
                  <th style={thStyle}>Description</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td style={{ ...tdStyle, color: "#C4A038", fontFamily: "var(--font-jetbrains-mono), 'JetBrains Mono', monospace" }}>SIT-Frontier</td>
                  <td style={tdStyle}>&gt;= 50</td>
                  <td style={tdStyle}>Top-tier models from frontier labs</td>
                </tr>
                <tr>
                  <td style={{ ...tdStyle, color: "#C4A038", fontFamily: "var(--font-jetbrains-mono), 'JetBrains Mono', monospace" }}>SIT-Standard</td>
                  <td style={tdStyle}>30 — 49</td>
                  <td style={tdStyle}>Mid-tier production models</td>
                </tr>
                <tr>
                  <td style={{ ...tdStyle, color: "#C4A038", fontFamily: "var(--font-jetbrains-mono), 'JetBrains Mono', monospace" }}>SIT-Budget</td>
                  <td style={tdStyle}>15 — 29</td>
                  <td style={tdStyle}>Low-cost models for high-volume tasks</td>
                </tr>
                <tr>
                  <td style={{ ...tdStyle, color: "#C4A038", fontFamily: "var(--font-jetbrains-mono), 'JetBrains Mono', monospace" }}>SIT-Micro</td>
                  <td style={tdStyle}>&lt; 15</td>
                  <td style={tdStyle}>Ultra-cheap models for simple tasks</td>
                </tr>
              </tbody>
            </table>
            <p style={{ ...p, marginTop: 20 }}>Current tier examples (August 2026):</p>
            <p style={exampleLineStyle}>
              <span style={{ color: "#C4A038" }}>SIT-Frontier</span> <span style={{ color: "#8a8a8a" }}>(8 models):</span>{" "}
              Claude Opus 5 <span style={mutedMono}>(AA: 61)</span>, GPT-5.6 <span style={mutedMono}>(AA: 57)</span>, Kimi
              K3 <span style={mutedMono}>(AA: 54)</span>, Grok 4.5 <span style={mutedMono}>(AA: 51)</span>, GLM-5.2{" "}
              <span style={mutedMono}>(AA: 51)</span>, Muse Spark 1.1 <span style={mutedMono}>(AA: 50)</span>, Gemini 3.6
              Flash <span style={mutedMono}>(AA: 50)</span>, Llama 4 Behemoth <span style={mutedMono}>(AA: 50)</span>
            </p>
            <p style={exampleLineStyle}>
              <span style={{ color: "#C4A038" }}>SIT-Standard</span> <span style={{ color: "#8a8a8a" }}>(156 models):</span>{" "}
              DeepSeek V4 Flash <span style={mutedMono}>(AA: 44)</span>, Nemotron 3 Ultra <span style={mutedMono}>(AA: 38)</span>,
              and 154 more
            </p>
            <p style={exampleLineStyle}>
              <span style={{ color: "#C4A038" }}>SIT-Budget</span> <span style={{ color: "#8a8a8a" }}>(78 models):</span>{" "}
              Gemma 3 27B, Llama 4 8B, Mistral Small, and 75 more
            </p>
            <p style={exampleLineStyle}>
              <span style={{ color: "#C4A038" }}>SIT-Micro</span> <span style={{ color: "#8a8a8a" }}>(73 models):</span>{" "}
              1B–8B parameter models without AA Index scores
            </p>
          </Section>

          {/* 4. Index Calculation */}
          <Section n="4" title="Index Calculation" id="calculation">
            <SubSection n="4.1" title="Tier Indices">
              <p style={p}>Each quality tier has its own composite index:</p>
              <table style={tableStyle}>
                <thead>
                  <tr>
                    <th style={thStyle}>Index</th>
                    <th style={thStyle}>What it tracks</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td style={{ ...tdStyle, color: "#C4A038" }}>SIT-Frontier</td>
                    <td style={tdStyle}>Average blended price of all Frontier-tier models</td>
                  </tr>
                  <tr>
                    <td style={{ ...tdStyle, color: "#C4A038" }}>SIT-Standard</td>
                    <td style={tdStyle}>Average blended price of all Standard-tier models</td>
                  </tr>
                  <tr>
                    <td style={{ ...tdStyle, color: "#C4A038" }}>SIT-Budget</td>
                    <td style={tdStyle}>Average blended price of all Budget-tier models</td>
                  </tr>
                  <tr>
                    <td style={{ ...tdStyle, color: "#C4A038" }}>SIT-Composite</td>
                    <td style={tdStyle}>Blended index across all tiers</td>
                  </tr>
                  <tr>
                    <td style={{ ...tdStyle, color: "#C4A038" }}>SIT-Spread</td>
                    <td style={tdStyle}>Frontier price minus Budget price</td>
                  </tr>
                </tbody>
              </table>
            </SubSection>

            <SubSection n="4.2" title="Weighting Methodology">
              <p style={{ ...p, marginBottom: 6 }}>
                <span style={{ color: "#C4A038" }}>Phase 1 (Launch):</span> Equal weighting across all models within each
                tier.
              </p>
              <pre style={formulaStyle}>{`SIT-Composite = Σ(blended_price_i × weight_i) / Σ(weight_i)
where weight_i = 1.0 (equal weight)`}</pre>
              <p style={{ ...p, marginTop: 16, marginBottom: 6 }}>
                <span style={{ color: "#C4A038" }}>Phase 2 (3–6 months):</span> Capacity-weighted. Models weighted by
                context window and provider size.
              </p>
              <p style={{ ...p, marginBottom: 6 }}>
                <span style={{ color: "#C4A038" }}>Phase 3 (6–12 months):</span> Volume-weighted. Models weighted by
                actual API transaction volume, sourced from provider-reported volumes and OpenRouter routing volumes.
              </p>
            </SubSection>

            <SubSection n="4.3" title="Calculation Frequency">
              <table style={tableStyle}>
                <thead>
                  <tr>
                    <th style={thStyle}>Frequency</th>
                    <th style={thStyle}>What happens</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td style={tdStyle}>Hourly</td>
                    <td style={tdStyle}>Pull pricing from all sources, update database</td>
                  </tr>
                  <tr>
                    <td style={tdStyle}>Daily</td>
                    <td style={tdStyle}>Calculate SIT indices, publish at 00:00 UTC</td>
                  </tr>
                  <tr>
                    <td style={tdStyle}>Monthly</td>
                    <td style={tdStyle}>Review tier composition, add/remove models</td>
                  </tr>
                </tbody>
              </table>
            </SubSection>

            <SubSection n="4.4" title="Base Date and Rebaselining">
              <ul style={bulletList}>
                <li style={bulletItem}>
                  Base date: <span style={mutedMono}>August 3, 2026</span>
                </li>
                <li style={bulletItem}>
                  Base value: <span style={mutedMono}>SIT-Composite = 1000 index points</span>
                </li>
                <li style={bulletItem}>
                  Rebaselining only on methodology changes. All rebaselining events are published with full explanation
                  and a 14-day public comment period.
                </li>
              </ul>
            </SubSection>
          </Section>

          {/* 5. SIT Variants */}
          <Section n="5" title="SIT Variants" id="variants">
            <p style={p}>
              Inference is not a single homogeneous commodity. The SIT supports attribute-based filtering, similar to
              how CoinMarketCap filters by category (DeFi, Layer 1, etc.).
            </p>
            <table style={tableStyle}>
              <thead>
                <tr>
                  <th style={thStyle}>SIT Variant</th>
                  <th style={thStyle}>Filter</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td style={{ ...tdStyle, color: "#C4A038" }}>SIT-Composite</td>
                  <td style={tdStyle}>All models (headline number)</td>
                </tr>
                <tr>
                  <td style={{ ...tdStyle, color: "#C4A038" }}>SIT-Frontier</td>
                  <td style={tdStyle}>AA Index &gt;= 50</td>
                </tr>
                <tr>
                  <td style={{ ...tdStyle, color: "#C4A038" }}>SIT-Standard</td>
                  <td style={tdStyle}>AA Index 30–49</td>
                </tr>
                <tr>
                  <td style={{ ...tdStyle, color: "#C4A038" }}>SIT-Budget</td>
                  <td style={tdStyle}>AA Index 15–29</td>
                </tr>
                <tr>
                  <td style={{ ...tdStyle, color: "#C4A038" }}>SIT-EU-Sovereign</td>
                  <td style={tdStyle}>EU-hosted, zero data retention</td>
                </tr>
                <tr>
                  <td style={{ ...tdStyle, color: "#C4A038" }}>SIT-Open</td>
                  <td style={tdStyle}>Open weights models only</td>
                </tr>
                <tr>
                  <td style={{ ...tdStyle, color: "#C4A038" }}>SIT-Proprietary</td>
                  <td style={tdStyle}>Proprietary models only</td>
                </tr>
                <tr>
                  <td style={{ ...tdStyle, color: "#C4A038" }}>SIT-Cached</td>
                  <td style={tdStyle}>With prompt caching applied (7:2:1 blend)</td>
                </tr>
              </tbody>
            </table>
            <p style={p}>
              The SIT-Composite is always the headline number. Variant indices allow users to track specific segments of
              the inference market.
            </p>
          </Section>

          {/* 6. Data Sources */}
          <Section n="6" title="Data Sources" id="sources">
            <SubSection n="6.1" title="Primary Sources">
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
                  <tr>
                    <td style={tdStyle}>OpenRouter API</td>
                    <td style={tdStyle}>Aggregator</td>
                    <td style={tdStyle}>315+</td>
                    <td style={tdStyle}>Hourly</td>
                  </tr>
                  <tr>
                    <td style={tdStyle}>Together AI API</td>
                    <td style={tdStyle}>Aggregator</td>
                    <td style={tdStyle}>~80</td>
                    <td style={tdStyle}>Hourly</td>
                  </tr>
                  <tr>
                    <td style={tdStyle}>Fireworks AI API</td>
                    <td style={tdStyle}>Aggregator</td>
                    <td style={tdStyle}>~50</td>
                    <td style={tdStyle}>Hourly</td>
                  </tr>
                  <tr>
                    <td style={tdStyle}>Groq API</td>
                    <td style={tdStyle}>Aggregator</td>
                    <td style={tdStyle}>~15</td>
                    <td style={tdStyle}>Hourly</td>
                  </tr>
                  <tr>
                    <td style={tdStyle}>OpenAI pricing</td>
                    <td style={tdStyle}>Direct</td>
                    <td style={tdStyle}>~15</td>
                    <td style={tdStyle}>Daily scrape</td>
                  </tr>
                  <tr>
                    <td style={tdStyle}>Anthropic pricing</td>
                    <td style={tdStyle}>Direct</td>
                    <td style={tdStyle}>~10</td>
                    <td style={tdStyle}>Daily scrape</td>
                  </tr>
                  <tr>
                    <td style={tdStyle}>Google AI Studio</td>
                    <td style={tdStyle}>Direct</td>
                    <td style={tdStyle}>~20</td>
                    <td style={tdStyle}>Daily scrape</td>
                  </tr>
                  <tr>
                    <td style={tdStyle}>DeepSeek pricing</td>
                    <td style={tdStyle}>Direct</td>
                    <td style={tdStyle}>~5</td>
                    <td style={tdStyle}>Daily scrape</td>
                  </tr>
                  <tr>
                    <td style={tdStyle}>TensorX</td>
                    <td style={tdStyle}>Direct</td>
                    <td style={tdStyle}>~10</td>
                    <td style={tdStyle}>Daily</td>
                  </tr>
                </tbody>
              </table>
            </SubSection>

            <SubSection n="6.2" title="Source Hierarchy">
              <p style={p}>When a model is available from multiple sources, priority:</p>
              <ol style={numberedList}>
                <li style={numberedItem}>
                  Direct provider (e.g. openai.com pricing for GPT-5.6)
                </li>
                <li style={numberedItem}>
                  Aggregator with lowest markup (e.g. OpenRouter base price)
                </li>
                <li style={numberedItem}>
                  Community submission (verified against at least one other source)
                </li>
              </ol>
            </SubSection>

            <SubSection n="6.3" title="Data Quality">
              <ul style={bulletList}>
                <li style={bulletItem}>
                  Every price point stores: timestamp, source URL, raw price, normalized price
                </li>
                <li style={bulletItem}>
                  Automated anomaly detection: if a price moves &gt;50% in one hour, flagged
                </li>
                <li style={bulletItem}>Manual review of all tier additions and removals</li>
                <li style={bulletItem}>
                  Full audit trail: every index calculation is reproducible from stored raw data
                </li>
              </ul>
            </SubSection>
          </Section>

          {/* 7. Governance */}
          <Section n="7" title="Governance" id="governance">
            <SubSection n="7.1" title="Methodology Changes">
              <p style={p}>Any change to this methodology triggers:</p>
              <ol style={numberedList}>
                <li style={numberedItem}>14-day public comment period</li>
                <li style={numberedItem}>Full version increment (0.1 → 0.2)</li>
                <li style={numberedItem}>Recalculation of historical indices using new methodology</li>
                <li style={numberedItem}>Publication of both old and new values for 30-day overlap</li>
              </ol>
            </SubSection>

            <SubSection n="7.2" title="Conflict of Interest">
              <ul style={bulletList}>
                <li style={bulletItem}>InferenceIndexer is an independent price reporting agency</li>
                <li style={bulletItem}>InferenceIndexer does not provide inference services</li>
                <li style={bulletItem}>InferenceIndexer does not take positions in inference futures or derivatives</li>
                <li style={bulletItem}>All data sources are public and verifiable</li>
                <li style={bulletItem}>Methodology is fully transparent and reproducible</li>
              </ul>
            </SubSection>
          </Section>

          {/* 8. Limitations */}
          <Section n="8" title="Limitations" id="limitations">
            <SubSection n="8.1" title="Known Limitations">
              <ol style={numberedList}>
                <li style={numberedItem}>
                  <strong style={{ color: "#e5e5e5" }}>Tokenizer differences:</strong> Different models use different
                  tokenizers. A &quot;million tokens&quot; from GPT-5.6 processes more text than a million tokens from
                  Llama 3.2. This is analogous to different crude oil grades having different energy densities. The SIT
                  accepts this imprecision as the cost of standardization.
                </li>
                <li style={numberedItem}>
                  <strong style={{ color: "#e5e5e5" }}>Volume data:</strong> Phase 1 uses equal weighting because
                  real-world transaction volumes are not publicly available. The index may over-represent niche models.
                </li>
                <li style={numberedItem}>
                  <strong style={{ color: "#e5e5e5" }}>Aggregator dependency:</strong> Many prices are sourced via
                  OpenRouter. If OpenRouter changes its pricing model, coverage may temporarily decrease.
                </li>
                <li style={numberedItem}>
                  <strong style={{ color: "#e5e5e5" }}>Quality benchmark dependency:</strong> Tier assignments depend on
                  the Artificial Analysis Intelligence Index. Changes to their methodology affect our tiers.
                </li>
                <li style={numberedItem}>
                  <strong style={{ color: "#e5e5e5" }}>Excluded models:</strong> Per-request pricing, enterprise-only
                  pricing, and deprecated models are not tracked.
                </li>
              </ol>
            </SubSection>

            <SubSection n="8.2" title="Future Enhancements">
              <ul style={bulletList}>
                <li style={bulletItem}>Volume weighting with real API call volumes</li>
                <li style={bulletItem}>Latency-adjusted pricing (tokens/second as a factor)</li>
                <li style={bulletItem}>Cache pricing tracked separately</li>
                <li style={bulletItem}>Batch pricing tracked separately</li>
                <li style={bulletItem}>Regional pricing (US, EU, Asia)</li>
              </ul>
            </SubSection>
          </Section>

          {/* 9. Citing the SIT */}
          <Section n="9" title="Citing the SIT" id="citing">
            <p style={p}>When citing InferenceIndexer data in research, articles, or reports:</p>

            <p style={{ ...p, marginTop: 16, marginBottom: 4 }}>
              <span style={{ color: "#C4A038", fontSize: 13 }}>Text format:</span>
            </p>
            <pre style={codeStyle}>{`InferenceIndexer SIT-Composite, August 3, 2026.
Available at: https://inferenceindexer.ai`}</pre>

            <p style={{ ...p, marginTop: 16, marginBottom: 4 }}>
              <span style={{ color: "#C4A038", fontSize: 13 }}>Academic format:</span>
            </p>
            <pre style={codeStyle}>{`InferenceIndexer (2026). Standard Inference Token
Methodology, v0.1.
Retrieved from https://inferenceindexer.ai/methodology`}</pre>

            <p style={{ ...p, marginTop: 16, marginBottom: 4 }}>
              <span style={{ color: "#C4A038", fontSize: 13 }}>BibTeX:</span>
            </p>
            <pre style={codeStyle}>{`@misc{inferenceindexer2026,
  title  = {InferenceIndexer: Standard Inference Token Methodology},
  author = {InferenceIndexer},
  year   = {2026},
  url    = {https://inferenceindexer.ai/methodology},
  note   = {Version 0.1}
}`}</pre>
          </Section>
        </main>

        {/* Sticky Table of Contents */}
        <aside
          style={{
            width: 200,
            flexShrink: 0,
            position: "sticky",
            top: 76,
            alignSelf: "flex-start",
          }}
        >
          {/* Scoped hover/active styles for TOC links (server-rendered) */}
          <style>{`
            .toc-link {
              color: #8a8a8a;
              transition: color 0.12s ease;
              text-decoration: none;
              display: block;
              padding: 4px 0;
              font-size: 13px;
              font-family: var(--font-jetbrains-mono), 'JetBrains Mono', monospace;
              line-height: 1.5;
            }
            .toc-link:hover { color: #C4A038; }
            .toc-num { color: #5f5f5f; margin-right: 8px; }
            .toc-link:hover .toc-num { color: #C4A038; }
          `}</style>
          <div
            style={{
              fontSize: 11,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              color: "#5f5f5f",
              marginBottom: 14,
              paddingBottom: 10,
              borderBottom: "1px solid #1a1a1a",
            }}
          >
            Contents
          </div>
          <nav style={{ display: "flex", flexDirection: "column" }}>
            {TOC_ITEMS.map((item) => (
              <a key={item.href} href={item.href} className="toc-link">
                <span className="toc-num">{item.n}.</span>
                {item.title}
              </a>
            ))}
          </nav>
        </aside>
      </div>
      <Footer models={316} providers={57} updatedAt="2026-08-03 00:00 UTC" />
    </div>
  );
}

/* ---------- Shared inline styles ---------- */

const p: React.CSSProperties = {
  fontSize: 15,
  color: "#e5e5e5",
  lineHeight: 1.7,
  marginBottom: 14,
};

const codeStyle: React.CSSProperties = {
  background: "#0d0d0d",
  border: "1px solid #2a2a2a",
  borderRadius: 6,
  padding: "14px 18px",
  fontFamily: "var(--font-jetbrains-mono), 'JetBrains Mono', monospace",
  fontSize: 12.5,
  color: "#c9c9c9",
  overflowX: "auto",
  lineHeight: 1.5,
  marginBottom: 14,
  whiteSpace: "pre-wrap",
};

const formulaStyle: React.CSSProperties = {
  background: "#0d0d0d",
  border: "1px solid #2a2a2a",
  borderRadius: 6,
  padding: "14px 18px",
  fontFamily: "var(--font-jetbrains-mono), 'JetBrains Mono', monospace",
  fontSize: 12.5,
  color: "#C4A038",
  overflowX: "auto",
  lineHeight: 1.6,
  marginBottom: 14,
  whiteSpace: "pre-wrap",
};

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

const bulletList: React.CSSProperties = {
  listStyle: "none",
  padding: 0,
  margin: "0 0 14px 0",
};

const bulletItem: React.CSSProperties = {
  fontSize: 15,
  color: "#e5e5e5",
  lineHeight: 1.7,
  marginBottom: 8,
  paddingLeft: 18,
  position: "relative" as const,
};

const numberedList: React.CSSProperties = {
  paddingLeft: 0,
  listStyle: "none",
  counterReset: "lim",
  margin: "0 0 14px 0",
};

const numberedItem: React.CSSProperties = {
  fontSize: 15,
  color: "#e5e5e5",
  lineHeight: 1.7,
  marginBottom: 10,
  paddingLeft: 32,
  position: "relative" as const,
};

const noteCallout: React.CSSProperties = {
  borderLeft: "2px solid #C4A038",
  paddingLeft: 16,
  marginLeft: 16,
  marginTop: 16,
  marginBottom: 16,
};

const exampleLineStyle: React.CSSProperties = {
  fontSize: 14,
  color: "#e5e5e5",
  lineHeight: 1.7,
  marginBottom: 12,
};

const mutedMono: React.CSSProperties = {
  fontFamily: "var(--font-jetbrains-mono), 'JetBrains Mono', monospace",
  fontSize: 13,
  color: "#8a8a8a",
};

/* ---------- Sub-components ---------- */

function Section({
  n,
  title,
  id,
  children,
}: {
  n: string;
  title: string;
  id: string;
  children: React.ReactNode;
}) {
  return (
    <section id={id} style={{ marginBottom: 44, scrollMarginTop: 76 }}>
      <h2
        style={{
          fontSize: 22,
          fontWeight: 700,
          color: "#ffffff",
          marginBottom: 16,
          lineHeight: 1.3,
          letterSpacing: "-0.01em",
        }}
      >
        <span style={{ color: "#C4A038", marginRight: 10 }}>{n}.</span>
        {title}
      </h2>
      {children}
    </section>
  );
}

function SubSection({
  n,
  title,
  children,
}: {
  n: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div style={{ marginBottom: 20, marginTop: 8 }}>
      <h3
        style={{
          fontSize: 18,
          fontWeight: 700,
          color: "#ffffff",
          marginBottom: 10,
          lineHeight: 1.4,
        }}
      >
        <span style={{ color: "#C4A038", marginRight: 8 }}>{n}</span>
        {title}
      </h3>
      {children}
    </div>
  );
}
