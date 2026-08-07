#!/usr/bin/env python3
"""
Fetch OpenRouter weekly usage rankings and store as usage_weights.
Calculates usage-weighted SIT-Composite (SIT-Usage50) from top 50 models by token volume.
"""
import os
import sys
import json
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone, date
import psycopg2

OPENROUTER_RANKINGS_URL = "https://openrouter.ai/api/frontend/v1/rankings/models?view=week"

# Manual mappings for OpenRouter slugs -> our DB model IDs
# (for models where OpenRouter uses dated slugs we don't have)
SLUG_MAPPINGS = {
    "anthropic/claude-4.6-sonnet-20260217": "anthropic/claude-sonnet-4.6",
    "anthropic/claude-4.8-opus-20260528": "anthropic/claude-opus-4.8",
    "anthropic/claude-4.5-haiku-20251001": "anthropic/claude-haiku-4.5",
    "anthropic/claude-5-fable-20260609": "anthropic/claude-fable-5",
    "anthropic/claude-4.7-opus-20260416": "anthropic/claude-opus-4.7",
    "anthropic/claude-4.6-opus-20260205": "anthropic/claude-opus-4.6",
    "deepseek/deepseek-v4-flash-20260423": "deepseek/deepseek-v4-flash",
    "tencent/hy3-20260706": "tencent/hy3-preview",
    "xiaomi/mimo-v2.5-20260422": "xiaomi/mimo-v2.5",
    "deepseek/deepseek-v4-flash-20260731": "deepseek/deepseek-v4-flash-0731",
    "openai/gpt-5.6-luna-20260709": "openai/gpt-5.6-luna",
    "z-ai/glm-5.2-20260616": "z-ai/glm-5.2",
    "deepseek/deepseek-v4-pro-20260423": "deepseek/deepseek-v4-pro",
    "nvidia/nemotron-3-ultra-550b-a55b-20260604": "nvidia/nemotron-3-ultra-550b-a55b",
    "minimax/minimax-m3-20260531": "minimax/minimax-m3",
    "poolside/laguna-s-2.1-20260720": "poolside/laguna-s-2.1",
    "stepfun/step-3.7-flash-20260528": "stepfun/step-3.7-flash",
    "moonshotai/kimi-k3-20260715": "moonshotai/kimi-k3",
    "inclusionai/ling-3.0-flash-20260723": "inclusionai/ling-3.0-flash",
    "google/gemini-3.6-flash-20260721": "google/gemini-3.6-flash",
    "anthropic/claude-opus-5-20260723": "anthropic/claude-opus-5",
    "anthropic/claude-sonnet-5-20260630": "anthropic/claude-sonnet-5",
    "openai/gpt-5.6-terra-20260709": "openai/gpt-5.6-terra",
    "google/gemini-2.5-flash-lite": "google/gemini-2.5-flash-lite",
    "google/gemini-2.5-flash": "google/gemini-2.5-flash",
    "google/gemini-3.1-flash-lite-20260507": "google/gemini-3.1-flash-lite",
    "openai/gpt-5.6-sol-20260709": "openai/gpt-5.6-sol",
    "openai/gpt-5.6-luna-pro-20260709": "openai/gpt-5.6-luna-pro",
    "google/gemma-4-31b-it-20260402": "google/gemma-4-31b-it",
    "deepseek/deepseek-v3.2-20251201": "deepseek/deepseek-v3.2",
    "google/gemma-4-26b-a4b-it-20260403": "google/gemma-4-26b-a4b-it",
    "nvidia/nemotron-3-super-120b-a12b-20230311": "nvidia/nemotron-3-super-120b-a12b",
    "x-ai/grok-4.5-20260708": "x-ai/grok-4.5",
    "inclusionai/ling-2.6-flash-20260421": "inclusionai/ling-2.6-flash",
    "google/gemini-3.5-flash-20260519": "google/gemini-3.5-flash",
    "minimax/minimax-m2.7-20260318": "minimax/minimax-m2.7",
    "poolside/laguna-xs-2.1-20260625": "poolside/laguna-xs-2.1",
    "openai/gpt-5.4-20260305": "openai/gpt-5.4",
    "moonshotai/kimi-k2.6-20260420": "moonshotai/kimi-k2.6",
    "google/gemini-3.5-flash-lite-20260721": "google/gemini-3.5-flash-lite",
    "google/gemini-3.1-pro-preview-20260219": "google/gemini-3.1-pro-preview",
    "openai/gpt-5-mini-2025-08-07": "openai/gpt-5-mini",
}

def get_db():
    with open(os.path.expanduser("~/.hermes/.env")) as f:
        for line in f:
            if line.startswith("SUPABASE_DB_URL"):
                url = line.split("=", 1)[1].strip()
                return psycopg2.connect(url)
    raise RuntimeError("SUPABASE_DB_URL not found")

def fetch_rankings():
    """Fetch weekly usage rankings from OpenRouter."""
    print(f"[{datetime.now(timezone.utc).isoformat()}] Fetching OpenRouter rankings...")
    req = urllib.request.Request(OPENROUTER_RANKINGS_URL)
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    
    models = data.get("data", [])
    
    # Aggregate by model slug
    usage = defaultdict(lambda: {"tokens": 0, "requests": 0})
    for m in models:
        slug = m["model_permaslug"]
        usage[slug]["tokens"] += m.get("total_completion_tokens", 0) + m.get("total_prompt_tokens", 0)
        usage[slug]["requests"] += m.get("count", 0)
    
    # Sort by token volume
    ranked = sorted(usage.items(), key=lambda x: x[1]["tokens"], reverse=True)
    return ranked

