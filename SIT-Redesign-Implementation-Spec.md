# SIT Redesign: Implementation Specification

**Date:** 2026-08-28
**Author:** Frank
**Purpose:** Step-by-step implementation guide for a fresh agent (Kimi K3) with no prior context.
**Related:** [[SIT-Redesign-Brainstorm]], [[SIT-Redesign-Review]], [[sit-methodology]]

---

## 0. Project Context

**InferenceIndexer.ai** is an independent price index for AI inference. Architecture:

```
OpenRouter + Direct Scrapers → pipeline.py → Supabase (Postgres) → api.py (FastAPI on Lightsail) → Next.js frontend (Vercel SSG + ISR)
```

**All code lives in:** `/home/ubuntu/obsidian-vault/10-Projects/inference-futures-exchange/`
**Python venv:** `.venv/bin/python3`
**DB:** Supabase Postgres. Connection string in `~/.hermes/.env` as `SUPABASE_DB_URL`.
**Cron:** `crontab -l` (pipeline runs hourly, endpoints daily at 3am, niche pricing hourly at :05)
**Website:** Next.js in `web/`, deployed to Vercel (SSG + ISR, 300s revalidation)
**API:** FastAPI (`api.py`), runs on Lightsail at `3.255.179.226`, Nginx proxy with 5min timeout

**Read these first:**
- `SIT-Redesign-Brainstorm.md` (design rationale)
- `SIT-Redesign-Review.md` (change inventory + risks)
- `sit-methodology.md` (current methodology, v0.1)

---

## 1. What We're Changing

### Current State
- Per-model "SIT Score" = `(sit_adjusted_price / tier_median) * 100`, 100 = tier median. Tier-relative, not comparable across tiers.
- SIT-Composite = usage-weighted top 50 models by usage_weights, quality gate AA >= 35.
- Reasoning multiplier (2x-4x) inflates price for reasoning models.
- 4 tiers: frontier (AA>=50), standard (30-49), budget (15-29), micro (<15).

### Target State
- Per-model ranking = `sit_adjusted_price` directly (cost per GPT-4-equivalent token). Absolute, comparable across all models.
- TPI (Token Price Index) replaces SIT-Composite = equal-weight per provider, 30% cap, quality gate AA >= 35, cheapest SIT-qualified model per provider.
- No reasoning multiplier. `is_reasoning` flag shown in UI only.
- Tiers remain as UI filter and for per-tier indices, but NOT for per-model scoring.
- `sit_score` column kept in DB and API for backward compat (NULL for new snapshots).

---

## 2. Pipeline Changes (`pipeline.py`)

### 2.1 Stop Applying Reasoning Multiplier to SIT-Adjusted Price

In `normalize_model()` (line ~2172), the `sit_adjusted_price` is currently:
```python
sit_adjusted_price = calculate_sit_adjusted_price(
    blended_price_per_m, reasoning_multiplier, aa_score
)
```

Change `calculate_sit_adjusted_price()` (line 159-172) to ignore the reasoning multiplier:

```python
def calculate_sit_adjusted_price(blended_price, reasoning_multiplier=None, aa_score=None):
    """Calculate the quality-adjusted price (Cost per IQ).
    
    Quality-Adjusted Price = Blended Price * (GPT-4-Turbo Reference / AA Intelligence Score)
    
    The reasoning_multiplier parameter is kept for backward compatibility but ignored.
    Reasoning token overhead varies by task, not model, so a fixed multiplier is misleading.
    The is_reasoning flag is shown in the UI instead.
    """
    if not aa_score or aa_score <= 0:
        return None
    return round(blended_price * (GPT4_TURBO_AA_REFERENCE / aa_score), 6)
```

### 2.2 Stop Computing SIT Scores in main()

In `main()` (line ~3170), there's:
```python
priced = calculate_sit_scores(priced, tier_avgs)
```

Comment this out or remove it. The `calculate_sit_scores()` function stays in the file (for backward compat / backfill scripts) but is no longer called from `main()`.

### 2.3 Add TPI Calculation Function

Add this new function after `calculate_composite_usage_weighted()` (line ~2519):

