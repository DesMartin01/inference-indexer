import { cookies } from "next/headers";
import { isAdminCookie } from "@/lib/admin-auth";
import { redirect } from "next/navigation";
import { SubmissionsClient } from "./client";

export const dynamic = "force-dynamic";

export default async function SubmissionsPage() {
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
      <h1 style={{ fontSize: 24, color: "var(--text-heading)", marginBottom: 6 }}>
        Provider Submissions
      </h1>
      <p style={{ color: "var(--text-secondary)", marginBottom: 24 }}>
        Review providers that submitted their pricing endpoint. Approved
        providers go live as tracked providers.
      </p>
      <SubmissionsClient />
    </div>
  );
}