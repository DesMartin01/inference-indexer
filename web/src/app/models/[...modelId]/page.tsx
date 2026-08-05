import { notFound } from "next/navigation";
import Link from "next/link";
import { getModel, getModelHistory, getModelEndpoints, providerFaviconUrl } from "@/lib/api";
import { Sparkline } from "@/components/Sparkline";
import { Header } from "@/components/Header";
import type { Metadata } from "next";

const GREEN = "#22c55e";
const RED = "#ef4444";
const FLAT = "#7a7a7a";
const ACCENT = "#C4A038";

const TIER_COLOR: Record<string, string> = {
  frontier: ACCENT,
  standard: "#5b8def",
  budget: GREEN,
  micro: "#7a7a7a",
};

function pctColor(n: number) {
  return n < 0 ? GREEN : n > 0 ? RED : FLAT;
}

function pct(n: number) {
  if (n === 0) return "0%";
  const a = Math.abs(n);
  return (n < 0 ? "\u2193 " : "\u2191 ") + a.toFixed(1) + "%";
}

function money(n: number) {
  return "$" + n.toFixed(2);
}

// Clean model name: "OpenAI: GPT-5.6 Luna" -> "GPT-5.6 Luna"
function cleanModelName(raw: string): string {
  return raw.replace(/^[^:]+:\s*/, "");
}

// Generate SEO-optimized metadata per model page
export async function generateMetadata({ params }: { params: Promise<{ modelId: string[] }> }): Promise<Metadata> {
  const { modelId: modelIdParts } = await params;
  const modelId = modelIdParts.join("/");

  let model;
  try {
    model = await getModel(modelId);
  } catch {
    return {
      title: "Model Not Found - InferenceIndexer.ai",
      robots: { index: false, follow: true },
    };
  }

  const name = cleanModelName(model.name);
  const provider = model.provider;
  const blended = money(model.blended_price_per_m);
  const tier = model.tier.charAt(0).toUpperCase() + model.tier.slice(1);
  const sitScore = model.sit_score.toFixed(2);

  // Title: "GPT-5.6 Luna Price - $0.40/M | InferenceIndexer"
  const title = `${name} Price - ${blended}/M | InferenceIndexer`;

  // Description: "GPT-5.6 Luna inference pricing: input $0.10/M, output $0.60/M, blended $0.40/M. SIT Score 0.01 (Frontier tier). Compare API costs across providers."
  const description = `${name} by ${provider} inference pricing: input ${money(model.input_price_per_m)}/M, output ${money(model.output_price_per_m)}/M, blended ${blended}/M. SIT Score ${sitScore} (${tier} tier). Compare AI inference costs across providers.`;

  const url = `https://inferenceindexer.ai/models/${modelId}`;

  return {
    title,
    description,
    alternates: { canonical: url },
    openGraph: {
      title,
      description,
      url,
      siteName: "InferenceIndexer.ai",
      type: "website",
    },
    twitter: {
      card: "summary",
      title: `${name} - ${blended}/M`,
      description: `${provider} ${tier} tier model. Input ${money(model.input_price_per_m)}/M, output ${money(model.output_price_per_m)}/M.`,
    },
    keywords: [
      `${name} price`,
      `${name} API cost`,
      `${name} inference`,
      `${provider} ${name} pricing`,
      `${name} per million tokens`,
      `${name} input output price`,
      `AI inference pricing ${name}`,
      `${provider} API pricing`,
      `${provider} model prices`,
      "inference cost comparison",
      "AI model pricing",
    ],
  };
}

