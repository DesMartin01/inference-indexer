#!/usr/bin/env python3
"""
One-time script: Backfill TPI history under the current RELATIVE (P60) methodology.

Problem: the composite price series is four different baskets stitched together
(17 providers v4.1 -> 10 v4.2 -> 9 v4.3 -> 18 relative-gate), so the homepage
chart seesaws across the AA rebase boundaries even after the Sep 4 = 1000
index-point rebase. The rebase fixed the index axis, not the price series.

Fix: recompute every historical day's composite from that day's stored
snapshots under TODAY'S methodology:
  - implied AA score per model = blended * 40 / sit_adjusted_price (exact
    inverse of the stored computation - no invented data)
  - eligibility = P60 of that day's scored population (relative, rebase-proof)
  - cheapest qualifying model per provider, equal weight, 30% cap
  - index points anchored so the recomputed 2026-09-04 value = 1000

Old composite rows are preserved: renamed to method
'tpi_equal_weight_provider_capped_gate35' before inserting new rows.
The pipeline + API keep reading 'tpi_equal_weight_provider_capped'.

Usage:
    .venv/bin/python3 backfill_tpi_relative.py --dry-run
    .venv/bin/python3 backfill_tpi_relative.py
"""
import os, json, argparse
from datetime import date, timedelta
from dotenv import dotenv_values
import psycopg2

vals = dotenv_values(os.path.expanduser("~/.hermes/.env"))
DB_URL = vals["SUPABASE_DB_URL"]

METHOD = "tpi_equal_weight_provider_capped"
ARCHIVED = "tpi_equal_weight_provider_capped_gate35"
REBASE_DATE = date(2026, 9, 4)
BASE_VALUE = 1000.0
EXCLUDED_MODALITIES = ("embedding", "tts", "stt", "reranker", "reader",
                       "image-generation", "video-generation")

ERA_BOUNDARIES = [
    ("v4.1", None, "2026-09-04"),
    ("v4.2", "2026-09-05", "2026-09-06"),
    ("v4.3", "2026-09-07", None),
]

def era_for(d_iso):
    for name, start, end in ERA_BOUNDARIES:
        if start and d_iso < start:
            continue
        if end and d_iso > end:
            continue
        return name
    return None

def percentile(sorted_vals, p):
    if not sorted_vals:
        return None
    i = (len(sorted_vals) - 1) * p
    lo = int(i)
    frac = i - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[min(lo + 1, len(sorted_vals) - 1)] * frac

