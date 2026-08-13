#!/usr/bin/env python3
"""
Niche model pricing scrapers for InferenceIndexer.

Collects pricing for ALL model types beyond text generation:
- Embeddings (delegates to embedding_pricing.py)
- TTS (text-to-speech)
- STT (speech-to-text / transcription)
- Rerankers
- Image generation
- Video generation

Data is stored in the same models/price_snaptables tables with pricing_unit
indicating the unit of measure (per_million_tokens, per_minute, per_image, per_second).

This runs hourly via cron alongside the main pipeline.
"""

import os
import json
import requests
from datetime import datetime, timezone

from pipeline import (
    get_db_connection, upsert_models, insert_endpoints, insert_price_snapshots,
    canonical_model_id, BLENDED_INPUT_WEIGHT, BLENDED_OUTPUT_WEIGHT,
)
from embedding_pricing import fetch_all_embeddings
from provider_pricing import parse_money


# ---------------------------------------------------------------------------
# TTS (Text-to-Speech) - Priced per 1M tokens or per character
# ---------------------------------------------------------------------------

def fetch_openai_tts():
    """OpenAI TTS models.

    From pricing page (Aug 2026):
    - gpt-4o-tts: $5/M input (text), $40/M output (audio)
    - gpt-4o-mini-tts: $2.50/M input (text), $20/M output (audio)
    - tts-1: $15/M input (text), N/A (flat per-char pricing)
    - tts-1-hd: $30/M input (text), N/A (flat per-char pricing)

    Older models (tts-1, tts-1-hd) charge per character but we store as
    per_million_tokens for consistency. 1 token ~= 4 chars, so per 1M tokens
    = per 4M chars. tts-1 = $15/1M chars = $3.75/1M tokens equivalent.
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Loading OpenAI TTS (static)...")

    models = {
        "gpt-4o-tts": {
            "canonical_id": "openai/gpt-4o-tts",
            "name": "OpenAI: GPT-4o TTS",
            "input_price": 5.0,
            "output_price": 40.0,
        },
        "gpt-4o-mini-tts": {
            "canonical_id": "openai/gpt-4o-mini-tts",
            "name": "OpenAI: GPT-4o Mini TTS",
            "input_price": 2.5,
            "output_price": 20.0,
        },
        "tts-1": {
            "canonical_id": "openai/tts-1",
            "name": "OpenAI: TTS-1",
            "input_price": 15.0,
            "output_price": 0.0,
        },
        "tts-1-hd": {
            "canonical_id": "openai/tts-1-hd",
            "name": "OpenAI: TTS-1 HD",
            "input_price": 30.0,
            "output_price": 0.0,
        },
    }

    return _build_endpoints(models, "OpenAI", "openai_tts", "tts", "per_million_tokens")


def fetch_google_tts():
    """Google Gemini TTS models.

    From Google pricing page (Aug 2026):
    - gemini-2.5-flash-preview-tts: $1.00/M input (text), $20.00/M output (audio)
    - gemini-2.5-pro-preview-tts: higher tier pricing
    - gemini-3.1-flash-tts-preview: $1.00/M input (text), $20.00/M output (audio)

    Audio tokens: 25 tokens per second of audio.
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Loading Google TTS (static)...")

    models = {
        "gemini-2.5-flash-preview-tts": {
            "canonical_id": "google/gemini-2.5-flash-preview-tts",
            "name": "Google: Gemini 2.5 Flash TTS",
            "input_price": 1.0,
            "output_price": 20.0,
        },
        "gemini-2.5-pro-preview-tts": {
            "canonical_id": "google/gemini-2.5-pro-preview-tts",
            "name": "Google: Gemini 2.5 Pro TTS",
            "input_price": 3.0,
            "output_price": 50.0,
        },
        "gemini-3.1-flash-tts-preview": {
            "canonical_id": "google/gemini-3.1-flash-tts-preview",
            "name": "Google: Gemini 3.1 Flash TTS",
            "input_price": 1.0,
            "output_price": 20.0,
        },
    }

    return _build_endpoints(models, "Google", "google_tts", "tts", "per_million_tokens")


