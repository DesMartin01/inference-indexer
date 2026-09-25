#!/usr/bin/env python3
"""
Direct pricing scrapers for Z.AI (Zhipu), Alibaba Cloud (DashScope), and Moonshot AI.

Z.AI: Clean markdown pricing page at docs.z.ai/guides/overview/pricing.md
      OpenAI-compatible API at api.z.ai/api/paas/v4 (catalog only, no prices in API)
Alibaba: Pricing page at alibabacloud.com/help/en/model-studio/model-pricing
         OpenAI-compatible API at dashscope-intl.aliyuncs.com/compatible-mode/v1
Moonshot: OpenAI-compatible API at api.moonshot.ai/v1 (catalog only, no prices)
          Pricing page at platform.kimi.ai/docs/pricing/chat-v1

Each fetch_*_pricing() -> (endpoints, new_models) returns rows ready for
pipeline insert_endpoints() / upsert_venice_models(), matching the
provider_scrapers.py pattern.
"""

import re
import logging
from datetime import datetime, timezone

import requests

from provider_pricing import extract_model_rows, parse_money

log = logging.getLogger("direct_scrapers")

# ---------------------------------------------------------------------------
# Z.AI (Zhipu AI) - markdown pricing page
# ---------------------------------------------------------------------------

ZAI_PRICING_URL = "https://docs.z.ai/guides/overview/pricing.md"
ZAI_API_BASE = "https://api.z.ai/api/paas/v4"

# Z.AI model name -> our canonical model_id
# Z.AI uses uppercase GLM names; our canonical scheme is lowercase provider/model
ZAI_MODEL_MAP = {
    "glm-5.3-flash": "z-ai/glm-5.3-flash",
    "glm-5.3": "z-ai/glm-5.3",
    "glm-5.2": "z-ai/glm-5.2",
    "glm-5.1": "z-ai/glm-5.1",
    "glm-5": "z-ai/glm-5",
    "glm-5-turbo": "z-ai/glm-5-turbo",
    "glm-4.7": "z-ai/glm-4.7",
    "glm-4.7-flashx": "z-ai/glm-4.7-flash",
    "glm-4.7-h": "z-ai/glm-4.7-h",
    "glm-4.6": "z-ai/glm-4.6",
    "glm-4.5": "z-ai/glm-4.5",
    "glm-4.5-x": "z-ai/glm-4.5-x",
    "glm-4.5-air": "z-ai/glm-4.5-air",
    "glm-4-32b-0414-128k": "thudm/glm-4-32b-0414",
    "glm-5v-turbo": "z-ai/glm-5v-turbo",
    "glm-4.6v": "z-ai/glm-4.6v",
    "glm-4.5v": "z-ai/glm-4.5v",
    "glm-4.6v-flash": "z-ai/glm-4.6v-flash",
    "glm-ocr": "z-ai/glm-ocr",
}


def _parse_zai_price(cell):
    """Parse a Z.AI pricing cell. Handles 'Free', '~~$0.15~~ $0.075', '$1.4'."""
    cell = cell.strip()
    if not cell or cell.lower() == "free" or cell == "\\":
        return 0.0
    # Remove strikethrough: ~~$0.15~~ $0.075 -> take last price
    if "~~" in cell:
        # Take the non-strikethrough price (after last ~~)
        parts = cell.split("~~")
        cell = parts[-1].strip()
    m = re.search(r"\$([\d.]+)", cell)
    if m:
        return float(m.group(1))
    return 0.0


