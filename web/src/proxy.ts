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
  modelIds: Set<string>;
  // True only when the model list fetch covered the whole catalogue (the API
  // caps a single page at 500; a sub-500 page means nothing was left). The
  // exact-ID guard only 404s on complete lists, so partial fetches never
  // 404 a model that just fell outside the fetched window.
  modelIdsComplete: boolean;
  providerNames: Set<string>;
  ts: number;
}

let liveCache: LiveSlugs | null = null;
const CACHE_TTL_MS = 300_000; // 5 minutes
// Covers two paginated model-list pages plus the providers fetch on a cold
// cache. A miss here fails open (no 404 guard for 5 min), so err generous.
const FETCH_TIMEOUT_MS = 8_000;

async function fetchLiveSlugs(): Promise<LiveSlugs | null> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
  try {
    // Fetch ALL pages of the model list (API caps a page at 500) so the
    // exact-ID guard has a complete catalogue. Full model_ids are collected
    // so dead exact URLs (e.g. legacy endpoint-host slugs like
    // sambanova/gpt-oss-120b) 404 before rendering — the slug-level check
    // alone lets them through to a soft-404 page.
    const allModels: Array<{ model_id: string }> = [];
    const PAGE = 500;
    let complete = false; // true iff a page came back with fewer than PAGE rows
    let modelsOk = true;
    for (let offset = 0; ; offset += PAGE) {
      const res = await fetch(`${API_URL}/v1/models?limit=${PAGE}&offset=${offset}`, {
        cache: "no-store",
        headers: { "X-SSR-Secret": "inferenceindexer-ssr-2026" },
        signal: controller.signal,
      });
      if (!res.ok) {
        modelsOk = false;
        break;
      }
      const data = await res.json();
      const page: Array<{ model_id: string }> = data.models || [];
      allModels.push(...page);
      if (page.length < PAGE) {
        complete = true;
        break;
      }
      if (offset > 5_000) break; // hard stop: catalogue can't be this big
    }

    const providersRes = await fetch(`${API_URL}/v1/providers`, {
      cache: "no-store",
      headers: { "X-SSR-Secret": "inferenceindexer-ssr-2026" },
      signal: controller.signal,
    });
    if (!modelsOk || !providersRes.ok) return null;
    const providersData = await providersRes.json();
    const providers: Array<{ name: string }> = providersData.providers || [];

    const modelProviderSlugs = new Set<string>();
    const modelIds = new Set<string>();
    for (const m of allModels) {
      modelIds.add(m.model_id);
      const slash = m.model_id.indexOf("/");
      if (slash > 0) modelProviderSlugs.add(m.model_id.slice(0, slash));
    }
    const providerNames = new Set<string>();
    for (const p of providers) {
      if (p.name) providerNames.add(p.name);
    }

    return {
      modelProviderSlugs,
      modelIds,
      modelIdsComplete: complete,
      providerNames,
      ts: Date.now(),
    };
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
    // Do NOT guard static pages that live under /providers/ (e.g. the
    // self-serve submission page). Only the dynamic /providers/{name}
    // detail route should be checked against live provider names.
    const isStaticProviderPage =
      pathname === "/providers/submit" ||
      pathname === "/providers/submit/";
    const live = await getLiveSlugs();
    if (live && !isStaticProviderPage) {
      if (pathname.startsWith("/models/")) {
        const rest = pathname.slice("/models/".length);
        const slug = rest.split("/")[0];
        if (slug && !live.modelProviderSlugs.has(slug)) {
          return NextResponse.json(
            { error: "Not found" },
            { status: 404, headers: { "X-Robots-Tag": "noindex" } },
          );
        }
        // Exact-ID guard: the provider slug exists but the model doesn't
        // (e.g. legacy endpoint-host slugs). The API list is paginated (limit
        // 500) and the catalogue is ~670, so a one-page miss is not proof of
        // death — only 404 when the fetched list is complete (fewer than the
        // page size) or the ID appeared on a fetched page.
        const requestedId = decodeURIComponent(rest);
        if (
          slug &&
          live.modelProviderSlugs.has(slug) &&
          !live.modelIds.has(requestedId) &&
          live.modelIdsComplete
        ) {
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
    // Admin pages manage their own session cookie (ADMIN_SECRET) and must NOT
    // be touched by the Proxy or Supabase middleware — running middleware over
    // them was intermittently dropping the admin auth cookie and logging the
    // owner out. Exclude /admin entirely so its route-handler Set-Cookie is
    // never re-wrapped.
    "/((?!admin|_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|css|js)$).*)",
  ],
};