# II: /v1/recommend + /v1/explain Implementation Spec (v1)

**Date:** 2026-09-02
**Author:** Frank
**Status:** DRAFT — awaiting Des sign-off before coding
**Related:** [[II-PRD]] (FR-4, FR-5), [[II-Strategy-Memo]], [[SIT-Redesign-Implementation-Spec]]

---

## 0. What we verified before writing this

| Question | Answer |
|---|---|
| Can we rank models without quality data? | Yes: 308 of 728 active models have `sit_adjusted_price` (Cost/IQ). Ranking = Cost/IQ ascending. AA scores enrich context, not load-bearing. |
| ZDR / EU filters? | Provider-level flags in `providers` table (Venice, TensorX, AkashML, Phala are ZDR). 107 models sit on ZDR providers. The API already joins these (api.py line ~758). |
| Modality filtering? | `models.modality` has values like `text->text`, plus TTS/STT/embedding/image-gen variants. Recommend v1 filters to `text->text` by default. |
| Reasoning flag? | `models.is_reasoning` exists. Shown as a warning in results, not a filter (PRD: thinking tokens aren't in price). |
| Price history for explain? | `price_snapshots` back to Aug 3, plus `/v1/models/{id}/history` endpoint. |
| Probe/quality data? | 1 of ~73 providers only. **Deliberately excluded from v1 ranking** (PRD: data enters only when the actionability test fails). |

---

## 1. `/v1/recommend` — POST

**Purpose:** given constraints, return the best models. One call, ranked, with receipts and a hot-swap config. The agent should be able to switch models with zero other lookups.

### Request

```json
POST /v1/recommend
{
  "budget_max_usd_per_m": 1.0,       // optional: max blended $/M
  "context_min": 100000,             // optional: min context window tokens
  "modality": "text",                // optional: default "text" (-> text->text models)
  "zdr": false,                      // optional: require zero-data-retention providers
  "eu_sovereign": false,             // optional: require EU-sovereign providers
  "reasoning": null,                 // optional: null=any, true/false filter
  "exclude_reasoning_penalty": true, // optional: annotate reasoning models' prices as understated
  "limit": 5,                        // optional: 1-20, default 5
  "providers": []                    // optional: restrict to named endpoint providers
}
```

At least one of `budget_max_usd_per_m`, `context_min`, `zdr`, `eu_sovereign`, `reasoning`, or `providers` must be set (400 otherwise). Pure "no constraints" calls get a 400 with a pointer to `/v1/models`.

### Ranking

1. Candidates = active text->text models with `sit_adjusted_price` (the Cost/IQ quality gate, AA >= 35, already applied by the pipeline).
2. Hard filters: budget (blended price), context, ZDR/EU (via provider join), reasoning flag.
3. Rank by `sit_adjusted_price` ascending (Cost/IQ: price per GPT-4-equivalent token).
4. Per-model, pick the **cheapest endpoint provider** hosting it (from `model_endpoints`) for `endpoint_config`; if none, use the aggregate source.
5. If `exclude_reasoning_penalty` (default true): reasoning models get an annotation, not a rank change.

### Response (evidence-in-response)

```json
{
  "query": { ...echo of constraints..., "methodology_version": "0.2" },
  "recommendations": [
    {
      "rank": 1,
      "model_id": "meta/llama-4-scout",
      "name": "...",
      "tier": "standard",
      "blended_price_per_m": 0.65,
      "cost_per_iq": 0.42,
      "context_length": 327680,
      "is_reasoning": false,
      "zdr": false,
      "eu_sovereign": false,
      "why": "Cheapest Cost/IQ (0.42) of 47 models under $1.00/M with >=100k context",
      "endpoint_config": {
        "provider": "DeepInfra",
        "base_url": "https://api.deepinfra.com/v1/openai",
        "model_id_on_provider": "meta-llama/Meta-Llama-4-Scout",
        "input_price_per_m": 0.55,
        "output_price_per_m": 0.75
      },
      "as_of": {
        "price": "2026-09-02T09:00:00Z",
        "aa_score": "2026-08-30T00:00:00Z"
      },
      "caveats": ["reasoning model: thinking tokens not reflected in output price"]
    }
  ],
  "alternatives_considered": {
    "count": 47,
    "runner_ups": [ /* ranks 6-8 with the reason they lost */ ]
  },
  "ranking_basis": {
    "method": "cost_per_iq_ascending",
    "description": "Blended price x (40 / AA score). Lower is better. Quality gate AA >= 35.",
    "excludes": "Providers without verified pricing; models without AA scores (415 of 728)"
  },
  "disclaimer": "Estimates based on aggregated public pricing. Verify with the provider before committing spend."
}
```

### Implementation notes

- Single SQL query against `latest_prices` + `models` + `model_endpoints` + `providers` (the same join pattern api.py already uses for the ZDR filter). No new tables.
- Cache the ranking computation for 5 min (matching pipeline cadence + ISR) with in-process TTL cache; `X-Cache: HIT/MISS` header. Stale-with-`as_of` on upstream error, never a bare 500 (NFR-5b pattern).
- Auth: existing anonymous-key flow. Free tier rate limit applies.
- The `why` string is generated from the query shape (deterministic template), NOT an LLM. No model calls in the API path.
- `endpoint_config.base_url` comes from a provider→base_url mapping table we add now (one row per major endpoint provider, ~15 rows, hand-verified). Providers without a known base_url get `endpoint_config: null` and a caveat. **This table is the honest answer to "hot-swap" until we have verified endpoint inventory.**

---

## 2. `/v1/explain` — GET

**Purpose:** one call answers "what is model X like right now". Composition of data we already serve across four endpoints.

```json
GET /v1/explain?model_id=anthropic/claude-sonnet-5
```

### Response

```json
{
  "model_id": "anthropic/claude-sonnet-5",
  "name": "Claude Sonnet 5",
  "tier": "frontier",
  "context_length": 200000,
  "modality": "text->text",
  "is_reasoning": true,
  "as_of": "2026-09-02T09:00:00Z",
  "pricing": {
    "input_per_m": 3.0, "output_per_m": 15.0, "blended_per_m": 10.2,
    "cost_per_iq": 4.8,
    "change_24h": 0.0, "change_7d": -2.1, "change_30d": -12.5
  },
  "price_history_summary": {
    "days_observed": 30,
    "min_blended": 10.2, "max_blended": 13.4,
    "trend": "declining",
    "series_url": "/v1/models/anthropic/claude-sonnet-5/history?days=30"
  },
  "endpoints": [
    { "provider": "OpenRouter", "input": 3.0, "output": 15.0 },
    { "provider": "AWS Bedrock", "input": 3.0, "output": 15.0 }
  ],
  "cheapest_endpoint": { "provider": "OpenRouter", "blended_per_m": 10.2 },
  "privacy": {
    "zdr_available": false,
    "eu_sovereign_available": false,
    "note": "Provider-level claims, aggregated not certified. See providers endpoints for verification dates."
  },
  "quality": {
    "aa_score": 88.2,
    "aa_as_of": "2026-08-30T00:00:00Z",
    "probe_data": "insufficient coverage"   // honest placeholder until FR-2/FR-15
  },
  "methodology_version": "0.2"
}
```

### Implementation notes

- Composes: `latest_prices` + `price_changes_24h/7d` + `model_endpoints` + `providers` + models row. One SQL round-trip, or 2-3 cheap ones.
- 404 with a suggestions list (nearest model IDs by prefix) when unknown.
- Same auth/caching/rate-limit treatment as recommend.
- `price_history_summary.trend` = simple slope sign over the window; labelled as estimate (NFR-2).

---

## 3. What we are NOT doing in v1 (explicit)

| Excluded | Why |
|---|---|
| Quality/latency in ranking | 1/73 provider coverage. Enrichment only, and only once coverage is real (FR-15). |
| LLM-generated explanations | No model calls in the API path. Deterministic templates. Fast, cheap, no hallucinations. |
| `region` constraint | Meaningless until multi-region probes (NFR-8). Rejected at spec stage. |
| Per-user personalisation / history | No accounts tied to recommend calls. Stateless. |
| Forecast data | FR-13, later. |

## 4. Acceptance criteria

1. `POST /v1/recommend` with `{"budget_max_usd_per_m": 1, "context_min": 100000}` returns 5 ranked models with `why`, `endpoint_config`, `as_of`, runner-ups. <500ms cached, <2s cold.
2. `GET /v1/explain?model_id=...` returns the full shape above for any ranked model; 404 + suggestions for unknown IDs.
3. ZDR and EU filters return only models on flagged providers (spot-check against providers table).
4. Fresh-agent actionability test (PRD FR-4): given one recommend response, an agent can construct a working chat call from `endpoint_config` alone. Tested with a scripted harness against DeepInfra/OpenRouter.
5. No external LLM calls in either path.
6. api-docs page + llms.txt updated; MCP server gains `recommend_models` and `explain_model` tools.

## 5. Deployment

Atomic per house rule: api.py changes deploy to Lightsail via systemctl, website api-docs page deploys with the endpoint live, llms.txt updated in same push. MCP tools added in a following deploy of the mcp-server package (can lag by a day; it's additive).
