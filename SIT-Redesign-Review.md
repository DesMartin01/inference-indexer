# SIT Redesign: Change Review

**Date:** 2026-08-28
**Author:** Frank
**Related:** [[SIT-Redesign-Brainstorm]]

---

## 1. UI Changes (Website)

### 1.1 Files Affected

| File | What It Does | SIT References |
|------|-------------|----------------|
| `web/src/components/ModelTable.tsx` | Main model pricing table | 15 references to sit_score, tier-relative scoring, "not comparable across tiers" |
| `web/src/components/ProviderModelTable.tsx` | Provider comparison table | 5 references to sit_score and sit_adjusted_price |
| `web/src/app/page.tsx` | Homepage | "SIT-Composite" in metadata, "Ranked by SIT Score" copy |
| `web/src/app/models/[...modelId]/page.tsx` | Model detail page | SIT Score bar, tier median comparison, JSON-LD, meta description |
| `web/src/app/methodology/page.tsx` | Methodology page | Full SIT Score formula, tier description, composite calculation |
| `web/src/app/api-docs/page.tsx` | API documentation | "SIT scores" in meta, sort parameter, example responses |
| `web/src/app/for-agents/page.tsx` | Agent-facing page | "SIT-Composite" endpoint references |
| `web/src/app/about/page.tsx` | About page | "SIT-Composite index" mention |
| `web/src/lib/api.ts` | API client types | `sit_score` field in 5 type definitions, `reasoning_multiplier` field |

### 1.2 Specific UI Changes Required

**ModelTable.tsx (the biggest change):**
- Remove "SIT Score" column (the 100 = tier median relative score)
- Promote "Cost / IQ" column (already exists, shows `sit_adjusted_price`) to primary sort and default
- Remove all the "not comparable across tiers" tooltips and caveats
- Remove the tier-relative sort logic (lines 97-98, 169-172, 199-202, 217-218)
- Replace tier median tooltip (line 482, 707) with: "Cost per GPT-4-equivalent token. Lower = better value. Comparable across all models."
- Keep tier color coding as visual indicator only

**Model detail page (models/[...modelId]/page.tsx):**
- Replace "SIT Score (100 = tier median)" section with "Cost / IQ" showing absolute $/M
- Replace "X% below/above tier median" with "X% below/above TPI"
- Update JSON-LD structured data: `PropertyValue name: "SIT Score"` becomes `"Cost / IQ"`
- Update meta description: "SIT Score X (Frontier tier)" becomes "Cost / IQ $X/M"
- Replace "Tier Ranking (by SIT Score)" section with "Value Ranking" sorted by sit_adjusted_price
- Replace the SIT Score bar (0-200 scale, 100 = median) with a value gauge relative to TPI

**Methodology page (methodology/page.tsx):**
- Remove the SIT Score formula section (lines 375-376: "SIT Score = round(Quality-Adjusted Price / Tier Median x 100)")
- Remove the "100 = tier median" explanation (lines 398-399)
- Add TPI calculation description: equal weight per provider, 30% cap, quality gate >= 35
- Update composite description: remove "usage-weighted mean of top 50" (line 407-417), replace with TPI formula
- Update the FAQ: "How is the SIT-Composite calculated?" answer changes from usage-weighted to provider-equal-weighted
- Update tier description: tiers are for filtering and per-tier indices, not per-model scoring

**Homepage (page.tsx):**
- Line 419: "Ranked by SIT Score below" becomes "Ranked by Cost / IQ below"
- Line 30, 39, 118-119: Keep "SIT-Composite" name (brand recognition) but update description if we rename to TPI

**API docs (api-docs/page.tsx):**
- Line 329: `sort=sit_score` becomes `sort=sit_adjusted_price` (keep sit_score as alias)
- Lines 344, 371: Update example JSON responses to show `sit_adjusted_price` instead of `sit_score`
- Line 11: "SIT scores" becomes "quality-adjusted prices"

**API client types (api.ts):**
- Keep `sit_score` field (nullable, for backward compat)
- Add `sit_adjusted_price` as primary field (already exists in some types)
- Keep `reasoning_multiplier` field (will be 1.0 going forward)

### 1.3 SEO Considerations

