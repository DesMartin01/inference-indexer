#!/usr/bin/env python3
"""
InferenceIndexer.ai - API Server
Serves inference pricing data and SIT index values from Supabase.

Endpoints:
  GET /v1/sit/composite/latest       - Current SIT-Composite + tier breakdown
  GET /v1/sit/composite/history      - Historical SIT values
  GET /v1/models                      - All models with current pricing
  GET /v1/models/{model_id}          - Single model detail
  GET /v1/models/{model_id}/history  - Single model price history

Auth: Bearer token (API key) for some endpoints, public for others.
Rate limits: Public 100/day, Free 1000/day, Paid 50000/day
"""

import os
import sys
import time
import json
import secrets
from datetime import datetime, timezone, date, timedelta
from collections import defaultdict
from typing import Optional

import psycopg2
from fastapi import FastAPI, HTTPException, Header, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

# ============================================
# CONFIG
# ============================================

RATE_LIMITS = {
    "public": {"daily": 1000, "per_minute": 60, "history_days": 7},
    "free": {"daily": 10000, "per_minute": 100, "history_days": 30},
    "paid": {"daily": 50000, "per_minute": 200, "history_days": 365},
    "ssr": {"daily": 100000, "per_minute": 500, "history_days": 365},  # For Next.js SSR
}

# Secret header for SSR requests to bypass public rate limits
SSR_SECRET = "inferenceindexer-ssr-2026"

BASE_DATE = date(2026, 8, 3)
BASE_VALUE = 1000.0

# ============================================
# DATABASE
# ============================================

def get_db():
    """Get database connection."""
    db_url = os.environ.get("SUPABASE_DB_URL")
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
        raise RuntimeError("SUPABASE_DB_URL not configured")
    
    return psycopg2.connect(db_url, connect_timeout=10)

# ============================================
# AUTH & RATE LIMITING
# ============================================

# In-memory rate limit tracking (per API key per day)
# For production, move to Redis. For MVP, this is fine.
_rate_limits = defaultdict(lambda: {"count": 0, "date": date.today(), "minute_count": 0, "minute": datetime.now(timezone.utc).minute})

def get_api_user(authorization: Optional[str]):
    """Determine the user's plan from their API key."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    
    token = authorization.replace("Bearer ", "").strip()
    if not token or token == "public":
        return {"plan": "public", "email": None}
    
    # Check against api_users table
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT email, plan FROM api_users WHERE api_key = %s", (token,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            return {"plan": row[1], "email": row[0]}
    except:
        pass
    
    return None

def check_rate_limit(api_user, is_ssr=False):
    """Check if the user has exceeded their rate limit."""
    if is_ssr:
        plan = "ssr"
    elif not api_user:
        plan = "public"
    else:
        plan = api_user.get("plan", "public")
    
    limits = RATE_LIMITS.get(plan, RATE_LIMITS["public"])
    now = datetime.now(timezone.utc)
    today = now.date()
    current_minute = now.minute
    
    key = api_user["email"] if api_user else "anonymous"
    state = _rate_limits[key]
    
    # Reset daily count if new day
    if state["date"] != today:
        state["count"] = 0
        state["date"] = today
    
    # Reset minute count if new minute
    if state["minute"] != current_minute:
        state["minute_count"] = 0
        state["minute"] = current_minute
    
    state["count"] += 1
    state["minute_count"] += 1
    
    if state["count"] > limits["daily"]:
        raise HTTPException(
            status_code=429,
            detail={
                "error": {
                    "code": "rate_limit_exceeded",
                    "message": f"Rate limit of {limits['daily']} requests/day exceeded. Resets at {today + timedelta(days=1)}T00:00:00Z.",
                    "documentation_url": "https://inferenceindexer.ai/api/docs#rate-limits"
                }
            },
            headers={
                "X-RateLimit-Limit": str(limits["daily"]),
                "X-RateLimit-Remaining": str(max(0, limits["daily"] - state["count"])),
                "X-RateLimit-Reset": str(int((datetime.combine(today + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)).timestamp())),
            }
        )
    
    if state["minute_count"] > limits["per_minute"]:
        raise HTTPException(
            status_code=429,
            detail={
                "error": {
                    "code": "rate_limit_exceeded",
                    "message": f"Rate limit of {limits['per_minute']} requests/minute exceeded.",
                    "documentation_url": "https://inferenceindexer.ai/api/docs#rate-limits"
                }
            },
            headers={
                "X-RateLimit-Limit": str(limits["daily"]),
                "X-RateLimit-Remaining": str(max(0, limits["daily"] - state["count"])),
            }
        )
    
    return limits

def get_rate_limit_headers(api_user, limits):
    """Return rate limit headers for the response."""
    if not api_user:
        key = "anonymous"
    else:
        key = api_user["email"] or "anonymous"
    
    state = _rate_limits[key]
    remaining = max(0, limits["daily"] - state["count"])
    today = datetime.now(timezone.utc).date()
    reset_ts = int(datetime.combine(today + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc).timestamp())
    
    return {
        "X-RateLimit-Limit": str(limits["daily"]),
        "X-RateLimit-Remaining": str(remaining),
        "X-RateLimit-Reset": str(reset_ts),
    }

# ============================================
# DATABASE MIGRATION: Update latest_prices view
# ============================================

def ensure_latest_prices_view():
    """Recreate the latest_prices view to include SIT-adjusted columns."""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            CREATE OR REPLACE VIEW latest_prices AS
            SELECT DISTINCT ON (model_id)
              model_id,
              input_price_per_m,
              output_price_per_m,
              blended_price_per_m,
              sit_score,
              reasoning_multiplier,
              sit_adjusted_price,
              source,
              source_count,
              fetched_at
            FROM price_snapshots
            ORDER BY model_id, fetched_at DESC
        """)
        conn.commit()
        cur.close()
        conn.close()
        print("  latest_prices view updated with SIT-adjusted columns")
    except Exception as e:
        print(f"  WARN: Could not update latest_prices view: {e}")

