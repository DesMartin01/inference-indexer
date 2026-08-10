import { NextRequest, NextResponse } from "next/server";
import crypto from "crypto";

// Server-side only. Never expose ADMIN_SECRET to the client.
const ADMIN_SECRET = process.env.ADMIN_SECRET || "";
// Signing key for the session cookie. Derived from ADMIN_SECRET so we don't
// need a second env var.
const COOKIE_NAME = "ii_admin_session";
const COOKIE_MAX_AGE = 60 * 60 * 12; // 12 hours

function sign(value: string): string {
  return crypto
    .createHmac("sha256", ADMIN_SECRET)
    .update(value)
    .digest("base64url");
}

export async function GET() {
  // Return the message for the login page (or a health check).
  return NextResponse.json({ ok: true });
}

let lastAttempt: number | null = null;

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const password = (body?.password || "") as string;

    // Simple brute-force throttle: 1 attempt per 2 seconds.
    const now = Date.now();
    if (lastAttempt && now - lastAttempt < 2000 && password !== ADMIN_SECRET) {
      return NextResponse.json(
        { success: false, error: "Too many attempts. Try again in a moment." },
        { status: 429 }
      );
    }
    lastAttempt = now;

    if (!ADMIN_SECRET) {
      return NextResponse.json(
        { success: false, error: "Admin auth not configured." },
        { status: 500 }
      );
    }

    if (password !== ADMIN_SECRET) {
      return NextResponse.json(
        { success: false, error: "Incorrect password." },
        { status: 401 }
      );
    }

    // Valid: set a signed session cookie.
    const issued = Date.now().toString();
    const payload = `v1.${issued}`;
    const signature = sign(payload);
    const cookieValue = `${payload}.${signature}`;

    const res = NextResponse.json({ success: true });
    res.cookies.set({
      name: COOKIE_NAME,
      value: cookieValue,
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/admin",
      maxAge: COOKIE_MAX_AGE,
    });
    return res;
  } catch (err) {
    return NextResponse.json(
      { success: false, error: "Invalid request." },
      { status: 400 }
    );
  }
}