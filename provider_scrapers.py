#!/usr/bin/env python3
"""
Direct pricing scrapers for Groq and Together AI.

Both providers serve their per-model pricing as clean Markdown tables on
Mintlify/docs sites (reachable by appending .md). Sources:

  Groq     : https://console.groq.com/docs/models.md
  Together : https://docs.together.ai/docs/serverless/models.md

These share the same structure as Fireworks' docs and reuse the generic
markdown-table parser in provider_pricing.py. Following the Venice/Fireworks
pattern, provider model IDs are mapped onto our canonical InferenceIndexer
model IDs via *_MODEL_MAP so pricing merges onto one model row.

Each fetch_*_pricing(api_key) -> (endpoints, new_models) returns rows ready
for pipeline insert_endpoints() / upsert_venice_models().
"""

import re
import logging
from datetime import datetime, timezone

import requests

from provider_pricing import extract_model_rows, parse_money

log = logging.getLogger("provider_scrapers")

GROQ_DOCS_URL = "https://console.groq.com/docs/models.md"
TOGETHER_DOCS_URL = "https://docs.together.ai/docs/serverless/models.md"

# ---------------------------------------------------------------------------
# Groq
# ---------------------------------------------------------------------------

# Groq model id -> our canonical InferenceIndexer model id.
# Groq IDs that are ALREADY our canonical format (openai/gpt-oss-120b, etc.)
# pass through unchanged. Others get mapped to the canonical row where one
# exists; genuinely-new Groq models are created natively.
GROQ_MODEL_MAP = {
    # pass-through (canonical already)
    # Explicit remaps where native differs from canonical
}

# Clean a Groq markdown model-id cell: it is wrapped in image-link markup like
#   [![Meta](...icon...)Llama 3.1 8B](/docs/model/llama-3.1-8b-instant)llama-3.1-8b-instant
# The raw ID is the bare token AFTER the last ')' of the markdown link.
def _strip_groq_id(cell: str) -> str:
    if ")" in cell:
        # take everything after the last closing paren of the image/link
        return cell.rsplit(")", 1)[-1].strip()
    return cell.strip()