def fetch_elevenlabs_tts():
    """ElevenLabs TTS pricing.

    From their pricing page (Aug 2026):
    - Pro: $0.30 per 1000 characters ~= $1.20/1M tokens
    - Creator: $0.22 per 1000 characters ~= $0.88/1M tokens
    We track the per-character price converted to per-1M-tokens (4 chars/token).
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Loading ElevenLabs TTS (static)...")

    models = {
        "eleven-multilingual-v2": {
            "canonical_id": "elevenlabs/eleven-multilingual-v2",
            "name": "ElevenLabs: Multilingual v2",
            "input_price": 1.20,  # ~$0.30/1k chars * 4 = per 1M tokens
            "output_price": 0.0,
        },
        "eleven-turbo-v2": {
            "canonical_id": "elevenlabs/eleven-turbo-v2",
            "name": "ElevenLabs: Turbo v2",
            "input_price": 0.88,  # ~$0.22/1k chars
            "output_price": 0.0,
        },
    }

    return _build_endpoints(models, "ElevenLabs", "elevenlabs_tts", "tts", "per_million_tokens")


# ---------------------------------------------------------------------------
# STT (Speech-to-Text / Transcription) - Priced per minute
# ---------------------------------------------------------------------------

def fetch_openai_stt():
    """OpenAI transcription models.

    From pricing page (Aug 2026):
    - gpt-transcribe: $0.0045/minute
    - gpt-4o-transcribe: $0.006/minute
    - gpt-4o-mini-transcribe: $0.003/minute
    - gpt-realtime-whisper: $0.017/minute
    - gpt-live-transcribe: $0.017/minute
    - gpt-realtime-translate: $0.034/minute
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Loading OpenAI STT (static)...")

    models = {
        "gpt-transcribe": {
            "canonical_id": "openai/gpt-transcribe",
            "name": "OpenAI: GPT Transcribe",
            "input_price": 0.0045,  # per minute
            "output_price": 0.0,
        },
        "gpt-4o-transcribe": {
            "canonical_id": "openai/gpt-4o-transcribe",
            "name": "OpenAI: GPT-4o Transcribe",
            "input_price": 0.006,
            "output_price": 0.0,
        },
        "gpt-4o-mini-transcribe": {
            "canonical_id": "openai/gpt-4o-mini-transcribe",
            "name": "OpenAI: GPT-4o Mini Transcribe",
            "input_price": 0.003,
            "output_price": 0.0,
        },
        "gpt-realtime-whisper": {
            "canonical_id": "openai/gpt-realtime-whisper",
            "name": "OpenAI: Realtime Whisper",
            "input_price": 0.017,
            "output_price": 0.0,
        },
        "gpt-live-transcribe": {
            "canonical_id": "openai/gpt-live-transcribe",
            "name": "OpenAI: Live Transcribe",
            "input_price": 0.017,
            "output_price": 0.0,
        },
        "gpt-realtime-translate": {
            "canonical_id": "openai/gpt-realtime-translate",
            "name": "OpenAI: Realtime Translate",
            "input_price": 0.034,
            "output_price": 0.0,
        },
    }

    return _build_endpoints(models, "OpenAI", "openai_stt", "stt", "per_minute")


def fetch_google_stt():
    """Google STT pricing.

    Google Cloud Speech-to-Text:
    - Standard: $0.024/minute (first 60 min free/month)
    - Enhanced: $0.039/minute
    - Chirp 2 (Gemini-powered): $0.035/minute

    We store the standard rate. Enhanced models tracked separately.
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Loading Google STT (static)...")

    models = {
        "chirp-2": {
            "canonical_id": "google/chirp-2",
            "name": "Google: Chirp 2 (Gemini STT)",
            "input_price": 0.035,  # per minute
            "output_price": 0.0,
        },
        "chirp": {
            "canonical_id": "google/chirp",
            "name": "Google: Chirp",
            "input_price": 0.024,
            "output_price": 0.0,
        },
    }

    return _build_endpoints(models, "Google", "google_stt", "stt", "per_minute")


def fetch_deepgram_stt():
    """Deepgram STT pricing.

    - Nova-3: $0.0043/minute (pay-as-you-go)
    - Nova-2: $0.0043/minute
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Loading Deepgram STT (static)...")

    models = {
        "nova-3": {
            "canonical_id": "deepgram/nova-3",
            "name": "Deepgram: Nova 3",
            "input_price": 0.0043,  # per minute
            "output_price": 0.0,
        },
        "nova-2": {
            "canonical_id": "deepgram/nova-2",
            "name": "Deepgram: Nova 2",
            "input_price": 0.0043,
            "output_price": 0.0,
        },
    }

    return _build_endpoints(models, "Deepgram", "deepgram_stt", "stt", "per_minute")


