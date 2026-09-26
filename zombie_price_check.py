#!/usr/bin/env python3
"""Zombie-price check (Sep 26 decision): do INACTIVE model rows still receive
fresh endpoint prices? Baseline Sep 26 18:40 UTC: 27 inactive rows priced
within 3d -- Vercel AI Gateway 17, Alibaba Cloud 9, DeepInfra 4, Novita 1,
SiliconFlow 1, Tencent 1. The VERCEL_SLUG_MAP went live ~midday Sep 26; if
Vercel's count drops to 0 the remap closed the drift.
Run with: .venv/bin/python zombie_price_check.py
"""
import os, re, psycopg2

env = open(os.path.expanduser('~/.hermes/.env')).read()
url = re.search(r'SUPABASE_DB_URL=(.+)', env).group(1).strip()
conn = psycopg2.connect(url, connect_timeout=15)
cur = conn.cursor()

print("=== Providers writing prices to INACTIVE model IDs (last 24h) ===")
cur.execute("""
    SELECT me.endpoint_provider, COUNT(DISTINCT me.model_id) AS n,
           MAX(me.fetched_at) AS latest
    FROM model_endpoints me
    JOIN models m ON m.id = me.model_id
    WHERE m.is_active = FALSE
      AND me.blended_price_per_m > 0
      AND me.fetched_at > NOW() - INTERVAL '24 hours'
    GROUP BY 1 ORDER BY 2 DESC
""")
for provider, n, latest in cur.fetchall():
    print(f"  {provider:25s} models={n:3d}  latest={latest}")

print("\n=== Inactive model IDs priced in last 24h ===")
cur.execute("""
    SELECT DISTINCT m.id
    FROM models m
    JOIN model_endpoints me ON me.model_id = m.id
    WHERE m.is_active = FALSE
      AND me.blended_price_per_m > 0
      AND me.fetched_at > NOW() - INTERVAL '24 hours'
    ORDER BY m.id
""")
ids = [r[0] for r in cur.fetchall()]
print(f"  {len(ids)} inactive IDs")
for i in ids:
    print(f"    {i}")

print("\n=== Verdict inputs ===")
cur.execute("SELECT COUNT(*) FROM model_endpoints WHERE fetched_at > NOW() - INTERVAL '24 hours'")
print(f"  total endpoint rows written last 24h: {cur.fetchone()[0]}")
cur.execute("""
    SELECT MAX(fetched_at) FROM model_endpoints
    WHERE endpoint_provider = 'Vercel AI Gateway'
""")
print(f"  latest Vercel AI Gateway fetch: {cur.fetchone()[0]}")
conn.close()
