#!/usr/bin/env python3
"""
Migration: AA-rebase resilience (Sep 2026).

Adds:
  1. sit_index_values.aa_version        - AA Intelligence Index version that produced the row
  2. sit_index_values.basket_providers  - JSONB array of providers in the TPI basket
  3. sit_index_values.eligibility_threshold - the score threshold used for eligibility
  4. sit_index_values.rebase_group      - grouping for era breaks (e.g. 'v4.1', 'v4.2+')
  5. models.aa_score_version            - AA version per model score
  6. aa_index_versions table            - version registry + first-seen date
  7. aa_ingest_log table                - daily stats for rebase detection

Idempotent: safe to run multiple times.
"""
import os
from dotenv import dotenv_values
import psycopg2

vals = dotenv_values(os.path.expanduser("~/.hermes/.env"))
conn = psycopg2.connect(vals["SUPABASE_DB_URL"], connect_timeout=10)
cur = conn.cursor()

def col_exists(table, col):
    cur.execute("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name=%s AND column_name=%s
    """, (table, col))
    return cur.fetchone() is not None

def table_exists(table):
    cur.execute("""
        SELECT 1 FROM information_schema.tables
        WHERE table_name=%s
    """, (table,))
    return cur.fetchone() is not None

# 1-3. sit_index_values new columns
for col, ddl in [
    ("aa_version", "ALTER TABLE sit_index_values ADD COLUMN aa_version TEXT"),
    ("basket_providers", "ALTER TABLE sit_index_values ADD COLUMN basket_providers JSONB"),
    ("eligibility_threshold", "ALTER TABLE sit_index_values ADD COLUMN eligibility_threshold NUMERIC"),
    ("rebase_group", "ALTER TABLE sit_index_values ADD COLUMN rebase_group TEXT"),
]:
    if not col_exists("sit_index_values", col):
        print(f"  sit_index_values: adding {col}")
        cur.execute(ddl)
    else:
        print(f"  sit_index_values.{col} exists, skipping")

# 4. models.aa_score_version
if not col_exists("models", "aa_score_version"):
    print("  models: adding aa_score_version")
    cur.execute("ALTER TABLE models ADD COLUMN aa_score_version TEXT")
else:
    print("  models.aa_score_version exists, skipping")

# 5. aa_index_versions registry
if not table_exists("aa_index_versions"):
    print("  creating aa_index_versions")
    cur.execute("""
        CREATE TABLE aa_index_versions (
            version TEXT PRIMARY KEY,
            first_seen DATE NOT NULL,
            announced_on DATE,
            notes TEXT
        )
    """)
else:
    print("  aa_index_versions exists, skipping")

# 6. aa_daily_ingest stats (for median-shift rebase detection)
if not table_exists("aa_daily_ingest"):
    print("  creating aa_daily_ingest")
    cur.execute("""
        CREATE TABLE aa_daily_ingest (
            date DATE PRIMARY KEY,
            aa_version TEXT,
            models_scored INT,
            median_score NUMERIC,
            frontier_count INT,   -- count at/above that day's P90
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
else:
    print("  aa_daily_ingest exists, skipping")

conn.commit()

# Populate known versions
cur.execute("""
    INSERT INTO aa_index_versions (version, first_seen, notes)
    VALUES
        ('v4.1', '2026-08-04', 'Baseline for II; TPI originally built on these scores'),
        ('v4.2', '2026-09-04', 'AA-Briefcase + GDP.pdf added, GPQA Diamond retired, 40% held-out weight'),
        ('v4.3', '2026-09-07', 'Terminal-Bench v4 + AutomationBench-AA, 45% held-out weight')
    ON CONFLICT (version) DO NOTHING
""")
conn.commit()

# Verify
cur.execute("""
    SELECT column_name FROM information_schema.columns
    WHERE table_name='sit_index_values' ORDER BY ordinal_position
""")
print("\nFinal sit_index_values columns:", [r[0] for r in cur.fetchall()])
cur.execute("SELECT version, first_seen FROM aa_index_versions ORDER BY first_seen")
print("aa_index_versions:", cur.fetchall())
cur.close()
conn.close()
print("\nMigration complete.")