def fetch_zai_pricing(timeout=30):
    """Fetch Z.AI (Zhipu) pricing from their markdown docs page.

    Returns (endpoints, new_models).
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Fetching Z.AI pricing...")
    try:
        r = requests.get(ZAI_PRICING_URL, timeout=timeout)
        r.raise_for_status()
        md = r.text
    except Exception as e:
        print(f"  Z.AI fetch error: {e}")
        return [], []

    endpoints = []
    new_models = []

    # Parse markdown tables. Look for lines with | Model | Input | ... | Output |
    # The tables have: | Model | Input | Cached Input | ... | Output |
    lines = md.split("\n")
    for line in lines:
        line = line.strip()
        if not line.startswith("|") or "Model" in line:
            continue
        # Skip separator rows
        if re.match(r"^\|[\s:|-]+\|$", line):
            continue

        cells = [c.strip() for c in line.split("|")[1:-1]]  # drop empty first/last
        if len(cells) < 5:
            continue

        model_name = cells[0].lower().strip()
        if not model_name or "model" in model_name:
            continue

        # Skip non-token models (image gen, video gen, audio, agents)
        # These are priced per-image/per-video, not per-token
        if any(x in model_name for x in ["cogview", "cogvideo", "vidu", "glm-image", "glm-asr", "agent"]):
            continue

        input_price = _parse_zai_price(cells[1])
        output_price = _parse_zai_price(cells[-1])  # Output is last column

        if input_price == 0 and output_price == 0:
            continue  # Free models or unparseable

        canonical_id = ZAI_MODEL_MAP.get(model_name)
        if not canonical_id:
            # Try to construct: z-ai/glm-...
            if model_name.startswith("glm-"):
                canonical_id = f"z-ai/{model_name}"
            else:
                continue

        blended = round(0.4 * input_price + 0.6 * output_price, 6)

        endpoints.append({
            "endpoint_provider": "Z.AI",
            "model_id": canonical_id,
            "input_price_per_m": round(input_price, 6),
            "output_price_per_m": round(output_price, 6),
            "blended_price_per_m": blended,
            "context_length": None,
            "source": "zai_direct",
            "raw_data": {"zai_model": model_name},
        })
        new_models.append({
            "model_id": canonical_id,
            "name": model_name.replace("-", " ").title(),
            "provider": "Z.AI",
            "context_length": None,
            "is_reasoning": "thinking" in model_name.lower() or "reasoning" in model_name.lower(),
            "modality": "text",
        })

    print(f"  Z.AI priced endpoints: {len(endpoints)}")
    return endpoints, new_models


# ---------------------------------------------------------------------------
# Alibaba Cloud (DashScope) - pricing page scrape
# ---------------------------------------------------------------------------

ALIBABA_PRICING_URL = "https://www.alibabacloud.com/help/en/model-studio/model-pricing"
ALIBABA_API_BASE = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"

# Alibaba model IDs -> our canonical model_id
ALIBABA_MODEL_MAP = {
    "qwen3.7-max": "alibaba/qwen3.7-max",
    "qwen3.7-plus": "qwen/qwen-3.7-plus",
    "qwen3.6-max-preview": "alibaba/qwen3.6-max-preview",
    "qwen3.6-plus": "qwen/qwen-3.6-plus",
    "qwen3.6-flash": "alibaba/qwen3.6-flash",
    "qwen3.5-plus": "alibaba/qwen3.5-plus",
    "qwen3.5-flash": "alibaba/qwen3.5-flash",
    "qwen3-max": "alibaba/qwen3-max",
    "qwen3-plus": "qwen/qwen3-plus",
    "qwen3-turbo": "alibaba/qwen-turbo",
    "qwen-plus": "alibaba/qwen-plus",
    "qwen-turbo": "alibaba/qwen-turbo",
    "qwen-max": "alibaba/qwen-max",
    "qwen3.8-max": "qwen/qwen-3.8-max",
    "qwen3.8-flash": "alibaba/qwen3.8-flash",
    "qwen3.8-27b": "alibaba/qwen3.8-27b",
}


def _parse_alibaba_text(text, endpoints, new_models, seen_models):
    """Parse Qwen model IDs + $prices out of flattened page text.

    Shared by the direct fetch and the r.jina.ai fallback. Appends to
    endpoints/new_models, dedupes via seen_models.
    """
    # Find Qwen model IDs and nearby prices
    # Pattern: qwen[version]-[tier] followed by $X.XX input and $X.XX output
    # The Singapore section uses $X.XX format for international pricing
    # We look for patterns like: qwen3.7-max ... $2.5 ... $7.5
    qwen_pattern = re.compile(
        r"(qwen[\d.]*-(?:max|plus|turbo|flash|coder|vl|omni|embedding|reranker)[\w.-]*)"
        r"(?:(?!\s*qwen).){0,200}?\$(\d+\.?\d*)"
        r"(?:(?!\s*qwen).){0,100}?\$(\d+\.?\d*)",
        re.IGNORECASE
    )

    for match in qwen_pattern.finditer(text):
        model_id_raw = match.group(1).lower().strip()
        input_price = float(match.group(2))
        output_price = float(match.group(3))

        # Skip unreasonable prices (page noise)
        if input_price > 100 or output_price > 200:
            continue
        if input_price == 0 and output_price == 0:
            continue

        canonical_id = ALIBABA_MODEL_MAP.get(model_id_raw)
        if not canonical_id:
            if model_id_raw.startswith("qwen"):
                canonical_id = f"alibaba/{model_id_raw}"
            else:
                continue

        if canonical_id in seen_models:
            continue
        seen_models.add(canonical_id)

        blended = round(0.4 * input_price + 0.6 * output_price, 6)

        endpoints.append({
            "endpoint_provider": "Alibaba Cloud",
            "model_id": canonical_id,
            "input_price_per_m": round(input_price, 6),
            "output_price_per_m": round(output_price, 6),
            "blended_price_per_m": blended,
            "context_length": None,
            "source": "alibaba_direct",
            "raw_data": {"alibaba_model": model_id_raw},
        })
        new_models.append({
            "model_id": canonical_id,
            "name": model_id_raw.replace("-", " ").title(),
            "provider": "Alibaba Cloud",
            "context_length": None,
            "is_reasoning": "thinking" in model_id_raw.lower() or "reasoning" in model_id_raw.lower(),
            "modality": "text",
        })


def fetch_alibaba_pricing(timeout=30):
    """Fetch Alibaba Cloud (DashScope) pricing from their docs page.

    Alibaba bot-walls datacenter IPs with their 'punish'/x5sec captcha page
    (HTTP 200, no model data) - hit us from Sep 19 2026 on Lightsail. Strategy:
    1. Direct fetch; parse.
    2. If 0 matches (block OR layout drift), retry through the r.jina.ai
       reader proxy, which fetches from Jina's IPs and returns clean text.
    3. If both fail, print a loud WARN so a silent zero-day shows in the log.

    Returns (endpoints, new_models).
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Fetching Alibaba Cloud pricing...")
    endpoints = []
    new_models = []
    seen_models = set()

    # --- Attempt 1: direct fetch ---
    html = None
    try:
        r = requests.get(ALIBABA_PRICING_URL, timeout=timeout)
        r.raise_for_status()
        html = r.text
    except Exception as e:
        print(f"  Alibaba direct fetch error: {e}")

    if html:
        # Remove HTML tags, get text
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text)
        _parse_alibaba_text(text, endpoints, new_models, seen_models)

    if endpoints:
        print(f"  Alibaba priced endpoints: {len(endpoints)} (direct)")
        return endpoints, new_models

    # --- Attempt 2: r.jina.ai reader proxy (bot-wall bypass) ---
    # Runs when the direct fetch errored OR returned the captcha/punish page
    # (HTTP 200 but zero matches - the silent-failure shape).
    print("  Direct fetch yielded 0 endpoints (block or layout drift); trying r.jina.ai fallback...")
    try:
        r = requests.get(
            f"https://r.jina.ai/{ALIBABA_PRICING_URL}",
            timeout=timeout * 2,
            headers={"Accept": "text/plain"},
        )
        r.raise_for_status()
        jina_text = r.text
    except Exception as e:
        print(f"  WARN: Alibaba pricing fetch FAILED completely (direct + jina): {e}")
        print("  WARN: alibaba_direct prices will go stale - investigate the source page.")
        return [], []

    # Jina returns markdown/plain text; strip any residual HTML then parse.
    text = re.sub(r"<[^>]+>", " ", jina_text)
    text = re.sub(r"\s+", " ", text)
    _parse_alibaba_text(text, endpoints, new_models, seen_models)

    if not endpoints:
        print("  WARN: Alibaba pricing parse found 0 endpoints via BOTH direct and r.jina.ai.")
        print("  WARN: This is an incident, not an empty day - check the source page layout.")
    else:
        print(f"  Alibaba priced endpoints: {len(endpoints)} (via r.jina.ai fallback)")
    return endpoints, new_models


