import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { isAdminCookie } from "@/lib/admin-auth";
import { getPriceCompare } from "@/lib/admin-api";
import { PriceCompareClient } from "./client";

export const revalidate = 0;

export default async function PricingPage() {
  const cookieStore = await cookies();
  const cookieHeader = cookieStore
    .getAll()
    .map((c) => `${c.name}=${c.value}`)
    .join("; ");
  if (!isAdminCookie(cookieHeader)) {
    redirect("/admin/login");
  }

  let initial;
  let error: string | null = null;
  try {
    initial = await getPriceCompare("abs_diff", "desc", 0);
  } catch (e) {
    error = (e as Error).message;
  }
  return <PriceCompareClient initial={initial ?? null} error={error} />;
}