# ============================================
# FASTAPI APP
# ============================================

app = FastAPI(
    title="InferenceIndexer API",
    description="Independent price index for AI inference",
    version="1.2.0",
)

# Update latest_prices view on startup to include source_count
ensure_latest_prices_view()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# HELPER: Query helpers
# ============================================

def calc_change_24h(conn, model_id, current_price):
    """Calculate 24h change for a model."""
    cur = conn.cursor()
    cur.execute("""
        SELECT blended_price_per_m
        FROM price_snapshots
        WHERE model_id = %s AND fetched_at < NOW() - INTERVAL '20 hours'
        ORDER BY fetched_at DESC LIMIT 1
    """, (model_id,))
    row = cur.fetchone()
    cur.close()
    if row and row[0] and row[0] > 0:
        return round(((current_price - row[0]) / row[0]) * 100, 2)
    return 0.0

def calc_change_7d(conn, model_id, current_price):
    """Calculate 7d change for a model."""
    cur = conn.cursor()
    cur.execute("""
        SELECT blended_price_per_m
        FROM price_snapshots
        WHERE model_id = %s AND fetched_at < NOW() - INTERVAL '6 days'
        ORDER BY fetched_at DESC LIMIT 1
    """, (model_id,))
    row = cur.fetchone()
    cur.close()
    if row and row[0] and row[0] > 0:
        return round(((current_price - row[0]) / row[0]) * 100, 2)
    return 0.0

# ============================================
# ENDPOINTS
# ============================================

@app.get("/")
async def root():
    return {
        "name": "InferenceIndexer API",
        "version": "1.1.0",
        "docs": "/docs",
        "endpoints": [
            "/v1/sit/composite/latest",
            "/v1/sit/composite/history",
            "/v1/models",
            "/v1/models/{model_id}",
            "/v1/models/{model_id}/endpoints",
            "/v1/models/{model_id}/history"
        ]
    }

