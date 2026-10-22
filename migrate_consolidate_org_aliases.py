#!/usr/bin/env python3
"""B2: consolidate org-alias duplicate model IDs onto canonical rows.

Extends the dotted-dups migration pattern (2026-10-21). Two duplicate classes:

1. Org-alias duplicates: deepseek-ai/* vs deepseek/*, meta/* vs meta-llama/*,
   zai-org/* vs z-ai/*, minimaxai/* vs minimax/*, stepfun-ai/* vs stepfun/*,
   moonshot/* vs moonshotai/*, x-ai/* vs xai/*. Canonical org map below; the
   SURVIVING row is the one with more 24h endpoints (ties: the id OpenRouter
   itself uses, which the dotted-dups convention follows: shorter/canonical).

2. Dot/hyphen twins inside ONE org (openai/gpt-5-5 vs openai/gpt-5.5,
   bytedance-seed/seed-2-1-turbo, mistralai/mistral-medium-3-5): same rule as
   migrate_consolidate_dotted_dups (dotted wins), re-run here for the
   stragglers.

For every dup pair: move endpoints (deduped) to the canonical row, repoint
model_aliases, insert an alias row so old URLs resolve (page.tsx redirects
already exist for stepfun-ai/zai-org/minimaxai/x-ai prefixes), then retire
the duplicate (is_active=FALSE).

Dry-run by default. --apply to execute.
"""
import os
import re
import argparse
import psycopg2
from collections import defaultdict

ORG_ALIAS = {
    'deepseek-ai': 'deepseek',
    'meta': 'meta-llama',
    'zai-org': 'z-ai',
    'minimaxai': 'minimax',
    'stepfun-ai': 'stepfun',
    'moonshot': 'moonshotai',
    # x-ai REMOVED 2026-10-22: OpenRouter emits x-ai/*, so x-ai is canonical;
    # the Oct-21 x-ai->xai consolidation was reversed (migrate_xai_rename.py).
}

def get_env():
    for line in open(os.path.expanduser('~/.hermes/.env')):
        if line.startswith('SUPABASE_DB_URL'):
            return {'SUPABASE_DB_URL': line.split('=',1)[1].strip().strip('"')}
    raise SystemExit('SUPABASE_DB_URL not found')

def norm_model_part(mid: str) -> str:
    org, _, rest = mid.partition('/')
    return re.sub(r'[._]+', '-', rest.lower())

def canon(mid: str) -> str:
    org, _, rest = mid.partition('/')
    return ORG_ALIAS.get(org, org) + '/' + rest

def style_score(rest: str) -> int:
    """Canonical id style: dotted (4.5) best, all-hyphen next, underscore worst.
    NOTE: '.' AND '_' both read as '-' by norm_model_part, so a dotted id
    (deepseek-v3.x) outranks plain-hyphen which outranks underscore."""
    if '.' in rest:
        return 2
    if '_' not in rest:
        return 1
    return 0

def pick_survivor(members, eps):
    """Org-canonical ALWAYS wins (acceptance: deepseek-ai/* aliases to deepseek/*);
    then id style (dotted > hyphen > underscore); then endpoint coverage. Endpoints
    are moved to the survivor by the migration, so coverage is never lost."""
    def key(m):
        org, _, rest = m.partition('/')
        return (org not in ORG_ALIAS, style_score(rest), eps.get(m, 0), m)
    return sorted(members, key=key, reverse=True)[0]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()
    conn = psycopg2.connect(get_env()['SUPABASE_DB_URL'])
    cur = conn.cursor()

    cur.execute("SELECT id, is_active FROM models")
    all_models = {r[0]: r[1] for r in cur.fetchall()}

    # 24h endpoint counts per model (Standard only, as the read path sees it)
    cur.execute("""
        SELECT model_id, count(*)
        FROM model_endpoints
        WHERE fetched_at >= NOW() - INTERVAL '24 hours'
          AND blended_price_per_m > 0
          AND COALESCE(raw_data->>'service_tier','') NOT IN ('flex','priority','ultrafast')
        GROUP BY 1
    """)
    eps = {r[0]: r[1] for r in cur.fetchall()}

    groups = defaultdict(list)
    for mid, active in all_models.items():
        if active:
            groups[canon(mid).rsplit('/',1)[0] + '/' + norm_model_part(mid)].append(mid)

    pairs = []
    for key, members in groups.items():
        if len(members) < 2:
            continue
        survivor = pick_survivor(members, eps)
        for m in members:
            if m != survivor:
                pairs.append((m, survivor))

    print(f"Found {len(pairs)} duplicate rows to consolidate:")
    total_ep = 0
    for dup, keep in sorted(pairs):
        n = eps.get(dup, 0) + cur_rowcount(cur, dup)
        print(f"  {dup:46s} -> {keep:42s} (eps24h dup={eps.get(dup,0)}, keep={eps.get(keep,0)}, total_rows={n})")
        total_ep += n

    if not args.apply:
        print(f"\nDRY RUN - {len(pairs)} pairs, ~{total_ep} endpoint rows affected. Re-run with --apply.")
        conn.close()
        return

    conn.rollback()  # discard read txn
    cur = conn.cursor()
    try:
        moved = 0
        for dup, keep in pairs:
            # 1. Move endpoints (deduped by provider+prices)
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
            moved += cur.rowcount

            # 2. Repoint aliases
            cur.execute("UPDATE model_aliases SET canonical_model_id = %s WHERE canonical_model_id = %s",
                        (keep, dup))
            # 3. Ensure the dup resolves to the canonical row going forward
            cur.execute("""
                INSERT INTO model_aliases (alias, canonical_model_id)
                VALUES (%s, %s)
                ON CONFLICT (alias) DO UPDATE SET canonical_model_id = EXCLUDED.canonical_model_id
            """, (dup, keep))
            # 4. Retire the dup
            cur.execute("UPDATE models SET is_active = FALSE WHERE id = %s", (dup,))
        conn.commit()
        print(f"\nCommitted: {len(pairs)} rows retired, {moved} endpoint rows moved.")
    except Exception as e:
        conn.rollback()
        print(f"\nFAILED, rolled back: {e}")
        raise
    finally:
        conn.close()

def cur_rowcount(cur, model_id):
    cur.execute("SELECT count(*) FROM model_endpoints WHERE model_id = %s", (model_id,))
    return cur.fetchone()[0]

if __name__ == '__main__':
    main()
