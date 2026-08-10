import type { Metadata } from "next";
import Link from "next/link";
import { SubmitClient } from "./client";

export const metadata: Metadata = {
  title: "Submit a Provider | InferenceIndexer.ai",
  description:
    "Are you an inference provider? Submit your pricing endpoint and get listed on InferenceIndexer, the independent AI inference price index.",
  alternates: { canonical: "https://www.inferenceindexer.ai/providers/submit" },
};

export default function ProviderSubmitPage() {
  return (
    <main
      style={{
        maxWidth: 760,
        margin: "0 auto",
        padding: "48px 20px 80px",
      }}
    >
      <Link
        href="/providers"
        style={{ color: "var(--text-muted)", fontSize: 13, textDecoration: "none" }}
      >
        ← All Providers
      </Link>

      <h1
        style={{
          fontSize: 28,
          fontWeight: 700,
          color: "var(--text-heading)",
          margin: "18px 0 8px",
        }}
      >
        Submit your provider
      </h1>
      <p style={{ color: "var(--text-secondary)", fontSize: 14, lineHeight: 1.6 }}>
        Are you an inference provider? Get listed on the independent AI inference
        price index. We verify your pricing endpoint live, then put it up for review.
        Approved providers flow straight into the index.
      </p>

      <div style={{ height: 28 }} />

      <SubmitClient />
    </main>
  );
}