def fetch_groq_pricing(timeout: int = 30):
    """Fetch Groq pricing from their docs markdown.

    Returns (endpoints, new_models). Groq's API is catalog-only (needs key,
    no prices), so the docs table is the authoritative source.
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Fetching Groq pricing...")
    try:
        r = requests.get(GROQ_DOCS_URL, timeout=timeout)
        r.raise_for_status()
        md = r.text
    except Exception as e:
        print(f"  Groq fetch error: {e}")
        return [], []

    rows = extract_model_rows(md, "MODEL ID")
    print(f"  Groq docs table: {len(rows)} rows")

    endpoints = []
    new_models = []
    for raw_id, cells in rows:
        model_id = _strip_groq_id(raw_id)
        if not model_id or "/" not in model_id and not model_id:
            continue
        # The pricing cell contains: $X input$Y output  (e.g. "$0.05 input$0.08 output")
        price_row = cells[2] if len(cells) > 2 else ""
        m = re.search(r"\$([\d.]+) input\s*\$([\d.]+) output", price_row)
        if not m:
            # skip non-token models (per-hour, per-char, ContactSales)
            continue
        in_price = float(m.group(1))
        out_price = float(m.group(2))

        canonical_id = GROQ_MODEL_MAP.get(model_id, model_id)
        blended = round(0.4 * in_price + 0.6 * out_price, 6)

        endpoints.append({
            "endpoint_provider": "Groq",
            "model_id": canonical_id,
            "input_price_per_m": round(in_price, 6),
            "output_price_per_m": round(out_price, 6),
            "blended_price_per_m": blended,
            "context_length": None,  # not parsed from this cell; optional
            "source": "groq_direct",
            "raw_data": {"groq_id": model_id, "provider_portal": "groqcloud"},
        })
        new_models.append({
            "model_id": canonical_id,
            "name": model_id.split("/")[-1].replace("-", " ").replace("-", " ").title(),
            "provider": "Groq",
            "context_length": None,
            "is_reasoning": "reasoning" in model_id.lower(),
            "modality": "text",
        })

    print(f"  Groq priced endpoints: {len(endpoints)}")
    return endpoints, new_models


# ---------------------------------------------------------------------------
# Together AI
# ---------------------------------------------------------------------------

# Together API model string -> canonical InferenceIndexer model id.
# Our canonical scheme is lowercase `provider/model`. Together IDs are often
# title-cased (moonshotai/Kimi-K3, zai-org/GLM-5.2); the default is to
# lowercase them so they match the existing canonical rows. Explicit remaps
# handle cases where Together's provider prefix differs from our canonical one.
TOGETHER_MODEL_MAP = {
    "minimaxai/minimax-m2.7": "minimax/minimax-m2.7",
    "minimaxai/minimax-m3": "minimax/minimax-m3",
    "zai-org/glm-5.2": "z-ai/glm-5.2",
    "deepseek-ai/deepseek-v4-pro": "deepseek/deepseek-v4-pro",
    "deepseek-ai/deepseek-v4-flash": "deepseek/deepseek-v4-flash",
    "deepseek-ai/deepseek-v4-flash-0731": "deepseek/deepseek-v4-flash-0731",
    "qwen/qwen3.7-plus": "qwen/qwen-3.7-plus",
}


def _together_canonical(api_string: str) -> str:
    """Resolve a Together API model string to our canonical model id.

    Lowercases by default (our canonical scheme is lowercase provider/model),
    then applies the explicit remap for prefix differences.
    """
    norm = api_string.strip()
    if "/" not in norm:
        return norm
    lower = norm.split("/")[0].lower() + "/" + norm.split("/")[1].lower()
    return TOGETHER_MODEL_MAP.get(lower, lower)


def fetch_together_pricing(timeout: int = 30):
    """Fetch Together serverless pricing from their docs markdown.

    Returns (endpoints, new_models). Clean table: input/cached/output per 1M.
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Fetching Together pricing...")
    try:
        r = requests.get(TOGETHER_DOCS_URL, timeout=timeout)
        r.raise_for_status()
        md = r.text
    except Exception as e:
        print(f"  Together fetch error: {e}")
        return [], []

    rows = extract_model_rows(md, "API model string")
    print(f"  Together docs table: {len(rows)} rows")

    endpoints = []
    new_models = []
    for api_string, cells in rows:
        # cols: 0 org, 1 name, 2 API string, 3 ctx, 4 input, 5 cached, 6 output
        if not api_string or api_string == "Model string for API":
            continue
        in_price = parse_money(cells[4]) if len(cells) > 4 else None
        out_price = parse_money(cells[6]) if len(cells) > 6 else None
        cached = parse_money(cells[5]) if len(cells) > 5 else None
        if in_price is None or out_price is None:
            continue

        canonical_id = _together_canonical(api_string)
        blended = round(0.4 * in_price + 0.6 * out_price, 6)

        endpoints.append({
            "endpoint_provider": "Together",
            "model_id": canonical_id,
            "input_price_per_m": round(in_price, 6),
            "output_price_per_m": round(out_price, 6),
            "blended_price_per_m": blended,
            "context_length": int(cells[3]) if len(cells) > 3 and cells[3].isdigit() else None,
            "source": "together_direct",
            "raw_data": {
                "together_id": api_string,
                "cached_input_per_m": round(cached, 6) if cached else None,
                "organization": cells[0] if len(cells) > 0 else "",
            },
        })
        new_models.append({
            "model_id": canonical_id,
            "name": cells[1] if len(cells) > 1 and cells[1] else api_string,
            "provider": cells[0] if len(cells) > 0 and cells[0] else "Together",
            "context_length": int(cells[3]) if len(cells) > 3 and cells[3].isdigit() else None,
            "is_reasoning": False,
            "modality": "text",
        })

    print(f"  Together priced endpoints: {len(endpoints)}")
    return endpoints, new_models


if __name__ == "__main__":
    import sys
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("groq", "all"):
        ep, nm = fetch_groq_pricing()
        print(f"Groq: {len(ep)} endpoints")
        for e in sorted(ep, key=lambda x: x["model_id"]):
            print(f"  {e['model_id']:40} ${e['input_price_per_m']}/ ${e['output_price_per_m']}")
    if which in ("together", "all"):
        ep, nm = fetch_together_pricing()
        print(f"Together: {len(ep)} endpoints")
        for e in sorted(ep, key=lambda x: x["model_id"]):
            print(f"  {e['model_id']:40} ${e['input_price_per_m']}/ ${e['output_price_per_m']}")