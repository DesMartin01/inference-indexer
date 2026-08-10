import { NextRequest, NextResponse } from "next/server";

const COOKIE_NAME = "ii_admin_session";

export async function GET(request: NextRequest) {
  const url = new URL("/admin/login", request.url);
  const res = NextResponse.redirect(url);
  res.cookies.set({
    name: COOKIE_NAME,
    value: "",
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/admin",
    maxAge: 0,
  });
  return res;
}

export async function POST(request: NextRequest) {
  return GET(request);
}