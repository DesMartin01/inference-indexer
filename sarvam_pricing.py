#!/usr/bin/env python3
"""
Sarvam AI direct pricing scraper.

Sarvam is India's sovereign AI inference platform (self-hosted, own models -
NOT an aggregator). It exposes an OpenAI-compatible API at
https://api.sarvam.ai/v1 (public /v1/models enumeration, keyed chat
completions) but does NOT expose token pricing machine-readably - pricing
lives only on the HTML /api-pricing page.

The /api-pricing page is a Next.js SSR doc whose RSC payload contains objects
of the shape:

    {"service":["0","Sarvam-105B"],
     "description":["0","Chat completion. Input ₹4 · Cached input ₹2.5 · Output ₹16, per 1M tokens."],
     "price":["0","₹4 / ₹2.5 / ₹16"],
     "unit":["0","per 1M input / cached / output tokens"]}

We pick only the *chat LLM* rows (Sarvam-105B, Sarvam-30B) and ignore the
non-token services (TTS, STT, translation, vision) which don't belong in the
index. Prices are in INR; we convert to USD at scrape time using a fetched
FX rate (falling back to a stored constant).

Returns (endpoints, new_models) for pipeline.py, mirroring
openrelay_pricing.py / tensorx_pricing.py.
"""
import json
import re
import logging
from datetime import datetime, timezone

import requests

log = logging.getLogger("sarvam_pricing")

PRICING_URL = "https://www.sarvam.ai/api-pricing"
MODELS_URL = "https://api.sarvam.ai/v1/models"
FX_URL = "https://open.er-api.com/v6/latest/INR"
USER_AGENT = "Mozilla/5.0 (InferenceIndexer price-index)"

# Fallback INR->USD (1 INR = this many USD). Refreshed at scrape time from
# ExchangeRate-API; if that fetch fails we keep this. Checked Aug 2026.
INR_USD_FALLBACK = 0.010498

# Only the chat-completion models belong in the index. Non-token services
# (TTS/STT/translation/vision) are excluded - they're priced per char/hour/page.
SARVAM_CHAT_MODELS = {
    "Sarvam-105B": "sarvam/sarvam-105b",
    "Sarvam-30B": "sarvam/sarvam-30b",
}

# Context lengths (tokens) - not on the pricing page; from Sarvam's model
# cards/docs as of Aug 2026.
SARVAM_CONTEXT = {
    "sarvam/sarvam-105b": 65536,
    "sarvam/sarvam-30b": 65536,
}


def _fetch_inr_usd(timeout: int = 12) -> float:
    """Fetch current INR->USD rate, falling back to a stored constant."""
    try:
        r = requests.get(FX_URL, timeout=timeout, headers={"User-Agent": USER_AGENT})
        r.raise_for_status()
        d = r.json()
        usd = d.get("rates", {}).get("USD")
        if isinstance(usd, (int, float)) and usd > 0:
            log.info("  Sarvam FX: 1 INR = %s USD (live)" , usd)
            return float(usd)
    except Exception as e:
        log.warning("  Sarvam FX fetch failed (%s); using fallback rate", e)
    return INR_USD_FALLBACK


def _extract_pricing_objects(html: str) -> list[dict]:
    """Pull the {service, description, price, unit} objects out of the RSC payload."""
    objects: list[dict] = []
    # The RSC payload has &quot; entities that we need to unescape before JSON.
    # Greedy-match each {...} containing a 'service' key with a price field.
    for m in re.finditer(
        r'\{&quot;service&quot;.*?\}',
        html,
        re.DOTALL,
    ):
        raw = m.group(0).replace("&quot;", '"').replace("&amp;", "&")
        consume = raw
        # It may be wrapped: ["0",{...},["0","..."]]. The object itself is balanced braces.
        try:
            obj = json.loads(consume)
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        service = obj.get("service")
        price = obj.get("price")
        if isinstance(service, list) and service and isinstance(price, list) and price:
            objects.append(obj)
    return objects


