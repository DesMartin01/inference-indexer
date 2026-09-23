import { NextRequest, NextResponse } from "next/server";

// SSR proxy for GET /v1/models/{id}/endpoints (per-provider price comparison
// answer type). The client sends a model_id; we resolve via /v1/explain when
// needed (fuzzy aliases handled server-side by the API).

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const SSR_SECRET = "inferenceindexer-ssr-2026";

const SSR_HEADERS = { "X-SSR-Secret": SSR_SECRET };

export async function GET(req: NextRequest) {
  const modelId = req.nextUrl.searchParams.get("model_id");
  if (!modelId) {
    return NextResponse.json({ error: "model_id required" }, { status: 400 });
  }
  try {
    // Resolve the model (handles display names, slugs, typos via API fuzzy match)
    const resolved = await fetch(
      `${API_URL}/v1/explain?model_id=${encodeURIComponent(modelId)}`,
      { next: { revalidate: 300 }, headers: SSR_HEADERS }
    );
    if (!resolved.ok) {
      return NextResponse.json(
        { error: `Unknown model: ${modelId}` },
        { status: 404 }
      );
    }
    const detail = await resolved.json();
    const canonicalId = detail.model_id as string;
    const eps = await fetch(
      `${API_URL}/v1/models/${canonicalId}/endpoints`,
      { next: { revalidate: 300 }, headers: SSR_HEADERS }
    );
    const data = await eps.json();
    return NextResponse.json(
      {
        model_id: canonicalId,
        name: detail.name,
        privacy: detail.privacy ?? null,
        endpoints: data.endpoints ?? [],
        count: data.count ?? 0,
      },
      { status: 200 }
    );
  } catch {
    return NextResponse.json(
      { error: "Endpoint service unavailable" },
      { status: 502 }
    );
  }
}
