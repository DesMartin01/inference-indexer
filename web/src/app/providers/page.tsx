import Link from "next/link";
import { getProviders, type ProviderSummary } from "@/lib/api";
import ProvidersTable from "@/components/ProvidersTable";
import { Header, Footer } from "@/components/Header";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "AI Inference Providers - Compare Pricing | InferenceIndexer.ai",
  description: "Compare inference pricing across 74 AI model providers. Model counts, price ranges, ZDR and EU sovereign status.",
  alternates: { canonical: "https://www.inferenceindexer.ai/providers" },
};

export default async function ProvidersPage() {
  let providers: ProviderSummary[] = [];
  try {
    const data = await getProviders();
    providers = data.providers;
  } catch {
    providers = [];
  }

  return (
    <div style={{ minHeight: "100vh", background: "#0a0a0a", color: "#e5e5e5" }}>
      <Header activePage="" />
      <main style={{ maxWidth: 1200, margin: "0 auto", padding: "24px 20px 60px" }}>
        <h1 style={{ fontSize: 28, fontWeight: 700, color: "#f2f2f2", marginBottom: 8 }}>
          Inference Providers
        </h1>
        <p style={{ fontSize: 15, color: "#8a8a8a", marginBottom: 32 }}>
          {providers.length} providers tracked across {providers.reduce((a, p) => a + p.model_count, 0)} models
        </p>

        <ProvidersTable providers={providers} />

        {providers.some((p) => p.show_in_list && p.avg_price == null) && (
          <div
            style={{
              marginTop: 24,
              padding: "16px 20px",
              border: "1px solid #262626",
              borderLeft: "3px solid #C4A038",
              borderRadius: 6,
              background: "#111112",
              fontSize: 13,
              color: "#c9c9c9",
              lineHeight: 1.6,
            }}
          >
            <strong style={{ color: "#f2f2f2" }}>Why some providers show N/A pricing.</strong>{" "}
            A few providers, such as NVIDIA, publish their model catalog but
            do not expose list prices through a public API. Their models are
            tracked and searchable, but we show&nbsp;N/A instead of pricing we
            cannot verify. Where the same model is priced by another provider,
            it still appears with that price on the model page.
          </div>
        )}

        <div
          style={{
            marginTop: 32,
            padding: "18px 24px",
            border: "1px solid #262626",
            borderRadius: 8,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: 12,
            background: "#111112",
          }}
        >
          <span style={{ fontSize: 14, color: "#c9c9c9" }}>
            Are you an inference provider?
          </span>
          <Link
            href="/providers/submit"
            style={{
              fontSize: 13.5,
              fontWeight: 600,
              color: "#C4A038",
              padding: "9px 18px",
              border: "1px solid #C4A038",
              borderRadius: 6,
              textDecoration: "none",
            }}
          >
            Submit your models here
          </Link>
        </div>
      </main>
      <Footer providers={74} updatedAt="" />
    </div>
  );
}
