#!/usr/bin/env python3
"""
Vercel AI Gateway direct pricing scraper.

Vercel's AI Gateway publishes a public, no-auth OpenAI-compatible catalog at
https://ai-gateway.vercel.sh/v1/models with per-model per-token pricing in
USD (decimal strings, per single token):

    {"id": "openai/gpt-4o",
     "pricing": {"input": "0.0000025", "output": "0.00001",
                 "input_cache_read": "0.00000125", ...},
     "context_window": 128000,
     "type": "language", "modalities": {...}, "reasoning_options": [...]}

Prices are per TOKEN, so multiply by 1M to get our $/M unit.

Model ids are mostly already canonical (anthropic/claude-sonnet-4,
deepseek/deepseek-v4-flash). Known deviations are handled two ways:
  1. VERCEL_MODEL_MAP: explicit remaps (e.g. zai/ -> z-ai/, spacexai/ -> xai/)
  2. Suffix stripping: Vercel splits serving modes into separate ids
     (-fast = priority tier, -thinking, -premium). When the base id exists
     canonically we map onto it and record the tier in raw_data.

Only `type: language` models enter the index. Embeddings/transcription/
image/video/evaluation are out of scope (matching the homepage modality rule).
Returns (endpoints, new_models) for pipeline.py, mirroring tensorx_pricing.py.
"""
import json
import logging
import re
from datetime import datetime, timezone

import requests

log = logging.getLogger("vercel_pricing")

MODELS_URL = "https://ai-gateway.vercel.sh/v1/models"
USER_AGENT = "Mozilla/5.0 (InferenceIndexer price-index)"

# Vercel provider prefix -> our canonical provider prefix.
# Vercel uses some non-OpenRouter-style prefixes (zai, spacexai, bfl, kimi).
VERCEL_PROVIDER_MAP = {
    "zai": "z-ai",
    "spacexai": "xai",
    "kimi": "moonshotai",
    "bfl": "blackforestlabs",
    "qwen": "alibaba",
}

# Serving-mode suffixes Vercel splits into separate ids. Strip longest-first.
# Only stripped when the base id matches canonically; otherwise the id stands.
_TIER_SUFFIXES = [
    "-thinking-fast",
    "-thinking",
    "-premium",
    "-fast",
]


def _remap_id(vid: str, canonical: set, norm_map: dict) -> tuple[str, str | None]:
    """Map a Vercel id to a canonical model id.

    Returns (canonical_id, tier_note). tier_note is set when a serving-mode
    suffix was stripped to reach the canonical id.
    """
    # 1. direct hit
    if vid in canonical:
        return vid, None

    parts = vid.split("/")
    if len(parts) == 2:
        vp, vslug = parts
        cp = VERCEL_PROVIDER_MAP.get(vp, vp)

        # 2. provider remap, both raw and normalized
        for cand in (f"{cp}/{vslug}",):
            if cand in canonical:
                return cand, None
            if norm(cand) in norm_map:
                return norm_map[norm(cand)], None

        # 3. tier suffix strip (longest first)
        for suf in _TIER_SUFFIXES:
            if vslug.endswith(suf):
                base = f"{cp}/{vslug[: -len(suf)]}"
                if base in canonical:
                    return base, suf.lstrip("-")
                if norm(base) in norm_map:
                    return norm_map[norm(base)], suf.lstrip("-")

        # 4. normalized whole-id match (dots/dashes drift)
        nv = norm(f"{cp}/{vslug}")
        if nv in norm_map:
            return norm_map[nv], None

    return vid, None


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def fetch_vercel_pricing(timeout: int = 30):
    """Fetch Vercel AI Gateway model pricing.

    Returns (endpoints, new_models).
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Fetching Vercel AI Gateway pricing...")
    try:
        r = requests.get(
            MODELS_URL,
            timeout=timeout,
            headers={"User-Agent": USER_AGENT},
        )
        r.raise_for_status()
        data = r.json().get("data", [])
    except Exception as e:
        print(f"  Vercel fetch error: {e}")
        return [], []

    from pipeline import get_db_connection  # late import to avoid cycle

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM models WHERE is_active")
    canonical = {row[0] for row in cur.fetchall()}
    norm_map = {}
    for cid in canonical:
        norm_map.setdefault(norm(cid), cid)
    cur.close()
    conn.close()

    endpoints = []
    new_models = []
    mapped = 0
    unmapped = []
    for m in data:
        if m.get("type") != "language":
            continue
        pricing = m.get("pricing") or {}
        try:
            inp = float(pricing["input"]) * 1_000_000
            outp = float(pricing["output"]) * 1_000_000
        except (KeyError, TypeError, ValueError):
            continue
        if inp <= 0 and outp <= 0:
            continue

        cid, tier = _remap_id(m["id"], canonical, norm_map)
        if cid in canonical:
            mapped += 1
        else:
            unmapped.append(m["id"])

        cache_read = pricing.get("input_cache_read")
        cache_write = pricing.get("input_cache_write")
        blended = round(0.4 * inp + 0.6 * outp, 6)

        endpoints.append({
            "endpoint_provider": "Vercel AI Gateway",
            "model_id": cid,
            "input_price_per_m": round(inp, 6),
            "output_price_per_m": round(outp, 6),
            "blended_price_per_m": blended,
            "context_length": m.get("context_window"),
            "source": "vercel_direct",
            "raw_data": {
                "vercel_id": m["id"],
                "matched_from": m["id"] if m["id"] != cid else None,
                "serving_tier": tier,
                "cache_read_per_m": round(float(cache_read) * 1e6, 6) if cache_read else None,
                "cache_write_per_m": round(float(cache_write) * 1e6, 6) if cache_write else None,
                "zdr": m.get("zdr"),
                "no_training": m.get("no_training"),
                "gateway": "ai-gateway.vercel.sh",
            },
        })
        new_models.append({
            "model_id": cid,
            "name": (m.get("name") or cid.split("/")[-1].replace("-", " ").title()),
            "provider": cid.split("/")[0] if "/" in cid else "Vercel AI Gateway",
            "context_length": m.get("context_window"),
            "is_reasoning": bool(m.get("reasoning_options")),
            "modality": "text",
        })

    print(f"  Vercel: {len(data)} total, {len(endpoints)} priced language endpoints, "
          f"{mapped} mapped to canonical, {len(unmapped)} unmapped (still priced under vercel id)")
    return endpoints, new_models


if __name__ == "__main__":
    ep, nm = fetch_vercel_pricing()
    print(f"Vercel: {len(ep)} priced endpoints")
    for e in sorted(ep, key=lambda x: x["model_id"])[:20]:
        print(f"  {e['model_id']:45} ${e['input_price_per_m']:.4f} / ${e['output_price_per_m']:.4f}  ctx={e['context_length']}")
