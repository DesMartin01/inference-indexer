# Inference Indexer: Product Requirements Document
**Agent Answer Layer + Operational Feed | v4, 29 Aug 2026**

**Source:** Strategy memo v7 + Appendix 1 (data) + Appendix 2 (costs)
**Status:** Draft for Des's review
**Owner:** Des Martin. Build: Frank.

> v3 revision: incorporates adversarial review (Grok, Claude Opus). The deprecation/operational feed is promoted to THE paid product (subscription-shaped, not call-metered). Privacy/compliance ontology promoted to P1. Per-call metering demoted to a watched metric. Demand discovery is a formal Phase -1 gate. Actionability test corrected: agent constructs the call given keys it already holds.

---

## 1. Problem

Agents (and their builders) must answer inference questions: which model, which provider, what price, how fast, how reliable, what privacy posture, is it still available. Today those answers are scattered across provider docs, aggregator pages, and benchmark sites, mixed with stale data. OpenRouter covers ~60 providers and is structurally conflicted (it sells the inference it rates). Nobody offers a single impartial answer layer that agents can call as part of their own logic — and nobody indexes *what changes*: deprecations, outages, price moves, policy changes. Every agent maintainer has been broken by an unannounced model retirement; almost none has ever wished to pay per query to compare tokenizers.

**The two-product insight:** agents need free answers at runtime; the teams behind them need a subscription that guarantees the answers never go stale or silently wrong. The feed is the business; recommend is the distribution.

## 2. Product vision

One platform: (a) free answer endpoints (`/v1/recommend`, `/v1/explain`, `/v1/quality`) agents embed via MCP/REST, evidence-rich, anonymous-key; (b) a subscription operational feed (deprecations, outages, price moves, privacy changes) with webhooks for the teams behind the agents; (c) catalog + feed licensing for gateways and frameworks.

**Success metrics (6 months):** 30+ feed subscribers (paid revenue started), 50-100 real embeds, recommend passing the 20-job constraint bake-off at ≥90% policy-correct, one framework docs citation, deprecation feed catching every major model retirement within 24h.
**12-month goal: $50k/mo revenue**, conditional on 6-month evidence (100 teams × $500/mo avg is the legible path).

## 3. Functional requirements

### Phase -1 — Demand discovery (weeks 1-2, GATE)