```python
def calculate_tpi(conn):
    """Calculate the Token Price Index (TPI).
    
    TPI = equal-weight per provider, 30% cap, quality gate AA >= 35.
    For each provider, take their cheapest SIT-qualified model's sit_adjusted_price.
    Weight each provider equally, cap any single provider at 30% of total weight.
    
    This replaces the old usage_weighted_quality_gated composite calculation.
    """
    cur = conn.cursor()
    
    # Step 1: For each provider, find their cheapest SIT-qualified model
    cur.execute("""
        WITH qualified AS (
            SELECT m.id, m.provider, m.tier,
                   lp.blended_price_per_m,
                   lp.sit_adjusted_price,
                   lp.sit_score
            FROM models m
            JOIN latest_prices lp ON m.id = lp.model_id
            WHERE m.is_active = TRUE
              AND lp.blended_price_per_m > 0
              AND lp.sit_adjusted_price IS NOT NULL
              AND lp.sit_adjusted_price > 0
              AND m.aa_index_score IS NOT NULL
              AND m.aa_index_score >= 35
              AND m.id NOT LIKE '%%:batch'
              AND m.modality NOT IN ('embedding', 'tts', 'stt', 'reranker', 'reader',
                                      'image-generation', 'video-generation')
        ),
        cheapest_per_provider AS (
            SELECT DISTINCT ON (provider)
                provider,
                sit_adjusted_price
            FROM qualified
            ORDER BY provider, sit_adjusted_price ASC
        )
        SELECT provider, sit_adjusted_price
        FROM cheapest_per_provider
        ORDER BY provider
    """)
    
    providers = cur.fetchall()
    cur.close()
    
    if not providers:
        return {"price": 0.0, "model_count": 0, "provider_count": 0}
    
    n = len(providers)
    base_weight = 1.0 / n
    capped_weight = min(base_weight, 0.30)
    
    # Normalize weights after cap
    total_weight = sum(min(base_weight, 0.30) for _ in providers)
    weights = [min(base_weight, 0.30) / total_weight for _ in providers]
    
    tpi = sum(w * p[1] for w, p in zip(weights, providers))
    
    return {
        "price": round(tpi, 6),
        "model_count": n,  # one model per provider
        "provider_count": n,
    }
```

### 2.4 Replace Composite Calculation in main()

In `main()` (line ~3175), replace:

```python
composite_data = calculate_composite_usage_weighted(conn)
```

With:

```python
composite_data = calculate_tpi(conn)
```

### 2.5 Update insert_sit_values() Method Name

In `insert_sit_values()` (line ~2884), change the composite method name:

```python
# OLD:
if tier == "composite":
    method = "usage_weighted_quality_gated"

# NEW:
if tier == "composite":
    method = "tpi_equal_weight_provider_capped"
```

### 2.6 Stop Setting reasoning_multiplier in normalize_model()

In `normalize_model()` (line ~2169), the reasoning_multiplier is computed and set. Keep it in the dict (for DB compat) but set it to 1.0:

```python
# Keep for DB backward compat, but always 1.0 (no longer used in SIT calculation)
reasoning_multiplier = 1.0
```

Remove or comment out the `get_reasoning_multiplier()` call. Keep the function itself for backward compat.

### 2.7 Same Changes in build_orphan_snapshots()