@app.get("/v1/sit/composite/latest")
async def get_sit_latest(request: Request, authorization: Optional[str] = Header(None)):
    """Returns the current SIT-Composite index value, including tier breakdowns.
    
    The SIT-Composite is a usage-weighted mean of the top 50 models by OpenRouter
    token volume. This reflects what CTOs actually pay for inference, not the
    raw median of all models (which is dragged down by cheap micro models).
    """
    api_user = get_api_user(authorization)
    limits = check_rate_limit(api_user, is_ssr=request.headers.get("X-SSR-Secret") == SSR_SECRET)
    
    conn = get_db()
    cur = conn.cursor()
    
    # Calculate usage-weighted composite from top 50 models
    # Quality gate: only models with AA score >= 35 (GPT-4-Turbo baseline)
    cur.execute("""
        WITH top50 AS (
            SELECT uw.model_id, uw.weight_pct, lp.blended_price_per_m, m.tier, m.provider,
                   m.aa_index_score
            FROM usage_weights uw
            JOIN latest_prices lp ON uw.model_id = lp.model_id
            JOIN models m ON uw.model_id = m.id
            WHERE m.is_active = TRUE AND lp.blended_price_per_m > 0
              AND m.aa_index_score IS NOT NULL AND m.aa_index_score >= 35
            ORDER BY uw.weight_pct DESC
            LIMIT 50
        )
        SELECT 
            SUM(weight_pct * blended_price_per_m) / SUM(weight_pct) AS weighted_mean,
            COUNT(*) AS model_count,
            COUNT(DISTINCT provider) AS provider_count
        FROM top50
    """)
    comp_row = cur.fetchone()
    weighted_mean = float(comp_row[0]) if comp_row and comp_row[0] else 0
    model_count = comp_row[1] if comp_row else 0
    provider_count = comp_row[2] if comp_row else 0
    
    # Get tier breakdowns — ALL models in each tier, simple median
    # (tier indices show what a typical model in that tier costs, not usage-weighted)
    cur.execute("""
        WITH tier_prices AS (
            SELECT m.tier, lp.blended_price_per_m, m.provider
            FROM latest_prices lp
            JOIN models m ON lp.model_id = m.id
            WHERE m.is_active = TRUE AND lp.blended_price_per_m > 0
        )
        SELECT 
            tier,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY blended_price_per_m) AS price,
            COUNT(*) AS model_count,
            COUNT(DISTINCT provider) AS provider_count
        FROM tier_prices
        GROUP BY tier
    """)
    tier_rows = cur.fetchall()
    
    composite = {
        "price_per_m": round(weighted_mean, 2),
        "index_points": 1000.0,
        "models": model_count,
        "providers": provider_count,
    }
    
    tiers = {}
    for row in tier_rows:
        tier_name = row[0]
        tiers[tier_name] = {
            "price_per_m": round(float(row[1]), 2),
            "index_points": 1000.0,
            "models": row[2],
            "providers": row[3],
        }
    
    # Spread (frontier - budget)
    spread = None
    if "frontier" in tiers and "budget" in tiers:
        spread = {
            "price_per_m": round(tiers["frontier"]["price_per_m"] - tiers["budget"]["price_per_m"], 2),
            "index_points": 1000.0,
            "models": 0,
            "providers": 0,
        }
    
    # Get changes (like-for-like: only models that have prices on both days)
    # This prevents the composite from jumping when new models are added/removed
    cur.execute("""
        WITH today_prices AS (
            SELECT ps.model_id, ps.blended_price_per_m
            FROM latest_prices ps
        ),
        prev_prices AS (
            SELECT DISTINCT ON (ps.model_id) ps.model_id, ps.blended_price_per_m
            FROM price_snapshots ps
            WHERE ps.fetched_at < NOW() - INTERVAL '20 hours'
            ORDER BY ps.model_id, ps.fetched_at DESC
        ),
        like_for_like AS (
            SELECT t.model_id, t.blended_price_per_m AS today_price, p.blended_price_per_m AS prev_price,
                   m.tier
            FROM today_prices t
            JOIN prev_prices p ON t.model_id = p.model_id
            JOIN models m ON t.model_id = m.id
            WHERE m.is_active = TRUE AND t.blended_price_per_m > 0 AND p.blended_price_per_m > 0
        )
        SELECT
            -- Composite: median of today prices vs median of prev prices (same model set)
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY lfl.today_price) AS composite_today,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY lfl.prev_price) AS composite_prev,
            -- Per-tier
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY CASE WHEN lfl.tier = 'frontier' THEN lfl.today_price END) AS frontier_today,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY CASE WHEN lfl.tier = 'frontier' THEN lfl.prev_price END) AS frontier_prev,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY CASE WHEN lfl.tier = 'standard' THEN lfl.today_price END) AS standard_today,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY CASE WHEN lfl.tier = 'standard' THEN lfl.prev_price END) AS standard_prev,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY CASE WHEN lfl.tier = 'budget' THEN lfl.today_price END) AS budget_today,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY CASE WHEN lfl.tier = 'budget' THEN lfl.prev_price END) AS budget_prev,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY CASE WHEN lfl.tier = 'micro' THEN lfl.today_price END) AS micro_today,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY CASE WHEN lfl.tier = 'micro' THEN lfl.prev_price END) AS micro_prev,
            COUNT(*) AS like_for_like_count
        FROM like_for_like lfl
    """)
    lfl_row = cur.fetchone()
    
    def calc_change(current, prev):
        if prev and prev > 0:
            return round(((float(current) - float(prev)) / float(prev)) * 100, 2)
        return 0.0
    
    if composite and lfl_row:
        composite["change_24h"] = calc_change(lfl_row[0], lfl_row[1])
    
    tier_changes = {
        "frontier": (lfl_row[2], lfl_row[3]),
        "standard": (lfl_row[4], lfl_row[5]),
        "budget": (lfl_row[6], lfl_row[7]),
        "micro": (lfl_row[8], lfl_row[9]),
    }
    for tier_name in tiers:
        if tier_name in tier_changes:
            today_val, prev_val = tier_changes[tier_name]
            if today_val is not None and prev_val is not None:
                tiers[tier_name]["change_24h"] = calc_change(today_val, prev_val)
            else:
                tiers[tier_name]["change_24h"] = 0.0
    
    if spread:
        spread["change_24h"] = 0.0
    
    cur.close()
    conn.close()
    
    headers = get_rate_limit_headers(api_user, limits)
    return JSONResponse(
        content={
            "date": str(date.today()),
            "composite": composite,
            "tiers": tiers,
            "spread": spread,
        },
        headers=headers
    )

@app.get("/v1/sit/composite/history")
async def get_sit_history(
    request: Request,
    days: int = Query(30, ge=1, le=365),
    tier: Optional[str] = Query(None, regex="^(composite|frontier|standard|budget|micro|spread)$"),
    authorization: Optional[str] = Header(None)
):
    """Returns historical SIT-Composite values."""
    api_user = get_api_user(authorization)
    limits = check_rate_limit(api_user, is_ssr=request.headers.get("X-SSR-Secret") == SSR_SECRET)
    
    # Limit history based on plan
    max_days = limits["history_days"]
    if days > max_days:
        days = max_days
    
    conn = get_db()
    cur = conn.cursor()
    
    if tier:
        cur.execute("""
            SELECT date, tier, sit_price, sit_index_points, model_count
            FROM sit_index_values
            WHERE tier = %s AND date >= CURRENT_DATE - make_interval(days => %s)
            ORDER BY date ASC
        """, (tier, days))
    else:
        cur.execute("""
            SELECT date, tier, sit_price, sit_index_points, model_count
            FROM sit_index_values
            WHERE date >= CURRENT_DATE - make_interval(days => %s)
            ORDER BY date ASC, tier
        """, (days,))
    
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    # Group by date
    history = []
    current_date = None
    current_entry = None
    
    for row in rows:
        if row[0] != current_date:
            if current_entry:
                history.append(current_entry)
            current_date = row[0]
            current_entry = {"date": str(row[0]), "tiers": {}}
        current_entry["tiers"][row[1]] = {
            "price_per_m": row[2],
            "index_points": row[3],
            "model_count": row[4],
        }
    
    if current_entry:
        history.append(current_entry)
    
    headers = get_rate_limit_headers(api_user, limits)
    return JSONResponse(
        content={"history": history, "days": len(history)},
        headers=headers
    )

