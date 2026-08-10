# InferenceIndexer — Phase 1: Provider Quality Probe Runner

**Status:** Design / decision-complete, awaiting Des sign-off
**Created:** Aug 9 2026
**Supersedes:** the "Planning" section of `Quality-Metrics-Plan.md` — this is the implementable spec for its Phase 1.

## Why this is the priority (the moat)

The index is currently 1D: price per million tokens. OpenRouter + AA give price and *model-level* capability scores. **Nobody** measures *provider-level* latency / uptime / error rate — you have to build your own probes to get it. That is exactly the barrier the `Direct-Provider-API-Strategy.md` calls the moat: "Anyone can scrape OpenRouter. Nobody else is going direct to 70+ provider APIs." Same logic applies to quality: provider-level quality data is not published anywhere; it must be measured. It cannot be scraped from a competitor.

This converts "a $1.50/M model with 98% uptime and 3s TTFT" from invisible to comparable against "the same model at $2/M with 99.9% uptime and 200ms TTFT." That is a real purchasing decision our competitors' price-only indexes cannot answer.

## Scope of Phase 1 (latency + reliability only)

Measure, per provider endpoint:
- **TTFT** (time to first token, ms)
- **Throughput** (tokens/sec, from stream)
- **Uptime / availability** (success vs failure over time)
- **Error rate + latency consistency** (HTTP 429/500/timeout; p50 vs p95 vs p99)

Hardware/GPU type is **Phase 4** (deferred — harder, no clean instrument). This phase is latency + reliability, which is instrumentable with probes.

## Key decision resolved: probe, not source

"Source" was considered. Artificial Analysis publishes *model-level* latency/throughput, NOT per-provider, and no public API for the per-provider breakdown. Provider status pages give uptime but not latency/throughput, and aren't machine-queryable consistently. **There is no existing source for provider-level quality — it must be probed.** Decision: build the probe runner. This is Phase 1 of the existing plan.

## Probe design

### The probe call
Every provider exposes an **OpenAI-compatible** `/v1/chat/completions` (streaming). The probe:
1. Picks a small, cheap, widely-hosted model on that provider (e.g. a Llama/gemma-class model) — one representative probe model per provider, NOT every model (keep volume sane).
2. Sends a fixed tiny prompt (e.g. "Reply with OK.").
3. Measures TTFT = time from request send until first streamed chunk.
4. Measures tokens/sec = total tokens / total stream time.
5. Records success/failure + HTTP status + per-request latency (for distribution).

Use `stream=True`. Deterministic prompt + small `max_tokens` so cost stays negligible.

### Provider coverage — staged
- **Tier A (start):** the providers we already have live API keys for + no-auth providers that list a probe-able model. ~8-12 providers. This is enough to prove the product and be credible.
- **Tier B (expand):** the rest of the 70+ as keys/access are confirmed via the provider-signup workflow. Do NOT block Phase 1 on full coverage — ship Tier A, grow from there.

### Probe frequency — **HOURLY (Des decision, Aug 9 2026)**
**Every hour, rolling, per provider** (staggered, not a synchronized burst). Chosen over 15-min to be gentler on providers. Trade-off accepted: p99/uptime confidence builds more slowly (roughly 24 samples/day vs 96). 429-aware backoff still applies. This is the cadence the design proceeds with.

### Storage — new table `provider_latency_snapshots`
```sql
CREATE TABLE provider_latency_snapshots (
  id BIGSERIAL PRIMARY KEY,
  provider TEXT NOT NULL,            -- endpoint_provider name
  probe_model TEXT NOT NULL,         -- canonical model id probed
  ttft_ms FLOAT,
  throughput_tps FLOAT,
  http_status INT,
  success BOOLEAN NOT NULL,
  error_type TEXT,                   -- 'timeout' | 'rate_limit' | '5xx' | 'connection' | NULL
  probed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_provider_latency_provider_time
  ON provider_latency_snapshots(provider, probed_at DESC);
```
RLS: public READ, service-role WRITE (same pattern as price_snapshots).

### Scheduling
A new cron entry on the VPS, e.g. `*/15 * * * *` running `probe_quality.py`. Runs alongside the existing hourly + 3am pipeline jobs. **Does not touch the price pipeline.** The probe runner and the scraper are independent so a probe interruption never blocks pricing.

### API surface
New endpoints (all gated by the same SSR/anon auth):
- `GET /v1/providers/{name}/quality` → agg: avg/p95 TTFT, avg throughput, uptime %, error rate over 7d/30d windows.
- Optionally `GET /v1/quality` → per-provider quality summary for a comparison/screener surface.

### Surfacing (Phase 2, after ~30 days of data)
Per your existing plan: endpoint rows on the provider/model detail page get latency + uptime columns (7d + 30d). The **30-day credibility floor before public surfacing** stays — a day of probes is not trustworthy, a month is.

## What this cost / risk is
- **Cost:** negligible per probe (tiny prompt × frequent ≈ a few cents/month/provider).
- **Risk:** some providers block aggressive probing. Mitigation: 15-min cadence is polite, 429-aware backoff, stop probing a provider that returns 403 on the probe path (don't fight them — note it as "not probed").
- **No production-DB mutation beyond the new snapshots table.** The probe runner writes its own table; it never touches `price_snapshots` or `models`.

## Explicit non-goals for Phase 1
- No hardware/GPU inference (Phase 4).
- No multi-model-per-provider probing (one representative model/prov is enough to start).
- No public surfacing until 30 days of data.
- No changes to the price/SIT methodology (quality is additive data, not yet folded into the index).

## Acceptance criteria
1. `probe_quality.py` runs standalone, writes to `provider_latency_snapshots` with real TTFT/throughput/success data.
2. Cron runs it every 15 min; log shows no crash loop.
3. A manual API query returns the aggregate quality for a Tier-A provider.
4. After 30 days, data is surfaced on provider/model pages (Phase 2).

## Next steps (awaiting sign-off)
1. Des confirms the design + the 15-min cadence + Tier-A-first sequencing.
2. I build `probe_quality.py` + migration for the snapshots table.
3. I wire the cron + a test run, then the `/v1/providers/{name}/quality` endpoint.
4. After 30 days, Phase 2 surfacing.

## Open decisions needing Des
- **15 min vs hourly** — 15 gives better p99/uptime signal in a day; hourly is gentler on providers. Recommend 15.
- **Which probe model per provider** — recommend the cheapest widely-hosted Llama/gemma-class per provider for cost; or a provider's own flagship if we want their real-world flagship latency. Recommend the cheap one for Phase 1.
- **Whether to probe only Tier A (~8-12) first or stand up all reachable** — recommend Tier A to prove the loop fast.