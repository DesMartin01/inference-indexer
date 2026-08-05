import { Header, Footer } from "@/components/Header";
import type { CSSProperties } from "react";

export const metadata = {
  title: "About - Independent AI Inference Price Index | InferenceIndexer.ai",
  description:
    "InferenceIndexer is an independent price index for AI inference, built by Des Martin and Frank Drebin. Not owned by any provider. Open methodology. Free API access.",
  alternates: { canonical: "https://inferenceindexer.ai/about" },
  openGraph: {
    title: "About InferenceIndexer.ai - Independent AI Pricing Index",
    description: "Independent AI inference price index. Built by Des Martin and Frank Drebin. Open methodology, free API.",
    url: "https://inferenceindexer.ai/about",
    siteName: "InferenceIndexer.ai",
  },
};

const sectionHeading: CSSProperties = {
  fontSize: 22,
  fontWeight: 700,
  color: "#f2f2f2",
  marginBottom: 12,
  marginTop: 0,
  letterSpacing: "-0.01em",
};

const bodyText: CSSProperties = {
  fontSize: 15,
  color: "#c9c9c9",
  lineHeight: 1.7,
  marginBottom: 24,
};

const cardBase: CSSProperties = {
  background: "#16161a",
  border: "1px solid #2a2a2a",
  borderRadius: 8,
  padding: 24,
};

const goldLink: CSSProperties = {
  color: "#C4A038",
  textDecoration: "none",
};

const tocItems = [
  { id: "mission", label: "Mission" },
  { id: "collaboration", label: "The Collaboration" },
  { id: "team", label: "The Team" },
  { id: "commitments", label: "Commitments" },
];

const commitments = [
  {
    title: "Independence",
    body: "Not owned by any inference provider. Open methodology. Not a market participant.",
  },
  {
    title: "Transparency",
    body: "All calculation methods published. Data sources are public and verifiable. Every index calculation is reproducible.",
  },
  {
    title: "Accuracy",
    body: "Prices fetched hourly from multiple sources. Anomaly detection flags any price movement over 50% in a single hour.",
  },
  {
    title: "Accessibility",
    body: "The index is free to view. The API is free for 1,000 requests per day. Historical data with a free API key.",
  },
  {
    title: "Open Methodology",
    body: "Any change to the SIT methodology triggers a 14-day public comment period. All changes are versioned and documented.",
  },
];

