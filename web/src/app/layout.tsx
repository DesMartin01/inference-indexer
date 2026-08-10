import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import { Suspense } from "react";
import "./globals.css";
import { getModelCount } from "@/lib/api";
import { CURRENT_MODEL_COUNT } from "@/lib/counts";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  display: "swap",
});

export async function generateMetadata(): Promise<Metadata> {
  const count = (await getModelCount().catch(() => 0)) || CURRENT_MODEL_COUNT;
  return {
  title: "InferenceIndexer.ai — Independent Price Index for AI Inference",
  description:
    `The Standard Inference Token (SIT) is a standardized unit for tracking AI inference prices across providers. ${count} models, updated hourly.`,
  };
}

// Google Analytics
const GA_ID = "G-8L4MLB262D";
const gaScript = `
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', '${GA_ID}');
`;

// Site-wide structured data (WebSite + Organization) for search engines & AI agents.
const siteSchema = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "WebSite",
      "@id": "https://www.inferenceindexer.ai/#website",
      url: "https://www.inferenceindexer.ai/",
      name: "InferenceIndexer",
      description:
        "Independent price reporting agency for AI inference. Live and historical inference pricing across providers.",
      publisher: { "@id": "https://www.inferenceindexer.ai/#organization" },
    },
    {
      "@type": "Organization",
      "@id": "https://www.inferenceindexer.ai/#organization",
      name: "InferenceIndexer.ai",
      url: "https://www.inferenceindexer.ai/",
      logo: "https://www.inferenceindexer.ai/profile-icon.png",
      sameAs: ["https://x.com/inferenceindex"],
      description:
        "Independent AI inference price index. Live and historical pricing, direct from providers.",
    },
  ],
};

export default function RootLayout({
  children,
}: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${jetbrainsMono.variable} h-full antialiased`}
    >
      <head>
        {/* Google Analytics */}
        <script async src={`https://www.googletagmanager.com/gtag/js?id=${GA_ID}`} />
        <script dangerouslySetInnerHTML={{ __html: gaScript }} />
        {/* Structured data for search engines & AI agents */}
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(siteSchema) }}
        />
      </head>
      <body className="min-h-full">
        <Suspense fallback={null}>{children}</Suspense>
      </body>
    </html>
  );
}
