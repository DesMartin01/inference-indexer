# II Homepage v6: Recommendation Engine Lead — PRD

**Date:** 2026-09-23
**Author:** Frank
**Status:** APPROVED — Des signed off all four open questions 2026-09-23. Build in progress.
**Related:** [[Recommend-Explain-Endpoint-Spec]] (backend, DONE) | [[Recommend-Explain-Implementation-Log]] | [[II-PRD]] | Homepage mock: `/tmp/ii-homepage/v6-mock.html` + PNG in `.hermes/attachments/`

---

## 1. Vision & Scope

Reposition the II homepage from price index to recommendation engine, per the agreed order:

1. **Engine** — prompt box wired to the LIVE `/v1/recommend` (deployed Sep 3, not new work)
2. **Coverage** — pillars + attestation table (who attests vs who verifies)
3. **Proof** — Standard Inference Token price card (per Des: never lead with the "SIT-Composite" term; "SIT" only as shorthand after the full name is established)
4. **Catalogue preview** — input/output/blended + country cols; full rankings move to their own page

Nav: `API · For agents · Providers · Methodology · About`.

**This is a homepage + rankings-page build. The engine backend exists.** Live check 2026-09-23: recommend returned 3 ranked models with endpoint recipes, freshness (price age 0.9h), runner-ups.

### Non-goals (v6)
- No LLM in any request path (deterministic only; house rule)
- No saved briefs / accounts-gated features (enrolment band stays copy-only)
- No thumb-vote eval loop (Phase 2)
- No new data collection (privacy/security remain provider-stated, badged as such)

## 2. Viability Assessment (Des's three questions)

| Question | Answer |
|---|---|
| Where does it sit? | Homepage restructure (existing `/` page.tsx), new `/rankings` page (extracts existing ModelTable), prompt box calls existing `/v1/recommend`. One new table, no pipeline changes. |
| Cost per result? | ~€0. Deterministic SQL over `latest_prices` (308 rankable models), 5-min TTL cache already live (0.07s cached / 2.2s warm). Cost does NOT scale with popularity. |
| Likely interest / revenue? | Interest: routing demand is proven (OpenRouter $160M ARR, 10M req/day) but II's slice is research, not routing. Revenue: indirect — engine is acquisition for enrolment + API tiers. Honest rating: **differentiator, not revenue product.** Success metric = receipts counter + return rate, not conversion. |

## 3. What's already built (do NOT rebuild)

- `POST/GET /v1/recommend`: budget/context/modality/zdr/eu_sovereign/reasoning/providers/use_case/limit/prefer_callable
- Evidence-in-response: `why`, `endpoint_config` (hot-swap recipe), `callability`, `freshness` + SLA, `ranking_basis`, runner-ups
- `/v1/explain`: full model profile, alias + fuzzy resolution
- MCP tools `recommend_models` / `explain_model`; llms.txt; api-docs page
- Known limits (from impl log): cold calls 2-6s (no pooling), `use_case` not on MCP tool yet, ~30 models lack verified endpoints, AA gate applies to having Cost/IQ at all (docs fixed, gate unchanged)

## 4. New build items

