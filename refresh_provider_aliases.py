#!/usr/bin/env python3
"""Refresh provider_model_alias: canonical -> native model ids per provider.

Fetches each verified provider's public /models endpoint and maps our canonical
ids to the provider's native ids. Runs daily (cron). Missing mappings are fine:
the API falls back to the heuristic with a caveat.
"""
import json, os, re, sys, time, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import dotenv_values
import psycopg2

DB_URL = dotenv_values(os.path.expanduser("~/.hermes/.env"))["SUPABASE_DB_URL"]
# On Lightsail the env var comes from the service env file
if not DB_URL:
    for line in open("/home/ubuntu/inference-indexer/.env"):
        line = line.strip()
        if line.startswith("SUPABASE_DB_URL="):
            DB_URL = line.split("=", 1)[1]

def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())

PROVIDERS = [
    ("DeepInfra", "https://api.deepinfra.com/v1/openai/models", {}, "data"),
    ("Venice",    "https://api.venice.ai/api/v1/models", {}, "data"),
    ("Novita",    "https://api.novita.ai/v3/openai/models", {"User-Agent": "Mozilla/5.0 (compatible; InferenceIndexer/1.0)"}, "data"),
    ("SambaNova", "https://api.sambanova.ai/v1/models", {}, "data"),
    ("Mistral",   "https://api.mistral.ai/v1/models", None, "data"),  # key added below if present
    ("Fireworks", "https://api.fireworks.ai/inference/v1/models", None, None),
]

def main():
    env = dotenv_values(os.path.expanduser("~/.hermes/.env"))
    if os.path.exists("/home/ubuntu/inference-indexer/.env"):
        env = {**dotenv_values("/home/ubuntu/inference-indexer/.env"), **env}
    mistral_key = env.get("MISTRAL_API_KEY")
    fireworks_key = env.get("FIREWORKS_API_KEY")

    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT id FROM models WHERE is_active")
    canonical = {r[0] for r in cur.fetchall()}

    total = 0
    for name, murl, base_headers, path in PROVIDERS:
        headers = dict(base_headers) if base_headers else {}
        if name == "Mistral" and mistral_key:
            headers = {"Authorization": f"Bearer {mistral_key}"}
        if name == "Fireworks":
            if not fireworks_key:
                continue
            headers = {"Authorization": f"Bearer {fireworks_key}"}
        try:
            req = urllib.request.Request(murl, headers=headers)
            d = json.loads(urllib.request.urlopen(req, timeout=20).read())
            items = d.get("data") or []
            natives = [m.get("id") for m in items if m.get("id")]
        except Exception as e:
            print(f"{name}: fetch failed: {e}", flush=True)
            continue
        added = 0
        for cid in canonical:
            _, _, cslug = cid.partition("/")
            cn, fn = norm(cslug), norm(cid)
            best = None
            for n in natives:
                nn = norm(n)
                if nn == cn or nn == fn or (cn and nn.endswith(cn)):
                    best = n
                    break
            if best:
                cur.execute("""
                    INSERT INTO provider_model_alias (provider_name, canonical_model_id, native_model_id, verified_at)
                    VALUES (%s, %s, %s, now())
                    ON CONFLICT (provider_name, canonical_model_id)
                    DO UPDATE SET native_model_id = EXCLUDED.native_model_id, verified_at = now()
                """, (name, cid, best))
                added += 1
        print(f"{name}: {len(natives)} native, {added} aliases", flush=True)
        time.sleep(0.5)

    cur.execute("SELECT count(*) FROM provider_model_alias")
    print("total aliases:", cur.fetchone()[0], flush=True)
    cur.close()
    conn.close()

    try:
        refresh_model_aliases()
    except Exception as e:
        print(f"model_aliases refresh failed: {e}", flush=True)


def refresh_model_aliases():
    """PR-6: keep model_aliases fresh (identity/slug/display-name/native)."""
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO model_aliases (alias, canonical_model_id, source)
        SELECT id, id, 'identity' FROM models WHERE is_active
        ON CONFLICT (alias) DO NOTHING
    """)
    cur.execute("""
        INSERT INTO model_aliases (alias, canonical_model_id, source)
        SELECT split_part(id, '/', 2), id, 'slug' FROM models WHERE is_active AND id LIKE '%/%'
        ON CONFLICT (alias) DO NOTHING
    """)
    cur.execute("""
        INSERT INTO model_aliases (alias, canonical_model_id, source)
        SELECT lower(name), id, 'display_name' FROM models WHERE is_active AND name IS NOT NULL
        ON CONFLICT (alias) DO NOTHING
    """)
    cur.execute("""
        INSERT INTO model_aliases (alias, canonical_model_id, source)
        SELECT native_model_id, canonical_model_id, 'provider_native' FROM provider_model_alias
        ON CONFLICT (alias) DO NOTHING
    """)
    cur.execute("SELECT count(*) FROM model_aliases")
    print("model_aliases total:", cur.fetchone()[0], flush=True)

if __name__ == "__main__":
    main()
