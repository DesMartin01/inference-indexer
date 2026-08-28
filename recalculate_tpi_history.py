#!/usr/bin/env python3
"""
One-time script: Recalculate SIT-Composite index values using the new TPI method
for all dates from first data (2026-08-04) to today.

Old method: usage_weighted_quality_gated
New method: tpi_equal_weight_provider_capped

Does NOT delete old rows. Inserts/updates rows with the new method name.
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


def get_db():
    return psycopg2.connect(DB_URL, connect_timeout=10)


def calculate_tpi_for_date(conn, target_date):
    """Calculate TPI for a specific date using the last snapshot of each model on that date."""
    cur = conn.cursor()

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
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no DB writes")
    args = parser.parse_args()

    conn = get_db()

    # Get date range
    cur = conn.cursor()
    cur.execute("SELECT MIN(fetched_at::date), MAX(fetched_at::date) FROM price_snapshots")
    first_date, last_date = cur.fetchone()
    cur.close()

    print(f"Recalculating TPI from {first_date} to {last_date}")

    # Calculate TPI for base date (first date with data)
    base_tpi = calculate_tpi_for_date(conn, first_date)
    if not base_tpi:
        print("ERROR: Could not calculate base TPI. Aborting.")
        sys.exit(1)

    base_price = base_tpi["price"]
    print(f"Base TPI ({first_date}): ${base_price} ({base_tpi['provider_count']} providers)")

    # Compare with old composite for same date
    cur = conn.cursor()
    cur.execute("""
        SELECT sit_price, sit_index_points FROM sit_index_values
        WHERE tier = 'composite' AND date = %s
    """, (first_date,))
    old = cur.fetchone()
    cur.close()
    if old:
        print(f"  Old composite for same date: ${old[0]} (index {old[1]})")
        if old[0] and old[0] > 0:
            pct = ((base_price - old[0]) / old[0]) * 100
            print(f"  TPI vs old: {pct:+.1f}%")

    # Iterate through all dates
    current = first_date
    count = 0
    errors = 0
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
            print(f"  {current}: No qualifying data, skipping")
            errors += 1

        current += timedelta(days=1)

    print(f"\n{'Would insert' if args.dry_run else 'Inserted/updated'} {count} TPI values ({errors} dates skipped)")
    conn.close()


if __name__ == "__main__":
    main()
