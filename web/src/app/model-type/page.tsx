import Link from "next/link";
import type { Metadata } from "next";
import { Header, Footer } from "@/components/Header";

export const metadata: Metadata = {
  title: "Model Types - Embedding Models & More | InferenceIndexer.ai",
  description:
    "InferenceIndexer tracks pricing across multiple model types including embedding models. Browse all model type directories.",
  alternates: { canonical: "https://www.inferenceindexer.ai/model-type" },
};

export default function ModelTypePage() {
  return (
    <div style={{ minHeight: "100vh", background: "#0a0a0a", color: "#e5e5e5", display: "flex", flexDirection: "column" }}>
      <Header activePage="" />
      <main style={{ maxWidth: "1320px", margin: "0 auto", padding: "44px 28px 60px", width: "100%", flex: 1 }}>
        <h1 style={{ fontSize: "28px", fontWeight: 700, color: "#f2f2f2", margin: "0 0 8px" }}>
          Model Types
        </h1>
        <p style={{ fontSize: "14px", color: "#8a8a8a", margin: "0 0 36px", maxWidth: "560px", lineHeight: 1.6 }}>
          InferenceIndexer tracks pricing across multiple model types. Not all are displayed on the homepage.
        </p>

        {/* Cards grid */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
            gap: "16px",
            maxWidth: "600px",
          }}
        >
          <Link
            href="/embeddings"
            style={{
              display: "block",
              background: "#16161a",
              border: "1px solid #2a2a2a",
              borderRadius: "8px",
              padding: "24px 22px",
              textDecoration: "none",
              transition: "border-color 150ms, background 150ms",
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: "12px",
              }}
            >
              <div>
                <div style={{ fontSize: "16px", fontWeight: 600, color: "#f2f2f2", marginBottom: "6px" }}>
                  Embedding Models
                </div>
                <div style={{ fontSize: "12.5px", color: "#7a7a7a" }}>
                  Live pricing for text embedding APIs
                </div>
              </div>
              <span style={{ fontSize: "18px", color: "#C4A038", fontWeight: 500, whiteSpace: "nowrap" }}>
                →
              </span>
            </div>
          </Link>
        </div>
      </main>
      <Footer />
    </div>
  );
}
