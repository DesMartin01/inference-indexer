#!/usr/bin/env python3
"""
Fireworks direct pricing scraper for InferenceIndexer.

Fireworks' REST API (/inference/v1/models) returns the model CATALOG but NO
pricing field. The authoritative per-model prices live on their docs page:
    https://docs.fireworks.ai/serverless/pricing.md  (Mintlify markdown)

This module:
  1. Fetches the API catalog to get the canonical, live set of model IDs.
  2. Fetches the docs pricing markdown and parses the "Text and vision models"
     table (input / cached input / output per 1M tokens, USD).
  3. Maps docs display rows onto the real API model IDs (base model + Fast
     router variants + US variants).
  4. Returns priced endpoints + catalog-only new models in InferenceIndexer
     format, ready for insert_endpoints() / upsert_venice_models().

Resilience:
  - If the docs fetch fails, falls back to an embedded static pricing map
    (seeded from the same docs page) so the connector never silently empties.
"""

import re
import logging
from datetime import datetime, timezone

import requests

log = logging.getLogger("fireworks_pricing")

FIREWORKS_CATALOG_API = "https://api.fireworks.ai/inference/v1/models"
FIREWORKS_DOCS_PRICING = "https://docs.fireworks.ai/serverless/pricing.md"

# --- URL regex ---
# | [Name](https://app.fireworks.ai/models/fireworks/SLUG) | \$x / \$y / \$z | ... |
MODEL_ROW_RE = re.compile(
    r"\|\s*\[([^\]]+)\]\(https://app\.fireworks\.ai/models/fireworks/([^)]+)\)"
    r"\s*\|\s*\\\$([\d.]+) \/ \\\$([\d.]+) \/ \\\$([\d.]+)\s*\|\s*(\S[\s\S]*?)\s*\|"
)

# --- Embedded static pricing (input, cached, output per 1M USD) ---
# Keyed by the REAL Fireworks API model ID (from the /inference/v1/models
# catalog, exact string). Seeded from docs.fireworks.ai /serverless/pricing.md
# on 2026-08-08. "Fast" variants are the routers/* models; the K2.6 fast router
# is named "-turbo". Used both as the canonical map AND as fallback if the live
# docs fetch fails.
STATIC_PRICING = {
    "accounts/fireworks/models/kimi-k3": (3.00, 0.30, 15.00),
    "accounts/fireworks/routers/kimi-k3-fast": (4.50, 0.45, 22.50),
    "accounts/fireworks/models/kimi-k2p7-code": (0.95, 0.19, 4.00),
    "accounts/fireworks/routers/kimi-k2p7-code-fast": (1.90, 0.38, 8.00),
    "accounts/fireworks/models/kimi-k2p6": (0.95, 0.16, 4.00),
    "accounts/fireworks/routers/kimi-k2p6-turbo": (2.00, 0.30, 8.00),
    "accounts/fireworks/models/deepseek-v4-pro": (1.74, 0.145, 3.48),
    "accounts/fireworks/models/deepseek-v4-flash": (0.14, 0.028, 0.28),
    "accounts/fireworks/models/deepseek-v4-flash-0731": (0.14, 0.028, 0.28),
    "accounts/fireworks/models/glm-5p2": (1.40, 0.14, 4.40),
    "accounts/fireworks/routers/glm-5p2-fast": (2.10, 0.21, 6.60),
    "accounts/fireworks/models/glm-5p1": (1.40, 0.26, 4.40),
    "accounts/fireworks/routers/glm-5p1-fast": (2.80, 0.52, 8.80),
    "accounts/fireworks/models/qwen3p7-plus": (0.40, 0.08, 1.60),
    "accounts/fireworks/models/minimax-m3": (0.30, 0.06, 1.20),
    "accounts/fireworks/models/minimax-m2p7": (0.30, 0.06, 1.20),
    "accounts/fireworks/models/gpt-oss-120b": (0.15, 0.015, 0.60),
    "accounts/fireworks/models/gpt-oss-20b": (0.07, 0.035, 0.30),
    "accounts/fireworks/models/nemotron-3-ultra-nvfp4": (0.60, 0.12, 2.40),
}

