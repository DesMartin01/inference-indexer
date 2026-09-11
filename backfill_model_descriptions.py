#!/usr/bin/env python3
"""
Backfill models.description from OpenRouter's catalog.

OpenRouter serves a human-written description for 100% of its 444-model
catalog (median ~211 chars). 398 of our 748 active models are covered; the
rest (direct-provider niche models: embeddings, rerankers, TTS) stay NULL.

Usage:
    .venv/bin/python3 backfill_model_descriptions.py            # apply
    .venv/bin/python3 backfill_model_descriptions.py --dry-run  # preview
"""
import os, sys, requests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import dotenv_values
import psycopg2

vals = dotenv_values(os.path.expanduser("~/.hermes/.env"))

print("Fetching OpenRouter catalog...")
d = requests.get("https://openrouter.ai/api/v1/models", timeout=30).json()["data"]
by_id = {m["id"]: m for m in d}
print(f"catalog: {len(d)} models, {sum(1 for m in d if m.get('description'))} with descriptions")

conn = psycopg2.connect(vals["SUPABASE_DB_URL"], connect_timeout=10)
cur = conn.cursor()
cur.execute("SELECT id FROM models WHERE is_active")
ours = [r[0] for r in cur.fetchall()]

updates = []
for mid in ours:
    m = by_id.get(mid)
    desc = (m or {}).get("description")
    if desc:
        updates.append((desc, "openrouter", mid))

print(f"fillable: {len(updates)} of {len(ours)} active models")

if "--dry-run" in sys.argv:
    for desc, src, mid in updates[:5]:
        print(f"  {mid}: {desc[:120]}...")
    print("DRY RUN: nothing written.")
    sys.exit(0)

# Only overwrite when the new value is non-null; never clobber a
# hand-written description with a re-harvest of the same source.
cur.executemany("""
    UPDATE models
    SET description = %s, description_source = %s, updated_at = NOW()
    WHERE id = %s AND (description IS NULL OR description_source = 'openrouter')
""", updates)
conn.commit()

cur.execute("""
    SELECT count(*) FILTER (WHERE description IS NOT NULL),
           count(*) FILTER (WHERE description IS NULL), count(*)
    FROM models WHERE is_active
""")
have, miss, total = cur.fetchone()
print(f"after: {have} with description, {miss} without, {total} total")
cur.close()
conn.close()