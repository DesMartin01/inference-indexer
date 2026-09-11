# Appendix 2: Costs
**Inference Indexer strategy | v3, 29 Aug 2026**

> Aligned to strategy memo v7 (subscription-first): revenue sits on feed subscriptions + licensing, not per-call metering. Per-call volume is a watched metric. Serving stays cache-first and cheap.

## Build + embed phase (months 1-6): ~$150-300/mo

| Item | Cost/mo | Notes |
|---|---|---|
| Lightsail VPS | $5-20 | Current box: 1GB/2vCPU/38GB, 10% used. Upgrade to 2-4GB when probes + MCP traffic land |
| Supabase | $25 | **Required now: free tier caps 500MB, DB is at 847MB** (~300-400MB/mo growth). Pro = 8GB + daily backups (free tier has none: 300k rows of price history unprotected) |
| Vercel | $0-20 | Hobby tier. Pro when subscriptions (commercial) go live |
| Probe credits | $20-80 | ~250 tiered pairs (top 20 providers: 2-4 models each; long tail: 1). Per-provider spend caps |
| LLM-assisted curation | $10-40 | Privacy-policy parsing + normalization across 89 providers |
| Domain | ~$3 | ~$40/yr, Blacknight |
| Frank's inference | $10-50 | OpenRouter usage, variable |
| Marketing | $0-50 | Free channels until Phase -1 demand evidence validates spend (MCP registries, GitHub, llms.txt, embed kit) |
| **Total** | **~$150-300** | |

## Revenue model (subscription-first)

| Tier | Price | What |
|---|---|---|
| Agent free | $0 | recommend/explain/quality, anonymous key, generous caps. The distribution |
| Feed: Team | $99-299/mo | Deprecation/outage/price webhooks, event history, privacy graph, priority freshness |
| Feed: Business | $499-999/mo | + compliance exports, feed delivery SLA, multi-seat |
| Licensing | $1-5k/mo | Gateways/frameworks embedding catalog + feed |
| Enterprise (Phase 4) | Contract | SLAs, bulk exports, redistribution rights |

**Why subscription fixes the arithmetic both reviews caught:** per-call metering contradicted our own caching architecture (a customer who caches locally hits us 24×/day per constraint set; $50k needed 50M metered calls). Model selection is design-time; the recurring need is "tell me when what I chose stops being the right choice" — alert-shaped, therefore subscription-shaped. **Path to $50k/mo (12-month goal, conditional):** 100 teams × $500/mo avg, or 30 teams + 3-5 gateway licensing deals. First evidence: 30+ subscribers and bake-off ≥90% by month 6.

Per-call metering: demoted to a watched metric. Healthy embeds (one resolve per session + webhook refresh) are what subscriptions monetize; per-call punishes them.

## Demand discovery first (Phase -1)

Two weeks, ~15 conversations (Des), $0. Gate: if nobody names an inference-data problem unprompted, replan before building. This is the cheapest possible falsification of the whole plan and it precedes M1.

## Deferred to Phase 4 (month 6+, gated)

| Item | Cost | Notes |
|---|---|---|
| AA commercial license | $100-500/mo (unknown) | **Conversation this week** (needed before FR-4 ships, regardless of their sales cycle) |
| Legal (contracts, DPA, entity) | $3-5k one-off | Only at Phase 4 gate |
| Enterprise sales/tooling | $50-150/mo | CRM, procurement docs |
| Conference/sponsorship | $250-1k lumpy | Only if licensing pipeline justifies |

## Funding from outset (6-month runway)

| Phase | Months | Cash/mo | Total |
|---|---|---|---|
| Demand discovery + build (Phases -1 to 1) | 1-2 | ~$200 | ~$400 |
| Distribution + first subscribers (Phase 2) | 3-4 | ~$300 | ~$600 |
| Feed scaling (Phase 3) | 5-6 | ~$300-800 | ~$2,000 |
| Contingency (AA license, slips) 30% | | | ~$1,000 |
| **Total funding needed from outset** | | | **~$4,000-5,000** |

Downside is bounded by design: no sales motion, no per-call infrastructure risk, and the demand gate (Phase -1) can stop the spend at week 2. If feed velocity validates, metered-subscription revenue covers scale costs from month 4 onward.

## Cost controls

1. Per-provider probe spend caps (hard limits in probe config)
2. raw_data trimming after 90 days + monthly rollup tables (keeps Supabase at $25 indefinitely)
3. AA scores display-only, not load-bearing (product survives losing them)
4. Marketing spend gated on Phase -1 demand evidence, not calendar
5. Cache-first serving: infra scales only when subscriptions do
6. No per-call billing infrastructure to build or run (demoted to a metric): Stripe subscriptions only
