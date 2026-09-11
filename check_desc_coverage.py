#!/usr/bin/env python3
"""Coverage check: how many of our active models have OpenRouter descriptions?"""
import requests, os
import psycopg2
from dotenv import dotenv_values

d = requests.get("https://openrouter.ai/api/v1/models", timeout=30).json()["data"]
with_desc = [m for m in d if m.get("description")]
print(f"catalog: {len(d)} models | with description: {len(with_desc)} ({100*len(with_desc)//len(d)}%)")
lens = [len(m["description"]) for m in with_desc]
print("desc length: min", min(lens), "median", sorted(lens)[len(lens)//2], "max", max(lens))

vals = dotenv_values(os.path.expanduser("~/.hermes/.env"))
conn = psycopg2.connect(vals["SUPABASE_DB_URL"], connect_timeout=10)
cur = conn.cursor()
cur.execute("SELECT id FROM models WHERE is_active")
ours = {r[0] for r in cur.fetchall()}
conn.close()
theirs = {m["id"] for m in d}
print(f"our active: {len(ours)} | in OR catalog: {len(ours & theirs)}")
covered = sum(1 for mid in ours if any(m["id"] == mid and m.get("description") for m in d))
print(f"our active with OR description: {covered}")