def match_to_db(conn, ranked):
    """Match OpenRouter slugs to our DB model IDs."""
    cur = conn.cursor()
    cur.execute("SELECT id FROM models WHERE is_active = TRUE")
    db_ids = set(r[0] for r in cur.fetchall())
    cur.close()
    
    matched = []
    unmatched = []
    
    for slug, stats in ranked:
        # Check manual mappings first
        if slug in SLUG_MAPPINGS:
            db_id = SLUG_MAPPINGS[slug]
            if db_id in db_ids:
                matched.append((db_id, stats["tokens"], stats["requests"]))
                continue
        
        # Try exact match
        if slug in db_ids:
            matched.append((slug, stats["tokens"], stats["requests"]))
            continue
        
        # Try stripping date suffix
        parts = slug.split("-")
        while len(parts) > 1:
            parts.pop()
            candidate = "-".join(parts)
            if candidate in db_ids:
                matched.append((candidate, stats["tokens"], stats["requests"]))
                break
        else:
            unmatched.append((slug, stats["tokens"]))
    
    return matched, unmatched

def store_weights(conn, matched):
    """Store usage weights in DB, normalized to percentages."""
    cur = conn.cursor()
    today = date.today()
    
    # Aggregate by model_id (multiple OpenRouter slugs may map to same DB model)
    agg = defaultdict(lambda: {"tokens": 0, "requests": 0})
    for model_id, tokens, requests in matched:
        agg[model_id]["tokens"] += tokens
        agg[model_id]["requests"] += requests
    
    # Total tokens for weight calculation
    total_tokens = sum(v["tokens"] for v in agg.values())
    
    # Clear old weights for this week
    cur.execute("DELETE FROM usage_weights WHERE week_start = %s", (today,))
    
    for model_id, stats in agg.items():
        weight_pct = round((stats["tokens"] / total_tokens) * 100, 4) if total_tokens > 0 else 0
        cur.execute("""
            INSERT INTO usage_weights (model_id, week_start, total_tokens, total_requests, weight_pct)
            VALUES (%s, %s, %s, %s, %s)
        """, (model_id, today, stats["tokens"], stats["requests"], weight_pct))
    
    conn.commit()
    cur.close()
    print(f"Stored {len(agg)} usage weights (total: {total_tokens/1e9:.1f}B tokens)")

def calculate_usage_weighted_composite(conn):
    """Calculate SIT-Usage50: usage-weighted median of top 50 models' blended prices."""
    cur = conn.cursor()
    
    cur.execute("""
        SELECT uw.model_id, uw.weight_pct, lp.blended_price_per_m, m.tier
        FROM usage_weights uw
        JOIN latest_prices lp ON uw.model_id = lp.model_id
        JOIN models m ON uw.model_id = m.id
        WHERE m.is_active = TRUE AND lp.blended_price_per_m > 0
        ORDER BY uw.weight_pct DESC
    """)
    rows = cur.fetchall()
    
    if not rows:
        print("No matched models with prices found")
        cur.close()
        return None
    
    # Weighted median: sort by price, find where cumulative weight crosses 50%
    rows_by_price = sorted(rows, key=lambda x: x[2])
    total_weight = sum(r[1] for r in rows_by_price)
    cumulative = 0
    weighted_median = None
    
    for model_id, weight, price, tier in rows_by_price:
        cumulative += weight
        if cumulative >= total_weight / 2:
            weighted_median = float(price)
            break
    
    # Weighted mean
    total_weight_f = float(total_weight)
    weighted_mean = sum(float(r[1]) * float(r[2]) for r in rows) / total_weight_f if total_weight_f > 0 else 0
    
    # Simple median of the top 50
    prices = sorted([float(r[2]) for r in rows])
    n = len(prices)
    simple_median = prices[n // 2] if n % 2 == 1 else (prices[n // 2 - 1] + prices[n // 2]) / 2
    
    # Tier breakdown
    tier_stats = defaultdict(lambda: {"count": 0, "prices": []})
    for _, weight, price, tier in rows:
        tier_stats[tier]["count"] += 1
        tier_stats[tier]["prices"].append(float(price))
    
    print(f"\nSIT-Usage50 (top {len(rows)} models by usage):")
    print(f"  Simple median:      ${simple_median:.2f}/M")
    print(f"  Weighted median:    ${weighted_median:.2f}/M")
    print(f"  Weighted mean:      ${weighted_mean:.2f}/M")
    print(f"  Total weight:       {total_weight:.1f}%")
    print(f"\n  Tier breakdown:")
    for tier, stats in sorted(tier_stats.items(), key=lambda x: -len(x[1]["prices"])):
        prices = sorted(stats["prices"])
        n = len(prices)
        med = prices[n // 2] if n % 2 == 1 else (prices[n // 2 - 1] + prices[n // 2]) / 2
        print(f"    {tier:12s}  count={stats['count']:3d}  median=${med:.2f}/M  min=${min(prices):.2f}  max=${max(prices):.2f}")
    
    cur.close()
    return weighted_median

def main():
    conn = get_db()
    
    # Fetch rankings
    ranked = fetch_rankings()
    print(f"Fetched {len(ranked)} models from OpenRouter rankings")
    
    # Match to DB
    matched, unmatched = match_to_db(conn, ranked)
    print(f"Matched: {len(matched)}, Unmatched: {len(unmatched)}")
    
    if unmatched:
        print(f"\nUnmatched (top 10):")
        for slug, tokens in unmatched[:10]:
            print(f"  {slug:<50} {tokens/1e9:.1f}B tokens")
    
    # Store weights
    store_weights(conn, matched)
    
    # Calculate composite
    composite = calculate_usage_weighted_composite(conn)
    
    if composite:
        print(f"\n>>> SIT-Usage50 Composite: ${composite:.2f}/M")
    
    conn.close()

if __name__ == "__main__":
    main()
