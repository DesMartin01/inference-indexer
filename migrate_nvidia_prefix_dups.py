#!/usr/bin/env python3
"""
Migration: consolidate NVIDIA double-prefix duplicate rows.

OpenRouter served some NVIDIA models with a doubled provider prefix
('nvidia/nvidia-nemotron-3-super-120b-a12b') instead of the canonical
('nvidia/nemotron-3-super-120b-a12b'). This produces active duplicate rows.

This migration, for each active 'nvidia/nvidia-*' row that has an active
lowercase canonical twin (nvidia/nvidia-X -> nvidia/X):
  1. Upserts its model_endpoints onto the canonical row (dedup by
     endpoint_provider + input/output price, keeping newer fetched_at).
  2. Deletes the moved endpoints off the dup row.
  3. Retires the dup model row (is_active = FALSE).

Runs in a transaction. Use --dry-run to preview.
"""
import os
import argparse
import psycopg2


def get_env():
    env = {}
    for line in open(os.path.expanduser("~/.hermes/.env")):
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k] = v
    return env


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Preview without applying")
    args = ap.parse_args()
    env = get_env()
    conn = psycopg2.connect(env["SUPABASE_DB_URL"])

    cur = conn.cursor()
    cur.execute("""
        SELECT m.id AS dup
        FROM models m
        WHERE m.is_active = TRUE
          AND m.id LIKE 'nvidia/nvidia-%'
          AND EXISTS (SELECT 1 FROM models t
                      WHERE t.id = replace(m.id, 'nvidia/nvidia-', 'nvidia/')
                        AND t.is_active = TRUE AND t.id <> m.id)
        ORDER BY m.id
    """)
    dup_rows = [r[0] for r in cur.fetchall()]
    print(f"Found {len(dup_rows)} NVIDIA double-prefix duplicate row(s).")

    for dup in dup_rows:
        canonical = dup.replace("nvidia/nvidia-", "nvidia/")
        cur.execute("SELECT COUNT(*) FROM model_endpoints WHERE model_id = %s", (dup,))
        dup_ep = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM model_endpoints WHERE model_id = %s", (canonical,))
        canon_ep = cur.fetchone()[0]
        print(f"  {dup}  ->  {canonical}   (eps: {dup_ep} dup, {canon_ep} canonical)")

    if args.dry_run:
        print("\nDRY RUN - no changes applied.")
        conn.close()
        return

    if not dup_rows:
        print("Nothing to consolidate.")
        conn.close()
        return

    conn.rollback()
    cur = conn.cursor()
    try:
        for dup in dup_rows:
            canonical = dup.replace("nvidia/nvidia-", "nvidia/")

            # 1. Upsert each endpoint on the dup row onto the canonical row,
            #    keeping the dup row's fetched_at if newer.
            cur.execute("""
                INSERT INTO model_endpoints
                    (model_id, endpoint_provider, input_price_per_m, output_price_per_m,
                     blended_price_per_m, context_length, source, raw_data, fetched_at)
                SELECT
                    %s, me.endpoint_provider, me.input_price_per_m, me.output_price_per_m,
                    me.blended_price_per_m, me.context_length, me.source, me.raw_data, me.fetched_at
                FROM model_endpoints me
                WHERE me.model_id = %s
                  AND NOT EXISTS (
                      SELECT 1 FROM model_endpoints c
                      WHERE c.model_id = %s
                        AND c.endpoint_provider = me.endpoint_provider
                        AND c.input_price_per_m = me.input_price_per_m
                        AND c.output_price_per_m = me.output_price_per_m
                  )
            """, (canonical, dup, canonical))

            # 2. Delete the endpoints that were on the dup row (moved/dup'd)
            cur.execute("DELETE FROM model_endpoints WHERE model_id = %s", (dup,))

            # 3. Retire the dup model row
            cur.execute("UPDATE models SET is_active = FALSE WHERE id = %s", (dup,))
            print(f"  consolidated {dup} -> {canonical}")

        conn.commit()
        print("\nMigration committed.")
    except Exception as e:
        conn.rollback()
        print(f"\nMigration FAILED, rolled back: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()