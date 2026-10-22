#!/usr/bin/env python3
"""x-ai consolidation reversal (2026-10-22).

The Oct-21 consolidation made xai/ canonical for five Grok models, but
OpenRouter itself emits x-ai/* for every current Grok model. A feed that
disagrees with its own consolidation re-creates duplicates every hourly run.
So the canonical prefix goes back to x-ai/ (the OR-emitted prefix), matching
the zai-org -> z-ai convention: canonical = the prefix the primary feed uses.

Renames the five xai/* model rows onto the pre-existing (retired, inactive)
x-ai/* rows: endpoints, price_snapshots, aliases, then reactivates.

Canonical = x-ai/*. The web 308 must therefore point xai -> x-ai (not the
reverse), and ORG_CANONICAL in pipeline.py maps xai -> x-ai.

Dry-run by default, --apply to execute.
"""
import os
import argparse
import psycopg2

RENAMES = [
    # (dup, keep) : merge dup onto the existing inactive keep row
    ("xai/grok-4.20", "x-ai/grok-4.20"),
    ("xai/grok-4.20-multi-agent", "x-ai/grok-4.20-multi-agent"),
    ("xai/grok-4.3", "x-ai/grok-4.3"),
    ("xai/grok-4.5", "x-ai/grok-4.5"),
    ("xai/grok-build-0.1", "x-ai/grok-build-0.1"),
]


def get_env():
    for line in open(os.path.expanduser("~/.hermes/.env")):
        if line.startswith("SUPABASE_DB_URL"):
            return {"SUPABASE_DB_URL": line.split("=", 1)[1].strip().strip('"')}
    raise SystemExit("SUPABASE_DB_URL not found")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    conn = psycopg2.connect(get_env()["SUPABASE_DB_URL"])
    cur = conn.cursor()

    ok = True
    for dup, keep in RENAMES:
        cur.execute("SELECT is_active FROM models WHERE id = %s", (dup,))
        d = cur.fetchone()
        cur.execute("SELECT is_active FROM models WHERE id = %s", (keep,))
        k = cur.fetchone()
        if not d or not k:
            print(f"MISSING: {dup} d={bool(d)} keep={bool(k)}")
            ok = False
        elif d[0] is not True or k[0] is not False:
            print(f"UNEXPECTED STATE: {dup} active={d[0]} / {keep} active={k[0]} (expected active/inactive)")
            ok = False
        else:
            print(f"OK: {dup} (active) -> merge into {keep} (inactive)")
    if not ok:
        print("\nState differs from expectations; aborting. Inspect before applying.")
        conn.close()
        return

    if not args.apply:
        print("\nDRY RUN - re-run with --apply to execute.")
        conn.close()
        return

    conn.rollback()  # discard read txn
    cur = conn.cursor()
    try:
        for dup, keep in RENAMES:
            # 1. Endpoints: move dup rows onto keep where keep has no
            # identical (provider, prices, fetched_at) row already
            cur.execute("""
                INSERT INTO model_endpoints
                    (model_id, endpoint_provider, input_price_per_m, output_price_per_m,
                     blended_price_per_m, context_length, source, raw_data, fetched_at)
                SELECT %s, me.endpoint_provider, me.input_price_per_m, me.output_price_per_m,
                       me.blended_price_per_m, me.context_length, me.source, me.raw_data, me.fetched_at
                FROM model_endpoints me
                WHERE me.model_id = %s
                  AND NOT EXISTS (
                      SELECT 1 FROM model_endpoints c
                      WHERE c.model_id = %s
                        AND c.endpoint_provider = me.endpoint_provider
                        AND c.input_price_per_m = me.input_price_per_m
                        AND c.output_price_per_m = me.output_price_per_m
                        AND c.fetched_at = me.fetched_at
                  )
            """, (keep, dup, keep))
            n_ep = cur.rowcount

            # 2. Price snapshots: same dedup rule (provider row identity here
            # is source + prices + fetched_at)
            cur.execute("""
                INSERT INTO price_snapshots
                    (model_id, source, input_price_per_m, output_price_per_m,
                     blended_price_per_m, sit_score, raw_data, fetched_at,
                     is_anomalous, reviewed_at)
                SELECT %s, ps.source, ps.input_price_per_m, ps.output_price_per_m,
                       ps.blended_price_per_m, ps.sit_score, ps.raw_data, ps.fetched_at,
                       ps.is_anomalous, ps.reviewed_at
                FROM price_snapshots ps
                WHERE ps.model_id = %s
                  AND NOT EXISTS (
                      SELECT 1 FROM price_snapshots c
                      WHERE c.model_id = %s
                        AND c.source = ps.source
                        AND c.input_price_per_m = ps.input_price_per_m
                        AND c.output_price_per_m = ps.output_price_per_m
                        AND c.fetched_at = ps.fetched_at
                  )
            """, (keep, dup, keep))
            n_ps = cur.rowcount

            # 3. Repoint aliases at the keep row; alias dup itself resolves to
            # keep so old xai/* URLs/ids resolve going forward
            cur.execute(
                "UPDATE model_aliases SET canonical_model_id = %s WHERE canonical_model_id = %s",
                (keep, dup),
            )
            cur.execute("""
                INSERT INTO model_aliases (alias, canonical_model_id, source)
                VALUES (%s, %s, 'consolidation')
                ON CONFLICT (alias) DO UPDATE SET canonical_model_id = EXCLUDED.canonical_model_id
            """, (dup, keep))

            # 4. Retire the dup
            cur.execute("UPDATE models SET is_active = FALSE WHERE id = %s", (dup,))
            # 5. Reactivate the keep row
            cur.execute("UPDATE models SET is_active = TRUE WHERE id = %s", (keep,))

            print(f"  {dup} -> {keep}: endpoints={n_ep}, snapshots={n_ps}, alias upserted, keep reactivated")

        # 6. Refresh latest_prices matview so headline reads see the merged
        # rows. CONCURRENTLY requires autocommit, so COMMIT the data txn
        # FIRST (a rollback here discards the entire migration, hit
        # 2026-10-22 on first apply), then flip to autocommit with an
        # extended statement timeout.
        conn.commit()
        conn.autocommit = True
        rcur = conn.cursor()
        rcur.execute("SET statement_timeout = 300000")
        rcur.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY latest_prices")
        rcur.close()
        print("\nCommitted; latest_prices refreshed concurrently.")
    except Exception as e:
        conn.rollback()
        print(f"FAILED, rolled back: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
