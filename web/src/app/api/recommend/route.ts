import { NextRequest, NextResponse } from "next/server";

// SSR proxy for POST /v1/recommend. The homepage engine panel calls THIS route
// (same-origin, no CORS pain, no API key in the browser). Server-side we attach
// the SSR secret so the call lands on the site's own 100k/day budget instead of
// the shared anonymous "public" quota.

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const SSR_SECRET = "inferenceindexer-ssr-2026";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    // AbortSignal timeout: a hung upstream call must fail visibly, not stall
    // the browser fetch forever (des reported second-in-a-row stalling).
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);
    let res: Response;
    try {
      res = await fetch(`${API_URL}/v1/recommend`, {
        method: "POST",
        cache: "no-store",
        signal: controller.signal,
        headers: {
          "Content-Type": "application/json",
          "X-SSR-Secret": SSR_SECRET,
        },
        body: JSON.stringify(body),
      });
    } finally {
      clearTimeout(timeout);
    }
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json(
      { error: { code: "upstream_error", message: "Recommendation service unavailable or timed out. Please try again." } },
      { status: 502 }
    );
  }
}