@app.get("/v1/models")
async def get_models(
    request: Request,
    tier: Optional[str] = Query(None, regex="^(frontier|standard|budget|micro)$"),
    provider: Optional[str] = Query(None),
    sort: str = Query("sit_score", regex="^(blended|input|output|sit_score)$"),
    limit: int = Query(50, ge=1, le=315),
    authorization: Optional[str] = Header(None)
):
    """Returns all tracked models with current pricing."""
    api_user = get_api_user(authorization)
    limits = check_rate_limit(api_user, is_ssr=request.headers.get("X-SSR-Secret") == SSR_SECRET)
    
    conn = get_db()
    cur = conn.cursor()
    
    # Build query using latest_prices view
    # ZDR/EU flags: check if any endpoint for this model is on a ZDR or EU provider
    # 24h change from price_changes_24h view, 7d change via subquery on price_snapshots
    query = """
        SELECT m.id, m.name, m.provider, m.tier, m.context_length, m.aa_index_score,
               m.modality, m.is_reasoning,
               lp.input_price_per_m, lp.output_price_per_m, lp.blended_price_per_m,
               lp.sit_score, lp.reasoning_multiplier, lp.sit_adjusted_price,
               lp.fetched_at, lp.source_count,
               COALESCE(zdr_sub.is_zdr, FALSE), COALESCE(eu_sub.is_eu, FALSE),
               COALESCE(pc24.change_24h_pct, 0),
               COALESCE(ch7.change_pct, 0)
        FROM models m
        JOIN latest_prices lp ON m.id = lp.model_id
        LEFT JOIN price_changes_24h pc24 ON m.id = pc24.model_id
        LEFT JOIN (
            SELECT DISTINCT ON (ps.model_id) ps.model_id,
                   ROUND(((lp2.blended_price_per_m - ps.blended_price_per_m)::numeric / NULLIF(ps.blended_price_per_m, 0)::numeric) * 100, 2) AS change_pct
            FROM price_snapshots ps
            JOIN latest_prices lp2 ON ps.model_id = lp2.model_id
            WHERE ps.fetched_at < NOW() - INTERVAL '6 days'
            ORDER BY ps.model_id, ps.fetched_at DESC
        ) ch7 ON m.id = ch7.model_id
        LEFT JOIN (
            SELECT DISTINCT me.model_id, TRUE as is_zdr
            FROM model_endpoints me
            JOIN providers p ON me.endpoint_provider = p.name
            WHERE p.is_zdr = TRUE
        ) zdr_sub ON m.id = zdr_sub.model_id
        LEFT JOIN (
            SELECT DISTINCT me.model_id, TRUE as is_eu
            FROM model_endpoints me
            JOIN providers p ON me.endpoint_provider = p.name
            WHERE p.is_eu_sovereign = TRUE
        ) eu_sub ON m.id = eu_sub.model_id
        WHERE m.is_active = TRUE AND lp.blended_price_per_m > 0 AND m.id NOT LIKE '%%:batch'
    """
    params = []
    
    if tier:
        query += " AND m.tier = %s"
        params.append(tier)
    
    if provider:
        query += " AND m.provider ILIKE %s"
        params.append(f"%{provider}%")
    
    # Sort
    sort_map = {
        "blended": "lp.blended_price_per_m ASC",
        "input": "lp.input_price_per_m ASC",
        "output": "lp.output_price_per_m ASC",
        "sit_score": "lp.sit_score ASC NULLS LAST",
    }
    query += f" ORDER BY {sort_map.get(sort, sort_map['sit_score'])}"
    
    query += " LIMIT %s"
    params.append(limit)
    
    cur.execute(query, params)
    rows = cur.fetchall()
    
    # Get total count
    count_query = "SELECT COUNT(*) FROM models m JOIN latest_prices lp ON m.id = lp.model_id WHERE m.is_active = TRUE AND lp.blended_price_per_m > 0 AND m.id NOT LIKE '%%:batch'"
    count_params = []
    if tier:
        count_query += " AND m.tier = %s"
        count_params.append(tier)
    if provider:
        count_query += " AND m.provider ILIKE %s"
        count_params.append(f"%{provider}%")
    
    cur.execute(count_query, count_params)
    total = cur.fetchone()[0]
    
    cur.close()
    conn.close()
    
    models = []
    for row in rows:
        models.append({
            "model_id": row[0],
            "name": row[1],
            "provider": row[2],
            "tier": row[3],
            "context_length": row[4],
            "aa_index_score": row[5],
            "modality": row[6],
            "is_reasoning": row[7],
            "input_price_per_m": row[8],
            "output_price_per_m": row[9],
            "blended_price_per_m": row[10],
            "sit_score": row[11],
            "reasoning_multiplier": row[12] if row[12] else 1.0,
            "sit_adjusted_price": row[13],
            "fetched_at": row[14].isoformat() if row[14] else None,
            "source_count": row[15] if row[15] else 1,
            "is_zdr": row[16],
            "is_eu_sovereign": row[17],
            "change_24h": float(row[18]) if row[18] else 0,
            "change_7d": float(row[19]) if row[19] else 0,
        })
    
    headers = get_rate_limit_headers(api_user, limits)
    return JSONResponse(
        content={
            "count": total,
            "returned": len(models),
            "models": models,
        },
        headers=headers
    )

