import { NextRequest } from "next/server";

// Server-side admin API client. The backend admin endpoints are gated by the
// SSR secret, which this sends via header. This module only runs server-side.
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const SSR_SECRET = "inferenceindexer-ssr-2026";

export interface FeedSource {
  source: string;
  cadence: string;
  model_count: number;
  priced_count: number;
  endpoint_count: number;
  last_fetch: string | null;
  age_minutes: number | null;
  status: string;
  expected_cadence: string;
  stale: boolean;
}

export interface FeedStatus {
  generated_at: string;
  health: string;
  source_count: number;
  total_models_indexed: number;
  sources: FeedSource[];
  problem_count: number;
  problems: FeedSource[];
}

export interface PricePair {
  model_id: string;
  endpoint_provider: string;
  direct_blended: number;
  openrouter_blended: number;
  pct_diff: number;
  direct_input: number;
  direct_output: number;
  openrouter_input: number;
  openrouter_output: number;
}

export interface PriceCompare {
  generated_at: string;
  count: number;
  sort: string;
  order: string;
  pairs: PricePair[];
}

async function getJson<T>(endpoint: string): Promise<T> {
  const res = await fetch(`${API_URL}${endpoint}`, {
    cache: "no-store",
    headers: { "X-SSR-Secret": SSR_SECRET },
  });
  if (!res.ok) {
    throw new Error(`Admin API error: ${res.status} on ${endpoint}`);
  }
  return res.json() as Promise<T>;
}

export function getFeedStatus(): Promise<FeedStatus> {
  return getJson<FeedStatus>("/v1/admin/feeds");
}

export function getPriceCompare(
  sort = "abs_diff",
  order = "desc",
  minDiff = 0,
  provider?: string
): Promise<PriceCompare> {
  const q = new URLSearchParams();
  q.set("sort", sort);
  q.set("order", order);
  q.set("min_diff", String(minDiff));
  if (provider) q.set("provider", provider);
  return getJson<PriceCompare>(`/v1/admin/price-compare?${q.toString()}`);
}

// --- Provider submissions review queue (owner-only) ---

export interface PendingSubmission {
  id: number;
  provider_name: string;
  website: string;
  api_base_url: string;
  country: string;
  is_eu_sovereign: boolean;
  is_zdr: boolean;
  zdr_notes: string;
  contact_email: string;
  notes: string;
  status: string;
  created_at: string;
  integration_status?: string;
}

export interface SubmissionList {
  count: number;
  submissions: PendingSubmission[];
}

export function getSubmissions(status?: string): Promise<SubmissionList> {
  const q = status ? `?status=${status}` : "";
  return getJson<SubmissionList>(`/v1/providers/submissions${q}`);
}

export async function reviewSubmission(
  id: number,
  decision: { status: "approved" | "rejected"; is_zdr?: boolean; is_eu_sovereign?: boolean }
): Promise<{ id: number; status: string }> {
  const res = await fetch(`${API_URL}/v1/providers/submissions/${id}/review`, {
    method: "POST",
    cache: "no-store",
    headers: {
      "X-SSR-Secret": SSR_SECRET,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(decision),
  });
  if (!res.ok) throw new Error(`Review failed (${res.status})`);
  return res.json();
}

// --- API usage analytics (owner-only) ---

export interface UsageToday {
  requests: number;
  unique_users: number;
  free_requests: number;
  public_requests: number;
  free_users: number;
}

export interface UsageDailyPoint {
  date: string;
  requests: number;
  unique_users: number;
  free_users: number;
}

export interface UsagePlanMix {
  plan: string;
  requests: number;
  users: number;
}

export interface UsageEndpoint {
  endpoint: string;
  requests: number;
}

export interface UsageHourlyPoint {
  hour: string;
  requests: number;
}

export interface UsageStatusMix {
  status: number;
  requests: number;
}

export interface FreeKeyActivity {
  user: string;
  endpoint: string;
  requests: number;
  last: string | null;
}

export interface ApiUsage {
  today: UsageToday;
  daily: UsageDailyPoint[];
  plan_mix: UsagePlanMix[];
  top_endpoints: UsageEndpoint[];
  hourly: UsageHourlyPoint[];
  status_mix: UsageStatusMix[];
  new_free_signups_30d: number;
  free_key_activity: FreeKeyActivity[];
  scope: string;
}

export function getApiUsage(includeSsr = false): Promise<ApiUsage> {
  const q = includeSsr ? `?include_ssr=1` : "";
  return getJson<ApiUsage>(`/v1/admin/api-usage${q}`);
}