// Generate JSON-LD structured data for a model
function modelJsonLd(model: Awaited<ReturnType<typeof getModel>>) {
  const name = cleanModelName(model.name);
  return {
    "@context": "https://schema.org",
    "@type": "Product",
    name: `${name} - AI Inference API`,
    description: `${name} by ${model.provider}. Input ${money(model.input_price_per_m)}/M tokens, output ${money(model.output_price_per_m)}/M tokens. ${model.tier} tier model.`,
    brand: { "@type": "Brand", name: model.provider },
    category: "AI Inference API",
    offers: {
      "@type": "Offer",
      price: model.blended_price_per_m,
      priceCurrency: "USD",
      priceSpecification: [
        {
          "@type": "UnitPriceSpecification",
          name: "Input price per million tokens",
          price: model.input_price_per_m,
          priceCurrency: "USD",
          unitText: "per million tokens",
        },
        {
          "@type": "UnitPriceSpecification",
          name: "Output price per million tokens",
          price: model.output_price_per_m,
          priceCurrency: "USD",
          unitText: "per million tokens",
        },
      ],
    },
    additionalProperty: [
      { "@type": "PropertyValue", name: "SIT Score", value: model.sit_score },
      { "@type": "PropertyValue", name: "Quality Tier", value: model.tier },
      { "@type": "PropertyValue", name: "Context Length", value: model.context_length },
      ...(model.aa_index_score
        ? [{ "@type": "PropertyValue" as const, name: "AA Intelligence Index", value: model.aa_index_score }]
        : []),
      { "@type": "PropertyValue", name: "Model ID", value: model.model_id },
    ],
  };
}

