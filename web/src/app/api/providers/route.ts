import { NextRequest, NextResponse } from "next/server";

// SSR proxy for GET /v1/providers (provider list answer type).
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const SSR_SECRET = "inferenceindexer-ssr-2026";

export async function GET(_req: NextRequest) {
  try {
    const res = await fetch(`${API_URL}/v1/providers`, {
      next: { revalidate: 300 },
      headers: { "X-SSR-Secret": SSR_SECRET },
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ count: 0, providers: [] }, { status: 502 });
  }
}
