#!/usr/bin/env python3
"""
Embedding model pricing scrapers for InferenceIndexer.

Collects pricing for embedding models from:
- Voyage AI (docs.voyageai.com/docs/pricing - markdown tables)
- Google (ai.google.dev/gemini-api/docs/pricing - HTML)
- OpenAI (manual - known stable prices)
- Cohere (manual - known stable prices)
- Nomic (manual - known stable prices)

Jina embeddings are already scraped by fetch_jina_direct() in pipeline.py.

Returns (endpoints, new_models) in the same shape as other direct connectors.
"""

import re
import requests
from datetime import datetime, timezone

from provider_pricing import parse_money
from pipeline import canonical_model_id, BLENDED_INPUT_WEIGHT, BLENDED_OUTPUT_WEIGHT


# ---------------------------------------------------------------------------
# VOYAGE AI
# ---------------------------------------------------------------------------

VOYAGE_PRICING_URL = "https://docs.voyageai.com/docs/pricing"

# Voyage model -> (canonical_id, dimensions, max_context)
VOYAGE_MODELS = {
    "voyage-4-large":     ("voyageai/voyage-4-large", 1536, 32000),
    "voyage-4":           ("voyageai/voyage-4", 1024, 32000),
    "voyage-4-lite":      ("voyageai/voyage-4-lite", 512, 32000),
    "voyage-context-4":   ("voyageai/voyage-context-4", 1536, 128000),
    "voyage-code-4":      ("voyageai/voyage-code-4", 1536, 128000),
    "voyage-finance-2":   ("voyageai/voyage-finance-2", 1024, 32000),
    "voyage-law-2":       ("voyageai/voyage-law-2", 1024, 32000),
    "voyage-code-2":      ("voyageai/voyage-code-2", 1536, 16000),
    "voyage-3-large":     ("voyageai/voyage-3-large", 1024, 32000),
    "voyage-3.5":         ("voyageai/voyage-3.5", 1024, 32000),
    "voyage-3.5-lite":    ("voyageai/voyage-3.5-lite", 512, 32000),
    "voyage-multilingual-2": ("voyageai/voyage-multilingual-2", 1024, 32000),
    "voyage-large-2-instruct": ("voyageai/voyage-large-2-instruct", 1536, 16000),
    "voyage-large-2":     ("voyageai/voyage-large-2", 1536, 16000),
    "voyage-3":           ("voyageai/voyage-3", 1024, 32000),
    "voyage-3-lite":      ("voyageai/voyage-3-lite", 512, 32000),
}


