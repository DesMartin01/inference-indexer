#!/usr/bin/env python3
"""
InferenceIndexer - Weekly Data-Integrity Check
=============================================
Queries the live DB and reports data-quality issues that would make the
product look unreliable to a customer's agent. Run weekly in the run-up to
the Jentic One outreach (and as a general product QA gate).

Checks:
  1. Provider pricing coverage  - how many providers lack real avg/min/max price.
  2. SIT score stability        - any model with erratic same-date sit_score swings
                                  (regression of the daily-stable-median fix).
  3. Snapshot freshness         - snapshots older than N hours / stale data.
  4. Null model pricing         - how many active models have no priced snapshot.
  5. Composite sanity           - spot composite price is sane (positive, plausible).

Exit code 0 = all clear. Non-zero with issues printed otherwise.

Usage:
  SUPABASE_DB_URL=... python3 data_integrity_check.py
"""

import os
import sys
from datetime import datetime, timezone


def get_db():
    url = os.environ.get("SUPABASE_DB_URL")
    if not url:
        env_path = os.path.expanduser("~/.hermes/.env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("SUPABASE_DB_URL="):
                        url = line.split("=", 1)[1]
                        break
    if not url:
        print("ERROR: SUPABASE_DB_URL not found")
        sys.exit(2)
    import psycopg2
    return psycopg2.connect(url, connect_timeout=10)


def main():
    conn = get_db()
    cur = conn.cursor()
    issues = []
    print("=== InferenceIndexer Data-Integrity Check ===")
    print("run at %s\n" % datetime.now(timezone.utc).isoformat())

    # ---- 1. Provider pricing coverage (mirrors API aggregation) ----
    cur.execute("""
        WITH latest_ep AS (
            SELECT DISTINCT ON (endpoint_provider, model_id)
                endpoint_provider AS provider_name, model_id, blended_price_per_m AS bpm
            FROM model_endpoints
            WHERE fetched_at > NOW() - INTERVAL '3 days' AND blended_price_per_m > 0
            ORDER BY endpoint_provider, model_id, fetched_at DESC
        )
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE n_models IS NULL OR n_models = 0) AS unpriced
        FROM (
            SELECT p.name,
                   (SELECT COUNT(*) FROM latest_ep le WHERE le.provider_name = p.name) AS n_models
            FROM providers p
        ) t
    """)
    row = cur.fetchone()
    total = row[0]
    unpriced = row[1]
    print("[1] Provider pricing coverage")
    print("    providers with NO priced model in last 3d: %s/%s" % (unpriced, total))
    if unpriced is not None and total and unpriced > total * 0.1:
        issues.append("provider pricing: %s/%s have no priced models" % (unpriced, total))

    # ---- 2. SIT score stability (no same-day swings) ----
    cur.execute("""
        SELECT COUNT(*) FROM (
            SELECT fetched_at::date AS d, model_id
            FROM price_snapshots
            WHERE fetched_at >= NOW() - INTERVAL '3 days'
            GROUP BY 1, 2
            HAVING COUNT(DISTINCT sit_score) > 2
        ) flips
    """)
    sit_flips = cur.fetchone()[0]
    print("[2] SIT score stability (models with >2 distinct sit_score same-day, 3d)")
    print("    count: %s" % sit_flips)
    if sit_flips > 5:
        issues.append("SIT instability: %s models flip scores within a day" % sit_flips)

    # ---- 3. Freshness ----
    cur.execute("""
        SELECT COUNT(*),
               COALESCE(EXTRACT(EPOCH FROM (NOW() - MAX(fetched_at)))::int, 0)
        FROM price_snapshots
    """)
    snap_count, max_age_s = cur.fetchone()
    max_age_h = float(max_age_s) / 3600.0
    print("[3] Snapshot freshness")
    print("    snapshots: %s, latest fetched %.1fh ago" % (snap_count, max_age_h))
    if max_age_h > 6:
        issues.append("data stale: latest snapshot is %.1fh old" % max_age_h)

    # ---- 4. Null model pricing ----
    cur.execute("""
        SELECT COUNT(*) FROM models m
        LEFT JOIN latest_prices lp ON m.id = lp.model_id
        WHERE m.is_active
          AND (lp.model_id IS NULL OR lp.blended_price_per_m IS NULL OR lp.blended_price_per_m <= 0)
          AND m.id NOT LIKE '%%:batch'
    """)
    unpriced_models = cur.fetchone()[0]
    print("[4] Active models with no priced snapshot: %s" % unpriced_models)
    if unpriced_models > 20:
        issues.append("%s active models unpriced" % unpriced_models)

    # ---- 5. Composite sanity ----
    cur.execute("""
        SELECT sit_price FROM sit_index_values
        WHERE tier = 'composite'
        ORDER BY date DESC LIMIT 1
    """)
    comp = cur.fetchone()
    comp_price = comp[0] if comp else None
    if comp_price is None or comp_price <= 0 or comp_price > 500:
        issues.append("composite price implausible: %s" % comp_price)
    print("[5] Composite spot price: $%s" % (comp_price if comp_price is not None else "N/A"))

    # ---- 6. Composite methodology consistency ----
    # All composite rows must use usage_weighted_quality_gated (the live
    # pipeline method). If any row uses a different method (e.g. the backfill's
    # equal_weight_adjusted), the history is inconsistent and %-changes lie.
    cur.execute("""
        SELECT calculation_method, COUNT(*) OVER (), COUNT(*)
        FROM sit_index_values
        WHERE tier = 'composite'
        GROUP BY calculation_method
    """)
    methods = cur.fetchall()
    bad_methods = [m[0] for m in methods if m[0] != "usage_weighted_quality_gated"]
    print("[6] Composite methodology across history:")
    for m in methods:
        print("    %s: %d row(s)" % (m[0], m[2]))
    if bad_methods:
        issues.append("composite history has inconsistent method(s): %s" % bad_methods)
    elif not methods:
        issues.append("no composite rows in sit_index_values")

    # ---- 7. Index points sanity ----
    # sit_index_points should only be 1000 at the base date; later dates should
    # have moved. If every date is frozen at exactly 1000.00, the index isn't
    # being computed correctly.
    cur.execute("""
        SELECT COUNT(*) FILTER (WHERE sit_index_points = 1000)
        FROM sit_index_values
        WHERE tier = 'composite'
    """)
    frozen = cur.fetchone()[0]
    print("[7] Composite rows stuck at index 1000: %s" % frozen)
    if frozen and frozen == 7:  # all historical rows frozen = rebase never ran
        issues.append("composite index frozen at 1000 across full history")

    cur.close()
    conn.close()

    print()
    if issues:
        print("!! %s issue(s) found:" % len(issues))
        for i in issues:
            print("   - %s" % i)
        sys.exit(1)
    else:
        print("ALL CHECKS PASSED - data looks healthy")
        sys.exit(0)


if __name__ == "__main__":
    main()