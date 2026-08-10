import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { isAdminCookie } from "@/lib/admin-auth";
import { getApiUsage } from "@/lib/admin-api";
import { ApiUsageClient } from "./client";

export const revalidate = 0; // always fetch fresh

export default async function ApiUsagePage() {
  const cookieStore = await cookies();
  const cookieHeader = cookieStore
    .getAll()
    .map((c) => `${c.name}=${c.value}`)
    .join("; ");
  if (!isAdminCookie(cookieHeader)) {
    redirect("/admin/login");
  }

  let data;
  let error: string | null = null;
  try {
    data = await getApiUsage();
  } catch (e) {
    error = (e as Error).message;
  }

  return <ApiUsageClient initial={data ?? null} error={error} />;
}