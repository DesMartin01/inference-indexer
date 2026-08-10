#!/usr/bin/env python3
"""
InferenceIndexer - Provider Discovery Script

Finds inference providers we do NOT yet track, by diffing known upstream
sources against the live `providers` table. Delivers a shortlist of
candidates to review.

Sources (primary, machine-readable):
  1. LiteLLM model_prices_and_context_window.json  (BerriAI/litellm)
     Flat model keys "provider/model" -> collects every distinct provider
     prefix seen. High recall but noisy (includes cloud-provider model IDs
     like anthropic.claude-*, image sizes, etc).

Run modes:
  --shortlist   : print candidate providers not in our DB (default)
  --full        : print ALL providers found upstream, with tracked flag
  --count       : just summary counts

All output is plain text suitable for a cron delivery.
"""

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Upstream sources
# ---------------------------------------------------------------------------
LITELLM_PRICES_URL = (
    "https://raw.githubusercontent.com/BerriAI/litellm/main/"
    "model_prices_and_context_window.json"
)

# Prefixes that are NOT standalone inference providers (noise). These are
# cloud/model-id prefixes, image resolutions, or internal LiteLLM keys.
NOISE_PREFIXES = {
    "1024-x-1024", "1024-x-1536", "1536-x-1024", "256-x-256", "512-x-512",
    "1024-x-768", "768-x-1024", "512-x-768", "768-x-512", "512-x-512",
    "256-x-512", "512-x-1536", "1536-x-512", "1280-x-720", "720-x-1280",
    "1920-x-1080", "1080-x-1920",
}

# Treat these as hosted cloud provider catalogs or obvious non-inference
# tools (speech, image, video, web search, MLOps) not relevant to LLM
# inference pricing. Exclude from the discovery shortlist.
CLOUD_PRIMARY_PREFIXES = {
    "amazon", "amazon-nova", "azure", "google", "openai", "anthropic",
    "bedrock", "vertex", "cohere", "mistral", "meta", "amazon.titan",
    "ai21.jamba", "ai21.j2", "ai21", "gcp", "aws", "azure-openai",
    # speech / audio
    "assemblyai", "deepgram", "elevenlabs", "soniox", "aws_polly",
    # image / video / art
    "black_forest_labs", "recraft", "runwayml", "stability", "max-x-max",
    "fal_ai",
    # web search / tools (not inference)
    "firecrawl", "tavily", "searxng", "serper", "duckduckgo", "linkup",
    "exa_ai", "you_com", "perplexity", "v0", "github_copilot",
    # MLOps / infra / misc
    "wandb", "snowflake", "databricks", "databricks_mosaic", "heroku",
    "sagemaker", "vertex_ai", "oci", "watsonx", "google_pse", "vercel_ai_gateway",
    # pricing tiers / junk keys that aren't providers
    "low", "medium", "high", "standard", "hd", "palm",
}

def fetch_litellm_providers(timeout=30):
    """Fetch the LiteLLM price file and collect distinct provider prefixes."""
    req = urllib.request.Request(
        LITELLM_PRICES_URL,
        headers={"User-Agent": "inference-indexer/discovery 1.0"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", "replace")
    data = json.loads(raw)

    providers = set()
    for model_key in data:
        if "/" not in model_key:
            # Some keys are bare ids or sizes
            continue
        prov = model_key.split("/", 1)[0].strip().lower()
        if not prov:
            continue
        if prov in NOISE_PREFIXES:
            continue
        providers.add(prov)
    return providers


def load_tracked_providers():
    """Load provider names from the live DB via the public API endpoint."""
    # Read DB URL from ~/.hermes/.env (matching pipeline convention)
    env_path = os.path.expanduser("~/.hermes/.env")
    db_url = None
    if os.path.exists(env_path):
        for line in open(env_path):
            line = line.strip()
            if line.startswith("SUPABASE_DB_URL="):
                db_url = line.split("=", 1)[1].strip()
                break
    if db_url:
        try:
            import psycopg2
            conn = psycopg2.connect(db_url)
            cur = conn.cursor()
            cur.execute("SELECT name FROM providers")
            names = {r[0].strip().lower() for r in cur.fetchall()}
            cur.close()
            conn.close()
            return names
        except Exception:
            pass
    return set()


def normalize(name):
    """Best-effort normalize a candidate so it compares with tracked names."""
    return name.lower().replace("_", " ").replace(".", " ").strip()


def main():
    args = [a for a in sys.argv[1:]]

    try:
        litellm_providers = fetch_litellm_providers()
    except Exception as e:
        print(f"ERROR: could not fetch LiteLLM providers: {e}")
        return 1

    tracked = load_tracked_providers()
    # Normalize tracked names for comparison
    tracked_norm = {normalize(n) for n in tracked}

    # Normalize candidate providers
    candidates = {
        p for p in litellm_providers
        if normalize(p) not in tracked_norm
    }

    # Only keep candidates that look like independent providers
    # (exclude the cloud mega-provider prefixes above)
    independent_candidates = {
        p for p in candidates
        if p.split("-")[0] not in CLOUD_PRIMARY_PREFIXES
    }

    if "--count" in args:
        print(f"Upstream LiteLLM providers (raw):      {len(litellm_providers)}")
        print(f"Providers already tracked:              {len(tracked)}")
        print(f"New candidates:                         {len(independent_candidates)}")
        return 0

    if "--full" in args:
        print(f"# Upstream LiteLLM providers: {len(litellm_providers)}")
        print(f"# Tracked: {len(tracked)} | New: {len(independent_candidates)}")
        print()
        print("=== NEW (not yet tracked) — candidate review list ===")
        for p in sorted(independent_candidates):
            print(f"  {p}")
        print()
        print("=== ALL UPSTREAM (LiteLLM) — with tracked flag ===")
        for p in sorted(litellm_providers):
            flag = "OK" if normalize(p) in tracked_norm else "NEW"
            print(f"  [{flag}] {p}")
        return 0

    # Default: shortlist
    print(f"Inference Provider Discovery — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"Source: LiteLLM provider catalog")
    print()
    if independent_candidates:
        print(f"{len(independent_candidates)} provider(s) found that we don't yet track:")
        for p in sorted(independent_candidates):
            print(f"  • {p}")
        print()
        print("Review these on the LiteLLM docs or their sites, then add via")
        print("a no-auth connector or the /providers/submit flow.")
    else:
        print("No new providers found in this run.")

    # Also show a few near-miss noisy ones for awareness, capped
    excluded_cloud = sorted(candidates - independent_candidates)
    if excluded_cloud:
        print()
        print(f"(Ignored {len(excluded_cloud)} cloud/mega-provider prefixes, e.g.: "
              + ", ".join(excluded_cloud[:8]) + ")")

    return 0


if __name__ == "__main__":
    sys.exit(main())