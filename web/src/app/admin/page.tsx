import { cookies } from "next/headers";
import { isAdminCookie } from "@/lib/admin-auth";
import { redirect } from "next/navigation";
import Link from "next/link";

export default async function AdminHome() {
  const cookieStore = await cookies();
  const cookieHeader = cookieStore
    .getAll()
    .map((c) => `${c.name}=${c.value}`)
    .join("; ");
  const authed = isAdminCookie(cookieHeader);

  if (!authed) {
    redirect("/admin/login");
  }

  return (
    <div>
      <h1
        style={{ fontSize: 24, color: "var(--text-heading)", marginBottom: 6 }}
      >
        Admin Dashboard
      </h1>
      <p style={{ color: "var(--text-secondary)", marginBottom: 28 }}>
        Internal monitoring. Check these at the start and end of each day.
      </p>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
          gap: 20,
        }}
      >
        <Card href="/admin/feeds" title="Feed Status" color="var(--blue)">
          Is all pricing data flowing and up to date? Per-source health, last
          fetch age, model/priced counts. Spot any broken or stale feeds.
        </Card>
        <Card href="/admin/pricing" title="Price Compare" color="var(--accent)">
          OpenRouter price vs direct provider price, side by side. Sorted to
          surface discrepancies across every provider we list.
        </Card>
      </div>
    </div>
  );
}

function Card({
  href,
  title,
  color,
  children,
}: {
  href: string;
  title: string;
  color: string;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      style={{
        display: "block",
        padding: 24,
        background: "var(--bg-card)",
        border: "1px solid var(--border-card)",
        borderRadius: 12,
        textDecoration: "none",
        transition: "border-color 0.18s ease",
      }}
    >
      <div
        style={{
          width: 8,
          height: 8,
          borderRadius: "50%",
          background: color,
          marginBottom: 12,
        }}
      />
      <h2 style={{ fontSize: 18, color: "var(--text-heading)", marginBottom: 8 }}>
        {title}
      </h2>
      <p style={{ color: "var(--text-secondary)", fontSize: 13, lineHeight: 1.6 }}>
        {children}
      </p>
    </Link>
  );
}