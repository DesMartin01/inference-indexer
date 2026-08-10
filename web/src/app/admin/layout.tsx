import type { Metadata } from "next";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { isAdminCookie } from "@/lib/admin-auth";
import Link from "next/link";

export const metadata: Metadata = {
  title: "InferenceIndexer Admin",
  robots: { index: false, follow: false },
};

export default async function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Server-side auth check on every /admin request.
  const cookieStore = await cookies();
  const cookieHeader = cookieStore
    .getAll()
    .map((c) => `${c.name}=${c.value}`)
    .join("; ");
  const authed = isAdminCookie(cookieHeader);

  return (
    <div className="min-h-screen" style={{ background: "var(--bg)" }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "16px 32px",
          borderBottom: "1px solid var(--border-card)",
          background: "var(--bg-card)",
        }}
      >
        <Link
          href="/admin"
          style={{ fontWeight: 600, color: "var(--text-heading)", fontSize: 15 }}
        >
          InferenceIndexer <span style={{ color: "var(--accent)" }}>Admin</span>
        </Link>
        {authed && (
          <nav style={{ display: "flex", gap: 20, alignItems: "center" }}>
            <Link href="/admin/feeds" style={{ fontSize: 13 }}>
              Feed Status
            </Link>
            <Link href="/admin/pricing" style={{ fontSize: 13 }}>
              Price Compare
            </Link>
            <Link href="/admin/logout" style={{ fontSize: 13, color: "var(--text-muted)" }}>
              Logout
            </Link>
          </nav>
        )}
      </div>
      <main style={{ padding: "28px 32px" }}>{children}</main>
    </div>
  );
}