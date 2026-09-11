#!/usr/bin/env python3
"""
One-time backfill: populate models.creator_country from creator_countries.py.

Two sources, in priority order:
  1. The AA leaderboard creator name (AA dropped modelCreatorCountry in v4.3)
  2. The model's II provider label (OpenRouter prefix, normalized)

Only overwrites NULL creator_country values - existing data is preserved.

Usage:
    .venv/bin/python3 backfill_creator_countries.py           # apply
    .venv/bin/python3 backfill_creator_countries.py --dry-run # preview
"""
import os, sys, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import dotenv_values
import psycopg2
from creator_countries import country_for_creator

vals = dotenv_values(os.path.expanduser("~/.hermes/.env"))
conn = psycopg2.connect(vals["SUPABASE_DB_URL"], connect_timeout=10)
cur = conn.cursor()

cur.execute("SELECT id, name, provider, creator_country FROM models WHERE is_active")
rows = cur.fetchall()

updates = []
for model_id, name, provider, existing in rows:
    if model_id.endswith(":batch"):
        continue  # batches inherit via upsert on the base id
    cc = None
    # 1. From AA creator name embedded in the display name ("Anthropic: Claude...")
    if name and ":" in name:
        cc = country_for_creator(name.split(":", 1)[0].strip())
    # 2. From the II provider label
    if not cc:
        cc = country_for_creator(provider)
    if cc:
        updates.append((model_id, cc))

print(f"active models: {len(rows)} | fillable: {len(updates)}")

# Show per-provider summary
from collections import Counter
summary = Counter()
for model_id, cc in updates:
    summary[cc] += 1
print("by country:", dict(summary))

if __import__("sys").argv[1:2] == ["--dry-run"]:
    for mid, cc in updates[:15]:
        print("  ", mid, "->", cc)
    print(f"DRY RUN: nothing written.")
    sys.exit(0)

for model_id, cc in updates:
    cur.execute("""
        UPDATE models SET creator_country = %s, updated_at = NOW()
        WHERE id = %s AND creator_country IS NULL
    """, (cc, model_id))
conn.commit()
cur.execute("SELECT creator_country IS NULL, count(*) FROM models WHERE is_active GROUP BY 1")
print("after:", cur.fetchall())
cur.close()
conn.close()