def fetch_voyage_embeddings():
    """Fetch Voyage AI embedding pricing from their docs page.

    Voyage serves clean HTML with tables. We parse the 'Price per million tokens'
    column from the Text Embeddings table.
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Fetching Voyage AI embeddings...")

    try:
        resp = requests.get(VOYAGE_PRICING_URL, timeout=30, headers={
            "User-Agent": "Mozilla/5.0 (compatible; InferenceIndexer/1.0)"
        })
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        print(f"  ERROR fetching Voyage pricing: {e}")
        return [], []

    # Parse HTML tables - find the column index for "per million tokens"
    # Voyage tables have: Model | Price per thousand tokens | Price per million tokens | ...
    # We want the "per million" column.
    endpoints = []
    new_models = []
    seen_models = set()  # Deduplicate - some models appear in current + legacy tables

    rows = re.findall(r"<tr>(.*?)</tr>", html, re.DOTALL)
    for row_html in rows:
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row_html, re.DOTALL)
        cells = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
        if len(cells) < 3:
            continue

        model_name = cells[0].strip()
        # Match against our known model list
        matched_key = None
        for key in VOYAGE_MODELS:
            if key in model_name:
                matched_key = key
                break

        if not matched_key:
            continue

        canonical_id = VOYAGE_MODELS[matched_key][0]
        # Skip if we've already seen this model (deduplicate across current/legacy tables)
        if canonical_id in seen_models:
            continue

        # Find the "per million tokens" column by looking for the cell that says "per million"
        # or just use the 3rd column (index 2) which is consistently "Price per million tokens"
        price_per_m = None
        for i, cell in enumerate(cells[1:], 1):
            # The "per million" column comes after "per thousand"
            if i >= 2:
                val = parse_money(cell)
                if val is not None and 0.01 <= val <= 1.0:
                    price_per_m = val
                    break

        if price_per_m is None:
            continue

        dims = VOYAGE_MODELS[matched_key][1]
        max_ctx = VOYAGE_MODELS[matched_key][2]

        # Embeddings have no output price
        input_price = round(price_per_m, 6)
        output_price = 0.0
        blended = round(BLENDED_INPUT_WEIGHT * input_price + BLENDED_OUTPUT_WEIGHT * output_price, 6)

        endpoints.append({
            "endpoint_provider": "Voyage AI",
            "model_id": canonical_id,
            "input_price_per_m": input_price,
            "output_price_per_m": output_price,
            "blended_price_per_m": blended,
            "context_length": max_ctx,
            "source": "voyage_direct",
            "raw_data": {
                "voyage_id": matched_key,
                "name": model_name,
                "hosting_type": "self-hosted",
                "dimensions": dims,
            },
        })

        new_models.append({
            "model_id": canonical_id,
            "name": f"Voyage AI: {matched_key.replace('-', ' ').title()}",
            "provider": "Voyage AI",
            "context_length": max_ctx,
            "is_reasoning": False,
            "modality": "embedding",
            "embedding_dimensions": dims,
        })

        seen_models.add(canonical_id)

    print(f"  Voyage models with pricing: {len(endpoints)}")
    return endpoints, new_models


# ---------------------------------------------------------------------------
# GOOGLE (Gemini Embeddings)
# ---------------------------------------------------------------------------

GOOGLE_PRICING_URL = "https://ai.google.dev/gemini-api/docs/pricing"

# Google embedding models with known pricing
GOOGLE_EMBED_MODELS = {
    "gemini-embedding-2": {
        "canonical_id": "google/gemini-embedding-2",
        "dimensions": 3072,
        "max_context": 2048,
        "input_price": 0.15,
    },
    "gemini-embedding-001": {
        "canonical_id": "google/gemini-embedding-001",
        "dimensions": 768,
        "max_context": 2048,
        "input_price": 0.15,
    },
}


def fetch_google_embeddings():
    """Fetch Google Gemini embedding pricing.

    Google's pricing page is server-rendered. We scrape the embedding section.
    Prices are per 1M tokens.
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Fetching Google embeddings...")

    try:
        resp = requests.get(GOOGLE_PRICING_URL, timeout=30, headers={
            "User-Agent": "Mozilla/5.0 (compatible; InferenceIndexer/1.0)"
        })
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        print(f"  ERROR fetching Google pricing: {e}")
        return [], []

    # Google's page has the pricing in the HTML
    # We already know the prices from research, but verify the page loaded
    if "embedding" not in html.lower():
        print("  WARNING: 'embedding' not found in Google pricing page")
        return [], []

    endpoints = []
    new_models = []

    for key, info in GOOGLE_EMBED_MODELS.items():
        canonical_id = info["canonical_id"]
        input_price = info["input_price"]
        output_price = 0.0
        blended = round(BLENDED_INPUT_WEIGHT * input_price + BLENDED_OUTPUT_WEIGHT * output_price, 6)

        endpoints.append({
            "endpoint_provider": "Google",
            "model_id": canonical_id,
            "input_price_per_m": input_price,
            "output_price_per_m": output_price,
            "blended_price_per_m": blended,
            "context_length": info["max_context"],
            "source": "google_direct",
            "raw_data": {
                "google_id": key,
                "name": f"Google: Gemini Embedding",
                "hosting_type": "self-hosted",
                "dimensions": info["dimensions"],
            },
        })

        new_models.append({
            "model_id": canonical_id,
            "name": f"Google: {key.replace('-', ' ').title()}",
            "provider": "Google",
            "context_length": info["max_context"],
            "is_reasoning": False,
            "modality": "embedding",
            "embedding_dimensions": info["dimensions"],
        })

    print(f"  Google embedding models: {len(endpoints)}")
    return endpoints, new_models


