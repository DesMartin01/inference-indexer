# PRD: The Planning Plane — II as the Go-To Resource for Agent Inference Queries

**Date:** 2026-09-03
**Author:** Frank
**Status:** DRAFT — awaiting Des sign-off
**Trigger:** Grok external review ("Could a high-standard InferenceIndexer become the go-to? Yes — for the planning query. No — for the token query.")
**Related:** [[II-PRD]] | [[Recommend-Explain-Implementation-Log]] | [[II-Strategy-Memo]]

---

## 0. Viability Assessment (required before architecture)

**Where does this sit on the existing product?**
Entirely within the existing API + MCP surface (`api.py`, `inferenceindexer-mcp`). No new site pages except one: a freshness/status badge. Deepens `/v1/recommend` and `/v1/explain` rather than adding new surfaces. The llms.txt and api-docs pages gain sections; the MCP server gains parameter coverage.

**What does it cost per result served, and does cost scale with popularity?**
- Recommend/explain: read-only DB queries behind a 5-min cache. Marginal cost per call ≈ €0.00x (Supabase pooler, Lightsail CPU). Cache-first serving already implemented; 1M calls/mo ≈ $5-10 (NFR-5b stands).
- The two features with real marginal cost:
  - **Endpoint probe expansion** (item 2): ~$20-80/mo API spend, hard-capped per provider (PRD FR-15 budget already approved in principle; needs Des's final sign-off).
  - **Effective-economics data** (cache/batch discounts): scraper work, no per-call cost.
- Probe spend is capped and fixed; serving scales with cache hits, not traffic. Cost does NOT scale with popularity.

**Competitor feature parity check:**
- OpenRouter: has live prices + routing but is conflicted (sells the inference it rates). No independent ZDR/EU verification, no history.
- LiteLLM/Portkey: execution planes with proxy-side cost tracking; they consume catalogs, don't publish auditable ones.
- Artificial Analysis: benchmarks for humans, no agent API, no hot-swap recipes.
- **Nobody treats a price index as the planning plane.** Grok's diagram (planner → "what's good/fast/allowed" vs "run this now") is the open seat. Verdict: no competitor ships this combination today; the moat is the pipeline + verified-endpoint discipline, which is exactly the maintenance treadmill competitors won't copy.

**Revenue streams (ranked, honest):**
1. **Feed subscriptions (existing FR-6c, high):** this build makes the feed data (price moves, endpoint changes, probe alerts) the thing agents' teams pay for. The planning plane increases embed surface; embeds drive feed subscriptions.
2. **Gateway licensing (medium):** LiteLLM/Portkey consuming our verified catalog — catalog quality (recipes + freshness SLA) is what they'd license.
3. **API paid tiers (low-medium):** recommend/explain volume is cacheable; metering stays demoted per PRD v7.
4. **Honest answer:** this build is a *differentiator that converts the existing subscription thesis into reality*, not a standalone revenue product. It strengthens the M1/M2 gates rather than adding revenue directly.

**Interest evidence:** 522 /mcp requests in 48h post-listing (mostly scanners) + at least one genuine client session; Grok independently built a 5-scenario test suite against the API without being asked. The agent market is already probing; the gaps Grok found are the gap between "interesting" and "trusted."

**Gate alignment:** this PRD covers P0/P1 work (FR-2 live performance, FR-6 consistency, FR-8 embed ergonomics). The `use_case` heuristics and bake-off validation still gate on Phase -1 conversations. This PRD does NOT preempt the demand gate: everything here hardens what agents *already ask for*, evidenced by Grok's unrequested test.

---

## 1. Product Vision & Goals

**Vision:** An agent makes ONE call to InferenceIndexer and trusts the answer enough to act on it — pinned host, callable recipe, honest costs. II owns the planning query ("what's good, fast, and allowed for this job?") and explicitly does not own the execution query ("run this completion now").

**Problem/solution:**

| Problem (from Grok review) | Solution in this PRD |
|---|---|
| Privacy flags are model-level claims | Host-level ZDR/EU/residency/training-use with verification dates (PR-1) |
| Rank-1 with `endpoint_config: null` is a failed tool | Callable-recipe guarantee + completion backfill (PR-2) |
| Cost/IQ without latency recommends timeout-blowers | Live performance fields from expanded probing (PR-3) |
| Every use case collapses to the same 4 flash models | Task axes beyond one Cost/IQ sort (PR-4 — extends the `use_case` profiles shipped Sep 3) |
| Blended $/M ≠ dollars per solved task | Effective economics: cache/batch/thinking-token pricing (PR-5) |
| Dirty model names 404 uselessly | Canonical ID + alias resolution + fuzzy suggestions (PR-6) |
| `as_of` alone can't express staleness | Freshness SLA + signed methodology version (PR-7) |
| Trust requires auditability | Stay deterministic — no LLM in the ranking path (NFR, already held) |

**Primary goal:** an agent can trust one recommend+explain round-trip enough to act without a second source.
**Success definition:** external agents complete the actionability loop (recommend → call the pinned host) at ≥90% across a published 20-job bake-off (FR-10b), and II appears as the default MCP pair in at least one public agent framework's docs (FR-10).

**Explicit non-goals:**
- **Never the execution plane.** No proxying, no token flow, no billing of completions. That's OpenRouter's business; competing there destroys the impartiality moat.
- No LLM in the ranking path (advantage over unauditable smart routers).
- No benchmark suite of our own (AA license conversation + no-AA ranking principle stands).
- No natural-language parser in v1 (the agent compiles constraints; the bake-off validates the constraint set).

## 2. Personas (abridged — full versions in [[II-PRD]])

- **The cost-aware agent developer** (primary): runs a support or ops agent at volume; needs policy-filtered shortlists + callable hosts; hates surprise bills.
- **The compliance-gated platform team** (buyer persona): EU enterprise; needs host-level ZDR/residency truth with verification dates before letting an agent call anything.
- **The framework maintainer**: ships a default model-selection tool; needs deterministic, citable, cacheable endpoints with a freshness SLA.

## 3. Core Design — the eight PRs

This is a data-product PRD: the core design is the **interface + data specification** for each PR. Each is a typed interface with data source, freshness, and acceptance test.

### PR-1 Host-Level Truth (privacy & residency per endpoint)

**Problem:** `zdr`/`eu_sovereign` are model-level ("some provider of this model claims ZDR"). Grok: "easy to mis-route if the agent treats the flag as certified."

**Interface (extends `endpoint_config`):**
```json
"privacy": {
  "zdr": true,
  "eu_sovereign": false,
  "residency": ["eu-west-1"],           // claimed processing regions
  "training_use": "opt-in",             // claims: opt-in | opt-out | never | unknown
  "verification": {
    "checked_at": "2026-09-01",
    "source_url": "https://deepinfra.com/dpa",
    "method": "provider_docs_review"
  }
}
```

**Data source:** extend `providers` table with per-provider JSONB `privacy_claims` (already exists in schema direction per FR-6b: `processing_regions`, `training_default`, `verified_at`, `source_url`). Researched for top-20 providers (~90% of query volume) per FR-6b; long tail stays `null` → fields omitted + caveat. II aggregates and dates claims; never certifies (NFR-9).

**Ranking rule:** when `zdr: true` is requested, recommend only models whose cheapest verified endpoint has host-level `zdr: true` — not model-level matches. (Today the flag can rank a model whose cheapest host isn't compliant.)

**Effort:** 2-3 sessions. Schema + top-20 provider research + recommend/explain wiring.

### PR-2 Callable-Recipe Guarantee

**Problem:** rank-1 with `endpoint_config: null` is a failed tool (Grok measured it; we measured 30/256 uncovered).

**Rules:**
1. Recommend responses carry a `callability` field per result: `callable` (verified recipe), `heuristic` (prefix-derived, caveated), `unverified` (null config).
2. `prefer_callable: true` (default) demotes non-callable results below callable ones with equal-or-better task score — an agent should never see rank-1-null when rank-2 is callable.
3. Backfill: extend `refresh_provider_aliases.py` to also seed endpoint rows for connector-priced models (the Inclusionai fix, generalized). Coverage target: ≥90% of rankable models callable within 2 weeks.
4. Explain gains `call_recipes`: array of ALL verified endpoints (not just cheapest), each with base_url/native id/auth/streaming/tool-calling support flags.

**Data source:** `endpoint_provider_config` (20 providers) + `provider_model_alias` (510 rows) + per-connector catalog data already flowing hourly. Streaming/tool-calling support: connector-observed flags (Venice/DeepInfra/Novita already expose features arrays) — store in `provider_model_alias`, default unknown.

### PR-3 Live Performance (FR-2 completion)

**Problem:** Cost/IQ without latency recommends a cheap model that blows the agent's timeout. Probes exist but cover 3 providers with 8-28% success rates — the probe runner itself is failing.

**Interface (new `/v1/quality` + fields in recommend/explain):**
```json
"performance": {
  "ttft_ms": {"p50": 420, "p95": 1100, "sample_count": 168, "window": "24h"},
  "throughput_tps": {"p50": 48.2},
  "error_rate_24h": 0.04,
  "vantage": "dublin-eu-west",
  "caveat": "single-region probes; dropped from sort when region != vantage (NFR-8)"
}
```

**Prerequisites (honest):** the probe runner must be repaired BEFORE fields are exposed:
1. Fix stale model IDs (TensorX 400, Fireworks 404 — identified Sep 2).
2. Add keys for Tier-A providers (DeepInfra, Novita, Groq, Together, SambaNova need keys from Des).
3. Budget cap per provider (~$20-80/mo total, per FR-15; needs Des approval).
4. Multi-region is Phase 2 (NFR-8): until then `vantage: dublin-eu-west` on every quality field, and latency drops out of the sort when the agent requests a different region.

**Ranking integration:** performance is a *filter and tie-break*, not a sort key. `max_ttft_ms_p95` constraint optional. If probe coverage for a model < N samples, `performance: null` + caveat. Never fake it.

**Acceptance:** ≥10 providers probed hourly with ≥95% probe success; /v1/quality live; performance fields in recommend when available.

### PR-4 Task Axes (extends `use_case`, shipped Sep 3)

**Problem:** one Cost/IQ sort collapses every use case onto the same four flash models.

**Design:** `use_case` (shipped) becomes the first of three orthogonal axes:
1. `use_case` (shipped): support | volume | extraction | summarization | coding | research — AA floor + reasoning preference.
2. **`output_type`:** `text` | `json` | `tool_calls` — filters/boosts models with structured-output or function-calling features (data already exists: Novita connector exposes `features: ['function-calling', 'structured-outputs']`; OpenRouter exposes moderated/tool_support flags). Data source: raw_data in connectors; add `supports_tools`, `supports_json_mode` to models table.
3. **`context_profile`:** `needle` (long-context recall matters) vs default — boosts effective context above a threshold; documents that AA is measured on short context, not 1M-token recall.

**Honest limit:** these are still proxies for benchmarks we don't run (SWE-bench, GAIA). ranking_basis says so. The bake-off (FR-10b) is the validator: 20 jobs, ≥90% policy-correct.

### PR-5 Effective Economics

**Problem:** agents budget in dollars per solved task, not blended $/M on a 3:1 mix. Cache pricing, batch discounts, and thinking tokens change real cost by 5-10x.

**Interface (extends pricing objects in recommend/explain):**
```json
"economics": {
  "list_blended_per_m": 0.224,
  "cache_read_per_m": 0.022,        // if provider publishes cache pricing
  "batch_discount_pct": 50,          // if provider publishes batch API
  "thinking_cost_note": "reasoning model: budget output tokens x 3-5 for thinking",
  "solved_task_estimate": {
    "assumptions": "10k input (cached repeat) + 500 output, no thinking",
    "usd_per_1k_tasks": 1.31
  }
}
```

**Data source:** provider pricing pages already scraped (OpenRouter exposes `prompt_cache_read`, batch pricing in raw_data); needs a normalization pass to surface cache/batch fields. Thinking-token multipliers stay a *labelled estimate* (NFR-2) until real ratios ship per model.

**Scope control:** solved-task estimates ship for the top-20 models first (manual verification), then automated.

### PR-6 Canonical IDs + Alias Resolution

**Problem:** agents pass dirty names (`DeepSeek V4 Flash`, `deepseek-v4`, `@openrouter/deepseek/...`). 404 with empty suggestions loses them.

**Design:**
1. New `model_aliases` table: alias string → canonical model_id. Sources: OpenRouter ids, HuggingFace ids, provider display names, common nicknames. Seeded from existing scrapers + hand-curated top-50.
2. Fuzzy resolution: recommend/explain/get_model accept dirty strings; exact → alias → trigram similarity (pg_trgm, threshold 0.35). Response includes `resolved_from` when a fuzzy match occurred.
3. 404 suggestions: always populated from trigram matches (currently empty on no-prefix-match).
4. Alias table versioned + dated (feeds PR-7 freshness SLA).

**Acceptance:** `explain?model_id=DeepSeek V4 Flash 0731` resolves; `explain?model_id=deepsik-v4-flsh` (typo) returns the right model with `resolved_from`.

### PR-7 Freshness SLA + Methodology Versioning

**Design:**
1. Every response gains `freshness: {price_age_hours: 1.2, aa_age_days: 3, probe_age_hours: 1, stale_flags: []}` where `stale_flags` lists any field older than its SLA (prices 6h, AA 7d, probes 24h).
2. `methodology_version` becomes semver with a signed changelog: `methodology: {version: "0.3.0", changes: [...], signed_at: ...}`. Breaking changes to ranking bump major.
3. `stale: true` responses include the last-good data + the flag (stale-with-timestamp, never a bare 500 — NFR-3).
4. Published SLA page: what freshness agents can rely on per field (llms.txt + status page, NFR-7).

### PR-8 Determinism Guarantee (NFR, formalize)

Already true (no LLM in path). Formalize: ranking inputs versioned (AA snapshot id, price snapshot ids), `ranking_basis.inputs` block in response so two agents can prove they saw the same inputs. This is the auditability moat Grok called "your advantage over smart routers."

## 4. Technical Architecture

```
                    ┌──────────────────────────────────────┐
                    │  InferenceIndexer (planning plane)   │
                    │                                      │
 Agent ──MCP/HTTPS──▶  /v1/recommend ──┐                    │
                    │   /v1/explain  ──┼─▶ api.py (Lightsail)│
                    │   /v1/quality ───┘    │                │
                    │                       ▼                │
                    │                 Supabase (pooled)      │
                    └───────────────────────▲────────────────┘
                                            │ hourly + daily
                          ┌─────────────────┼──────────────────┐
                          ▼                 ▼                  ▼
                   price connectors   probe_quality.py    alias refresh
                   (OpenRouter +      (repaired, 10+      (provider /models
                   12 direct)         providers, keys)    + endpoint seeds)
```

- **Stack unchanged:** FastAPI + Supabase + Next.js + MCP. No new services.
- **Probe repair** is the critical-path item for PR-3: fix runner (stale IDs), add keys, expand Tier-A list, budget-capped.
- **Cache-first serving** unchanged; new fields flow through the same 5-min TTL.
- **Atomic deploys** (NFR-6): API + docs + MCP ship together.

## 5. Data Specification (new/changed tables)

| Table | Change | Purpose |
|-------|--------|---------|
| `providers` | +JSONB `privacy_claims` (zdr, residency[], training_use, verified_at, source_url) | PR-1 |
| `models` | +`supports_tools` bool, +`supports_json_mode` bool | PR-4 axis 2 |
| `model_aliases` (new) | alias TEXT PK, canonical_model_id, source, verified_at | PR-6 |
| `endpoint_probe_summary` (new matview) | per provider+model 24h/7d: p50/p95 TTFT, tok/s, error rate | PR-3 |
| `endpoint_provider_config` | +streaming, +tool_calling columns | PR-2 |

## 6. Analytics & Success Metrics

| Metric | Current | Target (4 weeks post-build) |
|--------|---------|------------------------------|
| Rankable models with verified call recipe | 83% | ≥95% |
| Providers with live probe data | 3 (failing) | ≥10, ≥95% probe success |
| Recommend responses with null endpoint_config at rank 1 | measured | ≤5% |
| Alias resolution rate on dirty IDs | n/a | ≥80% of top-100 model name variants |
| External agents completing actionability loop | 1 observed | measured via bake-off harness, ≥90% |
| MCP tool calls/day (real clients) | ~0 | trending series published |

## 7. MVP Scope vs Phase 2

**MVP (this build):** PR-2 (callability guarantee + backfill), PR-6 (aliases + fuzzy), PR-3 (probe repair + /v1/quality basic), PR-7 (freshness flags), PR-4 axis 2 (tool/json flags), PR-8 formalization. Est. 6-8 Frank sessions.

**Phase 2:** PR-1 full top-20 privacy research (needs the research sprint; ship schema + top-5 first), PR-5 solved-task estimates beyond top-20, context needle-profile, multi-region probes (NFR-8).

**Deliberately not in scope:** execution plane / routing / proxying (becoming OpenRouter destroys the impartiality moat); NL parsing; own benchmarks; SLA-backed uptime guarantees (Phase 4).

## 8. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Probe keys/budget not approved | PR-3 stalls | Scoped ask: $20-80/mo cap; ship PR-2/6/7 without probes |
| Provider docs drift breaks privacy claims | Trust damage | verification dates + quarterly re-check (NFR-9) + feed events on change |
| Alias table wrong → mis-routing | Trust damage | model_id_source field + resolution confidence; verified-only for bake-off scoring |
| AA license terms change | Data foundation | no-AA ranking already exists; AA enriches, never load-bearing |
| Scope creep toward routing | Moat destruction | Non-goals section is binding; execution = OpenRouter/LiteLLM's lane |

## 9. Open Questions (owner: Des unless noted)

1. Approve probe budget $20-80/mo + provide Tier-A API keys (needed-by: probe repair start).
2. Approve the six `use_case` profiles as bake-off seed (validate in Phase -1).
3. AA license conversation (from PRD v7, still open) — happens before FR-4-wide use of AA in marketing claims.
4. Freshness SLA numbers (6h prices / 7d AA / 24h probes): agree or adjust?
5. Signed methodology changelog: PGP-signed file in repo sufficient, or status-page service?

## 10. Effort & Sequence

| Week | Work |
|------|------|
| 1 | PR-6 aliases + fuzzy 404s; PR-2 backfill generalization; GET/POST parity checks |
| 2 | PR-3 probe repair (model IDs, keys, Tier-A expansion) + /v1/quality endpoint |
| 3 | PR-4 axes 2-3 (tools/json flags, context profile) + PR-7 freshness SLA + methodology signing |
| 3-4 | PR-1 privacy schema + top-5 provider research (full top-20 after Phase -1) + PR-5 economics fields |
| Continuous | Bake-off harness runs in CI from week 2 (FR-10b) |
