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

## External review: Grok adversarial test (Sep 3)

Grok independently tested the API with 5 agent-shaped jobs (support, coding, research, EU compliance, sales volume). Full findings:

### Bug found and FIXED same day
**`modality: "text"` excluded vision-capable models.** Grok's ZDR + $1 + non-reasoning query returned 0. Root cause: DB has 96 pure `text->text` but **209 vision-capable `text+X->text` models** - the filter excluded the 209. A vision-capable model can do text-only jobs. Fix: `"text"` now matches both (`text->text OR text+X->text`). Grok's empty-set scenario now returns 4 (gemma-3-27b $0.168, mistral-small-3.2 $0.1875...). Lesson: an "honest empty set" can still be a filter bug masquerading as honesty.

### Confirmed accurate (accept, don't argue)
- **Cost/IQ is a price-efficiency sort, not task fitness.** Five different jobs collapsed onto the same cheap long-context reasoners. Correct criticism: recommend is `filter_models(policy) -> shortlist`, not `choose_model_for_task(prompt)`.
- **AA>=35 gate is not enforced in recommend results.** Verified: low-AA models (Sao10K aa=23.9, cpiq $0.077) rank top on cheap queries. This is by design (gate applies to what the pipeline computes) but the docs claim reads otherwise. Fix the docs, not the gate.
- **Reasoning-token caveat is real and material.** Blended price understates reasoning-model cost.
- **GET /v1/recommend returns 405.** Grok's harness tried GET first. Fix: add GET with query-param constraints as an alias (agents/proxies sometimes can't POST), or at least a 405 with Allow header pointing at POST.
- **`suggestions: []` on unknown explain IDs.** Agent needs canonical ID knowledge; recommend is the discovery step. Acceptable, but richer suggestions would help.
- **Explain is the stronger agent tool.** Grok's verdict: "recommend proposes; explain justifies and gives a host." Their proposed loop (recommend -> explain -> check privacy flags on the actual host -> skip null-endpoint picks -> cache on as_of) matches the PRD's intent exactly.

### Build next (priority order from this feedback)
1. **task/use_case hint on recommend** (support/coding/research/extraction) - the single biggest gap: "choose_model_for_task" needs a task dimension. Even a coarse enum that adjusts ranking (e.g. precision->down-rank reasoning, coding->prefer high-AA) beats nothing. Validate enum against Phase -1 conversations.
2. **Privacy flags at the endpoint level** - zdr/eu on the specific host in endpoint_config, not model-level "some provider matches". Grok: "easy to mis-route if the agent treats the flag as certified."
3. **GET alias for recommend** + 405 Allow header.
4. **Docs fix**: AA>=35 gate claim vs reality; state clearly Cost/IQ = price-efficiency sort.
5. **endpoint_config completion**: every verified-provider model should have a config (backfill was done for 3, check rate).
6. Later (FR-15 dependent): latency/uptime in ranking; tool-calling/JSON-mode signal.

### Strategic takeaway
Grok's framing is the product positioning, for free: **"useful infrastructure, not a decision brain."** Procurement tool for agents: high value. Router/replacement for evals: explicitly not. The combined loop (recommend -> explain -> verified host) is the embed pattern to document in llms.txt recipes and the FR-8 embed kit.
