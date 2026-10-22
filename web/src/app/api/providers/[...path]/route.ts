import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { isAdminCookie } from "@/lib/admin-auth";

// B8 (2026-10-21): provider-submission review proxy. Same pattern as
// /api/admin/*: admin cookie check server-side, admin token attached here,
// browser never sees the token. N1 (2026-10-21): the API gates
// /v1/providers/submissions* on II_ADMIN_TOKEN (X-Admin-Token).

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
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

export async function GET(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const denied = await guard();
  if (denied) return denied;
  const { path } = await ctx.params;
  const target = `${API_URL}/v1/providers/${path.join("/")}${req.nextUrl.search}`;
  try {
    const res = await fetch(target, {
      headers: { "X-Admin-Token": ADMIN_TOKEN },
      cache: "no-store",
      signal: AbortSignal.timeout(30_000),
    });
    return new NextResponse(await res.text(), {
      status: res.status,
      headers: { "Content-Type": "application/json" },
    });
  } catch {
    return NextResponse.json({ error: "Admin API unreachable" }, { status: 502 });
  }
}

export async function POST(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const denied = await guard();
  if (denied) return denied;
  const { path } = await ctx.params;
  const target = `${API_URL}/v1/providers/${path.join("/")}`;
  try {
    const res = await fetch(target, {
      method: "POST",
      headers: { "X-Admin-Token": ADMIN_TOKEN, "Content-Type": "application/json" },
      body: await req.text(),
      cache: "no-store",
      signal: AbortSignal.timeout(30_000),
    });
    return new NextResponse(await res.text(), {
      status: res.status,
      headers: { "Content-Type": "application/json" },
    });
  } catch {
    return NextResponse.json({ error: "Admin API unreachable" }, { status: 502 });
  }
}
