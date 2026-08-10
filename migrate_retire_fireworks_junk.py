#!/usr/bin/env python3
"""
Migration: retire the junk Fireworks-provider model rows and their orphaned
`fireworks_direct` endpoints, after the scraper now writes to canonical IDs.

The previous fireworks_pricing.py used Fireworks' native API IDs
(accounts/fireworks/models/...) as model IDs, creating 20 junk model rows
(provider='Fireworks') with poor names, and 17 `fireworks_direct` endpoints
referencing them. The fixed scraper writes to canonical model IDs instead
(moonshotai/kimi-k3, z-ai/glm-5.2, etc.), so these native-ID rows are now
obsolete and must be retired.

This script runs in a transaction and can be dry-run via --dry-run.
"""
import os
import sys
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
    ap.add_argument("--dry-run", action="store_true", help="Show what would change without applying")
    args = ap.parse_args()

    env = get_env()
    conn = psycopg2.connect(env["SUPABASE_DB_URL"])
    cur = conn.cursor()

    # The junk rows: models where provider = 'Fireworks' (native IDs).
    # The 3 legit Fireworks-specific catalog models (qwen3-reranker-8b,
    # qwen3-embedding-8b, inkling) are excluded -- those stay as native.
    keep = [
        "accounts/fireworks/models/qwen3-reranker-8b",
        "accounts/fireworks/models/qwen3-embedding-8b",
        "accounts/fireworks/models/inkling",
    ]

    cur.execute("SELECT id FROM models WHERE provider = 'Fireworks' ORDER BY id")
    all_fw = [r[0] for r in cur.fetchall()]
    junk = [i for i in all_fw if i not in keep]

    print(f"Fireworks-provider rows: {len(all_fw)} | to retire: {len(junk)} | keep native: {len(keep)}")
    for i in sorted(all_fw):
        marker = "RETAIN (native)" if i in keep else "retire"
        print(f"  [{marker:15}] {i}")

    # Find orphaned fireworks_direct endpoints on those junk ids
    cur.execute(
        "SELECT COUNT(*) FROM model_endpoints WHERE model_id = ANY(%s)",
        (junk,),
    )
    ep_count = cur.fetchone()[0] if junk else 0
    print(f"model_endpoints on junk ids (fireworks_direct or otherwise): {ep_count}")

    # Any other refs
    cur.execute(
        "SELECT COUNT(*) FROM price_snapshots WHERE model_id = ANY(%s)",
        (junk,),
    )
    ps_count = cur.fetchone()[0] if junk else 0
    print(f"price_snapshots on junk ids: {ps_count}")

    if args.dry_run:
        print("\nDRY RUN - no changes applied.")
        conn.close()
        return

    if not junk:
        print("Nothing to retire.")
        conn.close()
        return

    conn.rollback()  # discard read txn
    cur = conn.cursor()
    try:
        # Delete orphaned endpoints first (FK-safe)
        if ep_count:
            cur.execute(
                "DELETE FROM model_endpoints WHERE model_id = ANY(%s)",
                (junk,),
            )
            print(f"Deleted {ep_count} model_endpoints on junk ids")
        if ps_count:
            cur.execute(
                "DELETE FROM price_snapshots WHERE model_id = ANY(%s)",
                (junk,),
            )
            print(f"Deleted {ps_count} price_snapshots on junk ids")
        # Retire the junk model rows (soft delete via is_active=FALSE)
        cur.execute(
            "UPDATE models SET is_active = FALSE WHERE id = ANY(%s)",
            (junk,),
        )
        print(f"Retired {len(junk)} junk Fireworks model rows (is_active=FALSE)")

        conn.commit()
        print("Migration committed.")
    except Exception as e:
        conn.rollback()
        print(f"Migration FAILED, rolled back: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()