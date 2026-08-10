#!/usr/bin/env python3
"""
TensorX direct pricing scraper.

TensorX serves its model library (with per-model pricing) as server-rendered
HTML at https://tensorx.ai/models/ (WordPress). Model cards use a stable
structure:

    <a class="so-m2-card" data-name="moonshotai/kimi-k3" href="...">
      <div class="so-m2-price-row"><span>Input</span><span>$3.00 / 1M</span></div>
      <div class="so-m2-price-row"><span>Cache Read</span><span>$0.75 / 1M</span></div>
      <div class="so-m2-price-row"><span>Output</span><span>$15.00 / 1M</span></div>
    </a>

The data-name attribute is already our canonical lowercase provider/model id
(moonshotai/kimi-k3), so pricing merges onto the existing canonical rows
(Venice-style). Returns (endpoints, new_models) for pipeline.py.
"""
import re
import logging
from datetime import datetime, timezone

import requests

log = logging.getLogger("tensorx_pricing")

TENSORX_URL = "https://tensorx.ai/models/"

# TensorX provider slug in URL may differ from canonical provider prefix.
# e.g. link is tensorx.ai/models/z-ai--glm-5.2/ but data-name is z-ai/glm-5.2.
# data-name is authoritative and already canonical, so no map needed unless
# we find a mismatch. Kept for explicit remaps:
TENSORX_MODEL_MAP = {}


def _card_prices(card_html: str) -> dict:
    """Extract input/cached/output prices from a single so-m2-card block.

    Price rows are: <div class="so-m2-price-row"><span>Label</span><span>$X / 1M</span></div>
    Returns {"input": float|None, "cached": float|None, "output": float|None}.
    """
    result = {"input": None, "cached": None, "output": None}
    label_map = {"input": "input", "cache read": "cached", "output": "output"}
    for m in re.finditer(
        r'<div class="so-m2-price-row"><span>([^<]+)</span><span>\$([\d.]+)\s*/\s*1M</span></div>',
        card_html,
    ):
        label = m.group(1).strip().lower()
        value = float(m.group(2))
        key = label_map.get(label)
        if key:
            result[key] = value
    return result


def _card_context(card_html: str) -> int | None:
    """Extract context window from the chips (e.g. '1M', '256K', '198K')."""
    chip = re.search(r'<span class="so-m2-chip">(\d+)\s*([KM])\s*</span>', card_html)
    if not chip:
        return None
    n = int(chip.group(1))
    unit = chip.group(2)
    return n * 1_000_000 if unit == "M" else n * 1_000


def fetch_tensorx_pricing(timeout: int = 30):
    """Fetch TensorX model pricing from their models page.

    Returns (endpoints, new_models).
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Fetching TensorX pricing...")
    try:
        r = requests.get(
            TENSORX_URL,
            timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0 (InferenceIndexer price-index)"},
        )
        r.raise_for_status()
        html = r.text
    except Exception as e:
        print(f"  TensorX fetch error: {e}")
        return [], []

    # Split into individual card blocks
    cards = re.split(r'(?=<a class="so-m2-card")', html)
    endpoints = []
    new_models = []
    for chunk in cards:
        m = re.search(r'<a class="so-m2-card" data-name="([^"]+)"', chunk)
        if not m:
            continue
        canonical_id = m.group(1).strip()
        canonical_id = TENSORX_MODEL_MAP.get(canonical_id, canonical_id)
        prices = _card_prices(chunk)
        if prices["input"] is None or prices["output"] is None:
            continue
        context = _card_context(chunk)

        blended = round(0.4 * prices["input"] + 0.6 * prices["output"], 6)

        endpoints.append({
            "endpoint_provider": "TensorX",
            "model_id": canonical_id,
            "input_price_per_m": round(prices["input"], 6),
            "output_price_per_m": round(prices["output"], 6),
            "blended_price_per_m": blended,
            "context_length": context,
            "source": "tensorx_direct",
            "raw_data": {
                "tensorx_id": canonical_id,
                "cached_input_per_m": round(prices["cached"], 6) if prices["cached"] else None,
                "provider_portal": "tensorx.ai",
            },
        })
        new_models.append({
            "model_id": canonical_id,
            "name": canonical_id.split("/")[-1].replace("-", " ").title(),
            "provider": canonical_id.split("/")[0] if "/" in canonical_id else "TensorX",
            "context_length": context,
            "is_reasoning": "reasoning" in canonical_id.lower(),
            "modality": "text",
        })

    print(f"  TensorX priced endpoints: {len(endpoints)}")
    return endpoints, new_models


if __name__ == "__main__":
    ep, nm = fetch_tensorx_pricing()
    print(f"TensorX: {len(ep)} priced endpoints")
    for e in sorted(ep, key=lambda x: x["model_id"]):
        print(f"  {e['model_id']:42} ${e['input_price_per_m']}/ ${e['output_price_per_m']}  ctx={e['context_length']}")