**FR-0 Demand validation.**
- 15 conversations with agent framework maintainers and platform teams (Des's network + outreach). Script: what broke last quarter? what would you pay to have caught? would you license a deprecation/catalog feed? at what price?
- Output: named prospect list, pain evidence, willingness-to-pay signals, licensing interest from ≥1 gateway.
- **Gate: if nobody names an inference-data problem unprompted, stop and replan before M1.** Two weeks of calls vs six months of building the wrong thing.

### P0 — Unblock (weeks 2-4)

**FR-1 Publish MCP server.**
- MCP service (`inferenceindexer-mcp.service`, Lightsail :8899, currently bound to 127.0.0.1) gets nginx reverse proxy route + TLS via existing Let's Encrypt path.
- Route: `https://api.inferenceindexer.ai/mcp` (or `mcp.inferenceindexer.ai` if cleaner cert handling).
- Auth: existing anonymous-key flow; public read-only tier unchanged.
- Submit to MCP registries/directories (official registry, parse.bot, community lists).
- Acceptance: external MCP client completes tools/list + one query over TLS from outside the VPS.

**FR-2 `/v1/quality` endpoint.**
- Expose `provider_latency_snapshots` (TTFT, throughput, success rate, error types): per-provider 24h/7d/30d windows: uptime %, p50/p95 TTFT, tokens/s.
- Method + vantage point documented in response (`vantage: dublin-eu-west`), per-window sample counts.
- Acceptance: one GET returns current reliability of every probed provider; listed in api-docs + llms.txt.

**FR-3 SSR model pages.**
- Model detail pages render full data server-side (no "Loading model..." for non-JS crawlers).
- Acceptance: `curl` of any model page contains price/quality data in initial HTML.

**FR-3b Deprecation/operational feed v1 (passive).**
- Collect provider status pages, changelogs, doc diffs hourly (existing anomaly detection extended): deprecations, outages, new models, price moves.
- Stored as structured events; surfaced via `/v1/feed` endpoint (event list, filterable) + homepage "what changed" section.
- Acceptance: next major deprecation appears in the feed within 24h of the provider announcing it.

### P1 — Answer layer + the paid feed (weeks 3-6)

**FR-4 `/v1/recommend` — the free core.**
- Input: constraints JSON `{context_min, budget_max_usd_per_m, modality, privacy, reasoning: bool, use_case: enum(...), region}`. All optional except one of budget/use_case.
- Output: ranked models with per-field scores + `why` string + per-field as-of timestamps.
- **Evidence-in-response:** `ranking_basis` (method + methodology_version), `data_sources` (price source, probe coverage, AA score if used, each with `as_of`), `alternatives_considered` (runner-ups with the reason they lost). "Recommendations with receipts, not routing with a black box." (Receipts are the human-buyer trust feature.)
- **Hot-swappable answer:** `endpoint_config` per result (provider base URL, model ID, auth scheme, current per-call price).
- Ranking: Cost/IQ, filtered by hard constraints, tie-broken by probe quality. AA scores enrich but are NOT load-bearing; **the no-AA ranking must exist before FR-4 ships.**
- **Vantage honesty:** `vantage` always returned in quality fields; **latency dropped from the sort when requested region ≠ probe vantage** (a confident, timestamped, region-wrong ranking is worse than none).
- **Serve architecture:** cache-first (Cloudflare + TTL matched to data freshness); stale-with-`as_of` on error, never a bare 500.
- **Actionability test (corrected):** a fresh agent, given one recommend response **and the provider keys it already holds**, constructs and executes the model switch with zero *other* lookups. Keys live with the agent, never in our payload; org-gated ZDR cannot be hot-swapped from a public response and is signposted, not asserted. Measured with a scripted fresh-agent harness. New fields enter only when the test fails.
- Acceptance: bake-off constraint set (20 jobs, built from Phase -1 conversations) passes ≥90% policy-correct; <500ms; evidence trail + endpoint_config in response.

**FR-5 `/v1/explain`.**
- One call returns everything about a model or provider: current price (input/output/cache/batch), price history summary, capability flags, probe stats (with vantage), privacy claims (source + verified date), context, deprecation status.
- Acceptance: single GET fully answers "what is DeepInfra's GLM 5.2 endpoint like right now".

**FR-6 Consistency layer.**
- One reconciled model count (definition documented) used by homepage, API health, llms.txt, sitemap.
- Every API response: `as_of` per field group + `methodology_version`.
- Acceptance: no two public surfaces report different model counts.

**FR-6b Privacy/compliance schema + top-20 graph (promoted from FR-16).**
- New schema replacing the `privacy: [zdr|eu|self_host]` enum ("eu is not one bit"): `processing_regions`, `legal_entity_parent`, `zdr_eligible` + `zdr_api_exclusions`, `training_default`, `retention_policy`, `eu_sovereign`, `verified_at`, `source_url`.
- Researched for top 20 providers (~90% of query volume), every claim sourced + dated, "we aggregate, we don't certify."
- Surfaced in `/v1/explain`, recommend filters, provider pages, and the feed (privacy-policy changes are events).
- Acceptance: top-20 graph published with sources and dates; privacy filter in recommend uses the real fields.

**FR-6c Feed subscription on sale.**
- Early-access: Team tier $99-299/mo (webhooks on deprecations/outages/price moves, full event history, privacy graph, priority freshness), Business $499-999/mo (+ compliance exports, feed SLA, multi-seat).
- Stripe subscription billing; per-key webhook endpoints, HMAC-signed.
- Acceptance: first subscriber paying; webhook delivery end-to-end on real events.

### P2 — Distribution (weeks 4-8)

**FR-7 llms.txt v2 + recipes.** Worked 2-call examples, auto-generated endpoint inventory, MCP link. Acceptance: fresh LLM-session test cites II.
**FR-8 Embed kit + graceful degradation pattern.** Copy-paste snippets (Python/TS/MCP config) for `/v1/recommend`, including the fail-safe reference pattern (cache last-good with TTL, fail open, never hard-depend). Acceptance: stranger to working call in <5 minutes, fail-safe included.
**FR-8b Thin SDKs.** Python + TS SDKs generated from OpenAPI, PyPI/npm, used in all snippets. Acceptance: pip/npm install → typed recommend call in <3 lines.
**FR-9 Weekly data brief pipeline.** Cron assembles price moves/outages/new models into draft + chart; Des edits and posts. Acceptance: zero manual data pulls.
**FR-10 Framework + gateway motion (promoted: the core distribution).**
- Frameworks (LangChain, CrewAI, AutoGen ecosystems): free keys, citation-ready stats, goal: one ships II in docs.
- **Gateways as licensing customers, not competitors** (LiteLLM, Portkey, Cloudflare): pitch catalog + deprecation feed licensing from the Phase -1 conversations. Goal: one licensing deal in negotiation.
- Acceptance: one framework citation OR one gateway licensing negotiation active.

**FR-10b 20-job constraint bake-off.** Test set of 20 realistic constraint cards (from Phase -1 conversations) run against `/v1/recommend`; ≥90% policy-correct required before any billing beyond free tiers exists. Acceptance: bake-off harness runs in CI; results published.

### P3 — Scale the feed (months 3-6)

**FR-11 Subscription billing + usage metrics.**
- Stripe subscriptions per the pricing table (Team/Business/Licensing). Metered per-call **demoted to a usage metric** (watched, not billed): the healthy embed pattern (one resolve per session + webhook refresh) is what subscriptions monetize; per-call punishes it.
- Usage dashboard per key: embeds, calls, webhook deliveries, tier.
- Acceptance: first 30 subscribers; billing, dunning, self-serve upgrade all no-contact.
**FR-12 Webhooks (feed delivery).** `alert_subscribers` table activated: deprecation, outage, price-move, new-model, privacy-change alerts. Retries, HMAC, per-event-type filters. Acceptance: alert fires end-to-end on injected test event.
**FR-13 `/v1/forecast`.** TPI trend + volatility → 90-day probabilistic projection, explicit confidence bands, labelled estimates. Acceptance: backtest vs held-out history shows calibrated bands.
**FR-14 Three connectors.** Cerebras, Mistral, SiliconFlow direct APIs (existing `fetch_with_auth` pattern, canonical IDs). Past 1,000 models. Keys from Des.

### Data collection (parallel track, per Appendix 1)

**FR-15 Tiered probe expansion.** probe_quality.py → ~250 pairs (top 20 providers × 2-4 models, long tail × 1), per-provider spend caps, research identity, batch discounts. Acceptance: 250 pairs probed hourly within budget.

### Phase 4 — Enterprise-ready (month 6+, gated)

**FR-18 Enterprise packaging.** SLAs, committed rates, bulk export endpoints, redistribution licensing, procurement docs (security page, DPA, ToS review), invoice billing. Design partners drawn from feed subscribers.
**Gate:** Phase 4 starts on 6-month evidence (30+ subscribers, bake-off ≥90%) or Des calls the gate.

## 4. Non-functional requirements

> **Scope boundary (guards the data hunt):** II is actionable *through the switch* (decide → integrate → monitor). Execution quality is the agent's job and AA's lane, out of bounds. New data enters only when the FR-4 actionability test fails, never because the data exists.

- **NFR-1 Freshness:** per-field `as_of`; price hourly; probes hourly; privacy claims re-verified quarterly; feed events within 24h of source.
- **NFR-2 Honesty:** every derived number documents method + vantage point; estimates labelled.
- **NFR-3 Survivability:** product functions without AA data (no-AA ranking ready before FR-4) and without any single provider's cooperation. **Customer side: agents never hard-depend on II** (FR-8 fail-safe pattern; stale-with-timestamp over erroring).
- **NFR-4 Cost:** infra ≤$300/mo through Phase 2; probe spend hard-capped per provider. Customer cost is subscription-based and predictable: no per-call surprise bills.
- **NFR-5 Embeddability:** every answer endpoint single-call, stable schema, versioned, cacheable, <500ms.
- **NFR-5b Read-path economics:** cache-first serving; compute scales with cache hits, not traffic. 1M calls/mo ≈ $5-10; 10M ≈ $25; 100M ≈ $150-250. Serving HA/SLA is Phase 4 spend priced into contracts.
- **NFR-6 Atomic deploys:** pipeline + API + website ship together (existing rule).
- **NFR-7 Publish our own reliability.** II's own status page + uptime SLO on answer endpoints AND feed delivery. Dogfood the product on ourselves.
- **NFR-8 Multi-region probes (roadmap, not v1):** Dublin + one US + one APAC box. **Until then: `vantage` returned in every quality-bearing response; latency dropped from recommend sort when requested region ≠ vantage.** A confident region-wrong ranking is worse than no latency field.
- **NFR-9 Privacy liability discipline:** every privacy claim sourced + dated; changes to privacy claims are feed events; "aggregate, not certify" stated on every privacy surface.

## 5. Out of scope (for now)

Enterprise contracts/SLAs (Phase 4, gated); own benchmark suite; execution-quality data (AA's lane); real usage/volume data (provider partnerships); non-inference modalities beyond current embeddings scope (until demand shown).

## 6. Dependencies & decisions needed from Des

1. **Phase -1 conversation sprint: Des's gate.** 15 conversations before M1. Happens first, before any build.
2. **AA license conversation: this week.** Redistribution terms + no-AA fallback sign-off before FR-4 ships.
3. Probe budget approval (~$20-80/mo, per-provider caps) before FR-15.
4. Stripe account (subscriptions) before FR-6c goes on sale.
5. API keys for FR-14 connectors.
6. Bake-off job list sign-off (the 20 constraint cards) before it gates billing.

## 7. Milestones

| Milestone | Scope | Target | Metric gate |
|---|---|---|---|
| M-1 | FR-0 demand discovery | End week 2 | ≥1 named pain from ≥5 conversations; ≥1 gateway licensing interest; else replan |
| M1 | FR-1,2,3,3b live (answers + feed v1 public) | End week 4 | MCP reachable externally; quality endpoint live; feed catches a real event |
| M2 | FR-4,5,6,6b answer layer + privacy graph | End week 7 | recommend passes bake-off ≥90%; no-AA ranking live; top-20 privacy graph published |
| M3 | FR-6c,7,8,8b,9,10,10b: subscriptions on sale + distribution | End week 8 | First paying subscriber; framework citation or gateway negotiation open |
| M4 | FR-11,12,13,14 feed scaling | Month 5 | 30+ subscribers; feed SLA met 30 consecutive days |
| M5 | Review: revenue evidence; Phase 4 gate | Month 6 | Paid revenue trajectory + embed velocity OR replan |
| Review gates | After M-1 (demand), M2 (quality), M4 (feed traction), M5 (revenue) | | |

## 8. Competitive context (why this spec)

- **Not Diamond** sells per-request routing. We refused that seat (impartiality) and their pricing model with it. FR-4's evidence-in-response + FR-6b privacy graph + the operational feed are the counter: evidence and state, not routing.
- **Artificial Analysis** may fast-follow or ignore us (reviews disagree); the plan stops depending on their behaviour: no-AA ranking before FR-4, probe history as the moat, feed as the product they'd have to rebuild from scratch.
- **Gateways are customers, not threats** (corrected from v3): they need neutral catalog + deprecation data and would rather license than build. Licensing to five is faster revenue than competing for their embeds.
- **Frontier-model lookups** are stale by construction; the feed and compliance data are the parts a model cannot self-generate.
