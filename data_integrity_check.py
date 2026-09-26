#!/usr/bin/env python3
"""
InferenceIndexer - Data-Integrity Check
=============================================
Queries the live DB and reports data-quality issues that would make the
product look unreliable to a customer's agent. Run DAILY (cron) as a
product QA gate. Since Sep 2026 it also detects AA Index rebases (fix 5).

Checks:
  1. Provider pricing coverage  - how many providers lack real avg/min/max price.
  2. TPI stability              - daily TPI should not move > 20%.
  3. Snapshot freshness         - snapshots older than N hours / stale data.
  4. Null model pricing         - how many active models have no priced snapshot.
  5. Composite sanity           - spot composite price is sane (positive, plausible).
  6. Composite methodology      - consistent calculation_method across history.
  7. Index points sanity        - TPI rows not frozen at 1000.
  8. AA rebase detector         - version flip or >5% median-score shift day-over-day.
  9. TPI basket churn           - providers entering/leaving the basket.
 10. Direct-source freshness    - scrapers returning zero endpoints (silent regex break).

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
    valid_methods = {"tpi_equal_weight_provider_capped", "usage_weighted_quality_gated",
                     "tpi_equal_weight_provider_capped_gate35"}  # archived pre-backfill series (Sep 2026)
    bad_methods = [m[0] for m in methods if m[0] not in valid_methods]
    print("[6] Composite methodology across history:")
    for m in methods:
        print("    %s: %d row(s)" % (m[0], m[2]))
    if bad_methods:
        issues.append("composite history has inconsistent method(s): %s" % bad_methods)
    elif not methods:
        issues.append("no composite rows in sit_index_values")

    # ---- 7. Index points sanity ----
    # Check only new-method rows (tpi_equal_weight_provider_capped)
    cur.execute("""
        SELECT COUNT(*) FILTER (WHERE sit_index_points = 1000)
        FROM sit_index_values
        WHERE tier = 'composite'
          AND calculation_method = 'tpi_equal_weight_provider_capped'
    """)
    frozen = cur.fetchone()[0]
    print("[7] TPI rows stuck at index 1000: %s" % frozen)
    if frozen and frozen > 1:  # >1 row at 1000 = rebase never ran properly
        issues.append("TPI index frozen at 1000 across %d rows" % frozen)

    # ---- 8. AA median-score shift (rebase detector, Sep 2026) ----
    # AA rebases its Index without notice (v4.2 Sep 4, v4.3 Sep 7, 2026).
    # A median shift >5% day-over-day means scores are no longer comparable
    # to yesterday: tiers/indices derived from absolute thresholds break.
    cur.execute("""
        SELECT date, aa_version, models_scored, median_score
        FROM aa_daily_ingest
        ORDER BY date DESC LIMIT 3
    """)
    ing = cur.fetchall()
    print("[8] AA ingest stats (rebase detector)")
    for r in ing:
        print("    %s: v=%s scored=%s median=%s" % (r[0], r[1], r[2],
              round(float(r[3]), 2) if r[3] is not None else None))
    if len(ing) >= 2:
        today_row, prev_row = ing[0], ing[1]
        # version flip = definite rebase
        if today_row[1] and prev_row[1] and today_row[1] != prev_row[1]:
            issues.append("AA version changed %s -> %s on %s (rebase: scores not comparable)" % (
                prev_row[1], today_row[1], today_row[0]))
        # median shift catches unannounced score changes within a version too
        if today_row[3] and prev_row[3] and float(prev_row[3]) > 0:
            shift = (float(today_row[3]) - float(prev_row[3])) / float(prev_row[3])
            if abs(shift) > 0.05:
                issues.append("AA median score moved %+.1f%% day-over-day (possible rebase or scoring change)" % (shift * 100))

    # ---- 9. TPI basket churn (eligibility stability, Sep 2026) ----
    # Providers entering/leaving the TPI basket move the headline index even
    # when no real price changed. Store the basket per row (basket_providers)
    # and flag any churn between the last two days.
    cur.execute("""
        SELECT date, basket_providers
        FROM sit_index_values
        WHERE tier = 'composite'
          AND calculation_method = 'tpi_equal_weight_provider_capped'
          AND basket_providers IS NOT NULL
        ORDER BY date DESC LIMIT 2
    """)
    baskets = cur.fetchall()
    print("[9] TPI basket churn")
    if len(baskets) >= 2 and baskets[0][1] and baskets[1][1]:
        now_set = set(baskets[0][1])
        prev_set = set(baskets[1][1])
        left = sorted(prev_set - now_set)
        joined = sorted(now_set - prev_set)
        print("    %s: %d providers" % (baskets[0][0], len(now_set)))
        print("    %s: %d providers" % (baskets[1][0], len(prev_set)))
        if left or joined:
            print("    left: %s | joined: %s" % (left, joined))
            issues.append("TPI basket churn on %s: left=%s joined=%s (index moved without prices moving)" % (
                baskets[0][0], left, joined))
        else:
            print("    no churn")
    else:
        print("    insufficient basket history (rows must carry basket_providers)")

    # ---- 10. Direct-source freshness (zero-endpoint detector, Sep 2026) ----
    # Scrapers (direct_scrapers.py etc.) write endpoints with a `source` tag.
    # If a page layout changes, the regex matches nothing, zero rows are
    # inserted, and the run "succeeds" silently. Detect by checking that each
    # expected source has inserted at least one endpoint in the last 26 hours
    # (hourly cron + 2h slack). Thresholds are per-source minimums, not zero:
    # a source whose true yield is small still needs a floor above 0.
    DIRECT_SOURCE_FLOORS = {
        "alibaba_direct": 20,
        "zai_direct": 5,
        "moonshot_direct": 2,
        "openrelay_direct": 1,
        "sarvam_direct": 1,
        "tensorx_direct": 5,
        "engy_direct": 1,
    }
    cur.execute("""
        SELECT source, COUNT(DISTINCT model_id) AS n_models
        FROM model_endpoints
        WHERE fetched_at >= NOW() - INTERVAL '26 hours'
          AND source = ANY(%s)
        GROUP BY source
    """, (list(DIRECT_SOURCE_FLOORS.keys()),))
    counts = {row[0]: row[1] for row in cur.fetchall()}
    print("[10] Direct-source endpoint freshness (last 26h)")
    for src, floor in sorted(DIRECT_SOURCE_FLOORS.items()):
        n = counts.get(src, 0)
        status = "OK" if n >= floor else "STALE/BROKEN"
        print("    %-18s %3d models (floor %d) %s" % (src, n, floor, status))
        if n < floor:
            issues.append(
                "direct source '%s' yielded %d models in last 26h (floor %d) - "
                "scraper may be silently broken (regex/layout change)" % (src, n, floor))
    unexpected = sorted(set(counts) - set(DIRECT_SOURCE_FLOORS))
    if unexpected:
        print("    (other sources seen, no floor set: %s)" % ", ".join(unexpected))

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