export default async function ModelDetailPage({
  params,
}: {
  params: Promise<{ modelId: string[] }>;
}) {
  const { modelId: modelIdParts } = await params;
  const modelId = modelIdParts.join("/");

  let model;
  try {
    model = await getModel(modelId);
  } catch {
    notFound();
  }

  let history;
  try {
    history = await getModelHistory(modelId, 30);
  } catch {
    history = { model_id: model.model_id, name: model.name, history: [], days: 0 };
  }

  let endpoints;
  try {
    endpoints = await getModelEndpoints(modelId);
  } catch {
    endpoints = { model_id: model.model_id, name: model.name, endpoints: [], count: 0 };
  }

  const sitScore = model.sit_score;
  const sitPct = Math.min(sitScore * 100, 100);
  const tierColor = TIER_COLOR[model.tier] || FLAT;

  const providerFav = providerFaviconUrl(model.provider);

  return (
    <div style={{ background: "#0a0a0a", minHeight: "100vh", paddingBottom: 40 }}>
      {/* JSON-LD structured data for SEO */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(modelJsonLd(model)) }}
      />
      {/* Header */}
      <Header activePage="" />

      <div style={{ maxWidth: 1320, margin: "0 auto", padding: "28px 28px" }}>
        {/* Breadcrumb */}
        <div style={{ marginBottom: 24 }}>
          <Link href="/" style={{ fontSize: 13, color: "#8a8a8a", textDecoration: "none" }}>{"\u2190 All Models"}</Link>
          <span style={{ fontSize: 13, color: "#5f5f5f", margin: "0 8px" }}>/</span>
          <span style={{ fontSize: 13, color: "#e5e5e5" }}>{model.name}</span>
        </div>

        {/* Model Header */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: 48, alignItems: "start", marginBottom: 36 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 16 }}>
              <span style={{ width: 44, height: 44, borderRadius: "50%", background: "#16161a", border: "1px solid #333", display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden" }}>
                {providerFav ? (
                  <img src={providerFav} alt={model.provider} width={28} height={28} style={{ width: "28px", height: "28px", objectFit: "contain" }} />
                ) : (
                  <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 16, fontWeight: 600, color: "#8f8f96" }}>
                    {model.provider.charAt(0)}
                  </span>
                )}
              </span>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <h1 style={{ fontSize: 28, fontWeight: 600, color: "#f2f2f2", margin: 0, letterSpacing: "-0.02em" }}>{model.name}</h1>
                  <span style={{ fontSize: 11, letterSpacing: "0.04em", textTransform: "uppercase", padding: "3px 8px", borderRadius: 3, border: `1px solid ${tierColor}`, color: tierColor, background: "transparent" }}>
                    {model.tier}
                  </span>
                </div>
                <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: "#6a6a6a", marginTop: 4 }}>
                  {model.model_id}
                </div>
              </div>
            </div>
          </div>

          {/* Stats Grid */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, auto)", gap: "8px 32px", padding: "12px 0" }}>
            <StatRow label="AA INDEX" value={model.aa_index_score ? model.aa_index_score.toFixed(1) : "N/A"} />
            <StatRow label="CONTEXT" value={model.context_length ? `${(model.context_length / 1000).toFixed(0)}K` : "N/A"} />
            <StatRow label="MODALITY" value={model.modality || "N/A"} />
            <StatRow label="OPENNESS" value={model.tokenizer ? "Proprietary" : "N/A"} />
            <StatRow label="ADDED" value={model.date_added ? new Date(model.date_added).toLocaleDateString("en-US", { month: "short", year: "numeric" }) : "N/A"} />
            <StatRow label="LAST PRICED" value={model.fetched_at ? "2 min ago" : "N/A"} />
          </div>
        </div>

        {/* Price Card */}
        <div style={{ background: "#16161a", border: "1px solid #2a2a2a", borderRadius: 8, padding: "24px 28px", marginBottom: 28 }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 32, marginBottom: 24 }}>
            <div>
              <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.1em", color: "#6a6a6a", marginBottom: 8 }}>Input</div>
              <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 22, fontWeight: 500, color: "#c9c9c9" }}>
                {money(model.input_price_per_m)}<span style={{ fontSize: 13, color: "#6a6a6a" }}> /M</span>
              </div>
            </div>
            <div>
              <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.1em", color: "#6a6a6a", marginBottom: 8 }}>Output</div>
              <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 22, fontWeight: 500, color: "#c9c9c9" }}>
                {money(model.output_price_per_m)}<span style={{ fontSize: 13, color: "#6a6a6a" }}> /M</span>
              </div>
            </div>
            <div>
              <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.1em", color: "#6a6a6a", marginBottom: 8 }}>Blended (40/60)</div>
              <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 28, fontWeight: 500, color: ACCENT }}>
                {money(model.blended_price_per_m)}<span style={{ fontSize: 14, color: "#8a8a8a" }}> /M</span>
              </div>
            </div>
          </div>
          <div style={{ display: "flex", gap: 26, flexWrap: "wrap", borderTop: "1px solid #232327", paddingTop: 16 }}>
            <PeriodChange label="24h" value={model.change_24h} />
            <PeriodChange label="7d" value={model.change_7d} />
          </div>
        </div>

        {/* Price History Chart */}
        <div style={{ background: "#16161a", border: "1px solid #2a2a2a", borderRadius: 8, padding: "20px 24px", marginBottom: 28 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
            <div style={{ fontSize: 14, fontWeight: 500, color: "#e5e5e5" }}>Price History</div>
            <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "#5f5f5f" }}>
              30-day view, daily close
            </div>
          </div>
          {history.history.length > 0 ? (
            <>
              <Sparkline
                data={history.history.map((h) => h.blended_price_per_m)}
                width={640}
                height={180}
                color={ACCENT}
              />
              <div style={{ display: "flex", gap: 32, marginTop: 12, fontFamily: "'JetBrains Mono', monospace", fontSize: 12 }}>
                <ChartStat label="Low" value={money(Math.min(...history.history.map((h) => h.blended_price_per_m)))} />
                <ChartStat label="High" value={money(Math.max(...history.history.map((h) => h.blended_price_per_m)))} />
                <ChartStat label="Average" value={money(history.history.reduce((s, h) => s + h.blended_price_per_m, 0) / history.history.length)} />
              </div>
            </>
          ) : (
            <div style={{ height: 180, display: "flex", alignItems: "center", justifyContent: "center", color: "#6a6a6a", fontSize: 13 }}>
              Price history available after 24h of data collection
            </div>
          )}
        </div>

        {/* Provider Comparison Table */}
        {endpoints.count > 1 && (
          <div style={{ background: "#16161a", border: "1px solid #2a2a2a", borderRadius: 8, padding: "20px 24px", marginBottom: 28 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <div style={{ fontSize: 14, fontWeight: 500, color: "#e5e5e5" }}>Provider Comparison</div>
              <div style={{ fontSize: 12, color: "#6a6a6a" }}>
                {endpoints.count} providers · sorted by blended price
              </div>
            </div>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid #2a2a2a" }}>
                    <th style={{ textAlign: "left", padding: "8px 12px", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.08em", color: "#8a8a8a", fontWeight: 500 }}>Provider</th>
                    <th style={{ textAlign: "right", padding: "8px 12px", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.08em", color: "#8a8a8a", fontWeight: 500 }}>Input $/M</th>
                    <th style={{ textAlign: "right", padding: "8px 12px", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.08em", color: "#8a8a8a", fontWeight: 500 }}>Output $/M</th>
                    <th style={{ textAlign: "right", padding: "8px 12px", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.08em", color: "#8a8a8a", fontWeight: 500 }}>Blended $/M</th>
                    <th style={{ textAlign: "right", padding: "8px 12px", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.08em", color: "#8a8a8a", fontWeight: 500 }}>vs Median</th>
                  </tr>
                </thead>
                <tbody>
                  {endpoints.endpoints.map((ep, i) => {
                    const diff = ep.blended_price_per_m - model.blended_price_per_m;
                    const diffPct = model.blended_price_per_m > 0 ? (diff / model.blended_price_per_m) * 100 : 0;
                    const isCheapest = i === 0;
                    return (
                      <tr key={i} style={{ borderBottom: "1px solid #1c1c20" }}>
                        <td style={{ padding: "9px 12px", color: isCheapest ? "#e5e5e5" : "#c9c9c9", fontWeight: isCheapest ? 600 : 400 }}>
                          {isCheapest && <span style={{ color: GREEN, marginRight: 6 }}>{"\u2193"}</span>}
                          {ep.provider}
                        </td>
                        <td style={{ padding: "9px 12px", textAlign: "right", color: "#c9c9c9", fontVariantNumeric: "tabular-nums", fontFamily: "'JetBrains Mono', monospace", fontSize: 12 }}>
                          {money(ep.input_price_per_m)}
                        </td>
                        <td style={{ padding: "9px 12px", textAlign: "right", color: "#c9c9c9", fontVariantNumeric: "tabular-nums", fontFamily: "'JetBrains Mono', monospace", fontSize: 12 }}>
                          {money(ep.output_price_per_m)}
                        </td>
                        <td style={{ padding: "9px 12px", textAlign: "right", color: isCheapest ? GREEN : "#c9c9c9", fontWeight: isCheapest ? 600 : 400, fontVariantNumeric: "tabular-nums", fontFamily: "'JetBrains Mono', monospace", fontSize: 12 }}>
                          {money(ep.blended_price_per_m)}
                        </td>
                        <td style={{ padding: "9px 12px", textAlign: "right", fontSize: 12, color: diff < 0 ? GREEN : diff > 0 ? RED : FLAT, fontVariantNumeric: "tabular-nums" }}>
                          {diff === 0 ? "median" : `${diff > 0 ? "+" : ""}${diffPct.toFixed(1)}%`}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <div style={{ marginTop: 12, fontSize: 11, color: "#5f5f5f" }}>
              Blended price = 40% input + 60% output. Median price shown in header is the reference price for this model.
            </div>
          </div>
        )}

        {/* SIT Comparison Panel */}
        <div style={{ background: "#16161a", border: "1px solid #2a2a2a", borderRadius: 8, padding: "20px 24px", marginBottom: 28 }}>
          <div style={{ fontSize: 14, fontWeight: 500, color: "#e5e5e5", marginBottom: 16 }}>SIT Comparison</div>

          {/* SIT Score Bar */}
          <div style={{ marginBottom: 20 }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
              <span style={{ fontSize: 12, color: "#8a8a8a" }}>SIT Score</span>
              <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 14, fontWeight: 600, color: sitScore < 0.5 ? GREEN : sitScore <= 1.0 ? "#e5e5e5" : ACCENT }}>
                {sitScore.toFixed(2)} ({(sitScore * 100).toFixed(0)}% of tier average)
              </span>
            </div>
            <div style={{ height: 8, background: "#1a1a1a", borderRadius: 4, overflow: "hidden" }}>
              <div style={{ width: `${sitPct}%`, height: "100%", background: sitScore < 0.5 ? GREEN : sitScore <= 1.0 ? "#5b8def" : ACCENT, borderRadius: 4 }} />
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", marginTop: 4, fontFamily: "'JetBrains Mono', monospace", fontSize: 10.5, color: "#5f5f5f" }}>
              <span>0.00 (free)</span>
              <span>1.00 (tier average)</span>
            </div>
          </div>

          {/* Comparison Statements */}
          <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 20 }}>
            {model.comparisons.below_tier_avg_pct !== undefined && model.comparisons.below_tier_avg_pct > 0 && (
              <div style={{ fontSize: 13, color: GREEN }}>
                {model.comparisons.below_tier_avg_pct}% below {model.tier} tier average ({money(model.tier_average_price)}/M)
              </div>
            )}
            {model.comparisons.above_tier_avg_pct !== undefined && model.comparisons.above_tier_avg_pct > 0 && (
              <div style={{ fontSize: 13, color: ACCENT }}>
                {model.comparisons.above_tier_avg_pct}% above {model.tier} tier average ({money(model.tier_average_price)}/M)
              </div>
            )}
            {model.comparisons.above_composite_pct !== undefined && model.comparisons.above_composite_pct > 0 && (
              <div style={{ fontSize: 13, color: ACCENT }}>
                {model.comparisons.above_composite_pct}% above SIT-Composite
              </div>
            )}
          </div>

          {/* Tier Ranking */}
          <div>
            <div style={{ fontSize: 12, color: "#8a8a8a", marginBottom: 8 }}>Tier Ranking (by SIT Score)</div>
            <div style={{ fontSize: 13, color: "#e5e5e5" }}>
              Rank #{model.tier_rank} of {model.tier_total_models} {model.tier} models
            </div>
            <div style={{ marginTop: 8, padding: "8px 12px", background: "#1a1a1a", borderRadius: 4, border: "1px solid #2a2a2a", fontSize: 12, color: ACCENT }}>
              {"\u2190 YOU ARE HERE"} | {model.name}
            </div>
          </div>
        </div>

        {/* Data Sources */}
        <div style={{ background: "#16161a", border: "1px solid #2a2a2a", borderRadius: 8, padding: "20px 24px", marginBottom: 28 }}>
          <div style={{ fontSize: 14, fontWeight: 500, color: "#e5e5e5", marginBottom: 12 }}>Data Sources</div>
          <div style={{ display: "flex", gap: 16, marginBottom: 16 }}>
            <div style={{ flex: 1, border: "1px solid #2a2a2a", borderRadius: 4, padding: "10px 14px" }}>
              <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.1em", color: "#6a6a6a" }}>Primary</div>
              <div style={{ fontSize: 13, color: "#e5e5e5", marginTop: 4 }}>OpenRouter</div>
              <div style={{ fontSize: 11, color: "#5f5f5f", marginTop: 2 }}>Updated {model.fetched_at ? "2 min ago" : "N/A"}</div>
            </div>
          </div>
        </div>

        {/* API Access */}
        <div style={{ background: "#16161a", border: "1px solid #2a2a2a", borderRadius: 8, padding: "20px 24px", marginBottom: 28 }}>
          <div style={{ fontSize: 14, fontWeight: 500, color: "#e5e5e5", marginBottom: 12 }}>API Access</div>
          <div style={{ background: "#0d0d0d", border: "1px solid #2a2a2a", borderRadius: 4, padding: "12px 16px", fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: "#c9c9c9", overflowX: "auto" }}>
            <div style={{ color: "#6a6a6a" }}># Get this model&apos;s current price</div>
            <div style={{ marginTop: 4 }}>
              <span style={{ color: GREEN }}>curl</span> https://api.inferenceindexer.ai/v1/models/{model.model_id}
            </div>
            <div style={{ color: "#6a6a6a", marginTop: 12 }}># Response (truncated)</div>
            <div style={{ marginTop: 4, color: "#8a8a8a" }}>
              {`{ "model_id": "${model.model_id}", "name": "${model.name}", "blended_price_per_m": ${model.blended_price_per_m}, "sit_score": ${model.sit_score} }`}
            </div>
          </div>
          <div style={{ marginTop: 12 }}>
            <Link href="/#signup" style={{ fontSize: 13, color: "#C4A038" }}>Sign up for a free API key {"\u2192"}</Link>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <span style={{ fontSize: 10.5, textTransform: "uppercase", letterSpacing: "0.1em", color: "#5f5f5f" }}>{label}</span>
      <span style={{ fontSize: 13, color: "#e5e5e5" }}>{value}</span>
    </div>
  );
}

function PeriodChange({ label, value }: { label: string; value: number }) {
  const color = pctColor(value);
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <span style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.1em", color: "#6a6a6a" }}>{label}</span>
      <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 14, color, fontWeight: 500 }}>{pct(value)}</span>
    </div>
  );
}

function ChartStat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span style={{ color: "#5f5f5f" }}>{label}: </span>
      <span style={{ color: "#c9c9c9" }}>{value}/M</span>
    </div>
  );
}
