#!/usr/bin/env python3
"""
One-time script: Rebase the TPI index series at 2026-09-04 = 1000.

Why: AA shipped Intelligence Index v4.2 (Sep 4) and v4.3 (Sep 7) in one week.
The absolute AA>=35 eligibility gate shed providers from the TPI basket
(17 -> 9) and the headline tripled while real prices were flat or falling.
The old series (anchored Aug 4 = 1000) is meaningless across that boundary.

This script:
  1. Rescales sit_index_points for tpi_equal_weight_provider_capped composite
     rows so the 2026-09-04 row = 1000.
  2. Tags every composite row with rebase_group + aa_version:
       date <  2026-09-05 -> v4.1
       2026-09-05..06     -> v4.2
       date >= 2026-09-07 -> v4.3
  3. Leaves old-method (v0.1) rows untouched.

Does NOT delete anything. Idempotent (re-running produces the same values).

Usage:
    .venv/bin/python3 rebase_tpi_sep2026.py            # Full run
    .venv/bin/python3 rebase_tpi_sep2026.py --dry-run  # Preview only
"""
import os, argparse
from dotenv import dotenv_values
import psycopg2

vals = dotenv_values(os.path.expanduser("~/.hermes/.env"))
DB_URL = vals["SUPABASE_DB_URL"]

REBASE_DATE = "2026-09-04"
BASE_VALUE = 1000.0
METHOD = "tpi_equal_weight_provider_capped"

ERA_BOUNDARIES = [
    ("v4.1", None, "2026-09-04"),
    ("v4.2", "2026-09-05", "2026-09-06"),
    ("v4.3", "2026-09-07", None),
]


def era_for(d):
    for name, start, end in ERA_BOUNDARIES:
        if start and d < start:
            continue
        if end and d > end:
            continue
        return name
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    conn = psycopg2.connect(DB_URL, connect_timeout=10)
    conn.autocommit = False
    cur = conn.cursor()

    # Anchor: the Sep 4 composite row's index points
    cur.execute("""
        SELECT sit_index_points FROM sit_index_values
        WHERE tier='composite' AND calculation_method=%s AND date=%s
    """, (METHOD, REBASE_DATE))
    row = cur.fetchone()
    if not row:
        print(f"ERROR: no composite row for {REBASE_DATE}; cannot anchor rebasing.")
        cur.close(); conn.close()
        return 1
    anchor_points = float(row[0])
    factor = BASE_VALUE / anchor_points
    print(f"Anchor {REBASE_DATE}: index {anchor_points} -> 1000 (factor {factor:.6f})")

    # Fetch all composite rows under the current method
    cur.execute("""
        SELECT date, sit_index_points, sit_price, aa_version, rebase_group
        FROM sit_index_values
        WHERE tier='composite' AND calculation_method=%s
        ORDER BY date
    """, (METHOD,))
    rows = cur.fetchall()
    print(f"{len(rows)} composite rows to rebase\n")

    updates = []
    for d, pts, price, ver, grp in rows:
        d_iso = d.isoformat() if hasattr(d, "isoformat") else str(d)
        new_pts = round(float(pts) * factor, 2)
        era = era_for(d_iso)
        if args.dry_run:
            print(f"  {d_iso}: {pts} -> {new_pts}  (era {era}, was ver={ver} grp={grp})")
        else:
            cur.execute("""
                UPDATE sit_index_values
                SET sit_index_points=%s, aa_version=COALESCE(aa_version,%s),
                    rebase_group=%s
                WHERE tier='composite' AND calculation_method=%s AND date=%s
            """, (new_pts, era, era, METHOD, d))
    print()

    if args.dry_run:
        print(f"DRY RUN: would update {len(rows)} rows")
        cur.close(); conn.close()
        return 0

    conn.commit()
    print(f"Updated {len(rows)} composite rows (rebased to {REBASE_DATE} = 1000)")

    # Verify
    cur.execute("""
        SELECT date, sit_index_points, aa_version, rebase_group
        FROM sit_index_values
        WHERE tier='composite' AND calculation_method=%s
        ORDER BY date DESC LIMIT 6
    """, (METHOD,))
    print("\nverify (latest 6):")
    for r in cur.fetchall():
        print("  ", r)
    cur.close()
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
