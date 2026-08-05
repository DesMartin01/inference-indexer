import { NextRequest } from "next/server";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const SSR_SECRET = "inferenceindexer-ssr-2026";

// Simple in-memory cache for API responses
const cache = new Map<string, { data: unknown; ts: number }>();
const CACHE_TTL = 60_000; // 1 minute

async function fetchWithCache<T>(endpoint: string): Promise<T> {
  const cached = cache.get(endpoint);
  if (cached && Date.now() - cached.ts < CACHE_TTL) {
    return cached.data as T;
  }

  const res = await fetch(`${API_URL}${endpoint}`, {
    next: { revalidate: 60 },
    headers: { "X-SSR-Secret": SSR_SECRET },
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  const data = await res.json();
  cache.set(endpoint, { data, ts: Date.now() });
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
  sit_score: number;
  change_24h: number;
  change_7d: number;
  fetched_at: string;
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

export async function getModel(modelId: string): Promise<ModelDetail> {
  const res = await fetch(`${API_URL}/v1/models/${modelId}`, { next: { revalidate: 60 } });
  if (!res.ok) throw new Error(`Model not found: ${res.status}`);
  return res.json();
}

export async function getModelHistory(modelId: string, days: number = 30): Promise<ModelHistory> {
  const res = await fetch(`${API_URL}/v1/models/${modelId}/history?days=${days}`, { next: { revalidate: 60 } });
  if (!res.ok) throw new Error(`History not found: ${res.status}`);
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

export function sitColor(s: number): string {
  return s < 0.5 ? "#22c55e" : s <= 1.0 ? "#e5e5e5" : "#C4A038";
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
  return `https://www.google.com/s2/favicons?domain=${domain}&sz=64`;
}
