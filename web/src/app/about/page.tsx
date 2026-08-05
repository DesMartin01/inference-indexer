import { Header, Footer } from "@/components/Header";
import type { CSSProperties } from "react";

export const metadata = {
  title: "About - Independent AI Inference Price Index | InferenceIndexer.ai",
  description:
    "InferenceIndexer is an independent price reporting agency for AI inference, built by Des Martin and Frank Drebin. Not owned by any provider. Open methodology. Free API access.",
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
  { id: "commitment", label: "Commitment" },
];

const commitments = [
  {
    title: "Independence",
    body: "InferenceIndexer does not provide inference services, route API calls, or take positions in any inference derivatives market. We are a price reporting agency, not a market participant.",
  },
  {
    title: "Transparency",
    body: "The full SIT methodology is published. Data sources are public and verifiable. Every index calculation is reproducible from stored raw data.",
  },
  {
    title: "Accuracy",
    body: "Prices are fetched hourly from multiple sources. Anomaly detection flags any price movement over 50% in a single hour for manual review.",
  },
  {
    title: "Accessibility",
    body: "The index is free to view. The API is free for 1,000 requests per day. Historical data is accessible with a free API key.",
  },
  {
    title: "Open methodology",
    body: "Any change to the SIT methodology triggers a 14-day public comment period. All changes are versioned and documented.",
  },
];

export default function AboutPage() {
  return (
    <div style={{ background: "#0a0a0a", minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <Header activePage="about" />
      <div style={{ maxWidth: 1320, width: "100%", margin: "0 auto", padding: "44px 28px 0", flex: 1, display: "flex", gap: 48 }}>
        {/* Main content */}
        <div style={{ maxWidth: 800, flex: 1 }}>
          <h1 style={{ fontSize: 28, fontWeight: 700, color: "#f2f2f2", marginBottom: 8, letterSpacing: "-0.01em" }}>
            About InferenceIndexer
          </h1>
          <p style={{ fontSize: 14, color: "#8a8a8a", marginBottom: 40 }}>
            An independent price reporting agency for AI inference.
          </p>

          {/* Mission */}
          <div id="mission" style={{ marginBottom: 40 }}>
            <h2 style={sectionHeading}>Mission</h2>
            <p style={bodyText}>
              InferenceIndexer exists to bring price transparency to AI inference. As the number of model providers
              explodes and pricing structures fragment, developers, investors, and enterprises need a neutral, independent
              reference point. The Standard Inference Token (SIT) is that reference: a single, standardized unit that
              makes inference pricing comparable across 300+ models and 40+ providers.
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
              marketing executive who understands the inference market from the inside, and a CTO that handles the data
              pipeline, research, and technical execution.
            </p>
            <p style={bodyText}>
              Des sets the vision, defines the methodology, and owns the commercial strategy. Frank runs the data
              collection, market research, and infrastructure. One human, one agent, one product.
            </p>
          </div>

          {/* Team */}
          <div id="team" style={{ marginBottom: 40 }}>
            <h2 style={sectionHeading}>The Team</h2>
            <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 20, marginBottom: 8 }}>
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
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 4 }}>
                  <h3 style={{ fontSize: 16, fontWeight: 600, color: "#f2f2f2", margin: 0 }}>Des Martin</h3>
                  <span style={{ fontSize: 12, color: "#5f5f5f" }}>Wicklow, Ireland</span>
                </div>
                <p style={{ fontSize: 12, color: "#C4A038", marginBottom: 12 }}>
                  Vision, methodology, commercial strategy
                </p>
                <p style={{ fontSize: 13, color: "#8a8a8a", lineHeight: 1.6, marginBottom: 12 }}>
                  Des Martin is a technology marketing executive based in Wicklow, Ireland. He has held senior marketing
                  roles at Brave (VP Marketing), NearForm (CMO), Outlier Ventures (CMO), Perkbox (Marketing Director),
                  and Tensorix (GTM).
                </p>
                <p style={{ fontSize: 13, color: "#8a8a8a", lineHeight: 1.6, marginBottom: 12 }}>
                  His career has sat at the intersection of emerging technology and go-to-market strategy: browser
                  privacy, enterprise software, venture capital, and now AI infrastructure. He has launched products,
                  built brands, and led growth for companies across crypto, AI, and developer tools.
                </p>
                <p style={{ fontSize: 13, color: "#8a8a8a", lineHeight: 1.6, marginBottom: 12 }}>
                  InferenceIndexer grew out of a simple observation: the AI inference market has no price index. Every
                  comparable commodity market - oil, crypto, cloud compute - has one. Inference doesn&apos;t. That gap
                  is the opportunity.
                </p>
                <a href="https://desmartin.io" style={{ display: "inline-block", fontSize: 13, ...goldLink }}>
                  Website: desmartin.io
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
                  }}
                >
                  <img
                    src="/images/frank-drebin.png"
                    alt="Frank Drebin"
                    style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
                  />
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 4 }}>
                  <h3 style={{ fontSize: 16, fontWeight: 600, color: "#f2f2f2", margin: 0 }}>Frank Drebin</h3>
                  <span style={{ fontSize: 12, color: "#5f5f5f" }}>VPS &middot; Dublin</span>
                </div>
                <p style={{ fontSize: 12, color: "#C4A038", marginBottom: 12 }}>
                  Data pipeline, research, infrastructure
                </p>
                <p style={{ fontSize: 13, color: "#8a8a8a", lineHeight: 1.6, marginBottom: 12 }}>
                  Frank handles the technical work on InferenceIndexer: data pipeline architecture, API integration,
                  market research, competitive analysis, and infrastructure management. He operates with persistent
                  memory across sessions, runs scheduled data collection jobs, and executes tasks autonomously.
                </p>
                <p style={{ fontSize: 13, color: "#8a8a8a", lineHeight: 1.6, marginBottom: 12 }}>
                  Frank is an exceptional AI Agent. He runs terminal commands, writes code, manages servers, and does
                  the heavy lifting on data collection and normalization. The SIT methodology, competitive landscape
                  research, and technical architecture were all produced through this collaboration.
                </p>
              </div>
            </div>
          </div>

          {/* Commitment */}
          <div id="commitment" style={{ marginBottom: 40 }}>
            <h2 style={sectionHeading}>Commitment</h2>
            <p style={bodyText}>
              We are committed to building the most comprehensive, transparent, and independent price index for AI
              inference. Specifically:
            </p>
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
