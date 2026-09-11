#!/usr/bin/env python3
"""
Migration: model descriptions from OpenRouter.

Adds models.description and models.description_source. Descriptions are
harvested from OpenRouter's /api/v1/models catalog (same fetch the pipeline
already makes hourly). 398 of 748 active models are covered; the rest are
direct-provider niche models OR doesn't list.

Run once. Idempotent.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import dotenv_values
import psycopg2

vals = dotenv_values(os.path.expanduser("~/.hermes/.env"))
conn = psycopg2.connect(vals["SUPABASE_DB_URL"], connect_timeout=10)
cur = conn.cursor()

# 1. Columns
cur.execute("""
    ALTER TABLE models ADD COLUMN IF NOT EXISTS description TEXT;
    ALTER TABLE models ADD COLUMN IF NOT EXISTS description_source TEXT;
""")
conn.commit()

# 2. Verify
cur.execute("""
    SELECT column_name FROM information_schema.columns
    WHERE table_name = 'models' AND column_name IN ('description', 'description_source')
""")
cols = [r[0] for r in cur.fetchall()]
print("columns now:", cols)
cur.close()
conn.close()
print("migration complete")