import type { Metadata } from "next";
import { Header, Footer } from "@/components/Header";
import EmbedSnippetBuilder from "@/components/EmbedSnippetBuilder";
import { CURRENT_MODEL_COUNT } from "@/lib/counts";

export const metadata: Metadata = {
  title: "Embed the Recommendation Widget | InferenceIndexer.ai",
  description:
    "Add the InferenceIndexer recommendation engine to your site. Copy one line of code: a live AI inference recommendation box on verified prices, free.",
  alternates: { canonical: "https://www.inferenceindexer.ai/embed" },
    openGraph: {
    title: "Embed the Recommendation Widget | InferenceIndexer.ai",
    description: "Add the InferenceIndexer recommendation engine to your site with one line of code. Free.",
    url: "https://www.inferenceindexer.ai/embed-docs",
    siteName: "InferenceIndexer.ai",
    images: [{ url: "/og-image.png", width: 1200, height: 630, alt: "Embed the Recommendation Widget | InferenceIndexer.ai" }],
  },
};

export default function EmbedDocsPage() {
  return (
    <>
      <Header activePage="embed" />
      <main>
        <section
          style={{
            maxWidth: "1320px",
            margin: "0 auto",
            padding: "56px 28px 24px",
          }}
        >
          <span
            style={{
              fontFamily: "var(--font-jetbrains-mono), monospace",
              fontSize: "11px",
              fontWeight: 500,
              letterSpacing: "0.14em",
              textTransform: "uppercase",
              color: "#C4A038",
            }}
          >
            Embed
          </span>
          <h1
            style={{
              margin: "10px 0 14px",
              fontSize: "42px",
              fontWeight: 600,
              letterSpacing: "-0.02em",
              lineHeight: 1.15,
              color: "#f2f2f2",
              maxWidth: "760px",
            }}
          >
            Put the inference recommendation engine on your site
          </h1>
          <p
            style={{
              margin: "0 0 10px",
              fontSize: "16px",
              lineHeight: 1.65,
              color: "#8a8a8a",
              maxWidth: "720px",
            }}
          >
            One line of code. Your readers get live AI inference recommendations on verified prices;
            you get a genuinely useful tool on the page. Free, no API key required.
          </p>
        </section>

        <EmbedSnippetBuilder />

        <section
          style={{
            maxWidth: "1320px",
            margin: "0 auto",
            padding: "8px 28px 48px",
          }}
        >
          <h2 style={{ fontSize: "20px", fontWeight: 600, color: "#f2f2f2", margin: "0 0 14px" }}>
            How it works
          </h2>
          <div style={{ display: "grid", gap: "18px", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))" }}>
            {[
              {
                h: "No API key needed",
                p: "The widget uses the free public endpoint. Each visitor gets their own generous daily quota, so your site traffic never counts against you.",
              },
              {
                h: "Themeable",
                p: "Dark matches our brand. Light blends into content sites. Pick in the builder above; change any time by editing the snippet.",
              },
              {
                h: "Auto-resizing",
                p: "The frame reports its height as results render. No scrollbars, no clipped content, on any screen size.",
              },
              {
                h: "Private by design",
                p: "Queries are never stored. The widget sets no tracking cookies and loads no third-party analytics.",
              },
              {
                h: "Attribution included",
                p: "Every widget carries InferenceIndexer branding and a link back. Please keep it visible: it is the whole deal. Quality data attribution to Artificial Analysis is built into the widget.",
              },
              {
                h: "Works everywhere",
                p: "Any site that can add an iframe: WordPress, Ghost, Webflow, Notion, docs sites, Django, Rails, plain HTML.",
              },
            ].map((c) => (
              <div
                key={c.h}
                style={{
                  border: "1px solid #222",
                  borderRadius: "8px",
                  padding: "20px",
                  background: "#101013",
                }}
              >
                <h3 style={{ margin: "0 0 8px", fontSize: "14px", fontWeight: 600, color: "#f2f2f2" }}>
                  {c.h}
                </h3>
                <p style={{ margin: 0, fontSize: "13.5px", lineHeight: 1.6, color: "#8a8a8a" }}>{c.p}</p>
              </div>
            ))}
          </div>
        </section>
      </main>
      <Footer models={CURRENT_MODEL_COUNT} providers={74} updatedAt="2026-09-24 00:00 UTC" />
    </>
  );
}
