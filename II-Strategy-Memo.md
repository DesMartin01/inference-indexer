# Inference Indexer: Strategy Memo
**Becoming the #1 inference information resource for agents | v7, 29 Aug 2026**

> v7 revision: incorporates adversarial review (Grok, Claude Opus). Key correction: the recommend endpoints are the wedge, not the business. The business is the operational + compliance data feed, sold by subscription to the teams behind the agents. Demand discovery is now a formal gate before M1.

---

## Position

II is the #1 place on the web for agents' inference queries. Any question an agent has about inference, II answers: quality, recommendation, explanation, price, latency, uptime, privacy, ZDR, infra location, context window, rate limits, deprecations, best model for a job. Not a price index, not a benchmark site: an **answer layer embedded in agent workflows**, with the data pipeline as the moat.

Today: 711 models, 89 providers, hourly pipeline, 200k endpoint rows, MCP server built, public API with anonymous keys. The strongest independent inference data foundation on the web, and mostly invisible: MCP is on localhost, quality data has no endpoint, agents can only download tables, not ask questions.

The structural insight: **OpenRouter sells flow (conflicted: it sells the inference it rates). Artificial Analysis sells benchmarks to humans. Not Diamond sells routing decisions (black box, per-token tax). Nobody sells verified *state* — what changed, what broke, what's true right now, with receipts.** The agent market is forecast at $10.9-12B in 2026, ~45% CAGR, 100M+ agents within 18 months.

## Who pays (the correction from review)

**The agent is the user. The team behind the agent is the buyer.** Agents have no credit cards; the evidence-in-response design is a human-trust feature. And model selection is a design-time decision: a team picks a model, ships, revisits when something *changes*. The recurring need is not "recommend me a model" (a handful of decisions per quarter); it is **"tell me when what I chose stops being the right choice"** — a deprecation, a price move, a compliance change, an outage. That need is alert-shaped, which means subscription-shaped.

Therefore: **agents consume II free at runtime; their teams subscribe to the feed that guarantees what changes never blindsides them; gateways and frameworks license the same feed.** We charge operators for never missing what changes, not agents per question.

## Goal

**6-month headline: paid revenue started (30+ feed subscribers), 50-100 real embeds, recommend passing the 20-job constraint bake-off at ≥90% policy-correct, one framework docs citation.**

**12-month goal: $50k/month revenue**, conditional on the 6-month evidence: subscription math (100 teams × $500/mo avg) is the legible path; per-call revenue is a watched metric, not the model.

Supporting targets: deprecation feed catching every major model retirement within 24h, top-20 privacy graph published with sources and dates, 5 gateway/framework data-licensing conversations.

## Strategy: free answers for agents, subscription for operators

| Stage | State | Build | Who pays |
|---|---|---|---|
| Discover | llms.txt, sitemap | MCP registry listings, LLM-citable docs | — |
| Authenticate | Anonymous keys, one POST | Done | — |
| **Decide** | Missing | **`/v1/quality`, `/v1/recommend`, `/v1/explain`: free, the core agent surface** | — |
| Integrate | MCP built, not public | nginx route, TLS, registries | — |
| **Monitor** | Unbuilt | **Deprecation/outage/price-change feed + webhooks: THE paid product** | **Team subscription** |
| License | — | Catalog + feed licensing to gateways/frameworks | **B2B licensing** |