# ============================================
# PROVIDERS
# ============================================

@app.get("/v1/providers")
async def get_providers(
    request: Request,
    authorization: Optional[str] = Header(None)
):
    """Returns all providers with model counts and price stats."""
    api_user = get_api_user(authorization)
    limits = check_rate_limit(api_user, is_ssr=request.headers.get("X-SSR-Secret") == SSR_SECRET)
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        WITH direct_models AS (
            SELECT 
                p.name as provider_name,
                COUNT(DISTINCT m.id) as direct_count,
                ROUND(AVG(lp.blended_price_per_m)::numeric, 4) as avg_price,
                ROUND(MIN(lp.blended_price_per_m)::numeric, 4) as min_price,
                ROUND(MAX(lp.blended_price_per_m)::numeric, 4) as max_price,
                COUNT(m.aa_index_score) as with_aa
            FROM providers p
            LEFT JOIN models m ON m.provider = p.name AND m.is_active = TRUE
            LEFT JOIN latest_prices lp ON m.id = lp.model_id AND lp.blended_price_per_m > 0
            WHERE m.id IS NULL OR (m.is_active = TRUE AND lp.blended_price_per_m > 0 AND m.id NOT LIKE '%%:batch')
            GROUP BY p.name
        ),
        endpoint_models AS (
            SELECT
                me.endpoint_provider as provider_name,
                COUNT(DISTINCT me.model_id) as endpoint_count
            FROM model_endpoints me
            JOIN models m ON me.model_id = m.id
            WHERE m.is_active = TRUE AND m.id NOT LIKE '%%:batch'
            GROUP BY me.endpoint_provider
        )
        SELECT 
            p.name,
            p.is_zdr,
            p.is_eu_sovereign,
            p.zdr_notes,
            p.eu_notes,
            COALESCE(dm.direct_count, 0) as model_count,
            dm.avg_price,
            dm.min_price,
            dm.max_price,
            COALESCE(dm.with_aa, 0) as with_aa,
            COALESCE(em.endpoint_count, 0) as endpoint_count
        FROM providers p
        LEFT JOIN direct_models dm ON p.name = dm.provider_name
        LEFT JOIN endpoint_models em ON p.name = em.provider_name
        WHERE COALESCE(dm.direct_count, 0) > 0 OR COALESCE(em.endpoint_count, 0) > 0
        ORDER BY (COALESCE(dm.direct_count, 0) + COALESCE(em.endpoint_count, 0)) DESC
    """)

    providers = []
    for row in cur.fetchall():
        direct = row[5] or 0
        endpoints = row[10] or 0
        if direct > 0 and endpoints > 0:
            ptype = "hybrid"
        elif direct > 0:
            ptype = "self-host"
        else:
            ptype = "aggregator"
        providers.append({
            "name": row[0],
            "is_zdr": row[1],
            "is_eu_sovereign": row[2],
            "zdr_notes": row[3] or "",
            "eu_notes": row[4] or "",
            "model_count": direct if direct > 0 else endpoints,
            "avg_price": float(row[6]) if row[6] else None,
            "min_price": float(row[7]) if row[7] else None,
            "max_price": float(row[8]) if row[8] else None,
            "with_aa": row[9] or 0,
            "endpoint_count": endpoints,
            "provider_type": ptype,
        })

    cur.close()
    conn.close()

    return JSONResponse(
        content={"count": len(providers), "providers": providers},
        headers={"Cache-Control": "public, max-age=300"}
    )


@app.get("/v1/providers/{provider_name}")
async def get_provider_detail(
    provider_name: str,
    request: Request,
    authorization: Optional[str] = Header(None)
):
    """Returns detailed stats for a single provider, including hosted endpoints."""
    api_user = get_api_user(authorization)
    limits = check_rate_limit(api_user, is_ssr=request.headers.get("X-SSR-Secret") == SSR_SECRET)
    conn = get_db()
    cur = conn.cursor()

    # Provider info
    cur.execute("""
        SELECT name, is_zdr, is_eu_sovereign, zdr_notes, eu_notes
        FROM providers WHERE name = %s
    """, (provider_name,))
    prow = cur.fetchone()
    if not prow:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Provider not found")

    # Hosted models: from model_endpoints (what this provider serves to users)
    # Includes both own models and third-party models they aggregate
    cur.execute("""
        SELECT DISTINCT ON (me.model_id)
            me.model_id, m.name, m.provider as model_owner, m.tier, m.context_length,
            m.aa_index_score, m.modality, m.is_reasoning,
            me.input_price_per_m, me.output_price_per_m, me.blended_price_per_m,
            lp.sit_score, lp.sit_adjusted_price, me.fetched_at, me.source, me.raw_data
        FROM model_endpoints me
        JOIN models m ON me.model_id = m.id
        LEFT JOIN latest_prices lp ON me.model_id = lp.model_id
        WHERE me.endpoint_provider = %s
          AND m.is_active = TRUE
          AND me.blended_price_per_m > 0
          AND m.id NOT LIKE '%%:batch'
        ORDER BY me.model_id, me.fetched_at DESC
    """, (provider_name,))

    models = []
    for row in cur.fetchall():
        raw = row[15] if row[15] else {}
        if isinstance(raw, str):
            import json as _json
            try:
                raw = _json.loads(raw)
            except Exception:
                raw = {}
        models.append({
            "model_id": row[0],
            "name": row[1],
            "model_owner": row[2],
            "tier": row[3],
            "context_length": row[4],
            "aa_index_score": float(row[5]) if row[5] else None,
            "modality": row[6],
            "is_reasoning": row[7],
            "input_price_per_m": float(row[8]) if row[8] else 0,
            "output_price_per_m": float(row[9]) if row[9] else 0,
            "blended_price_per_m": float(row[10]) if row[10] else 0,
            "sit_score": int(row[11]) if row[11] else None,
            "sit_adjusted_price": float(row[12]) if row[12] else None,
            "fetched_at": row[13].isoformat() if row[13] else None,
            "source": row[14] or "",
            "hosting_type": raw.get("hosting_type", ""),
            "quantization": raw.get("quantization", ""),
            "is_zdr": prow[1] or False,
            "is_eu_sovereign": prow[2] or False,
        })

    # Direct models (owned by this provider)
    cur.execute("""
        SELECT COUNT(*) FROM models
        WHERE provider = %s AND is_active = TRUE
          AND id NOT LIKE '%%:batch'
    """, (provider_name,))
    direct_count = cur.fetchone()[0]

    # Unique model owners (for aggregator detection)
    owner_set = set(m["model_owner"] for m in models if m["model_owner"] and m["model_owner"] != provider_name)
    is_aggregator = len(owner_set) > 0
    provider_type = "aggregator" if len(owner_set) > 3 else ("hybrid" if len(owner_set) > 0 and direct_count > 0 else ("self-host" if direct_count > 0 else "aggregator"))

    # Tier breakdown from hosted models
    tier_map = {}
    for m in models:
        t = m["tier"]
        if t not in tier_map:
            tier_map[t] = []
        tier_map[t].append(m["blended_price_per_m"])

    tiers = {}
    for t, prices in tier_map.items():
        tiers[t] = {
            "count": len(prices),
            "avg_price": round(sum(prices) / len(prices), 4),
            "min_price": round(min(prices), 4),
            "max_price": round(max(prices), 4),
        }

    cur.close()
    conn.close()

    return JSONResponse(
        content={
            "name": prow[0],
            "is_zdr": prow[1] or False,
            "is_eu_sovereign": prow[2] or False,
            "zdr_notes": prow[3] or "",
            "eu_notes": prow[4] or "",
            "model_count": len(models),
            "direct_model_count": direct_count,
            "provider_type": provider_type,
            "owners": sorted(owner_list) if (owner_list := list(owner_set)) else [],
            "models": models,
            "tiers": tiers,
        },
        headers={"Cache-Control": "public, max-age=300"}
    )


@app.get("/v1/models/{model_id:path}/endpoints")
async def get_model_endpoints(
    model_id: str,
    request: Request,
    authorization: Optional[str] = Header(None)
):
    """Returns all provider endpoints for a single model (multi-provider pricing)."""
    # Strip trailing /endpoints if captured via :path
    if model_id.endswith("/endpoints"):
        model_id = model_id[:-10]
    
    api_user = get_api_user(authorization)
    limits = check_rate_limit(api_user, is_ssr=request.headers.get("X-SSR-Secret") == SSR_SECRET)
    
    conn = get_db()
    cur = conn.cursor()
    
    # Check model exists
    cur.execute("SELECT id, name FROM models WHERE id = %s", (model_id,))
    model = cur.fetchone()
    if not model:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail={
            "error": {
                "code": "not_found",
                "message": f"Model '{model_id}' not found"
            }
        })
    
    # Get latest endpoints (within 24h)
    cur.execute("""
        SELECT DISTINCT ON (endpoint_provider)
            endpoint_provider,
            input_price_per_m,
            output_price_per_m,
            blended_price_per_m,
            context_length,
            fetched_at
        FROM model_endpoints
        WHERE model_id = %s AND fetched_at >= NOW() - INTERVAL '24 hours'
        ORDER BY endpoint_provider, fetched_at DESC
    """, (model_id,))
    
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    endpoints = []
    for row in rows:
        endpoints.append({
            "provider": row[0],
            "input_price_per_m": row[1],
            "output_price_per_m": row[2],
            "blended_price_per_m": row[3],
            "context_length": row[4],
            "fetched_at": row[5].isoformat() if row[5] else None,
        })
    
    # Sort by blended price ascending (cheapest first)
    endpoints.sort(key=lambda x: x["blended_price_per_m"] or 0)
    
    headers = get_rate_limit_headers(api_user, limits)
    return JSONResponse(
        content={
            "model_id": model[0],
            "name": model[1],
            "endpoints": endpoints,
            "count": len(endpoints),
        },
        headers=headers
    )

@app.get("/v1/models/{model_id:path}/history")
async def get_model_history(
    model_id: str,
    request: Request,
    days: int = Query(30, ge=1, le=365),
    authorization: Optional[str] = Header(None)
):
    """Returns historical price data for a single model."""
    # Strip trailing /history if FastAPI captured it via :path
    if model_id.endswith("/history"):
        model_id = model_id[:-8]
    
    api_user = get_api_user(authorization)
    limits = check_rate_limit(api_user, is_ssr=request.headers.get("X-SSR-Secret") == SSR_SECRET)
    
    # Limit history based on plan
    max_days = limits["history_days"]
    if days > max_days:
        days = max_days
    
    conn = get_db()
    cur = conn.cursor()
    
    # Check model exists
    cur.execute("SELECT id, name FROM models WHERE id = %s", (model_id,))
    model = cur.fetchone()
    if not model:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail={
            "error": {
                "code": "not_found",
                "message": f"Model '{model_id}' not found"
            }
        })
    
    # Get daily close (last snapshot per day)
    cur.execute("""
        SELECT DISTINCT ON (fetched_at::date)
            fetched_at::date AS day,
            input_price_per_m,
            output_price_per_m,
            blended_price_per_m,
            sit_score,
            reasoning_multiplier,
            sit_adjusted_price,
            fetched_at
        FROM price_snapshots
        WHERE model_id = %s
            AND fetched_at >= NOW() - make_interval(days => %s)
        ORDER BY fetched_at::date ASC, fetched_at DESC
    """, (model_id, days))
    
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    history = []
    for row in rows:
        history.append({
            "date": str(row[0]),
            "input_price_per_m": row[1],
            "output_price_per_m": row[2],
            "blended_price_per_m": row[3],
            "sit_score": row[4],
            "reasoning_multiplier": row[5] if row[5] else 1.0,
            "sit_adjusted_price": row[6],
            "fetched_at": row[7].isoformat() if row[7] else None,
        })
    
    headers = get_rate_limit_headers(api_user, limits)
    return JSONResponse(
        content={
            "model_id": model[0],
            "name": model[1],
            "history": history,
            "days": len(history),
        },
        headers=headers
    )

@app.get("/v1/models/{model_id:path}")
async def get_model(
    model_id: str,
    request: Request,
    authorization: Optional[str] = Header(None)
):
    """Returns detailed pricing and metadata for a single model."""
    # If someone hits /models/{id}/history without the history route matching,
    # redirect them
    if model_id.endswith("/history"):
        raise HTTPException(status_code=404, detail={
            "error": {
                "code": "not_found",
                "message": f"Model '{model_id}' not found. Did you mean /v1/models/{model_id[:-8]}/history?"
            }
        })
    api_user = get_api_user(authorization)
    limits = check_rate_limit(api_user, is_ssr=request.headers.get("X-SSR-Secret") == SSR_SECRET)
    
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT m.id, m.name, m.provider, m.tier, m.context_length, m.aa_index_score,
               m.modality, m.tokenizer, m.is_reasoning, m.created_at,
               lp.input_price_per_m, lp.output_price_per_m, lp.blended_price_per_m,
               lp.sit_score, lp.reasoning_multiplier, lp.sit_adjusted_price,
               lp.source, lp.fetched_at
        FROM models m
        JOIN latest_prices lp ON m.id = lp.model_id
        WHERE m.id = %s
    """, (model_id,))
    
    row = cur.fetchone()
    
    if not row:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail={
            "error": {
                "code": "not_found",
                "message": f"Model '{model_id}' not found",
                "documentation_url": "https://inferenceindexer.ai/api/docs#errors"
            }
        })
    
    # Get 24h change (use blended price, not sit_score which may be null)
    change_24h = calc_change_24h(conn, model_id, row[12])
    change_7d = calc_change_7d(conn, model_id, row[12])
    
    # Get tier median price from SIT index (consistent with homepage headline)
    cur.execute("""
        SELECT sit_price FROM sit_index_values
        WHERE tier = %s
        ORDER BY date DESC LIMIT 1
    """, (row[3],))
    tier_avg_result = cur.fetchone()
    tier_avg = tier_avg_result[0] if tier_avg_result else None
    
    # Get composite price for comparison
    cur.execute("""
        SELECT sit_price FROM sit_index_values
        WHERE tier = 'composite'
        ORDER BY date DESC LIMIT 1
    """)
    composite_price = cur.fetchone()
    composite_price = composite_price[0] if composite_price else None
    
    cur.close()
    conn.close()
    
    # Build comparison
    blended = row[12]  # blended_price_per_m
    reasoning_multiplier = row[14] if row[14] else 1.0
    sit_adjusted = row[15]
    comparisons = {}
    if tier_avg and tier_avg > 0 and blended is not None:
        comparisons["below_tier_avg_pct"] = round(((tier_avg - blended) / tier_avg) * 100, 1) if blended < tier_avg else 0
        comparisons["above_tier_avg_pct"] = round(((blended - tier_avg) / tier_avg) * 100, 1) if blended > tier_avg else 0
    if composite_price and composite_price > 0 and blended is not None:
        comparisons["above_composite_pct"] = round(((blended - composite_price) / composite_price) * 100, 1) if blended > composite_price else 0
    
    # Tier ranking
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT m.id, m.name, lp.blended_price_per_m, lp.sit_score
        FROM models m
        JOIN latest_prices lp ON m.id = lp.model_id
        WHERE m.tier = %s AND lp.blended_price_per_m > 0
        ORDER BY lp.sit_score ASC NULLS LAST
    """, (row[3],))
    tier_rows = cur.fetchall()
    tier_rank = None
    tier_total = len(tier_rows)
    for i, tr in enumerate(tier_rows, 1):
        if tr[0] == model_id:
            tier_rank = i
            break
    cur.close()
    conn.close()
    
    headers = get_rate_limit_headers(api_user, limits)
    return JSONResponse(
        content={
            "model_id": row[0],
            "name": row[1],
            "provider": row[2],
            "tier": row[3],
            "context_length": row[4],
            "aa_index_score": row[5],
            "modality": row[6],
            "tokenizer": row[7],
            "is_reasoning": row[8],
            "date_added": row[9].isoformat() if row[9] else None,
            "input_price_per_m": row[10],
            "output_price_per_m": row[11],
            "blended_price_per_m": row[12],
            "sit_score": row[13],
            "reasoning_multiplier": reasoning_multiplier,
            "sit_adjusted_price": sit_adjusted,
            "change_24h": change_24h,
            "change_7d": change_7d,
            "tier_average_price": round(tier_avg, 4) if tier_avg else None,
            "tier_rank": tier_rank,
            "tier_total_models": tier_total,
            "comparisons": comparisons,
            "source": row[16],
            "fetched_at": row[17].isoformat() if row[17] else None,
        },
        headers=headers
    )

# ============================================
# API KEY GENERATION (for signup)
# ============================================

def generate_api_key():
    """Generate a new API key."""
    return f"ii_sk_{secrets.token_hex(24)}"

@app.post("/v1/auth/signup")
async def signup(email: str):
    """Sign up for a free API key."""
    conn = get_db()
    cur = conn.cursor()
    
    # Check if email already exists
    cur.execute("SELECT api_key FROM api_users WHERE email = %s", (email,))
    existing = cur.fetchone()
    
    if existing:
        cur.close()
        conn.close()
        return {"api_key": existing[0], "plan": "free", "message": "Existing key retrieved"}
    
    api_key = generate_api_key()
    cur.execute("""
        INSERT INTO api_users (email, api_key, plan)
        VALUES (%s, %s, 'free')
        RETURNING api_key
    """, (email, api_key))
    
    new_key = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    
    return {"api_key": new_key, "plan": "free", "message": "API key created"}

# ============================================
# AUTH: USER INFO & KEY MANAGEMENT
# ============================================

@app.get("/v1/auth/me")
async def get_me(authorization: str = Header(None)):
    """Get current user info including API key, plan, and usage."""
    if not authorization or not authorization.startswith("Bearer "):
        return JSONResponse(status_code=401, content={"error": "Missing or invalid authorization header"})
    
    token = authorization.replace("Bearer ", "").strip()
    conn = get_db()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT email, api_key, plan, request_count, rate_limit_per_day
            FROM api_users WHERE api_key = %s
        """, (token,))
        row = cur.fetchone()
        
        if not row:
            return JSONResponse(status_code=401, content={"error": "Invalid API key"})
        
        return {
            "email": row[0],
            "api_key": row[1],
            "plan": row[2],
            "request_count": row[3],
            "rate_limit_per_day": row[4],
        }
    finally:
        cur.close()
        conn.close()