# ---------------------------------------------------------------------------
# Moonshot AI - pricing page scrape
# ---------------------------------------------------------------------------

MOONSHOT_PRICING_URLS = [
    "https://platform.kimi.ai/docs/pricing/chat-k3.md",
    "https://platform.kimi.ai/docs/pricing/chat-v1.md",
]
MOONSHOT_API_BASE = "https://api.moonshot.ai/v1"

# Moonshot model IDs -> our canonical model_id
MOONSHOT_MODEL_MAP = {
    "kimi-k3": "moonshotai/kimi-k3",
    "kimi-k3-fast": "moonshotai/kimi-k3-fast",
    "kimi-k2.7-code": "moonshotai/kimi-k2.7-code",
    "kimi-k2.7-code-fast": "moonshotai/kimi-k2.7-code-fast",
    "kimi-k2.6": "moonshotai/kimi-k2.6",
    "kimi-k2.6-highspeed": "moonshotai/kimi-k2.6-highspeed",
    "kimi-k2.5": "moonshotai/kimi-k2-5",
    "kimi-k2-instruct": "moonshotai/kimi-k2-instruct",
    "moonshot-v1-8k": "moonshotai/moonshot-v1-8k",
    "moonshot-v1-32k": "moonshotai/moonshot-v1-32k",
    "moonshot-v1-128k": "moonshotai/moonshot-v1-128k",
    "moonshot-v1-8k-vision-preview": "moonshotai/moonshot-v1-8k-vision-preview",
    "moonshot-v1-32k-vision-preview": "moonshotai/moonshot-v1-32k-vision-preview",
    "moonshot-v1-128k-vision-preview": "moonshotai/moonshot-v1-128k-vision-preview",
}


