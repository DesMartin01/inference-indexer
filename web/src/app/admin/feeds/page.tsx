import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { isAdminCookie } from "@/lib/admin-auth";
import { getFeedStatus } from "@/lib/admin-api";
import { FeedClient } from "./client";

export const revalidate = 0; // always fetch fresh

export default async function FeedsPage() {
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
    data = await getFeedStatus();
  } catch (e) {
    error = (e as Error).message;
  }

  return <FeedClient initial={data ?? null} error={error} />;
}