def _price_from_label(label: str) -> float | None:
    """Extract the '₹N.N' price from a string or a ['0','₹N.N'] list field."""
    if isinstance(label, list):
        txt = label[-1] if label else ""
    else:
        txt = str(label)
    m = re.search(r"₹\s*([\d.]+)", txt)
    return float(m.group(1)) if m else None


def _parse_triple(price_field) -> tuple[float | None, float | None, float | None]:
    """Parse price field '₹4 / ₹2.5 / ₹16' -> (input, cached, output) in INR."""
    txt = price_field[-1] if isinstance(price_field, list) else str(price_field)
    nums = re.findall(r"₹\s*([\d.]+)", txt)
    # Expect input / cached / output
    if len(nums) < 3:
        return (float(nums[0]), None, float(nums[1])) if len(nums) == 2 else (float(nums[0]), None, None) if nums else (None, None, None)
    return float(nums[0]), float(nums[1]), float(nums[2])


def fetch_sarvam_pricing(timeout: int = 20) -> tuple[list[dict], list[dict]]:
    """Scrape Sarvam's two chat LLM prices and return (endpoints, new_models)."""
    endpoints: list[dict] = []
    new_models: list[dict] = []

    fx = _fetch_inr_usd()

    # 1) Enumerate models machine-readably (connectivity + model ids)
    try:
        r = requests.get(MODELS_URL, timeout=timeout, headers={"User-Agent": USER_AGENT})
        r.raise_for_status()
        live_ids = [m.get("id") for m in r.json().get("data", [])]
        log.info("  Sarvam live model ids: %s", live_ids)
    except Exception as e:
        log.warning("  Sarvam /v1/models failed: %s", e)
        live_ids = []

    # 2) Scrape pricing from HTML
    try:
        r = requests.get(PRICING_URL, timeout=timeout, headers={"User-Agent": USER_AGENT})
        r.raise_for_status()
    except Exception as e:
        log.error("  Sarvam pricing page fetch failed: %s", e)
        return [], []

    objects = _extract_pricing_objects(r.text)
    by_service: dict[str, dict] = {}
    for obj in objects:
        service = obj["service"][-1] if obj["service"] else ""
        by_service[service] = obj

    now = datetime.now(timezone.utc).isoformat()
    for service, canonical_id in SARVAM_CHAT_MODELS.items():
        obj = by_service.get(service)
        if not obj:
            log.warning("  Sarvam: %s pricing object not found on page", service)
            continue

        input_inr, cached_inr, output_inr = _parse_triple(obj["price"])
        if input_inr is None or output_inr is None:
            log.warning("  Sarvam: %s price parse failed: %r", service, obj["price"])
            continue

        # Convert INR -> USD
        input_usd = round(input_inr * fx, 6)
        output_usd = round(output_inr * fx, 6)
        cached_usd = round(cached_inr * fx, 6) if cached_inr is not None else None
        blended = round(0.4 * input_usd + 0.6 * output_usd, 6)

        model_name = canonical_id.split("/")[-1].replace("-", " ").title()
        endpoints.append({
            "endpoint_provider": "Sarvam",
            "model_id": canonical_id,
            "input_price_per_m": input_usd,
            "output_price_per_m": output_usd,
            "blended_price_per_m": blended,
            "context_length": SARVAM_CONTEXT.get(canonical_id),
            "source": "sarvam_direct",
            "raw_data": {
                "sarvam_id": service.lower().replace("-", "-"),
                "cached_input_per_m": cached_usd,
                "currency": "INR",
                "fx_rate": fx,
                "prices_inr": {"input": input_inr, "cached": cached_inr, "output": output_inr},
            },
        })
        new_models.append({
            "model_id": canonical_id,
            "name": model_name,
            "provider": canonical_id.split("/")[0],
            "context_length": SARVAM_CONTEXT.get(canonical_id),
            "is_reasoning": False,
            "modality": "text",
        })

    log.info("  Sarvam priced endpoints: %d", len(endpoints))
    return endpoints, new_models


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    eps, nms = fetch_sarvam_pricing()
    for e in eps:
        print(f"  {e['model_id']}: in=${e['input_price_per_m']} out=${e['output_price_per_m']} blend=${e['blended_price_per_m']}")