#!/usr/bin/env python3
"""
OpenRelay direct pricing scraper.

OpenRelay publishes per-model token pricing as server-rendered HTML tables on
two pages:
  - https://openrelay.inc/inference-catalog   (input/output rates)
  - https://openrelay.inc/inference-pricing   (input/cached-input/output rates)

Each model row uses a stable structure (Next.js SSR, same on both pages):

    <tr key="openrelay/gpt-oss-120b">
      <td><span>GPT-OSS 120B</span><span>openrelay/gpt-oss-120b</span></td>
      <td>128K</td>
      <td>$0.15</td>            <- input / 1M
      <td>$0.015</td>           <- cached input / 1M (or <span>n/a</span>)
      <td>$0.60</td>            <- output / 1M
    </tr>

The row's model id is the canonical segment (openrelay/gpt-oss-120b). We map
that onto the canonical model in our DB where it already exists (GPT-OSS,
Gemma, GLM 5.2, DeepSeek-OCR) using OPENRELAY_MODEL_MAP. Returns
(endpoints, new_models) for pipeline.py, mirroring tensorx_pricing.py.
"""
import re
import logging
from datetime import datetime, timezone

import requests

log = logging.getLogger("openrelay_pricing")

CATALOG_URL = "https://openrelay.inc/inference-catalog"
PRICING_URL = "https://openrelay.inc/inference-pricing"
USER_AGENT = "Mozilla/5.0 (InferenceIndexer price-index)"

# Map OpenRelay's model ids onto canonical provider/model ids already in the
# index or canonical_model_id() shape. Unknown ids fall through unchanged.
OPENRELAY_MODEL_MAP = {
    "openrelay/gpt-oss-120b": "openai/gpt-oss-120b",
    "openrelay/gpt-oss-20b": "openai/gpt-oss-20b",
    "openrelay/gemma-4-31b": "google/gemma-4-31b",
    "openrelay/gemma-4-31b-nvfp4-32k": "google/gemma-4-31b",
    "openrelay/glm-5.2": "z-ai/glm-5.2",
    "openrelay/deepseek-ocr-2": "deepseek/deepseek-ocr-2",
}


def _parse_price(value: str) -> float | None:
    """Parse a '$0.15' cell to a float, or None for 'n/a'."""
    m = re.search(r"\$([\d.]+)", value)
    return float(m.group(1)) if m else None


def _parse_context(value: str) -> int | None:
    """Parse '128K' / '1M' context cell to token count."""
    m = re.search(r"(\d+)\s*([KM])", value)
    if not m:
        return None
    n = int(m.group(1))
    return n * 1_000_000 if m.group(2) == "M" else n * 1_000


def _extract_rows(html: str) -> list[dict]:
    """Extract (model_id, context, input, cached, output) from all <tr> rows."""
    rows = []
    # Each row begins with the model-id span. Split on that to isolate rows,
    # even when the cached cell is 'n/a' (wrapped in an extra <span>).
    chunks = re.split(r'(?=<span class="mt-0\.5 block font-mono text-\[11px\] text-faint">)', html)
    for chunk in chunks:
        m = re.search(r'text-faint">([^<]+)</span>', chunk)
        if not m:
            continue
        model_id = m.group(1).strip()
        if not model_id.startswith("openrelay/"):
            continue

        # Context cell: <td ...>128K</td>
        ctx_m = re.search(r'text-muted">([^<]+)</td>', chunk)
        context = _parse_context(ctx_m.group(1)) if ctx_m else None

        # Price cells are font-mono tabular-nums; capture input/cached/output.
        # Values may be '$0.15' or '<span class="text-faint">n/a</span>'.
        cells = re.findall(
            r'tabular-nums text-fg">(?:<span class="text-faint">)?([^<]+?)(?:</span>)?</td>',
            chunk,
        )
        # cells should be [input, cached, output] on the pricing page, but the
        # catalog page omits the cached column -> [input, output].
        prices = [_parse_price(c) for c in cells]
        input_price = prices[0] if len(prices) >= 1 else None
        cached_price = prices[2] if len(prices) >= 3 else None
        output_price = prices[2] if len(prices) >= 3 else (prices[1] if len(prices) == 2 else None)

        if input_price is None or output_price is None:
            continue
        rows.append(
            {
                "model_id": model_id,
                "context": context,
                "input": input_price,
                "cached": cached_price,
                "output": output_price,
            }
        )

    return rows


def fetch_openrelay_pricing(timeout: int = 30):
    """Fetch OpenRelay token pricing from the catalog and pricing pages.

    Returns (endpoints, new_models).
    """
    print(f"[{datetime.now(timezone.utc).isoformat()}] Fetching OpenRelay pricing...")
    all_html = ""
    for url in (PRICING_URL, CATALOG_URL):
        try:
            r = requests.get(
                url,
                timeout=timeout,
                headers={"User-Agent": USER_AGENT},
            )
            r.raise_for_status()
            all_html += r.text
        except Exception as e:
            print(f"  OpenRelay fetch error from {url}: {e}")

    rows = _extract_rows(all_html)
    if not rows:
        print("  OpenRelay: no rows parsed")
        return [], []

    # De-dupe by model id (prefer the pricing page, which has cached rates).
    by_id: dict[str, dict] = {}
    for r in rows:
        by_id.setdefault(r["model_id"], r)

    endpoints = []
    new_models = []
    for r in by_id.values():
        canonical_id = OPENRELAY_MODEL_MAP.get(r["model_id"], r["model_id"])
        assert canonical_id is not None
        blended = round(0.4 * r["input"] + 0.6 * r["output"], 6)
        endpoints.append(
            {
                "endpoint_provider": "OpenRelay",
                "model_id": canonical_id,
                "input_price_per_m": round(r["input"], 6),
                "output_price_per_m": round(r["output"], 6),
                "blended_price_per_m": blended,
                "context_length": r["context"],
                "source": "openrelay_direct",
                "raw_data": {
                    "openrelay_id": r["model_id"],
                    "cached_input_per_m": round(r["cached"], 6) if r["cached"] else None,
                },
            }
        )
        new_models.append(
            {
                "model_id": canonical_id,
                "name": canonical_id.split("/")[-1].replace("-", " ").title(),
                "provider": canonical_id.split("/")[0] if "/" in canonical_id else "OpenRelay",
                "context_length": r["context"],
                "is_reasoning": "reasoning" in canonical_id.lower() or "glm" in canonical_id.lower(),
                "modality": "text",
            }
        )

    print(f"  OpenRelay priced endpoints: {len(endpoints)}")
    return endpoints, new_models


if __name__ == "__main__":
    ep, nm = fetch_openrelay_pricing()
    print(f"OpenRelay: {len(ep)} priced endpoints")
    for e in sorted(ep, key=lambda x: x["model_id"]):
        print(
            f"  {e['model_id']:34} ${e['input_price_per_m']}/ ${e['output_price_per_m']}  ctx={e['context_length']}"
        )