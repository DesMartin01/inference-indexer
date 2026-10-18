#!/usr/bin/env python3
"""
Migration: consolidate dot/hyphen model-ID duplicates onto the dotted canonical row.

Canonical IDs use OpenRouter's dotted version style (claude-haiku-4.5). DeepInfra's
catalog emits hyphenated IDs (claude-haiku-4-5); canonical_model_id() lowercases
but does not unify the separator, so upsert_venice_models() created twin rows.

For every active hyphen twin with an active dotted twin (same id after
replace('.', '-')):
  1. Move its model_endpoints onto the dotted row (deduped on
     endpoint_provider + input/output price, proven pattern from the Sep 2026
     case-dup migration).
  2. Repoint model_aliases rows that resolve to the hyphen row onto the dotted row.
  3. Retire the hyphen row (is_active = FALSE; never delete).

Direction rule: the DOTTED variant survives (matches OpenRouter canonical style,
higher source_count in every observed pair).

Runs in a transaction. --dry-run to preview (default: dry-run).
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
    ap.add_argument("--apply", action="store_true", help="Apply (default: dry-run)")
    args = ap.parse_args()
    env = get_env()
    conn = psycopg2.connect(env["SUPABASE_DB_URL"])
    cur = conn.cursor()

    cur.execute("""
        SELECT h.id
        FROM models h JOIN models d
          ON h.provider = d.provider
         AND replace(h.id, chr(46), chr(45)) = replace(d.id, chr(46), chr(45))
         AND h.id <> d.id
         AND h.id LIKE '%%-%%'
         AND d.id LIKE '%%.%%'
         AND h.is_active = TRUE AND d.is_active = TRUE
        ORDER BY h.id
    """)
    hyphen_rows = [r[0] for r in cur.fetchall()]
    print(f"Found {len(hyphen_rows)} hyphen twins with a dotted twin.")

    targets = {}
    for h in hyphen_rows:
        cur.execute("""
            SELECT d.id FROM models d
            WHERE d.provider = (SELECT provider FROM models WHERE id = %s)
              AND replace(d.id, chr(46), chr(45)) = replace(%s, chr(46), chr(45))
              AND d.id <> %s AND d.is_active = TRUE
        """, (h, h, h))
        row = cur.fetchone()
        targets[h] = row[0] if row else None

    total_ep = 0
    for h, d in targets.items():
        if not d:
            print(f"  {h}: NO dotted twin found, skipping")
            continue
        cur.execute("SELECT count(*) FROM model_endpoints WHERE model_id = %s", (h,))
        n_ep = cur.fetchone()[0]
        total_ep += n_ep
        print(f"  {h}  ->  {d}   (endpoints to move: {n_ep})")

    if not args.apply:
        print("\nDRY RUN - no changes applied. Re-run with --apply.")
        conn.close()
        return

    conn.rollback()  # discard read txn
    cur = conn.cursor()
    try:
        for h, d in targets.items():
            if not d:
                continue
            # 1. Move endpoints onto the dotted row (deduped)
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
            """, (d, h, d))

            # 2. Repoint alias rows that resolve to the hyphen row
            cur.execute("""
                UPDATE model_aliases SET canonical_model_id = %s
                WHERE canonical_model_id = %s
            """, (d, h))

            # 3. Retire the hyphen row
            cur.execute("UPDATE models SET is_active = FALSE WHERE id = %s", (h,))
            print(f"  consolidated {h} -> {d}")

        conn.commit()
        print(f"\nMigration committed. {total_ep} endpoint rows moved.")
    except Exception as e:
        conn.rollback()
        print(f"\nMigration FAILED, rolled back: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
