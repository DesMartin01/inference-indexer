import Link from "next/link";
import type { Metadata } from "next";
import { Suspense } from "react";
import {
  getCompositeLatest,
  getCompositeHistory,
  getModels,
  getModelCount,
  getProviderCount,
  formatPrice,
  formatPct,
  pctColor,
} from "@/lib/api";
import { buildSparkPath } from "@/lib/charts";
import { Header, Footer } from "@/components/Header";
import ModelTable from "@/components/ModelTable";
import EnginePanel from "@/components/EnginePanel";
import { CURRENT_MODEL_COUNT, CURRENT_PROVIDER_COUNT } from "@/lib/counts";

export const revalidate = 60;

export async function generateMetadata(): Promise<Metadata> {
  const count = (await getModelCount().catch(() => 0)) || CURRENT_MODEL_COUNT;
  return {
  title: `AI Inference Recommendation Engine - ${count} Models | InferenceIndexer.ai`,
  description:
    `Describe your workload and constraints; get ranked AI inference recommendations on verified prices across ${count} models. Standard Inference Token price index, quality-adjusted rankings, and a free API.`,
  alternates: { canonical: "https://www.inferenceindexer.ai" },
  openGraph: {
    title: `InferenceIndexer.ai - AI Inference Recommendation Engine (${count} models)`,
    description:
      `Constraint-aware inference recommendations on verified prices for ${count} models. Standard Inference Token index, quality-adjusted rankings, free API access.`,
    url: "https://www.inferenceindexer.ai",
    siteName: "InferenceIndexer.ai",
    type: "website",
    images: [{ url: "/og-image.png", width: 1200, height: 630, alt: "InferenceIndexer.ai - AI Inference Recommendation Engine" }],
  },
  twitter: {
    card: "summary_large_image",
    title: `AI Inference Recommendation Engine - ${count} Models`,
    description: "Describe your constraints, get ranked inference recommendations on verified prices. Free API.",
    images: ["/og-image.png"],
  },
  keywords: [
    "AI inference pricing",
    "AI model recommendation",
    "inference cost",
    "API pricing comparison",
    "LLM pricing",
    "cheapest LLM API",
    "zero data retention inference",
    "EU AI inference providers",
    "DeepSeek V4 price",
    "GLM-5.2 price",
    "per million tokens cost",
    "SIT Standard Inference Token",
    "model API cost comparison",
    "inference price index",
  ],
  };
}