# ---------------------------------------------------------------------------
# RERANKERS - Priced per 1M tokens or per search
# ---------------------------------------------------------------------------

def fetch_cohere_rerankers():
    """Cohere reranker pricing.

    - rerank-v3.5: $2.00/1M search queries (1000 docs/query)
    - rerank-english-v3.0: $2.00/1M search queries
    - rerank-multilingual-v3.0: $2.00/1M search queries

    Stored as per_million_tokens with the per-query cost normalized.
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Loading Cohere rerankers (static)...")

    models = {
        "rerank-v3.5": {
            "canonical_id": "cohere/rerank-v3.5",
            "name": "Cohere: Rerank v3.5",
            "input_price": 2.0,  # per 1000 searches, stored as per_million_tokens
            "output_price": 0.0,
        },
        "rerank-english-v3.0": {
            "canonical_id": "cohere/rerank-english-v3.0",
            "name": "Cohere: Rerank English v3.0",
            "input_price": 2.0,
            "output_price": 0.0,
        },
        "rerank-multilingual-v3.0": {
            "canonical_id": "cohere/rerank-multilingual-v3.0",
            "name": "Cohere: Rerank Multilingual v3.0",
            "input_price": 2.0,
            "output_price": 0.0,
        },
    }

    return _build_endpoints(models, "Cohere", "cohere_rerank", "reranker", "per_million_tokens")


def fetch_voyage_rerankers():
    """Voyage AI reranker pricing.

    From Voyage pricing page:
    - rerank-2: $0.05 per 1M tokens
    - rerank-2-lite: $0.02 per 1M tokens
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Loading Voyage rerankers (static)...")

    models = {
        "rerank-2": {
            "canonical_id": "voyageai/rerank-2",
            "name": "Voyage AI: Rerank 2",
            "input_price": 0.05,
            "output_price": 0.0,
        },
        "rerank-2-lite": {
            "canonical_id": "voyageai/rerank-2-lite",
            "name": "Voyage AI: Rerank 2 Lite",
            "input_price": 0.02,
            "output_price": 0.0,
        },
    }

    return _build_endpoints(models, "Voyage AI", "voyage_rerank", "reranker", "per_million_tokens")