def fetch_moonshot_pricing(timeout=30):
    """Fetch Moonshot AI (Kimi) pricing from their markdown docs pages.

    The pricing pages are JSX-infused markdown. We parse the table rows
    which contain model IDs and $ prices.

    Returns (endpoints, new_models).
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Fetching Moonshot pricing...")
    endpoints = []
    new_models = []
    seen_models = set()

    for url in MOONSHOT_PRICING_URLS:
        try:
            r = requests.get(url, timeout=timeout)
            r.raise_for_status()
            text = r.text
        except Exception as e:
            print(f"  Moonshot fetch error ({url}): {e}")
            continue

        # The markdown has JSX table rows like:
        # ["kimi-k3", "1M tokens", <>{"$"}0.30</>, <>{"$"}3.00</>, <>{"$"}15.00</>, "1,048,576 tokens"],
        # ["moonshot-v1-8k", "1M tokens", <>{\"$\"}0.20</>, <>{\"$\"}2.00</>, "8,192 tokens"],
        # Parse these with regex
        row_pattern = re.compile(
            r'\["([\w.-]+)"\s*,\s*"[^"]*"\s*,'
            r'(?:.*?<>\{"\$"\}(\d+\.?\d*)</>.*?)+'
            r'\]',
            re.DOTALL
        )

        # Simpler approach: find all $X.XX values in each row
        row_matches = re.findall(r'\["([\w.-]+)"\s*,\s*"1M tokens"(.*?)\]', text, re.DOTALL)

        for model_id_raw, rest in row_matches:
            model_id_raw = model_id_raw.lower().strip()
            # Extract all $prices from the row
            prices = re.findall(r'\{"\$"\}(\d+\.?\d*)</>', rest)
            if len(prices) < 2:
                continue

            # First price = input (cache miss), last price = output
            # For K3: cache_hit, cache_miss, output -> use cache_miss as input
            if len(prices) >= 3:
                input_price = float(prices[1])  # cache miss = real input price
                output_price = float(prices[-1])
            else:
                input_price = float(prices[0])
                output_price = float(prices[-1])

            if input_price == 0 and output_price == 0:
                continue

            canonical_id = MOONSHOT_MODEL_MAP.get(model_id_raw)
            if not canonical_id:
                if model_id_raw.startswith("kimi") or model_id_raw.startswith("moonshot"):
                    canonical_id = f"moonshotai/{model_id_raw}"
                else:
                    continue

            if canonical_id in seen_models:
                continue
            seen_models.add(canonical_id)

            blended = round(0.4 * input_price + 0.6 * output_price, 6)

            endpoints.append({
                "endpoint_provider": "Moonshot AI",
                "model_id": canonical_id,
                "input_price_per_m": round(input_price, 6),
                "output_price_per_m": round(output_price, 6),
                "blended_price_per_m": blended,
                "context_length": None,
                "source": "moonshot_direct",
                "raw_data": {"moonshot_model": model_id_raw},
            })
            new_models.append({
                "model_id": canonical_id,
                "name": model_id_raw.replace("-", " ").title(),
                "provider": "Moonshot AI",
                "context_length": None,
                "is_reasoning": "kimi" in model_id_raw.lower() or "reasoning" in model_id_raw.lower(),
                "modality": "text",
            })

    print(f"  Moonshot priced endpoints: {len(endpoints)}")
    return endpoints, new_models


if __name__ == "__main__":
    import sys
    which = sys.argv[1] if len(sys.argv) > 1 else "all"

    if which in ("zai", "all"):
        ep, nm = fetch_zai_pricing()
        print(f"\nZ.AI: {len(ep)} endpoints")
        for e in sorted(ep, key=lambda x: x["model_id"]):
            print(f"  {e['model_id']:40} ${e['input_price_per_m']}/ ${e['output_price_per_m']}")

    if which in ("alibaba", "all"):
        ep, nm = fetch_alibaba_pricing()
        print(f"\nAlibaba: {len(ep)} endpoints")
        for e in sorted(ep, key=lambda x: x["model_id"]):
            print(f"  {e['model_id']:40} ${e['input_price_per_m']}/ ${e['output_price_per_m']}")

    if which in ("moonshot", "all"):
        ep, nm = fetch_moonshot_pricing()
        print(f"\nMoonshot: {len(ep)} endpoints")
        for e in sorted(ep, key=lambda x: x["model_id"]):
            print(f"  {e['model_id']:40} ${e['input_price_per_m']}/ ${e['output_price_per_m']}")
