import type { Metadata } from "next";
import { Suspense } from "react";
import { getEmbeddings, type EmbeddingModel } from "@/lib/api";
import { Header, Footer } from "@/components/Header";
import EmbeddingTable from "@/components/EmbeddingTable";

export const revalidate = 60;

export const metadata: Metadata = {
  title: "Embedding Model Pricing - Live API Costs | InferenceIndexer.ai",
  description:
    "Live pricing for AI embedding models. Compare per-million-token costs across OpenAI, Cohere, Voyage AI, Jina, Nomic, and Google. Prices per million tokens.",
  alternates: { canonical: "https://www.inferenceindexer.ai/embeddings" },
};

export default async function EmbeddingsPage() {
  let models: EmbeddingModel[] = [];
  let totalCount = 0;

  try {
    const data = await getEmbeddings("price");
    models = data.models;
    totalCount = data.count;
  } catch {
    models = [];
    totalCount = 0;
  }

  return (
    <div style={{ minHeight: "100vh", background: "#0a0a0a", color: "#e5e5e5", display: "flex", flexDirection: "column" }}>
      <Header activePage="" />

      <main style={{ flex: 1, width: "100%" }}>
        {/* Heading section */}
        <section style={{ maxWidth: "1320px", margin: "0 auto", padding: "40px 28px 24px" }}>
          <h1 style={{ fontSize: "28px", fontWeight: 700, color: "#f2f2f2", margin: "0 0 8px" }}>
            Embedding Models
          </h1>
          <p style={{ fontSize: "14px", color: "#8a8a8a", margin: 0, maxWidth: "560px", lineHeight: 1.6 }}>
            Live pricing for AI embedding models. Prices per million tokens.
          </p>
        </section>

        {/* Embedding table */}
        {models.length > 0 ? (
          <Suspense fallback={null}>
            <EmbeddingTable models={models} totalCount={totalCount} />
          </Suspense>
        ) : (
          <section style={{ maxWidth: "1320px", margin: "0 auto", padding: "40px 28px" }}>
            <p style={{ fontSize: "14px", color: "#6a6a6a" }}>
              Unable to load embedding model data. Please try again later.
            </p>
          </section>
        )}

        {/* Bottom spacing */}
        <section style={{ maxWidth: "1320px", margin: "0 auto", padding: "20px 28px 40px" }} />
      </main>

      <Footer />
    </div>
  );
}
