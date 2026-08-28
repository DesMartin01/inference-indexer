# SIT Redesign: From Tier-Relative Scores to Commodity Pricing

**Date:** 2026-08-28
**Author:** Des Martin + Frank
**Status:** Draft for review
**Related:** [[sit-methodology]], [[inference-price-index]], [[concept-analysis]]

---

## 1. Background

The original SIT methodology (v0.1, Aug 3 2026) was inspired by the paper "AI Token Futures Market: Commoditization of Compute and Derivatives Contract Design" (arXiv:2603.21690, Xing, March 2026). The paper defines:

- **SIT** = one inference token from a model meeting GPT-4-Turbo (Jan 2024) benchmarks (MMLU >= 86%, HumanEval >= 67%, GSM8K >= 92%)
- **TPI** (Token Price Index) = volume-weighted mean of SIT-equivalent prices across providers, with a 30% single-provider cap
- **SIT-equivalent price** = raw price * (S_ref / S_i), where S_ref is the reference quality and S_i is the model's quality

Our implementation diverged from the paper in several key ways. This note documents the problems, proposes a redesign, and reviews the impact on the website and pipeline.

---

## 2. Problems With the Current Approach

### 2.1 We Conflated "Commodity Unit" With "Ranking Score"

The paper defines SIT as a **unit of account** (one quality-equivalent token). It does NOT define a per-model "SIT score." The TPI is the commodity price, a single number for the whole market.

Our per-model SIT score (adjusted price / tier median * 100) is a relative value measure within a tier. That's useful, but it's not what the paper describes, and calling it "SIT Score" is confusing.

### 2.2 Tier Medians Are Unstable

We split models into 4 tiers (frontier/standard/budget/micro) and compute medians per tier. Problems:

- Tier boundaries (50/30/15 AA score) are arbitrary
- Models near boundaries flip between tiers as AA scores update, causing the SIT instability we diagnosed (16 models flipping scores within a day)
- The daily-stable median fix helped but did not eliminate the problem; the "blended" source still produces intra-day variation

### 2.3 The Reasoning Multiplier Is a Guess

We multiply price by 2x-4x for reasoning models to account for extra thinking tokens. But:

- The actual ratio varies wildly by task, not just by model
- o1 generates 10x more thinking tokens than the answer; a "reasoning" model that barely thinks might only add 20%
- Fixed multipliers are false precision

### 2.4 AA Intelligence Index Is a Single Proxy

The paper uses three specific benchmarks (MMLU, HumanEval, GSM8K). We use a single composite AA Intelligence Index score. This makes our quality adjustment entirely dependent on Artificial Analysis's methodology.

### 2.5 The Composite Is Not a True TPI

Our SIT-Composite uses usage_weights (external data that gets stale) with a quality gate >= 35. The paper's TPI is volume-weighted with a 30% provider cap. We don't have volume data.

---

## 3. Proposed Redesign

### 3.1 Two Separate Things

**A) Commodity price (TPI):** A single number. "What does one GPT-4-Turbo-equivalent token cost right now?"

$$TPI = \sum_{i} w_i \cdot P_i \cdot \frac{S_{ref}}{S_i}$$

Where:
- $P_i$ = blended price per million tokens for model $i$
- $S_{ref}$ = reference quality score (GPT-4-Turbo = 40 on AA Index)
- $S_i$ = model $i$'s AA Intelligence Index score
- $w_i$ = weight per provider, equal-weighted with 30% cap

**Weighting:** Equal weight per provider (not per model). Each provider contributes their cheapest SIT-qualified model. A single provider cannot exceed 30% of the total weight. This is the closest to the paper's TPI without volume data, and it's simple to compute and explain.

**Quality gate:** Only models with AA score >= 35 (our current QUALITY_FLOOR, roughly GPT-4-Turbo equivalent) are included. This matches the paper's SIT quality floor.

**B) Per-model ranking (SIT-adjusted price):** "How much does it cost to get one SIT-equivalent token from this model?"

$$SIT\text{-}adj_i = P_i \times \frac{S_{ref}}{S_i}$$

Lower = better value. This is what we already compute as `sit_adjusted_price`. The change is: **rank by this directly, not by a tier-relative score.**

### 3.2 Remove Tiers From Ranking

Tiers become a **UI filter only** ("show me frontier-class models"), not a scoring system. The tier concept stays for the index (TPI has a frontier version, a standard version, etc.), but per-model ranking is by absolute SIT-adjusted price.

This eliminates:
- Boundary-flip instability
- The "not comparable across tiers" caveat we currently show
- The need for daily-stable tier medians

### 3.3 Drop the Reasoning Multiplier

Report raw SIT-adjusted price. Let the `is_reasoning` flag speak for itself. The thinking token overhead varies by task, not just by model. A fixed multiplier is misleading.

### 3.4 Keep AA Index as Quality Proxy (Document the Limitation)

