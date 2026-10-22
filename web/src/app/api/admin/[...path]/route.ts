import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { isAdminCookie } from "@/lib/admin-auth";

// B8 (2026-10-21): the admin dashboards' client components used to import
// lib/admin-api directly, which put the X-Admin-Token builder in the browser
// bundle. They now call these server route handlers instead: the handler
// checks the admin session cookie, attaches the secret server-side, and
// proxies to the API. The secret never reaches the browser.

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
// N1 (2026-10-21): /v1/admin/* on the API is gated by II_ADMIN_TOKEN
// (X-Admin-Token), not the SSR secret. Missing token -> API returns 401.
const ADMIN_TOKEN = process.env.II_ADMIN_TOKEN || "";

async function guard(): Promise<NextResponse | null> {
  const cookieStore = await cookies();
  const cookieHeader = cookieStore
    .getAll()
    .map((c) => `${c.name}=${c.value}`)
    .join("; ");
  if (!isAdminCookie(cookieHeader)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  return null;
}

async function proxy(req: NextRequest, path: string[]): Promise<NextResponse> {
  const denied = await guard();
  if (denied) return denied;

  const target = `${API_URL}/v1/admin/${path.join("/")}${req.nextUrl.search}`;
  const headers: Record<string, string> = {
    "X-Admin-Token": ADMIN_TOKEN,
    "Content-Type": "application/json",
  };
  const method = req.method;
  const body = method === "POST" || method === "PUT" ? await req.text() : undefined;

  try {
    const res = await fetch(target, {
      method,
      headers,
      body,
      cache: "no-store",
      signal: AbortSignal.timeout(30_000),
    });
    const text = await res.text();
    return new NextResponse(text, {
      status: res.status,
      headers: { "Content-Type": "application/json" },
    });
  } catch {
    return NextResponse.json({ error: "Admin API unreachable" }, { status: 502 });
  }
}

export async function GET(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  return proxy(req, path);
}

export async function POST(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  return proxy(req, path);
}
