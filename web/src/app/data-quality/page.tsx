import { Header, Footer } from "@/components/Header";
import { CURRENT_MODEL_COUNT, CURRENT_PROVIDER_COUNT } from "@/lib/counts";
import type { Metadata } from "next";
import DataQualityClient from "./DataQualityClient";

export const metadata: Metadata = {
  title: "Data Quality - InferenceIndexer.ai",
  description:
    "Live data quality dashboard. See the last fetch time, model count, and staleness status for every data source we pull from. Transparent and verifiable.",
};

export default function DataQualityPage() {
  return (
    <>
      <Header />
      <main
        style={{
          minHeight: "100vh",
          background: "#0a0a0a",
          color: "#e5e5e5",
          fontFamily: "Inter, system-ui, sans-serif",
        }}
      >
        <div style={{ maxWidth: "1100px", margin: "0 auto", padding: "48px 28px 64px" }}>
          <h1 style={{ fontSize: "28px", fontWeight: 700, color: "#ffffff", marginBottom: "8px" }}>
            Data Quality
          </h1>
          <p style={{ fontSize: "15px", color: "#8a8a8a", marginBottom: "40px", lineHeight: 1.6 }}>
            Live status of every data source we pull from. Updated every minute.
            If a source goes stale or a price anomaly is detected, it shows here.
          </p>
          <DataQualityClient />
        </div>
      </main>
      <Footer models={CURRENT_MODEL_COUNT} providers={CURRENT_PROVIDER_COUNT} />
    </>
  );
}