def fetch_jina_rerankers():
    """Jina reranker pricing from their API.

    Jina API returns per-token pricing. We convert to per-1M-tokens.
    - jina-reranker-v3: $0.05/1M tokens (0.00000005 per token)
    - jina-reranker-v3.5: same
    - jina-reranker-m0: same
    - jina-colbert-v2: same
    - jina-colbert-v1-en: same
    - jina-reranker-v2-base-multilingual: same
    - jina-reranker-v1-tiny-en: $0.02/1M tokens
    - jina-reranker-v1-turbo-en: $0.02/1M tokens
    - jina-reranker-v1-base-en: $0.02/1M tokens

    Also includes reader models:
    - reader-lm-0.5b: $0.02/1M tokens
    - reader-lm-1.5b: $0.02/1M tokens
    - readerlm-v2: $0.02/1M tokens
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Fetching Jina rerankers/readers...")

    try:
        resp = requests.get("https://api.jina.ai/v1/models", timeout=30, headers={
            "User-Agent": "Mozilla/5.0 (compatible; InferenceIndexer/1.0)"
        })
        resp.raise_for_status()
        jina_models = resp.json().get("data", [])
    except Exception as e:
        print(f"  ERROR fetching Jina models: {e}")
        return [], []

    endpoints = []
    new_models = []
    seen = set()

    for m in jina_models:
        mid = m.get("id", "")
        if not any(x in mid for x in ["reranker", "reader", "colbert"]):
            continue
        if mid in seen:
            continue
        seen.add(mid)

        pricing = m.get("pricing", {})
        prompt_price = float(pricing.get("prompt", 0))
        # Convert per-token to per-1M-tokens
        input_price = round(prompt_price * 1_000_000, 6)
        if input_price <= 0:
            continue

        output_price = 0.0
        blended = round(BLENDED_INPUT_WEIGHT * input_price + BLENDED_OUTPUT_WEIGHT * output_price, 6)

        # Determine modality
        if "reranker" in mid or "colbert" in mid:
            modality = "reranker"
        elif "reader" in mid:
            modality = "reader"
        else:
            modality = "reranker"

        # Determine context length
        ctx = m.get("context_length", 8192)

        endpoints.append({
            "endpoint_provider": "Jina",
            "model_id": mid,
            "input_price_per_m": input_price,
            "output_price_per_m": output_price,
            "blended_price_per_m": blended,
            "context_length": ctx,
            "source": "jina_reranker",
            "raw_data": {"name": m.get("name", mid), "pricing_unit": "per_million_tokens"},
        })
        new_models.append({
            "model_id": mid,
            "name": m.get("name", mid),
            "provider": "Jina",
            "context_length": ctx,
            "is_reasoning": False,
            "modality": modality,
            "pricing_unit": "per_million_tokens",
        })

    print(f"  Jina reranker/reader models with pricing: {len(endpoints)}")
    return endpoints, new_models


# ---------------------------------------------------------------------------
# IMAGE GENERATION - Priced per image
# ---------------------------------------------------------------------------

def fetch_openai_image_gen():
    """OpenAI image generation models.

    From pricing page (Aug 2026):
    - gpt-image-2: $8.00/M input tokens, $30.00/M output tokens (image tokens)
    - dall-e-3: $0.040/image (1024x1024), $0.080/image (1024x1792)
    - dall-e-2: $0.016/image (512x512), $0.018/image (1024x1024)

    DALL-E is per-image, gpt-image-2 is token-based.
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Loading OpenAI image gen (static)...")

    models = {
        "gpt-image-2": {
            "canonical_id": "openai/gpt-image-2",
            "name": "OpenAI: GPT Image 2",
            "input_price": 8.0,
            "output_price": 30.0,
            "pricing_unit": "per_million_tokens",
        },
        "dall-e-3": {
            "canonical_id": "openai/dall-e-3",
            "name": "OpenAI: DALL-E 3",
            "input_price": 0.040,  # per image (standard 1024x1024)
            "output_price": 0.0,
            "pricing_unit": "per_image",
        },
        "dall-e-2": {
            "canonical_id": "openai/dall-e-2",
            "name": "OpenAI: DALL-E 2",
            "input_price": 0.016,  # per image (512x512)
            "output_price": 0.0,
            "pricing_unit": "per_image",
        },
    }

    endpoints = []
    new_models = []
    for key, info in models.items():
        canonical_id = info["canonical_id"]
        unit = info.get("pricing_unit", "per_million_tokens")
        input_price = info["input_price"]
        output_price = info["output_price"]
        blended = round(BLENDED_INPUT_WEIGHT * input_price + BLENDED_OUTPUT_WEIGHT * output_price, 6)

        endpoints.append({
            "endpoint_provider": "OpenAI",
            "model_id": canonical_id,
            "input_price_per_m": input_price,
            "output_price_per_m": output_price,
            "blended_price_per_m": blended,
            "context_length": None,
            "source": "openai_image_gen",
            "raw_data": {"openai_id": key, "name": info["name"], "pricing_unit": unit},
        })
        new_models.append({
            "model_id": canonical_id,
            "name": info["name"],
            "provider": "OpenAI",
            "context_length": None,
            "is_reasoning": False,
            "modality": "image-generation",
            "pricing_unit": unit,
        })

    print(f"  OpenAI image gen models: {len(endpoints)}")
    return endpoints, new_models