@app.post("/v1/auth/regenerate-key")
async def regenerate_key(authorization: str = Header(None)):
    """Generate a new API key, invalidating the old one."""
    if not authorization or not authorization.startswith("Bearer "):
        return JSONResponse(status_code=401, content={"error": "Missing or invalid authorization header"})
    
    token = authorization.replace("Bearer ", "").strip()
    conn = get_db()
    cur = conn.cursor()
    
    try:
        # Verify the old key exists
        cur.execute("SELECT id FROM api_users WHERE api_key = %s", (token,))
        if not cur.fetchone():
            return JSONResponse(status_code=401, content={"error": "Invalid API key"})
        
        # Generate new key
        new_key = generate_api_key()
        cur.execute("""
            UPDATE api_users SET api_key = %s WHERE api_key = %s
            RETURNING api_key
        """, (new_key, token))
        row = cur.fetchone()
        conn.commit()
        
        if not row:
            return JSONResponse(status_code=500, content={"error": "Failed to regenerate key"})
        
        return {"api_key": row[0], "message": "New API key generated. Old key is no longer valid."}
    finally:
        cur.close()
        conn.close()

# ============================================
# HEALTH CHECK
# ============================================

@app.get("/health")
async def health():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM models")
        count = cur.fetchone()[0]
        cur.execute("SELECT MAX(fetched_at) FROM price_snapshots")
        last_fetch = cur.fetchone()[0]
        cur.close()
        conn.close()
        return {
            "status": "healthy",
            "models": count,
            "last_fetch": last_fetch.isoformat() if last_fetch else None,
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )

# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
