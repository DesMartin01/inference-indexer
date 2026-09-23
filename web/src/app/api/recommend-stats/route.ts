import { NextRequest, NextResponse } from "next/server";

// Proxy for GET /v1/recommend/stats (anonymous receipts counter).
// Server-side attach of the SSR secret keeps this off the public quota.

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const SSR_SECRET = "inferenceindexer-ssr-2026";

export async function GET(_req: NextRequest) {
  try {
    const res = await fetch(`${API_URL}/v1/recommend/stats`, {
      cache: "no-store",
      headers: { "X-SSR-Secret": SSR_SECRET },
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ total: 0, available: false }, { status: 200 });
  }
}