def fetch_google_image_gen():
    """Google image generation models.

    - Imagen 4: $0.04/image (1024x1024), $0.08/image (2048x2048)
    - Imagen 3: $0.03/image (1024x1024)
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Loading Google image gen (static)...")

    models = {
        "imagen-4": {
            "canonical_id": "google/imagen-4",
            "name": "Google: Imagen 4",
            "input_price": 0.04,  # per image
        },
        "imagen-3": {
            "canonical_id": "google/imagen-3",
            "name": "Google: Imagen 3",
            "input_price": 0.03,
        },
    }

    return _build_endpoints(models, "Google", "google_image_gen", "image-generation", "per_image")


def fetch_stability_image_gen():
    """Stability AI image generation pricing.

    - Stable Image Ultra (SD3.5): $0.06/image
    - Stable Image Core: $0.03/image
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Loading Stability image gen (static)...")

    models = {
        "stable-image-ultra": {
            "canonical_id": "stabilityai/stable-image-ultra",
            "name": "Stability AI: Stable Image Ultra",
            "input_price": 0.06,
        },
        "stable-image-core": {
            "canonical_id": "stabilityai/stable-image-core",
            "name": "Stability AI: Stable Image Core",
            "input_price": 0.03,
        },
    }

    return _build_endpoints(models, "Stability AI", "stability_image_gen", "image-generation", "per_image")


# ---------------------------------------------------------------------------
# VIDEO GENERATION - Priced per second
# ---------------------------------------------------------------------------

def fetch_openai_video_gen():
    """OpenAI Sora video generation.

    From pricing page (Aug 2026):
    - sora-2 (720p): $0.10/second
    - sora-2-pro (720p): $0.30/second
    - sora-2-pro (1024p): $0.50/second
    - sora-2-pro (1080p): $0.70/second
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Loading OpenAI video gen (static)...")

    models = {
        "sora-2": {
            "canonical_id": "openai/sora-2",
            "name": "OpenAI: Sora 2 (720p)",
            "input_price": 0.10,  # per second
        },
        "sora-2-pro": {
            "canonical_id": "openai/sora-2-pro",
            "name": "OpenAI: Sora 2 Pro (720p)",
            "input_price": 0.30,
        },
        "sora-2-pro-1080p": {
            "canonical_id": "openai/sora-2-pro-1080p",
            "name": "OpenAI: Sora 2 Pro (1080p)",
            "input_price": 0.70,
        },
    }

    return _build_endpoints(models, "OpenAI", "openai_video_gen", "video-generation", "per_second")


def fetch_google_video_gen():
    """Google Veo video generation.

    From Google pricing page (Aug 2026):
    - Veo 3.1: $0.40/second (720p)
    - Veo 3: $0.40/second (720p)
    - Veo 2: $0.35/second (720p)
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Loading Google video gen (static)...")

    models = {
        "veo-3.1": {
            "canonical_id": "google/veo-3.1",
            "name": "Google: Veo 3.1",
            "input_price": 0.40,
        },
        "veo-3": {
            "canonical_id": "google/veo-3",
            "name": "Google: Veo 3",
            "input_price": 0.40,
        },
        "veo-2": {
            "canonical_id": "google/veo-2",
            "name": "Google: Veo 2",
            "input_price": 0.35,
        },
    }

    return _build_endpoints(models, "Google", "google_video_gen", "video-generation", "per_second")


# ---------------------------------------------------------------------------
# HELPER: Build endpoint + model dicts from a model dict
# ---------------------------------------------------------------------------

