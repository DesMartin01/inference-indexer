import type { Metadata } from "next";
import EnginePanel from "@/components/EnginePanel";
import EmbedFrame from "@/components/EmbedFrame";
import { getModelCount } from "@/lib/api";
import { CURRENT_MODEL_COUNT } from "@/lib/counts";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "InferenceIndexer Recommendation Widget",
  robots: { index: false, follow: false },
};

export default async function EmbedPage({
  searchParams,
}: {
  searchParams: Promise<{ theme?: string; default?: string }>;
}) {
  const params = await searchParams;
  const theme = params.theme === "light" ? "light" : "dark";
  const PRESETS: Record<string, string> = {
    coding: "Best model for coding agents priced under $2 per million tokens",
    "zdr-eu": "Zero data retention providers in the EU",
  };
  const initialQuery = params.default ? PRESETS[params.default] : undefined;
  const total = (await getModelCount().catch(() => 0)) || CURRENT_MODEL_COUNT;

  return (
    <div
      className={theme === "light" ? "ep-light" : ""}
      style={{
        minHeight: "100vh",
        background: theme === "light" ? "#ffffff" : "#0a0a0a",
      }}
    >
      <EmbedFrame />
      <EnginePanel totalModels={total} initialQuery={initialQuery} showEmbedLink={false} />
      <div
        style={{
          padding: "4px 28px 22px",
          fontSize: "12px",
          color: "var(--ep-faint)",
        }}
      >
        Powered by{" "}
        <a
          href="https://www.inferenceindexer.ai/?utm_source=embed"
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: "#C4A038", textDecoration: "none", fontWeight: 500 }}
        >
          InferenceIndexer
        </a>{" "}
        : AI inference recommendations on verified prices.
      </div>
    </div>
  );
}
