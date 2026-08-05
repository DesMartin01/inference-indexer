import { Header, Footer } from "@/components/Header";
import type { CSSProperties } from "react";

export const metadata = {
  title: "Privacy Policy - InferenceIndexer.ai",
  description:
    "How InferenceIndexer.ai collects, uses, and protects data. Google Analytics, API usage tracking, cookie policy, and data retention.",
  alternates: { canonical: "https://inferenceindexer.ai/privacy" },
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

export default function PrivacyPage() {
  return (
    <div style={{ background: "#0a0a0a", minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <Header activePage="" />
      <div style={{ maxWidth: 800, width: "100%", margin: "0 auto", padding: "44px 28px 60px", flex: 1 }}>
        <h1 style={{ fontSize: 28, fontWeight: 700, color: "#ffffff", marginBottom: 8, letterSpacing: "-0.01em" }}>
          Privacy Policy
        </h1>
        <p style={{ ...mutedMono, marginBottom: 32 }}>
          Last updated: August 5, 2026
        </p>

        <p style={p}>
          This Privacy Policy describes how InferenceIndexer.ai (&quot;we&quot;, &quot;us&quot;, or &quot;our&quot;)
          collects, uses, and shares information when you visit our website or use our API.
        </p>

        <h2 style={h2}>1. Information We Collect</h2>
        <h3 style={{ fontSize: 15, fontWeight: 600, color: "#e5e5e5", marginBottom: 8 }}>1.1 Information you provide</h3>
        <ul style={{ listStyle: "disc", padding: 0, marginBottom: 16 }}>
          <li style={li}>
            <strong style={{ color: "#e5e5e5" }}>API signup:</strong> When you request an API key, we collect your email
            address. This is used solely to issue and manage your API key.
          </li>
          <li style={li}>
            <strong style={{ color: "#e5e5e5" }}>Alert subscriptions:</strong> If you subscribe to price alerts via
            Telegram or Twitter, we store your Telegram chat ID or Twitter handle.
          </li>
        </ul>
        <h3 style={{ fontSize: 15, fontWeight: 600, color: "#e5e5e5", marginBottom: 8 }}>1.2 Information collected automatically</h3>
        <ul style={{ listStyle: "disc", padding: 0, marginBottom: 16 }}>
          <li style={li}>
            <strong style={{ color: "#e5e5e5" }}>Usage data:</strong> We use Google Analytics to collect anonymized
            usage data including page views, session duration, referral source, and approximate geographic location
            (country-level). We do not collect IP addresses in a form that identifies individuals.
          </li>
          <li style={li}>
            <strong style={{ color: "#e5e5e5" }}>API request logs:</strong> We log API requests for rate limiting and
            abuse prevention. Logs include API key, timestamp, endpoint, and response status. Logs are retained for
            30 days and then automatically deleted.
          </li>
          <li style={li}>
            <strong style={{ color: "#e5e5e5" }}>Cookies:</strong> See Section 3 below.
          </li>
        </ul>

        <h2 style={h2}>2. How We Use Your Information</h2>
        <ul style={{ listStyle: "disc", padding: 0, marginBottom: 16 }}>
          <li style={li}>To provide and maintain the InferenceIndexer API</li>
          <li style={li}>To enforce rate limits and prevent abuse</li>
          <li style={li}>To send price alerts you have explicitly subscribed to</li>
          <li style={li}>To analyze usage patterns and improve the product</li>
          <li style={li}>To communicate with you about API changes or service updates</li>
        </ul>
        <p style={p}>
          We do <strong style={{ color: "#e5e5e5" }}>not</strong> sell, rent, or trade your personal information to
          third parties. We do not use your data for targeted advertising.
        </p>

        <h2 style={h2}>3. Cookies</h2>
        <p style={p}>
          InferenceIndexer uses cookies and similar technologies for the following purposes:
        </p>
        <ul style={{ listStyle: "disc", padding: 0, marginBottom: 16 }}>
          <li style={li}>
            <strong style={{ color: "#e5e5e5" }}>Analytics:</strong> Google Analytics sets cookies
            (<code style={{ ...mutedMono, color: "#c9c9c9" }}>_ga</code>, <code style={{ ...mutedMono, color: "#c9c9c9" }}>_gid</code>)
            to distinguish unique users and measure session duration. These cookies expire after 2 years and 24 hours
            respectively.
          </li>
          <li style={li}>
            <strong style={{ color: "#e5e5e5" }}>Essential:</strong> Any future authentication features may use
            session cookies. These are strictly necessary for the service to function.
          </li>
        </ul>
        <p style={p}>
          You can control cookies through your browser settings. Disabling analytics cookies will not affect your
          ability to browse the site or use the API.
        </p>

        <h2 style={h2}>4. Third-Party Services</h2>
        <p style={p}>We use the following third-party services that may process limited personal data:</p>
        <ul style={{ listStyle: "disc", padding: 0, marginBottom: 16 }}>
          <li style={li}>
            <strong style={{ color: "#e5e5e5" }}>Google Analytics:</strong> Anonymized usage analytics. See
            Google&apos;s <a href="https://policies.google.com/privacy" style={{ color: "#C4A038" }}>Privacy Policy</a>.
          </li>
          <li style={li}>
            <strong style={{ color: "#e5e5e5" }}>Supabase:</strong> Database hosting for API user accounts. See
            Supabase&apos;s <a href="https://supabase.com/privacy" style={{ color: "#C4A038" }}>Privacy Policy</a>.
          </li>
          <li style={li}>
            <strong style={{ color: "#e5e5e5" }}>Vercel:</strong> Website hosting. See Vercel&apos;s{" "}
            <a href="https://vercel.com/legal/privacy-policy" style={{ color: "#C4A038" }}>Privacy Policy</a>.
          </li>
          <li style={li}>
            <strong style={{ color: "#e5e5e5" }}>Telegram:</strong> For delivering price alert notifications to
            subscribers who opt in. See Telegram&apos;s{" "}
            <a href="https://telegram.org/privacy" style={{ color: "#C4A038" }}>Privacy Policy</a>.
          </li>
        </ul>

        <h2 style={h2}>5. Data Retention</h2>
        <ul style={{ listStyle: "disc", padding: 0, marginBottom: 16 }}>
          <li style={li}>API request logs: 30 days</li>
          <li style={li}>API user accounts (email): Retained until you request deletion</li>
          <li style={li}>Price data (model prices, SIT scores): Retained indefinitely as historical index data. This is non-personal data.</li>
          <li style={li}>Analytics data: Retained per Google Analytics defaults (up to 14 months)</li>
        </ul>

        <h2 style={h2}>6. Your Rights</h2>
        <p style={p}>Under the GDPR and similar regulations, you have the right to:</p>
        <ul style={{ listStyle: "disc", padding: 0, marginBottom: 16 }}>
          <li style={li}>Access the personal data we hold about you</li>
          <li style={li}>Request correction of inaccurate data</li>
          <li style={li}>Request deletion of your personal data</li>
          <li style={li}>Object to processing of your data</li>
          <li style={li}>Withdraw consent for alert subscriptions at any time</li>
        </ul>
        <p style={p}>
          To exercise any of these rights, contact us at the email listed in Section 8. We will respond within 30 days.
        </p>

        <h2 style={h2}>7. Security</h2>
        <p style={p}>
          We take reasonable measures to protect your data. API keys are stored as hashed values. Database access is
          restricted to authenticated service accounts. All API traffic is encrypted via HTTPS/TLS. However, no method
          of transmission or storage is 100% secure, and we cannot guarantee absolute security.
        </p>

        <h2 style={h2}>8. Contact</h2>
        <p style={p}>
          If you have questions about this Privacy Policy, please contact us via the methods listed on our{" "}
          <a href="/about" style={{ color: "#C4A038" }}>About page</a>.
        </p>

        <h2 style={h2}>9. Changes to This Policy</h2>
        <p style={p}>
          We may update this Privacy Policy from time to time. Material changes will be announced on the homepage.
          The &quot;Last updated&quot; date above indicates when the policy was last revised.
        </p>
      </div>
      <Footer />
    </div>
  );
}