def tpi_for_date(cur, d):
    """Recompute one day's composite under the relative P60 methodology."""
    cur.execute("""
        SELECT DISTINCT ON (ps.model_id)
            m.provider, ps.blended_price_per_m, ps.sit_adjusted_price
        FROM price_snapshots ps
        JOIN models m ON ps.model_id = m.id
        WHERE ps.fetched_at::date = %s
          AND ps.blended_price_per_m > 0
          AND ps.sit_adjusted_price IS NOT NULL
          AND ps.sit_adjusted_price > 0
          AND ps.model_id NOT LIKE '%%:batch'
          AND m.modality NOT IN %s
        ORDER BY ps.model_id, ps.fetched_at DESC
    """, (d, EXCLUDED_MODALITIES))
    rows = cur.fetchall()
    if not rows:
        return None

    scored = sorted(float(b) * 40.0 / float(s) for _, b, s in rows)
    if len(scored) >= 50:
        threshold = percentile(scored, 0.60)
    else:
        threshold = 35.0

    # Cheapest qualifying model per provider.
    best = {}
    for provider, blended, sit in rows:
        implied = float(blended) * 40.0 / float(sit)
        if implied < threshold:
            continue
        if provider not in best or float(sit) < best[provider]:
            best[provider] = float(sit)

    if not best:
        return None

    n = len(best)
    base_w = 1.0 / n
    capped = [min(base_w, 0.30) for _ in range(n)]
    total = sum(capped)
    weights = [w / total for w in capped]
    price = sum(w * v for w, v in zip(weights, best.values()))
    return {
        "price": price,
        "providers": n,
        "threshold": round(threshold, 4),
        "basket": sorted(best.keys()),
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    conn = psycopg2.connect(DB_URL, connect_timeout=10)
    cur = conn.cursor()

    # Date range: first snapshot day through today
    cur.execute("SELECT MIN(fetched_at)::date FROM price_snapshots")
    first = cur.fetchone()[0]
    today = date.today()
    dates = [first + timedelta(days=i) for i in range((today - first).days + 1)]
    print(f"Recomputing {len(dates)} days ({first} .. {today}) under relative P60 gate\n")

    series = {}
    for d in dates:
        r = tpi_for_date(cur, d)
        if r:
            series[d] = r

    if not series:
        print("No computable days - aborting.")
        return 1

    anchor = series.get(REBASE_DATE)
    if not anchor:
        print(f"ERROR: {REBASE_DATE} not computable; cannot anchor index points.")
        return 1
    print(f"Anchor {REBASE_DATE}: recomputed price ${anchor['price']:.4f} = {BASE_VALUE:.0f}\n")

    print("date       | price    | index    | providers | threshold")
    for d in sorted(series):
        r = series[d]
        pts = round(r["price"] / anchor["price"] * BASE_VALUE, 2)
        print(f"{d} | {r['price']:.4f} | {pts:8.2f} | {r['providers']:9d} | {r['threshold']}")

    if args.dry_run:
        print(f"\nDRY RUN: nothing written. Would archive old composite rows to '{ARCHIVED}' and insert {len(series)} new rows.")
        cur.close(); conn.close()
        return 0

    # 1. Archive existing current-method composite rows (preserve history)
    cur.execute("""
        UPDATE sit_index_values
        SET calculation_method = %s
        WHERE tier = 'composite' AND calculation_method = %s
    """, (ARCHIVED, METHOD))
    archived = cur.rowcount
    print(f"\nArchived {archived} old composite rows -> {ARCHIVED}")

    # 2. Insert recomputed rows under the live method name
    inserted = 0
    for d in sorted(series):
        r = series[d]
        pts = round(r["price"] / anchor["price"] * BASE_VALUE, 2)
        era = era_for(d.isoformat())
        cur.execute("""
            INSERT INTO sit_index_values
                (date, tier, sit_price, sit_index_points, model_count,
                 provider_count, calculation_method, aa_version,
                 basket_providers, eligibility_threshold, rebase_group)
            VALUES (%s, 'composite', %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (date, tier) DO UPDATE SET
                sit_price = EXCLUDED.sit_price,
                sit_index_points = EXCLUDED.sit_index_points,
                model_count = EXCLUDED.model_count,
                provider_count = EXCLUDED.provider_count,
                calculation_method = EXCLUDED.calculation_method,
                aa_version = EXCLUDED.aa_version,
                basket_providers = EXCLUDED.basket_providers,
                eligibility_threshold = EXCLUDED.eligibility_threshold,
                rebase_group = EXCLUDED.rebase_group,
                calculated_at = NOW()
        """, (
            d, round(r["price"], 6), pts, r["providers"], r["providers"],
            METHOD, era, json.dumps(r["basket"]), r["threshold"], era,
        ))
        inserted += 1
    conn.commit()
    print(f"Inserted {inserted} recomputed composite rows under '{METHOD}'")

    # Verify latest rows
    cur.execute("""
        SELECT date, sit_price, sit_index_points, provider_count
        FROM sit_index_values
        WHERE tier='composite' AND calculation_method=%s
        ORDER BY date DESC LIMIT 6
    """, (METHOD,))
    print("\nverify (latest 6):")
    for row in cur.fetchall():
        print("  ", row)

    cur.close()
    conn.close()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
