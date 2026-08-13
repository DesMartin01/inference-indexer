import Link from "next/link";
import type { Metadata } from "next";
import { Suspense } from "react";
import {
  getCompositeLatest,
  getCompositeHistory,
  getModels,
  getModelCount,
  formatPrice,
  formatPct,
  pctColor,
} from "@/lib/api";
import { buildSparkPath } from "@/lib/charts";
import { Header, Footer } from "@/components/Header";
import ModelTable from "@/components/ModelTable";
import { CURRENT_MODEL_COUNT, CURRENT_PROVIDER_COUNT } from "@/lib/counts";

export const revalidate = 60;

export async function generateMetadata(): Promise<Metadata> {
  const count = (await getModelCount().catch(() => 0)) || CURRENT_MODEL_COUNT;
  return {
  title: `AI Inference Pricing Index - ${count} Models | InferenceIndexer.ai`,
  description:
    `The Standard Inference Token (SIT) tracks AI inference prices across ${count} models. Live pricing, SIT scores, price history charts, and a free API. The CoinMarketCap of AI inference.`,
  alternates: { canonical: "https://www.inferenceindexer.ai" },
  openGraph: {
    title: `InferenceIndexer.ai - AI Inference Price Index (${count} models)`,
    description:
      `Live AI inference pricing for ${count} models. SIT-Composite index, tier rankings, price history, and free API access.`,
    url: "https://www.inferenceindexer.ai",
    siteName: "InferenceIndexer.ai",
    type: "website",
    images: [{ url: "/og-image.svg", width: 1200, height: 630, alt: "InferenceIndexer.ai - AI Inference Price Index" }],
  },
  twitter: {
    card: "summary_large_image",
    title: `AI Inference Pricing Index - ${count} Models`,
    description: "Live AI inference prices. SIT-Composite index, model pricing charts, free API.",
    images: ["/og-image.svg"],
  },
  keywords: [
    "AI inference pricing",
    "inference cost",
    "API pricing comparison",
    "LLM pricing",
    "GPT-5.6 price",
    "Claude Opus 5 price",
    "DeepSeek V4 price",
    "GLM-5.2 price",
    "Grok 4.5 price",
    "Gemini 3.6 price",
    "Llama 4 price",
    "per million tokens cost",
    "SIT Standard Inference Token",
    "model API cost comparison",
    "inference price index",
  ],
  };
}

