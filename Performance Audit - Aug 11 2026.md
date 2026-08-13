# InferenceIndexer.ai Performance & SEO/AiEO Audit

**Date:** 11 August 2026
**Auditor:** Frank Drebin
**URL tested:** https://inferenceindexer.ai (Vercel: web-gamma-fawn-69.vercel.app)
**API backend:** http://34.246.208.210:8000 (FastAPI/uvicorn, AWS Dublin)

---

## Executive Summary

The site is **server-rendered (SSR) via Next.js 16 on Vercel** with `force-dynamic` on every page load. This means every visitor triggers a fresh round of API calls to the backend, which in turn hits Supabase Postgres. The Vercel edge cache is bypassed (`cache-control: private, no-cache, no-store`), making the site feel slow because TTFB is inflated by backend round-trips.

Three areas need attention: **rendering strategy** (biggest UX/SEO win), **JS payload size** (Core Web Vitals), and **AiEO completeness** (structured data gaps).

---

## 1. Performance Findings

### 1.1 No Vercel Edge Caching (CRITICAL)

| Metric | Value |
|--------|-------|
| Vercel TTFB (homepage) | **169ms** (good, but cache MISS) |
| Vercel cache status | `MISS` on every request |
| `cache-control` header | `private, no-cache, no-store, max-age=0, must-revalidate` |
| Page rendering mode | `dynamic = "force-dynamic"` (bypasses ISR) |

**Root cause:** `page.tsx` has `export const dynamic = "force-dynamic"` and `export const revalidate = 60`, but `force-dynamic` takes precedence and disables all caching. Every page load triggers 3 backend API calls via `Promise.all`:
- `GET /v1/sit/composite/latest`
- `GET /v1/sit/composite/history?days=30`
- `GET /v1/models?limit=500`

**Impact:** Vercel can never serve a cached page. Every visitor gets a cold render with 3 backend round-trips. This is the single biggest performance bottleneck.

**Fix:** Remove `force-dynamic`, keep `revalidate = 60` (ISR with 60-second revalidation). The data is hourly anyway; a 60-second stale window is fine. This alone would cut TTFB to ~20ms for cached requests and let Vercel's edge network do its job.

### 1.2 API Response Times

| Endpoint | TTFB | Size |
|----------|------|------|
| `/v1/sit/composite/latest` | **1.6s** | 887 bytes |
| `/v1/models?limit=50` | 360ms | 24.7KB |
| `/v1/models?limit=500` (homepage) | Not measured, likely ~1s+ | ~50KB est. |

