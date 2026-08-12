import { NextRequest } from "next/server";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const SSR_SECRET = "inferenceindexer-ssr-2026";

// Next.js fetch with ISR revalidation. Using next: { revalidate } instead of
// cache: "no-store" allows Vercel to serve cached pages at the edge and
// revalidate in the background, instead of forcing dynamic rendering on every
// request.
const ISR_REVALIDATE = 60; // seconds

async function fetchWithCache<T>(endpoint: string): Promise<T> {
  const res = await fetch(`${API_URL}${endpoint}`, {
    next: { revalidate: ISR_REVALIDATE },
    headers: { "X-SSR-Secret": SSR_SECRET },
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  const data = await res.json();
  return data as T;
}

export interface SITLatest {
  date: string;
  composite: { price_per_m: number; index_points: number; models: number; providers: number; change_24h?: number; change_7d?: number; change_30d?: number; change_90d?: number };
  tiers: Record<string, { price_per_m: number; index_points: number; models: number; providers: number; change_24h?: number; change_7d?: number; change_30d?: number; change_90d?: number }>;
  spread: { price_per_m: number; index_points: number; models: number; providers: number; change_24h?: number };
}

export interface SITHistory {
  history: Array<{
    date: string;
    tiers: Record<string, { price_per_m: number; index_points: number; model_count: number }>;
  }>;
  days: number;
}

export interface ModelSummary {
  model_id: string;
  name: string;
  provider: string;
  tier: string;
  context_length: number;
  aa_index_score: number | null;
  modality: string;
  is_reasoning: boolean;
  input_price_per_m: number;
  output_price_per_m: number;
  blended_price_per_m: number;
  sit_adjusted_price: number | null;
  sit_score: number;
  change_24h: number;
  change_7d: number;
  fetched_at: string;
  source_count: number;
  is_zdr: boolean;
  is_eu_sovereign: boolean;
}

export interface ModelList {
  count: number;
  returned: number;
  models: ModelSummary[];
}

export interface ModelDetail {
  model_id: string;
  name: string;
  provider: string;
  tier: string;
  context_length: number;
  aa_index_score: number | null;
  modality: string;
  tokenizer: string | null;
  is_reasoning: boolean;
  date_added: string;
  input_price_per_m: number;
  output_price_per_m: number;
  blended_price_per_m: number;
  sit_adjusted_price: number | null;
  reasoning_multiplier: number;
  sit_score: number;
  change_24h: number;
  change_7d: number;
  tier_average_price: number;
  tier_rank: number;
  tier_total_models: number;
  comparisons: {
    below_tier_avg_pct?: number;
    above_tier_avg_pct?: number;
    above_composite_pct?: number;
  };
  source: string;
  fetched_at: string;
}

export interface ModelHistory {
  model_id: string;
  name: string;
  history: Array<{
    date: string;
    input_price_per_m: number;
    output_price_per_m: number;
    blended_price_per_m: number;
    sit_score: number;
    fetched_at: string;
  }>;
  days: number;
}

export interface ModelEndpoints {
  model_id: string;
  name: string;
  endpoints: Array<{
    provider: string;
    input_price_per_m: number;
    output_price_per_m: number;
    blended_price_per_m: number;
    context_length: number | null;
    fetched_at: string;
  }>;
  count: number;
}

export async function getSITLatest(): Promise<SITLatest> {
  return fetchWithCache<SITLatest>("/v1/sit/composite/latest");
}

export async function getSITHistory(days: number = 30): Promise<SITHistory> {
  return fetchWithCache<SITHistory>(`/v1/sit/composite/history?days=${days}`);
}

export async function getModels(tier?: string, sort?: string, limit?: number, _revalidate?: number): Promise<ModelList> {
  const q = new URLSearchParams();
  if (tier) q.set("tier", tier);
  if (sort) q.set("sort", sort);
  if (limit) q.set("limit", String(limit));
  const qs = q.toString();
  return fetchWithCache<ModelList>(`/v1/models${qs ? `?${qs}` : ""}`);
}

/**
 * Lightweight model count for headers/footers/SEO. Hits /v1/models?limit=1
 * and reads the `count` field so it stays in sync with the table without
 * pulling every model row. Single source of truth for "how many models".
 */
export async function getModelCount(): Promise<number> {
  const res = await fetchWithCache<ModelList>("/v1/models?limit=1");
  const count = res?.count;
  // A non-positive/unusable count is treated as a failure so callers fall
  // back to their known-good constant rather than ever flashing 0.
  if (typeof count !== "number" || count <= 0) throw new Error("Invalid model count");
  return count;
}

/**
 * Lightweight provider count (all registered providers) for footers/SEO.
 * Hits /v1/providers and reads the `count` field. Throws on a non-positive
 * count so callers fall back rather than flashing 0.
 */
export async function getProviderCount(): Promise<number> {
  const res = await fetchWithCache<ProviderList>("/v1/providers");
  const count = res?.count;
  if (typeof count !== "number" || count <= 0) throw new Error("Invalid provider count");
  return count;
}

const SSR_HEADERS = { "X-SSR-Secret": SSR_SECRET };

export async function getModel(modelId: string): Promise<ModelDetail> {
  const res = await fetch(`${API_URL}/v1/models/${modelId}`, { next: { revalidate: ISR_REVALIDATE }, headers: SSR_HEADERS });
  if (!res.ok) throw new Error(`Model not found: ${res.status}`);
  return res.json();
}

export async function getModelHistory(modelId: string, days: number = 30): Promise<ModelHistory> {
  const res = await fetch(`${API_URL}/v1/models/${modelId}/history?days=${days}`, { next: { revalidate: ISR_REVALIDATE }, headers: SSR_HEADERS });
  if (!res.ok) throw new Error(`History not found: ${res.status}`);
  return res.json();
}

export async function getModelEndpoints(modelId: string): Promise<ModelEndpoints> {
  const res = await fetch(`${API_URL}/v1/models/${modelId}/endpoints`, { next: { revalidate: ISR_REVALIDATE }, headers: SSR_HEADERS });
  if (!res.ok) throw new Error(`Endpoints not found: ${res.status}`);
  return res.json();
}

// ============================================
// PROVIDERS
// ============================================

export interface ProviderSummary {
  name: string;
  is_zdr: boolean;
  is_eu_sovereign: boolean;
  zdr_notes: string;
  eu_notes: string;
  model_count: number;
  avg_price: number | null;
  min_price: number | null;
  max_price: number | null;
  with_aa: number;
  endpoint_count: number;
  provider_type: string;
}

export interface ProviderList {
  count: number;
  providers: ProviderSummary[];
}

export interface ProviderModel {
  model_id: string;
  name: string;
  model_owner: string;
  tier: string;
  context_length: number | null;
  aa_index_score: number | null;
  modality: string | null;
  is_reasoning: boolean;
  input_price_per_m: number;
  output_price_per_m: number;
  blended_price_per_m: number;
  sit_score: number | null;
  sit_adjusted_price: number | null;
  fetched_at: string;
  source: string;
  hosting_type: string;
  quantization: string;
  is_zdr: boolean;
  is_eu_sovereign: boolean;
}

export interface ProviderTierBreakdown {
  count: number;
  avg_price: number;
  min_price: number;
  max_price: number;
}

export interface ProviderQualityProbe {
  ttft_ms: number | null;
  throughput_tps: number | null;
  success: boolean;
  error_type: string | null;
  probed_at: string | null;
}

export interface ProviderQuality {
  total_probes: number;
  successful_probes: number;
  avg_ttft_ms: number | null;
  min_ttft_ms: number | null;
  max_ttft_ms: number | null;
  avg_throughput_tps: number | null;
  success_rate: number | null;
  last_probe: string | null;
  probe_model: string | null;
  recent_probes: ProviderQualityProbe[];
}

export interface ProviderDetail {
  name: string;
  is_zdr: boolean;
  is_eu_sovereign: boolean;
  zdr_notes: string;
  eu_notes: string;
  model_count: number;
  direct_model_count: number;
  provider_type: string;
  owners: string[];
  models: ProviderModel[];
  tiers: Record<string, ProviderTierBreakdown>;
  quality?: ProviderQuality;
}

export async function getProviders(): Promise<ProviderList> {
  return fetchWithCache<ProviderList>("/v1/providers");
}

export async function getProviderDetail(providerName: string): Promise<ProviderDetail> {
  const res = await fetch(`${API_URL}/v1/providers/${encodeURIComponent(providerName)}`, { next: { revalidate: ISR_REVALIDATE }, headers: SSR_HEADERS });
  if (!res.ok) throw new Error(`Provider not found: ${res.status}`);
  return res.json();
}

// Convenience aliases used by homepage
export async function getCompositeLatest(_revalidate: number = 60): Promise<SITLatest> {
  return getSITLatest();
}

export async function getCompositeHistory(days: number = 30, _revalidate: number = 60): Promise<SITHistory> {
  return getSITHistory(days);
}

export function formatPrice(n: number): string {
  return "$" + n.toFixed(2);
}

export function formatPct(n: number): string {
  if (n === 0) return "0%";
  const a = Math.abs(n);
  return (n < 0 ? "\u2193 " : "\u2191 ") + a.toFixed(1) + "%";
}

export function pctColor(n: number): string {
  return n < 0 ? "#22c55e" : n > 0 ? "#ef4444" : "#7a7a7a";
}

export function sitColor(s: number | null | undefined): string {
  if (!s) return "#5f5f5f"; // No SIT score (no AA score)
  return s < 100 ? "#22c55e" : s <= 100 ? "#e5e5e5" : "#C4A038";
}

export function tierColor(tier: string): string {
  const map: Record<string, string> = {
    frontier: "#C4A038",
    standard: "#5b8def",
    budget: "#22c55e",
    micro: "#7a7a7a",
  };
  return map[tier.toLowerCase()] || "#7a7a7a";
}

export function capitalizeTier(tier: string): string {
  return tier.charAt(0).toUpperCase() + tier.slice(1);
}

export function providerInitials(provider: string): string {
  return provider
    .replace(/[^A-Za-z0-9 ]/g, " ")
    .trim()
    .split(/\s+/)
    .map((w) => w[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

const PROVIDER_DOMAINS: Record<string, string> = {
  "OpenAI": "openai.com",
  "~Openai": "openai.com",
  "Anthropic": "anthropic.com",
  "~Anthropic": "anthropic.com",
  "Google": "google.com",
  "~Google": "google.com",
  "Deepseek": "deepseek.com",
  "~Deepseek": "deepseek.com",
  "Meta": "meta.com",
  "Meta Llama": "meta.com",
  "Microsoft": "microsoft.com",
  "Amazon": "amazon.com",
  "Mistralai": "mistral.ai",
  "Cohere": "cohere.com",
  "Qwen": "qwen.com",
  "Tencent": "tencent.com",
  "Baidu": "baidu.com",
  "Bytedance": "bytedance.com",
  "Bytedance Seed": "bytedance.com",
  "Xiaomi": "xiaomi.com",
  "Z Ai": "z.ai",
  "xAI": "x.ai",
  "~X Ai": "x.ai",
  "Moonshotai": "moonshot.ai",
  "~Moonshotai": "moonshot.ai",
  "Ai21": "ai21labs.com",
  "Perplexity": "perplexity.ai",
  "Nvidia": "nvidia.com",
  "Minimax": "minimaxi.com",
  "Stepfun": "stepfun.com",
  "Meituan": "meituan.com",
  "Nousresearch": "nousresearch.com",
  "Upstage": "upstage.ai",
  "Rekaai": "reka.ai",
  "Sakana": "sakana.ai",
  "Writer": "writer.com",
  "Allenai": "allenai.org",
  "Inclusionai": "inclusionai.com",
  "Ibm Granite": "ibm.com",
  "Inception": "inceptionlabs.ai",
  "Kwaipilot": "kwaipilot.com",
  "Thinkingmachines": "thinkingmachines.ai",
  "Poolside": "poolside.ai",
  "Mancer": "mancer.ai",
  "Morph": "morph.ai",
  "Arcee Ai": "arcee.ai",
  "Aion Labs": "aion-labs.ai",
  "Nex Agi": "nexagi.ai",
  "Perceptron": "perceptron.ai",
  "Deepcogito": "deepcogito.com",
  "Cognitivecomputations": "cognitivecomputations.com",
  "Anthracite Org": "anthropic.com",
  "Gryphe": "gryphe.com",
  "Sao10K": "sao10k.com",
  "Thedrummer": "thedrummer.ai",
  "Undi95": "undi95.com",
  "Relace": "relace.ai",
};

export function providerFaviconUrl(provider: string): string {
  const domain = PROVIDER_DOMAINS[provider] || PROVIDER_DOMAINS[provider.toLowerCase()];
  if (!domain) return "";
  // Serve from local /favicons/ directory (self-hosted, no third-party DNS lookup)
  return `/favicons/${domain}.png`;
}

// --- Provider submissions (public self-serve listing) ---

export interface ProviderSubmission {
  provider_name: string;
  api_base_url: string;
  website?: string;
  api_key?: string;
  country?: string;
  is_eu_sovereign?: boolean;
  is_zdr?: boolean;
  zdr_notes?: string;
  contact_email?: string;
  notes?: string;
}

export interface SubmissionResult {
  id: number;
  status: string;
  endpoint_probe?: { ok: boolean; model_count: number; detail: string };
  message: string;
}

/** POST a provider pricing submission to the review queue. No auth needed. */
export async function submitProvider(
  sub: ProviderSubmission
): Promise<SubmissionResult> {
  const res = await fetch(`${API_URL}/v1/providers/submit`, {
    method: "POST",
    cache: "no-store",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(sub),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { error?: string }).error || `Submission failed (${res.status})`);
  }
  return res.json();
}
