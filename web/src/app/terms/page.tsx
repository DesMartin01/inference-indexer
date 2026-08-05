import { Header, Footer } from "@/components/Header";
import type { CSSProperties } from "react";

export const metadata = {
  title: "Terms of Service - InferenceIndexer.ai",
  description:
    "Terms of Service for InferenceIndexer.ai. Acceptable use, API rate limits, data licensing, disclaimer of financial advice, and limitation of liability.",
  alternates: { canonical: "https://inferenceindexer.ai/terms" },
};

const h2: CSSProperties = {
  fontSize: 18,
  fontWeight: 600,
  color: "#f2f2f2",
  marginTop: 32,
  marginBottom: 10,
  letterSpacing: "-0.01em",
};

const p: CSSProperties = {
  fontSize: 14,
  color: "#c9c9c9",
  lineHeight: 1.7,
  marginBottom: 14,
};

const li: CSSProperties = {
  fontSize: 14,
  color: "#c9c9c9",
  lineHeight: 1.7,
  marginBottom: 6,
  marginLeft: 20,
};

const mutedMono = {
  fontFamily: "var(--font-jetbrains-mono), 'JetBrains Mono', monospace",
  fontSize: 12,
  color: "#8a8a8a",
} as CSSProperties;

export default function TermsPage() {
  return (
    <div style={{ background: "#0a0a0a", minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <Header activePage="" />
      <div style={{ maxWidth: 800, width: "100%", margin: "0 auto", padding: "44px 28px 60px", flex: 1 }}>
        <h1 style={{ fontSize: 28, fontWeight: 700, color: "#ffffff", marginBottom: 8, letterSpacing: "-0.01em" }}>
          Terms of Service
        </h1>
        <p style={{ ...mutedMono, marginBottom: 32 }}>
          Last updated: August 5, 2026
        </p>

        <p style={p}>
          These Terms of Service (&quot;Terms&quot;) govern your use of InferenceIndexer.ai (the &quot;Service&quot;),
          operated by InferenceIndexer.ai (&quot;we&quot;, &quot;us&quot;, or &quot;our&quot;). By accessing or using
          the Service, you agree to be bound by these Terms.
        </p>

        <h2 style={h2}>1. The Service</h2>
        <p style={p}>
          InferenceIndexer.ai is an independent price reporting agency for AI inference. The Service provides:
        </p>
        <ul style={{ listStyle: "disc", padding: 0, marginBottom: 16 }}>
          <li style={li}>A standardized price index (the Standard Inference Token, or SIT) for AI inference pricing</li>
          <li style={li}>A public website displaying model pricing, SIT scores, and tier indices</li>
          <li style={li}>A REST API for programmatic access to pricing data</li>
          <li style={li}>Price alert notifications via Telegram and Twitter (for subscribers)</li>
        </ul>
        <p style={p}>
          We are a <strong style={{ color: "#e5e5e5" }}>price information layer</strong>. We do not provide inference
          services, route API calls, operate models, or act as a broker. We are not an exchange.
        </p>

        <h2 style={h2}>2. Acceptable Use</h2>
        <p style={p}>You agree not to:</p>
        <ul style={{ listStyle: "disc", padding: 0, marginBottom: 16 }}>
          <li style={li}>Use the Service for any unlawful purpose</li>
          <li style={li}>Attempt to reverse-engineer, decompile, or extract our proprietary methodology beyond what is published in our Methodology page</li>
          <li style={li}>Scrape the website in a manner that degrades service for other users (use the API instead)</li>
          <li style={li}>Resell or redistribute raw API data without attribution</li>
          <li style={li}>Circumvent API rate limits through multiple accounts or any other means</li>
          <li style={li}>Use the Service to manipulate or attempt to manipulate inference pricing on any platform</li>
        </ul>

        <h2 style={h2}>3. API Access and Rate Limits</h2>
        <p style={p}>The API is available in the following tiers:</p>
        <ul style={{ listStyle: "disc", padding: 0, marginBottom: 16 }}>
          <li style={li}><strong style={{ color: "#e5e5e5" }}>Public:</strong> 1,000 requests/day, no API key required</li>
          <li style={li}><strong style={{ color: "#e5e5e5" }}>Free:</strong> 10,000 requests/day, requires email signup</li>
          <li style={li}><strong style={{ color: "#e5e5e5" }}>Paid:</strong> 50,000 requests/day, for commercial use</li>
        </ul>
        <p style={p}>
          We reserve the right to modify rate limits, suspend access, or revoke API keys for violations of these Terms.
        </p>

        <h2 style={h2}>4. Data Licensing</h2>
        <p style={p}>
          SIT index values, SIT scores, and aggregate statistics published on InferenceIndexer.ai are copyright
          InferenceIndexer.ai. You may:
        </p>
        <ul style={{ listStyle: "disc", padding: 0, marginBottom: 16 }}>
          <li style={li}>Reference SIT values in research, articles, and reports with attribution</li>
          <li style={li}>Display SIT values on your own website or application, provided you link back to InferenceIndexer.ai</li>
          <li style={li}>Use API data for internal analysis and commercial products</li>
        </ul>
        <p style={p}>You may not:</p>
        <ul style={{ listStyle: "disc", padding: 0, marginBottom: 16 }}>
          <li style={li}>Claim the SIT methodology or index as your own</li>
          <li style={li}>Remove attribution or branding from data sourced from the Service</li>
          <li style={li}>Create a competing price index using our data without permission</li>
        </ul>
        <p style={p}>
          See our <a href="/methodology" style={{ color: "#C4A038" }}>Methodology page</a> for citing the SIT in academic work.
        </p>

        <h2 style={h2}>5. No Financial Advice</h2>
        <p style={p}>
          The information provided by InferenceIndexer.ai is for informational purposes only. It does not constitute
          financial, investment, trading, or commercial advice. The SIT index reflects market prices for AI inference
          and does not predict future price movements. You are solely responsible for any decisions you make based on
          data from this Service.
        </p>

        <h2 style={h2}>6. No Warranty</h2>
        <p style={p}>
          The Service is provided &quot;as is&quot; and &quot;as available&quot; without warranties of any kind, whether
          express or implied. We do not warrant that:
        </p>
        <ul style={{ listStyle: "disc", padding: 0, marginBottom: 16 }}>
          <li style={li}>Prices are accurate, complete, or current at any given moment</li>
          <li style={li}>The Service will be uninterrupted or error-free</li>
          <li style={li}>The methodology will remain unchanged (see our rebaselining policy)</li>
          <li style={li}>Any particular model or provider will continue to be tracked</li>
        </ul>
        <p style={p}>
          Price data is sourced from third-party APIs (primarily OpenRouter) and may contain errors or delays from
          upstream sources.
        </p>

        <h2 style={h2}>7. Limitation of Liability</h2>
        <p style={p}>
          To the maximum extent permitted by law, InferenceIndexer.ai shall not be liable for any indirect, incidental,
          special, consequential, or punitive damages, or any loss of profits or revenues, arising from your use of
          or inability to use the Service. This includes, without limitation, losses arising from:
        </p>
        <ul style={{ listStyle: "disc", padding: 0, marginBottom: 16 }}>
          <li style={li}>Trading or investment decisions based on SIT data</li>
          <li style={li}>Inaccurate or delayed pricing information</li>
          <li style={li}>API downtime or rate limiting</li>
          <li style={li}>Methodology changes or rebaselining</li>
        </ul>

        <h2 style={h2}>8. Indemnification</h2>
        <p style={p}>
          You agree to indemnify and hold harmless InferenceIndexer.ai from any claims, damages, or expenses arising
          from your misuse of the Service or violation of these Terms.
        </p>

        <h2 style={h2}>9. Changes to the Service</h2>
        <p style={p}>
          We reserve the right to modify, suspend, or discontinue any part of the Service at any time. Material changes
          to the SIT methodology will follow the rebaselining process described in our{" "}
          <a href="/methodology" style={{ color: "#C4A038" }}>Methodology page</a> (14-day public comment period).
        </p>

        <h2 style={h2}>10. Changes to These Terms</h2>
        <p style={p}>
          We may update these Terms from time to time. Material changes will be announced on the homepage. Continued use
          of the Service after changes take effect constitutes acceptance of the revised Terms.
        </p>

        <h2 style={h2}>11. Governing Law</h2>
        <p style={p}>
          These Terms are governed by the laws of Ireland. Any disputes shall be subject to the exclusive jurisdiction
          of the Irish courts.
        </p>

        <h2 style={h2}>12. Contact</h2>
        <p style={p}>
          For questions about these Terms, please contact us via the methods listed on our{" "}
          <a href="/about" style={{ color: "#C4A038" }}>About page</a>.
        </p>
      </div>
      <Footer />
    </div>
  );
}
