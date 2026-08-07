#!/usr/bin/env python3
"""
InferenceIndexer.ai - Data Pipeline
Fetches model pricing from OpenRouter, normalizes, calculates SIT, stores to Supabase.

Usage:
  python3 pipeline.py              # Full run: fetch + store + calculate SIT
  python3 pipeline.py --fetch-only # Just fetch and print, don't store
  python3 pipeline.py --sit-only    # Just calculate SIT from existing data

Requirements:
  pip install psycopg2-binary requests python-dotenv
"""

import os
import sys
import json
import time
import math
import argparse
import subprocess
import requests
from datetime import datetime, timezone, date
from pathlib import Path

# Try psycopg2 for Supabase, fall back to just printing
try:
    import psycopg2
    HAS_DB = True
except ImportError:
    HAS_DB = False

# ============================================
# CONFIG
# ============================================

OPENROUTER_API = "https://openrouter.ai/api/v1/models"
OPENROUTER_ENDPOINTS_API = "https://openrouter.ai/api/v1/models/{}/endpoints"
SOURCE_NAME = "openrouter"
VENICE_API = "https://api.venice.ai/api/v1/models"
DEEPINFRA_API = "https://api.deepinfra.com/v1/openai/models"
NOVITA_API = "https://api.novita.ai/v3/openai/models"
# Novita prices are expressed as (price per 1M tokens) * 10000. Divide by 10000 to get $/M.
NOVITA_PRICE_DIVISOR = 10000
# No-auth direct API providers
SAMABANOVA_API = "https://api.sambanova.ai/v1/models"
INFERENCE_NET_API = "https://api.inference.net/v1/models"
JINA_API = "https://api.jina.ai/v1/models"
# Auth-required providers (API keys loaded from env or Jentic One)
TOGETHER_API = "https://api.together.xyz/v1/models"
GROQ_API = "https://api.groq.com/openai/v1/models"
FIREWORKS_API = "https://api.fireworks.ai/inference/v1/models"
CEREBRAS_API = "https://api.cerebras.ai/v1/models"
MISTRAL_API = "https://api.mistral.ai/v1/models"
SILICONFLOW_API = "https://api.siliconflow.cn/v1/models"
PERPLEXITY_API = "https://api.perplexity.ai/v1/models"
OPENAI_DIRECT_API = "https://api.openai.com/v1/models"
ANTHROPIC_DIRECT_API = "https://api.anthropic.com/v1/models"
TENSORX_API = "https://api.tensorx.ai/v1/models"
HYPERBOLIC_API = "https://api.hyperbolic.xyz/v1/models"
# Additional no-auth providers
AIML_API = "https://api.aimlapi.com/v1/models"
# Additional auth-required providers
DEEPSEEK_DIRECT_API = "https://api.deepseek.com/v1/models"
MOONSHOT_DIRECT_API = "https://api.moonshot.cn/v1/models"
# SambaNova prices are per-token (like OpenRouter). Multiply by 1M for $/M.
# Jina prices are per-token. Multiply by 1M for $/M.
BLENDED_INPUT_WEIGHT = 0.4
BLENDED_OUTPUT_WEIGHT = 0.6

# AA Index tier thresholds
TIER_FRONTIER = 50
TIER_STANDARD = 30
TIER_BUDGET = 15

# Quality gate: models below this AA score are excluded from the composite
# GPT-4-Turbo (Jan 2024) scored ~35-40 on AA Intelligence Index v4.1
GPT4_TURBO_AA_REFERENCE = 40.0
QUALITY_FLOOR = 35.0

# Reasoning token multipliers (kept for backwards compatibility / fallback)
# These are no longer used in the SIT formula but stored for reference.
REASONING_MULTIPLIERS = {
    "frontier": 4.0,
    "standard": 3.0,
    "budget": 2.5,
    "micro": 2.0,
}
NON_REASONING_MULTIPLIER = 1.0

# Base date for index rebaselining
BASE_DATE = date(2026, 8, 3)
BASE_VALUE = 1000.0

# Anomaly threshold
ANOMALY_THRESHOLD = 0.50  # 50% price change in one fetch

# ============================================
# TIER ASSIGNMENT
# ============================================

def assign_tier(aa_score, blended_price=None):
    """Assign a quality tier based on AA Intelligence Index score.
    
    Primary: AA score thresholds (Frontier >= 50, Standard >= 30, Budget >= 15).
    Fallback: If no AA score, use blended price as a proxy:
      - > $10/M  → frontier (expensive models are almost always high quality)
      - > $1/M   → standard
      - > $0.15/M → budget
      - else     → micro
    """
    if aa_score is not None:
        if aa_score >= TIER_FRONTIER:
            return "frontier"
        if aa_score >= TIER_STANDARD:
            return "standard"
        if aa_score >= TIER_BUDGET:
            return "budget"
        return "micro"
    
    # Price-based fallback for models without AA scores
    if blended_price is not None and blended_price > 0:
        if blended_price > 10.0:
            return "frontier"
        if blended_price > 1.0:
            return "standard"
        if blended_price > 0.15:
            return "budget"
    return "micro"

def get_reasoning_multiplier(tier, is_reasoning):
    """Get the reasoning token multiplier for a model.
    
    Returns 1.0 for non-reasoning models.
    For reasoning models, returns a tier-based estimate of how many
    extra tokens the model generates (thinking + answer) relative to
    just the answer.
    """
    if not is_reasoning:
        return NON_REASONING_MULTIPLIER
    return REASONING_MULTIPLIERS.get(tier, NON_REASONING_MULTIPLIER)

def calculate_sit_adjusted_price(blended_price, reasoning_multiplier, aa_score):
    """Calculate the quality-adjusted price (Cost per IQ).
    
    Quality-Adjusted Price = Blended Price * (GPT-4-Turbo Reference / AA Intelligence Score)
    
    This gives the cost of producing GPT-4-Turbo-equivalent inference tokens.
    A model scoring higher than GPT-4-Turbo will have a lower adjusted price
    (cheaper per unit of intelligence). Lower is better.
    
    For models without an AA score, returns None.
    """
    if not aa_score or aa_score <= 0:
        return None
    return round(blended_price * (GPT4_TURBO_AA_REFERENCE / aa_score), 6)

# ============================================
# FETCH FROM OPENROUTER
# ============================================