export default async function Home() {
  // Fetch all data in parallel - API is now 82ms (was 8.1s) so fetching all models is fine
  const [latest, history, modelsData, apiModelCount, apiProviderCount] = await Promise.all([
    getCompositeLatest(60).catch(() => null),
    getCompositeHistory(30, 60).catch(() => null),
    getModels(undefined, undefined, 500).catch(() => null),
    getModelCount().catch(() => null),
    getProviderCount().catch(() => null),
  ]);

  // Fallback data if API is down
  const composite = latest?.composite;
  const models = modelsData?.models ?? [];
  // Headline count uses the API's authoritative model count (all active models),
  // not the 500-row page fetch. Falls back to the page fetch, then the static constant.
  const totalCount = apiModelCount ?? modelsData?.count ?? modelsData?.returned ?? models.length ?? CURRENT_MODEL_COUNT;
  const providerCount = apiProviderCount ?? CURRENT_PROVIDER_COUNT;
  // Honest count for "models quality-adjusted": only rows with a Cost/IQ value
  const qualityAdjusted = models.filter((m) => m.sit_adjusted_price != null).length;

  // Build sparkline from history (with AA era tags for rebase break-lines)
  const histPoints =
    history?.history
      ?.map((h) => ({
        price: h.tiers.composite?.price_per_m ?? 0,
        aaVersion: h.tiers.composite?.aa_version ?? null,
        date: h.date,
      }))
      .filter((p) => p.price > 0) ?? [];

  const histVals = histPoints.map((p) => p.price);

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

  // AA rebase era-breaks (Sep 2026): dashed vertical lines where the
  // Intelligence Index version changed. The series is rebased (Sep 4 = 1000),
  // so segments on either side of a break are not directly comparable.
  const X0 = 8;
  const X1 = 580;
  const eraBreaks: { x: number; label: string }[] = [];
  for (let i = 1; i < histPoints.length; i++) {
    const prevV = histPoints[i - 1].aaVersion;
    const curV = histPoints[i].aaVersion;
    if (prevV && curV && prevV !== curV) {
      const x = X0 + (i * (X1 - X0)) / (histPoints.length - 1);
      eraBreaks.push({ x, label: curV });
    }
  }

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

  // Catalogue preview: top 3 by Cost/IQ among models that have one (any tier,
  // mirrors the engine's ranking basis so the preview demonstrates the method)
  const preview = models
    .filter((m) => m.sit_adjusted_price != null)
    .sort((a, b) => (a.sit_adjusted_price ?? Infinity) - (b.sit_adjusted_price ?? Infinity))
    .slice(0, 3);

  return (
    <>
      {/* JSON-LD: Dataset schema for the SIT index */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "Dataset",
            name: "InferenceIndexer Standard Inference Token price index - AI Inference Prices",
            description: `Independent price index and recommendation engine for AI inference. ${composite ? `Standard Inference Token price: $${composite.price_per_m.toFixed(4)}/M GPT-4-equivalent tokens, equal-weighted across ${composite.providers} providers.` : `${totalCount} models, updated hourly.`}`,
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

      {/* ============ BLOCK 1 — THE ENGINE ============ */}
      <section style={{ maxWidth: "1320px", margin: "0 auto", padding: "40px 28px 0" }}>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(0, 1fr) minmax(220px, 280px)",
            gap: "48px",
            alignItems: "end",
            paddingBottom: "16px",
          }}
        >
          <h1
            style={{
              margin: 0,
              maxWidth: "17em",
              fontSize: "46px",
              lineHeight: 1.05,
              fontWeight: 600,
              letterSpacing: "-0.04em",
              color: "#f2f2f2",
            }}
          >
            AI inference recommendation engine
          </h1>
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "7px",
              fontFamily: "var(--font-jetbrains-mono), monospace",
              fontSize: "12px",
              color: "#8a8a8a",
              fontVariantNumeric: "tabular-nums",
              paddingBottom: "6px",
            }}
          >
            <span style={{ display: "flex", justifyContent: "space-between", gap: "12px" }}>
              <span>Models indexed</span>
              <span style={{ color: "#c9c9c9" }}>{totalCount.toLocaleString()}</span>
            </span>
            <span style={{ display: "flex", justifyContent: "space-between", gap: "12px" }}>
              <span>Providers indexed</span>
              <span style={{ color: "#c9c9c9" }}>{providerCount}</span>
            </span>
            <span style={{ display: "flex", justifyContent: "space-between", gap: "12px" }}>
              <span>Prices sourced</span>
              <span style={{ color: "#c9c9c9" }}>hourly</span>
            </span>
          </div>
        </div>
      </section>

      <Suspense fallback={null}>
        <EnginePanel totalModels={totalCount} />
      </Suspense>

      {/* ============ BLOCK 2 — COVERAGE ============ */}
      <section style={{ maxWidth: "1320px", margin: "0 auto", padding: "72px 28px 0" }}>
        <div
          style={{
            display: "flex",
            alignItems: "baseline",
            gap: "12px",
            paddingBottom: "10px",
            borderBottom: "1px solid #2a2a2a",
            marginBottom: "24px",
          }}
        >
          <span
            style={{
              fontFamily: "var(--font-jetbrains-mono), monospace",
              fontSize: "10.5px",
              fontWeight: 600,
              letterSpacing: "0.14em",
              textTransform: "uppercase",
              color: "#C4A038",
            }}
          >
            Coverage
          </span>
          <span style={{ color: "#3a3a3a", fontSize: "10.5px" }}>·</span>
          <span
            style={{
              fontFamily: "var(--font-jetbrains-mono), monospace",
              fontSize: "10.5px",
              letterSpacing: "0.13em",
              textTransform: "uppercase",
              color: "#8a8a8a",
            }}
          >
            What is verified today, and what comes next
          </span>
          <span style={{ flex: 1, height: 1, background: "#1c1c1c", marginBottom: 3 }} />
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) minmax(0, 1fr)", gap: "48px" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            <div style={{ display: "flex", alignItems: "baseline", gap: "12px" }}>
              <span style={{ fontSize: "24px", fontWeight: 600, letterSpacing: "-0.025em", color: "#f2f2f2" }}>Price</span>
              <span style={{ fontSize: "12px", fontWeight: 500, color: "#C4A038" }}>Verified</span>
            </div>
            <p style={{ margin: 0, fontSize: "14px", lineHeight: 1.55, color: "#c9c9c9" }}>
              Composite and per-model prices pulled directly from provider APIs and rebuilt every hour.
            </p>
            <div style={{ display: "flex", alignItems: "baseline", gap: "10px", paddingTop: "2px" }}>
              <span
                style={{
                  fontFamily: "var(--font-jetbrains-mono), monospace",
                  fontSize: "26px",
                  fontWeight: 500,
                  letterSpacing: "-0.02em",
                  color: "#f2f2f2",
                  fontVariantNumeric: "tabular-nums",
                }}
              >
                {providerCount}
              </span>
              <span style={{ fontSize: "12.5px", color: "#8a8a8a" }}>providers polled hourly</span>
            </div>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            <div style={{ display: "flex", alignItems: "baseline", gap: "12px" }}>
              <span style={{ fontSize: "24px", fontWeight: 600, letterSpacing: "-0.025em", color: "#f2f2f2" }}>Quality</span>
              <span style={{ fontSize: "12px", fontWeight: 500, color: "#C4A038" }}>Verified: intelligence</span>
            </div>
            <p style={{ margin: 0, fontSize: "14px", lineHeight: 1.55, color: "#c9c9c9" }}>
              Intelligence verified against the AA index, then divided into price so rankings reward value, not cheapness.
            </p>
            <div style={{ display: "flex", alignItems: "baseline", gap: "10px", paddingTop: "2px" }}>
              <span
                style={{
                  fontFamily: "var(--font-jetbrains-mono), monospace",
                  fontSize: "26px",
                  fontWeight: 500,
                  letterSpacing: "-0.02em",
                  color: "#f2f2f2",
                  fontVariantNumeric: "tabular-nums",
                }}
              >
                {qualityAdjusted.toLocaleString()}
              </span>
              <span style={{ fontSize: "12.5px", color: "#8a8a8a" }}>models quality-adjusted</span>
            </div>
          </div>
        </div>

        <div
          style={{
            marginTop: "36px",
            borderTop: "1px solid #1d1d21",
            paddingTop: "18px",
            display: "grid",
            gridTemplateColumns: "minmax(0, 200px) minmax(0, 1fr) minmax(0, 1fr)",
            gap: "36px",
            alignItems: "start",
          }}
        >
          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            <span style={{ fontSize: "14px", fontWeight: 600, color: "#c9c9c9" }}>In development</span>
            <span style={{ fontSize: "12px", lineHeight: 1.5, color: "#8a8a8a" }}>
              Criteria published before any provider is rated against them.
            </span>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "7px" }}>
            <span style={{ fontSize: "16px", fontWeight: 600, letterSpacing: "-0.015em", color: "#c9c9c9" }}>Privacy</span>
            <p style={{ margin: 0, fontSize: "13px", lineHeight: 1.5, color: "#8a8a8a" }}>
              Whether a provider keeps your tokens, for how long, and under whose jurisdiction. Matched on provider
              statements today.
            </p>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "7px" }}>
            <span style={{ fontSize: "16px", fontWeight: 600, letterSpacing: "-0.015em", color: "#c9c9c9" }}>Security</span>
            <p style={{ margin: 0, fontSize: "13px", lineHeight: 1.5, color: "#8a8a8a" }}>
              What could go wrong using this inference, stated in terms that can be checked. Not yet scored.
            </p>
          </div>
        </div>

        <div style={{ marginTop: "40px" }}>
          <h2 style={{ margin: "0 0 12px", fontSize: "16px", fontWeight: 600, letterSpacing: "-0.01em", color: "#f2f2f2" }}>
            Who attests each claim today, and who verifies it
          </h2>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "minmax(180px, 1fr) minmax(0, 220px) minmax(0, 220px)",
              gap: "14px",
              padding: "0 0 8px",
              alignItems: "center",
              borderBottom: "1px solid #2a2a2a",
            }}
          >
            {["The claim", "Provider attested", "Verified by"].map((h, i) => (
              <span
                key={h}
                style={{
                  fontFamily: "var(--font-jetbrains-mono), monospace",
                  fontSize: "10px",
                  fontWeight: 500,
                  letterSpacing: "0.12em",
                  textTransform: "uppercase",
                  color: "#8a8a8a",
                  textAlign: i === 2 ? "right" : "left",
                }}
              >
                {h}
              </span>
            ))}
          </div>
          {[
            ["Price per million tokens", "Inference Indexer"],
            ["Model quality and intelligence", "Inference Indexer"],
            ["Model identity and quantization", "In development"],
            ["Data retention and privacy", "In development"],
            ["Security posture", "In development"],
          ].map(([claim, verifier]) => (
            <div
              key={claim}
              style={{
                display: "grid",
                gridTemplateColumns: "minmax(180px, 1fr) minmax(0, 220px) minmax(0, 220px)",
                gap: "14px",
                alignItems: "center",
                padding: "11px 0",
                minHeight: "42px",
                borderBottom: "1px solid #1d1d21",
              }}
            >
              <span style={{ fontSize: "13.5px", lineHeight: 1.35, color: "#f2f2f2" }}>{claim}</span>
              <span style={{ fontSize: "13px", color: "#8a8a8a" }}>The provider</span>
              <span
                style={{
                  fontSize: "13px",
                  fontWeight: 500,
                  color: verifier === "In development" ? "#c9c9c9" : "#C4A038",
                  textAlign: "right",
                }}
              >
                {verifier}
              </span>
            </div>
          ))}
        </div>
      </section>

      {/* ============ BLOCK 3 — STANDARD INFERENCE TOKEN PRICE ============ */}
      <section style={{ maxWidth: "1320px", margin: "0 auto", padding: "72px 28px 0" }}>
        <div
          style={{
            display: "flex",
            alignItems: "baseline",
            gap: "12px",
            paddingBottom: "10px",
            borderBottom: "1px solid #2a2a2a",
            marginBottom: "20px",
          }}
        >
          <span
            style={{
              fontFamily: "var(--font-jetbrains-mono), monospace",
              fontSize: "10.5px",
              fontWeight: 600,
              letterSpacing: "0.14em",
              textTransform: "uppercase",
              color: "#C4A038",
            }}
          >
            Standard Inference Token price
          </span>
          <span style={{ color: "#3a3a3a", fontSize: "10.5px" }}>·</span>
          <span
            style={{
              fontFamily: "var(--font-jetbrains-mono), monospace",
              fontSize: "10.5px",
              letterSpacing: "0.13em",
              textTransform: "uppercase",
              color: "#8a8a8a",
            }}
          >
            Verified hourly, pulled directly from provider APIs
          </span>
          <span style={{ flex: 1, height: 1, background: "#1c1c1c", marginBottom: 3 }} />
        </div>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(0, 0.72fr) minmax(0, 1fr)",
            background: "#16161a",
            border: "1px solid #2a2a2a",
            borderRadius: 8,
          }}
        >
          <div
            style={{
              padding: "26px 30px 24px",
              borderRight: "1px solid #2a2a2a",
              display: "flex",
              flexDirection: "column",
              gap: "20px",
            }}
          >
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              <a
                href="#"
                title="Open full index history"
                style={{
                  display: "flex",
                  alignItems: "flex-end",
                  gap: "12px",
                  flexWrap: "wrap",
                  textDecoration: "none",
                  width: "fit-content",
                }}
              >
                <span
                  style={{
                    fontFamily: "Inter, sans-serif",
                    fontSize: "58px",
                    fontWeight: 500,
                    lineHeight: 0.9,
                    letterSpacing: "-0.045em",
                    color: "#C4A038",
                    fontVariantNumeric: "tabular-nums",
                  }}
                >
                  {heroPrice}
                </span>
                <span style={{ fontFamily: "Inter, sans-serif", fontSize: "13px", color: "#8a8a8a", paddingBottom: "5px" }}>
                  / M tokens
                </span>
              </a>
              <div style={{ display: "flex", alignItems: "baseline", gap: "10px", flexWrap: "wrap" }}>
                <span
                  style={{
                    fontFamily: "var(--font-jetbrains-mono), monospace",
                    fontSize: "11.5px",
                    letterSpacing: "0.05em",
                    color: "#c9c9c9",
                  }}
                >
                  SIT index
                </span>
                <span
                  style={{
                    fontFamily: "Inter, sans-serif",
                    fontSize: "16px",
                    fontWeight: 500,
                    color: pctColor(d1),
                    fontVariantNumeric: "tabular-nums",
                  }}
                >
                  {formatPct(d1)}
                </span>
                <span style={{ fontSize: "12px", color: "#7a7a7a" }}>today</span>
              </div>
            </div>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
                borderTop: "1px solid #222",
                borderBottom: "1px solid #222",
              }}
            >
              {[
                period("7 day", d7),
                period("30 day", d30),
                period("90 day", d90),
              ].map((p) => (
                <div key={p.label} style={{ padding: "11px 0", display: "flex", flexDirection: "column", gap: "3px" }}>
                  <span style={{ fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.1em", color: "#6a6a6a" }}>
                    {p.label}
                  </span>
                  <span
                    style={{
                      fontFamily: "Inter, sans-serif",
                      fontSize: "15px",
                      fontWeight: 500,
                      color: p.color,
                      fontVariantNumeric: "tabular-nums",
                    }}
                  >
                    {p.value}
                  </span>
                </div>
              ))}
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              <p style={{ margin: 0, fontSize: "13px", lineHeight: 1.55, color: "#8a8a8a" }}>
                The Standard Inference Token (SIT) tracks the cost of producing one million GPT-4-Turbo-equivalent
                inference tokens, the commodity unit for AI compute.
                {latest?.methodology?.aa_version && (
                  <>
                    {" "}Basket: cheapest qualifying model per provider, eligibility set relative to the scored-model
                    population (top 40%), based on Artificial Analysis {latest.methodology.aa_version}.
                  </>
                )}
              </p>
              <Link href="/methodology" style={{ fontSize: "13px", fontWeight: 500, color: "#C4A038" }}>
                → Read methodology
              </Link>
            </div>
          </div>

          {/* Sparkline chart */}
          <div style={{ padding: "26px 30px 24px", display: "flex", flexDirection: "column", gap: "12px" }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: "12px",
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
                <span style={{ fontFamily: "Inter, sans-serif", fontSize: "11px", color: "#5f5f5f", marginLeft: "4px" }}>
                  {sparkVals.length}-day spot
                </span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <span style={{ fontFamily: "Inter, sans-serif", fontSize: "11px", color: "#5f5f5f" }}>
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
                aria-label="30-day Standard Inference Token price history"
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
                {eraBreaks.map((b, i) => (
                  <g key={`era-${i}`}>
                    <line
                      x1={b.x}
                      y1={15}
                      x2={b.x}
                      y2={248}
                      stroke="#5f5f5f"
                      strokeWidth="1"
                      strokeDasharray="3 3"
                    />
                    <text
                      x={b.x + 4}
                      y={26}
                      fill="#8a8a8a"
                      fontSize="10"
                      fontFamily="Inter, sans-serif"
                    >
                      {b.label} ↻
                    </text>
                  </g>
                ))}
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
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: "14px",
                paddingTop: "10px",
                borderTop: "1px solid #222",
                flexWrap: "wrap",
              }}
            >
              <span style={{ fontSize: "11.5px", color: "#8a8a8a", display: "flex", alignItems: "center", gap: "7px", whiteSpace: "nowrap" }}>
                <span style={{ display: "inline-block", width: "10px", height: 1, background: "#5c5c5c" }} />
                era break — basket reconstitution
              </span>
              <span style={{ fontSize: "11.5px", color: "#8a8a8a", display: "flex", gap: "7px", whiteSpace: "nowrap" }}>
                <span style={{ color: "#22c55e" }}>green = price down</span>
                <span style={{ color: "#3a3a3a" }}>/</span>
                <span style={{ color: "#ef4444" }}>red = price up</span>
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* ============ BLOCK 4 — CATALOGUE PREVIEW ============ */}
      <section style={{ maxWidth: "1320px", margin: "0 auto", padding: "72px 28px 0" }}>
        <div
          style={{
            display: "flex",
            alignItems: "flex-end",
            justifyContent: "space-between",
            gap: "28px",
            flexWrap: "wrap",
            marginBottom: "16px",
          }}
        >
          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            <h2 style={{ margin: 0, fontSize: "28px", fontWeight: 600, letterSpacing: "-0.028em", color: "#f2f2f2" }}>
              Quality-adjusted price across {totalCount.toLocaleString()} models
            </h2>
            <p style={{ margin: 0, maxWidth: "56em", fontSize: "13.5px", lineHeight: 1.5, color: "#8a8a8a" }}>
              Grouped by quality tier, ranked within tier by Cost/IQ — verified price per million tokens per unit of AA
              Intelligence Index. Input, output, and blended prices per model.
            </p>
          </div>
          <Link
            href="/models"
            style={{ fontSize: "13px", fontWeight: 500, color: "#C4A038", whiteSpace: "nowrap", paddingBottom: "4px" }}
          >
            Full rankings →
          </Link>
        </div>
        {preview.length > 0 && (
          <div>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "40px minmax(160px, 1.5fr) minmax(110px, 1fr) minmax(0, 200px) 88px 88px 92px 84px",
                alignItems: "center",
                padding: "0 0 8px",
                borderBottom: "1px solid #2a2a2a",
              }}
            >
              {[
                ["#", "left"],
                ["Model", "left"],
                ["Creator", "left"],
                ["Basis", "left"],
                ["Input $/M", "right"],
                ["Output $/M", "right"],
                ["Blended $/M", "right"],
                ["Cost / IQ", "right"],
              ].map(([label, align]) => (
                <span
                  key={label}
                  style={{
                    fontFamily: "var(--font-jetbrains-mono), monospace",
                    fontSize: "10px",
                    fontWeight: 500,
                    letterSpacing: "0.11em",
                    textTransform: "uppercase",
                    color: "#8a8a8a",
                    padding: "0 8px",
                    textAlign: align as "left" | "right",
                  }}
                >
                  {label}
                </span>
              ))}
            </div>
            {preview.map((m, i) => (
              <Link
                key={m.model_id}
                href={`/models/${m.model_id}`}
                style={{
                  display: "grid",
                  gridTemplateColumns: "40px minmax(160px, 1.5fr) minmax(110px, 1fr) minmax(0, 200px) 88px 88px 92px 84px",
                  alignItems: "center",
                  height: "42px",
                  borderBottom: "1px solid #18181c",
                  textDecoration: "none",
                }}
              >
                <span style={{ padding: "0 8px", fontFamily: "var(--font-jetbrains-mono), monospace", fontSize: "12.5px", color: i === 0 ? "#f2f2f2" : "#8a8a8a" }}>
                  {["🥇", "🥈", "🥉"][i]}
                </span>
                <span style={{ padding: "0 8px", fontSize: "13.5px", fontWeight: 500, color: "#f2f2f2", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                  {m.name}
                </span>
                <span style={{ padding: "0 8px", display: "flex", alignItems: "center", gap: "7px", minWidth: 0 }}>
                  <span style={{ fontSize: "12.5px", color: "#8a8a8a", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                    {m.provider}
                  </span>
                  {m.creator_country && (
                    <span
                      title={m.creator_country.toUpperCase()}
                      style={{
                        fontFamily: "var(--font-jetbrains-mono), monospace",
                        fontSize: "9.5px",
                        fontWeight: 500,
                        padding: "1px 5px",
                        background: "#131316",
                        border: "1px solid #2a2a2a",
                        color: "#8a8a8a",
                        flexShrink: 0,
                      }}
                    >
                      {m.creator_country.toUpperCase()}
                    </span>
                  )}
                </span>
                <span style={{ padding: "0 8px", display: "flex", gap: "5px" }}>
                  <span
                    title="Price verified hourly from provider APIs"
                    style={{ fontSize: "10.5px", padding: "2px 7px", background: "rgba(196,160,56,0.08)", border: "1px solid rgba(196,160,56,0.35)", color: "#C4A038" }}
                  >
                    Price: verified
                  </span>
                </span>
                <span style={{ padding: "0 8px", textAlign: "right", fontFamily: "var(--font-jetbrains-mono), monospace", fontSize: "12.5px", color: "#c9c9c9", fontVariantNumeric: "tabular-nums" }}>
                  ${m.input_price_per_m.toFixed(2)}
                </span>
                <span style={{ padding: "0 8px", textAlign: "right", fontFamily: "var(--font-jetbrains-mono), monospace", fontSize: "12.5px", color: "#c9c9c9", fontVariantNumeric: "tabular-nums" }}>
                  ${m.output_price_per_m.toFixed(2)}
                </span>
                <span style={{ padding: "0 8px", textAlign: "right", fontFamily: "var(--font-jetbrains-mono), monospace", fontSize: "12.5px", color: "#f2f2f2", fontVariantNumeric: "tabular-nums" }}>
                  ${m.blended_price_per_m.toFixed(2)}
                </span>
                <span style={{ padding: "0 8px", textAlign: "right", fontFamily: "var(--font-jetbrains-mono), monospace", fontSize: "12.5px", color: "#C4A038", fontVariantNumeric: "tabular-nums" }}>
                  {m.sit_adjusted_price?.toFixed(2)}
                </span>
              </Link>
            ))}
            <p style={{ margin: "14px 0 0", fontSize: "12px", lineHeight: 1.6, color: "#6a6a6a" }}>
              Quality here means intelligence only. Latency and uptime verification is in development; neither is scored
              on this page.
            </p>
          </div>
        )}
      </section>

      {/* API signup */}
      <section
        id="api"
        style={{
          maxWidth: "1320px",
          margin: "0 auto",
          padding: "56px 28px 44px",
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

      <Footer models={totalCount} providers={providerCount} updatedAt={lastUpdated} />
    </>
  );
}
