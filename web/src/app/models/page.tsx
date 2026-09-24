import { Suspense } from "react";
import type { Metadata } from "next";
import {
  getModels,
  getModelCount,
} from "@/lib/api";
import { Header, Footer } from "@/components/Header";
import ModelTable from "@/components/ModelTable";
import { CURRENT_MODEL_COUNT, CURRENT_PROVIDER_COUNT } from "@/lib/counts";

export const revalidate = 60;

export async function generateMetadata(): Promise<Metadata> {
  const count = (await getModelCount().catch(() => 0)) || CURRENT_MODEL_COUNT;
  return {
    title: `Quality-Adjusted Model Rankings - ${count} Models | InferenceIndexer.ai`,
    description: `Full rankings across ${count} AI inference models: blended prices, Cost/IQ quality-adjusted value, AA intelligence scores. Verified hourly from provider APIs.`,
    alternates: { canonical: "https://www.inferenceindexer.ai/models" },
  };
}

export default async function ModelsPage() {
  const [modelsData, apiModelCount] = await Promise.all([
    getModels(undefined, undefined, 500).catch(() => null),
    getModelCount().catch(() => null),
  ]);
  const models = modelsData?.models ?? [];
  const totalCount =
    apiModelCount ?? modelsData?.count ?? modelsData?.returned ?? models.length ?? CURRENT_MODEL_COUNT;

  return (
    <>
      <Header activePage="models" />
      <section style={{ maxWidth: "1320px", margin: "0 auto", padding: "34px 28px 0" }}>
        <h1 style={{ fontSize: "30px", fontWeight: 600, letterSpacing: "-0.028em", color: "#f2f2f2", margin: 0 }}>
          Quality-adjusted price across {totalCount} models
        </h1>
        <p style={{ margin: "8px 0 0", maxWidth: "56em", fontSize: "14px", lineHeight: 1.5, color: "#8a8a8a" }}>
          Grouped by quality tier, ranked within tier by Cost/IQ: verified price per million tokens per unit of
          AA Intelligence Index. Input, output, and blended prices shown per model.{" "}
          <a href="/api-docs" style={{ color: "#C4A038" }}>
            Full data via the API
          </a>
          .
        </p>
        <p style={{ margin: "6px 0 0", fontSize: "12.5px", lineHeight: 1.6, color: "#6a6a6a" }}>
          Quality here means intelligence only. Latency and uptime verification is in development; neither is scored on
          this page. Green means price down (cheaper), red means price up.
        </p>
      </section>
      {models.length > 0 && (
        <Suspense fallback={null}>
          <ModelTable models={models} totalCount={totalCount} />
        </Suspense>
      )}
      <p style={{ maxWidth: "1320px", margin: "0 auto", padding: "0 28px 8px", fontSize: "12px", color: "#6a6a6a" }}>
        Quality scores: source Artificial Analysis (artificialanalysis.ai). Tier groupings and rankings are
        InferenceIndexer&apos;s own; not endorsed by Artificial Analysis.
      </p>
      <section
        style={{
          maxWidth: "1320px",
          margin: "0 auto",
          padding: "40px 28px 44px",
          textAlign: "center",
        }}
      >
        <span style={{ fontSize: "14px", color: "#8a8a8a" }}>
          Get the data via API →{" "}
          <a href="/api-docs" style={{ color: "#C4A038" }}>
            View API documentation
          </a>
        </span>
      </section>
      <Footer models={totalCount} providers={CURRENT_PROVIDER_COUNT} />
    </>
  );
}