export default function AboutPage() {
  return (
    <div style={{ background: "#0a0a0a", minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <Header activePage="about" />
      <div style={{ maxWidth: 1100, margin: "0 auto", padding: "44px 28px 0", flex: 1, width: "100%", display: "flex", gap: 48 }}>
        {/* Main content */}
        <div style={{ maxWidth: 800, flex: 1 }}>
          <h1 style={{ fontSize: 28, fontWeight: 700, color: "#f2f2f2", marginBottom: 8, letterSpacing: "-0.01em" }}>
            About
          </h1>
          <p style={{ fontSize: 14, color: "#8a8a8a", marginBottom: 40 }}>
            The independent price index for AI inference. Built by one human and one agent.
          </p>

          {/* Mission */}
          <div id="mission" style={{ marginBottom: 40 }}>
            <h2 style={sectionHeading}>Mission</h2>
            <p style={bodyText}>
              InferenceIndexer exists to bring price transparency to AI inference. As the number of model providers
              explodes and pricing structures fragment, developers, investors, and enterprises need a neutral, independent
              reference point for what inference actually costs. The Standard Inference Token (SIT) is that reference: a
              single, standardized unit that makes inference pricing comparable across 300+ models and 40+ providers.
            </p>
            <p style={bodyText}>
              We are building the CoinMarketCap of AI inference. Not an exchange. Not an aggregator. Not a routing
              service. A price information layer that the entire industry can cite, trust, and build on.
            </p>
          </div>

          {/* Collaboration */}
          <div id="collaboration" style={{ marginBottom: 40 }}>
            <h2 style={sectionHeading}>The Collaboration</h2>
            <p style={bodyText}>
              InferenceIndexer.ai is a collaboration between two very different skill sets: a seasoned technology
              marketing executive who understands the inference market from the inside, and an AI agent that handles
              the data pipeline, research, and technical execution.
            </p>
            <p style={bodyText}>
              Des sets the vision, defines the methodology, and owns the commercial strategy. Frank runs the data
              collection, market research, and infrastructure. One human, one agent, one product.
            </p>
          </div>

          {/* Team */}
          <div id="team" style={{ marginBottom: 40 }}>
            <h2 style={sectionHeading}>The Team</h2>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 8 }}>
              {/* Des Martin */}
              <div style={cardBase}>
                <div
                  style={{
                    width: "100%",
                    aspectRatio: "1",
                    borderRadius: 8,
                    overflow: "hidden",
                    marginBottom: 16,
                    background: "#1a1a1a",
                    border: "1px solid #333",
                  }}
                >
                  <img
                    src="/images/des-martin.png"
                    alt="Des Martin"
                    style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
                  />
                </div>
                <h3 style={{ fontSize: 16, fontWeight: 600, color: "#f2f2f2", marginBottom: 8 }}>Des Martin</h3>
                <p style={{ fontSize: 13, color: "#8a8a8a", lineHeight: 1.6, marginBottom: 12 }}>
                  Technology marketing executive based in Wicklow, Ireland. ex-Brave VP Marketing, NearForm CMO,
                  Outlier Ventures CMO, Perkbox Marketing Director. Brand: Agentic CMO.
                </p>
                <a href="https://desmartin.io" style={{ display: "inline-block", fontSize: 13, ...goldLink }}>
                  desmartin.io &rarr;
                </a>
              </div>
              {/* Frank Drebin */}
              <div style={cardBase}>
                <div
                  style={{
                    width: "100%",
                    aspectRatio: "1",
                    borderRadius: 8,
                    overflow: "hidden",
                    marginBottom: 16,
                    background: "#1a1a1a",
                    border: "1px solid #333",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <span style={{ fontSize: 48, fontWeight: 700, color: "#8f8f96", fontFamily: "Inter, sans-serif" }}>
                    FD
                  </span>
                </div>
                <h3 style={{ fontSize: 16, fontWeight: 600, color: "#f2f2f2", marginBottom: 8 }}>Frank Drebin</h3>
                <p style={{ fontSize: 13, color: "#8a8a8a", lineHeight: 1.6, marginBottom: 12 }}>
                  AI agent on Hermes Agent by Nous Research. Runs the data pipeline, API, research, and infrastructure
                  for InferenceIndexer. Named after Leslie Nielsen&apos;s character. Runs on a VPS in Dublin.
                </p>
              </div>
            </div>
          </div>

          {/* Commitments */}
          <div id="commitments" style={{ marginBottom: 40 }}>
            <h2 style={sectionHeading}>Commitments</h2>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
              {commitments.map((c) => (
                <div key={c.title} style={cardBase}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
                    <span
                      style={{
                        width: 6,
                        height: 6,
                        borderRadius: "50%",
                        background: "#C4A038",
                        display: "block",
                        flexShrink: 0,
                      }}
                    />
                    <span style={{ fontSize: 15, fontWeight: 600, color: "#f2f2f2" }}>{c.title}</span>
                  </div>
                  <p style={{ fontSize: 14, color: "#c9c9c9", lineHeight: 1.7, margin: 0, paddingLeft: 16 }}>{c.body}</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Sticky TOC */}
        <aside
          style={{
            width: 200,
            flexShrink: 0,
            position: "sticky",
            top: 76,
            height: "fit-content",
          }}
        >
          <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.1em", color: "#5f5f5f", marginBottom: 14 }}>
            Contents
          </div>
          <nav style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {tocItems.map((item) => (
              <a
                key={item.id}
                href={`#${item.id}`}
                style={{
                  fontSize: 13,
                  color: "#8a8a8a",
                  textDecoration: "none",
                  fontFamily: "Inter, sans-serif",
                }}
              >
                {item.label}
              </a>
            ))}
          </nav>
        </aside>
      </div>
      <Footer />
    </div>
  );
}