In `build_orphan_snapshots()` (line ~2750), the same pattern applies:
- Set `reasoning_mult = 1.0` (don't call `get_reasoning_multiplier`)
- The `sit_adjusted_price` calculation already calls `calculate_sit_adjusted_price` which will now ignore the multiplier

---

## 3. Historical Recalculation Script

Create a new file: `recalculate_tpi_history.py`

```python
#!/usr/bin/env python3
"""
One-time script: Recalculate SIT-Composite index values using the new TPI method
for all dates from 2026-08-04 (first data) to today.

Old method: usage_weighted_quality_gated
New method: tpi_equal_weight_provider_capped

Does NOT delete old rows. Inserts new rows with the new method name.
If a row already exists for (date, 'composite') with the new method, updates it.

Usage:
    .venv/bin/python3 recalculate_tpi_history.py           # Full run
    .venv/bin/python3 recalculate_tpi_history.py --dry-run  # Preview only
"""
import os, sys, argparse
from datetime import date, timedelta
from dotenv import dotenv_values
import psycopg2

# Load config
env_path = os.path.expanduser("~/.hermes/.env")
vals = dotenv_values(env_path)
DB_URL = vals["SUPABASE_DB_URL"]

# Constants (must match pipeline.py)
GPT4_TURBO_AA_REFERENCE = 40.0
QUALITY_FLOOR = 35.0
BASE_VALUE = 1000.0
BASE_DATE = date(2026, 8, 3)  # Original base date

def get_db():
    return psycopg2.connect(DB_URL, connect_timeout=10)

def calculate_tpi_for_date(conn, target_date):
    """Calculate TPI for a specific date using the last snapshot of each model on that date."""
    cur = conn.cursor()
    
    # Get the last snapshot per model for the target date
    cur.execute("""
        WITH last_snap AS (
            SELECT DISTINCT ON (model_id)
                ps.model_id, ps.blended_price_per_m, ps.sit_adjusted_price,
                m.provider, m.aa_index_score, m.modality, m.is_active
            FROM price_snapshots ps
            JOIN models m ON ps.model_id = m.id
            WHERE ps.fetched_at::date = %s
              AND m.aa_index_score IS NOT NULL
              AND m.aa_index_score >= %s
              AND m.id NOT LIKE '%%:batch'
              AND m.modality NOT IN ('embedding', 'tts', 'stt', 'reranker', 'reader',
                                      'image-generation', 'video-generation')
            ORDER BY ps.model_id, ps.fetched_at DESC
        ),
        cheapest_per_provider AS (
            SELECT DISTINCT ON (provider)
                provider,
                sit_adjusted_price,
                blended_price_per_m
            FROM last_snap
            WHERE sit_adjusted_price IS NOT NULL
              AND sit_adjusted_price > 0
              AND blended_price_per_m > 0
            ORDER BY provider, sit_adjusted_price ASC
        )
        SELECT provider, sit_adjusted_price, blended_price_per_m
        FROM cheapest_per_provider
        ORDER BY provider
    """, (target_date, QUALITY_FLOOR))
    
    providers = cur.fetchall()
    cur.close()
    
    if not providers:
        return None
    
    # Equal weight per provider, 30% cap
    n = len(providers)
    base_weight = 1.0 / n
    capped = [min(base_weight, 0.30) for _ in providers]
    total = sum(capped)
    weights = [w / total for w in capped]
    
    tpi = sum(w * p[1] for w, p in zip(weights, providers))
    
    return {
        "price": round(tpi, 6),
        "model_count": n,
        "provider_count": n,
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    
    conn = get_db()
    
    # Get date range
    cur = conn.cursor()
    cur.execute("SELECT MIN(fetched_at::date), MAX(fetched_at::date) FROM price_snapshots")
    first_date, last_date = cur.fetchone()
    cur.close()
    
    print(f"Recalculating TPI from {first_date} to {last_date}")
    
    # Calculate TPI for base date first (for rebaselining)
    # The base date is the first date we have data
    base_tpi = calculate_tpi_for_date(conn, first_date)
    if not base_tpi:
        print("ERROR: Could not calculate base TPI. Aborting.")
        sys.exit(1)
    
    base_price = base_tpi["price"]
    print(f"Base TPI ({first_date}): ${base_price}")
    
    # Iterate through all dates
    current = first_date
    count = 0
    while current <= last_date:
        result = calculate_tpi_for_date(conn, current)
        
        if result:
            index_points = round((result["price"] / base_price) * BASE_VALUE, 2)
            
            if not args.dry_run:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO sit_index_values
                        (date, tier, sit_price, sit_index_points, model_count,
                         provider_count, calculation_method)
                    VALUES (%s, 'composite', %s, %s, %s, %s, 'tpi_equal_weight_provider_capped')
                    ON CONFLICT (date, tier) DO UPDATE SET
                        sit_price = EXCLUDED.sit_price,
                        sit_index_points = EXCLUDED.sit_index_points,
                        model_count = EXCLUDED.model_count,
                        provider_count = EXCLUDED.provider_count,
                        calculation_method = EXCLUDED.calculation_method,
                        calculated_at = NOW()
                """, (
                    current, result["price"], index_points,
                    result["model_count"], result["provider_count"]
                ))
                conn.commit()
                cur.close()
            
            print(f"  {current}: TPI=${result['price']:.4f} index={index_points:.2f} ({result['provider_count']} providers)")
            count += 1
        else:
            print(f"  {current}: No data, skipping")
        
        current += timedelta(days=1)
    
    print(f"\n{'Would insert' if args.dry_run else 'Inserted'} {count} TPI values")
    conn.close()

if __name__ == "__main__":
    main()
```

**Run order:**
1. Dry run first: `.venv/bin/python3 recalculate_tpi_history.py --dry-run`
2. Review output (check base TPI, trend direction, provider counts)
3. Full run: `.venv/bin/python3 recalculate_tpi_history.py`

---

## 4. API Changes (`api.py`)

### 4.1 Change Default Sort

Line 718:
```python
# OLD:
sort: str = Query("sit_score", regex="^(blended|input|output|sit_score)$"),

# NEW:
sort: str = Query("sit_adjusted_price", regex="^(blended|input|output|sit_score|sit_adjusted_price)$"),
```

### 4.2 Update Sort Map

Lines 778-784:
```python
# OLD:
sort_map = {
    "blended": "lp.blended_price_per_m ASC",
    "input": "lp.input_price_per_m ASC",
    "output": "lp.output_price_per_m ASC",
    "sit_score": "lp.sit_score ASC NULLS LAST",
}
query += f" ORDER BY {sort_map.get(sort, sort_map['sit_score'])}"

# NEW:
sort_map = {
    "blended": "lp.blended_price_per_m ASC",
    "input": "lp.input_price_per_m ASC",
    "output": "lp.output_price_per_m ASC",
    "sit_score": "lp.sit_adjusted_price ASC NULLS LAST",  # alias, same as sit_adjusted_price
    "sit_adjusted_price": "lp.sit_adjusted_price ASC NULLS LAST",
}
query += f" ORDER BY {sort_map.get(sort, sort_map['sit_adjusted_price'])}"
```

### 4.3 No Other API Changes

The API already returns `sit_adjusted_price` (line 825). It also returns `sit_score` (line 823) and `reasoning_multiplier` (line 824). Keep all three in the response. New snapshots will have `sit_score = NULL` and `reasoning_multiplier = 1.0`, but the fields stay for backward compat.

---

## 5. Integrity Check Changes (`data_integrity_check.py`)

### 5.1 Check 2: Replace SIT Stability with TPI Stability

Replace the SIT score stability check (lines 80-93) with:

```python
    # ---- 2. TPI stability (daily TPI should not move > 20%) ----
    cur.execute("""
        SELECT date, sit_price, sit_index_points
        FROM sit_index_values
        WHERE tier = 'composite'
          AND calculation_method = 'tpi_equal_weight_provider_capped'
        ORDER BY date DESC
        LIMIT 3
    """)
    recent_tpi = cur.fetchall()
    print("[2] TPI stability (last 3 daily values)")
    for r in recent_tpi:
        print("    %s: $%s (index %s)" % (r[0], r[1], r[2]))
    if len(recent_tpi) >= 2:
        latest_tpi = recent_tpi[0][1]
        prev_tpi = recent_tpi[1][1]
        if prev_tpi > 0:
            change = abs((latest_tpi - prev_tpi) / prev_tpi)
            if change > 0.20:
                issues.append("TPI moved %.1f%% in one day ($%s -> $%s)" % (
                    change * 100, prev_tpi, latest_tpi))
```

### 5.2 Check 6: Accept New Method Name

Lines 144-149, update the `bad_methods` check:

```python
    # OLD:
    bad_methods = [m[0] for m in methods if m[0] != "usage_weighted_quality_gated"]
    
    # NEW:
    valid_methods = {"tpi_equal_weight_provider_capped", "usage_weighted_quality_gated"}
    bad_methods = [m[0] for m in methods if m[0] not in valid_methods]
```

### 5.3 Check 7: Update Frozen Check

Line 164, update the frozen-at-1000 check to handle the new method:

```python
    # OLD:
    if frozen and frozen == 7:  # all historical rows frozen = rebase never ran
    
    # NEW: Check only new-method rows
    cur.execute("""
        SELECT COUNT(*) FILTER (WHERE sit_index_points = 1000)
        FROM sit_index_values
        WHERE tier = 'composite'
          AND calculation_method = 'tpi_equal_weight_provider_capped'
    """)
    frozen_new = cur.fetchone()[0]
    print("[7] TPI rows stuck at index 1000: %s" % frozen_new)
    if frozen_new and frozen_new > 1:  # >1 row at 1000 = rebase never ran properly
        issues.append("TPI index frozen at 1000 across %d rows" % frozen_new)
```

---

## 6. Website Changes (Next.js)

### 6.1 `web/src/components/ModelTable.tsx`

**Primary sort column:** Change from SIT Score to Cost / IQ (sit_adjusted_price).

Replace column definitions (lines 50, 66):
```typescript
// OLD:
{ key: "sit", label: "SIT Score", align: "right" },

// NEW:
{ key: "sitadj", label: "Cost / IQ", align: "right" },
```

Replace sort logic (lines 97-98, 169-172, 199-202):
```typescript
// Sort by sit_adjusted_price always (not tier-relative)
// Remove the "all" vs "specific tier" split
const av = a.sit_adjusted_price;
const bv = b.sit_adjusted_price;
if (av == null && bv == null) return 0;
if (av == null) return 1;
if (bv == null) return -1;
return (av - bv) * sign;
```

Replace tooltip (line 482):
```typescript
// OLD:
SIT Score is tier-relative (100 = your tier's median). Lower = cheaper than your tier's median. Colors match tier: gold = Frontier, blue = Standard, green = Budget, grey = Micro. Scores are NOT comparable across tiers.

// NEW:
Cost / IQ = quality-adjusted price per million tokens. Lower = better value. Comparable across ALL models. Quality-adjusted using AA Intelligence Index (GPT-4-Turbo = 40 reference score).
```

Replace tooltip (line 707):
```typescript
// OLD:
title={s != null ? `${m.name}: SIT Score ${s} (${capitalizeTier(m.tier)} tier, 100 = tier median. Lower = cheaper than median. Score is tier-relative, not comparable across tiers.)` : `${m.name}: no AA Intelligence Index score, SIT Score not available`}

// NEW:
title={m.sit_adjusted_price != null ? `${m.name}: Cost / IQ $${m.sit_adjusted_price.toFixed(4)}/M (quality-adjusted, lower = better value)` : `${m.name}: no AA Intelligence Index score, Cost / IQ not available`}
```

Replace SIT Score cell rendering (line 510, 707) with sit_adjusted_price rendering:
```typescript
// OLD: shows sit_score as integer
// NEW: shows sit_adjusted_price as $X.XXXX
const adj = m.sit_adjusted_price;
// ... render adj != null ? `$${adj.toFixed(4)}` : "N/A"
```

Replace tier ranking logic (lines 217-218):
```typescript
// OLD: filter by tier and sort by sit_score
// NEW: sort all by sit_adjusted_price, tier is just a filter
.sort((a, b) => (a.sit_adjusted_price! - b.sit_adjusted_price!));
```

### 6.2 `web/src/app/models/[...modelId]/page.tsx`

Replace SIT Score section (lines 73, 79-80, 150, 189, 392-405, 413, 418, 423, 430, 464):

- Line 73: `const sitScore = model.sit_score != null ? model.sit_score : null;` → remove or keep as secondary
- Line 80: Meta description: replace "SIT Score X (Frontier tier)" with "Cost / IQ $X/M"
- Line 150: JSON-LD: `"SIT Score"` → `"Cost / IQ"`, `value: model.sit_score` → `value: model.sit_adjusted_price`
- Lines 392-405: Replace SIT Score bar with Cost / IQ display:
```tsx
{/* Cost / IQ */}
<span style={{ fontSize: 12, color: "#8a8a8a" }}>Cost / IQ (quality-adjusted $/M)</span>
// Show absolute value, not relative to tier median
{model.sit_adjusted_price != null ? `$${model.sit_adjusted_price.toFixed(4)}/M` : "N/A (no AA score)"}
// Compare to TPI instead of tier median
{model.comparisons.above_composite_pct}% above SIT-Composite
```
- Lines 413-418: Remove "below/above tier median" comparison. Replace with "below/above TPI" using composite price.
- Line 430: "Tier Ranking (by SIT Score)" → "Value Ranking (by Cost / IQ)"
- Line 464: JSON snippet: `sit_score` → `sit_adjusted_price`

### 6.3 `web/src/app/page.tsx`

- Line 419: "Ranked by SIT Score below, our price-per-intelligence metric." → "Ranked by Cost / IQ, our quality-adjusted price per million tokens."
- Lines 30, 39, 118-119: Keep "SIT-Composite" in metadata (brand name). No change needed.

### 6.4 `web/src/app/methodology/page.tsx`

Major rewrite of the methodology page:

- Line 37: Keep SIT definition. Update composite description.
- Line 45: Replace "usage-weighted mean of top 50" with "equal-weight per provider, 30% cap"
- Line 61: Keep tier description but note tiers are for filtering/index, not per-model scoring
- Lines 375-376: Remove SIT Score formula. Replace with:
  ```
  Cost / IQ = Blended Price × (40 / AA Intelligence Score)
  Lower = cheaper per unit of intelligence. Comparable across all models.
  ```
- Lines 398-399: Remove "100 = tier median" explanation
- Lines 407-417: Replace usage-weighting description with TPI formula:
  ```
  TPI = Σ(w_i × SIT-adjusted-price_i)
  where w_i = equal weight per provider, capped at 30% per provider
  Only the cheapest SIT-qualified model per provider is included.
  Quality gate: AA Intelligence Index >= 35 (GPT-4-Turbo baseline).
  ```

### 6.5 `web/src/app/api-docs/page.tsx`

- Line 329: `sort=sit_score` → `sort=sit_adjusted_price` (keep sit_score as alias)
- Lines 344, 371: Update example JSON to show `sit_adjusted_price` instead of `sit_score`
- Line 11: "SIT scores" → "quality-adjusted prices"

### 6.6 `web/src/lib/api.ts`

No type changes needed. `sit_score`, `sit_adjusted_price`, and `reasoning_multiplier` all already exist in the types.

### 6.7 `web/src/components/ProviderModelTable.tsx`

Already has `sit_adjusted_price` column labeled "Cost / IQ". Just ensure default sort is by `sit_adjusted_price` instead of `sit_score`.

### 6.8 `web/src/app/for-agents/page.tsx` and `web/src/app/about/page.tsx`

Keep "SIT-Composite" references (brand name). No changes needed unless renaming to TPI.

---

## 7. Methodology Document Update

Update `sit-methodology.md` to v0.2:

- Section 2.3: Remove reasoning multiplier from quality standard description
- Section 3.1: Change SIT-Composite calculation from usage-weighted to TPI (equal-weight per provider, 30% cap)
- Section 3.4: Replace formula:
  ```
  # OLD:
  SIT-Composite = Σ(blended_price_i × weight_i) / Σ(weight_i)
  
  # NEW:
  TPI = Σ(w_p × min_sit_adjusted_price_p)
  where w_p = equal weight per provider, capped at 30%
  min_sit_adjusted_price_p = cheapest SIT-qualified model's sit_adjusted_price for provider p
  ```
- Add new section: "Per-Model Ranking" explaining Cost / IQ = sit_adjusted_price, absolute, cross-tier comparable
- Remove or deprecate the old "SIT Score" section (100 = tier median)
- Version bump: 0.1 → 0.2
- Add changelog note: "v0.2: Replaced tier-relative SIT Score with absolute Cost / IQ. Replaced usage-weighted composite with TPI (equal-weight per provider). Removed reasoning multiplier."

---

## 8. Deployment Sequence

**Do NOT deploy piecemeal. All steps must go live together.**

### Step 1: Pipeline changes
```bash
cd /home/ubuntu/obsidian-vault/10-Projects/inference-futures-exchange

# Test pipeline imports
.venv/bin/python3 -c "import pipeline; print('OK')"

# Test TPI calculation (fetch-only, no DB writes)
.venv/bin/python3 pipeline.py --fetch-only 2>&1 | grep -E "TPI|composite|SIT"
```

### Step 2: Historical recalculation
```bash
# Dry run first
.venv/bin/python3 recalculate_tpi_history.py --dry-run

# Review output. Check:
# - Base TPI value is reasonable ($1-5 range)
# - Trend direction matches old composite
# - Provider count increases over time as scrapers were added

# Full run
.venv/bin/python3 recalculate_tpi_history.py
```

### Step 3: Integrity check update
```bash
# Test the updated integrity check
.venv/bin/python3 data_integrity_check.py
# Should pass with 0 issues (or only the known 386 unpriced models issue)
```

### Step 4: API changes
```bash
# api.py runs on Lightsail. SSH to deploy.
# After updating api.py, restart the API:
ssh ubuntu@3.255.179.226 "cd /home/ubuntu/inference-indexer && sudo systemctl restart inferenceindexer-api"

# NEVER use `pkill -f uvicorn` + nohup: a leftover nohup uvicorn holding port 8000
# caused a 13,800-restart systemd crash-loop on Aug 27-28 2026. The service is
# systemd-managed; restart it with systemctl only. api.py can be copied over with
# scp from the vault repo before restarting.
```

### Step 5: Website changes
```bash
cd /home/ubuntu/obsidian-vault/10-Projects/inference-futures-exchange/web

# Build test
npm run build

# Deploy to Vercel
npx vercel --prod
```

### Step 6: Methodology doc
Update `sit-methodology.md` in the Obsidian vault. The website methodology page reads from a hardcoded copy, so update both.

### Step 7: Verify
```bash
# Check API returns sit_adjusted_price as default sort
curl "https://api.inferenceindexer.ai/v1/models?limit=3" | python3 -m json.tool | head -20

# Check website loads
curl -s https://inferenceindexer.ai | grep -o "Cost / IQ"

# Check integrity check passes
.venv/bin/python3 data_integrity_check.py

# Wait for next cron run (top of the hour), then check:
# 1. New snapshots have sit_score = NULL
# 2. New snapshots have reasoning_multiplier = 1.0
# 3. TPI is calculated and inserted
# 4. latest_prices matview is refreshed
```

---

## 9. Verification Checklist

After deployment, verify:

- [ ] Pipeline runs without errors on next cron tick
- [ ] New price_snapshots have `sit_score = NULL`
- [ ] New price_snapshots have `reasoning_multiplier = 1.0`
- [ ] New price_snapshots have `sit_adjusted_price` populated (for models with AA scores)
- [ ] `sit_index_values` has new rows with `calculation_method = 'tpi_equal_weight_provider_capped'`
- [ ] TPI value is in a reasonable range ($1-5/M)
- [ ] TPI index points are near 1000 for the base date
- [ ] `latest_prices` matview is refreshed (sit_adjusted_price visible)
- [ ] API `/v1/models` returns models sorted by `sit_adjusted_price` by default
- [ ] API still returns `sit_score` field (NULL for new data, non-null for old)
- [ ] Website homepage shows "Cost / IQ" instead of "SIT Score"
- [ ] Model detail page shows Cost / IQ, not tier-relative score
- [ ] Methodology page describes TPI, not usage-weighted composite
- [ ] Integrity check passes with 0 issues (or only known unpriced-models issue)
- [ ] Historical TPI chart shows continuous data from Aug 4 to today

---

## 10. Rollback Plan

If something goes wrong:

1. **Revert pipeline.py changes:** `git checkout` the pipeline file, restart cron
2. **Revert API:** Redeploy old `api.py` to Lightsail
3. **Revert website:** `vercel rollback` to previous deployment
4. **Revert historical data:** Delete new-method rows and keep old-method rows:
   ```sql
   DELETE FROM sit_index_values
   WHERE calculation_method = 'tpi_equal_weight_provider_capped'
   AND tier = 'composite';
   ```
5. **Revert integrity check:** `git checkout data_integrity_check.py`

The old `usage_weighted_quality_gated` rows are NOT deleted during the forward migration, so rollback just means switching back to reading them.
