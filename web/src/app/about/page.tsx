import { Header, Footer } from "@/components/Header";

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

export default function AboutPage() {
  return (
    <div style={{ background: "#0a0a0a", minHeight: "100vh" }}>
      <Header activePage="about" />
      <div style={{ maxWidth: 700, margin: "0 auto", padding: "60px 28px" }}>
        <h1 style={{ fontSize: 32, fontWeight: 600, color: "#f2f2f2", marginBottom: 24 }}>About</h1>

        <h2 style={{ fontSize: 18, fontWeight: 600, color: "#C4A038", marginBottom: 12 }}>Mission</h2>
        <p style={{ fontSize: 15, color: "#c9c9c9", lineHeight: 1.7, marginBottom: 24 }}>
          InferenceIndexer exists to bring price transparency to AI inference. As the number of model providers explodes and pricing structures fragment, developers, investors, and researchers need a neutral, independent reference point for what inference actually costs. We aim to be the CoinMarketCap of AI inference pricing.
        </p>

        <h2 style={{ fontSize: 18, fontWeight: 600, color: "#C4A038", marginBottom: 12 }}>The Collaboration</h2>
        <p style={{ fontSize: 15, color: "#c9c9c9", lineHeight: 1.7, marginBottom: 24 }}>
          This is a collaboration between Des Martin and Frank Drebin. Des provides the vision, market expertise, and business strategy. Frank is an AI agent running on Hermes Agent (by Nous Research) who handles the data pipeline, research, and infrastructure. One human, one agent, building something neither could alone.
        </p>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, marginBottom: 32 }}>
          <div style={{ background: "#16161a", border: "1px solid #2a2a2a", borderRadius: 8, padding: 24 }}>
            <div style={{ width: 64, height: 64, borderRadius: "50%", background: "#1a1a1a", border: "1px solid #333", marginBottom: 16, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 24, color: "#8f8f96" }}>DM</div>
            <h3 style={{ fontSize: 16, fontWeight: 600, color: "#f2f2f2", marginBottom: 8 }}>Des Martin</h3>
            <p style={{ fontSize: 13, color: "#8a8a8a", lineHeight: 1.6 }}>
              ex-Brave VP Marketing, NearForm CMO, Outlier Ventures CMO, Perkbox Marketing Director, Tensorix GTM. Self-employed in Wicklow, Ireland. Brand: Agentic CMO.
            </p>
            <a href="https://desmartin.io" style={{ display: "inline-block", marginTop: 12, fontSize: 13, color: "#C4A038", textDecoration: "none" }}>desmartin.io →</a>
          </div>
          <div style={{ background: "#16161a", border: "1px solid #2a2a2a", borderRadius: 8, padding: 24 }}>
            <div style={{ width: 64, height: 64, borderRadius: "50%", background: "#1a1a1a", border: "1px solid #333", marginBottom: 16, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 24, color: "#8f8f96" }}>FD</div>
            <h3 style={{ fontSize: 16, fontWeight: 600, color: "#f2f2f2", marginBottom: 8 }}>Frank Drebin</h3>
            <p style={{ fontSize: 13, color: "#8a8a8a", lineHeight: 1.6 }}>
              AI agent on Hermes Agent by Nous Research. Runs the data pipeline, API, research, and infrastructure for InferenceIndexer. Named after Leslie Nielsen&apos;s character. Runs on a VPS in Dublin.
            </p>
          </div>
        </div>

        <h2 style={{ fontSize: 18, fontWeight: 600, color: "#C4A038", marginBottom: 12 }}>Commitment</h2>
        <ul style={{ paddingLeft: 20, marginBottom: 32 }}>
          <li style={{ fontSize: 14, color: "#c9c9c9", lineHeight: 1.8 }}><strong style={{ color: "#e5e5e5" }}>Independence.</strong> Not owned by any inference provider. Open methodology.</li>
          <li style={{ fontSize: 14, color: "#c9c9c9", lineHeight: 1.8 }}><strong style={{ color: "#e5e5e5" }}>Transparency.</strong> All calculation methods published. Anyone can verify.</li>
          <li style={{ fontSize: 14, color: "#c9c9c9", lineHeight: 1.8 }}><strong style={{ color: "#e5e5e5" }}>Accuracy.</strong> Hourly data refresh. Multiple source cross-check.</li>
          <li style={{ fontSize: 14, color: "#c9c9c9", lineHeight: 1.8 }}><strong style={{ color: "#e5e5e5" }}>Accessibility.</strong> Free API with generous limits. No paywall on core data.</li>
          <li style={{ fontSize: 14, color: "#c9c9c9", lineHeight: 1.8 }}><strong style={{ color: "#e5e5e5" }}>Open methodology.</strong> SIT calculation is public IP. The moat is data quality, not secrecy.</li>
        </ul>

        <h2 style={{ fontSize: 18, fontWeight: 600, color: "#C4A038", marginBottom: 12 }}>Contact</h2>
        <p style={{ fontSize: 14, color: "#8a8a8a", lineHeight: 1.6 }}>
          Email: <a href="mailto:dm@desmartin.io" style={{ color: "#C4A038" }}>dm@desmartin.io</a><br />
          Web: <a href="https://desmartin.io" style={{ color: "#C4A038" }}>desmartin.io</a><br />
          Domain: <a href="https://inferenceindexer.ai" style={{ color: "#C4A038" }}>inferenceindexer.ai</a>
        </p>
      </div>
    </div>
  );
}
