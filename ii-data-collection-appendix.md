# Appendix 1: Data Collection
**Inference Indexer strategy | v3, 29 Aug 2026**

> Aligned to strategy memo v7: the data build serves two products — the free answer layer (`/v1/quality`, `/v1/recommend`, `/v1/explain`) and the paid operational + compliance feed (deprecations, outages, price moves, privacy changes). Probe history and freshness discipline are the moat against fast followers and gateways: copiers can copy endpoints, not years of freshness discipline. **Gateways and frameworks are licensing customers of this data, not competitors.**

## What agents and teams need (the query taxonomy)

| Category | Fields | Current coverage | Product home |
|---|---|---|---|
| Cost | input/output, cache-hit/write, batch discounts, volatility | Strong (711 models, 89 providers, hourly) | Free answers |
| Capability | tool calling, structured output, vision/audio, reasoning + thinking budget, supported params, caching, fine-tuning | Partial (OpenRouter publishes free for ~60 providers; our 29 exclusive providers are gaps) | Free answers |
| Performance | TTFT, tokens/s, p50/p95, uptime % | **4 of 82 fresh-priced providers probed.** Biggest gap | Free answers (+ vantage honesty) |
| **Operational** | outages, deprecations, versioning, policy changes | **Missing entirely. Unowned category.** | **THE paid feed** |
| **Privacy** | ZDR eligibility + API exclusions, retention, training default, processing regions, parent entity | Scattered in raw_data JSON, no schema | **Paid feed + compliance graph** |
| Limits | RPM/TPM, max output, concurrency | Mostly missing | Free answers (documented-unknown default) |
| Fit | best model for job, context window, knowledge cutoff | Partial (AA covers 304/711 models) | Free answers |
| Integration | OpenAI-compatible?, endpoints, streaming | Partial | Free answers |

Price is the most complete column and the least defensible. **Operational and privacy data are empty everywhere, including OpenRouter: the categories the subscription sells.** Model selection is a design-time decision; the recurring need is "tell me when what I chose stops being the right choice" — that is the feed.

## Data sourcing: three tiers

**Tier 1: flowing, ~$0.** Price, context, modality, tokenizer from provider APIs we already hit hourly. Done.

**Tier 2: the build (~6-7 Frank sessions, $20-150/mo).**
- **Latency/uptime probes.** Unit = provider-model pair (different models sit on different GPUs/regions). 1,500 fresh pairs exist; full matrix is unaffordable ($121-983/mo). Tier instead: top 20 providers get 2-4 models, long tail gets 1 → ~250 pairs, ~$20-80/mo. Probe from Dublin, documented vantage point (AA publishes us-central1, we publish ours). **Vantage honesty rule: latency never ranks when requested region ≠ vantage.** Research identity ("InferenceIndexer Research"), per-provider spend caps, batch/free-tier discounts. Existing `probe_quality.py` design extends.
- **Operational feed collection (promoted to core).** Passive: status pages, changelogs, doc diffs, pricing-page diffs, hourly. Active: probes catch silent outages. Provider self-reporting via the existing submission flow. Every event: source, timestamp, category.
- **Privacy/compliance graph.** Schema: `processing_regions`, `legal_entity_parent`, `zdr_eligible` + `zdr_api_exclusions`, `training_default`, `retention_policy`, `eu_sovereign`, `verified_at`, `source_url`. Top 20 providers first (~90% of query volume). Every claim sourced + dated; privacy-policy changes become feed events. We aggregate, we don't certify.
- **Rate limits.** Not published; empirical probing, carefully, or documented-as-unknown.

**Tier 3: deferred until a customer names it.** Own benchmarks (AA already does it), real usage volumes (providers never share), execution-quality data (the agent's job). Don't build speculative data.

## Blockers and mitigations

| Blocker | Reality | Mitigation |
|---|---|---|
| AA licensing | Free API = attribution only; redistribution in recommend responses = commercial license, price unknown | **Conversation this week.** No-AA ranking ships before FR-4. Product must survive losing AA |
| Providers won't share | Not needed for price/latency/capabilities (public or self-probed). Needed for: rate limits, volumes, private deals | Build on public + probed. Provider submission flow (exists) becomes the front door for corrections |
| Probe cut-off risk | Real but asymmetric: a provider refusing measurement gets a "denies independent verification" flag. Refusal is data. | Dedicated research identity, documented methodology, honest numbers. Refusal is a feature |
| Scraping fragility/ToS | Moonshot JS pages, docs moves; some ToS prohibit | Prefer official APIs and `.md` endpoints; isolated per-provider scrapers; hourly anomaly detection flags silent failures |
| Staleness = silent wrongness | A wrong ZDR claim to enterprise buyers is a trust-killer (weighted higher post-review) | Per-field timestamps, source links, top-20-first verification, quarterly re-verify, privacy changes are feed events, "aggregate, not certify" on every privacy surface |
| Free-riding | Copiers take snapshots, not the pipeline discipline | Moat = freshness + probes + feed history. Copier data decays the moment they stop paying maintenance |
| DB growth | 847MB now, ~300-400MB/mo | Trim raw_data after 90d, monthly rollups, Supabase Pro 8GB = 18+ months headroom |
| **Demand never materialises** | Four docs of architecture, zero named prospects | **Phase -1 gate: 15 conversations before M1. If nobody names the pain unprompted, replan.** |

## The operational-data opportunity (now the paid product)

Deprecations/outages: every agent maintainer has been broken by an unindexed deprecation; nobody serves this. Sources: (1) passive collection of status pages/changelogs/doc diffs, free and uncensorable; (2) active probes under research identity; (3) provider self-reporting via the existing submission flow. **Alert-shaped, therefore subscription-shaped: this is the product that fixes the pricing contradiction.**

## Actionability guard (what we will NOT collect)

The data hunt is bounded by the agent journey: discover → decide → integrate → monitor → **execute**. II's data responsibility ends at the switch: decide (evidence), integrate (endpoint config), monitor (feed + webhooks). **Execution quality** (did the model complete the user's task?) is out of bounds: chasing it means rebuilding AA's benchmark business, and it is never finishable. New fields enter the answer schema only when the PRD FR-4 actionability test (fresh agent + its own keys completes a model switch with zero external lookups) fails for lack of a field. Tier 3 stays deferred for the same reason.
