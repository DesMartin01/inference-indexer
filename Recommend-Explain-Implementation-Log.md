# II: Recommend/Explain Implementation Log (v1)

**Date:** 2026-09-02
**Status:** DEPLOYED + VERIFIED
**Related:** [[Recommend-Explain-Endpoint-Spec]] | [[II-PRD]] (FR-4, FR-5) | [[SIT-Redesign-Implementation-Spec]]

---

## What shipped

### 1. `/v1/recommend` (POST) — live
- Constraint-filtered ranking: budget, context_min, modality (text/vision/any), zdr, eu_sovereign, reasoning, providers. Requires >=1 constraint (400 otherwise).
- Ranks by Cost/IQ (`sit_adjusted_price` ASC). Quality gate AA>=35 via the pipeline. 308 of 728 active models rankable.
- Evidence-in-response: `why` (deterministic template, no LLM), `endpoint_config` (provider, base_url, native model id, `model_id_source`: verified|heuristic), per-field `as_of`, runner-ups, `ranking_basis`, disclaimer.
- Cache: 5-min in-process TTL, `X-Cache: HIT/MISS`. Cached 0.07s, warm 2.2s, cold up to 6s (per-request DB connections - pooling is a known future fix).
- `aa_index_score` added per-model after first live test showed it missing.

### 2. `/v1/explain` (GET) — live
- One call = pricing + 24h/7d changes + history summary (trend = first-3 vs last-3 average, labelled estimate) + all endpoints + cheapest hand-verified endpoint + ZDR/EU availability + AA score.
- 404 with suggestions for unknown IDs.

### 3. Supporting infrastructure
- `endpoint_provider_config` table: 15 providers with hand-verified base_urls (live-tested: 200 unauth or 401-auth-required = path confirmed).
- `provider_model_alias` table: canonical -> native model IDs per provider (125 aliases: Novita 43+53, Venice 16+9, DeepInfra 16, Fireworks 4, SambaNova 4, Mistral 0 - catalog skew). Daily refresh 4am via `refresh_provider_aliases.py` on Lightsail.
- MCP server v0.3.0: `recommend_models` + `explain_model` tools added (10 total). Pushed to GitHub `76d84cf`.
- llms.txt + api-docs page updated and deployed to Vercel.
- II MCP server wired into Frank's own Hermes config (`mcp_servers.inferenceindexer`, HTTP transport) - standing demo, loads on new sessions.

### 4. Fresh-agent actionability test (FR-4): PASS
One recommend response (providers=["Fireworks"]) -> constructed and executed a real chat call on Fireworks (`accounts/fireworks/models/deepseek-v4-flash-0731`) using only `endpoint_config` + the provider key the agent already holds. Returned `SWITCH-OK`. Zero other lookups.

---

## Live test findings (invoicing scenario)

Query: precise-not-smart, <$1.50/M, large context. Findings:

1. **Default ranking surfaces reasoning models first** (they dominate raw Cost/IQ). For precision tasks they're wrong (thinking-token overhead). The `reasoning: false` filter fixes it, but agents may not think to set it. -> feeds the `use_case` field design for FR-4 v2; validate in Phase -1 conversations.
2. **`aa_index_score` was missing from recommend responses** - fixed and deployed (it reveals budget models score 13-24 vs the 40 reference; honest evidence for "doesn't need to be smart").
3. **3 Inclusionai models had no endpoint rows** (direct-connector priced, missed by the OpenRouter endpoints fetch). Backfilled from Novita's live API using their decimal price fields: `ling-2.6-flash` ($0.10/$0.30), `ling-2.6-1t` + `ring-2.6-1t` ($0.30/$2.50). Scenario now resolves 2-of-3 with verified endpoints.
4. `thedrummer/unslopnemo-12b` honestly unverified: hosted by NextBit/Parasail, no verified base_url (would need their API docs checked). Caveat shown, nothing faked.
5. **Data-quality issue found:** `model_endpoints` can list providers for models they don't actually serve via API (e.g. `z-ai/glm-5.2` @ Mistral, from a docs scrape; Mistral's live API 400s on every ID variant). `model_id_source` field is the guardrail; a scrape-vs-live reconciliation is future work.
6. **model_endpoints bloat:** hourly rows per model-provider, only 7-day cleanup = ~160k rows. A daily dedup (keep latest per model+provider) is a cheap maintenance win, not done yet.

---

## Ops notes

- Deploys: api.py -> scp to Lightsail + `sudo systemctl restart inferenceindexer-api` (approval-gated). Website: Vercel token needed (`vcp_...` supplied Sep 2; rotate it - it was pasted in chat).
- Vercel deploy must run from the repo root (vault project dir), not `web/` - the project's Root Directory setting is `web`. The `web/.vercel` link points at project `web` (prj_C0e8WrqLFJDyvSFo982LjuskjGCD).
- Historical data untouched throughout: 383,079 price_snapshots (Aug 4 -> present).
- Personal VPS security re-audited Sep 2: SSH is the only open inbound port (8000/9119/631 externally verified blocked; UFW default-deny; no docker bypass; MCP server config has zero references to the personal VPS IP; stale README default fixed on Lightsail).

## Open items

- [ ] DB connection pooling for the API (cold calls 2-6s vs <500ms target)
- [ ] model_endpoints daily dedup
- [ ] Scrape-vs-live reconciliation for model_endpoints (z-ai/glm-5.2 @ Mistral case)
- [ ] NextBit/Parasail verification (only if those models matter)
- [ ] Bake-off harness (blocked on Phase -1: the 20 constraint cards come from Des's demand-discovery conversations)
- [ ] `use_case` field on recommend (precision -> down-rank reasoning) - validate in Phase -1