**Issues:**
- The composite/latest endpoint takes **1.6 seconds** for 887 bytes of data. This is a database query problem, not a network problem (the VPS is in Dublin, same as the frontend's origin).
- The API sets `Cache-Control: no-store` on the composite/models endpoints, meaning browsers and CDNs can't cache API responses either.
- No `ETag` or `Last-Modified` headers on any API response, so conditional requests aren't possible.

**Fixes:**
- Add `Cache-Control: public, max-age=300` to `/v1/sit/composite/latest` and `/v1/models` (data updates hourly; 5-minute cache is safe)
- Profile and optimize the composite query (likely missing index or doing a full table scan on `price_snapshots`)
- Add ETag support for conditional requests

### 1.3 JavaScript Payload

| Asset | Raw | Brotli | Notes |
|-------|-----|--------|-------|
| `0y_e64z0k_u0p.js` | 224KB | 73KB | Largest chunk (likely React/Next framework) |
| `08n6j5cy3t5hv.js` | 245KB | 67KB | App-specific code |
| `3wnn44pz0zf13.js` | 155KB | 44KB | |
| `0c0hxoamwjsbw.js` | 110KB | 41KB | |
| `20es43nb27oti.js` | 34KB | 9KB | |
| `1bkn25p8m_o2-.js` | 36KB | 11.5KB | |
| **Total JS** | **~820KB raw** | **~246KB br** | |
| CSS | 19.3KB | - | Single file |
| HTML | 377KB raw | 29.5KB br | Inline RSC data (full model table) |

**Issues:**
- 246KB of compressed JS is above the 170KB budget Google recommends for interactivity
- The homepage HTML is **377KB** because the entire 45-row model table is server-rendered as inline RSC payload. With `limit=500` on the API call, this could balloon to 3MB+ of HTML if all models render.
- Brotli compression is working (good)

### 1.4 External Requests (56 Google Favicon calls)

The homepage preloads and renders **56 favicons** from `https://www.google.com/s2/favicons`. These are:
- Third-party domain (DNS lookup, TLS handshake to Google)
- Not cached locally
- Preloaded with `rel=preload; as=image` in the `<head>`, blocking initial render
- Many are for models that are below the fold

**Fix:** Self-host favicons locally (download once, serve from Vercel's CDN), or lazy-load them. At minimum, remove the `rel=preload` hints for favicons.

### 1.5 Google Analytics (render-blocking)

`gtag/js` is loaded with `async` but still in the `<head>`. It adds a DNS lookup + connection to `googletagmanager.com` on every page load. Consider deferring or using Partytown.

### 1.6 No og:image

The site has no `og:image` meta tag. Social sharing shows no preview image. This hurts click-through rates from Twitter/LinkedIn.

---

## 2. SEO Findings

### 2.1 Good: Already in place
- ✅ SSR (server-rendered HTML, not client-only)
- ✅ Structured data: `WebSite`, `Organization`, `Dataset` schema.org types
- ✅ `robots.txt` with sitemap reference
- ✅ Sitemap with 327 URLs (homepage, pages, all models)
- ✅ Canonical URLs
- ✅ Meta descriptions, OpenGraph, Twitter cards
- ✅ `llms.txt` file for AI agents

### 2.2 Gaps

| Issue | Impact | Fix |
|-------|--------|-----|
| No `og:image` | Social shares show no preview image | Create a branded share image |
| Sitemap `changefreq: hourly` on homepage | Crawler fatigue | Change to `daily`; data updates hourly but crawlers don't need to check every hour |
| No `hreflang` tags | Single language, low priority | Skip for now |
| Model pages not in sitemap with `lastmod` from data | Crawlers don't know when prices change | Add `<lastmod>` from `fetched_at` per model |
| No breadcrumb structured data | Missing rich result eligibility | Add `BreadcrumbList` schema to model/provider pages |

---

## 3. AiEO (AI Engine Optimization) Findings

### 3.1 Good: Already in place
- ✅ `llms.txt` file at `/llms.txt` (well-structured, covers API + pages)
- ✅ `/for-agents` page (agent-focused onboarding)
- ✅ Structured data (`Dataset` schema with `distribution` pointing to API)
- ✅ OpenAPI spec at `api.inferenceindexer.ai/openapi.json`
- ✅ API has anonymous key endpoint (`POST /v1/auth/anonymous`)

### 3.2 Gaps

| Issue | Impact | Fix |
|-------|--------|-----|
| No `llms-full.txt` | AI agents get summary, not full detail | Create comprehensive version with methodology, all endpoints, example responses |
| No `ai-plugin.json` | Not discoverable by ChatGPT plugins | Add OpenAI plugin manifest |
| No `well-known/ai-manifest.json` | Not discoverable by AI crawlers | Add per the `agent-search-optimisation` skill |
| `llms.txt` references `api.inferenceindexer.ai` but actual API is on raw IP `34.246.208.210:8000` | AI agents following `llms.txt` will hit a domain that may not resolve | Set up `api.inferenceindexer.ai` DNS pointing to the VPS, or document the IP clearly |
| No FAQ schema | Missing rich result eligibility for "how is SIT calculated" type queries | Add `FAQPage` schema to methodology page |
| No `SoftwareApplication` or `WebApplication` schema | AI agents don't know this is a tool/API service | Add structured data |

---

## 4. Prioritized Action Plan

### Tier 1: Quick wins (hours, biggest impact)

| # | Action | Effort | Impact |
|---|--------|--------|--------|
| 1 | **Remove `force-dynamic` from `page.tsx`**, keep `revalidate = 60` | 1 line | Eliminates cold renders on every visit; Vercel edge cache kicks in |
| 2 | **Add `Cache-Control: public, max-age=300` to `/v1/sit/composite/latest` and `/v1/models` API responses** | 2 lines | Browser + CDN caching of API responses |
| 3 | **Remove favicon `rel=preload` hints** from `<head>` | Few lines in Header component | Eliminates 11 render-blocking preload hints |
| 4 | **Investigate composite/latest query** taking 1.6s | 30 min profiling | Likely missing index or expensive aggregate |

### Tier 2: Medium effort (1-2 days)

| # | Action | Effort | Impact |
|---|--------|--------|--------|
| 5 | **Self-host provider favicons** (download once, serve from `/public/favicons/`) | Script + cron | Eliminates 56 third-party requests per page load |
| 6 | **Create `og:image`** branded share image | 30 min in Figma/Canva | Social sharing previews |
| 7 | **Add `ai-plugin.json`** and `well-known/ai-manifest.json` | 30 min | AiEO discoverability |
| 8 | **Add FAQ schema** to methodology page | 30 min | Rich result eligibility |
| 9 | **Reduce model table initial render** (paginate or virtualize) | 2-3 hours | Cuts HTML payload from 377KB to ~50KB |

### Tier 3: Strategic (1 week+)

| # | Action | Effort | Impact |
|---|--------|--------|--------|
| 10 | **Set up `api.inferenceindexer.ai` domain** with HTTPS (Cloudflare proxy or Caddy) | 1-2 hours | Professional API URL, enables CDN caching, fixes `llms.txt` consistency |
| 11 | **Code-split the ModelTable** (dynamic import, load interactive features on demand) | 1 day | Reduce JS payload by ~100KB |
| 12 | **Add `BreadcrumbList` schema** to model/provider pages | 2 hours | Rich results |
| 13 | **Create `llms-full.txt`** with full methodology + example API responses | 1 hour | AiEO depth |
| 14 | **Add ETag/304 support** to API | 1-2 hours | Conditional requests save bandwidth + compute |
| 15 | **Consider Cloudflare in front of VPS API** for edge caching of API responses | Half day | Global API performance |

---

## 5. Expected Impact of Tier 1 Changes

| Metric | Current | After Tier 1 |
|--------|---------|-------------|
| TTFB (cached) | 169ms (MISS every time) | ~20-30ms (edge HIT) |
| TTFB (uncached) | 169ms + 1.6s API | ~200ms (ISR) |
| LCP | Likely 2-3s | Likely <1s |
| API calls per page load | 3 (always cold) | 0 (cached) or 1 (revalidation) |
| Favicon requests | 56 to Google | 0 (removed from preload) |

The `force-dynamic` removal alone will transform the site from "feels slow" to "feels instant" for the majority of visitors, because Vercel's edge will serve the cached page and revalidate in the background.

---

## 6. Technical Details

### Current request waterfall (homepage, cold)
```
Browser → Vercel edge (MISS) → Vercel origin → Next.js SSR
  → Promise.all([
      fetch API /v1/sit/composite/latest (1.6s)
      fetch API /v1/sit/composite/history (???ms)
      fetch API /v1/models?limit=500 (???ms)
    ])
  → Render React tree (377KB HTML)
  → Stream to browser
  → Browser loads 246KB JS (br)
  → Browser fetches 56 favicons from Google
  → Browser loads gtag from Google
  → Hydration
```

### After Tier 1 (cached)
```
Browser → Vercel edge (HIT) → 20ms → Done
  (background: ISR revalidation every 60s)
```

### Files to modify
- `web/src/app/page.tsx` - remove `force-dynamic`
- `web/src/app/models/[...modelId]/page.tsx` - same, if present
- `web/src/app/methodology/page.tsx` - same, if present
- `web/src/app/api-docs/page.tsx` - same, if present
- `web/src/app/about/page.tsx` - same, if present
- `web/src/components/Header.tsx` - remove favicon preloads
- `api.py` - add `Cache-Control: public, max-age=300` to composite/models endpoints
- `api.py` - investigate/optimize composite query