# Map docs display name -> canonical Fireworks API model ID.
# The docs URL slug always points to the BASE model even for Fast/US variants,
# so the router/variant IDs are resolved here explicitly against the real catalog.
DOCS_NAME_TO_ID = {
    "Kimi K3": "accounts/fireworks/models/kimi-k3",
    "Kimi K3 Fast": "accounts/fireworks/routers/kimi-k3-fast",
    "Kimi K3 US": "accounts/fireworks/models/kimi-k3",
    "Kimi K2.7 Code": "accounts/fireworks/models/kimi-k2p7-code",
    "Kimi K2.7 Code Fast": "accounts/fireworks/routers/kimi-k2p7-code-fast",
    "Kimi K2.6": "accounts/fireworks/models/kimi-k2p6",
    "Kimi K2.6 Fast": "accounts/fireworks/routers/kimi-k2p6-turbo",
    "DeepSeek V4 Pro": "accounts/fireworks/models/deepseek-v4-pro",
    "DeepSeek V4 Flash": "accounts/fireworks/models/deepseek-v4-flash",
    "DeepSeek V4 Flash (0731)": "accounts/fireworks/models/deepseek-v4-flash-0731",
    "GLM 5.2": "accounts/fireworks/models/glm-5p2",
    "GLM 5.2 Fast": "accounts/fireworks/routers/glm-5p2-fast",
    "GLM 5.2 Fast US": "accounts/fireworks/routers/glm-5p2-fast",
    "GLM 5.1": "accounts/fireworks/models/glm-5p1",
    "GLM 5.1 Fast": "accounts/fireworks/routers/glm-5p1-fast",
    "Qwen 3.7 Plus": "accounts/fireworks/models/qwen3p7-plus",
    "MiniMax M3": "accounts/fireworks/models/minimax-m3",
    "MiniMax M2.7": "accounts/fireworks/models/minimax-m2p7",
    "OpenAI GPT OSS 120B": "accounts/fireworks/models/gpt-oss-120b",
    "OpenAI GPT OSS 20B": "accounts/fireworks/models/gpt-oss-20b",
    "NVIDIA Nemotron 3 Ultra (Preview)": "accounts/fireworks/models/nemotron-3-ultra-nvfp4",
}

# Map Fireworks native API model IDs -> our canonical InferenceIndexer model IDs.
# Base models merge onto the existing canonical (OpenRouter) row so direct and
# OpenRouter pricing share one model row (source_count=2), exactly like Venice.
# Fast/router variants are kept as SEPARATE priced rows per Des's decision, so
# they map to their own canonical IDs (created on first run if absent).
# Catalog-only Fireworks models with no canonical equivalent stay native.
FIREWORKS_MODEL_MAP = {
    # Base models -> merge onto canonical rows
    "accounts/fireworks/models/kimi-k3": "moonshotai/kimi-k3",
    "accounts/fireworks/models/kimi-k2p7-code": "moonshotai/kimi-k2.7-code",
    "accounts/fireworks/models/kimi-k2p6": "moonshotai/kimi-k2.6",
    "accounts/fireworks/models/deepseek-v4-pro": "deepseek/deepseek-v4-pro",
    "accounts/fireworks/models/deepseek-v4-flash": "deepseek/deepseek-v4-flash",
    "accounts/fireworks/models/deepseek-v4-flash-0731": "deepseek/deepseek-v4-flash-0731",
    "accounts/fireworks/models/glm-5p2": "z-ai/glm-5.2",
    "accounts/fireworks/models/qwen3p7-plus": "qwen/qwen-3.7-plus",
    "accounts/fireworks/models/minimax-m3": "minimax/minimax-m3",
    "accounts/fireworks/models/minimax-m2p7": "minimax/minimax-m2.7",
    "accounts/fireworks/models/gpt-oss-120b": "openai/gpt-oss-120b",
    "accounts/fireworks/models/gpt-oss-20b": "openai/gpt-oss-20b",
    "accounts/fireworks/models/nemotron-3-ultra-nvfp4": "nvidia/nemotron-3-ultra-550b-a55b",
    # Fast/router variants -> separate canonical rows (own pricing)
    "accounts/fireworks/routers/kimi-k3-fast": "moonshotai/kimi-k3-fast",
    "accounts/fireworks/routers/kimi-k2p7-code-fast": "moonshotai/kimi-k2.7-code-fast",
    "accounts/fireworks/routers/kimi-k2p6-turbo": "moonshotai/kimi-k2.6-highspeed",
    "accounts/fireworks/routers/glm-5p2-fast": "z-ai/glm-5.2-fast",
}

