import type { MetadataRoute } from "next";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const BASE_URL = "https://inferenceindexer.ai";

interface ModelSummary {
  model_id: string;
  fetched_at: string;
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const entries: MetadataRoute.Sitemap = [];

  // Static pages
  const staticPages = [
    { url: "", priority: 1.0, changeFrequency: "hourly" as const },
    { url: "/api-docs", priority: 0.8, changeFrequency: "monthly" as const },
    { url: "/methodology", priority: 0.7, changeFrequency: "monthly" as const },
    { url: "/about", priority: 0.5, changeFrequency: "monthly" as const },
  ];

  for (const page of staticPages) {
    entries.push({
      url: `${BASE_URL}${page.url}`,
      lastModified: new Date(),
      changeFrequency: page.changeFrequency,
      priority: page.priority,
    });
  }

  // Dynamic model pages
  try {
    const res = await fetch(`${API_URL}/v1/models?limit=315`, {
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

  return entries;
}
