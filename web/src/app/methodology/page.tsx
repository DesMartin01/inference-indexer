import { Header, Footer } from "@/components/Header";
import DataSourcesTable from "./DataSourcesTable";

export const metadata = {
  title: "Methodology - SIT Standard Inference Token | InferenceIndexer.ai",
  description:
    "How the Standard Inference Token (SIT) is calculated. Blended pricing formula, quality tier definitions, index weighting, data sources, and governance. Open methodology for AI inference price tracking.",
  alternates: { canonical: "https://www.inferenceindexer.ai/methodology" },
  openGraph: {
    title: "SIT Methodology - How AI Inference Prices Are Calculated",
    description: "Open methodology: blended pricing, quality tiers, index calculation, data sources, and governance.",
    url: "https://www.inferenceindexer.ai/methodology",
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
  { n: "10", title: "References", href: "#references" },
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
            Version 0.4 — Last updated: August 6, 2026
          </p>

          {/* 1. Overview */}
          <Section n="1" title="Overview" id="overview">
            <p style={p}>
              The Standard Inference Token (SIT) tracks the marginal cost of producing AI inference tokens
              at a defined quality standard. The SIT-Composite tracks the cost of producing one million
              GPT-4-Turbo-equivalent inference tokens, the commodity unit for AI compute.
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

            <SubSection n="2.3" title="Median Pricing (Multi-Provider Models)">
              <p style={p}>
                Many open-source models (e.g. GLM-5.2, Llama 4, DeepSeek V4) are hosted by multiple inference
                providers at different prices. For these models, InferenceIndexer computes the{" "}
                <strong style={{ color: "#e5e5e5" }}>median</strong> blended price across all available providers,
                rather than using a single source.
              </p>
              <p style={{ ...p, marginBottom: 8 }}>Median price formula:</p>
              <pre style={formulaStyle}>{`model_price = median(blended_price_1, blended_price_2, ..., blended_price_n)`}</pre>
              <p style={p}>
                The median is used instead of the mean or cheapest price because it is:
              </p>
              <ul style={bulletList}>
                <li style={bulletItem}>
                  <strong style={{ color: "#e5e5e5" }}>Robust to outliers:</strong> A single provider charging 10x
                  the market rate does not skew the index.
                </li>
                <li style={bulletItem}>
                  <strong style={{ color: "#e5e5e5" }}>Not gameable:</strong> A provider cannot manipulate the
                  headline price by temporarily dropping to $0.01.
                </li>
                <li style={bulletItem}>
                  <strong style={{ color: "#e5e5e5" }}>Realistic:</strong> The median represents what a user would
                  realistically pay, with half the providers charging more and half charging less.
                </li>
              </ul>
              <p style={p}>
                For models with only one provider, the single available price is used. The number of providers
                (Sources) is displayed for each model in the table and on the model detail page, where a full
                provider comparison table shows all available prices.
              </p>
              <p style={p}>
                Provider endpoints are fetched daily from OpenRouter&apos;s{" "}
                <code style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: "#c9c9c9" }}>
                  /api/v1/models/{"{id}"}/endpoints
                </code>{" "}
                endpoint. Hourly pipeline runs use the cached median from the most recent daily fetch.
              </p>
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
              <p style={p}>Each quality tier has its own index, tracking the median blended price per million tokens across all models in that tier. The SIT-Composite covers all tiers using usage-weighting (see Section 4.3):</p>
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
                    <td style={tdStyle}>Median blended price of all Frontier-tier models</td>
                  </tr>
                  <tr>
                    <td style={{ ...tdStyle, color: "#C4A038" }}>SIT-Standard</td>
                    <td style={tdStyle}>Median blended price of all Standard-tier models</td>
                  </tr>
                  <tr>
                    <td style={{ ...tdStyle, color: "#C4A038" }}>SIT-Budget</td>
                    <td style={tdStyle}>Median blended price of all Budget-tier models</td>
                  </tr>
                  <tr>
                    <td style={{ ...tdStyle, color: "#C4A038" }}>SIT-Composite</td>
                    <td style={tdStyle}>Usage-weighted mean of top 50 models by token volume (headline spot price)</td>
                  </tr>
                  <tr>
                    <td style={{ ...tdStyle, color: "#C4A038" }}>SIT-Spread</td>
                    <td style={tdStyle}>Frontier price minus Budget price</td>
                  </tr>
                </tbody>
              </table>
            </SubSection>

            <SubSection n="4.2" title="Quality-Adjusted Price (Cost / IQ)">
              <p style={p}>
                <strong style={{ color: "#C4A038" }}>The Quality-Adjusted Price is not a transactional price.</strong> It is a
                normalized index value for cross-model comparison. The actual price you pay a provider is the Blended
                Price. The Quality-Adjusted Price normalizes that price for intelligence so models of different
                capability levels can be compared on a like-for-like basis.
              </p>
              <p style={{ ...p, marginTop: 16 }}>
                The quality adjustment uses a transparent benchmark ratio:
              </p>
              <ul style={bulletList}>
                <li style={bulletItem}>
                  <strong style={{ color: "#e5e5e5" }}>Quality gate.</strong> Only models scoring at or above the
                  GPT-4-Turbo baseline (AA Intelligence Index &gt;= 35) are included in the SIT-Composite basket.
                  Models below this threshold are tracked but excluded from the headline number.
                </li>
                <li style={bulletItem}>
                  <strong style={{ color: "#e5e5e5" }}>Intelligence adjustment.</strong> Prices are adjusted by the
                  ratio of the GPT-4-Turbo reference score (40) to the model&apos;s own Artificial Analysis Intelligence
                  Index score. A model scoring higher than GPT-4-Turbo will have a lower adjusted price (cheaper per
                  unit of intelligence). Lower is better.
                </li>
              </ul>
              <p style={{ ...p, marginTop: 16 }}>The formula:</p>
              <pre style={formulaStyle}>{`Quality-Adjusted Price = Blended Price × (40 / AA Intelligence Score)

SIT Score = round(Quality-Adjusted Price / Tier Median × 100)
  100 = tier median, lower = cheaper, minimum = 1

SIT-Composite = Σ(weight_i × price_i) / Σ(weight_i)
  for top 50 models by token volume, AA score >= 35 only`}</pre>
              <p style={p}>
                Where:
              </p>
              <ul style={bulletList}>
                <li style={bulletItem}>
                  <span style={mutedMono}>Blended Price</span> = 0.4 × input + 0.6 × output (per million tokens)
                </li>
                <li style={bulletItem}>
                  <span style={mutedMono}>40</span> = GPT-4-Turbo (Jan 2024) reference score on AA Intelligence Index v4.1.
                  Models scoring 40 are at GPT-4-Turbo parity. The reference is based on the benchmark thresholds
                  defined in the SIT standard (MMLU &gt;= 86%, HumanEval &gt;= 67%, GSM8K &gt;= 92%).
                </li>
                <li style={bulletItem}>
                  <span style={mutedMono}>AA Intelligence Index</span> = Artificial Analysis Intelligence Index
                  v4.1, an independent third-party benchmark
                </li>
              </ul>
              <p style={{ ...p, marginTop: 16 }}>
                Lower Cost / IQ = cheaper per unit of intelligence. A SIT Score of 100 means the model is at the
                tier median. Scores below 100 are cheaper than the median; above 100 are more expensive. The minimum
                score is 1. Models without an AA Intelligence Index score do not receive a SIT score and are excluded
                from the composite basket.
              </p>
            </SubSection>

            <SubSection n="4.3" title="Usage Weighting">
              <p style={p}>
                The SIT-Composite uses a <strong style={{ color: "#e5e5e5" }}>usage-weighted mean</strong> of the
                top 50 models by weekly token volume on OpenRouter. This ensures the headline number reflects what
                developers actually pay for inference, not a raw average skewed by hundreds of niche models.
              </p>
              <p style={p}>
                Per-model median pricing (Section 2.3) is still used for the Blended Price column in the table.
                The usage weighting only applies to the SIT-Composite index calculation.
              </p>
              <pre style={formulaStyle}>{`weight_i = model_i_tokens / Σ(all top-50 model tokens)

SIT-Composite = Σ(weight_i × blended_price_i) / Σ(weight_i)`}</pre>
              <p style={p}>
                Usage data is sourced from{" "}
                <a href="https://openrouter.ai/rankings" style={{ color: "#C4A038", textDecoration: "none" }}>
                  OpenRouter Rankings
                </a>{" "}
                (weekly view). The basket is refreshed every Monday at 06:00 UTC. Between refreshes, the
                weights remain fixed so price changes are measured like-for-like.
              </p>
              <p style={p}>
                Per-tier indices (Frontier, Standard, Budget, Micro) use a simple median across all models
                in that tier. This answers: "What does a typical model in this tier cost?" The
                SIT-Composite uses usage-weighting to answer: "What do people actually pay for inference?"
              </p>
            </SubSection>

            <SubSection n="4.4" title="Calculation Frequency">
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
                    <td style={tdStyle}>Weekly</td>
                    <td style={tdStyle}>Refresh usage weights from OpenRouter Rankings (Mondays 06:00 UTC)</td>
                  </tr>
                  <tr>
                    <td style={tdStyle}>Monthly</td>
                    <td style={tdStyle}>Review tier composition, add/remove models</td>
                  </tr>
                </tbody>
              </table>
            </SubSection>

            <SubSection n="4.5" title="Base Date and Rebaselining">
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
                  <td style={tdStyle}>EU-hosted only (jurisdiction)</td>
                </tr>
                <tr>
                  <td style={{ ...tdStyle, color: "#C4A038" }}>SIT-ZDR</td>
                  <td style={tdStyle}>Zero data retention guaranteed (provider does not store or train on inputs)</td>
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
            <p style={{ ...p, marginTop: 16, fontSize: "12.5px", color: "#8a8a8a" }}>
              <strong style={{ color: "#C4A038" }}>ZDR and EU Infra status:</strong> Provider classifications for
              SIT-ZDR and SIT-EU-Sovereign are based on publicly available provider documentation as of August 2026.
              ZDR (Zero Data Retention) includes providers that do not store or train on user inputs by default on
              their standard API. EU-Sovereign includes providers domiciled in the EU/EEA that are not subject to the
              US CLOUD Act. Many providers offer ZDR or EU hosting only on enterprise plans; these are not classified
              as ZDR or EU-Sovereign here. Provider policies change; classifications are reviewed quarterly.
            </p>
          </Section>

          {/* 6. Data Sources */}
          <Section n="6" title="Data Sources" id="sources">
            <SubSection n="6.1" title="Primary Sources">
              <p style={p}>
                All providers in the index below, with their refresh cadence.
                The list updates automatically as new direct data providers are
                added, so it always reflects the current index.
              </p>
              <DataSourcesTable />
              <p style={{ fontSize: "12.5px", color: "#8a8a8a" }}>
                <strong style={{ color: "#C4A038" }}>Type:</strong> Aggregator
                sources aggregate and republish pricing from multiple upstream
                providers. Direct sources are provider-owned feeds pulled from
                their own endpoints or published pricing.
              </p>
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
                  <strong style={{ color: "#e5e5e5" }}>Volume data:</strong> Usage weights are sourced from
                  OpenRouter Rankings, which covers a subset of all inference traffic. Models not available on
                  OpenRouter are excluded from the composite basket.
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
                <li style={bulletItem}>Latency-adjusted pricing (tokens/second as a factor)</li>
                <li style={bulletItem}>Cache pricing tracked separately</li>
                <li style={bulletItem}>Batch pricing tracked separately</li>
                <li style={bulletItem}>Regional pricing (US, EU, Asia)</li>
                <li style={bulletItem}>Direct provider API usage data (beyond OpenRouter)</li>
              </ul>
            </SubSection>
          </Section>

          {/* 9. Citing the SIT */}
          <Section n="9" title="Citing the SIT" id="citing">
            <p style={p}>When citing InferenceIndexer data in research, articles, or reports:</p>

            <p style={{ ...p, marginTop: 16, marginBottom: 4 }}>
              <span style={{ color: "#C4A038", fontSize: 13 }}>Text format:</span>
            </p>
            <pre style={codeStyle}>{`InferenceIndexer SIT-Composite, August 5, 2026.
Available at: https://www.inferenceindexer.ai`}</pre>

            <p style={{ ...p, marginTop: 16, marginBottom: 4 }}>
              <span style={{ color: "#C4A038", fontSize: 13 }}>Academic format:</span>
            </p>
            <pre style={codeStyle}>{`InferenceIndexer (2026). Standard Inference Token
Methodology, v0.4.
Retrieved from https://www.inferenceindexer.ai/methodology`}</pre>

            <p style={{ ...p, marginTop: 16, marginBottom: 4 }}>
              <span style={{ color: "#C4A038", fontSize: 13 }}>BibTeX:</span>
            </p>
            <pre style={codeStyle}>{`@misc{inferenceindexer2026,
  title  = {InferenceIndexer: Standard Inference Token Methodology},
  author = {InferenceIndexer},
  year   = {2026},
  url    = {https://www.inferenceindexer.ai/methodology},
  note   = {Version 0.4}
}`}</pre>
          </Section>
          {/* 10. References */}
          <Section n="10" title="References" id="references">
            <ul style={bulletList}>
              <li style={bulletItem}>
                <a href="https://www.emergentmind.com/topics/standard-inference-token-sit" style={{ color: "#C4A038", textDecoration: "none" }}>
                  Standard Inference Token (SIT)
                </a>
                {" "}— Xing, Z. (23 Mar 2026) and Cunningham, M. (27 Feb 2026). EmergentMind topic summary.
                Defines SIT as a quality-gated inference token (MMLU &gt;= 86%, HumanEval &gt;= 67%, GSM8K &gt;= 92%)
                and the Token Price Index (TPI) as a volume-weighted, quality-adjusted mean of spot prices. Our
                quality gate and adjusted price formula are adapted from this framework.
              </li>
              <li style={bulletItem}>
                <a href="https://artificialanalysis.ai/" style={{ color: "#C4A038", textDecoration: "none" }}>
                  Artificial Analysis Intelligence Index
                </a>
                {" "}— Independent third-party benchmark for LLM intelligence scoring. Intelligence Index v4.1
                covers 257 models across 9 sub-evaluations. Used as the quality metric in our SIT formula.
              </li>
              <li style={bulletItem}>
                <a href="https://openrouter.ai/" style={{ color: "#C4A038", textDecoration: "none" }}>
                  OpenRouter API
                </a>
                {" "}— Primary pricing data source. 400+ models from 70+ providers. Hourly price refresh.
                Rankings endpoint provides weekly usage data for composite weighting.
              </li>
            </ul>
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
      <Footer providers={71} updatedAt="2026-08-03 00:00 UTC" />
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