def _build_endpoints(models, provider, source, modality, pricing_unit):
    """Build endpoint and new_model dicts from a model definition dict.

    Args:
        models: dict of {model_key: {canonical_id, name, input_price, output_price}}
        provider: provider name (e.g. "OpenAI")
        source: source label (e.g. "openai_tts")
        modality: modality string (e.g. "tts", "stt")
        pricing_unit: "per_million_tokens", "per_minute", "per_image", "per_second"
    """
    endpoints = []
    new_models = []

    for key, info in models.items():
        canonical_id = info["canonical_id"]
        input_price = info["input_price"]
        output_price = info.get("output_price", 0.0)
        blended = round(BLENDED_INPUT_WEIGHT * input_price + BLENDED_OUTPUT_WEIGHT * output_price, 6)

        endpoints.append({
            "endpoint_provider": provider,
            "model_id": canonical_id,
            "input_price_per_m": input_price,
            "output_price_per_m": output_price,
            "blended_price_per_m": blended,
            "context_length": info.get("context_length"),
            "source": source,
            "raw_data": {"name": info["name"], "pricing_unit": pricing_unit},
        })
        new_models.append({
            "model_id": canonical_id,
            "name": info["name"],
            "provider": provider,
            "context_length": info.get("context_length", None),
            "is_reasoning": False,
            "modality": modality,
            "pricing_unit": pricing_unit,
        })

    print(f"  {provider} {modality} models: {len(endpoints)}")
    return endpoints, new_models


# ---------------------------------------------------------------------------
# MAIN: fetch all niche pricing and sync to DB
# ---------------------------------------------------------------------------

def fetch_all_niche():
    """Fetch all niche model pricing (non-text-generation).

    Returns combined (endpoints, new_models) lists.
    Does NOT include Jina embeddings (already scraped by pipeline.py).
    Does NOT include text generation models (handled by main pipeline).
    """
    all_endpoints = []
    all_new_models = []

    fetchers = [
        # Embeddings (delegates to embedding_pricing.py)
        ("Embeddings", fetch_all_embeddings),
        # TTS
        ("TTS - OpenAI", fetch_openai_tts),
        ("TTS - Google", fetch_google_tts),
        ("TTS - ElevenLabs", fetch_elevenlabs_tts),
        # STT
        ("STT - OpenAI", fetch_openai_stt),
        ("STT - Google", fetch_google_stt),
        ("STT - Deepgram", fetch_deepgram_stt),
        # Rerankers
        ("Rerankers - Cohere", fetch_cohere_rerankers),
        ("Rerankers - Voyage", fetch_voyage_rerankers),
        ("Rerankers/Readers - Jina", fetch_jina_rerankers),
        # Image generation
        ("Image Gen - OpenAI", fetch_openai_image_gen),
        ("Image Gen - Google", fetch_google_image_gen),
        ("Image Gen - Stability", fetch_stability_image_gen),
        # Video generation
        ("Video Gen - OpenAI", fetch_openai_video_gen),
        ("Video Gen - Google", fetch_google_video_gen),
    ]

    for name, fetcher in fetchers:
        try:
            ep, nm = fetcher()
            all_endpoints.extend(ep)
            all_new_models.extend(nm)
            print(f"  [{name}] {len(ep)} endpoints, {len(nm)} models")
        except Exception as e:
            print(f"  ERROR in {name}: {e}")

    print(f"\n  Total niche endpoints: {len(all_endpoints)}")
    print(f"  Total niche models: {len(all_new_models)}")
    return all_endpoints, all_new_models


