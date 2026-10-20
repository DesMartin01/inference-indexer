#!/usr/bin/env python3
"""
Migration: retire bare-id (provider-less) shadow model rows.

Class: a bare id with no '/' (e.g. 'deepseek-v4.1-flash-1017') is a shadow
row created by direct connectors that skipped their canonical-ID map (Oct
2026: engy_direct). Each bare row has an active prefixed twin carrying the
real multi-source median price; the bare row reports a fake single-source
price and leaks into sitemap.xml (its site page 404s behind the proxy's
provider-slug guard).

Playbook (same three steps as the case/dot-hyphen migrations):
  1. Move the bare row's model_endpoints onto the canonical twin
     (deduped on endpoint_provider + input/output price).
  2. Repoint model_aliases rows resolving to the bare id onto the twin.
  3. Retire the bare row (is_active = FALSE; never delete).

Scope decisions (Des, Oct 19 2026 "Go"):
  - KEEP ming-image-0.1-design / -layer (real Novita image models, no twin).
  - RETIRE 'auto' (Fireworks catalog junk, Oct 3, zero endpoints/snapshots,
    not in latest_prices so invisible to lists/sitemap).
The canonical twin per bare id comes from CANONICAL_OVERRIDES; anything not
listed falls back to the highest-source-count prefixed twin (printed in
dry-run for review before --apply).
Runs in a transaction. --apply to write (default: dry-run).
"""
import argparse
import psycopg2


def get_env():
    env = {}
    for line in open("/home/ubuntu/.hermes/.env"):
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k] = v
    return env


# Explicit twin decisions reviewed against latest_prices (Oct 19 2026).
CANONICAL_OVERRIDES = {
    "deepseek-v4.1-flash": "deepseek/deepseek-v4.1-flash",
    "deepseek-v4.1-flash-1017": "deepseek/deepseek-v4.1-flash-1017",
    "glm-5.3": "z-ai/glm-5.3",
    "glm-5.3-flash": "z-ai/glm-5.3-flash",
    "qwen3.8-27b": "qwen/qwen3.8-27b",
    "minimax-h3": None,  # junk: zero endpoints, absurd $18000/M snapshot; retire, move nothing
    # 'auto': retire-only - Fireworks catalog junk (Oct 3), zero endpoints/snapshots,
    #   not in latest_prices so it never appeared in lists/sitemap. No twin.
    "auto": None,
}
# KEEP: real models that legitimately lack a provider prefix in our scheme
# (ming-image-* are genuine Novita image models, no prefixed twin exists).
# NB 'auto' (Fireworks ROUTER pseudo-model) resurrected once via upsert_venice_models
# before the fireworks connector learned to skip kind=ROUTER (deployed Oct 20);
# the bare-id defense in upsert_venice_models now blocks resurrection too.
KEEP_BARE = {"ming-image-0.1-design", "ming-image-0.1-design-layer"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="Apply (default: dry-run)")
    args = ap.parse_args()
    conn = psycopg2.connect(get_env()["SUPABASE_DB_URL"], connect_timeout=10)
    cur = conn.cursor()

    cur.execute("""
        SELECT m.id FROM models m
        WHERE m.is_active = TRUE AND m.id NOT LIKE '%/%'
    """)
    bare_rows = [r[0] for r in cur.fetchall()]
    print(f"Found {len(bare_rows)} active bare-id rows: {bare_rows}")

    targets = {}
    for b in bare_rows:
        if b in KEEP_BARE:
            print(f"  {b}  KEEP (explicit: real model, not a shadow)")
            continue
        if b in CANONICAL_OVERRIDES:
            targets[b] = CANONICAL_OVERRIDES[b]
        else:
            # unknown bare id: conservative default is SKIP, not guess-print
            print(f"  {b}  UNKNOWN bare id, not in overrides - SKIPPED (add to CANONICAL_OVERRIDES)")
            continue
    print(f"\nTargets: {targets}")

    total_ep = 0
    for b, t in targets.items():
        cur.execute("SELECT count(*) FROM model_endpoints WHERE model_id = %s", (b,))
        n_ep = cur.fetchone()[0]
        total_ep += n_ep
        action = f"-> {t} (endpoints to move: {n_ep})" if t else "RETIRE ONLY (no endpoints)"
        print(f"  {b}  {action}")
        if t:
            cur.execute("SELECT 1 FROM models WHERE id = %s AND is_active", (t,))
            if not cur.fetchone():
                print(f"    ERROR: twin {t} not active, skipping")
                targets[b] = None

    if not args.apply:
        print("\nDRY RUN - no changes applied. Re-run with --apply.")
        conn.close()
        return

    conn.rollback()
    cur = conn.cursor()
    try:
        for b, t in targets.items():
            if t:
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
                      )
                """, (t, b, t))
                cur.execute("""
                    UPDATE model_aliases SET canonical_model_id = %s
                    WHERE canonical_model_id = %s
                """, (t, b))
                # alias rows whose ALIAS is the bare id but pointed elsewhere stay put;
                # alias rows pointing AT the bare row now point at the twin.
            cur.execute("UPDATE models SET is_active = FALSE WHERE id = %s", (b,))
            print(f"  consolidated {b} -> {t or '(retired, no twin)'}")
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
