#!/usr/bin/env python3
"""One-shot DB repair for the 2026-10-22 tier-tag ingest bug + org aliases.

Does four things (dry-run by default, --apply to execute):

1. Backfill service_tier into raw_data for existing endpoints that came from
   OpenRouter with a tagged variant ('fireworks/spot' etc.) but no
   service_tier field. Same tier-token rule as pipeline.normalize_endpoints:
   known tier tokens only (spot/fast/us/flex/priority/ultrafast/batch);
   fp8/global are variant qualifiers, not tiers, and become quantization.

2. Add providers.pricing_notes (idempotent ALTER) and set the DeepInfra note:
   API prices are published; DeepInfra's marketing page occasionally shows
   lower promotional rates. Des's decision 2026-10-22: API is the source of
   truth, page difference is referenced, not copied.

3. Reverse safety aliases: for every ACTIVE x-ai/* model, alias
   xai/<model> -> x-ai/<model> so web 308s (x-ai -> xai prefix redirect) and
   /v1/models/{id} resolve instead of 404ing. (The 5 consolidated Grok ids
   already live under xai/; this covers the stragglers like x-ai/grok-4.6.)

4. Print org-alias duplicate-group counts for follow-up (does NOT run the
   consolidation; migrate_consolidate_org_aliases.py --apply does that).
"""
import os
import json
import argparse
import psycopg2

TIER_TOKENS = {"spot", "fast", "us", "flex", "priority", "ultrafast", "batch"}


def get_env():
    for line in open(os.path.expanduser("~/.hermes/.env")):
        if line.startswith("SUPABASE_DB_URL"):
            return {"SUPABASE_DB_URL": line.split("=", 1)[1].strip().strip('"')}
    raise SystemExit("SUPABASE_DB_URL not found")


def tier_from_tag(tag):
    if not tag or "/" not in tag:
        return None
    parts = [p for p in tag.partition("/")[2].split("/") if p]
    tier = next((p for p in parts if p in TIER_TOKENS), None)
    quant = next((p for p in parts if p not in TIER_TOKENS), None)
    return tier, quant


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    conn = psycopg2.connect(get_env()["SUPABASE_DB_URL"])
    cur = conn.cursor()

    # --- 1. service_tier backfill from raw_data.tag -----------------------
    cur.execute("""
        SELECT id, raw_data->>'tag'
        FROM model_endpoints
        WHERE raw_data ? 'tag'
          AND COALESCE(raw_data->>'service_tier','') = ''
    """)
    rows = cur.fetchall()
    updates = []
    for ep_id, tag in rows:
        parsed = tier_from_tag(tag)
        if not parsed:
            continue
        tier, quant = parsed
        if tier:
            updates.append((ep_id, tier, quant))
    print(f"[1] endpoints needing service_tier backfill: {len(updates)} of {len(rows)} tagged")
    from collections import Counter
    print("    by tier:", dict(Counter(u[1] for u in updates)))
    if args.apply:
        for ep_id, tier, quant in updates:
            if quant:
                cur.execute("""
                    UPDATE model_endpoints
                    SET raw_data = raw_data || jsonb_build_object('service_tier', %s, 'quantization', %s)
                    WHERE id = %s
                """, (tier, quant, ep_id))
            else:
                cur.execute("""
                    UPDATE model_endpoints
                    SET raw_data = raw_data || jsonb_build_object('service_tier', %s)
                    WHERE id = %s
                """, (tier, ep_id))
        print(f"    backfilled {len(updates)} rows")

    # --- 2. providers.pricing_notes + DeepInfra note ----------------------
    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'providers' AND column_name = 'pricing_notes'
    """)
    if not cur.fetchone():
        print("[2] adding providers.pricing_notes column")
        if args.apply:
            cur.execute("ALTER TABLE providers ADD COLUMN pricing_notes text")
    else:
        print("[2] providers.pricing_notes already exists")
    DEEPINFRA_NOTE = (
        "Listed prices come from the DeepInfra API. DeepInfra's marketing "
        "pricing page occasionally shows lower promotional rates (e.g. "
        "GLM-5.3 at 0.5625/2.5 vs the API's 0.9/4.0); the API rate is the "
        "price published here."
    )
    if args.apply:
        cur.execute("UPDATE providers SET pricing_notes = %s WHERE name = 'DeepInfra'", (DEEPINFRA_NOTE,))

    # --- 3. reverse aliases: SKIPPED (2026-10-22 decision) ----------------
    # Canonical xAI prefix is x-ai/ (OpenRouter-emitted; see
    # migrate_xai_rename.py). No reverse aliases needed; the web 308 points
    # xai -> x-ai and pipeline ORG_CANONICAL maps xai -> x-ai.
    print("[3] skipped: x-ai stays canonical (see migrate_xai_rename.py)")

    # --- 4. org-alias dup group census (informational) --------------------
    cur.execute("""
        SELECT split_part(id,'/',1), count(*) FROM models
        WHERE is_active GROUP BY 1
        HAVING split_part(id,'/',1) IN ('deepseek-ai','meta','zai-org','minimaxai','stepfun-ai','moonshot','x-ai')
        ORDER BY 2 DESC
    """)
    print("[4] active rows on alias orgs (consolidation candidates):")
    for org, n in cur.fetchall():
        print(f"    {org}: {n}")

    if args.apply:
        conn.commit()
        print("\nCommitted.")
    else:
        print("\nDRY RUN - re-run with --apply to execute.")
    conn.close()


if __name__ == "__main__":
    main()
