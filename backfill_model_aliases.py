#!/usr/bin/env python3
"""Backfill provider_model_alias: canonical -> native model ids per provider.

Pulls each provider's live public /models list, normalizes ids to canonical
form (lowercase, creator prefix), and stores native -> canonical mappings.
Only runs against providers whose /models is publicly reachable (the ones we
verified in endpoint_provider_config).

Safe to re-run: upserts by (provider_name, canonical_model_id).
Historical pricing data is never touched.
"""

import json
import os
import urllib.request

from dotenv import dotenv_values
import psycopg2

# (provider_name, models_url, id_json_path) - all verified reachable
PROVIDERS = [
    ("DeepInfra", "https://api.deepinfra.com/v1/openai/models"),
    ("Novita", "https://api.novita.ai/v3/openai/models"),
    ("SambaNova", "https://api.sambanova.ai/v1/models"),
    ("Mistral", "https://api.mistral.ai/v1/models"),
    ("OpenRouter", "https://openrouter.ai/api/v1/models"),
    ("TensorX", "https://api.tensorix.ai/v1/models"),
    ("Venice", "https://api.venice.ai/api/v1/models"),
    ("Jina", "https://api.jina.ai/v1/models"),
]


def fetch_ids(url: str) -> list[str]:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    data = json.loads(urllib.request.urlopen(req, timeout=20).read())
    items = data.get("data", data if isinstance(data, list) else [])
    return [it["id"] for it in items if isinstance(it, dict) and it.get("id")]


def main() -> None:
    db = dotenv_values(os.path.expanduser("~/.hermes/.env"))["SUPABASE_DB_URL"]
    conn = psycopg2.connect(db)
    conn.autocommit = True
    cur = conn.cursor()

    # existing canonical ids for the is_active check
    cur.execute("SELECT id FROM models WHERE is_active = TRUE")
    canonical_set = {r[0] for r in cur.fetchall()}

    inserted = 0
    for provider, models_url in PROVIDERS:
        try:
            native_ids = fetch_ids(models_url)
        except Exception as e:
            print(f"  {provider}: FETCH FAIL {e}")
            continue
        matched = 0
        for native in native_ids:
            # normalize: lowercase = our canonical form
            canonical = native.lower()
            if canonical in canonical_set:
                cur.execute("""
                    INSERT INTO provider_model_alias (provider_name, canonical_model_id, native_model_id, verified_at)
                    VALUES (%s, %s, %s, now())
                    ON CONFLICT (provider_name, canonical_model_id)
                    DO UPDATE SET native_model_id = EXCLUDED.native_model_id, verified_at = now()
                """, (provider, canonical, native))
                inserted += 1
        print(f"  {provider}: {len(native_ids)} native ids, {inserted} cumulative matches")

    cur.execute("SELECT count(*) FROM provider_model_alias")
    print("total alias rows:", cur.fetchone()[0])
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