# Display name used when creating a canonical model row for a Fireworks native id.
# Keyed by canonical id -> (name, provider, is_reasoning).
CANONICAL_MODEL_ATTRS = {
    "moonshotai/kimi-k3": ("Kimi K3", "MoonshotAI", False),
    "moonshotai/kimi-k3-fast": ("Kimi K3 Fast", "MoonshotAI", False),
    "moonshotai/kimi-k2.7-code": ("Kimi K2.7 Code", "MoonshotAI", True),
    "moonshotai/kimi-k2.7-code-fast": ("Kimi K2.7 Code Fast", "MoonshotAI", True),
    "moonshotai/kimi-k2.6": ("Kimi K2.6", "MoonshotAI", False),
    "moonshotai/kimi-k2.6-highspeed": ("Kimi K2.6 Highspeed", "MoonshotAI", False),
    "deepseek/deepseek-v4-pro": ("DeepSeek V4 Pro", "DeepSeek", False),
    "deepseek/deepseek-v4-flash": ("DeepSeek V4 Flash", "DeepSeek", False),
    "deepseek/deepseek-v4-flash-0731": ("DeepSeek V4 Flash 0731", "DeepSeek", False),
    "z-ai/glm-5.2": ("GLM 5.2", "Z AI", False),
    "z-ai/glm-5.2-fast": ("GLM 5.2 Fast", "Z AI", False),
    "qwen/qwen-3.7-plus": ("Qwen 3.7 Plus", "Qwen", False),
    "minimax/minimax-m3": ("MiniMax M3", "MiniMax", False),
    "minimax/minimax-m2.7": ("MiniMax M2.7", "MiniMax", False),
    "openai/gpt-oss-120b": ("OpenAI gpt-oss-120b", "OpenAI", False),
    "openai/gpt-oss-20b": ("OpenAI gpt-oss-20b", "OpenAI", False),
    "nvidia/nemotron-3-ultra-550b-a55b": ("NVIDIA Nemotron 3 Ultra", "NVIDIA", False),
}


def _canonical_fireworks_native(mid: str) -> str:
    """Resolve a Fireworks native model id to our canonical model id.

    Returns the canonical id if it existed in FIREWORKS_MODEL_MAP, else the
    native id unchanged (catalog-only / Fireworks-specific models).
    """
    return FIREWORKS_MODEL_MAP.get(mid, mid)


def _parse_docs_pricing(markdown: str) -> dict:
    """Parse the docs markdown table into {display_name: (input, cached, output)}."""
    prices = {}
    table_match = re.search(r"## Text and vision models(.*?)## Other base", markdown, re.S)
    if not table_match:
        raise ValueError("Could not locate 'Text and vision models' table in Fireworks docs")
    for name, _slug, inp, cached, out, _priority in MODEL_ROW_RE.findall(table_match.group(1)):
        prices[name.strip()] = (float(inp), float(cached), float(out))
    return prices


def _pricing_map_from_docs(markdown: str) -> dict:
    """Build {canonical API model id: (input, cached, output)} from docs table.

    Resolves each docs display row to its exact physical Fireworks API model id
    via DOCS_NAME_TO_ID, so Fast/US/router variants land on the correct ID.
    """
    named = _parse_docs_pricing(markdown)
    pricing = {}
    for display, api_id in DOCS_NAME_TO_ID.items():
        if display in named:
            pricing.setdefault(api_id, named[display])
    return pricing