We don't have MMLU/HumanEval/GSM8K per model. AA Index is the best single proxy available. Document this clearly in the methodology.

---

## 4. Impact on the Website

### 4.1 Model Table (`ModelTable.tsx`)

| Current | Change Required |
|---------|----------------|
| "SIT Score" column (100 = tier median, tier-relative) | Replace with "Cost / IQ" column showing `sit_adjusted_price` directly. Already exists as a column but is secondary. Make it the primary sort. |
| Sort by SIT Score within tier, by blended price across all | Sort by `sit_adjusted_price` always, regardless of tier filter |
| Tooltip: "SIT Score is tier-relative (100 = tier median). Scores are NOT comparable across tiers." | Replace with: "Cost per GPT-4-equivalent token. Lower = better value. Comparable across all models." |
| Color-coded by tier | Keep tier colors as a visual indicator, but remove the "not comparable" framing |
| SIT Score bar on model detail page (0-200 scale, 100 = median) | Replace with a "value for money" indicator based on absolute SIT-adjusted price vs TPI |

### 4.2 Model Detail Page (`models/[...modelId]/page.tsx`)

| Current | Change Required |
|---------|----------------|
| "SIT Score (100 = tier median)" label and bar | Replace with "Cost / IQ" showing absolute $/M SIT-adjusted price |
| "X% below/above tier median" comparison | Replace with "X% below/above TPI" (commodity price comparison) |
| `sit_score` in JSON-LD structured data | Replace with `sit_adjusted_price` |
| "Tier Ranking (by SIT Score)" section | Replace with "Value Ranking" sorted by SIT-adjusted price |

### 4.3 Homepage (`page.tsx`)

| Current | Change Required |
|---------|----------------|
| "Ranked by SIT Score below, our price-per-intelligence metric" | Update copy: "Ranked by Cost / IQ, our quality-adjusted price per million tokens" |
| SIT-Composite index display | Relabel as "TPI" (Token Price Index) or keep as "SIT-Composite" but update methodology description |

### 4.4 Methodology Page (`methodology/page.tsx`)

This page needs the most work:

- Remove the "SIT Score" section (100 = tier median, lower = cheaper, minimum = 1)
- Add TPI calculation description (equal weight per provider, 30% cap, quality gate)
- Update tier description: tiers are for filtering and per-tier indices, not for per-model scoring
- Remove reasoning multiplier from the methodology
- Add explicit note: "Per-model ranking uses SIT-adjusted price (cost per GPT-4-equivalent token), not a tier-relative score"

### 4.5 API (`api.ts`, `api-docs/page.tsx`)

| Current | Change Required |
|---------|----------------|
| `sit_score` field in API responses | Deprecate. Keep for backward compat but add `sit_adjusted_price` as the primary field |
| `sort=sit_score` API parameter | Change to `sort=sit_adjusted_price` (keep `sit_score` as alias for backward compat) |
| API docs mention "SIT Score" | Update to "Cost / IQ (SIT-adjusted price)" |

---

## 5. Impact on Pipeline / Backend

### 5.1 Pipeline Changes (`pipeline.py`)

| Function | Change |
|----------|--------|
| `calculate_sit_adjusted_price()` | Keep as-is. Already computes $P \times (S_{ref} / S_i)$ |
| `calculate_sit_scores()` | Deprecate. No longer needed for per-model scoring. Keep for backward compat if API still returns `sit_score` |
| `get_stable_tier_medians()` | No longer needed for SIT scoring. May still be useful for per-tier index calculation |
| `calculate_composite_usage_weighted()` | Replace with TPI calculation: equal weight per provider, 30% cap, quality gate >= 35 |
| `assign_tier()` | Keep for UI filtering and per-tier indices. Remove from SIT score calculation |
| `get_reasoning_multiplier()` | Deprecate. Stop applying reasoning multiplier to `sit_adjusted_price` |

### 5.2 Database Changes

| Table/View | Change |
|------------|--------|
| `price_snapshots.sit_score` | Stop computing. Set to NULL for new snapshots. Keep historical values. |
| `price_snapshots.reasoning_multiplier` | Stop computing. Set to 1.0 for new snapshots. Keep historical values. |
| `price_snapshots.sit_adjusted_price` | Keep. This becomes the primary ranking metric. |
| `sit_index_values` (composite tier) | Calculation method changes from `usage_weighted_quality_gated` to `tpi_equal_weight_provider_capped`. Old rows keep their method. New rows get new method. |
| `latest_prices` matview | No schema change. `sit_score` column will show NULL for new snapshots. |
| `daily_tier_medians` | May become unused if we stop computing tier-relative scores. Keep for now. |

### 5.3 Historical Price Continuity

This is the biggest risk. The SIT-Composite index was rebased at 1000 on 2026-08-03. If we change the calculation method:

- **Old methodology:** usage-weighted top 50, quality gate >= 35
- **New methodology:** equal-weight per provider, 30% cap, quality gate >= 35

