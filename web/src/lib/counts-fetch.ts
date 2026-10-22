// Client-safe count fetchers (B8 companion to lib/api.ts, which is
// `server-only`). lib/use-model-count.ts runs in the browser, so it must not
// import from api.ts. These mirror api.ts's getModelCount/getProviderCount
// (same endpoints, same >0 validation) but as plain client fetches: no ISR
// directives (server-only feature) and no secret header (counts are public
// API reads). The hook's module-level cache is the client-side cache here.
// Keep this file in sync with api.ts's versions if the endpoints change.

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchCount(endpoint: string, countKey: string): Promise<number> {
  const res = await fetch(`${API_URL}${endpoint}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  const data = (await res.json()) as Record<string, unknown>;
  const count = data?.[countKey];
  // A non-positive/unusable count is treated as a failure so callers fall
  // back to their known-good constant rather than ever flashing 0.
  if (typeof count !== "number" || count <= 0) {
    throw new Error(`Invalid count from ${endpoint}`);
  }
  return count;
}

export async function getModelCount(): Promise<number> {
  return fetchCount("/v1/models?limit=1", "count");
}

export async function getProviderCount(): Promise<number> {
  return fetchCount("/v1/providers", "count");
}
