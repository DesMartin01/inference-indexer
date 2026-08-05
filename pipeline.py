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
BLENDED_INPUT_WEIGHT = 0.4
BLENDED_OUTPUT_WEIGHT = 0.6

# AA Index tier thresholds
TIER_FRONTIER = 50
TIER_STANDARD = 30
TIER_BUDGET = 15

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
                    SELECT endpoint_provider, input_price_per_m, output_price_per_m, blended_price_per_m
                    FROM model_endpoints
                    WHERE model_id = %s AND fetched_at >= NOW() - INTERVAL '24 hours'
                    ORDER BY fetched_at DESC
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

def calculate_tier_averages(models):
    """Calculate the average blended price per tier."""
    tier_prices = {}
    for m in models:
        tier = m["tier"]
        if tier not in tier_prices:
            tier_prices[tier] = []
        tier_prices[tier].append(m["blended_price_per_m"])
    
    tier_avgs = {}
    for tier, prices in tier_prices.items():
        avg = sum(prices) / len(prices)
        tier_avgs[tier] = round(avg, 6)
    
    return tier_avgs

def calculate_sit_scores(models, tier_avgs):
    """Calculate SIT score for each model = model blended price / tier average."""
    for m in models:
        tier_avg = tier_avgs.get(m["tier"])
        if tier_avg and tier_avg > 0:
            m["sit_score"] = round(m["blended_price_per_m"] / tier_avg, 4)
        else:
            m["sit_score"] = None
    return models

def calculate_composite_price(models):
    """Calculate the SIT-Composite price: equal-weighted average of all model blended prices."""
    prices = [m["blended_price_per_m"] for m in models if m["blended_price_per_m"] > 0]
    if not prices:
        return 0.0
    return round(sum(prices) / len(prices), 6)

def calculate_tier_indices(models):
    """Calculate SIT index values for each tier and the composite."""
    results = {}
    
    # Per-tier
    for tier in ["frontier", "standard", "budget", "micro"]:
        tier_models = [m for m in models if m["tier"] == tier and m["blended_price_per_m"] > 0]
        if tier_models:
            prices = [m["blended_price_per_m"] for m in tier_models]
            avg = sum(prices) / len(prices)
            providers = set(m["provider"] for m in tier_models)
            results[tier] = {
                "price": round(avg, 6),
                "model_count": len(tier_models),
                "provider_count": len(providers),
            }
    
    # Composite
    composite_price = calculate_composite_price(models)
    all_providers = set(m["provider"] for m in models)
    results["composite"] = {
        "price": composite_price,
        "model_count": len(models),
        "provider_count": len(all_providers),
    }
    
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
            SOURCE_NAME, json.dumps(ep.get("raw_data", {}))
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
                 blended_price_per_m, sit_score, raw_data, is_anomalous, source_count)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            m["model_id"], SOURCE_NAME,
            m["input_price_per_m"], m["output_price_per_m"],
            m["blended_price_per_m"], m.get("sit_score"),
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
        
        cur.execute("""
            INSERT INTO sit_index_values 
                (date, tier, sit_price, sit_index_points, model_count, 
                 provider_count, calculation_method)
            VALUES (%s, %s, %s, %s, %s, %s, 'equal_weight')
            ON CONFLICT (date, tier) DO UPDATE SET
                sit_price = EXCLUDED.sit_price,
                sit_index_points = EXCLUDED.sit_index_points,
                model_count = EXCLUDED.model_count,
                provider_count = EXCLUDED.provider_count,
                calculated_at = NOW()
        """, (
            today, tier, data["price"], index_points,
            data["model_count"], data["provider_count"]
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
        print(f"  {tier:10s}: {count:4d} models, avg blended ${avg:.4f}/M")
    
    print(f"\nSIT-Composite: ${indices['composite']['price']:.4f}/M")
    print(f"  Models: {indices['composite']['model_count']}")
    print(f"  Providers: {indices['composite']['provider_count']}")
    
    if "spread" in indices:
        print(f"\nSIT-Spread: ${indices['spread']['price']:.4f}/M")
    
    # Top 10 cheapest by SIT Score
    scored = [m for m in models if m.get("sit_score") is not None]
    scored.sort(key=lambda x: x["sit_score"])
    
    print(f"\nTop 10 by SIT Score (cheapest for tier):")
    print(f"  {'Model':<40} {'Tier':<10} {'Blended $/M':<12} {'SIT Score':<10}")
    for m in scored[:10]:
        print(f"  {m['name'][:40]:<40} {m['tier']:<10} ${m['blended_price_per_m']:<11.4f} {m['sit_score']:.4f}")
    
    # Top 5 most expensive by SIT Score
    print(f"\nTop 5 most expensive (by SIT Score):")
    for m in scored[-5:]:
        print(f"  {m['name'][:40]:<40} {m['tier']:<10} ${m['blended_price_per_m']:<11.4f} {m['sit_score']:.4f}")
    
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
        if endpoint_data:
            insert_endpoints(conn, endpoint_data)
        insert_price_snapshots(conn, priced)
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