- Model detail pages have "SIT Score" in: meta description, JSON-LD, H1 area, page content
- These are indexed by Google. Changing them all at once is a content update, not a URL change
- No 301 redirects needed (URLs don't contain "sit-score")
- Risk: temporary ranking fluctuation while Google re-indexes. Low risk since the pages stay about the same topic
- Keep "SIT" brand name in the composite index name. "SIT-Composite" is recognizable. Just change what the per-model metric is called

---

## 2. Backend / Data Changes

### 2.1 Pipeline (`pipeline.py`)

| Function | Lines | Change |
|----------|-------|--------|
| `calculate_sit_adjusted_price()` | 159-172 | Keep as-is. This is the core formula: $P \times (40 / AA\_score)$ |
| `get_reasoning_multiplier()` | 142-157 | Deprecate. Stop calling it in `normalize_model()` and `build_orphan_snapshots()` |
| `calculate_sit_scores()` | 2297-2331 | Stop calling in `main()`. Keep function for backward compat / backfill scripts |
| `get_stable_tier_medians()` | 2388+ | Stop calling for SIT scoring. May keep for per-tier index calculation |
| `calculate_composite_usage_weighted()` | 2482-2519 | Replace with `calculate_tpi()`: equal weight per provider, 30% cap, quality gate |
| `normalize_model()` | 2114-2192 | Stop setting `reasoning_multiplier` and `sit_score`. Keep `sit_adjusted_price` |
| `main()` | ~3170 | Stop calling `calculate_sit_scores(priced, tier_avgs)`. Keep `sit_adjusted_price` in snapshots |

### 2.2 New TPI Calculation

```python
def calculate_tpi(conn):
    """Token Price Index: equal-weight per provider, 30% cap, quality gate >= 35.
    
    TPI = sum(w_i * P_i * (S_ref / S_i))
    where w_i is equal per provider (capped at 30%), P_i is the cheapest
    SIT-qualified model's blended price for that provider, S_ref = 40 (GPT-4-Turbo).
    """
    # 1. Get all active models with AA score >= 35 and priced snapshots
    # 2. For each provider, take their cheapest SIT-qualified model
    # 3. Equal weight per provider, cap any single provider at 30%
    # 4. Compute weighted mean of sit_adjusted_price
```

### 2.3 Database Schema

No schema changes needed. Existing columns:
- `price_snapshots.sit_score` - keep, will be NULL for new rows
- `price_snapshots.reasoning_multiplier` - keep, will be 1.0 for new rows
- `price_snapshots.sit_adjusted_price` - keep, this is the primary metric
- `sit_index_values.calculation_method` - new value: `tpi_equal_weight_provider_capped`
- `latest_prices` matview - no change (still exposes sit_score, will be NULL)

### 2.4 API Backend (`api.py`)

| Line | Current | Change |
|------|---------|--------|
| 220 | `sit_score,` in SELECT | Keep (backward compat) |
| 221 | `reasoning_multiplier,` in SELECT | Keep (will be 1.0) |
| 718 | `sort: str = Query("sit_score", ...)` | Change default to `sit_adjusted_price`. Keep `sit_score` as alias |
| 736 | `lp.sit_score, lp.reasoning_multiplier, lp.sit_adjusted_price` | Keep all three |
| 782 | `"sit_score": "lp.sit_score ASC NULLS LAST"` | Change to sort by `sit_adjusted_price` |
| 823-824 | Response includes `sit_score` and `reasoning_multiplier` | Keep. Add `sit_adjusted_price` if not already in response |

### 2.5 Backfill Script (`backfill_sit_adjusted.py`)

The existing backfill script recomputes `reasoning_multiplier`, `sit_adjusted_price`, and `sit_score` for historical data. After the redesign:
- `reasoning_multiplier` backfill: skip (set to 1.0)
- `sit_adjusted_price` backfill: keep (recalculate without reasoning multiplier: $P \times (40 / AA)$)
- `sit_score` backfill: skip (no longer needed)
- Add: TPI recalculation for all historical `sit_index_values` composite rows

---

## 3. Historical Price Continuity

### 3.1 The Problem

The SIT-Composite index has been published daily since 2026-08-03 with base value 1000. The calculation method was `usage_weighted_quality_gated`. If we switch to `tpi_equal_weight_provider_capped`, the index value will jump because:
- Different weighting (equal per provider vs usage-weighted top 50)
- Different model inclusion (cheapest per provider vs top 50 by usage)
- Different provider coverage (the 3 new scrapers add providers)

### 3.2 The Solution

**Recalculate full history.** We have all raw data in `price_snapshots` going back to Aug 3. For each day:
1. Query `price_snapshots` for the last snapshot of each model on that date
2. Filter to AA score >= 35
3. For each provider, take their cheapest SIT-qualified model
4. Apply equal weight with 30% cap
5. Compute TPI = weighted mean of `sit_adjusted_price`
6. Insert into `sit_index_values` with `calculation_method = 'tpi_equal_weight_provider_capped'`
7. Rebase to 1000 at base date (2026-08-03)

**Keep old values.** Don't delete the old `usage_weighted_quality_gated` rows. They remain as historical record. The API serves the latest calculation method.

### 3.3 What the Chart Will Show

The index line will shift when the method changes, but the trend (slope) should be similar since both methods track the same underlying prices. The key difference: TPI will be less volatile because it's not dependent on usage_weights changes.

### 3.4 Index Points Recalculation

For each date $d$ since base date:
$$Index_d = 1000 \times \frac{TPI_d}{TPI_{base}}$$

Where $TPI_{base}$ is the TPI on 2026-08-03 computed with the new method.

---

## 4. What Could Go Wrong

### 4.1 TPI Jumps When Providers Are Added

Adding the 3 new scrapers (Z.AI, Alibaba, Moonshot) adds 3 new providers to the TPI basket. With equal-weight-per-provider, each provider gets ~1/(N+3) of the weight. If these providers are cheaper than the current average, the TPI drops on the day they're added.

**Severity:** Medium. This is expected behaviour for a commodity index (adding suppliers changes the price). But it looks like a real price drop when it's actually a methodology change.

**Mitigation:** Publish a methodology change note. Run the recalculation with and without the new providers to show the impact separately.

### 4.2 Cheapest-Model-Per-Provider Is Gameable

A provider could launch a loss-leader model at $0.01/M with a decent AA score, and that becomes their TPI contribution, dragging the index down.

**Severity:** Low-Medium. The quality gate (AA >= 35) limits this to genuinely capable models. And a provider gaming the TPI downward is actually good for consumers.

**Mitigation:** Consider using median model per provider instead of cheapest. Or: require the model to have been priced for at least 7 days before inclusion.

### 4.3 Dropping Reasoning Multiplier Makes Reasoning Models Look Cheap

A reasoning model at $1/M output that generates 5x thinking tokens effectively costs $5/M of useful output. Without the multiplier, it ranks as if it costs $1/M.

**Severity:** Medium. This affects maybe 20-30% of models (reasoning models are a growing category).

**Mitigation:** Show `is_reasoning` badge prominently in the table. Add a note: "Reasoning models generate additional thinking tokens not reflected in output price." Consider a "thinking-adjusted price" as a future enhancement if thinking token ratios become available.

### 4.4 Models Without AA Scores (254 of 546 Active)

These models get no `sit_adjusted_price` and are excluded from TPI. They appear in the table with "N/A" for Cost / IQ.

**Severity:** Low. Same as current behaviour. But note: nearly half the catalog is unranked, which could look bad.

**Mitigation:** Show the count of ranked vs unranked. "X of Y models have quality-adjusted pricing." The unranked models are still sortable by raw price.

### 4.5 Historical TPI Recalculation Could Show Different Trend

If the new TPI formula produces a different trend direction than the old SIT-Composite (e.g., old showed prices rising, new shows them falling), it undermines confidence in the index.

**Severity:** Low. Both formulas track the same underlying prices. The trend should be similar. But the magnitude of changes will differ.

**Mitigation:** Before deploying, run the recalculation and compare old vs new for the full history. If the trends diverge significantly, investigate why and document it.

### 4.6 API Consumers Break

External consumers using `sit_score` from the API will see it go to NULL.

**Severity:** Low. We don't know of any external consumers beyond the website itself. But the API is public.

**Mitigation:** Keep `sit_score` in responses (NULL for new data). Add `sit_adjusted_price`. Add a deprecation notice. Don't remove `sit_score` from the schema.

### 4.7 Daily Tier Medians Table Becomes Orphaned

The `daily_tier_medians` table was built to stabilize SIT scores. If we stop computing SIT scores, this table stops getting new rows. The per-tier indices still use medians, but those are computed differently.

**Severity:** Very low. Just unused data.

**Mitigation:** Stop writing to it. Keep historical data. No action needed.

### 4.8 `data_integrity_check.py` Needs Updates

- Check 2 (SIT stability): becomes irrelevant. Replace with TPI stability check.
- Check 6 (composite methodology): the `bad_methods` check needs to accept the new method name.
- Check 7 (index frozen at 1000): update for new TPI calculation.

**Severity:** Medium. If we don't update the check, it will flag the new method as "inconsistent" (check 6) and the TPI will fail the SIT stability check (check 2).

**Mitigation:** Update `data_integrity_check.py` in the same deployment as the pipeline change.

---

## 5. Deployment Sequence

1. **Pipeline changes:** New TPI function, stop computing sit_score/reasoning_multiplier
2. **Historical recalculation script:** Backfill TPI for all dates since Aug 3
3. **API changes:** Default sort to sit_adjusted_price, keep sit_score as NULL
4. **Integrity check update:** Accept new method name, replace SIT stability check
5. **Website changes:** All UI files updated atomically
6. **Methodology doc:** Publish v0.2
7. **Test:** Run pipeline --fetch-only, verify TPI. Compare old vs new index chart.

Do NOT deploy piecemeal. The pipeline, API, and website should go live together to avoid showing inconsistent data.