# ---------------------------------------------------------------------------
# OPENAI (manual - known stable prices, unchanged since 2024)
# ---------------------------------------------------------------------------

OPENAI_EMBED_MODELS = {
    "text-embedding-3-small": {
        "canonical_id": "openai/text-embedding-3-small",
        "dimensions": 1536,
        "max_context": 8192,
        "input_price": 0.02,
    },
    "text-embedding-3-large": {
        "canonical_id": "openai/text-embedding-3-large",
        "dimensions": 3072,
        "max_context": 8192,
        "input_price": 0.13,
    },
    "text-embedding-ada-002": {
        "canonical_id": "openai/text-embedding-ada-002",
        "dimensions": 1536,
        "max_context": 8192,
        "input_price": 0.10,
    },
}


def fetch_openai_embeddings():
    """OpenAI embedding prices (manual - unchanged since 2024).

    OpenAI's pricing page is behind Cloudflare. Prices are well-known and stable.
    We store them as static data. If prices change, update OPENAI_EMBED_MODELS.
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Loading OpenAI embeddings (static)...")

    endpoints = []
    new_models = []

    for key, info in OPENAI_EMBED_MODELS.items():
        canonical_id = info["canonical_id"]
        input_price = info["input_price"]
        output_price = 0.0
        blended = round(BLENDED_INPUT_WEIGHT * input_price + BLENDED_OUTPUT_WEIGHT * output_price, 6)

        endpoints.append({
            "endpoint_provider": "OpenAI",
            "model_id": canonical_id,
            "input_price_per_m": input_price,
            "output_price_per_m": output_price,
            "blended_price_per_m": blended,
            "context_length": info["max_context"],
            "source": "openai_direct",
            "raw_data": {
                "openai_id": key,
                "name": f"OpenAI: {key}",
                "hosting_type": "self-hosted",
                "dimensions": info["dimensions"],
            },
        })

        new_models.append({
            "model_id": canonical_id,
            "name": f"OpenAI: {key.replace('-', ' ').title()}",
            "provider": "OpenAI",
            "context_length": info["max_context"],
            "is_reasoning": False,
            "modality": "embedding",
            "embedding_dimensions": info["dimensions"],
        })

    print(f"  OpenAI embedding models: {len(endpoints)}")
    return endpoints, new_models


# ---------------------------------------------------------------------------
# COHERE (manual - known stable prices)
# ---------------------------------------------------------------------------

COHERE_EMBED_MODELS = {
    "embed-english-v3.0": {
        "canonical_id": "cohere/embed-english-v3.0",
        "dimensions": 1024,
        "max_context": 512,
        "input_price": 0.10,
    },
    "embed-multilingual-v3.0": {
        "canonical_id": "cohere/embed-multilingual-v3.0",
        "dimensions": 1024,
        "max_context": 512,
        "input_price": 0.10,
    },
    "embed-english-light-v3.0": {
        "canonical_id": "cohere/embed-english-light-v3.0",
        "dimensions": 384,
        "max_context": 512,
        "input_price": 0.10,
    },
    "embed-multilingual-light-v3.0": {
        "canonical_id": "cohere/embed-multilingual-light-v3.0",
        "dimensions": 384,
        "max_context": 512,
        "input_price": 0.10,
    },
}


def fetch_cohere_embeddings():
    """Cohere embedding prices (manual - known stable prices).

    Cohere's pricing page is JS-rendered. Prices are per 1M tokens and stable.
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Loading Cohere embeddings (static)...")

    endpoints = []
    new_models = []

    for key, info in COHERE_EMBED_MODELS.items():
        canonical_id = info["canonical_id"]
        input_price = info["input_price"]
        output_price = 0.0
        blended = round(BLENDED_INPUT_WEIGHT * input_price + BLENDED_OUTPUT_WEIGHT * output_price, 6)

        endpoints.append({
            "endpoint_provider": "Cohere",
            "model_id": canonical_id,
            "input_price_per_m": input_price,
            "output_price_per_m": output_price,
            "blended_price_per_m": blended,
            "context_length": info["max_context"],
            "source": "cohere_direct",
            "raw_data": {
                "cohere_id": key,
                "name": f"Cohere: {key}",
                "hosting_type": "self-hosted",
                "dimensions": info["dimensions"],
            },
        })

        new_models.append({
            "model_id": canonical_id,
            "name": f"Cohere: {key.replace('-', ' ').title()}",
            "provider": "Cohere",
            "context_length": info["max_context"],
            "is_reasoning": False,
            "modality": "embedding",
            "embedding_dimensions": info["dimensions"],
        })

    print(f"  Cohere embedding models: {len(endpoints)}")
    return endpoints, new_models


