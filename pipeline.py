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

from fireworks_pricing import fetch_fireworks_pricing as _fetch_fireworks_pricing
from provider_scrapers import (
    fetch_groq_pricing as _fetch_groq_pricing,
    fetch_together_pricing as _fetch_together_pricing,
)
from tensorx_pricing import fetch_tensorx_pricing as _fetch_tensorx_pricing
from openrelay_pricing import fetch_openrelay_pricing as _fetch_openrelay_pricing
from sarvam_pricing import fetch_sarvam_pricing as _fetch_sarvam_pricing

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
AA_LEADERBOARD_URL = "https://artificialanalysis.ai/leaderboards/models"
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
ENGY_API = "https://api.engy.ai/v1/models"
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

def canonical_model_id(model_id: str) -> str:
    """Normalize a provider model id to our canonical lowercase form.

    Our canonical scheme is lowercase `provider/model` (moonshotai/kimi-k3,
    z-ai/glm-5.2). Some providers (DeepInfra, Novita, Jina, Together, Groq,
    OpenRouter) return mixed-case IDs (moonshotai/Kimi-K3, zai-org/GLM-5.2)
    which collide with the lowercase canonical rows. Lowercasing both path
    segments avoids case-duplicate rows.
    """
    if "/" not in model_id:
        return model_id.lower()
    provider, _, model = model_id.partition("/")
    return provider.lower() + "/" + model.lower()


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
        deepinfra_id = canonical_model_id(model_id)
        
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
        
        canonical_id = canonical_model_id(model_id)

        endpoints.append({
            "endpoint_provider": "Novita",
            "model_id": canonical_id,
            "input_price_per_m": input_price,
            "output_price_per_m": output_price,
            "blended_price_per_m": blended,
            "context_length": m.get("context_size"),
            "source": "novita_direct",
            "raw_data": {
                "novita_id": canonical_id,
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
            "model_id": canonical_id,
            "name": m.get("display_name") or model_id.split("/")[-1].replace("-", " "),
            "provider": canonical_id.split("/")[0] if "/" in canonical_id else "novita",
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

        # SambaNova model IDs don't have provider prefix; add one, lowercase canonical
        canonical_id = canonical_model_id(f"sambanova/{model_id}")

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
        canonical_id = canonical_model_id(f"inference-net/{model_id}")

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
            "model_id": canonical_model_id(model_id),
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
            "model_id": canonical_model_id(model_id),
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
    """Fetch Together pricing via their docs markdown scraper.

    Together's /v1/models API needs a key and returns catalog-only data. The
    authoritative per-model pricing lives on docs.together.ai (clean markdown).
    This delegates to provider_scrapers.fetch_together_pricing().

    Returns (endpoints, new_models) with canonical model IDs (Venice-style).
    """
    # Delegate to the markdown scraper (no API key needed).
    return _fetch_together_pricing()


# ============================================
# GROQ DIRECT API CONNECTOR
# ============================================

def fetch_groq_direct():
    """Fetch Groq pricing via their docs markdown scraper.

    Groq's /v1/models API needs a key and returns catalog-only (no pricing).
    The authoritative per-model pricing lives on console.groq.com/docs/models.md
    (clean markdown). Delegates to provider_scrapers.fetch_groq_pricing().

    Returns (endpoints, new_models) with canonical model IDs (Venice-style).
    """
    # Delegate to the markdown scraper (no API key needed).
    return _fetch_groq_pricing()


# ============================================
# FIREWORKS AI DIRECT API CONNECTOR
# ============================================

def fetch_fireworks_direct():
    """Fetch Fireworks catalog + pricing direct.

    Fireworks' REST API returns the model catalog but NO pricing field. Our
    scraper (fireworks_pricing.py) combines the live catalog with the
    authoritative per-model prices from the docs page (docs.fireworks.ai
    /serverless/pricing.md) and returns (endpoints, new_models).

    Requires API key. Falls back to catalog-only if the docs fetch fails.
    """
    api_key = get_provider_api_key("fireworks")
    if not api_key:
        print("  fireworks: No API key (auth required). Skipping.")
        return [], []

    # Delegates to fireworks_pricing.fetch_fireworks_pricing().
    return _fetch_fireworks_pricing(api_key)


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

        canonical_id = canonical_model_id(model_id if "/" in model_id else f"cerebras/{model_id}")

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

        canonical_id = canonical_model_id(f"mistralai/{model_id}")

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

                canonical_id = canonical_model_id(model_id if "/" in model_id else f"siliconflow/{model_id}")

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
        canonical_id = canonical_model_id(model_id if "/" in model_id else f"siliconflow/{model_id}")
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

        canonical_id = canonical_model_id(f"perplexity/{model_id}")

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

        canonical_id = canonical_model_id(f"openai/{model_id}")

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

        canonical_id = canonical_model_id(f"anthropic/{model_id}")

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

        canonical_id = canonical_model_id(model_id if "/" in model_id else f"hyperbolic/{model_id}")

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
        canonical_id = canonical_model_id(model_id)  # Already has provider/ prefix, normalize case

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

        canonical_id = canonical_model_id(f"deepseek/{model_id}")

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

        canonical_id = canonical_model_id(f"moonshotai/{model_id}")

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
# ENGY DIRECT API CONNECTOR (no auth)
# ============================================

def fetch_engy_direct():
    """Fetch model catalog and pricing directly from engy.ai's API.

    No auth required. Returns (endpoints, new_models).
    engy hosts open-source models (DeepSeek, GLM, Kimi, Qwen) with
    per-token pricing in the OpenRouter format (prompt/completion fields).
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Fetching engy direct API...")

    try:
        resp = requests.get(ENGY_API, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        models = data.get("data", [])
        print(f"  engy API returned {len(models)} models")
    except Exception as e:
        print(f"  ERROR fetching engy API: {e}")
        return [], []

    # engy hosts models from multiple owners. Map flat IDs to canonical
    # provider/model IDs so they merge with existing DB rows.
    ENGY_MODEL_MAP = {
        "deepseek-v4-flash-0731": "deepseek/deepseek-v4-flash-0731",
        "glm-5.2": "z-ai/glm-5.2",
        "kimi-k3": "moonshotai/kimi-k3",
        "qwen3.6-35b-a3b": "qwen/qwen3.6-35b-a3b",
    }

    endpoints = []
    new_models = []

    for m in models:
        raw_id = m.get("id", "")
        if not raw_id:
            continue

        pricing = m.get("pricing", {})
        prompt_price = pricing.get("prompt")
        completion_price = pricing.get("completion")

        if prompt_price is None or completion_price is None:
            continue
        if float(prompt_price) <= 0 and float(completion_price) <= 0:
            continue

        # Per-token -> per-million
        input_price = round(float(prompt_price) * 1_000_000, 6)
        output_price = round(float(completion_price) * 1_000_000, 6)
        blended = round((BLENDED_INPUT_WEIGHT * input_price) + (BLENDED_OUTPUT_WEIGHT * output_price), 6)

        canonical_id = ENGY_MODEL_MAP.get(raw_id, canonical_model_id(raw_id))

        endpoints.append({
            "endpoint_provider": "Engy",
            "model_id": canonical_id,
            "input_price_per_m": input_price,
            "output_price_per_m": output_price,
            "blended_price_per_m": blended,
            "context_length": m.get("context_length"),
            "source": "engy_direct",
            "raw_data": {
                "engy_id": raw_id,
                "owned_by": m.get("owned_by", "engy"),
                "cache_read_price": float(pricing["input_cache_read"]) * 1_000_000 if pricing.get("input_cache_read") else None,
            },
        })

        new_models.append({
            "model_id": canonical_id,
            "name": raw_id.replace("-", " "),
            "provider": canonical_id.split("/")[0],
            "context_length": m.get("context_length"),
            "is_reasoning": False,
            "modality": "text",
        })

    print(f"  engy: {len(endpoints)} priced endpoints")
    return endpoints, new_models


# ============================================
# TENSORX DIRECT API CONNECTOR (auth)
# ============================================

def fetch_tensorx_direct():
    """Fetch TensorX pricing via their models-page scraper.

    TensorX hosts models from Z-AI, DeepSeek, Qwen, Moonshot, Minimax etc.
    Its /v1/models API needs a key and returns catalog-only (no pricing).
    The authoritative per-model pricing lives on tensorx.ai/models/ (server-
    rendered HTML with data-name + price rows). Delegates to
    tensorx_pricing.fetch_tensorx_pricing(). The data-name attributes are
    already our canonical lowercase provider/model IDs.

    Returns (endpoints, new_models).
    """
    # Delegate to the models-page scraper (no API key needed).
    return _fetch_tensorx_pricing()


# ============================================
# OPENRELAY DIRECT PRICING SCRAPER (HTML)
# ============================================

def fetch_openrelay_direct():
    """Fetch OpenRelay token pricing from their catalog + pricing HTML pages.

    OpenRelay's /v1/models endpoint is auth-gated, but their per-model token
    rates are published as server-rendered HTML tables on the inference-catalog
    and inference-pricing pages. Delegates to openrelay_pricing.py.

    Returns (endpoints, new_models).
    """
    return _fetch_openrelay_pricing()


# ============================================
# SARVAM AI DIRECT PRICING SCRAPER (HTML + FX)
# ============================================

def fetch_sarvam_direct():
    """Fetch Sarvam AI chat-LLM token pricing (INR->USD).

    Sarvam exposes an OpenAI-compatible /v1/models endpoint (public) but does
    NOT expose token pricing machine-readably - it lives on the /api-pricing
    HTML page. Delegates to sarvam_pricing.py which scrapes the two chat
    models and converts INR to USD at a live FX rate.
    """
    return _fetch_sarvam_pricing()


# ============================================
# REPLICATE DIRECT CONNECTOR
# ============================================

REPLICATE_PRICING_URL = "https://replicate.com/pricing"

def fetch_replicate_direct():
    """Fetch text model pricing from Replicate's public pricing page.

    Replicate's API requires auth, but their /pricing page lists official
    text models with per-thousand-output-token and per-million-input-token
    pricing. We scrape the page HTML for model entries.

    Only text models (per-token pricing) are included. Image/video models
    (per-output pricing) are skipped as they don't fit the $/M token model.

    Returns (endpoints, new_models).
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Fetching Replicate pricing page...")

    try:
        resp = requests.get(REPLICATE_PRICING_URL, timeout=30, headers={
            "User-Agent": "InferenceIndexer/1.0 (pricing bot)"
        })
        resp.raise_for_status()
        html = resp.text
        print(f"  Replicate pricing page: {len(html)} bytes")
    except Exception as e:
        print(f"  ERROR fetching Replicate pricing: {e}")
        return [], []

    # Parse model entries from the HTML
    # The pricing page is a Next.js app. After stripping HTML tags and comments,
    # the text reads: "anthropic/claude-3.7-sonnet ... $0.015 / thousand output tokens $3.00 / million input tokens"
    import re

    # Strip HTML to get plain text
    clean = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    clean = re.sub(r'<style[^>]*>.*?</style>', '', clean, flags=re.DOTALL)
    clean = re.sub(r'<!--.*?-->', '', clean, flags=re.DOTALL)
    clean = re.sub(r'<[^>]+>', ' ', clean)
    clean = re.sub(r'&#x27;', "'", clean)
    clean = re.sub(r'\s+', ' ', clean)

    # Find: model_slug ... $price / thousand output tokens ... $price / million input tokens
    # The model slug appears before the pricing text, separated by description text
    pricing_blocks = re.findall(
        r'([a-z0-9_-]+/[a-z0-9._-]+)\s+(?:[A-Z][^$]*?)?\$[\d.]+\s*/\s*thousand\s*output\s*tokens\s+\$[\d.]+\s*/\s*million\s*input\s*tokens',
        clean, re.IGNORECASE
    )

    # Also extract the actual prices
    full_matches = re.findall(
        r'([a-z0-9_-]+/[a-z0-9._-]+)\s+(?:[A-Z][^$]*?)?\$(\d+\.?\d*)\s*/\s*thousand\s*output\s*tokens\s+\$(\d+\.?\d*)\s*/\s*million\s*input\s*tokens',
        clean, re.IGNORECASE
    )

    endpoints = []
    new_models = []
    skipped = 0

    for model_slug, output_per_1k_str, input_per_1m_str in full_matches:
        # Convert: $X per 1K tokens -> $X*1000 per 1M tokens
        output_per_1k = float(output_per_1k_str)
        input_per_1m = float(input_per_1m_str)

        output_per_m = round(output_per_1k * 1000, 6)
        input_per_m = round(input_per_1m, 6)

        # Skip if both are zero
        if input_per_m == 0 and output_per_m == 0:
            skipped += 1
            continue

        # Map Replicate model slug to our model_id format
        # Replicate uses owner/model, we use owner/model (same format)
        model_id = model_slug.lower()

        # Map known Replicate slugs to our existing model IDs where possible
        replicate_to_ii = {
            "anthropic/claude-3.7-sonnet": "anthropic/claude-sonnet-4.5",
            "deepseek-ai/deepseek-r1": "deepseek/deepseek-r1",
        }
        model_id = replicate_to_ii.get(model_id, model_id)

        blended = round((input_per_m + output_per_m) / 2, 6)

        ep = {
            "model_id": model_id,
            "endpoint_provider": "Replicate",
            "input_price_per_m": input_per_m,
            "output_price_per_m": output_per_m,
            "blended_price_per_m": blended,
            "context_length": None,
            "source": "replicate_direct",
            "raw_data": {
                "provider": "replicate",
                "slug": model_slug,
                "input_per_m": input_per_m,
                "output_per_m": output_per_m,
                "url": f"https://replicate.com/{model_slug}",
            }
        }
        endpoints.append(ep)

    print(f"  Replicate: {len(endpoints)} text models with token pricing ({skipped} skipped)")
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
                        endpoint_provider, input_price_per_m, output_price_per_m, blended_price_per_m, source
                    FROM model_endpoints
                    WHERE model_id = %s AND fetched_at >= NOW() - INTERVAL '24 hours'
                    ORDER BY endpoint_provider, fetched_at DESC
                """, (m["model_id"],))
                rows = cur.fetchall()
                # Apply endpoint pricing whenever there is AT LEAST ONE priced
                # endpoint, not just for multi-provider models. The old
                # `len(rows) > 1` guard left single-endpoint models unpriced
                # even when their sole provider served+published a price
                # (e.g. claude-haiku-4-5 only on DeepInfra). Fix: median over
                # whatever priced endpoints exist.
                if rows:
                    blended_prices = [r[3] for r in rows if r[3] and r[3] > 0]
                    input_prices = [r[1] for r in rows if r[1] and r[1] > 0]
                    output_prices = [r[2] for r in rows if r[2] and r[2] > 0]
                    endpoint_sources = [r[4] for r in rows if r[3] and r[3] > 0 and r[4]]
                    if blended_prices:
                        m["blended_price_per_m"] = compute_median(blended_prices)
                        m["input_price_per_m"] = compute_median(input_prices) if input_prices else m["input_price_per_m"]
                        m["output_price_per_m"] = compute_median(output_prices) if output_prices else m["output_price_per_m"]
                        m["source_count"] = len(blended_prices)
                        # Determine source label: direct, aggregator, or blended
                        has_direct = any(s and s != "openrouter" for s in endpoint_sources)
                        has_aggregator = any(s and s == "openrouter" for s in endpoint_sources)
                        if has_direct and has_aggregator:
                            m["source_label"] = "blended"
                        elif has_direct:
                            m["source_label"] = "direct"
                        else:
                            m["source_label"] = "aggregator"
                        # Recalculate SIT-adjusted price with updated blended price
                        m["sit_adjusted_price"] = calculate_sit_adjusted_price(
                            m["blended_price_per_m"], m.get("reasoning_multiplier", 1.0), m.get("aa_index_score")
                        )
                    else:
                        m["source_count"] = 1
                        m["source_label"] = "aggregator"
                else:
                    m["source_count"] = 1
                    m["source_label"] = "aggregator"
            cur.close()
            conn.close()
        except Exception as e:
            print(f"  WARN: Could not load cached endpoints: {e}")
            for m in models:
                m["source_count"] = 1
                m["source_label"] = "aggregator"
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
            # Determine source label from endpoint sources
            ep_sources = [ep.get("source", "openrouter") for ep in normalized_eps]
            has_direct = any(s != "openrouter" for s in ep_sources)
            has_aggregator = any(s == "openrouter" for s in ep_sources)
            if has_direct and has_aggregator:
                m["source_label"] = "blended"
            elif has_direct:
                m["source_label"] = "direct"
            else:
                m["source_label"] = "aggregator"
            # Recalculate SIT-adjusted price with updated blended price
            m["sit_adjusted_price"] = calculate_sit_adjusted_price(
                m["blended_price_per_m"], m.get("reasoning_multiplier", 1.0), m.get("aa_index_score")
            )
        else:
            m["source_count"] = 1
            m["source_label"] = "aggregator"
        
        # Store endpoint data for DB insert
        for ep in normalized_eps:
            ep["model_id"] = m["model_id"]
            all_endpoint_data.append(ep)
        
        # Rate limit: be gentle with OpenRouter
        time.sleep(0.3)
    
    print(f"  Endpoints fetched. {multi_provider_count} models have multiple providers.")
    return models, all_endpoint_data

# ============================================
# ARTIFICIAL ANALYSIS SCORES (direct scrape)
# ============================================

def fetch_aa_scores():
    """Fetch Artificial Analysis Intelligence Index scores directly from AA.

    AA's leaderboard page embeds all model scores in Next.js RSC data.
    This scraper extracts them so we don't depend on OpenRouter's stale copy.

    Returns dict: { aa_slug: { "name": str, "score": float, "estimated": bool } }
    """
    import re
    print(f"\n[{datetime.now(timezone.utc).isoformat()}] Fetching AA leaderboard scores...")
    resp = requests.get(AA_LEADERBOARD_URL, timeout=30, headers={"User-Agent": "InferenceIndexer/1.0"})
    if resp.status_code != 200:
        print(f"  WARN: AA leaderboard returned {resp.status_code}")
        return {}

    html = resp.text

    # Pattern: "name":"Model Name",...,"slug":"model-slug",...,"intelligenceIndex":SCORE,...
    # The JSON is escaped with backslashes in Next.js RSC data.
    # Between name and slug there's shortName; between slug and intelligenceIndex
    # there are many fields (releaseDate, isReasoning, modelCreator*, etc.)
    # Use [^\\""]+ to match field values without crossing into next field.
    pattern = r'\\"name\\":\\"([^"]+)\\"[^}]*?\\"slug\\":\\"([^"]+)\\"[^}]*?\\"intelligenceIndex\\":([0-9.]+),\\"intelligenceIndexIsEstimated\\":(true|false)'
    matches = re.findall(pattern, html, re.DOTALL)

    scores = {}
    for name, slug, score_str, est_str in matches:
        if slug not in scores:
            scores[slug] = {
                "name": name,
                "score": float(score_str),
                "estimated": est_str == "true",
            }

    print(f"  AA leaderboard: {len(scores)} models with scores")

    # Also build a name->slug mapping for fuzzy matching against OpenRouter IDs
    # AA uses hyphens, OpenRouter uses slashes and dots
    return scores


def match_aa_score(model_id, model_name, aa_scores):
    """Match an OpenRouter model ID/name to an AA leaderboard entry.

    Tries multiple matching strategies:
    1. Direct slug match (e.g. "deepseek-v4-pro" in both)
    2. Name-based fuzzy match
    3. Partial model ID match
    """
    import re
    if not aa_scores:
        return None

    # Strategy 1: Try to derive AA slug from model_id
    # OpenRouter: "deepseek/deepseek-v4-pro-0813" -> AA slug might be "deepseek-v4-pro"
    # Strip provider prefix, normalize
    parts = model_id.split("/")
    model_part = parts[-1] if len(parts) > 1 else model_id
    # Remove version suffixes for matching (0813, 0731, etc.)
    base = re.sub(r'-\d{4}$', '', model_part)  # Remove trailing -0813
    base = base.replace(".", "-").replace("_", "-")

    # Try direct slug match
    if base in aa_scores:
        return aa_scores[base]["score"]

    # Strategy 2: Try without version suffix
    # e.g. "deepseek-v4-pro-0813" -> "deepseek-v4-pro"
    base_no_version = re.sub(r'-\d{3,4}$', '', base)
    if base_no_version in aa_scores:
        return aa_scores[base_no_version]["score"]

    # Strategy 3: Check if any AA slug is a substring of our model ID
    model_lower = model_id.lower()
    for slug, data in aa_scores.items():
        if slug in model_lower or model_lower in slug:
            return data["score"]

    # Strategy 4: Name-based match (normalized, lowercase, no spaces/punctuation)
    def normalize(s):
        return re.sub(r'[^a-z0-9]', '', s.lower())

    norm_name = normalize(model_name or model_id)
    for slug, data in aa_scores.items():
        norm_aa_name = normalize(data["name"])
        if norm_name == norm_aa_name:
            return data["score"]
        # Check partial match (AA name contains model name or vice versa)
        if len(norm_name) > 5 and (norm_name in norm_aa_name or norm_aa_name in norm_name):
            return data["score"]

    return None


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

    `tier_avgs` should be the DAILY-STABLE tier medians (per UTC date) so scores
    stay constant across hourly runs within a day. Median is the SIT-adjusted
    price median, not the blended median. If a tier is missing from `tier_avgs`,
    fall back to computing it from the passed models for that run only.
    """
    # Ensure every tier present in models has a stable median; fall back to
    # recomputing transiently only for tiers the stable set omits.
    tier_adjusted_prices = {}
    for m in models:
        tier = m["tier"]
        adj = m.get("sit_adjusted_price")
        if adj and adj > 0:
            tier_adjusted_prices.setdefault(tier, []).append(adj)

    for tier, prices in tier_adjusted_prices.items():
        if tier not in tier_avgs and prices:
            tier_avgs[tier] = round(_median(prices), 8)

    for m in models:
        tier_median = tier_avgs.get(m["tier"])
        adj = m.get("sit_adjusted_price")
        if tier_median and tier_median > 0 and adj and adj > 0:
            ratio = adj / tier_median
            score = round(ratio * 100)
            m["sit_score"] = max(score, 1)
        else:
            # No AA score = no SIT score
            m["sit_score"] = None
    return models

# ---------------------------------------------------------------------------
# DAILY-STABLE SIT MEDIANS
#
# Per-model SIT scores are a *relative* ratio: (model SIT-adjusted price /
# tier median of SIT-adjusted prices) * 100. If the median is recomputed from
# the transient hourly run set, catalog churn (a model appearing/disappearing)
# moves the median and every score fluctuates within a single day with no price
# change. Customers/agents cross-checking scores see erratic, unreliable data.
#
# Fix: compute the SIT-adjusted tier median ONCE per UTC date from the
# authoritative `latest_prices` view (the complete set of active models), cache
# it for the day, and use the same median for every hourly run that day. Scores
# then change only when the *daily* median genuinely shifts, never hourly churn.
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# DAILY-STABLE SIT MEDIANS
#
# Per-model SIT scores are a *relative* ratio: (model SIT-adjusted price /
# tier median of SIT-adjusted prices) * 100. If the median is recomputed from
# the transient hourly run set, catalog churn (a model appearing/disappearing)
# moves the median and every score fluctuates within a single day with no price
# change. Customers/agents cross-checking scores see erratic, unreliable data.
#
# Fix: persist ONE SIT-adjusted tier median per UTC date in the
# `daily_tier_medians` table. The first run of a UTC date computes + stores it
# from the authoritative `latest_prices` view (complete active model set); all
# subsequent runs (separate cron processes!) read the stored value. Scores then
# change only when the *daily* median genuinely shifts, never hourly catalog
# churn.
# ---------------------------------------------------------------------------

def _cache_day_key():
    """UTC-date key for the daily tier-median table (rotates at UTC midnight)."""
    return datetime.now(timezone.utc).date().isoformat()

def _get_or_create_daily_medians(conn, day=None):
    """Return the SIT-adjusted tier median for the current UTC date.

    Reads from `daily_tier_medians`. If no row exists for today, computes it
    from `latest_prices` and stores it (first run of the day wins). Returns a
    dict {tier: median} — possibly empty if no data yet.
    """
    if day is None:
        day = _cache_day_key()
    medians = {}

    if conn is None:
        return medians

    # 1) Try to read today's persisted medians.
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT tier, sit_adjusted_median
            FROM daily_tier_medians
            WHERE date = %s
        """, (day,))
        rows = cur.fetchall()
        if rows:
            medians = {tier: float(m) for tier, m in rows}
            # Check all tiers are present (in case a tier was added mid-day we
            # still want a complete set; missing tiers fall back at caller).
            return medians
    except Exception:
        conn.rollback()
    finally:
        cur.close()

    # 2) No persisted value for today yet -> compute from the complete active
    #    model set and persist (first run of the UTC date wins).
    tier_prices = {}
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT m.tier, lp.sit_adjusted_price
            FROM latest_prices lp
            JOIN models m ON lp.model_id = m.id
            WHERE m.is_active = TRUE
              AND lp.sit_adjusted_price > 0
        """)
        for tier, adj in cur.fetchall():
            if adj and adj > 0:
                tier_prices.setdefault(tier, []).append(float(adj))
        cur.close()
    except Exception:
        conn.rollback()
        if cur:
            cur.close()
        return medians

    if not tier_prices:
        return medians

    now = datetime.now(timezone.utc)
    for tier, prices in tier_prices.items():
        medians[tier] = round(_median(prices), 8)

    # Persist atomically; ignore duplicate-key race from concurrent first runs.
    try:
        cur = conn.cursor()
        for tier, m in medians.items():
            cur.execute("""
                INSERT INTO daily_tier_medians (date, tier, sit_adjusted_median, model_count)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (date, tier) DO NOTHING
            """, (day, tier, m, len(tier_prices[tier])))
        conn.commit()
        cur.close()
    except Exception:
        conn.rollback()
        try:
            cur.close()
        except Exception:
            pass

    return medians

def get_stable_tier_medians(conn):
    """Return the counter global — daily tier medians stable for the UTC date.

    Reads from the persisted `daily_tier_medians` table (handles separate
    process invocations across hourly cron runs).
    """
    return _get_or_create_daily_medians(conn)

def reset_daily_median_cache():
    """No-op kept for API compatibility (medians are DB-persisted now)."""
    return None

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
            m["model_id"], m.get("source_label", "aggregator"),
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
        # For index points: the base is the EARLIEST stored price for this tier
        # (anchored to whenever we first have real data). index_points =
        # (current_price / base_price) * 1000, so 1000 = base date.
        # NOTE: We anchor to the earliest existing row, NOT a hardcoded
        # BASE_DATE (2026-08-03), because no Aug-3 data exists (earliest is
        # Aug 4). A hardcoded BASE_DATE with no row made the index freeze at
        # 1000 forever. See data_integrity_check.py #7.
        cur.execute("""
            SELECT sit_price FROM sit_index_values 
            WHERE tier = %s
            ORDER BY date ASC LIMIT 1
        """, (tier,))
        row = cur.fetchone()

        if row:
            base_price = row[0]
            index_points = calculate_index_points(data["price"], base_price)
        elif today == BASE_DATE:
            # First ever calculation on base date
            index_points = BASE_VALUE
        else:
            # No base price yet, anchor today as the base
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
    
    # Fetch AA scores directly from Artificial Analysis (overrides stale OpenRouter scores)
    aa_scores = fetch_aa_scores()
    
    # Normalize
    normalized = [normalize_model(m) for m in raw_models]
    
    # Override AA scores with direct-from-AA values (OpenRouter's copy lags by days/weeks)
    if aa_scores:
        updated = 0
        for m in normalized:
            direct_score = match_aa_score(m["model_id"], m.get("name", ""), aa_scores)
            if direct_score is not None:
                old_score = m.get("aa_index_score")
                m["aa_index_score"] = direct_score
                if old_score != direct_score:
                    updated += 1
        print(f"  AA direct scores: {updated} models updated (out of {len(normalized)})")

    # Apply median/endpoint pricing BEFORE filtering. Models with no catalog
    # price but a real price in model_endpoints (single-provider models like
    # claude-haiku-4-5 on DeepInfra) must not be dropped by filter_priced.
    # Reordering so apply_median_pricing enriches first means filter_priced
    # keeps them priced via their endpoints.
    if args.fetch_endpoints:
        print(f"\n[{datetime.now(timezone.utc).isoformat()}] Fetching provider endpoints (daily mode)...")
        enriched, endpoint_data = apply_median_pricing(normalized, fetch_endpoints=True)
    else:
        enriched = apply_median_pricing(normalized, fetch_endpoints=False)
        endpoint_data = []

    # Filter to only models with pricing (catalog or endpoint-derived)
    priced = filter_priced(enriched)
    
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
    if groq_endpoints:
        endpoint_data.extend(groq_endpoints)
        print(f"  Groq direct: {len(groq_endpoints)} endpoints added")
    
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
    if tensorx_endpoints:
        endpoint_data.extend(tensorx_endpoints)
        print(f"  TensorX direct: {len(tensorx_endpoints)} endpoints added")
    
    # engy direct (no auth, pricing included)
    engy_endpoints, engy_new_models = fetch_engy_direct()
    if engy_endpoints:
        endpoint_data.extend(engy_endpoints)
        print(f"  engy direct: {len(engy_endpoints)} endpoints added")

    # OpenRelay direct (HTML scraped pricing, no API key)
    openrelay_endpoints, openrelay_new_models = fetch_openrelay_direct()
    if openrelay_endpoints:
        endpoint_data.extend(openrelay_endpoints)
        print(f"  OpenRelay direct: {len(openrelay_endpoints)} endpoints added")

    # Sarvam AI direct (HTML scraped pricing, INR->USD, no API key)
    sarvam_endpoints, sarvam_new_models = fetch_sarvam_direct()
    if sarvam_endpoints:
        endpoint_data.extend(sarvam_endpoints)
        print(f"  Sarvam direct: {len(sarvam_endpoints)} endpoints added")

    # Replicate direct (pricing page scrape, no API key needed)
    replicate_endpoints, replicate_new_models = fetch_replicate_direct()
    if replicate_endpoints:
        endpoint_data.extend(replicate_endpoints)
        print(f"  Replicate direct: {len(replicate_endpoints)} endpoints added")
    
    # Calculate tier averages and SIT scores
    # Use DAILY-STABLE tier medians so per-model SIT scores are constant across
    # the day's hourly runs (catalog churn no longer flips the median hourly).
    tier_avgs = get_stable_tier_medians(get_db_connection())
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
        if tensorx_endpoints:
            upsert_venice_models(conn, tensorx_new_models, priced)
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
        if engy_new_models:
            upsert_venice_models(conn, engy_new_models, priced)
        if openrelay_new_models:
            upsert_venice_models(conn, openrelay_new_models, priced)
        if sarvam_new_models:
            upsert_venice_models(conn, sarvam_new_models, priced)
        
        if endpoint_data:
            insert_endpoints(conn, endpoint_data)
        insert_price_snapshots(conn, priced)
        
        # Recalculate composite using usage-weighted top 50 with quality gate
        # (the API methodology, not the simple median used in calculate_tier_indices)
        composite_data = calculate_composite_usage_weighted(conn)
        if composite_data["price"] > 0:
            indices["composite"] = composite_data
        
        insert_sit_values(conn, indices, today)
        
        # Refresh materialized views so the API sees fresh data
        # (latest_prices, price_changes_24h, price_changes_7d are MATVIEWs for performance)
        cur = conn.cursor()
        cur.execute("REFRESH MATERIALIZED VIEW latest_prices")
        cur.execute("REFRESH MATERIALIZED VIEW price_changes_24h")
        cur.execute("REFRESH MATERIALIZED VIEW price_changes_7d")
        conn.commit()
        print(f"  Refreshed materialized views (latest_prices, price_changes_24h, price_changes_7d)")
        
        print(f"\n✓ Pipeline complete at {datetime.now(timezone.utc).isoformat()}")
    except Exception as e:
        conn.rollback()
        print(f"\n✗ Pipeline error: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    main()