**Phase -1 (weeks 1-2): demand discovery, BEFORE M1.** 15 conversations with agent framework maintainers and platform teams (Des's network + outreach). Ask: what broke last quarter, what would you pay to have caught? Gate: if nobody names an inference-data problem unprompted, stop and replan before building. Two weeks of calls vs six months of building the wrong thing.

**Phase 0 (weeks 2-4): unblock.** Publish MCP (nginx + TLS + registries), `/v1/quality` endpoint, SSR model pages, **and the deprecation feed v1 (passive collection: status pages, changelogs, doc diffs)**. The core answers live; the paid product's data starts accruing.

**Phase 1 (weeks 3-6): the answer layer + the paid feed.** `/v1/recommend` + `/v1/explain` free (evidence-in-response, endpoint_config, actionability test). **Privacy/compliance schema + top-20 research promoted to Phase 1** (processing region, parent entity, ZDR eligibility + API exclusions, training default: "eu is not one bit"). **Feed subscription goes on sale** (early access pricing for design partners).

**Phase 2 (weeks 4-8): distribution.** llms.txt recipes, weekly data brief, **framework outreach promoted to core motion** (free keys, citation-ready stats, goal: one framework ships II in its docs), gateway licensing pitches (LiteLLM, Portkey, Cloudflare: customers, not competitors). 20-job constraint bake-off runs here; recommend must pass ≥90% before metering exists at all.

**Phase 2 (weeks 4-8): distribution.** (cont.) Deprecation feed becomes the marquee: "we caught it first" citations.

**Phase 3 (months 3-6): scale the feed.** Subscription tiers mature ($99-299/mo), gateway licensing deals, `/v1/forecast`, 3 more connectors. Per-call metering demoted to a usage metric; billing sits on the subscription, not the cacheable GET.

**Phase 4 (month 6+): enterprise-ready.** SLAs, bulk exports, redistribution licensing, procurement docs. Design partners from the subscriber base.

## Pricing (subscription-first)

| Tier | Price | What |
|---|---|---|
| Agent free | $0 | recommend/explain/quality, anonymous key, generous caps. The distribution |
| Feed: Team | $99-299/mo | Deprecation/outage/price webhooks, full history, privacy graph, priority freshness |
| Feed: Business | $499-999/mo | + compliance exports, SLA on feed delivery, multi-team seats |
| Licensing | $1-5k/mo | Gateways/frameworks embedding the catalog + feed in their products |
| Enterprise (Phase 4) | Contract | SLAs, bulk exports, redistribution rights |

Per-call metering: demoted to a watched metric. The healthy embed pattern (one resolve per session + webhook refresh) is exactly what a subscription monetizes; per-call punishes it.

## The three design answers (retained from v6)

1. **The dependency paradox costs less than it looks.** Cache-first serving, TTL matched to data freshness, stale-with-timestamp never a bare 500. Compute scales with cache hits, not traffic. (PRD FR-4 + NFR-5b.)
2. **Actionability is a closed test, not an open data hunt.** A fresh agent, given one recommend response and the keys it already holds, constructs and executes the model switch with zero *other* lookups. (Corrected per review: keys live with the agent; ZDR org-gating acknowledged.) (PRD FR-4 + Appendix 1 guard.)
3. **Impartiality + receipts win trust; freshness discipline becomes the moat once people pay for it.** The maintenance treadmill (89 connectors, scrapers, doc moves) is a cost today and a moat the day feed subscribers depend on it.

## Resources

**Effort:** ~15 Frank sessions + 30 min/week automation; **Des: Phase -1 conversation sprint (2 weeks, ~10 hrs) then 2-3 hrs/week outreach. The demand gate is Des's gate.**

**Cash:** ~$150-300/mo through Phase 2; ~$5-6k total exposure over 6 months. Downside bounded; the option is cheap. (Appendix 2.)

## Key risks

1. **No demand evidence yet.** Four documents of architecture, zero named prospects. Phase -1 exists to fix this before M1. If the 15 conversations don't surface the pain, replan.
2. **Metering never activates / free tier absorbs all volume.** Solved structurally: revenue sits on the subscription, not the call counter. Feed subscribers pay for freshness, not volume.
3. **AA's reaction is unknowable.** Grok says fast-follow is the clock; Opus says being ignored is worse. Either way: the AA license conversation happens this week, the no-AA ranking must exist before FR-4 ships, and the plan stops depending on their behaviour.
4. **Maintenance treadmill.** 89 connectors + scrapers on one person + an agent, forever. Becomes a moat only when feed subscribers depend on it: which is the point of the subscription model.
5. **Trust incident.** One wrong ZDR claim or stale uptime number cited by an enterprise buyer damages the impartiality position itself. Weighted higher than before: privacy claims carry sources, dates, and "we aggregate, we don't certify."
6. **Frontier models eat the generic lookup.** Real for "what does X cost" (their training data is stale; we're not); weak against the feed and compliance data, which a model cannot self-generate. Watch, don't fear.
7. **Not Diamond standardises from above.** Evidence per response is defensible in a way a ranking score is not. Never become a black box ourselves.
8. **Ergonomics beats impartiality.** MCP + recommend + SDKs are the wedge; framework citation (FR-10, now P1) is the distribution motion that matters.
9. **If after 3 months agents query but don't embed, the problem is answer quality, not distribution.** If conversations don't convert to subscribers by month 3, the problem is the feed's positioning, not its engineering.

Full detail: [Appendix 1: Data Collection](ii-data-collection-appendix.md) | [Appendix 2: Costs](ii-costs-appendix.md) | [Appendix 3: PRD](II-PRD.md)
