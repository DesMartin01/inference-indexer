import { type NextRequest, NextResponse } from "next/server";
import { updateSession } from "@/lib/supabase/middleware";

// ---------------------------------------------------------------------------
// Lean dead-slug guard
//
// Google and other crawlers hit /models/{slug}/{model} and /providers/{name}
// URLs for providers/models that have been renamed or removed from the index.
// In App Router, a `notFound()` inside a streamed route returns HTTP 200 with a
// <noindex> tag (a "soft 404"), which Google reports under "Excluded by
// noindex". To return a *true* HTTP 404 instead, we probe the provider slug /
// name here, before the page streams, and short-circuit with a real 404.
//
// Renames are already handled by 301/308 redirects in next.config.ts (they run
// BEFORE Proxy). This guard only catches slugs that no longer exist at all.
//
// To keep it fast we cache the live model/provider list at module scope with a
// short TTL. If the API is unreachable or slow we pass through rather than risk
// 404-ing a real page.
// ---------------------------------------------------------------------------

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface LiveSlugs {
  modelProviderSlugs: Set<string>;
  providerNames: Set<string>;
  ts: number;
}

let liveCache: LiveSlugs | null = null;
const CACHE_TTL_MS = 300_000; // 5 minutes
const FETCH_TIMEOUT_MS = 2_500;

async function fetchLiveSlugs(): Promise<LiveSlugs | null> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
  try {
    // Model provider slugs come from the model list (model_id = slug/model).
    // Provider page names come from the providers list (the /providers/{name}
    // URLs are built from the providers endpoint's `name` field, which differs
    // from the model `provider` field for some providers, e.g. "Z.AI" vs
    // "Z Ai"). So we fetch both.
    const [modelsRes, providersRes] = await Promise.all([
      fetch(`${API_URL}/v1/models?limit=500`, {
        cache: "no-store",
        headers: { "X-SSR-Secret": "inferenceindexer-ssr-2026" },
        signal: controller.signal,
      }),
      fetch(`${API_URL}/v1/providers`, {
        cache: "no-store",
        headers: { "X-SSR-Secret": "inferenceindexer-ssr-2026" },
        signal: controller.signal,
      }),
    ]);
    if (!modelsRes.ok || !providersRes.ok) return null;

    const [modelsData, providersData] = await Promise.all([
      modelsRes.json(),
      providersRes.json(),
    ]);
    const models: Array<{ model_id: string }> = modelsData.models || [];
    const providers: Array<{ name: string }> = providersData.providers || [];

    const modelProviderSlugs = new Set<string>();
    for (const m of models) {
      const slash = m.model_id.indexOf("/");
      if (slash > 0) modelProviderSlugs.add(m.model_id.slice(0, slash));
    }
    const providerNames = new Set<string>();
    for (const p of providers) {
      if (p.name) providerNames.add(p.name);
    }

    return { modelProviderSlugs, providerNames, ts: Date.now() };
  } catch {
    return null; // pass through on any API failure
  } finally {
    clearTimeout(timer);
  }
}

async function getLiveSlugs(): Promise<LiveSlugs | null> {
  if (liveCache && Date.now() - liveCache.ts < CACHE_TTL_MS) return liveCache;
  const fresh = await fetchLiveSlugs();
  if (fresh) liveCache = fresh;
  return fresh;
}

export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Only guard crawler-facing GET requests for model and provider detail pages.
  if (
    request.method === "GET" &&
    (pathname.startsWith("/models/") || pathname.startsWith("/providers/"))
  ) {
    const live = await getLiveSlugs();
    if (live) {
      if (pathname.startsWith("/models/")) {
        const slug = pathname.slice("/models/".length).split("/")[0];
        if (slug && !live.modelProviderSlugs.has(slug)) {
          return NextResponse.json(
            { error: "Not found" },
            { status: 404, headers: { "X-Robots-Tag": "noindex" } },
          );
        }
      } else if (pathname.startsWith("/providers/")) {
        const name = decodeURIComponent(
          pathname.slice("/providers/".length).split("/")[0],
        );
        if (name && !live.providerNames.has(name)) {
          return NextResponse.json(
            { error: "Not found" },
            { status: 404, headers: { "X-Robots-Tag": "noindex" } },
          );
        }
      }
    }
  }

  // The /admin routes use their own session cookie (ADMIN_SECRET) and must
  // NOT be touched by the Supabase middleware, which can drop the admin
  // cookie on refresh. Short-circuit them so the admin pages keep their
  // own auth gate.
  if (request.nextUrl.pathname.startsWith("/admin")) {
    return NextResponse.next({ request });
  }
  return await updateSession(request);
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|css|js)$).*)",
  ],
};