def sync_to_db(endpoints, new_models):
    """Sync niche model pricing to the database.

    Uses the same upsert/insert pattern as pipeline.py but with
    pricing_unit support.
    """
    print(f"\n[{datetime.now(timezone.utc).isoformat()}] Syncing niche pricing to DB...")
    conn = get_db_connection()
    try:
        # Upsert models (set modality, pricing_unit)
        cur = conn.cursor()
        for m in new_models:
            tier = m.get("tier", "micro")
            aa_score = m.get("aa_index_score")
            tokenizer = m.get("tokenizer")
            country = m.get("creator_country")
            cur.execute("""
                INSERT INTO models (id, name, provider, tier, context_length, aa_index_score,
                                    modality, tokenizer, is_reasoning, creator_country,
                                    pricing_unit, updated_at, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), TRUE)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    provider = EXCLUDED.provider,
                    modality = EXCLUDED.modality,
                    pricing_unit = EXCLUDED.pricing_unit,
                    updated_at = NOW()
            """, (
                m["model_id"], m["name"], m["provider"], tier,
                m.get("context_length"), aa_score,
                m["modality"], tokenizer, m.get("is_reasoning", False),
                country,
                m.get("pricing_unit", "per_million_tokens"),
            ))
        conn.commit()
        print(f"  Upserted {len(new_models)} model records")

        # Insert endpoints
        for ep in endpoints:
            cur.execute("""
                INSERT INTO model_endpoints
                    (model_id, endpoint_provider, input_price_per_m, output_price_per_m,
                     blended_price_per_m, context_length, source, raw_data)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                ep["model_id"], ep["endpoint_provider"],
                ep["input_price_per_m"], ep["output_price_per_m"],
                ep["blended_price_per_m"], ep.get("context_length"),
                ep.get("source", "niche_pricing"),
                json.dumps(ep.get("raw_data", {})),
            ))
        conn.commit()
        print(f"  Inserted {len(endpoints)} endpoint records")

        # Insert price snapshots with pricing_unit
        for ep in endpoints:
            unit = ep.get("raw_data", {}).get("pricing_unit", "per_million_tokens")
            cur.execute("""
                INSERT INTO price_snapshots
                    (model_id, source, input_price_per_m, output_price_per_m,
                     blended_price_per_m, raw_data, source_count, pricing_unit)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                ep["model_id"], ep.get("source", "niche_pricing"),
                ep["input_price_per_m"], ep["output_price_per_m"],
                ep["blended_price_per_m"],
                json.dumps(ep.get("raw_data", {})),
                1, unit,
            ))
        conn.commit()
        print(f"  Inserted {len(endpoints)} price snapshots")

        # Refresh materialized views
        cur.execute("REFRESH MATERIALIZED VIEW latest_prices")
        cur.execute("REFRESH MATERIALIZED VIEW price_changes_24h")
        cur.execute("REFRESH MATERIALIZED VIEW price_changes_7d")
        conn.commit()
        print(f"  Refreshed materialized views")

        print(f"\n  Niche pricing sync complete at {datetime.now(timezone.utc).isoformat()}")

    except Exception as e:
        conn.rollback()
        print(f"\n  ERROR syncing niche pricing: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    import sys

    fetch_only = "--fetch-only" in sys.argv

    endpoints, new_models = fetch_all_niche()

    print(f"\n{'='*60}")
    print(f"Niche Pricing Summary")
    print(f"{'='*60}")

    # Group by modality
    by_modality = {}
    for m in new_models:
        mod = m["modality"]
        if mod not in by_modality:
            by_modality[mod] = {"models": 0, "endpoints": 0}
        by_modality[mod]["models"] += 1
    for ep in endpoints:
        # Find matching model modality
        for m in new_models:
            if m["model_id"] == ep["model_id"]:
                mod = m["modality"]
                by_modality[mod]["endpoints"] += 1
                break

    print(f"\n{'Modality':<25} {'Models':>8} {'Endpoints':>10}")
    print(f"{'-'*25} {'-'*8} {'-'*10}")
    for mod, counts in sorted(by_modality.items()):
        print(f"{mod:<25} {counts['models']:>8} {counts['endpoints']:>10}")
    print(f"{'-'*25} {'-'*8} {'-'*10}")
    print(f"{'TOTAL':<25} {len(new_models):>8} {len(endpoints):>10}")

    # Print detail
    print(f"\n{'='*60}")
    print(f"Detail by Modality")
    print(f"{'='*60}")
    for mod in sorted(by_modality.keys()):
        print(f"\n--- {mod.upper()} ---")
        for ep in endpoints:
            for m in new_models:
                if m["model_id"] == ep["model_id"] and m["modality"] == mod:
                    unit = m.get("pricing_unit", "per_million_tokens")
                    print(f"  {ep['model_id']:<45} ${ep['input_price_per_m']:.4f}/{unit.split('_')[-1]}  ({ep['endpoint_provider']})")
                    break

    if fetch_only:
        print("\n--fetch-only: skipping database sync")
    else:
        sync_to_db(endpoints, new_models)
