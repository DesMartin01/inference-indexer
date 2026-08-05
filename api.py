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
# FASTAPI APP
# ============================================

app = FastAPI(
    title="InferenceIndexer API",
    description="Independent price index for AI inference",
    version="1.0.0",
)

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
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": [
            "/v1/sit/composite/latest",
            "/v1/sit/composite/history",
            "/v1/models",
            "/v1/models/{model_id}",
            "/v1/models/{model_id}/history"
        ]
    }

@app.get("/v1/sit/composite/latest")
async def get_sit_latest(request: Request, authorization: Optional[str] = Header(None)):
    """Returns the current SIT-Composite index value, including tier breakdowns."""
    api_user = get_api_user(authorization)
    limits = check_rate_limit(api_user, is_ssr=request.headers.get("X-SSR-Secret") == SSR_SECRET)
    
    conn = get_db()
    cur = conn.cursor()
    
    # Get latest SIT values
    cur.execute("""
        SELECT date, tier, sit_price, sit_index_points, model_count, provider_count
        FROM sit_index_values
        WHERE date = (SELECT MAX(date) FROM sit_index_values)
        ORDER BY 
            CASE tier 
                WHEN 'composite' THEN 0 
                WHEN 'frontier' THEN 1 
                WHEN 'standard' THEN 2 
                WHEN 'budget' THEN 3 
                WHEN 'micro' THEN 4 
                WHEN 'spread' THEN 5 
            END
    """)
    rows = cur.fetchall()
    
    if not rows:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="No SIT data available")
    
    latest_date = str(rows[0][0])
    
    composite = None
    tiers = {}
    spread = None
    
    for row in rows:
        entry = {
            "price_per_m": row[2],
            "index_points": row[3],
            "models": row[4],
            "providers": row[5],
        }
        if row[1] == "composite":
            composite = entry
        elif row[1] == "spread":
            spread = entry
        else:
            tiers[row[1]] = entry
    
    # Get changes (need yesterday's data)
    cur.execute("""
        SELECT date, tier, sit_price FROM sit_index_values
        WHERE date < (SELECT MAX(date) FROM sit_index_values)
        ORDER BY date DESC LIMIT 6
    """)
    prev_rows = cur.fetchall()
    prev_prices = {row[1]: row[2] for row in prev_rows}
    
    def calc_change(current, prev):
        if prev and prev > 0:
            return round(((current - prev) / prev) * 100, 2)
        return 0.0
    
    if composite and "composite" in prev_prices:
        composite["change_24h"] = calc_change(composite["price_per_m"], prev_prices.get("composite"))
    
    for tier_name in tiers:
        if tier_name in prev_prices:
            tiers[tier_name]["change_24h"] = calc_change(tiers[tier_name]["price_per_m"], prev_prices.get(tier_name))
    
    if spread and "spread" in prev_prices:
        spread["change_24h"] = calc_change(spread["price_per_m"], prev_prices.get("spread"))
    
    cur.close()
    conn.close()
    
    headers = get_rate_limit_headers(api_user, limits)
    return JSONResponse(
        content={
            "date": latest_date,
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
    query = """
        SELECT m.id, m.name, m.provider, m.tier, m.context_length, m.aa_index_score,
               m.modality, m.is_reasoning,
               lp.input_price_per_m, lp.output_price_per_m, lp.blended_price_per_m,
               lp.sit_score, lp.fetched_at
        FROM models m
        JOIN latest_prices lp ON m.id = lp.model_id
        WHERE m.is_active = TRUE AND lp.blended_price_per_m > 0
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
    count_query = "SELECT COUNT(*) FROM models m JOIN latest_prices lp ON m.id = lp.model_id WHERE m.is_active = TRUE AND lp.blended_price_per_m > 0"
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
            "fetched_at": row[12].isoformat() if row[12] else None,
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
            "fetched_at": row[5].isoformat() if row[5] else None,
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
               lp.sit_score, lp.source, lp.fetched_at
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
    
    # Get 24h change
    change_24h = calc_change_24h(conn, model_id, row[13])
    change_7d = calc_change_7d(conn, model_id, row[13])
    
    # Get tier average for comparison
    cur.execute("""
        SELECT AVG(lp.blended_price_per_m)
        FROM models m
        JOIN latest_prices lp ON m.id = lp.model_id
        WHERE m.tier = %s AND lp.blended_price_per_m > 0
    """, (row[3],))
    tier_avg = cur.fetchone()[0]
    
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
    blended = row[13]
    comparisons = {}
    if tier_avg and tier_avg > 0:
        comparisons["below_tier_avg_pct"] = round(((tier_avg - blended) / tier_avg) * 100, 1) if blended < tier_avg else 0
        comparisons["above_tier_avg_pct"] = round(((blended - tier_avg) / tier_avg) * 100, 1) if blended > tier_avg else 0
    if composite_price and composite_price > 0:
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
            "change_24h": change_24h,
            "change_7d": change_7d,
            "tier_average_price": round(tier_avg, 4) if tier_avg else None,
            "tier_rank": tier_rank,
            "tier_total_models": tier_total,
            "comparisons": comparisons,
            "source": row[14],
            "fetched_at": row[15].isoformat() if row[15] else None,
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
