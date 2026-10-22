import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";
import { isAdminCookie } from "@/lib/admin-auth";

// Server-side proxy for admin API calls made from the browser.
// II_ADMIN_TOKEN is server-only: a "use client" component cannot hold it
// (Oct 22: client-side admin fetches sent an empty token and 401'd). This
// route adds the header server-side, after checking the admin session
// cookie, so it is never an open proxy.
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const ADMIN_TOKEN = process.env.II_ADMIN_TOKEN || "";

const ALLOWED_PREFIXES = ["/v1/admin/", "/v1/providers/submissions"];

async function proxy(request: NextRequest, method: "GET" | "POST") {
  const cookieStore = await cookies();
  const cookieHeader = cookieStore
    .getAll()
    .map((c) => `${c.name}=${c.value}`)
    .join("; ");
  if (!isAdminCookie(cookieHeader)) {
    return NextResponse.json({ error: "Not signed in" }, { status: 401 });
  }

  const path = request.nextUrl.pathname.replace(/^\/admin\/api/, "");
  if (!ALLOWED_PREFIXES.some((p) => path === p || path.startsWith(p))) {
    return NextResponse.json({ error: "Path not allowed" }, { status: 403 });
  }

  const url = new URL(request.nextUrl.search, API_URL);
  url.pathname = path;

  const init: RequestInit = {
    method,
    cache: "no-store",
    headers: { "X-Admin-Token": ADMIN_TOKEN },
  };
  if (method === "POST") {
    init.body = await request.text();
    (init.headers as Record<string, string>)["Content-Type"] =
      "application/json";
  }
  const res = await fetch(url.toString(), init);
  const body = await res.text();
  return new NextResponse(body, {
    status: res.status,
    headers: { "Content-Type": "application/json" },
  });
}

export async function GET(request: NextRequest) {
  return proxy(request, "GET");
}

export async function POST(request: NextRequest) {
  return proxy(request, "POST");
}
