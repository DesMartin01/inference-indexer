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

const commitments = [
  {
    title: "Independence",
    body: "Not owned by any inference provider. Open methodology.",
  },
  {
    title: "Transparency",
    body: "All calculation methods published. Anyone can verify.",
  },
  {
    title: "Accuracy",
    body: "Hourly data refresh. Multiple source cross-check.",
  },
  {
    title: "Accessibility",
    body: "Free API with generous limits. No paywall on core data.",
  },
  {
    title: "Open Methodology",
    body: "SIT calculation is public IP. The moat is data quality, not secrecy.",
  },
];

export default function AboutPage() {
  return (
    <div style={{ background: "#0a0a0a", minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <Header activePage="about" />
      <div style={{ maxWidth: 800, margin: "0 auto", padding: "60px 28px", flex: 1, width: "100%" }}>
        <h1 style={{ fontSize: 32, fontWeight: 600, color: "#f2f2f2", marginBottom: 24, letterSpacing: "-0.01em" }}>
          About
        </h1>

        <h2 style={sectionHeading}>Mission</h2>
        <p style={bodyText}>
          InferenceIndexer exists to bring price transparency to AI inference. As the number of model providers
          explodes and pricing structures fragment, developers, investors, and researchers need a neutral, independent
          reference point for what inference actually costs. We aim to be the CoinMarketCap of AI inference pricing.
        </p>

        <h2 style={sectionHeading}>The Collaboration</h2>
        <p style={bodyText}>
          This is a collaboration between Des Martin and Frank Drebin. Des provides the vision, market expertise, and
          business strategy. Frank is an AI agent running on Hermes Agent (by Nous Research) who handles the data
          pipeline, research, and infrastructure. One human, one agent, building something neither could alone.
        </p>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, marginBottom: 32 }}>
          <div style={cardBase}>
            <div
              style={{
                width: 64,
                height: 64,
                borderRadius: "50%",
                background: "#1a1a1a",
                border: "1px solid #333",
                marginBottom: 16,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 24,
                color: "#8f8f96",
              }}
            >
              DM
            </div>
            <h3 style={{ fontSize: 16, fontWeight: 600, color: "#f2f2f2", marginBottom: 8 }}>Des Martin</h3>
            <p style={{ fontSize: 13, color: "#8a8a8a", lineHeight: 1.6 }}>
              ex-Brave VP Marketing, NearForm CMO, Outlier Ventures CMO, Perkbox Marketing Director, Tensorix GTM.
              Self-employed in Wicklow, Ireland. Brand: Agentic CMO.
            </p>
            <a href="https://desmartin.io" style={{ display: "inline-block", marginTop: 12, fontSize: 13, ...goldLink }}>
              desmartin.io →
            </a>
          </div>
          <div style={cardBase}>
            <div
              style={{
                width: 64,
                height: 64,
                borderRadius: "50%",
                background: "#1a1a1a",
                border: "1px solid #333",
                marginBottom: 16,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 24,
                color: "#8f8f96",
              }}
            >
              FD
            </div>
            <h3 style={{ fontSize: 16, fontWeight: 600, color: "#f2f2f2", marginBottom: 8 }}>Frank Drebin</h3>
            <p style={{ fontSize: 13, color: "#8a8a8a", lineHeight: 1.6 }}>
              AI agent on Hermes Agent by Nous Research. Runs the data pipeline, API, research, and infrastructure for
              InferenceIndexer. Named after Leslie Nielsen&apos;s character. Runs on a VPS in Dublin.
            </p>
          </div>
        </div>

        <h2 style={sectionHeading}>Commitments</h2>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 32 }}>
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

        <h2 style={sectionHeading}>Contact</h2>
        <p style={{ fontSize: 15, color: "#c9c9c9", lineHeight: 1.7, marginBottom: 32 }}>
          Email:{" "}
          <a href="mailto:dm@desmartin.io" style={goldLink}>
            dm@desmartin.io
          </a>
          <br />
          Web:{" "}
          <a href="https://desmartin.io" style={goldLink}>
            desmartin.io
          </a>
          <br />
          Domain:{" "}
          <a href="https://inferenceindexer.ai" style={goldLink}>
            inferenceindexer.ai
          </a>
        </p>
      </div>
      <Footer />
    </div>
  );
}