def fetch_fireworks_pricing(api_key: str, timeout: int = 30):
    """Fetch Fireworks catalog + docs pricing. Returns (endpoints, new_models).

    endpoints: list of dicts for insert_endpoints() (priced models).
    new_models: list of dicts for upsert_venice_models() (catalog models).
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Fetching Fireworks AI catalog + pricing...")

    # 1. Catalog from the API (authoritative model list, no prices).
    try:
        r = requests.get(FIREWORKS_CATALOG_API, headers={"Authorization": f"Bearer {api_key}"}, timeout=timeout)
        r.raise_for_status()
        catalog_models = r.json().get("data", [])
        print(f"  Fireworks API catalog: {len(catalog_models)} models")
    except Exception as e:
        print(f"  Fireworks API error: {e}")
        return [], []

    # 2. Pricing from the docs markdown, with static fallback.
    pricing = {}
    try:
        r = requests.get(FIREWORKS_DOCS_PRICING, timeout=timeout)
        r.raise_for_status()
        pricing = _pricing_map_from_docs(r.text)
        if pricing:
            log.info("Live Fireworks docs pricing fetched (%d priced IDs)", len(pricing))
        else:
            pricing = {}
    except Exception as e:
        log.warning("Fireworks docs fetch failed (%s); using static pricing map", e)
        pricing = _static_map()

    endpoints = []
    new_models = []
    seen = set()

    for m in catalog_models:
        mid = m.get("id", "")
        if not mid:
            continue
        canonical_id = _canonical_fireworks_native(mid)

        # Catalog model row always recorded (upsert will no-op if it exists).
        if canonical_id not in seen:
            seen.add(canonical_id)
            # Prefer proper name/provider from the canonical attributes table;
            # fall back to a cleaned native name for Fireworks-specific models.
            attrs = CANONICAL_MODEL_ATTRS.get(canonical_id)
            if attrs:
                disp_name, provider, is_reasoning = attrs
            else:
                disp_name = mid.split("/")[-1].replace("-", " ").replace(".", ".").title()
                provider = "Fireworks"
                is_reasoning = "reasoning" in mid.lower()
            new_models.append({
                "model_id": canonical_id,
                "name": disp_name,
                "provider": provider,
                "context_length": m.get("context_length"),
                "is_reasoning": is_reasoning,
                "modality": "text",
            })

        price = pricing.get(mid)
        if not price:
            continue  # catalog only

        input_price, cached_input, output_price = price
        blended = round((0.4 * input_price) + (0.6 * output_price), 6)
        endpoints.append({
            "endpoint_provider": "Fireworks",
            "model_id": canonical_id,
            "input_price_per_m": round(input_price, 6),
            "output_price_per_m": round(output_price, 6),
            "blended_price_per_m": blended,
            "context_length": m.get("context_length"),
            "source": "fireworks_direct",
            "raw_data": {
                "fireworks_id": mid,
                "owned_by": m.get("owned_by", "fireworks"),
                "hosting_type": "self-hosted",
                "cached_input_per_m": round(cached_input, 6),
                "description": m.get("description", ""),
            },
        })

    print(f"  Fireworks priced endpoints: {len(endpoints)}, catalog models: {len(new_models)}")
    return endpoints, new_models


def _static_map() -> dict:
    """Return the embedded static pricing map (fallback)."""
    return dict(STATIC_PRICING)


if __name__ == "__main__":
    import os
    key = os.environ.get("FIREWORKS_API_KEY", "")
    if not key:
        # read from env file
        for line in open(os.path.expanduser("~/.hermes/.env")):
            if line.startswith("FIREWORKS_API_KEY="):
                key = line.strip().split("=", 1)[1]
                break
    ep, nm = fetch_fireworks_pricing(key)
    print("\nPriced endpoints:")
    for e in sorted(ep, key=lambda x: x["model_id"]):
        print(f"  {e['model_id']}: ${e['input_price_per_m']} in / ${e['output_price_per_m']} out")
    print(f"\nCatalog only ({len(nm)}):")
    for m in nm:
        mid = m["model_id"]
        if not any(mid == e["model_id"] for e in ep):
            print(f"  {mid}")