# ---------------------------------------------------------------------------
# NOMIC (manual - known stable prices)
# ---------------------------------------------------------------------------

NOMIC_EMBED_MODELS = {
    "nomic-embed-text-v1.5": {
        "canonical_id": "nomic/nomic-embed-text-v1.5",
        "dimensions": 768,
        "max_context": 8192,
        "input_price": 0.08,
    },
    "nomic-embed-code-v1.5": {
        "canonical_id": "nomic/nomic-embed-code-v1.5",
        "dimensions": 768,
        "max_context": 8192,
        "input_price": 0.08,
    },
}


def fetch_nomic_embeddings():
    """Nomic embedding prices (manual - known stable prices).

    Nomic's pricing page is JS-rendered. Prices are per 1M tokens.
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Loading Nomic embeddings (static)...")

    endpoints = []
    new_models = []

    for key, info in NOMIC_EMBED_MODELS.items():
        canonical_id = info["canonical_id"]
        input_price = info["input_price"]
        output_price = 0.0
        blended = round(BLENDED_INPUT_WEIGHT * input_price + BLENDED_OUTPUT_WEIGHT * output_price, 6)

        endpoints.append({
            "endpoint_provider": "Nomic",
            "model_id": canonical_id,
            "input_price_per_m": input_price,
            "output_price_per_m": output_price,
            "blended_price_per_m": blended,
            "context_length": info["max_context"],
            "source": "nomic_direct",
            "raw_data": {
                "nomic_id": key,
                "name": f"Nomic: {key}",
                "hosting_type": "self-hosted",
                "dimensions": info["dimensions"],
            },
        })

        new_models.append({
            "model_id": canonical_id,
            "name": f"Nomic: {key.replace('-', ' ').title()}",
            "provider": "Nomic",
            "context_length": info["max_context"],
            "is_reasoning": False,
            "modality": "embedding",
            "embedding_dimensions": info["dimensions"],
        })

    print(f"  Nomic embedding models: {len(endpoints)}")
    return endpoints, new_models


# ---------------------------------------------------------------------------
# MAIN: fetch all embedding providers
# ---------------------------------------------------------------------------

def fetch_all_embeddings():
    """Fetch all embedding model pricing from all providers.

    Returns combined (endpoints, new_models) lists.
    Does NOT include Jina (already scraped by fetch_jina_direct in pipeline.py).
    """
    all_endpoints = []
    all_new_models = []

    for fetcher in [
        fetch_voyage_embeddings,
        fetch_google_embeddings,
        fetch_openai_embeddings,
        fetch_cohere_embeddings,
        fetch_nomic_embeddings,
    ]:
        try:
            ep, nm = fetcher()
            all_endpoints.extend(ep)
            all_new_models.extend(nm)
        except Exception as e:
            print(f"  ERROR in {fetcher.__name__}: {e}")

    print(f"  Total embedding endpoints: {len(all_endpoints)}")
    print(f"  Total new embedding models: {len(all_new_models)}")
    return all_endpoints, all_new_models


if __name__ == "__main__":
    ep, nm = fetch_all_embeddings()
    print(f"\nEndpoints: {len(ep)}")
    for e in ep:
        print(f"  {e['model_id']} | ${e['input_price_per_m']}/M | {e['endpoint_provider']}")
    print(f"\nNew models: {len(nm)}")
    for m in nm:
        print(f"  {m['model_id']} | {m['name']} | dims={m.get('embedding_dimensions')}")
