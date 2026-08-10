import crypto from "crypto";

const ADMIN_SECRET = process.env.ADMIN_SECRET || "";
const COOKIE_NAME = "ii_admin_session";

function sign(value: string): string {
  return crypto
    .createHmac("sha256", ADMIN_SECRET)
    .update(value)
    .digest("base64url");
}

/**
 * Verify the admin session cookie. Returns true if the cookie is present,
 * correctly signed, and not expired.
 */
export function isAdminCookie(cookieHeader: string | null | undefined): boolean {
  if (!cookieHeader || !ADMIN_SECRET) return false;
  // cookieHeader is the full Cookie header; parse our cookie out of it.
  const match = new RegExp(`${COOKIE_NAME}=([^;]+)`).exec(cookieHeader);
  if (!match) return false;
  const value = match[1];
  const parts = value.split(".");
  if (parts.length !== 3) return false;
  if (parts[0] !== "v1") return false;
  const issuedMs = Number(parts[1]);
  if (!Number.isFinite(issuedMs)) return false;
  // Expiry check (12h)
  if (Date.now() - issuedMs > 12 * 60 * 60 * 1000) return false;
  // Signature check (constant-time compare)
  const expected = sign(`v1.${parts[1]}`);
  const a = Buffer.from(expected);
  const b = Buffer.from(parts[2]);
  if (a.length !== b.length) return false;
  return crypto.timingSafeEqual(a, b);
}

export function adminLogoutPath(): string {
  return "/admin/logout";
}