| # | Item | Detail | Est |
|---|---|---|---|
| 1 | `recommendation_stats` table | `(ts, constraint_tuple, result_count, top_cost_iq)`. No free text, ever. Powers receipts counter + demand measurement. Constraint-tuple only: anonymous. | 0.5d |
| 2 | Homepage engine panel | Prompt box → parse constraints client-side (keyword matching, v1) → show **echo chips** → call recommend → render rows w/ badges (verified price = gold; provider-stated ZDR/EU = grey w/ tooltip) → funnel line + disclaimer. Deterministic parse, visible echo, no silent matching. | 1.5d |
| 3 | `/rankings` page | Extract ModelTable w/ full tiers, 24h, sort toggles. Homepage keeps 3-row preview. | 1d |
| 4 | Homepage restructure | Mock v6 order; SIT card; coverage block; enrolment band. Live data everywhere (588 not 580; live AA scores; live Standard Inference Token price). | 1d |
| 5 | Agents surface | "For agents" nav link → agent docs section; llms.txt recipe: recommend → explain → verified host loop (Grok's embed pattern). | 0.5d |

**Sample panel behavior (the validating artifact):** query "zero data retention providers in the EU, under $2/M" → echo chips `[ZDR] [EU] [<$2/M]` → funnel "N of 728 models match · M excluded (no AA score)" → rows with `ZDR: provider-stated` badges → footer: "Privacy constraints matched on provider statements; prices verified hourly. Query not stored."

## 5. Data honesty rules (violations reject the build)

1. Every number on the homepage comes from the same query layer as the API. No hardcoded counts (mock's "1,208 recommendations served" is placeholder until item 1 ships).
2. Mock's AA scores (70-81) and tier boundaries do NOT match live data (AA v4.3: frontier ≥ 50). Build uses live values only.
3. No "guaranteed security" anywhere in engine output. Example-prompt wording is Des's call (open question 2).
4. Engine results badge basis per row. Provider-stated ≠ verified, visually distinct, tooltip explains.
5. Queries never stored (no free text in recommendation_stats or logs).
6. Naming (Des, 2026-09-23): the price card leads with "Standard Inference Token price". "SIT-Composite" does not appear on the homepage; internal/API field names keep the composite naming, user-facing copy uses the full name with "SIT" as shorthand only after first use.

## 6. Metrics

- Receipts counter (from item 1): recommendations served / week — the demand instrument
- Return rate of recommend users (cookie-anon)
- Funnel: homepage box → echo shown → results shown → click through to /rankings or /models
- Baseline: 2 weeks post-launch before judging

## 7. Risks

| Risk | Mitigation |
|---|---|
| Cold queries 2-6s feel broken in the UI | Loading state on Recommend; ship DB pooling if it annoys (separate task, impl log open item) |
| Cheap-but-limited models top results (AA 15-24) and look silly | Panel shows AA score per row + ranking_basis note; docs already honest |
| AA licence scope (recommendation product vs display) | Check before launch; fallback = price+tier ranking only |
| Anon 3/day gate: cookie bypass is trivial | Accepted: soft gate is friction, not security. Hard limits live at the API-key tier |

## 8. Decisions (Des, 2026-09-23) — APPROVED

1. **Free/paid boundary**: anon 3 queries/day (cookie), account = unlimited, API tiers for programmatic. **Confirmed.**
2. **Example prompt wording**: softened per Des ("guaranteed security (no chance of...)" removed). New default example prompt: "Find me an inference provider with zero data retention, EU infrastructure, a strong security track record, and no router interference, at the best price. This agent will be running accounts receivable and payable for a mid sized SME in London." (Copy owner: Des; Frank polishes only.)
3. **"Or start from" suggestions**: curated standard set, see below. **Confirmed as set.**
4. **Rankings page URL**: `/models`. **Confirmed.** Homepage preview links there.

### Standard suggestion set (item 3 final)

Engine v1 parses structured constraints only; each suggestion maps to a parseable constraint tuple so every chip demonstrably works:

| Chip text | Parses to | Demos |
|---|---|---|
| Cheapest model above AA index 70 | `use_case: research` + AA floor display filter | value ranking |
| Zero data retention providers in the EU | `zdr: true, eu_sovereign: true` | the moat query |
| Best value for coding agents under $2/M | `use_case: coding, budget_max_usd_per_m: 2` | workload shaping |
| Providers serving DeepSeek V4, price compared | model lookup → `/models/deepseek-v4` endpoints view | multi-provider price truth |

(Rejected as chips, with reasons: "smartest model" — any leaderboard does that; "cheapest model overall" — biddable noise, micro-tier wins every time; anything about latency/uptime — not scored yet, chip would promise what the page disclaims.)

## 8a. LLM policy (Des question, 2026-09-23): no LLM answers recommendations

Confirmed: **no LLM in the answer path.** Decision and rationale:

- The product claim is *verifiable, deterministic, no hallucination*. An LLM sentence in the answer path undermines the one thing II sells. Grok's adversarial test validated exactly this design ("useful infrastructure, not a decision brain").
- The "feel of AI" comes from presentation, not generation: echo chips ("Understood as: ZDR, EU, <$2/M"), `why` strings from deterministic templates, funnel lines, badges. These read as intelligence because they expose reasoning, not because they're generated.
- Light local LLM is approved for exactly one job, Phase 2, isolated from data: **parsing free text into constraint tuples** (the echo step), never ranking, never prose in results, never visible in output except via the chips. Parse errors fail loud: unparseable input returns "Understood as: (nothing) — try structured constraints", never a guessed answer. Candidate: small local model on Lightsail is NOT viable (t3.micro has no headroom); options are a tiny hosted model or client-side keyword parse staying v1 default.
- The API's "no external LLM calls in path" acceptance criterion stays intact and testable.

## 9. Acceptance criteria

1. Homepage renders 4 blocks in order; engine panel returns LIVE results with echo + badges + funnel line.
2. `/rankings` serves full table; homepage preview links to it; no horizontal scroll at 1280/1440.
3. `recommendation_stats` rows written per query; zero free-text content stored (verified by query inspection).
4. Receipts counter renders real count.
5. llms.txt + api-docs updated same deploy (atomic, house rule).
6. No banned AI-design elements; dark theme; no LLM calls anywhere in path.