export default async function Home() {
  // Fetch all data in parallel - API is now 82ms (was 8.1s) so fetching all models is fine
  const [latest, history, modelsData] = await Promise.all([
    getCompositeLatest(60).catch(() => null),
    getCompositeHistory(30, 60).catch(() => null),
    getModels(undefined, undefined, 500).catch(() => null),
  ]);

  // Fallback data if API is down
  const composite = latest?.composite;
  const models = modelsData?.models ?? [];
  const totalCount = modelsData?.returned ?? models.length;

  // Build sparkline from history
  const histVals =
    history?.history
      ?.map((h) => h.tiers.composite.price_per_m)
      .filter((v) => v > 0) ?? [];

  // If no history, use a synthetic series based on current price
  const sparkVals =
    histVals.length > 1
      ? histVals
      : [composite?.price_per_m ?? 7.06, composite?.price_per_m ?? 7.06];

  const sp = buildSparkPath(sparkVals, {
    height: 272,
    top: 15,
    bot: 248,
  });

  const heroPrice = composite ? formatPrice(composite.price_per_m) : "—";
  const d1 = composite?.change_24h ?? 0;
  const d7 = composite?.change_7d ?? 0;
  const d30 = composite?.change_30d ?? 0;
  const d90 = composite?.change_90d ?? 0;

  const period = (label: string, n: number) => ({
    label,
    value: formatPct(n),
    color: pctColor(n),
  });

  const lastUpdated = latest?.date
    ? latest.date + " 06:00 UTC"
    : new Date().toISOString().slice(0, 16).replace("T", " ") + " UTC";

  return (
    <>
      {/* JSON-LD: Dataset schema for the SIT index */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "Dataset",
            name: "InferenceIndexer SIT-Composite - AI Inference Price Index",
            description: `Independent price index for AI inference. ${composite ? `SIT-Composite: $${composite.price_per_m.toFixed(2)}/M tokens across ${composite.models} models from ${composite.providers} providers.` : `${totalCount} models, updated hourly.`}`,
            url: "https://www.inferenceindexer.ai",
            creator: {
              "@type": "Organization",
              name: "InferenceIndexer.ai",
            },
            temporalCoverage: "2026-08-04/..",
            keywords: ["AI inference", "pricing", "LLM", "API cost", "per million tokens", "SIT"],
            isAccessibleForFree: true,
            license: "https://www.inferenceindexer.ai/methodology",
            distribution: {
              "@type": "DataDownload",
              encodingFormat: "application/json",
              contentUrl: "https://www.inferenceindexer.ai/api-docs",
            },
          }),
        }}
      />
      <Header activePage="home" />

      {/* Hero section */}
      <section
        style={{
          maxWidth: "1320px",
          margin: "0 auto",
          padding: "44px 28px 34px",
          borderBottom: "1px solid #1a1a1a",
          position: "relative",
        }}
      >
        <div
          style={{
            position: "absolute",
            left: 0,
            top: 0,
            width: "620px",
            height: "300px",
            background:
              "radial-gradient(60% 55% at 18% 32%, rgba(196,160,56,0.09), rgba(196,160,56,0) 70%)",
            pointerEvents: "none",
          }}
        />
        <div
          style={{
            position: "relative",
            display: "grid",
            gridTemplateColumns: "minmax(320px, 1fr) minmax(360px, 640px)",
            gap: "48px",
            alignItems: "start",
          }}
        >
          <div>
            <p style={{ margin: "0 0 10px", fontSize: "13px", color: "#C4A038", fontWeight: 500, letterSpacing: "0.01em" }}>
              Independent price index for AI inference
            </p>
            <div style={{ display: "flex", alignItems: "baseline", gap: "10px" }}>
              <span
                style={{
                  fontSize: "12px",
                  fontWeight: 500,
                  textTransform: "uppercase",
                  letterSpacing: "0.14em",
                  color: "#8a8a8a",
                }}
              >
                Standard Inference Token (SIT)
              </span>
            </div>
            <a
              href="#"
              title="Open full index history"
              style={{
                display: "flex",
                alignItems: "flex-end",
                gap: "14px",
                marginTop: "12px",
                flexWrap: "wrap",
                textDecoration: "none",
                width: "fit-content",
              }}
            >
              <span
                style={{
                  fontFamily: "Inter, sans-serif",
                  fontSize: "48px",
                  fontWeight: 500,
                  lineHeight: 1,
                  letterSpacing: "-0.02em",
                  color: "#C4A038",
                  fontVariantNumeric: "tabular-nums",
                }}
              >
                {heroPrice}
              </span>
              <span
                style={{
                  fontFamily: "Inter, sans-serif",
                  fontSize: "14px",
                  color: "#8a8a8a",
                  paddingBottom: "4px",
                }}
              >
                / M tokens
              </span>
              <span style={{ fontSize: "15px", color: "#6a6a6a", paddingBottom: "5px" }}>→</span>
            </a>
            <div style={{ marginTop: "14px", display: "flex", alignItems: "center", gap: "10px" }}>
              <span
                style={{
                  fontFamily: "Inter, sans-serif",
                  fontSize: "18px",
                  fontWeight: 500,
                  color: pctColor(d1),
                  fontVariantNumeric: "tabular-nums",
                }}
              >
                {formatPct(d1)}
              </span>
              <span style={{ fontSize: "12.5px", color: "#7a7a7a" }}>today</span>
            </div>
            <div style={{ marginTop: "18px", display: "flex", gap: "26px", flexWrap: "wrap" }}>
              {[
                period("7 day", d7),
                period("30 day", d30),
                period("90 day", d90),
              ].map((p) => (
                <div key={p.label} style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                  <span
                    style={{
                      fontSize: "11px",
                      textTransform: "uppercase",
                      letterSpacing: "0.1em",
                      color: "#6a6a6a",
                    }}
                  >
                    {p.label}
                  </span>
                  <span
                    style={{
                      fontFamily: "Inter, sans-serif",
                      fontSize: "14px",
                      color: p.color,
                      fontVariantNumeric: "tabular-nums",
                    }}
                  >
                    {p.value}
                  </span>
                </div>
              ))}
            </div>
            <p
              style={{
                margin: "26px 0 0",
                maxWidth: "420px",
                fontSize: "13.5px",
                lineHeight: 1.6,
                color: "#8a8a8a",
              }}
            >
              The Standard Inference Token (SIT)-Composite tracks the cost of producing
              one million GPT-4-Turbo-equivalent inference tokens, the commodity unit for AI compute.
            </p>
            <Link
              href="/methodology"
              style={{ display: "inline-block", marginTop: "12px", fontSize: "13px", color: "#C4A038" }}
            >
              → Read methodology
            </Link>
          </div>

          {/* Sparkline chart */}
          <div>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: "12px",
                marginBottom: "8px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "5px" }}>
                <button
                  type="button"
                  style={{
                    fontFamily: "Inter, sans-serif",
                    fontSize: "11px",
                    padding: "3px 9px",
                    borderRadius: "3px",
                    cursor: "default",
                    background: "#26262c",
                    color: "#f2f2f2",
                    border: "1px solid #3a3a3a",
                  }}
                >
                  30d
                </button>
                <span
                  style={{
                    fontFamily: "Inter, sans-serif",
                    fontSize: "11px",
                    color: "#5f5f5f",
                    marginLeft: "4px",
                  }}
                >
                  {sparkVals.length}-day spot
                </span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <span
                  style={{
                    fontFamily: "Inter, sans-serif",
                    fontSize: "11px",
                    color: "#5f5f5f",
                  }}
                >
                  {sp.min > 0 ? `low $${sp.min.toFixed(2)} · high $${sp.max.toFixed(2)}` : ""}
                </span>
                <Link href="/api-docs" style={{ fontSize: "11.5px", color: "#C4A038" }}>
                  API keys →
                </Link>
              </div>
            </div>
            <div style={{ position: "relative" }}>
              <svg
                viewBox="0 0 640 272"
                role="img"
                aria-label="30-day SIT price history"
                style={{ display: "block", width: "100%", height: "auto" }}
              >
                {sp.gridLines.map((g, i) => (
                  <line key={i} x1="8" y1={g.y} x2="580" y2={g.y} stroke="#1e1e20" strokeWidth="1" />
                ))}
                {sp.area && <path d={sp.area} fill="rgba(196,160,56,0.10)" />}
                {sp.line && (
                  <path
                    d={sp.line}
                    fill="none"
                    stroke="#C4A038"
                    strokeWidth="1.5"
                    strokeLinejoin="round"
                    strokeLinecap="round"
                  />
                )}
              </svg>
              {sp.gridLines.map((g, i) => (
                <div
                  key={i}
                  style={{
                    position: "absolute",
                    right: 0,
                    width: "56px",
                    textAlign: "left",
                    top: g.top,
                    transform: "translateY(-50%)",
                    fontFamily: "Inter, sans-serif",
                    fontSize: "10.5px",
                    color: "#6a6a6a",
                    pointerEvents: "none",
                    fontVariantNumeric: "tabular-nums",
                  }}
                >
                  {g.label}
                </div>
              ))}
            </div>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                marginTop: "2px",
                paddingRight: "60px",
                fontFamily: "Inter, sans-serif",
                fontSize: "11px",
                color: "#5f5f5f",
              }}
            >
              <span>{sparkVals.length > 0 ? history?.history?.[0]?.date ?? "" : ""}</span>
              <span>
                {sparkVals.length > 2
                  ? history?.history?.[Math.floor(sparkVals.length / 2)]?.date ?? ""
                  : ""}
              </span>
              <span>today</span>
            </div>
          </div>
        </div>
      </section>

      {/* Model count heading */}
      <section style={{ maxWidth: "1320px", margin: "0 auto", padding: "26px 28px 0" }}>
        <h2 style={{ fontSize: "22px", fontWeight: 700, color: "#ffffff", margin: 0 }}>
          {totalCount} Models Tracked
        </h2>
        <p style={{ fontSize: "13px", color: "#6a6a6a", margin: "4px 0 0" }}>
          Live pricing across {totalCount} AI inference models. Prices pulled directly from inference providers.{" "}
          <a href="/api-docs" style={{ color: "#C4A038", textDecoration: "underline" }}>Our API</a>{" "}
          also exposes historic price data and shows where providers have diverged from aggregators.
        </p>
        <p style={{ fontSize: "13px", color: "#6a6a6a", margin: "4px 0 0" }}>
          Ranked by SIT Score below, our price-per-intelligence metric. Switch to AA Score to rank purely on capability.
        </p>
      </section>

      {/* Model table (client component, wrapped in Suspense for ISR) */}
      {models.length > 0 && (
        <Suspense fallback={null}>
          <ModelTable models={models} totalCount={totalCount} />
        </Suspense>
      )}

      {/* API signup */}
      <section
        id="api"
        style={{
          maxWidth: "1320px",
          margin: "0 auto",
          padding: "40px 28px 44px",
          textAlign: "center",
        }}
      >
        <span style={{ fontSize: "14px", color: "#8a8a8a" }}>
          Get the data via API →{" "}
          <Link href="/api-docs" style={{ color: "#C4A038" }}>
            View API documentation
          </Link>
        </span>
      </section>

      <Footer models={totalCount} providers={CURRENT_PROVIDER_COUNT} updatedAt={lastUpdated} />
    </>
  );
}