def fetch_openrouter():
    """Fetch all models from OpenRouter API."""
    print(f"[{datetime.now(timezone.utc).isoformat()}] Fetching from OpenRouter...")
    
    headers = {}
    # OpenRouter doesn't require auth for model list, but include if available
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    if openrouter_key:
        headers["Authorization"] = f"Bearer {openrouter_key}"
    
    resp = requests.get(OPENROUTER_API, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    models = data.get("data", [])
    
    print(f"  Fetched {len(models)} models total")
    return models

def fetch_model_endpoints(model_id):
    """Fetch all provider endpoints for a single model from OpenRouter.
    Returns a list of endpoint dicts with provider name and pricing."""
    url = OPENROUTER_ENDPOINTS_API.format(model_id)
    headers = {}
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    if openrouter_key:
        headers["Authorization"] = f"Bearer {openrouter_key}"
    
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        # OpenRouter returns {"data": {"endpoints": [...]}}
        if isinstance(data.get("data"), dict):
            endpoints = data["data"].get("endpoints", [])
        elif isinstance(data.get("data"), list):
            endpoints = data["data"]
        else:
            endpoints = data.get("endpoints", [])
        return endpoints
    except Exception as e:
        print(f"  WARN: Failed to fetch endpoints for {model_id}: {e}")
        return []

def compute_median(prices):
    """Compute the median of a list of numbers."""
    if not prices:
        return 0.0
    sorted_prices = sorted(prices)
    n = len(sorted_prices)
    if n == 1:
        return sorted_prices[0]
    mid = n // 2
    if n % 2 == 0:
        return round((sorted_prices[mid - 1] + sorted_prices[mid]) / 2, 6)
    return round(sorted_prices[mid], 6)

def normalize_endpoints(model_id, raw_endpoints):
    """Normalize endpoint data from OpenRouter into per-provider price records."""
    results = []
    for ep in raw_endpoints:
        pricing = ep.get("pricing", {})
        prompt_str = pricing.get("prompt", "0")
        completion_str = pricing.get("completion", "0")
        
        try:
            prompt_per_token = float(prompt_str)
            completion_per_token = float(completion_str)
        except (ValueError, TypeError):
            continue
        
        if prompt_per_token <= 0 and completion_per_token <= 0:
            continue
        
        input_price = round(prompt_per_token * 1_000_000, 6)
        output_price = round(completion_per_token * 1_000_000, 6)
        blended = round((BLENDED_INPUT_WEIGHT * input_price) + (BLENDED_OUTPUT_WEIGHT * output_price), 6)
        
        provider_name = ep.get("provider_name", ep.get("name", "unknown"))
        # Clean up provider name (take first part before |)
        if "|" in provider_name:
            provider_name = provider_name.split("|")[0].strip()
        
        results.append({
            "endpoint_provider": provider_name,
            "input_price_per_m": input_price,
            "output_price_per_m": output_price,
            "blended_price_per_m": blended,
            "context_length": ep.get("context_length"),
            "raw_data": ep,
        })
    return results


# ============================================
# VENICE DIRECT API CONNECTOR
# ============================================

# Map Venice model IDs to our model IDs (provider/model format)
# Venice uses flat IDs like "kimi-k3" -> we need "moonshotai/kimi-k3"
VENICE_MODEL_MAP = {
    # DeepSeek
    "deepseek-v3.2": "deepseek/deepseek-v3.2",
    "deepseek-v4-flash": "deepseek/deepseek-v4-flash",
    "deepseek-v4-flash-0731": "deepseek/deepseek-v4-flash-0731",
    "deepseek-v4-pro": "deepseek/deepseek-v4-pro",
    "e2ee-deepseek-v4-flash": "deepseek/deepseek-v4-flash",  # E2EE variant, same model
    # Google
    "gemini-3-1-pro-preview": "google/gemini-3.1-pro-preview",
    "gemini-3-5-flash": "google/gemini-3.5-flash",
    "gemini-3-5-flash-lite": "google/gemini-3.5-flash-lite",
    "gemini-3-6-flash": "google/gemini-3.6-flash",
    "gemini-3-flash-preview": "google/gemini-3-flash-preview",
    "google-gemma-3-27b-it": "google/gemma-3-27b-it",
    "google-gemma-4-26b-a4b-it": "google/gemma-4-26b-a4b-it",
    "google-gemma-4-31b-it": "google/gemma-4-31b-it",
    "gemma-4-uncensored": "google/gemma-4-uncensored",
    "e2ee-gemma-3-27b-p": "google/gemma-3-27b-it",
    "e2ee-gemma-4-26b-a4b-uncensored-p": "google/gemma-4-26b-a4b-it",
    "e2ee-gemma-4-31b": "google/gemma-4-31b-it",
    # GLM / Z.AI
    "z-ai-glm-5-turbo": "z-ai/glm-5-turbo",
    "z-ai-glm-5v-turbo": "z-ai/glm-5v-turbo",
    "zai-org-glm-4.6": "z-ai/glm-4.6",
    "zai-org-glm-4.7": "z-ai/glm-4.7",
    "zai-org-glm-4.7-flash": "z-ai/glm-4.7-flash",
    "zai-org-glm-5": "z-ai/glm-5",
    "zai-org-glm-5-1": "z-ai/glm-5.1",
    "zai-org-glm-5-2": "z-ai/glm-5.2",
    "e2ee-glm-5-1": "z-ai/glm-5.1",
    "e2ee-glm-5-2-p": "z-ai/glm-5.2",
    "olafangensan-glm-4.7-flash-heretic": "z-ai/glm-4.7-flash",
    # Anthropic / Claude
    "claude-fable-5": "anthropic/claude-fable-5",
    "claude-opus-4-5": "anthropic/claude-opus-4.5",
    "claude-opus-4-6": "anthropic/claude-opus-4.6",
    "claude-opus-4-7": "anthropic/claude-opus-4.7",
    "claude-opus-4-8": "anthropic/claude-opus-4.8",
    "claude-opus-4-8-fast": "anthropic/claude-opus-4.8-fast",
    "claude-opus-5": "anthropic/claude-opus-5",
    "claude-opus-5-fast": "anthropic/claude-opus-5-fast",
    "claude-sonnet-4-5": "anthropic/claude-sonnet-4.5",
    "claude-sonnet-4-6": "anthropic/claude-sonnet-4.6",
    "claude-sonnet-5": "anthropic/claude-sonnet-5",
    # OpenAI / GPT
    "openai-gpt-4o-2024-11-20": "openai/gpt-4o-2024-11-20",
    "openai-gpt-4o-mini-2024-07-18": "openai/gpt-4o-mini-2024-07-18",
    "openai-gpt-52": "openai/gpt-5.2",
    "openai-gpt-52-codex": "openai/gpt-5.2-codex",
    "openai-gpt-53-codex": "openai/gpt-5.3-codex",
    "openai-gpt-54": "openai/gpt-5.4",
    "openai-gpt-54-mini": "openai/gpt-5.4-mini",
    "openai-gpt-54-pro": "openai/gpt-5.4-pro",
    "openai-gpt-55": "openai/gpt-5.5",
    "openai-gpt-55-pro": "openai/gpt-5.5-pro",
    "openai-gpt-56-luna": "openai/gpt-5.6-luna",
    "openai-gpt-56-luna-pro": "openai/gpt-5.6-luna-pro",
    "openai-gpt-56-sol": "openai/gpt-5.6-sol",
    "openai-gpt-56-sol-pro": "openai/gpt-5.6-sol-pro",
    "openai-gpt-56-terra": "openai/gpt-5.6-terra",
    "openai-gpt-56-terra-pro": "openai/gpt-5.6-terra-pro",
    "openai-gpt-oss-120b": "openai/gpt-oss-120b",
    "e2ee-gpt-oss-120b-p": "openai/gpt-oss-120b",
    "e2ee-gpt-oss-20b-p": "openai/gpt-oss-20b",
    # xAI / Grok
    "grok-4-3": "xai/grok-4.3",
    "grok-4-5": "xai/grok-4.5",
    "grok-4-20": "xai/grok-4.20",
    "grok-4-20-multi-agent": "xai/grok-4.20-multi-agent",
    "grok-build-0-1": "xai/grok-build-0.1",
    # Moonshot / Kimi
    "kimi-k2-5": "moonshotai/kimi-k2.5",
    "kimi-k2-6": "moonshotai/kimi-k2.6",
    "kimi-k2-7-code": "moonshotai/kimi-k2.7-code",
    "kimi-k3": "moonshotai/kimi-k3",
    "kimi-k3-fast-api": "moonshotai/kimi-k3-fast",
    # Qwen
    "qwen3-235b-a22b-instruct-2507": "qwen/qwen3-235b-a22b-2507",
    "qwen3-235b-a22b-thinking-2507": "qwen/qwen3-235b-a22b-thinking-2507",
    "qwen3-5-35b-a3b": "qwen/qwen3.5-35b-a3b",
    "qwen3-5-397b-a17b": "qwen/qwen3.5-397b-a17b",
    "qwen3-5-9b": "qwen/qwen3.5-9b",
    "qwen3-6-27b": "qwen/qwen3.6-27b",
    "qwen3-6-35b-a3b": "qwen/qwen3.6-35b-a3b",
    "qwen3-coder-480b-a35b-instruct-turbo": "qwen/qwen3-coder",
    "qwen3-next-80b": "qwen/qwen3-next-80b",
    "qwen3-vl-235b-a22b": "qwen/qwen3-vl-235b-a22b-instruct",
    "qwen-3-6-plus": "qwen/qwen-3.6-plus",
    "qwen-3-7-max": "qwen/qwen-3.7-max",
    "qwen-3-7-plus": "qwen/qwen-3.7-plus",
    "qwen-3-8-max": "qwen/qwen-3.8-max",
    "e2ee-qwen3-6-27b": "qwen/qwen3.6-27b",
    "e2ee-qwen3-6-35b-a3b": "qwen/qwen3.6-35b-a3b",
    "e2ee-qwen3-6-35b-a3b-uncensored-p": "qwen/qwen3.6-35b-a3b",
    "e2ee-qwen3-vl-30b-a3b-p": "qwen/qwen3-vl-235b-a22b-instruct",
    "e2ee-qwen-2-5-7b-p": "qwen/qwen2.5-7b",
    # Mistral
    "mistral-small-2603": "mistralai/mistral-small-2603",
    "mistral-small-3-2-24b-instruct": "mistralai/mistral-small-3.2-24b-instruct",
    # Minimax
    "minimax-m25": "minimax/minimax-m2.5",
    "minimax-m27": "minimax/minimax-m2.7",
    "minimax-m3-preview": "minimax/minimax-m3",
    # Nvidia
    "nvidia-nemotron-3-nano-30b-a3b": "nvidia/nemotron-3-nano-30b-a3b",
    "nvidia-nemotron-3-ultra-550b-a55b": "nvidia/nemotron-3-ultra-550b-a55b",
    # Xiaomi
    "xiaomi-mimo-v2-5": "xiaomi/mimo-v2.5",
    # Meta
    "llama-3.2-3b": "meta-llama/llama-3.2-3b",
    "llama-3.3-70b": "meta-llama/llama-3.3-70b",
    "hermes-3-llama-3.1-405b": "nousresearch/hermes-3-llama-3.1-405b",
    # Cognitivecomputations
    "cognitivecomputations/dolphin-mistral-24b-venice-edition": "cognitivecomputations/dolphin-mistral-24b-venice-edition",
    # Aion Labs
    "aion-labs-aion-3-0": "aionlabs/aion-3.0",
    "aion-labs-aion-3-0-mini": "aionlabs/aion-3.0-mini",
    # Venice originals (no upstream owner)
    "venice-uncensored-1-2": "venice/uncensored-1.2",
    "venice-uncensored-role-play": "venice/uncensored-role-play",
    # Others
    "mercury-2": "inception/mercury-2",
    "inkling": "perceptron/inkling",
    "seed-2-1-turbo": "bytedance-seed/seed-2.1-turbo",
}


def fetch_venice_direct():
    """Fetch model catalog and pricing directly from Venice's API.
    
    Returns list of endpoint dicts ready for insert_endpoints().
    This is a direct connector that bypasses OpenRouter entirely.
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Fetching Venice direct API...")
    
    try:
        resp = requests.get(VENICE_API, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        models = data.get("data", data) if isinstance(data, dict) else data
        print(f"  Venice API returned {len(models)} models")
    except Exception as e:
        print(f"  ERROR fetching Venice API: {e}")
        return []
    
    endpoints = []
    new_models = []
    mapped = 0
    unmapped = 0
    e2ee_count = 0
    
    for m in models:
        venice_id = m.get("id", "")
        spec = m.get("model_spec", {})
        pricing = spec.get("pricing", {})
        
        input_usd = pricing.get("input", {}).get("usd")
        output_usd = pricing.get("output", {}).get("usd")
        
        if input_usd is None or output_usd is None:
            continue
        if input_usd <= 0 and output_usd <= 0:
            continue
        
        # Skip E2EE variants (they're the same model with encryption)
        if venice_id.startswith("e2ee-"):
            e2ee_count += 1
            # Map to the underlying model
        
        # Map Venice ID to our model ID
        our_id = VENICE_MODEL_MAP.get(venice_id)
        if not our_id:
            # Try to auto-map by pattern
            unmapped += 1
            continue
        
        mapped += 1
        input_price = round(input_usd, 6)
        output_price = round(output_usd, 6)
        blended = round((BLENDED_INPUT_WEIGHT * input_price) + (BLENDED_OUTPUT_WEIGHT * output_price), 6)
        
        caps = spec.get("capabilities", {})
        is_reasoning = caps.get("supportsReasoning", False)
        
        endpoints.append({
            "endpoint_provider": "Venice",
            "model_id": our_id,
            "input_price_per_m": input_price,
            "output_price_per_m": output_price,
            "blended_price_per_m": blended,
            "context_length": m.get("context_length") or spec.get("availableContextTokens"),
            "source": "venice_direct",
            "raw_data": {
                "venice_id": venice_id,
                "venice_name": spec.get("name", ""),
                "owned_by": m.get("owned_by", "venice.ai"),
                "privacy": spec.get("privacy", ""),
                "hosting_type": "self-hosted" if spec.get("privacy") == "private" else "proxied",
                "quantization": caps.get("quantization", ""),
                "capabilities": caps,
                "max_completion_tokens": spec.get("maxCompletionTokens"),
                "offline": spec.get("offline", False),
                "cache_input_price": pricing.get("cache_input", {}).get("usd"),
            },
        })
        
        # Track new models we may need to upsert
        new_models.append({
            "model_id": our_id,
            "name": spec.get("name", venice_id),
            "provider": our_id.split("/")[0] if "/" in our_id else "venice",
            "context_length": m.get("context_length") or spec.get("availableContextTokens"),
            "is_reasoning": is_reasoning,
            "modality": "text" if caps.get("supportsVision", False) else "text",
            "venice_description": spec.get("description", ""),
        })
    
    print(f"  Mapped: {mapped}, Unmapped: {unmapped}, E2EE variants skipped: {e2ee_count}")
    if unmapped > 0:
        # Log unmapped IDs for debugging
        unmapped_ids = [m.get("id", "") for m in models if m.get("id") and m.get("id") not in VENICE_MODEL_MAP and not m.get("id", "").startswith("e2ee-")]
        if unmapped_ids:
            print(f"  Unmapped IDs: {unmapped_ids[:10]}")
    
    return endpoints, new_models


def upsert_venice_models(conn, new_models, existing_priced):
    """Upsert models discovered via Venice direct API that don't exist in our DB yet."""
    cur = conn.cursor()
    
    # Get all existing model IDs
    cur.execute("SELECT id FROM models")
    existing_ids = {row[0] for row in cur.fetchall()}
    
    # Also check models we're about to upsert from OpenRouter
    for m in existing_priced:
        existing_ids.add(m["model_id"])
    
    count = 0
    for m in new_models:
        if m["model_id"] in existing_ids:
            continue
        
        # Determine tier from price (fallback)
        blended = m.get("blended_price_per_m", 0)
        if not blended:
            # Use Venice pricing
            for ep in new_models:
                if ep["model_id"] == m["model_id"]:
                    blended = ep.get("blended_price_per_m", 0)
                    break
        
        if blended > TIER_FRONTIER:
            tier = "frontier"
        elif blended > TIER_STANDARD:
            tier = "standard"
        elif blended > TIER_BUDGET:
            tier = "budget"
        else:
            tier = "micro"
        
        # Clean up provider name
        provider = m["provider"]
        provider = provider.replace("-", " ").replace("_", " ").title()
        provider_map = {
            "Openai": "OpenAI",
            "X Ai": "xAI",
            "Z.Ai": "Z.ai",
            "Meta Llama": "Meta Llama",
            "Bytedance Seed": "Bytedance Seed",
        }
        provider = provider_map.get(provider, provider)
        
        cur.execute("""
            INSERT INTO models (id, name, provider, tier, context_length, is_reasoning, modality, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE)
            ON CONFLICT (id) DO NOTHING
        """, (
            m["model_id"],
            m["name"],
            provider,
            tier,
            m.get("context_length"),
            m.get("is_reasoning", False),
            m.get("modality", "text"),
        ))
        if cur.rowcount > 0:
            count += 1
            existing_ids.add(m["model_id"])
    
    conn.commit()
    cur.close()
    if count > 0:
        print(f"  Upserted {count} new models from Venice direct API")
    return count


# ============================================
# DEEPINFRA DIRECT API CONNECTOR
# ============================================

def fetch_deepinfra_direct():
    """Fetch model catalog and pricing directly from DeepInfra's API.
    
    Returns (endpoints, new_models) like fetch_venice_direct().
    No auth required - public API.
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Fetching DeepInfra direct API...")
    
    try:
        resp = requests.get(DEEPINFRA_API, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        models = data.get("data", [])
        print(f"  DeepInfra API returned {len(models)} models")
    except Exception as e:
        print(f"  ERROR fetching DeepInfra API: {e}")
        return [], []
    
    endpoints = []
    new_models = []
    skipped = 0
    
    for m in models:
        model_id = m.get("id", "")
        if not model_id:
            continue
        
        meta = m.get("metadata", {})
        pricing = meta.get("pricing", {})
        tags = meta.get("tags", [])
        
        # Skip image/video/audio generation models
        if "image-gen" in tags or "video-gen" in tags or "audio-gen" in tags:
            skipped += 1
            continue
        
        # Extract per-token pricing (DeepInfra prices are already per-million)
        input_price = pricing.get("input_tokens")
        output_price = pricing.get("output_tokens")
        
        if input_price is None or output_price is None:
            skipped += 1
            continue
        if input_price <= 0 and output_price <= 0:
            skipped += 1
            continue
        
        input_price = round(input_price, 6)
        output_price = round(output_price, 6)
        blended = round((BLENDED_INPUT_WEIGHT * input_price) + (BLENDED_OUTPUT_WEIGHT * output_price), 6)
        
        # DeepInfra model IDs already match our format (provider/model)
        # But some need normalization to match OpenRouter IDs
        deepinfra_id = model_id
        
        endpoints.append({
            "endpoint_provider": "DeepInfra",
            "model_id": deepinfra_id,
            "input_price_per_m": input_price,
            "output_price_per_m": output_price,
            "blended_price_per_m": blended,
            "context_length": meta.get("context_length"),
            "source": "deepinfra_direct",
            "raw_data": {
                "deepinfra_id": model_id,
                "owned_by": m.get("owned_by", "deepinfra"),
                "hosting_type": "self-hosted",
                "cache_read_price": pricing.get("cache_read_tokens"),
                "tags": tags,
                "description": meta.get("description", ""),
                "max_tokens": meta.get("max_tokens"),
            },
        })
        
        new_models.append({
            "model_id": deepinfra_id,
            "name": model_id.split("/")[-1].replace("-", " "),
            "provider": model_id.split("/")[0] if "/" in model_id else "deepinfra",
            "context_length": meta.get("context_length"),
            "is_reasoning": "reasoning" in tags or "thinking" in tags,
            "modality": "text",
        })
    
    print(f"  Text models with pricing: {len(endpoints)}, Skipped: {skipped}")
    return endpoints, new_models


# ============================================
# NOVITA DIRECT API CONNECTOR
# ============================================

def fetch_novita_direct():
    """Fetch model catalog and pricing directly from Novita's API.
    
    Returns (endpoints, new_models).
    No auth required - public endpoint.
    Novita prices are (price per 1M tokens) * 10000; divide by 10000 for $/M.
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Fetching Novita direct API...")
    
    try:
        resp = requests.get(NOVITA_API, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        models = data if isinstance(data, list) else data.get("data", [])
        print(f"  Novita API returned {len(models)} models")
    except Exception as e:
        print(f"  ERROR fetching Novita API: {e}")
        return [], []
    
    endpoints = []
    new_models = []
    skipped = 0
    
    for m in models:
        model_id = m.get("id", "")
        if not model_id:
            continue
        
        # Only active models (status==1). Skip status 4 (likely suspended/variants).
        if m.get("status") not in (1, None):
            skipped += 1
            continue
        
        # Only chat/completion models
        if m.get("model_type") not in ("chat", "completion", None):
            skipped += 1
            continue
        
        raw_in = m.get("input_token_price_per_m")
        raw_out = m.get("output_token_price_per_m")
        if raw_in is None or raw_out is None:
            skipped += 1
            continue
        if raw_in <= 0 and raw_out <= 0:
            skipped += 1
            continue
        
        input_price = round(raw_in / NOVITA_PRICE_DIVISOR, 6)
        output_price = round(raw_out / NOVITA_PRICE_DIVISOR, 6)
        blended = round((BLENDED_INPUT_WEIGHT * input_price) + (BLENDED_OUTPUT_WEIGHT * output_price), 6)
        
        features = m.get("features", []) or []
        is_reasoning = "reasoning" in features
        is_vision = "image" in (m.get("input_modalities", []) or [])
        
        endpoints.append({
            "endpoint_provider": "Novita",
            "model_id": model_id,
            "input_price_per_m": input_price,
            "output_price_per_m": output_price,
            "blended_price_per_m": blended,
            "context_length": m.get("context_size"),
            "source": "novita_direct",
            "raw_data": {
                "novita_id": model_id,
                "owned_by": m.get("owned_by", "novita"),
                "hosting_type": "self-hosted",
                "display_name": m.get("display_name", ""),
                "features": features,
                "context_size": m.get("context_size"),
                "cache_input_price": (m.get("pricing") or {}).get("input_cache_read", {}).get("price_per_m"),
                "description": m.get("description", ""),
            },
        })
        
        new_models.append({
            "model_id": model_id,
            "name": m.get("display_name") or model_id.split("/")[-1].replace("-", " "),
            "provider": model_id.split("/")[0] if "/" in model_id else "novita",
            "context_length": m.get("context_size"),
            "is_reasoning": is_reasoning,
            "modality": "vision" if is_vision else "text",
        })
    
    print(f"  Chat models with pricing: {len(endpoints)}, Skipped: {skipped}")
    return endpoints, new_models


# ============================================
# CREDENTIAL LOADER (Jentic One / env / file)
# ============================================

# Local credential cache file (used if Jentic One not available)
CREDENTIALS_FILE = os.path.expanduser("~/.hermes/.env")
# Jentic One credential store (if installed)
_JENTIC_CREDENTIALS = None


def _load_credentials_file():
    """Load credentials from ~/.hermes/.env file directly (no shell expansion)."""
    creds = {}
    try:
        with open(CREDENTIALS_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    creds[key] = val
    except FileNotFoundError:
        pass
    return creds


def get_provider_api_key(provider_name):
    """Get an API key for a provider.

    Tries in order:
    1. Environment variable (PROVIDER_API_KEY)
    2. Credentials file (~/.hermes/.env)
    3. Jentic One (if installed)
    """
    # Map provider names to env var names
    env_map = {
        "together": "TOGETHER_API_KEY",
        "groq": "GROQ_API_KEY",
        "fireworks": "FIREWORKS_API_KEY",
        "cerebras": "CEREBRAS_API_KEY",
        "mistral": "MISTRAL_API_KEY",
        "siliconflow": "SILICONFLOW_API_KEY",
        "perplexity": "PERPLEXITY_API_KEY",
        "openai_direct": "OPENAI_API_KEY",
        "anthropic_direct": "ANTHROPIC_API_KEY",
        "hyperbolic": "HYPERBOLIC_API_KEY",
        "deepseek_direct": "DEEPSEEK_API_KEY",
        "moonshot_direct": "MOONSHOT_API_KEY",
        "tensorx": "TENSORX_API_KEY",
    }
    env_var = env_map.get(provider_name.lower(), f"{provider_name.upper()}_API_KEY")

    # 1. Environment variable
    val = os.environ.get(env_var)
    if val:
        return val

    # 2. Credentials file
    creds = _load_credentials_file()
    if env_var in creds:
        return creds[env_var]

    # 3. Jentic One (if installed)
    try:
        result = subprocess.run(
            ["jenticctl", "credential", "get", "--name", env_var],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return None


def fetch_with_auth(url, provider_name, timeout=30):
    """Fetch a provider API with auth if available, without if not."""
    api_key = get_provider_api_key(provider_name)
    headers = {}
    if api_key:
        # Different providers use different auth headers
        if provider_name == "anthropic_direct":
            headers["x-api-key"] = api_key
            headers["anthropic-version"] = "2023-06-01"
        else:
            headers["Authorization"] = f"Bearer {api_key}"

    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 401:
            print(f"  {provider_name}: No API key (auth required). Skipping.")
        else:
            print(f"  {provider_name}: HTTP error: {e}")
        return None
    except Exception as e:
        print(f"  {provider_name}: Error: {e}")
        return None


# ============================================
# SAMBANOVA DIRECT API CONNECTOR
# ============================================

def fetch_sambanova_direct():
    """Fetch model catalog and pricing directly from SambaNova's API.

    Returns (endpoints, new_models).
    No auth required - public API.
    SambaNova pricing is per-token (like OpenRouter). Multiply by 1M for $/M.
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Fetching SambaNova direct API...")

    try:
        resp = requests.get(SAMABANOVA_API, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        models = data.get("data", [])
        print(f"  SambaNova API returned {len(models)} models")
    except Exception as e:
        print(f"  ERROR fetching SambaNova API: {e}")
        return [], []

    endpoints = []
    new_models = []
    skipped = 0

    for m in models:
        model_id = m.get("id", "")
        if not model_id:
            continue

        pricing = m.get("pricing", {})
        prompt_str = pricing.get("prompt", "0")
        completion_str = pricing.get("completion", "0")

        try:
            input_per_token = float(prompt_str)
            output_per_token = float(completion_str)
        except (ValueError, TypeError):
            skipped += 1
            continue

        if input_per_token <= 0 and output_per_token <= 0:
            skipped += 1
            continue

        # Convert per-token to per-million ($/M)
        input_price = round(input_per_token * 1_000_000, 6)
        output_price = round(output_per_token * 1_000_000, 6)
        blended = round((BLENDED_INPUT_WEIGHT * input_price) + (BLENDED_OUTPUT_WEIGHT * output_price), 6)

        # SambaNova model IDs don't have provider prefix; add one
        canonical_id = f"sambanova/{model_id}"

        endpoints.append({
            "endpoint_provider": "SambaNova",
            "model_id": canonical_id,
            "input_price_per_m": input_price,
            "output_price_per_m": output_price,
            "blended_price_per_m": blended,
            "context_length": m.get("context_length"),
            "source": "sambanova_direct",
            "raw_data": {
                "sambanova_id": model_id,
                "owned_by": m.get("owned_by", "sambanova"),
                "hosting_type": "self-hosted",
                "max_completion_tokens": m.get("max_completion_tokens"),
                "sn_metadata": m.get("sn_metadata", {}),
            },
        })

        new_models.append({
            "model_id": canonical_id,
            "name": model_id.replace("-", " "),
            "provider": "SambaNova",
            "context_length": m.get("context_length"),
            "is_reasoning": "deepseek" in model_id.lower() or "reasoning" in model_id.lower(),
            "modality": "text",
        })

    print(f"  Models with pricing: {len(endpoints)}, Skipped: {skipped}")
    return endpoints, new_models


# ============================================
# INFERENCE.NET DIRECT API CONNECTOR
# ============================================

def fetch_inference_net_direct():
    """Fetch model catalog directly from Inference.net's API.

    Returns (endpoints, new_models).
    No auth required - public API.
    Inference.net does NOT expose pricing in the models endpoint.
    We store the model catalog for comparison; pricing comes from other sources.
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Fetching Inference.net direct API...")

    try:
        resp = requests.get(INFERENCE_NET_API, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        models = data.get("data", [])
        print(f"  Inference.net API returned {len(models)} models")
    except Exception as e:
        print(f"  ERROR fetching Inference.net API: {e}")
        return [], []

    endpoints = []
    new_models = []
    skipped = 0

    for m in models:
        model_id = m.get("id", "")
        if not model_id:
            continue

        # Inference.net does not expose pricing in the models endpoint
        # We record it as a known provider but without price data
        # Pricing will be inferred from OpenRouter if available
        canonical_id = f"inference-net/{model_id}"

        # Check if this is a text model (skip non-text)
        if any(skip in model_id.lower() for skip in ["whisper", "tts", "embed", "image", "dall"]):
            skipped += 1
            continue

        new_models.append({
            "model_id": canonical_id,
            "name": model_id.replace("-", " "),
            "provider": "Inference.net",
            "context_length": None,  # Not exposed
            "is_reasoning": False,
            "modality": "text",
        })

    print(f"  Catalog models: {len(new_models)}, Skipped: {skipped}")
    return endpoints, new_models


# ============================================
# JINA DIRECT API CONNECTOR
# ============================================

def fetch_jina_direct():
    """Fetch model catalog and pricing directly from Jina AI's API.

    Returns (endpoints, new_models).
    No auth required - public API.
    Jina pricing is per-token. Multiply by 1M for $/M.
    Most Jina models are embeddings/rerankers (output price = 0).
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Fetching Jina direct API...")

    try:
        resp = requests.get(JINA_API, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        models = data.get("data", [])
        print(f"  Jina API returned {len(models)} models")
    except Exception as e:
        print(f"  ERROR fetching Jina API: {e}")
        return [], []

    endpoints = []
    new_models = []
    skipped = 0

    for m in models:
        model_id = m.get("id", "")
        if not model_id:
            continue

        pricing = m.get("pricing", {})
        prompt_str = pricing.get("prompt", "0")
        completion_str = pricing.get("completion", "0")

        try:
            input_per_token = float(prompt_str)
            output_per_token = float(completion_str)
        except (ValueError, TypeError):
            skipped += 1
            continue

        # For embeddings/rerankers, output price is 0 - that's expected
        # Convert per-token to per-million ($/M)
        input_price = round(input_per_token * 1_000_000, 6)
        output_price = round(output_per_token * 1_000_000, 6)
        blended = round((BLENDED_INPUT_WEIGHT * input_price) + (BLENDED_OUTPUT_WEIGHT * output_price), 6)

        # Determine modality from input/output modalities
        input_modalities = m.get("input_modalities", ["text"])
        output_modalities = m.get("output_modalities", ["text"])
        if "image" in input_modalities:
            modality = "vision"
        elif "embed" in model_id.lower() or "colbert" in model_id.lower():
            modality = "embedding"
        elif "reranker" in model_id.lower():
            modality = "reranker"
        elif "reader" in model_id.lower():
            modality = "reader"
        else:
            modality = "text"

        endpoints.append({
            "endpoint_provider": "Jina",
            "model_id": model_id,
            "input_price_per_m": input_price,
            "output_price_per_m": output_price,
            "blended_price_per_m": blended,
            "context_length": m.get("context_length"),
            "source": "jina_direct",
            "raw_data": {
                "jina_id": model_id,
                "name": m.get("name", ""),
                "hosting_type": "self-hosted",
                "input_modalities": input_modalities,
                "output_modalities": output_modalities,
                "quantization": m.get("quantization", ""),
                "max_output_length": m.get("max_output_length"),
                "cache_read_price": pricing.get("input_cache_read"),
                "image_price": pricing.get("image"),
                "request_price": pricing.get("request"),
            },
        })

        new_models.append({
            "model_id": model_id,
            "name": m.get("name", model_id.split("/")[-1].replace("-", " ")),
            "provider": "Jina",
            "context_length": m.get("context_length"),
            "is_reasoning": False,
            "modality": modality,
        })

    print(f"  Models with pricing: {len(endpoints)}, Skipped: {skipped}")
    return endpoints, new_models


# ============================================
# TOGETHER AI DIRECT API CONNECTOR
# ============================================

def fetch_together_direct():
    """Fetch model catalog and pricing directly from Together AI's API.

    Returns (endpoints, new_models).
    Requires API key (Together requires auth for /v1/models).
    Together pricing is per-million ($/M) - no conversion needed.
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Fetching Together AI direct API...")

    data = fetch_with_auth(TOGETHER_API, "together")
    if data is None:
        return [], []

    # Together returns a flat list, not {"data": [...]}
    models = data if isinstance(data, list) else data.get("data", [])
    print(f"  Together API returned {len(models)} models")

    endpoints = []
    new_models = []
    skipped = 0

    for m in models:
        model_id = m.get("id", "")
        if not model_id:
            continue

        # Together pricing is in a different structure
        pricing = m.get("pricing", {})
        # Try different pricing field names
        input_price = pricing.get("input") or pricing.get("prompt")
        output_price = pricing.get("output") or pricing.get("completion")

        if input_price is None or output_price is None:
            # Try top-level fields
            input_price = m.get("input_price")
            output_price = m.get("output_price")

        if input_price is None or output_price is None:
            skipped += 1
            continue

        try:
            input_price = float(input_price)
            output_price = float(output_price)
        except (ValueError, TypeError):
            skipped += 1
            continue

        if input_price <= 0 and output_price <= 0:
            skipped += 1
            continue

        # Together prices might be per-token or per-M depending on API version
        # Check magnitude: if < 0.1, it's likely per-token
        if input_price < 0.1:
            input_price = round(input_price * 1_000_000, 6)
            output_price = round(output_price * 1_000_000, 6)
        else:
            input_price = round(input_price, 6)
            output_price = round(output_price, 6)

        blended = round((BLENDED_INPUT_WEIGHT * input_price) + (BLENDED_OUTPUT_WEIGHT * output_price), 6)

        canonical_id = model_id if "/" in model_id else f"together/{model_id}"

        endpoints.append({
            "endpoint_provider": "Together",
            "model_id": canonical_id,
            "input_price_per_m": input_price,
            "output_price_per_m": output_price,
            "blended_price_per_m": blended,
            "context_length": m.get("context_length") or m.get("max_sequence_length"),
            "source": "together_direct",
            "raw_data": {
                "together_id": model_id,
                "owned_by": m.get("owned_by", "together"),
                "hosting_type": "self-hosted",
                "display_name": m.get("display_name", ""),
                "description": m.get("description", ""),
            },
        })

        new_models.append({
            "model_id": canonical_id,
            "name": m.get("display_name") or model_id.split("/")[-1].replace("-", " "),
            "provider": model_id.split("/")[0] if "/" in model_id else "Together",
            "context_length": m.get("context_length") or m.get("max_sequence_length"),
            "is_reasoning": "reasoning" in model_id.lower() or "deepseek" in model_id.lower(),
            "modality": "text",
        })

    print(f"  Models with pricing: {len(endpoints)}, Skipped: {skipped}")
    return endpoints, new_models


# ============================================
# GROQ DIRECT API CONNECTOR
# ============================================

def fetch_groq_direct():
    """Fetch model catalog from Groq's API.

    Returns (endpoints, new_models).
    Requires API key. Groq does NOT expose pricing in the models endpoint.
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Fetching Groq direct API...")

    data = fetch_with_auth(GROQ_API, "groq")
    if data is None:
        return [], []

    models = data.get("data", []) if isinstance(data, dict) else data
    print(f"  Groq API returned {len(models)} models")

    endpoints = []
    new_models = []
    skipped = 0

    for m in models:
        model_id = m.get("id", "")
        if not model_id:
            continue

        # Groq doesn't expose pricing in the models API
        # We record the catalog for comparison
        canonical_id = model_id if "/" in model_id else f"groq/{model_id}"

        new_models.append({
            "model_id": canonical_id,
            "name": model_id.replace("-", " ").replace("_", " ").title(),
            "provider": "Groq",
            "context_length": m.get("context_window_size") or m.get("context_length"),
            "is_reasoning": "reasoning" in model_id.lower() or "deepseek" in model_id.lower(),
            "modality": "text",
        })

    print(f"  Catalog models: {len(new_models)}, Skipped: {skipped}")
    return endpoints, new_models


# ============================================
# FIREWORKS AI DIRECT API CONNECTOR
# ============================================

def fetch_fireworks_direct():
    """Fetch model catalog from Fireworks AI's API.

    Returns (endpoints, new_models).
    Requires API key.
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Fetching Fireworks AI direct API...")

    data = fetch_with_auth(FIREWORKS_API, "fireworks")
    if data is None:
        return [], []

    models = data.get("data", []) if isinstance(data, dict) else data
    print(f"  Fireworks API returned {len(models)} models")

    endpoints = []
    new_models = []
    skipped = 0

    for m in models:
        model_id = m.get("id", "")
        if not model_id:
            continue

        pricing = m.get("pricing", {})
        input_price = pricing.get("input") or pricing.get("prompt")
        output_price = pricing.get("output") or pricing.get("completion")

        if input_price is None or output_price is None:
            # Skip models without pricing (embeddings, image gen, etc.)
            skipped += 1
            continue

        try:
            input_price = float(input_price)
            output_price = float(output_price)
        except (ValueError, TypeError):
            skipped += 1
            continue

        # Fireworks prices are per-million ($/M)
        input_price = round(input_price, 6)
        output_price = round(output_price, 6)
        blended = round((BLENDED_INPUT_WEIGHT * input_price) + (BLENDED_OUTPUT_WEIGHT * output_price), 6)

        canonical_id = model_id if "/" in model_id else f"fireworks/{model_id}"

        endpoints.append({
            "endpoint_provider": "Fireworks",
            "model_id": canonical_id,
            "input_price_per_m": input_price,
            "output_price_per_m": output_price,
            "blended_price_per_m": blended,
            "context_length": m.get("context_length"),
            "source": "fireworks_direct",
            "raw_data": {
                "fireworks_id": model_id,
                "owned_by": m.get("owned_by", "fireworks"),
                "hosting_type": "self-hosted",
                "description": m.get("description", ""),
            },
        })

        new_models.append({
            "model_id": canonical_id,
            "name": model_id.split("/")[-1].replace("-", " "),
            "provider": model_id.split("/")[0] if "/" in model_id else "Fireworks",
            "context_length": m.get("context_length"),
            "is_reasoning": "reasoning" in model_id.lower(),
            "modality": "text",
        })

    print(f"  Models with pricing: {len(endpoints)}, Skipped: {skipped}")
    return endpoints, new_models


# ============================================
# CEREBRAS DIRECT API CONNECTOR
# ============================================

def fetch_cerebras_direct():
    """Fetch model catalog from Cerebras's API.

    Returns (endpoints, new_models).
    Requires API key. Cerebras does NOT expose pricing in the models endpoint.
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Fetching Cerebras direct API...")

    data = fetch_with_auth(CEREBRAS_API, "cerebras")
    if data is None:
        return [], []

    models = data.get("data", []) if isinstance(data, dict) else data
    print(f"  Cerebras API returned {len(models)} models")

    endpoints = []
    new_models = []
    skipped = 0

    for m in models:
        model_id = m.get("id", "")
        if not model_id:
            continue

        canonical_id = model_id if "/" in model_id else f"cerebras/{model_id}"

        new_models.append({
            "model_id": canonical_id,
            "name": model_id.replace("-", " ").replace("_", " ").title(),
            "provider": "Cerebras",
            "context_length": m.get("context_length") or m.get("max_tokens"),
            "is_reasoning": "reasoning" in model_id.lower() or "deepseek" in model_id.lower(),
            "modality": "text",
        })

    print(f"  Catalog models: {len(new_models)}, Skipped: {skipped}")
    return endpoints, new_models


# ============================================
# MISTRAL AI DIRECT API CONNECTOR
# ============================================

def fetch_mistral_direct():
    """Fetch model catalog from Mistral AI's API.

    Returns (endpoints, new_models).
    Requires API key.
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Fetching Mistral AI direct API...")

    data = fetch_with_auth(MISTRAL_API, "mistral")
    if data is None:
        return [], []

    models = data.get("data", []) if isinstance(data, dict) else data
    print(f"  Mistral API returned {len(models)} models")

    endpoints = []
    new_models = []
    skipped = 0

    for m in models:
        model_id = m.get("id", "")
        if not model_id:
            continue

        canonical_id = f"mistralai/{model_id}"

        new_models.append({
            "model_id": canonical_id,
            "name": m.get("name", model_id.replace("-", " ").title()),
            "provider": "Mistral",
            "context_length": m.get("context_window") or m.get("max_context_length"),
            "is_reasoning": "reasoning" in model_id.lower(),
            "modality": "text",
        })

    print(f"  Catalog models: {len(new_models)}, Skipped: {skipped}")
    return endpoints, new_models


# ============================================
# SILICONFLOW DIRECT API CONNECTOR
# ============================================

def fetch_siliconflow_direct():
    """Fetch model catalog from SiliconFlow's API.

    Returns (endpoints, new_models).
    Requires API key.
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Fetching SiliconFlow direct API...")

    data = fetch_with_auth(SILICONFLOW_API, "siliconflow")
    if data is None:
        return [], []

    models = data.get("data", []) if isinstance(data, dict) else data
    print(f"  SiliconFlow API returned {len(models)} models")

    endpoints = []
    new_models = []
    skipped = 0

    for m in models:
        model_id = m.get("id", "")
        if not model_id:
            continue

        pricing = m.get("pricing", {})
        input_price = pricing.get("input") or pricing.get("prompt")
        output_price = pricing.get("output") or pricing.get("completion")

        if input_price is not None and output_price is not None:
            try:
                input_price = float(input_price)
                output_price = float(output_price)
                # SiliconFlow prices are per-million ($/M)
                input_price = round(input_price, 6)
                output_price = round(output_price, 6)
                blended = round((BLENDED_INPUT_WEIGHT * input_price) + (BLENDED_OUTPUT_WEIGHT * output_price), 6)

                canonical_id = model_id if "/" in model_id else f"siliconflow/{model_id}"

                endpoints.append({
                    "endpoint_provider": "SiliconFlow",
                    "model_id": canonical_id,
                    "input_price_per_m": input_price,
                    "output_price_per_m": output_price,
                    "blended_price_per_m": blended,
                    "context_length": m.get("context_length"),
                    "source": "siliconflow_direct",
                    "raw_data": {
                        "siliconflow_id": model_id,
                        "owned_by": m.get("owned_by", "siliconflow"),
                        "hosting_type": "self-hosted",
                    },
                })
            except (ValueError, TypeError):
                pass

        # Always add to new_models (even without pricing)
        canonical_id = model_id if "/" in model_id else f"siliconflow/{model_id}"
        new_models.append({
            "model_id": canonical_id,
            "name": model_id.split("/")[-1].replace("-", " "),
            "provider": model_id.split("/")[0] if "/" in model_id else "SiliconFlow",
            "context_length": m.get("context_length"),
            "is_reasoning": "reasoning" in model_id.lower() or "deepseek" in model_id.lower(),
            "modality": "text",
        })

    print(f"  Models with pricing: {len(endpoints)}, Skipped: {skipped}")
    return endpoints, new_models


# ============================================
# PERPLEXITY DIRECT API CONNECTOR
# ============================================

def fetch_perplexity_direct():
    """Fetch model catalog from Perplexity's API.

    Returns (endpoints, new_models).
    Requires API key. Perplexity uses OpenAI-compatible /models endpoint.
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Fetching Perplexity direct API...")

    data = fetch_with_auth(PERPLEXITY_API, "perplexity")
    if data is None:
        return [], []

    models = data.get("data", []) if isinstance(data, dict) else data
    print(f"  Perplexity API returned {len(models)} models")

    endpoints = []
    new_models = []
    skipped = 0

    for m in models:
        model_id = m.get("id", "")
        if not model_id:
            continue

        canonical_id = f"perplexity/{model_id}"

        new_models.append({
            "model_id": canonical_id,
            "name": model_id.replace("-", " ").replace("_", " ").title(),
            "provider": "Perplexity",
            "context_length": m.get("context_window_size") or m.get("context_length"),
            "is_reasoning": "reasoning" in model_id.lower() or "sonar" in model_id.lower(),
            "modality": "text",
        })

    print(f"  Catalog models: {len(new_models)}, Skipped: {skipped}")
    return endpoints, new_models


# ============================================
# OPENAI DIRECT API CONNECTOR
# ============================================

def fetch_openai_direct():
    """Fetch model catalog from OpenAI's API.

    Returns (endpoints, new_models).
    Requires API key. OpenAI's /v1/models does not include pricing.
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Fetching OpenAI direct API...")

    data = fetch_with_auth(OPENAI_DIRECT_API, "openai_direct")
    if data is None:
        return [], []

    models = data.get("data", []) if isinstance(data, dict) else data
    print(f"  OpenAI API returned {len(models)} models")

    endpoints = []
    new_models = []
    skipped = 0

    for m in models:
        model_id = m.get("id", "")
        if not model_id:
            continue

        # Filter to chat/text models only
        if any(skip in model_id.lower() for skip in ["whisper", "tts", "dall-e", "davinci", "babbage", "embedding", "moderation"]):
            skipped += 1
            continue

        canonical_id = f"openai/{model_id}"

        new_models.append({
            "model_id": canonical_id,
            "name": model_id.replace("-", " ").replace("_", " ").title(),
            "provider": "OpenAI",
            "context_length": m.get("context_window") or m.get("context_length"),
            "is_reasoning": "o1" in model_id.lower() or "o3" in model_id.lower() or "o4" in model_id.lower() or "reasoning" in model_id.lower(),
            "modality": "text",
        })

    print(f"  Catalog models: {len(new_models)}, Skipped: {skipped}")
    return endpoints, new_models


# ============================================
# ANTHROPIC DIRECT API CONNECTOR
# ============================================

def fetch_anthropic_direct():
    """Fetch model catalog from Anthropic's API.

    Returns (endpoints, new_models).
    Requires API key (x-api-key header). Anthropic's /v1/models is available.
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Fetching Anthropic direct API...")

    data = fetch_with_auth(ANTHROPIC_DIRECT_API, "anthropic_direct")
    if data is None:
        return [], []

    models = data.get("data", []) if isinstance(data, dict) else data
    print(f"  Anthropic API returned {len(models)} models")

    endpoints = []
    new_models = []
    skipped = 0

    for m in models:
        model_id = m.get("id", "")
        if not model_id:
            continue

        canonical_id = f"anthropic/{model_id}"

        new_models.append({
            "model_id": canonical_id,
            "name": model_id.replace("-", " ").title(),
            "provider": "Anthropic",
            "context_length": m.get("context_window") or m.get("context_length"),
            "is_reasoning": "claude" in model_id.lower() and ("thinking" in model_id.lower() or "opus" in model_id.lower()),
            "modality": "text",
        })

    print(f"  Catalog models: {len(new_models)}, Skipped: {skipped}")
    return endpoints, new_models


# ============================================
# HYPERBOLIC DIRECT API CONNECTOR
# ============================================

def fetch_hyperbolic_direct():
    """Fetch model catalog from Hyperbolic's API.

    Returns (endpoints, new_models).
    Requires API key.
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Fetching Hyperbolic direct API...")

    data = fetch_with_auth(HYPERBOLIC_API, "hyperbolic")
    if data is None:
        return [], []

    models = data.get("data", []) if isinstance(data, dict) else data
    print(f"  Hyperbolic API returned {len(models)} models")

    endpoints = []
    new_models = []
    skipped = 0

    for m in models:
        model_id = m.get("id", "")
        if not model_id:
            continue

        canonical_id = model_id if "/" in model_id else f"hyperbolic/{model_id}"

        new_models.append({
            "model_id": canonical_id,
            "name": model_id.split("/")[-1].replace("-", " "),
            "provider": model_id.split("/")[0] if "/" in model_id else "Hyperbolic",
            "context_length": m.get("context_length") or m.get("context_window"),
            "is_reasoning": "reasoning" in model_id.lower() or "deepseek" in model_id.lower(),
            "modality": "text",
        })

    print(f"  Catalog models: {len(new_models)}, Skipped: {skipped}")
    return endpoints, new_models


# ============================================
# AI/ML API DIRECT CONNECTOR (no auth)
# ============================================

def fetch_aiml_direct():
    """Fetch model catalog from AI/ML API.

    Returns (endpoints, new_models).
    No auth required - public API.
    AI/ML API does NOT expose pricing in the models endpoint (901 models, aggregator).
    We store the catalog for comparison; pricing comes from OpenRouter.
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Fetching AI/ML API direct...")

    try:
        resp = requests.get(AIML_API, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        models = data.get("data", [])
        print(f"  AI/ML API returned {len(models)} models")
    except Exception as e:
        print(f"  ERROR fetching AI/ML API: {e}")
        return [], []

    endpoints = []
    new_models = []
    skipped = 0

    for m in models:
        model_id = m.get("id", "")
        if not model_id:
            continue

        # Only include text/chat models
        mtype = m.get("type", "")
        if "chat-completions" not in mtype and "messages" not in mtype:
            skipped += 1
            continue

        info = m.get("info", {})
        canonical_id = model_id  # Already has provider/ prefix

        new_models.append({
            "model_id": canonical_id,
            "name": info.get("name", model_id.split("/")[-1].replace("-", " ")),
            "provider": info.get("developer", model_id.split("/")[0] if "/" in model_id else "AI/ML API"),
            "context_length": info.get("contextLength"),
            "is_reasoning": "o1" in model_id.lower() or "o3" in model_id.lower() or "reasoning" in model_id.lower() or "deepseek" in model_id.lower(),
            "modality": "text",
        })

    print(f"  Catalog models: {len(new_models)}, Skipped: {skipped}")
    return endpoints, new_models


# ============================================
# DEEPSEEK DIRECT API CONNECTOR (auth)
# ============================================

def fetch_deepseek_direct():
    """Fetch model catalog from DeepSeek's API.

    Returns (endpoints, new_models).
    Requires API key.
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Fetching DeepSeek direct API...")

    data = fetch_with_auth(DEEPSEEK_DIRECT_API, "deepseek_direct")
    if data is None:
        return [], []

    models = data.get("data", []) if isinstance(data, dict) else data
    print(f"  DeepSeek API returned {len(models)} models")

    endpoints = []
    new_models = []
    skipped = 0

    for m in models:
        model_id = m.get("id", "")
        if not model_id:
            continue

        canonical_id = f"deepseek/{model_id}"

        new_models.append({
            "model_id": canonical_id,
            "name": model_id.replace("-", " ").title(),
            "provider": "DeepSeek",
            "context_length": m.get("context_length") or m.get("context_window"),
            "is_reasoning": "reasoning" in model_id.lower() or "deepseek" in model_id.lower(),
            "modality": "text",
        })

    print(f"  Catalog models: {len(new_models)}, Skipped: {skipped}")
    return endpoints, new_models


# ============================================
# MOONSHOT/KIMI DIRECT API CONNECTOR (auth)
# ============================================

def fetch_moonshot_direct():
    """Fetch model catalog from Moonshot AI (Kimi) API.

    Returns (endpoints, new_models).
    Requires API key.
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Fetching Moonshot direct API...")

    data = fetch_with_auth(MOONSHOT_DIRECT_API, "moonshot_direct")
    if data is None:
        return [], []

    models = data.get("data", []) if isinstance(data, dict) else data
    print(f"  Moonshot API returned {len(models)} models")

    endpoints = []
    new_models = []
    skipped = 0

    for m in models:
        model_id = m.get("id", "")
        if not model_id:
            continue

        canonical_id = f"moonshotai/{model_id}"

        new_models.append({
            "model_id": canonical_id,
            "name": model_id.replace("-", " ").title(),
            "provider": "Moonshot",
            "context_length": m.get("context_length") or m.get("context_window"),
            "is_reasoning": "reasoning" in model_id.lower() or "kimi" in model_id.lower(),
            "modality": "text",
        })

    print(f"  Catalog models: {len(new_models)}, Skipped: {skipped}")
    return endpoints, new_models


# ============================================
# TENSORX DIRECT API CONNECTOR (auth)
# ============================================

def fetch_tensorx_direct():
    """Fetch model catalog from TensorX's API.

    Returns (endpoints, new_models).
    Requires API key. TensorX is an aggregator/proxy hosting models from
    Z-AI, DeepSeek, Qwen, Moonshot, Minimax and others.
    No pricing in /v1/models - catalog only.
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Fetching TensorX direct API...")

    data = fetch_with_auth(TENSORX_API, "tensorx")
    if data is None:
        return [], []

    models = data.get("data", []) if isinstance(data, dict) else data
    print(f"  TensorX API returned {len(models)} models")

    endpoints = []
    new_models = []
    skipped = 0

    for m in models:
        model_id = m.get("id", "")
        if not model_id:
            continue

        # TensorX model IDs already use provider/model format (e.g. z-ai/glm-5.2)
        canonical_id = model_id if "/" in model_id else f"tensorx/{model_id}"

        new_models.append({
            "model_id": canonical_id,
            "name": model_id.split("/")[-1].replace("-", " ").title() if "/" in model_id else model_id,
            "provider": "TensorX",
            "context_length": m.get("context_length") or m.get("context_window"),
            "is_reasoning": "reasoning" in model_id.lower() or "kimi" in model_id.lower() or "deepseek-r" in model_id.lower(),
            "modality": "text",
        })

    print(f"  Catalog models: {len(new_models)}, Skipped: {skipped}")
    return endpoints, new_models


def apply_median_pricing(models, fetch_endpoints=False):
    """For models with multiple endpoints, compute median price.
    
    If fetch_endpoints=True, fetch from OpenRouter API (daily run).
    If False, use existing endpoints from DB (hourly run).
    """
    if not fetch_endpoints:
        # Hourly run: try to load cached endpoints from DB
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            for m in models:
                cur.execute("""
                    SELECT DISTINCT ON (endpoint_provider)
                        endpoint_provider, input_price_per_m, output_price_per_m, blended_price_per_m
                    FROM model_endpoints
                    WHERE model_id = %s AND fetched_at >= NOW() - INTERVAL '24 hours'
                    ORDER BY endpoint_provider, fetched_at DESC
                """, (m["model_id"],))
                rows = cur.fetchall()
                if rows and len(rows) > 1:
                    blended_prices = [r[3] for r in rows if r[3] and r[3] > 0]
                    input_prices = [r[1] for r in rows if r[1] and r[1] > 0]
                    output_prices = [r[2] for r in rows if r[2] and r[2] > 0]
                    if blended_prices:
                        m["blended_price_per_m"] = compute_median(blended_prices)
                        m["input_price_per_m"] = compute_median(input_prices) if input_prices else m["input_price_per_m"]
                        m["output_price_per_m"] = compute_median(output_prices) if output_prices else m["output_price_per_m"]
                        m["source_count"] = len(blended_prices)
                        # Recalculate SIT-adjusted price with updated blended price
                        m["sit_adjusted_price"] = calculate_sit_adjusted_price(
                            m["blended_price_per_m"], m.get("reasoning_multiplier", 1.0), m.get("aa_index_score")
                        )
                    else:
                        m["source_count"] = 1
                else:
                    m["source_count"] = 1 if not rows else len(rows)
            cur.close()
            conn.close()
        except Exception as e:
            print(f"  WARN: Could not load cached endpoints: {e}")
            for m in models:
                m["source_count"] = 1
        return models
    
    # Daily run: fetch fresh endpoints from OpenRouter
    print(f"\n[{datetime.now(timezone.utc).isoformat()}] Fetching endpoints for {len(models)} models...")
    all_endpoint_data = []
    multi_provider_count = 0
    
    for i, m in enumerate(models):
        if (i + 1) % 50 == 0:
            print(f"  Progress: {i+1}/{len(models)}")
        
        raw_endpoints = fetch_model_endpoints(m["model_id"])
        normalized_eps = normalize_endpoints(m["model_id"], raw_endpoints)
        
        if len(normalized_eps) > 1:
            multi_provider_count += 1
            blended_prices = [ep["blended_price_per_m"] for ep in normalized_eps if ep["blended_price_per_m"] > 0]
            input_prices = [ep["input_price_per_m"] for ep in normalized_eps if ep["input_price_per_m"] > 0]
            output_prices = [ep["output_price_per_m"] for ep in normalized_eps if ep["output_price_per_m"] > 0]
            
            m["blended_price_per_m"] = compute_median(blended_prices)
            m["input_price_per_m"] = compute_median(input_prices)
            m["output_price_per_m"] = compute_median(output_prices)
            m["source_count"] = len(normalized_eps)
            # Recalculate SIT-adjusted price with updated blended price
            m["sit_adjusted_price"] = calculate_sit_adjusted_price(
                m["blended_price_per_m"], m.get("reasoning_multiplier", 1.0), m.get("aa_index_score")
            )
        else:
            m["source_count"] = 1
        
        # Store endpoint data for DB insert
        for ep in normalized_eps:
            ep["model_id"] = m["model_id"]
            all_endpoint_data.append(ep)
        
        # Rate limit: be gentle with OpenRouter
        time.sleep(0.3)
    
    print(f"  Endpoints fetched. {multi_provider_count} models have multiple providers.")
    return models, all_endpoint_data

# ============================================
# NORMALIZE
# ============================================

def normalize_model(raw):
    """Convert a raw OpenRouter model to our normalized format."""
    model_id = raw.get("id", "")
    name = raw.get("name", model_id)
    context_length = raw.get("context_length")
    
    # Provider: first part of model ID, or from name
    provider = model_id.split("/")[0] if "/" in model_id else "unknown"
    # Capitalize provider
    provider = provider.replace("-", " ").replace("_", " ").title()
    # Fix common ones
    provider_map = {
        "Openai": "OpenAI",
        "X Ai": "xAI",
        "Z.Ai": "Z.ai",
        "Meta": "Meta",
    }
    provider = provider_map.get(provider, provider)
    
    # Pricing (OpenRouter returns per-token prices as strings)
    pricing = raw.get("pricing", {})
    prompt_str = pricing.get("prompt", "0")
    completion_str = pricing.get("completion", "0")
    
    try:
        prompt_per_token = float(prompt_str)
        completion_per_token = float(completion_str)
    except (ValueError, TypeError):
        prompt_per_token = 0.0
        completion_per_token = 0.0
    
    # Convert to per-million ($/M)
    input_price_per_m = round(prompt_per_token * 1_000_000, 6)
    output_price_per_m = round(completion_per_token * 1_000_000, 6)
    blended_price_per_m = round(
        (BLENDED_INPUT_WEIGHT * input_price_per_m) + 
        (BLENDED_OUTPUT_WEIGHT * output_price_per_m), 6
    )
    
    # AA Index score
    benchmarks = raw.get("benchmarks", {})
    aa_data = benchmarks.get("artificial_analysis", {}) if benchmarks else {}
    aa_score = aa_data.get("intelligence_index") if aa_data else None
    
    # Tier (use blended price as fallback for models without AA scores)
    tier = assign_tier(aa_score, blended_price_per_m)
    
    # Modality
    arch = raw.get("architecture", {})
    modality = arch.get("modality", "text")
    
    # Reasoning
    is_reasoning = raw.get("reasoning") is not None and raw.get("reasoning") != False
    
    # Reasoning multiplier (tier-based estimate)
    reasoning_multiplier = get_reasoning_multiplier(tier, is_reasoning)
    
    # SIT-adjusted price (cost per unit of intelligence)
    sit_adjusted_price = calculate_sit_adjusted_price(
        blended_price_per_m, reasoning_multiplier, aa_score
    )
    
    return {
        "model_id": model_id,
        "name": name,
        "provider": provider,
        "tier": tier,
        "context_length": context_length,
        "aa_index_score": aa_score,
        "modality": modality,
        "tokenizer": arch.get("tokenizer"),
        "is_reasoning": is_reasoning,
        "reasoning_multiplier": reasoning_multiplier,
        "sit_adjusted_price": sit_adjusted_price,
        "input_price_per_m": input_price_per_m,
        "output_price_per_m": output_price_per_m,
        "blended_price_per_m": blended_price_per_m,
        "raw_data": raw,
    }

def filter_priced(models):
    """Filter to only models with non-zero pricing."""
    priced = [m for m in models if m["input_price_per_m"] > 0 or m["output_price_per_m"] > 0]
    print(f"  Filtered to {len(priced)} models with pricing (excluded {len(models) - len(priced)} unpriced)")
    return priced

# ============================================
# SIT CALCULATION
# ============================================

def _median(values):
    """Compute the median of a sorted list of numbers."""
    s = sorted(values)
    n = len(s)
    mid = n // 2
    if n % 2 == 0:
        return (s[mid - 1] + s[mid]) / 2
    return s[mid]


def calculate_tier_averages(models):
    """Calculate the median blended price per tier.

    Median is robust to outliers (e.g. o1-pro at $420/M skews the frontier
    tier mean to $38 vs a median of $20). Using median for the tier average
    makes SIT scores more meaningful: SIT 1.0 = at the median tier price.
    """
    tier_prices = {}
    for m in models:
        tier = m["tier"]
        if tier not in tier_prices:
            tier_prices[tier] = []
        tier_prices[tier].append(m["blended_price_per_m"])

    tier_avgs = {}
    for tier, prices in tier_prices.items():
        tier_avgs[tier] = round(_median(prices), 6)

    return tier_avgs

def calculate_sit_scores(models, tier_avgs):
    """Calculate SIT score for each model.
    
    SIT Score = (model's SIT-adjusted price / tier median SIT-adjusted price) * 100
    A score of 100 = at the tier median. Lower = cheaper per unit of intelligence.
    Minimum score is 1. Models without an AA score get no SIT score (None).
    """
    # Compute tier medians using ONLY models with SIT-adjusted prices
    tier_adjusted_prices = {}
    for m in models:
        tier = m["tier"]
        if tier not in tier_adjusted_prices:
            tier_adjusted_prices[tier] = []
        adj = m.get("sit_adjusted_price")
        if adj and adj > 0:
            tier_adjusted_prices[tier].append(adj)
    
    tier_adjusted_medians = {}
    for tier, prices in tier_adjusted_prices.items():
        if prices:
            tier_adjusted_medians[tier] = _median(prices)
    
    for m in models:
        tier_median = tier_adjusted_medians.get(m["tier"])
        adj = m.get("sit_adjusted_price")
        if tier_median and tier_median > 0 and adj and adj > 0:
            ratio = adj / tier_median
            score = round(ratio * 100)
            m["sit_score"] = max(score, 1)
        else:
            # No AA score = no SIT score
            m["sit_score"] = None
    return models

def calculate_composite_price(models):
    """Calculate the SIT-Composite price: usage-weighted mean of top 50 models by token volume.
    
    Quality gate: only models with AA score >= 35 (GPT-4-Turbo baseline) are included.
    Uses usage_weights from the database for weighting.
    
    This is the spot price headline number (what inference costs per million tokens).
    """
    import psycopg2
    
    # We need the DB connection to get usage weights
    # This is called from calculate_tier_indices which has access to conn
    # We'll use the global conn passed through the pipeline
    prices = [m["blended_price_per_m"] for m in models if m["blended_price_per_m"] > 0]
    if not prices:
        return 0.0
    return round(_median(prices), 6)


def calculate_composite_usage_weighted(conn):
    """Calculate the SIT-Composite using usage-weighted top 50 with quality gate.
    
    This is the authoritative composite calculation that matches the API methodology:
    - Filter to models with AA score >= 35
    - Take top 50 by usage weight
    - Usage-weighted mean of blended prices
    """
    cur = conn.cursor()
    cur.execute("""
        WITH top50 AS (
            SELECT uw.model_id, uw.weight_pct, lp.blended_price_per_m, m.tier, m.provider
            FROM usage_weights uw
            JOIN latest_prices lp ON uw.model_id = lp.model_id
            JOIN models m ON uw.model_id = m.id
            WHERE m.is_active = TRUE 
              AND lp.blended_price_per_m > 0
              AND m.aa_index_score IS NOT NULL 
              AND m.aa_index_score >= 35
              AND m.id NOT LIKE '%%:batch'
            ORDER BY uw.weight_pct DESC
            LIMIT 50
        )
        SELECT 
            SUM(weight_pct * blended_price_per_m) / NULLIF(SUM(weight_pct), 0) AS weighted_mean,
            COUNT(*) AS model_count,
            COUNT(DISTINCT provider) AS provider_count
        FROM top50
    """)
    row = cur.fetchone()
    cur.close()
    if row and row[0]:
        return {
            "price": round(float(row[0]), 6),
            "model_count": row[1],
            "provider_count": row[2],
        }
    return {"price": 0.0, "model_count": 0, "provider_count": 0}

def calculate_tier_indices(models):
    """Calculate SIT index values for each tier and the composite."""
    results = {}
    
    # Per-tier (spot price = median blended price)
    for tier in ["frontier", "standard", "budget", "micro"]:
        tier_models = [m for m in models if m["tier"] == tier and m["blended_price_per_m"] > 0]
        if tier_models:
            prices = [m["blended_price_per_m"] for m in tier_models]
            median_price = _median(prices)
            providers = set(m["provider"] for m in tier_models)
            results[tier] = {
                "price": round(median_price, 6),
                "model_count": len(tier_models),
                "provider_count": len(providers),
            }
    
    # Composite - uses usage-weighted top 50 with quality gate (from DB)
    # Fallback to median if conn not available
    try:
        # Try to get conn from the calling context
        # calculate_tier_indices is called with models, but we need conn
        # We'll use the composite from the API instead
        composite_price = calculate_composite_price(models)
        all_providers = set(m["provider"] for m in models)
        results["composite"] = {
            "price": composite_price,
            "model_count": len(models),
            "provider_count": len(all_providers),
        }
    except Exception:
        results["composite"] = {"price": 0.0, "model_count": 0, "provider_count": 0}
    
    # Spread (frontier - budget)
    if "frontier" in results and "budget" in results:
        results["spread"] = {
            "price": round(results["frontier"]["price"] - results["budget"]["price"], 6),
            "model_count": 0,
            "provider_count": 0,
        }
    
    return results

def calculate_index_points(current_price, base_price):
    """Calculate index points relative to base value of 1000."""
    if base_price <= 0:
        return 0.0
    return round((current_price / base_price) * BASE_VALUE, 2)

# ============================================
# ANOMALY DETECTION
# ============================================

def detect_anomalies(new_models, previous_prices):
    """Detect price changes > 50% from previous fetch."""
    anomalies = []
    for m in new_models:
        prev = previous_prices.get(m["model_id"])
        if prev and prev > 0:
            change = abs((m["blended_price_per_m"] - prev) / prev)
            if change > ANOMALY_THRESHOLD:
                anomalies.append({
                    "model_id": m["model_id"],
                    "previous_price": prev,
                    "new_price": m["blended_price_per_m"],
                    "change_pct": round(change * 100, 2),
                })
    return anomalies

# ============================================
# DATABASE OPERATIONS
# ============================================

def get_db_connection():
    """Get Postgres connection from environment variables."""
    # Try environment variable first
    db_url = os.environ.get("SUPABASE_DB_URL")
    
    # Fall back to ~/.hermes/.env file
    if not db_url:
        env_path = os.path.expanduser("~/.hermes/.env")
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("SUPABASE_DB_URL="):
                        db_url = line.split("=", 1)[1]
                        break
    
    if not db_url:
        print("ERROR: SUPABASE_DB_URL not found")
        print("Set it in ~/.hermes/.env as: SUPABASE_DB_URL=postgresql://postgres:...")
        sys.exit(1)
    
    return psycopg2.connect(db_url, connect_timeout=10)

def upsert_models(conn, models):
    """Insert or update models in the database."""
    cur = conn.cursor()
    count = 0
    
    for m in models:
        cur.execute("""
            INSERT INTO models (id, name, provider, tier, context_length, aa_index_score, 
                              modality, tokenizer, is_reasoning, updated_at, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), TRUE)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                provider = EXCLUDED.provider,
                tier = EXCLUDED.tier,
                context_length = EXCLUDED.context_length,
                aa_index_score = EXCLUDED.aa_index_score,
                modality = EXCLUDED.modality,
                tokenizer = EXCLUDED.tokenizer,
                is_reasoning = EXCLUDED.is_reasoning,
                updated_at = NOW()
        """, (
            m["model_id"], m["name"], m["provider"], m["tier"],
            m["context_length"], m["aa_index_score"],
            m["modality"], m["tokenizer"], m["is_reasoning"]
        ))
        count += 1
    
    conn.commit()
    cur.close()
    print(f"  Upserted {count} model records")
    return count

def insert_endpoints(conn, endpoint_data):
    """Insert endpoint data into model_endpoints table."""
    cur = conn.cursor()
    count = 0
    for ep in endpoint_data:
        cur.execute("""
            INSERT INTO model_endpoints
                (model_id, endpoint_provider, input_price_per_m, output_price_per_m,
                 blended_price_per_m, context_length, source, raw_data)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            ep["model_id"], ep["endpoint_provider"],
            ep["input_price_per_m"], ep["output_price_per_m"],
            ep["blended_price_per_m"], ep.get("context_length"),
            ep.get("source", SOURCE_NAME), json.dumps(ep.get("raw_data", {}))
        ))
        count += 1
    conn.commit()
    cur.close()
    print(f"  Inserted {count} endpoint records")
    return count

def insert_price_snapshots(conn, models):
    """Insert price snapshots for all models."""
    cur = conn.cursor()
    count = 0
    anomalies_found = 0
    
    # Get previous prices for anomaly detection
    cur.execute("""
        SELECT DISTINCT ON (model_id) model_id, blended_price_per_m
        FROM price_snapshots
        ORDER BY model_id, fetched_at DESC
    """)
    previous = {row[0]: row[1] for row in cur.fetchall()}
    
    for m in models:
        # Check for anomaly
        is_anomalous = False
        prev = previous.get(m["model_id"])
        if prev and prev > 0:
            change = abs((m["blended_price_per_m"] - prev) / prev)
            if change > ANOMALY_THRESHOLD:
                is_anomalous = True
                anomalies_found += 1
                print(f"  ⚠ ANOMALY: {m['model_id']} {prev} → {m['blended_price_per_m']} ({change*100:.1f}%)")
                
                # Insert anomaly record
                cur.execute("""
                    INSERT INTO anomalies (model_id, previous_price, new_price, change_pct)
                    VALUES (%s, %s, %s, %s)
                """, (m["model_id"], prev, m["blended_price_per_m"], round(change * 100, 2)))
        
        cur.execute("""
            INSERT INTO price_snapshots 
                (model_id, source, input_price_per_m, output_price_per_m, 
                 blended_price_per_m, sit_score, reasoning_multiplier, 
                 sit_adjusted_price, raw_data, is_anomalous, source_count)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            m["model_id"], SOURCE_NAME,
            m["input_price_per_m"], m["output_price_per_m"],
            m["blended_price_per_m"], m.get("sit_score"),
            m.get("reasoning_multiplier", 1.0),
            m.get("sit_adjusted_price"),
            json.dumps(m["raw_data"]), is_anomalous,
            m.get("source_count", 1)
        ))
        count += 1
    
    conn.commit()
    cur.close()
    print(f"  Inserted {count} price snapshots ({anomalies_found} anomalies flagged)")
    return count

def insert_sit_values(conn, indices, today):
    """Insert SIT index values for today."""
    cur = conn.cursor()
    count = 0
    
    for tier, data in indices.items():
        # For index points: on base date, price = base price
        # After base date: index_points = (current_price / base_price) * 1000
        # We store the first ever price as the base
        cur.execute("""
            SELECT sit_price FROM sit_index_values 
            WHERE tier = %s AND date = %s
            ORDER BY date ASC LIMIT 1
        """, (tier, BASE_DATE))
        row = cur.fetchone()
        
        if row:
            base_price = row[0]
            index_points = calculate_index_points(data["price"], base_price)
        elif today == BASE_DATE:
            # First ever calculation on base date
            index_points = BASE_VALUE
        else:
            # No base price yet, use today's price as base
            index_points = BASE_VALUE
        
        # Use correct calculation method name
        if tier == "composite":
            method = "usage_weighted_quality_gated"
        else:
            method = "median_tier"
        
        cur.execute("""
            INSERT INTO sit_index_values 
                (date, tier, sit_price, sit_index_points, model_count, 
                 provider_count, calculation_method)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (date, tier) DO UPDATE SET
                sit_price = EXCLUDED.sit_price,
                sit_index_points = EXCLUDED.sit_index_points,
                model_count = EXCLUDED.model_count,
                provider_count = EXCLUDED.provider_count,
                calculation_method = EXCLUDED.calculation_method,
                calculated_at = NOW()
        """, (
            today, tier, data["price"], index_points,
            data["model_count"], data["provider_count"], method
        ))
        count += 1
    
    conn.commit()
    cur.close()
    print(f"  Inserted {count} SIT index values")
    return count

# ============================================
# PRINT SUMMARY (for --fetch-only mode)
# ============================================

def print_summary(models, tier_avgs, indices):
    """Print a summary of the fetched data."""
    print("\n" + "=" * 60)
    print("INFERENCEINDEXER DATA SUMMARY")
    print("=" * 60)
    
    # Tier breakdown
    tier_counts = {}
    for m in models:
        tier_counts[m["tier"]] = tier_counts.get(m["tier"], 0) + 1
    
    print(f"\nTotal models: {len(models)}")
    print(f"Providers: {len(set(m['provider'] for m in models))}")
    print(f"\nTier breakdown:")
    for tier in ["frontier", "standard", "budget", "micro"]:
        count = tier_counts.get(tier, 0)
        avg = tier_avgs.get(tier, 0)
        print(f"  {tier:10s}: {count:4d} models, median blended ${avg:.4f}/M")
    
    print(f"\nSIT-Composite: ${indices['composite']['price']:.4f}/M")
    print(f"  Models: {indices['composite']['model_count']}")
    print(f"  Providers: {indices['composite']['provider_count']}")
    
    if "spread" in indices:
        print(f"\nSIT-Spread: ${indices['spread']['price']:.4f}/M")
    
    # Top 10 cheapest by SIT Score
    scored = [m for m in models if m.get("sit_score") is not None and isinstance(m.get("sit_score"), int)]
    scored.sort(key=lambda x: x["sit_score"])
    
    print(f"\nTop 10 by SIT Score (cheapest for tier, adjusted, 100=median):")
    print(f"  {'Model':<40} {'Tier':<10} {'Blended $/M':<12} {'R.Mult':<7} {'Adj $/M':<10} {'SIT':>6}")
    for m in scored[:10]:
        rm = m.get("reasoning_multiplier", 1.0)
        adj = m.get("sit_adjusted_price")
        adj_str = f"${adj:.6f}" if adj else "N/A"
        print(f"  {m['name'][:40]:<40} {m['tier']:<10} ${m['blended_price_per_m']:<11.4f} {rm:<7.1f} {adj_str:<10} {m['sit_score']:>6}")
    
    # Top 5 most expensive by SIT Score
    print(f"\nTop 5 most expensive (by SIT Score):")
    for m in scored[-5:]:
        rm = m.get("reasoning_multiplier", 1.0)
        adj = m.get("sit_adjusted_price")
        adj_str = f"${adj:.6f}" if adj else "N/A"
        print(f"  {m['name'][:40]:<40} {m['tier']:<10} ${m['blended_price_per_m']:<11.4f} {rm:<7.1f} {adj_str:<10} {m['sit_score']}")
    
    print("\n" + "=" * 60)

# ============================================
# MAIN
# ============================================

def main():
    parser = argparse.ArgumentParser(description="InferenceIndexer data pipeline")
    parser.add_argument("--fetch-only", action="store_true", help="Fetch and print, don't store to DB")
    parser.add_argument("--sit-only", action="store_true", help="Calculate SIT from existing DB data")
    parser.add_argument("--fetch-endpoints", action="store_true", help="Fetch per-provider endpoints from OpenRouter (daily run)")
    args = parser.parse_args()
    
    today = date.today()
    
    # --- FETCH ---
    raw_models = fetch_openrouter()
    
    # Normalize
    normalized = [normalize_model(m) for m in raw_models]
    priced = filter_priced(normalized)
    
    # Apply median pricing (fetch endpoints if --fetch-endpoints, else use DB cache)
    if args.fetch_endpoints:
        print(f"\n[{datetime.now(timezone.utc).isoformat()}] Fetching provider endpoints (daily mode)...")
        priced, endpoint_data = apply_median_pricing(priced, fetch_endpoints=True)
    else:
        priced = apply_median_pricing(priced, fetch_endpoints=False)
        endpoint_data = []
    
    # Always fetch Venice direct API (hourly - it's one HTTP call, no auth)
    venice_endpoints, venice_new_models = fetch_venice_direct()
    if venice_endpoints:
        endpoint_data.extend(venice_endpoints)
        print(f"  Venice direct: {len(venice_endpoints)} endpoints added")
    
    # Always fetch DeepInfra direct API (hourly - one HTTP call, no auth)
    deepinfra_endpoints, deepinfra_new_models = fetch_deepinfra_direct()
    if deepinfra_endpoints:
        endpoint_data.extend(deepinfra_endpoints)
        print(f"  DeepInfra direct: {len(deepinfra_endpoints)} endpoints added")
    
    # Always fetch Novita direct API (hourly - one HTTP call, no auth)
    novita_endpoints, novita_new_models = fetch_novita_direct()
    if novita_endpoints:
        endpoint_data.extend(novita_endpoints)
        print(f"  Novita direct: {len(novita_endpoints)} endpoints added")
    
    # Fetch SambaNova direct API (hourly - one HTTP call, no auth)
    sambanova_endpoints, sambanova_new_models = fetch_sambanova_direct()
    if sambanova_endpoints:
        endpoint_data.extend(sambanova_endpoints)
        print(f"  SambaNova direct: {len(sambanova_endpoints)} endpoints added")
    
    # Fetch Jina direct API (hourly - one HTTP call, no auth)
    jina_endpoints, jina_new_models = fetch_jina_direct()
    if jina_endpoints:
        endpoint_data.extend(jina_endpoints)
        print(f"  Jina direct: {len(jina_endpoints)} endpoints added")
    
    # Fetch Inference.net direct API (hourly - one HTTP call, no auth, catalog only)
    infernet_endpoints, infernet_new_models = fetch_inference_net_direct()
    if infernet_endpoints:
        endpoint_data.extend(infernet_endpoints)
        print(f"  Inference.net direct: {len(infernet_endpoints)} endpoints added")
    
    # Auth-required providers (will skip gracefully if no API key)
    together_endpoints, together_new_models = fetch_together_direct()
    if together_endpoints:
        endpoint_data.extend(together_endpoints)
        print(f"  Together direct: {len(together_endpoints)} endpoints added")
    
    groq_endpoints, groq_new_models = fetch_groq_direct()
    
    fireworks_endpoints, fireworks_new_models = fetch_fireworks_direct()
    if fireworks_endpoints:
        endpoint_data.extend(fireworks_endpoints)
        print(f"  Fireworks direct: {len(fireworks_endpoints)} endpoints added")
    
    cerebras_endpoints, cerebras_new_models = fetch_cerebras_direct()
    
    mistral_endpoints, mistral_new_models = fetch_mistral_direct()
    
    siliconflow_endpoints, siliconflow_new_models = fetch_siliconflow_direct()
    if siliconflow_endpoints:
        endpoint_data.extend(siliconflow_endpoints)
        print(f"  SiliconFlow direct: {len(siliconflow_endpoints)} endpoints added")
    
    perplexity_endpoints, perplexity_new_models = fetch_perplexity_direct()
    
    openai_direct_endpoints, openai_direct_new_models = fetch_openai_direct()
    
    anthropic_direct_endpoints, anthropic_direct_new_models = fetch_anthropic_direct()
    
    hyperbolic_endpoints, hyperbolic_new_models = fetch_hyperbolic_direct()
    
    # Fetch AI/ML API (no auth, catalog only, 900+ models)
    aiml_endpoints, aiml_new_models = fetch_aiml_direct()
    
    # Auth-required direct providers
    deepseek_direct_endpoints, deepseek_direct_new_models = fetch_deepseek_direct()
    
    moonshot_direct_endpoints, moonshot_direct_new_models = fetch_moonshot_direct()
    
    # TensorX direct (aggregator/proxy - catalog only, no pricing in API)
    tensorx_endpoints, tensorx_new_models = fetch_tensorx_direct()
    
    # Calculate tier averages and SIT scores
    tier_avgs = calculate_tier_averages(priced)
    priced = calculate_sit_scores(priced, tier_avgs)
    
    # Calculate SIT indices
    indices = calculate_tier_indices(priced)
    
    # Print summary
    print_summary(priced, tier_avgs, indices)
    
    if args.fetch_only:
        print("\n--fetch-only: skipping database storage")
        return
    
    # --- STORE TO DB ---
    if not HAS_DB:
        print("\nERROR: psycopg2 not installed. Install with: pip install psycopg2-binary")
        print("Or run with --fetch-only to test without database")
        sys.exit(1)
    
    print(f"\n[{datetime.now(timezone.utc).isoformat()}] Storing to Supabase...")
    conn = get_db_connection()
    
    try:
        upsert_models(conn, priced)
        
        # Always upsert provider-discovered models
        if venice_endpoints:
            upsert_venice_models(conn, venice_new_models, priced)
        if deepinfra_endpoints:
            upsert_venice_models(conn, deepinfra_new_models, priced)
        if novita_endpoints:
            upsert_venice_models(conn, novita_new_models, priced)
        if sambanova_endpoints:
            upsert_venice_models(conn, sambanova_new_models, priced)
        if jina_endpoints:
            upsert_venice_models(conn, jina_new_models, priced)
        if infernet_endpoints:
            upsert_venice_models(conn, infernet_new_models, priced)
        if together_endpoints:
            upsert_venice_models(conn, together_new_models, priced)
        if groq_new_models:
            upsert_venice_models(conn, groq_new_models, priced)
        if fireworks_endpoints:
            upsert_venice_models(conn, fireworks_new_models, priced)
        if cerebras_new_models:
            upsert_venice_models(conn, cerebras_new_models, priced)
        if mistral_new_models:
            upsert_venice_models(conn, mistral_new_models, priced)
        if siliconflow_endpoints:
            upsert_venice_models(conn, siliconflow_new_models, priced)
        if perplexity_new_models:
            upsert_venice_models(conn, perplexity_new_models, priced)
        if openai_direct_new_models:
            upsert_venice_models(conn, openai_direct_new_models, priced)
        if anthropic_direct_new_models:
            upsert_venice_models(conn, anthropic_direct_new_models, priced)
        if hyperbolic_new_models:
            upsert_venice_models(conn, hyperbolic_new_models, priced)
        if aiml_new_models:
            upsert_venice_models(conn, aiml_new_models, priced)
        if deepseek_direct_new_models:
            upsert_venice_models(conn, deepseek_direct_new_models, priced)
        if moonshot_direct_new_models:
            upsert_venice_models(conn, moonshot_direct_new_models, priced)
        if tensorx_new_models:
            upsert_venice_models(conn, tensorx_new_models, priced)
        
        if endpoint_data:
            insert_endpoints(conn, endpoint_data)
        insert_price_snapshots(conn, priced)
        
        # Recalculate composite using usage-weighted top 50 with quality gate
        # (the API methodology, not the simple median used in calculate_tier_indices)
        composite_data = calculate_composite_usage_weighted(conn)
        if composite_data["price"] > 0:
            indices["composite"] = composite_data
        
        insert_sit_values(conn, indices, today)
        print(f"\n✓ Pipeline complete at {datetime.now(timezone.utc).isoformat()}")
    except Exception as e:
        conn.rollback()
        print(f"\n✗ Pipeline error: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    main()
