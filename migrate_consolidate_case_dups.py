#!/usr/bin/env python3
"""
Migration: consolidate mixed-case model rows into their lowercase canonical twin.

Our canonical model-ID scheme is lowercase `provider/model`
(moonshotai/kimi-k3, z-ai/glm-5.2). Some direct connectors (DeepInfra, Novita,
Jina, Groq, etc.) create rows using OpenRouter's mixed-case IDs
(moonshotai/Kimi-K3, zai-org/GLM-5.2), producing case-duplicate rows for the
same logical model.

This migration for every active mixed-case row that has a lowercase twin:
  1. Upserts its model_endpoints onto the lowercase canonical row (deduping by
     endpoint_provider + input/output price so we preserve per-source pricing
     without creating exact duplicates).
  2. Retires the mixed-case model row (is_active=FALSE).

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
        SELECT m.id AS mixed
        FROM models m
        WHERE m.id ~ '[A-Z]' AND m.is_active = TRUE AND m.id NOT LIKE '%%:batch'
          AND EXISTS (SELECT 1 FROM models t
                      WHERE t.id = lower(m.id) AND t.is_active = TRUE AND t.id <> m.id)
        ORDER BY m.id
    """)
    dup_rows = [r[0] for r in cur.fetchall()]
    print(f"Found {len(dup_rows)} mixed-case duplicate rows with a lowercase twin.")

    total_ep_moved = 0
    total_ep_skipped = 0
    for mixed in dup_rows:
        canonical = mixed.lower()
        # Count endpoints on the mixed row, and how many would be moved vs skipped
        cur.execute(
            "SELECT COUNT(*) FROM model_endpoints WHERE model_id = %s", (mixed,)
        )
        mixed_ep = cur.fetchone()[0]
        # Count endpoints on the canonical row already
        cur.execute(
            "SELECT COUNT(*) FROM model_endpoints WHERE model_id = %s", (canonical,)
        )
        canon_ep = cur.fetchone()[0]
        print(f"  {mixed}  ->  {canonical}   (eps: {mixed_ep} mixed, {canon_ep} canonical)")
        total_ep_moved += mixed_ep

    if args.dry_run:
        print("\nDRY RUN - no changes applied.")
        conn.close()
        return

    if not dup_rows:
        print("Nothing to consolidate.")
        conn.close()
        return

    conn.rollback()  # discard read txn
    cur = conn.cursor()
    try:
        for mixed in dup_rows:
            canonical = mixed.lower()

            # 1. Upsert each endpoint on the mixed row onto the canonical row,
            #    keeping the mixed row's fetched_at/created_at if newer.
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
            """, (canonical, mixed, canonical))

            # 2. Delete the endpoints that were on the mixed row (now moved/dup'd)
            cur.execute("DELETE FROM model_endpoints WHERE model_id = %s", (mixed,))

            # 3. Retire the mixed-case model row
            cur.execute("UPDATE models SET is_active = FALSE WHERE id = %s", (mixed,))
            print(f"  consolidated {mixed} -> {canonical}")

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