The composite price will jump. Options:

1. **Recalculate full history** with new methodology, rebaseline to 1000 at the same base date. The index points will shift but the trend will be comparable. Old values published in a methodology appendix.
2. **Overlap period:** Publish both old and new for 30 days, then switch. Our methodology doc (Section 8.1) already commits to this.
3. **Hard switch:** Just change the method and accept the discontinuity. Simplest but least professional.

Recommendation: **Option 1** (recalculate + rebaseline). We have all raw data in `price_snapshots`. We can recompute the composite for every day since Aug 3 using the new TPI formula. The index points will change but the time series will be continuous.

### 5.4 Integrity Check Changes

- Check 2 (SIT stability): Becomes irrelevant if we stop computing per-model SIT scores. Replace with a check on TPI stability (daily TPI shouldn't move > 20%).
- Check 7 (index frozen at 1000): Update for new TPI calculation.

---

## 6. Risks and What Could Go Wrong

### 6.1 TPI Without Volume Data

The paper's TPI is volume-weighted. We're proposing equal-weight-per-provider as a proxy. Risks:
- A provider with 1 cheap model and no real volume gets the same weight as OpenAI
- The 30% cap helps but doesn't fully solve this
- **Mitigation:** Document clearly. Phase 2 could add volume data if it becomes available. The methodology already has this as a Phase 3 goal.

### 6.2 Dropping the Reasoning Multiplier

Reasoning models will appear cheaper than they effectively are, because they generate thinking tokens that aren't in the output price. A model at $1/M output that generates 5x thinking tokens effectively costs $5/M of useful output.
- **Impact:** Reasoning models will rank higher (appear cheaper) than they should
- **Mitigation:** Show the `is_reasoning` flag prominently. Let the user decide. This is more honest than a guess.
- **Alternative:** If AA or another source publishes average thinking token ratios, we could add a "thinking-adjusted price" as a secondary metric in the future.

### 6.3 Historical Discontinuity

Even with recalculation, the TPI value will differ from the old SIT-Composite. Users who have been tracking the index will see a jump.
- **Mitigation:** Publish a methodology change note. Show old vs new for 30 days. Our methodology doc already commits to this process.

### 6.4 API Backward Compatibility

External consumers may depend on `sit_score` in API responses.
- **Mitigation:** Keep `sit_score` in the response (computed from the old formula or set to NULL). Add `sit_adjusted_price` as the primary field. Deprecation notice in API docs.

### 6.5 SEO Impact

Model detail pages have "SIT Score" in meta descriptions, JSON-LD, and page content. Changing this could affect search rankings.
- **Mitigation:** Update all pages atomically. Use 301 redirects if any URLs change (unlikely since the URL structure doesn't include "sit-score"). Keep "SIT" in the terminology but clarify it means "Cost / IQ" or "SIT-adjusted price."

### 6.6 Provider Count Changes Affect TPI

With equal-weight-per-provider, adding or removing a provider changes the TPI even if no prices changed. If we add the 3 new scrapers (Z.AI, Alibaba, Moonshot), the TPI will shift.
- **Mitigation:** This is expected behaviour for a commodity index. Document it. The 30% cap limits the impact of any single provider.

### 6.7 Models Without AA Scores

292 of 546 active models have AA scores. The rest get no SIT-adjusted price and are excluded from the TPI. This is the same as the current approach but worth noting: nearly half the catalog is unranked.
- **Mitigation:** Keep showing these models in the table with "N/A" for Cost / IQ. They're still searchable and sortable by raw price.

---

## 7. Implementation Plan (High Level)

1. **Pipeline:** Add TPI calculation function. Stop computing `sit_score` and `reasoning_multiplier` for new snapshots. Keep `sit_adjusted_price`.
2. **Historical recalculation:** Write a one-time script to recompute `sit_index_values` (composite tier) using the new TPI formula for all dates since 2026-08-03.
3. **API:** Add `sit_adjusted_price` to all response shapes. Keep `sit_score` for backward compat (NULL for new data).
4. **Website:** Update ModelTable, ModelDetail, Homepage, Methodology page, API docs.
5. **Methodology doc:** Update `sit-methodology.md` to v0.2.
6. **Integrity check:** Update check 2 (SIT stability) to check TPI stability instead.
7. **Test:** Run pipeline in `--fetch-only` mode to verify TPI calculation. Compare old vs new composite for a few dates.

---

## 8. Open Questions

- [ ] Should the TPI use the cheapest model per provider, or the median model per provider?
- [ ] Should we publish a "SIT-spread" (frontier TPI vs budget TPI) as a separate metric?
- [ ] Do we need a separate index for non-text modalities (embeddings, image gen)?
- [ ] Should the 30% provider cap be applied to the number of models or to the weight?
- [ ] What happens if a provider's cheapest SIT-qualified model changes? (TPI jumps)
