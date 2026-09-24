import type { MetadataRoute } from "next";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const BASE_URL = "https://www.inferenceindexer.ai";

interface ModelSummary {
  model_id: string;
  fetched_at: string;
}

interface ProviderSummary {
  name: string;
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const entries: MetadataRoute.Sitemap = [];

  // Static pages
  const staticPages = [
    { url: "", priority: 1.0, changeFrequency: "hourly" as const },
    { url: "/models", priority: 0.9, changeFrequency: "hourly" as const },
    { url: "/for-agents", priority: 0.8, changeFrequency: "monthly" as const },
    { url: "/api-docs", priority: 0.8, changeFrequency: "monthly" as const },
    { url: "/embed-docs", priority: 0.7, changeFrequency: "monthly" as const },
    { url: "/methodology", priority: 0.7, changeFrequency: "monthly" as const },
    { url: "/providers", priority: 0.7, changeFrequency: "daily" as const },
    { url: "/embeddings", priority: 0.6, changeFrequency: "daily" as const },
    { url: "/model-type", priority: 0.6, changeFrequency: "monthly" as const },
    { url: "/data-quality", priority: 0.5, changeFrequency: "monthly" as const },
    { url: "/about", priority: 0.5, changeFrequency: "monthly" as const },
    { url: "/privacy", priority: 0.3, changeFrequency: "yearly" as const },
    { url: "/terms", priority: 0.3, changeFrequency: "yearly" as const },
  ];

  for (const page of staticPages) {
    entries.push({
      url: `${BASE_URL}${page.url}`,
      lastModified: new Date(),
      changeFrequency: page.changeFrequency,
      priority: page.priority,
    });
  }

  // Dynamic model pages (API caps a single page at 500)
  try {
    const res = await fetch(`${API_URL}/v1/models?limit=500`, {
      next: { revalidate: 3600 },
    });
    if (res.ok) {
      const data = await res.json();
      const models: ModelSummary[] = data.models || [];

      for (const model of models) {
        entries.push({
          url: `${BASE_URL}/models/${model.model_id}`,
          lastModified: model.fetched_at ? new Date(model.fetched_at) : new Date(),
          changeFrequency: "hourly",
          priority: 0.9,
        });
      }
    }
  } catch {
    // If API is down, just serve static pages
  }

  // Provider pages
  try {
    const res = await fetch(`${API_URL}/v1/providers`, {
      next: { revalidate: 3600 },
    });
    if (res.ok) {
      const data = await res.json();
      const providers: ProviderSummary[] = data.providers || [];
      for (const p of providers) {
        entries.push({
          url: `${BASE_URL}/providers/${encodeURIComponent(p.name)}`,
          lastModified: new Date(),
          changeFrequency: "daily",
          priority: 0.6,
        });
      }
    }
  } catch {
    // ignore
  }

  return entries;
}
