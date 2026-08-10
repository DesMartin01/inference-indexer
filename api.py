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
    
    # Key rate-limit state by (plan, identity). The site's own SSR requests
    # (plan="ssr") MUST NOT share the anonymous "public" counter — otherwise
    # internal SSR traffic exhausts the public budget and 429s real users.
    base_key = api_user["email"] if api_user else "anonymous"
    key = f"{plan}:{base_key}"
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
    
    # Stamp the actual counter key onto limits so headers always read the
    # same counter that this request incremented (plan-aware).
    limits["_key"] = key
    return limits

def get_rate_limit_headers(api_user, limits, state=None):
    """Return rate limit headers for the response.

    `limits` is what check_rate_limit returned; if it carries a stamped `_key`,
    read the exact same counter (plan-aware). Otherwise fall back to deriving
    the anonymous/email key.
    """
    plan_key = (limits or {}).get("_key")
    if plan_key:
        state = _rate_limits.get(plan_key)
        remaining = max(0, limits["daily"] - (state["count"] if state else 0))
    else:
        if not api_user:
            key = "anonymous"
        else:
            key = api_user["email"] or "anonymous"
        state = _rate_limits.get(key)
        remaining = max(0, limits["daily"] - (state["count"] if state else 0))
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
# REQUEST LOGGING (API usage analytics)
# ============================================
# Every request that hits a /v1 endpoint is logged to `api_request_log`.
# This powers the admin API-usage dashboard (requests/day, unique users,
# top endpoints, plan mix) and later the pro-API billing story.
# The plan / user label are derived from the Authorization header + SSR
# secret so we can segment "people/agents" vs our own SSR traffic.

def _classify_request(request: Request) -> tuple[str, str | None]:
    """Determine (plan, user_label) for a request.

    - SSR secret header  -> ('ssr', None)  (our own frontend traffic)
    - Bearer api key     -> looked up in api_users -> (plan, email|anon label)
    - no key / "public"  -> ('public', None)
    """
    auth = request.headers.get("authorization", "")
    if request.headers.get("X-SSR-Secret") == SSR_SECRET:
        return "ssr", None
    if auth.startswith("Bearer "):
        token = auth[len("Bearer "):].strip()
        if not token or token == "public":
            return "public", None
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT email, plan FROM api_users WHERE api_key = %s", (token,))
            row = cur.fetchone()
            cur.close()
            conn.close()
            if row:
                return row[1] or "public", row[0]
        except Exception:
            pass
        return "public", None
    return "public", None


def _client_ip(request: Request) -> str:
    """Best-effort client IP behind the SSR proxy / nginx.

    Reads X-Forwarded-For (first hop) then falls back to request.client.
    Returns '' if unavailable. So admin usage can filter our own traffic by
    IP instead of counting every anonymous self-call as external usage.
    """
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    if request.client:
        return request.client.host or ""
    return ""


_api_log_buffer: list[tuple] = []


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log every /v1 API request for usage analytics."""
    path = request.url.path
    try:
        response = await call_next(request)
    except Exception:
        raise
    # Only log real /v1 API endpoints (skip /health, docs, etc.)
    if path.startswith("/v1/"):
        try:
            plan, user_label = _classify_request(request)
            ip = _client_ip(request)
            _api_log_buffer.append((
                plan,
                user_label,
                path,
                response.status_code,
                ip,
            ))
            _flush_api_log()
        except Exception:
            pass  # never let logging break the API
    return response


# Keep DB writes off the hot path: buffer rows and flush them in a single
# executemany call. Traffic is low (MVP), so we flush on every request to
# guarantee no buffered data is stranded; the buffer only actually holds
# rows when bursts arrive faster than a single flush cycle.


def _flush_api_log():
    global _api_log_buffer
    if not _api_log_buffer:
        return
    buf, _api_log_buffer = _api_log_buffer[:], []
    _LAST_FLUSH = time.time()
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.executemany(
            "INSERT INTO api_request_log (plan, user_label, endpoint, status, ip) VALUES (%s, %s, %s, %s, %s)",
            buf,
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception:
        pass

# ============================================
# HELPER: Query helpers
# ============================================

def calc_change_24h(conn, model_id, current_price):
    """Calculate 24h change for a model.

    Baselines against the snapshot closest to exactly 24h ago (within a
    6h-48h search window). Using a stable rolling 24h baseline - rather than
    "most recent snapshot older than 20h" - keeps the change window at a true
    24h and prevents movers dropping off before a full day has elapsed.
    """
    cur = conn.cursor()
    cur.execute("""
        SELECT blended_price_per_m
        FROM price_snapshots
        WHERE model_id = %s AND fetched_at BETWEEN NOW() - INTERVAL '48 hours' AND NOW() - INTERVAL '6 hours'
        ORDER BY ABS(EXTRACT(EPOCH FROM (fetched_at - (NOW() - INTERVAL '24 hours'))) )
        LIMIT 1
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
        "version": "1.2.0",
        "description": (
            "Independent AI inference price reporting. Live and historical "
            "pricing by model, provider comparison, and the SIT-Composite index. "
            "Pulled direct from inference providers - a more complete picture "
            "than aggregators like OpenRouter."
        ),
        "base_url": "https://api.inferenceindexer.ai",
        "docs": "/docs",
        "openapi_json": "/openapi.json",
        "get_an_api_key": "https://www.inferenceindexer.ai/for-agents",
        "anon_key": "POST /v1/auth/anonymous (instant key, no email/account)",
        "web_docs": "https://www.inferenceindexer.ai/api-docs",
        "model_count": "GET /v1/models",
        "historical_data": "GET /v1/models/{model_id}/history",
        "endpoints": [
            "/v1/sit/composite/latest",
            "/v1/sit/composite/history",
            "/v1/models",
            "/v1/models/{model_id}",
            "/v1/models/{model_id}/endpoints",
            "/v1/models/{model_id}/history",
            "/v1/providers",
            "/v1/providers/{provider_name}",
            "/health"
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

    # Fetch the latest STORED sit_index_points per tier (real rebased values,
    # anchored to the earliest data date). The API must NOT hardcode 1000.0 —
    # that froze the index and hid real price movement.
    cur.execute("""
        SELECT DISTINCT ON (tier) tier, sit_index_points
        FROM sit_index_values
        ORDER BY tier, date DESC
    """)
    stored_points = {row[0]: row[1] for row in cur.fetchall()}

    def idx(tier):
        v = stored_points.get(tier)
        return float(v) if v is not None else 1000.0

    composite = {
        "price_per_m": round(weighted_mean, 2),
        "index_points": idx("composite"),
        "models": model_count,
        "providers": provider_count,
    }

    tiers = {}
    for row in tier_rows:
        tier_name = row[0]
        tiers[tier_name] = {
            "price_per_m": round(float(row[1]), 2),
            "index_points": idx(tier_name),
            "models": row[2],
            "providers": row[3],
        }

    # Spread (frontier - budget)
    spread = None
    if "frontier" in tiers and "budget" in tiers:
        spread = {
            "price_per_m": round(tiers["frontier"]["price_per_m"] - tiers["budget"]["price_per_m"], 2),
            "index_points": round(idx("frontier") - idx("budget"), 2),
            "models": 0,
            "providers": 0,
        }
    
    # Compute changes from sit_index_values (daily stored values).
    # This matches the displayed price (same composite methodology) and
    # avoids the old bug where change was computed from a different model
    # set (median of ALL models) than the headline (usage-weighted top 50).
    # We look back 1/7/30/90 days; if no row exists for the exact target
    # date, we use the most recent row before it.
    cur.execute("""
        WITH target_dates AS (
            SELECT
                (CURRENT_DATE - INTERVAL '1 day')::date  AS d1,
                (CURRENT_DATE - INTERVAL '7 days')::date AS d7,
                (CURRENT_DATE - INTERVAL '30 days')::date AS d30,
                (CURRENT_DATE - INTERVAL '90 days')::date AS d90
        ),
        latest_by_tier AS (
            SELECT DISTINCT ON (tier) tier, date, sit_price
            FROM sit_index_values
            ORDER BY tier, date DESC
        ),
        lookback AS (
            SELECT
                t.tier,
                t.sit_price AS today_price,
                (
                    SELECT s.sit_price FROM sit_index_values s
                    WHERE s.tier = t.tier AND s.date <= td.d1
                    ORDER BY s.date DESC LIMIT 1
                ) AS price_1d,
                COALESCE(
                    (SELECT s.sit_price FROM sit_index_values s
                     WHERE s.tier = t.tier AND s.date <= td.d7
                     ORDER BY s.date DESC LIMIT 1),
                    (SELECT s.sit_price FROM sit_index_values s
                     WHERE s.tier = t.tier
                     ORDER BY s.date ASC LIMIT 1)
                ) AS price_7d,
                COALESCE(
                    (SELECT s.sit_price FROM sit_index_values s
                     WHERE s.tier = t.tier AND s.date <= td.d30
                     ORDER BY s.date DESC LIMIT 1),
                    (SELECT s.sit_price FROM sit_index_values s
                     WHERE s.tier = t.tier
                     ORDER BY s.date ASC LIMIT 1)
                ) AS price_30d,
                COALESCE(
                    (SELECT s.sit_price FROM sit_index_values s
                     WHERE s.tier = t.tier AND s.date <= td.d90
                     ORDER BY s.date DESC LIMIT 1),
                    (SELECT s.sit_price FROM sit_index_values s
                     WHERE s.tier = t.tier
                     ORDER BY s.date ASC LIMIT 1)
                ) AS price_90d
            FROM latest_by_tier t
            CROSS JOIN target_dates td
        )
        SELECT tier, today_price, price_1d, price_7d, price_30d, price_90d
        FROM lookback
    """)
    change_rows = cur.fetchall()

    def calc_change(current, prev):
        if prev is not None and float(prev) > 0:
            return round(((float(current) - float(prev)) / float(prev)) * 100, 2)
        return 0.0

    # Map tier names from the query to the response structures
    # 'composite' -> composite dict, everything else -> tiers dict
    for row in change_rows:
        tier_name = row[0]
        today = row[1]
        c1 = calc_change(today, row[2])
        c7 = calc_change(today, row[3])
        c30 = calc_change(today, row[4])
        c90 = calc_change(today, row[5])

        if tier_name == "composite" and composite:
            composite["change_24h"] = c1
            composite["change_7d"] = c7
            composite["change_30d"] = c30
            composite["change_90d"] = c90
        elif tier_name in tiers:
            tiers[tier_name]["change_24h"] = c1
            tiers[tier_name]["change_7d"] = c7
            tiers[tier_name]["change_30d"] = c30
            tiers[tier_name]["change_90d"] = c90

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
    limit: int = Query(50, ge=1, le=500),
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
            WHERE ps.fetched_at < NOW() - INTERVAL '5 days'
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
# PROVIDER SUBMISSIONS (self-serve listing)
# ============================================

def _verify_provider_endpoint(api_base_url, api_key=None):
    """Test that a submitted API base URL responds on /v1/models.

    Used to pre-validate a submission before it's approved. Returns
    (ok, model_count, detail). Never crashes - a failed probe just
    marks the submission invalid.
    """
    url = api_base_url.rstrip("/") + "/v1/models"
    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    import urllib.request
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status >= 400:
                return False, 0, f"HTTP {resp.status}"
            raw = resp.read().decode("utf-8", "replace")
        data = json.loads(raw)
        models = data.get("data", []) if isinstance(data, dict) else []
        return True, len(models), f"{len(models)} models reachable"
    except Exception as e:
        return False, 0, f"Could not reach endpoint: {type(e).__name__}"


@app.post("/v1/providers/submit")
async def submit_provider(submission: dict):
    """Accept a provider pricing submission for review.

    Stores the submission in a queue (status='pending'). The pricing
    endpoint is probed live (no auth) to pre-validate it. A human then
    reviews and approves/rejects it; approved submissions flow into the
    main pipeline.
    """
    required = ["provider_name", "api_base_url"]
    for field in required:
        if not submission.get(field):
            return JSONResponse(status_code=400, content={"error": f"Missing required field: {field}"})

    provider_name = submission["provider_name"].strip()
    api_base_url = submission["api_base_url"].strip()

    # Pre-validate the endpoint
    ok, model_count, detail = _verify_provider_endpoint(api_base_url, submission.get("api_key"))

    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO provider_submissions
            (provider_name, website, api_base_url, api_key, country,
             is_eu_sovereign, is_zdr, zdr_notes, contact_email, notes,
             status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s)
            ON CONFLICT (provider_name) DO UPDATE SET
                api_base_url = EXCLUDED.api_base_url,
                website = EXCLUDED.website,
                contact_email = EXCLUDED.contact_email,
                status = 'pending',
                reviewed_at = NULL
            RETURNING id
        """, (
            provider_name,
            submission.get("website", ""),
            api_base_url,
            submission.get("api_key"),
            submission.get("country", ""),
            bool(submission.get("is_eu_sovereign")),
            bool(submission.get("is_zdr")),
            submission.get("zdr_notes", ""),
            submission.get("contact_email", ""),
            submission.get("notes", ""),
            "pending",
        ))
        sub_id = cur.fetchone()[0]
        conn.commit()
    finally:
        cur.close()
        conn.close()

    return {
        "id": sub_id,
        "status": "pending",
        "endpoint_probe": {"ok": ok, "model_count": model_count, "detail": detail},
        "message": "Submission received. We'll review it and get back to you.",
    }


@app.get("/v1/providers/submissions")
async def list_submissions(request: Request):
    """List provider submissions. Review queue for the site owner.

    Protected by the SSR secret header - not public.
    """
    if request.headers.get("X-SSR-Secret") != SSR_SECRET:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    where = ""
    params = []
    if request.query_params.get("status"):
        where = "WHERE status = %s"
        params.append(request.query_params.get("status"))

    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT ps.id, ps.provider_name, ps.website, ps.api_base_url, ps.country,
                   ps.is_eu_sovereign, ps.is_zdr, ps.zdr_notes, ps.contact_email, ps.notes,
                   ps.status, ps.created_at,
                   p.integration_status
            FROM provider_submissions ps
            LEFT JOIN providers p ON lower(p.name) = lower(ps.provider_name)
            {where}
            ORDER BY ps.created_at DESC
        """.format(where=where), params)
        rows = cur.fetchall()
        return {
            "count": len(rows),
            "submissions": [
                {
                    "id": r[0], "provider_name": r[1], "website": r[2],
                    "api_base_url": r[3], "country": r[4],
                    "is_eu_sovereign": r[5], "is_zdr": r[6], "zdr_notes": r[7],
                    "contact_email": r[8], "notes": r[9],
                    "status": r[10], "created_at": r[11].isoformat() if r[11] else None,
                    "integration_status": r[12],
                }
                for r in rows
            ],
        }
    finally:
        cur.close()
        conn.close()


@app.post("/v1/providers/submissions/{submission_id}/review")
async def review_submission(submission_id: int, decision: dict, request: Request):
    """Approve or reject a submitted provider. Owner-only (SSR secret)."""
    if request.headers.get("X-SSR-Secret") != SSR_SECRET:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    new_status = decision.get("status")
    if new_status not in ("approved", "rejected"):
        return JSONResponse(status_code=400, content={"error": "status must be approved or rejected"})

    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE provider_submissions
            SET status = %s, reviewed_by = 'des', reviewed_at = now()
            WHERE id = %s
            RETURNING id
        """, (new_status, submission_id))
        if cur.fetchone() is None:
            return JSONResponse(status_code=404, content={"error": "Submission not found"})
        conn.commit()

        if new_status == "approved":
            # If approved, ensure the provider exists in the providers table.
            # Newly approved providers are marked 'pending_integration' until
            # a pipeline connector is wired up to actually fetch their prices.
            # If the provider already exists and is integrated, keep it
            # integrated (don't downgrade it).
            cur.execute("""
                SELECT provider_name FROM provider_submissions WHERE id = %s
            """, (submission_id,))
            row = cur.fetchone()
            if row:
                cur.execute("""
                    INSERT INTO providers (name, is_zdr, is_eu_sovereign, integration_status)
                    VALUES (%s, %s, %s, 'pending_integration')
                    ON CONFLICT (name) DO UPDATE SET
                        is_zdr = EXCLUDED.is_zdr,
                        is_eu_sovereign = EXCLUDED.is_eu_sovereign,
                        integration_status = providers.integration_status
                """, (row[0], decision.get("is_zdr", False), decision.get("is_eu_sovereign", False)))
                conn.commit()
    finally:
        cur.close()
        conn.close()

    return {"id": submission_id, "status": new_status}


# ============================================
# API USAGE ANALYTICS (admin dashboard)
# ============================================

@app.get("/v1/admin/api-usage")
async def api_usage(request: Request):
    """Aggregate API usage for the admin dashboard.

    Returns requests/day, unique users/agents, plan mix, top endpoints and
    an hourly series. Protected by the SSR secret header - not public.
    Excludes our own SSR (frontend) traffic by default so the numbers show
    external people/agent usage; set ?include_ssr=1 to include it.
    """
    if request.headers.get("X-SSR-Secret") != SSR_SECRET:
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    include_ssr = request.query_params.get("include_ssr") == "1"
    # Exclude our own frontend SSR traffic AND our own admin/monitoring
    # self-calls (/v1/admin/*) by default, so the headline numbers reflect
    # real external endpoint usage, not the dashboard counting itself.
    # include_ssr=1 also surfaces the ssr/admin rows for a full audit.
    scope_filter = "" if include_ssr else "AND plan <> 'ssr' AND endpoint NOT LIKE '/v1/admin/%%'"

    conn = get_db()
    cur = conn.cursor()
    try:
        now = datetime.now(timezone.utc)

        # --- Today summary ---
        # Primary "requests" headline = registered API-key (free) traffic,
        # which by construction reflects real third-party signups. Anonymous
        # 'public' traffic (bots/crawlers/our own browsing) is reported
        # separately and not presented as usage.
        cur.execute(
            f"""\
            SELECT
                COUNT(*) FILTER (WHERE plan = 'free'),
                COUNT(DISTINCT user_label) FILTER (WHERE plan = 'free' AND user_label IS NOT NULL),
                COUNT(*) FILTER (WHERE plan = 'public'),
                COUNT(*)
            FROM api_request_log
            WHERE ts >= %s {scope_filter}
            """,
            (now.replace(hour=0, minute=0, second=0, microsecond=0),),
        )
        r = cur.fetchone()
        today = {
            "requests": r[0],            # registered-key real usage (headline)
            "registered_key_requests": r[0],
            "unique_users": r[1],        # distinct registered-key users today
            "free_requests": r[0],       # kept for frontend card (registered-key)
            "free_users": r[1],          # kept for frontend card
            "public_requests": r[2],     # anonymous traffic (separate, not usage)
            "all_requests": r[3],        # everything non-ssr incl. anonymous
            "public_users": None,
        }

        # --- Last 14 days daily series ---
        cur.execute(
            f"""
            SELECT
                date_trunc('day', ts)::date AS day,
                COUNT(*),
                COUNT(DISTINCT user_label::text),
                COUNT(DISTINCT user_label::text) FILTER (WHERE plan = 'free' AND user_label IS NOT NULL)
            FROM api_request_log
            WHERE ts >= %s {scope_filter}
            GROUP BY 1 ORDER BY 1
            """,
            (now - timedelta(days=14),),
        )
        daily = [
            {"date": d.isoformat(), "requests": c, "unique_users": u, "free_users": f}
            for d, c, u, f in cur.fetchall()
        ]

        # --- Plan mix (this month), with distinct users per plan ---
        cur.execute(
            f"""
            SELECT plan, COUNT(*), COUNT(DISTINCT user_label::text) FILTER (WHERE user_label IS NOT NULL)
            FROM api_request_log
            WHERE ts >= %s {scope_filter}
            GROUP BY plan ORDER BY 2 DESC
            """,
            (now - timedelta(days=30),),
        )
        plan_mix = [{"plan": p, "requests": c, "users": u} for p, c, u in cur.fetchall()]

        # --- New free-plan signups (30d) + recent free-key activity ---
        cur.execute(
            """
            SELECT COUNT(*) FROM api_users
            WHERE plan = 'free' AND created_at >= NOW() - INTERVAL '30 days'
            """
        )
        new_free_signups_30d = cur.fetchone()[0] or 0

        cur.execute(
            f"""
            SELECT user_label, endpoint, COUNT(*), MAX(ts)
            FROM api_request_log
            WHERE plan = 'free' AND user_label IS NOT NULL AND ts >= %s {scope_filter}
            GROUP BY user_label, endpoint
            ORDER BY MAX(ts) DESC
            LIMIT 25
            """,
            (now - timedelta(days=30),),
        )
        free_key_activity = [
            {"user": u, "endpoint": e, "requests": c, "last": l.isoformat() if l else None}
            for u, e, c, l in cur.fetchall()
        ]

        # --- Top endpoints (7d) ---
        cur.execute(
            f"""
            SELECT endpoint, COUNT(*)
            FROM api_request_log
            WHERE ts >= %s {scope_filter}
            GROUP BY endpoint ORDER BY 2 DESC LIMIT 12
            """,
            (now - timedelta(days=7),),
        )
        top_endpoints = [{"endpoint": e, "requests": c} for e, c in cur.fetchall()]

        # --- Hourly series for today ---
        cur.execute(
            f"""
            SELECT date_trunc('hour', ts) AS h, COUNT(*)
            FROM api_request_log
            WHERE ts >= %s {scope_filter}
            GROUP BY 1 ORDER BY 1
            """,
            (now.replace(hour=0, minute=0, second=0, microsecond=0),),
        )
        hourly = [{"hour": h.isoformat(), "requests": c} for h, c in cur.fetchall()]

        # --- Status mix (7d) ---
        cur.execute(
            f"""
            SELECT status, COUNT(*)
            FROM api_request_log
            WHERE ts >= %s {scope_filter}
            GROUP BY status ORDER BY 2 DESC
            """,
            (now - timedelta(days=7),),
        )
        status_mix = [{"status": s, "requests": c} for s, c in cur.fetchall()]

        return {
            "today": today,
            "daily": daily,
            "plan_mix": plan_mix,
            "top_endpoints": top_endpoints,
            "hourly": hourly,
            "status_mix": status_mix,
            "new_free_signups_30d": new_free_signups_30d,
            "free_key_activity": free_key_activity,
            "scope": "external" if not include_ssr else "external+ssr",
        }
    finally:
        cur.close()
        conn.close()


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
        WITH endpoint_models AS (
            SELECT
                me.endpoint_provider AS provider_name,
                COUNT(DISTINCT me.model_id) AS endpoint_count
            FROM model_endpoints me
            JOIN models m ON me.model_id = m.id
            WHERE m.is_active = TRUE AND m.id NOT LIKE '%%:batch'
            GROUP BY me.endpoint_provider
        ),
        latest_ep AS (
            -- Current price of each distinct model as served by each endpoint
            -- provider (latest fetched within 3 days), so pricing reflects the
            -- models the provider actually serves - not just models it "owns".
            SELECT DISTINCT ON (endpoint_provider, model_id)
                endpoint_provider AS provider_name,
                model_id,
                blended_price_per_m AS bpm
            FROM model_endpoints
            WHERE fetched_at > NOW() - INTERVAL '3 days'
              AND blended_price_per_m > 0
            ORDER BY endpoint_provider, model_id, fetched_at DESC
        ),
        direct_models AS (
            SELECT
                p.name AS provider_name,
                COUNT(DISTINCT csv.model_id) AS priced_models,
                ROUND(AVG(csv.bpm)::numeric, 4) AS avg_price,
                ROUND(MIN(csv.bpm)::numeric, 4) AS min_price,
                ROUND(MAX(csv.bpm)::numeric, 4) AS max_price,
                COUNT(DISTINCT CASE WHEN m.aa_index_score IS NOT NULL THEN csv.model_id END) AS with_aa
            FROM providers p
            LEFT JOIN latest_ep csv ON csv.provider_name = p.name
            LEFT JOIN models m ON m.id = csv.model_id
            GROUP BY p.name
        )
        SELECT
            p.name,
            p.is_zdr,
            p.is_eu_sovereign,
            p.zdr_notes,
            p.eu_notes,
            COALESCE(dm.priced_models, 0) AS model_count,
            dm.avg_price,
            dm.min_price,
            dm.max_price,
            COALESCE(dm.with_aa, 0) AS with_aa,
            COALESCE(em.endpoint_count, 0) AS endpoint_count,
            COALESCE(p.show_in_list, FALSE) AS show_in_list
        FROM providers p
        LEFT JOIN direct_models dm ON p.name = dm.provider_name
        LEFT JOIN endpoint_models em ON p.name = em.provider_name
        WHERE COALESCE(dm.priced_models, 0) > 0
           OR COALESCE(em.endpoint_count, 0) > 0
           OR p.show_in_list = TRUE
        ORDER BY (COALESCE(dm.priced_models, 0) + COALESCE(em.endpoint_count, 0)) DESC
    """)

    providers = []
    for row in cur.fetchall():
        direct = row[5] or 0
        endpoints = row[10] or 0
        show_in_list = row[11] or False
        # A provider is "hybrid" if it has both direct models AND endpoint records
        # (hosting other providers' models). "self-host" if only direct models.
        # "aggregator" if only endpoint records (no own models in our DB).
        if direct > 0 and endpoints > 0:
            ptype = "hybrid"
        elif direct > 0:
            ptype = "self-host"
        elif endpoints > 0:
            ptype = "hybrid"
        elif show_in_list:
            # Tracked catalog provider with no priced endpoints yet (e.g. NVIDIA).
            # It hosts its own models (self-host) but we have no direct price data.
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
            "show_in_list": show_in_list,
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
    # Includes both own models and third-party models they aggregate.
    # Also includes models OWNED by this provider but hosted via other endpoint
    # providers (e.g. Mistralai owns models but they're hosted under "Mistral"
    # in model_endpoints). We UNION those so the provider page isn't empty.
    cur.execute("""
        WITH hosted AS (
            SELECT DISTINCT ON (me.model_id, quant_key)
                me.model_id, m.name, m.provider as model_owner, m.tier, m.context_length,
                m.aa_index_score, m.modality, m.is_reasoning,
                me.input_price_per_m, me.output_price_per_m, me.blended_price_per_m,
                lp.sit_score, lp.sit_adjusted_price, me.fetched_at, me.source, me.raw_data,
                COALESCE(
                    NULLIF(me.raw_data->>'openrelay_id', ''),
                    NULLIF(me.raw_data->>'quantization', ''),
                    'default'
                ) AS quant_key,
                COALESCE(NULLIF(me.raw_data->>'quantization',''), '') AS quantization
            FROM model_endpoints me
            JOIN models m ON me.model_id = m.id
            LEFT JOIN latest_prices lp ON me.model_id = lp.model_id
            WHERE me.endpoint_provider = %s
              AND m.is_active = TRUE
              AND me.blended_price_per_m > 0
              AND m.id NOT LIKE '%%:batch'
            ORDER BY me.model_id, quant_key, me.fetched_at DESC
        ),
        owned AS (
            SELECT DISTINCT ON (me.model_id, quant_key)
                me.model_id, m.name, m.provider as model_owner, m.tier, m.context_length,
                m.aa_index_score, m.modality, m.is_reasoning,
                me.input_price_per_m, me.output_price_per_m, me.blended_price_per_m,
                lp.sit_score, lp.sit_adjusted_price, me.fetched_at, me.source, me.raw_data,
                COALESCE(
                    NULLIF(me.raw_data->>'openrelay_id', ''),
                    NULLIF(me.raw_data->>'quantization', ''),
                    'default'
                ) AS quant_key,
                COALESCE(NULLIF(me.raw_data->>'quantization',''), '') AS quantization
            FROM models m
            JOIN model_endpoints me ON m.id = me.model_id
            LEFT JOIN latest_prices lp ON m.id = lp.model_id
            WHERE m.provider = %s
              AND m.is_active = TRUE
              AND me.blended_price_per_m > 0
              AND m.id NOT LIKE '%%:batch'
              AND me.endpoint_provider != %s
            ORDER BY me.model_id, quant_key, me.fetched_at DESC
        )
        SELECT DISTINCT ON (model_id, quant_key)
            model_id, name, model_owner, tier, context_length,
            aa_index_score, modality, is_reasoning,
            input_price_per_m, output_price_per_m, blended_price_per_m,
            sit_score, sit_adjusted_price, fetched_at, source, raw_data, quantization
        FROM (
            SELECT * FROM hosted
            UNION ALL
            SELECT * FROM owned
        ) combined
        ORDER BY model_id, quant_key, fetched_at DESC
    """, (provider_name, provider_name, provider_name))

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
            "hosting_type": raw.get("hosting_type", ""),
            "quantization": (row[16] or raw.get("quantization", "")) or "",
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

    # Determine provider type using same logic as the providers list endpoint:
    # hybrid if the provider has endpoint records (hosts models, including from other owners)
    # self-host if only direct models exist (no endpoints for other providers)
    # aggregator if only endpoint records exist from OpenRouter (no direct API)
    owner_set = set(m["model_owner"] for m in models if m["model_owner"] and m["model_owner"] != provider_name)
    is_aggregator = len(owner_set) > 0
    # If the provider hosts models from multiple owners, it's at least hybrid
    provider_type = "hybrid" if is_aggregator else ("self-host" if direct_count > 0 else "aggregator")

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

    # Quality data: recent latency probes for this provider
    cur.execute("""
        SELECT
            COUNT(*) AS total_probes,
            COUNT(*) FILTER (WHERE success = TRUE) AS successful,
            ROUND(AVG(ttft_ms) FILTER (WHERE success = TRUE AND ttft_ms IS NOT NULL)::numeric, 0) AS avg_ttft_ms,
            ROUND(MIN(ttft_ms) FILTER (WHERE success = TRUE AND ttft_ms IS NOT NULL)::numeric, 0) AS min_ttft_ms,
            ROUND(MAX(ttft_ms) FILTER (WHERE success = TRUE AND ttft_ms IS NOT NULL)::numeric, 0) AS max_ttft_ms,
            ROUND(AVG(throughput_tps) FILTER (WHERE success = TRUE AND throughput_tps IS NOT NULL)::numeric, 1) AS avg_tps,
            COUNT(*) FILTER (WHERE success = TRUE) * 100.0 / NULLIF(COUNT(*), 0) AS success_rate,
            MAX(probed_at) AS last_probe
        FROM provider_latency_snapshots
        WHERE provider = %s AND probed_at >= NOW() - INTERVAL '7 days'
    """, (provider_name,))
    qrow = cur.fetchone()
    quality_data = {
        "total_probes": qrow[0] or 0,
        "successful_probes": qrow[1] or 0,
        "avg_ttft_ms": float(qrow[2]) if qrow[2] else None,
        "min_ttft_ms": float(qrow[3]) if qrow[3] else None,
        "max_ttft_ms": float(qrow[4]) if qrow[4] else None,
        "avg_throughput_tps": float(qrow[5]) if qrow[5] else None,
        "success_rate": round(float(qrow[6]), 1) if qrow[6] else None,
        "last_probe": qrow[7].isoformat() if qrow[7] else None,
        "probe_model": None,  # filled below
    }

    # Get the probe model name and recent probes for a sparkline
    cur.execute("""
        SELECT probe_model, ttft_ms, throughput_tps, success, error_type, probed_at
        FROM provider_latency_snapshots
        WHERE provider = %s AND probed_at >= NOW() - INTERVAL '24 hours'
        ORDER BY probed_at ASC
        LIMIT 24
    """, (provider_name,))
    recent_probes = []
    for pr in cur.fetchall():
        recent_probes.append({
            "ttft_ms": float(pr[1]) if pr[1] else None,
            "throughput_tps": float(pr[2]) if pr[2] else None,
            "success": pr[3],
            "error_type": pr[4],
            "probed_at": pr[5].isoformat() if pr[5] else None,
        })
        if quality_data["probe_model"] is None and pr[0]:
            quality_data["probe_model"] = pr[0]
    quality_data["recent_probes"] = recent_probes

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
            "quality": quality_data,
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
    """Returns historical price data and trends for a single model.

    This is InferenceIndexer's differentiator: aggregators like OpenRouter
    expose only current price, while this endpoint returns the price over
    time (input, output, and blended $/M), allowing trend analysis and
    historical comparison. Use `days` to control the window (default 30).
    """
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

@app.post("/v1/auth/anonymous")
async def anonymous_signup():
    """Get an API key instantly with NO email/account/password.

    Designed for AI agents: one request, no signup, no verification.
    Returns a key valid on the standard free tier (10,000 requests/day,
    30 days history). Key is tracked only by itself (synthetic email
    marker `anon_*.ii.local`); no contact identity is captured.
    """
    api_key = generate_api_key()
    # Distinct per-key bucket: synthetic unique email so each anonymous key
    # gets its own rate-limit bucket (get_api_user keys off email).
    anon_email = f"anon_{secrets.token_hex(8)}@ii.local"
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO api_users (email, api_key, plan) VALUES (%s, %s, 'free') RETURNING api_key",
            (anon_email, api_key),
        )
        new_key = cur.fetchone()[0]
        conn.commit()
    finally:
        cur.close()
        conn.close()
    return {
        "api_key": new_key,
        "plan": "free",
        "anonymous": True,
        "message": "Anonymous API key created. No email required.",
    }

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
# ADMIN: FEED STATUS & PRICING COMPARISON
# ============================================

def _require_admin(x_ssr_secret: Optional[str]):
    """Gate admin endpoints behind the SSR secret. Admin-only internal tooling."""
    if x_ssr_secret != SSR_SECRET:
        return JSONResponse(
            status_code=401,
            content={"error": "Unauthorized"},
            headers={"Cache-Control": "no-store"},
        )
    return None


@app.get("/v1/admin/feeds")
async def admin_feeds(x_ssr_secret: Optional[str] = Header(None)):
    """Feed status for all data sources: is data flowing, complete, fresh.

    For each source in model_endpoints reports:
      - model_count / priced_count        (completeness)
      - last_fetch / age_minutes          (flow: is data up to date?)
      - endpoint_count                    (volume of endpoint rows)
      - expected_cadence                  (daily vs hourly, so staleness is judged right)
    Returns per-source status plus a derived overall health summary.
    """
    deny = _require_admin(x_ssr_secret)
    if deny:
        return deny
    conn = get_db()
    cur = conn.cursor()
    now = datetime.now(timezone.utc)
    try:
        cur.execute("""
            SELECT me.source,
                   COUNT(DISTINCT me.model_id) AS model_count,
                   COUNT(DISTINCT CASE WHEN me.blended_price_per_m > 0 THEN me.model_id END) AS priced_count,
                   COUNT(*) AS endpoint_count,
                   MAX(me.fetched_at) AS last_fetch
            FROM model_endpoints me
            JOIN models m ON m.id = me.model_id AND m.is_active = TRUE
            WHERE me.fetched_at > NOW() - INTERVAL '7 days'
            GROUP BY me.source
            ORDER BY me.source
        """)
        sources = []
        # Hourly sources must update every ~75 min; daily sources every ~26h.
        hourly = {"venice_direct", "deepinfra_direct", "novita_direct",
                  "sambanova_direct", "jina_direct", "tensorx_direct"}
        for row in cur.fetchall():
            source, model_count, priced_count, endpoint_count, last_fetch = row
            age_min = (now - last_fetch).total_seconds() / 60.0 if last_fetch else None
            cadence = "hourly" if source in hourly else "daily"
            threshold_min = 85 if cadence == "hourly" else 60 * 28
            stale = age_min is not None and age_min > threshold_min
            status = "ok"
            if stale:
                status = "stale"
            elif priced_count is None or priced_count == 0:
                status = "no_prices"
            elif age_min is None:
                status = "never_fetched"
            sources.append({
                "source": source,
                "cadence": cadence,
                "model_count": model_count,
                "priced_count": priced_count,
                "endpoint_count": endpoint_count,
                "last_fetch": last_fetch.isoformat() if last_fetch else None,
                "age_minutes": round(age_min, 1) if age_min is not None else None,
                "status": status,
                "expected_cadence": cadence,
                "stale": stale,
            })

        # Overall health: count sources that are stale / broken
        problems = [s for s in sources if s["status"] != "ok"]
        total_models = sum(s["model_count"] for s in sources)
        health = "healthy"
        if problems:
            health = "degraded"
        if len(problems) >= len(sources) // 2 + 1:
            health = "critical"
        return JSONResponse(content={
            "generated_at": now.isoformat(),
            "health": health,
            "source_count": len(sources),
            "total_models_indexed": total_models,
            "sources": sources,
            "problem_count": len(problems),
            "problems": problems,
        }, headers={"Cache-Control": "no-store"})
    finally:
        cur.close()
        conn.close()


@app.get("/v1/admin/price-compare")
async def admin_price_compare(
    x_ssr_secret: Optional[str] = Header(None),
    sort: str = Query("abs_diff", description="Sort key: abs_diff, direct, openrouter, model, provider, pct_diff"),
    order: str = Query("desc", description="asc or desc"),
    min_diff: float = Query(0.0, description="Minimum absolute % difference to include"),
    provider: Optional[str] = Query(None, description="Filter by endpoint provider"),
):
    """Compare OpenRouter-reported price vs our direct price for the same
    provider+model. Highlights discrepancies in the pricing we pull vs what
    OpenRouter reports for the same host.
    """
    deny = _require_admin(x_ssr_secret)
    if deny:
        return deny
    conn = get_db()
    cur = conn.cursor()
    try:
        # Sort column is whitelisted; provider filter is parameterized.
        sort_map = {
            "abs_diff": "ABS(pct_diff)",
            "direct": "direct_blend",
            "openrouter": "orange_blend",
            "model": "model_id",
            "provider": "endpoint_provider",
            "pct_diff": "pct_diff",
        }
        sort_col = sort_map.get(sort, "ABS(pct_diff)")
        direction = "ASC" if order == "asc" else "DESC"

        params = []
        p_where = ""
        if provider:
            params.append(provider)
            p_where = " AND d.endpoint_provider = %s"
        params.append(min_diff)

        sql = f"""
            WITH latest_ep AS (
              SELECT DISTINCT ON (is_openrouter, endpoint_provider, model_id)
                model_id, endpoint_provider, (source='openrouter') AS is_openrouter,
                blended_price_per_m AS bpm, input_price_per_m AS inp, output_price_per_m AS outp
              FROM model_endpoints
              WHERE fetched_at > NOW() - INTERVAL '3 days'
              ORDER BY (source='openrouter'), endpoint_provider, model_id, fetched_at DESC
            )
            SELECT model_id, endpoint_provider, direct_blend, orange_blend, pct_diff,
                   direct_in, direct_out, or_in, or_out
            FROM (
              SELECT d.model_id, d.endpoint_provider,
                     d.bpm AS direct_blend, o.bpm AS orange_blend,
                     ROUND((100.0*(d.bpm - o.bpm)/NULLIF(o.bpm,0))::numeric, 1) AS pct_diff,
                     d.inp AS direct_in, d.outp AS direct_out, o.inp AS or_in, o.outp AS or_out
              FROM latest_ep d
              JOIN latest_ep o
                ON o.model_id = d.model_id AND o.endpoint_provider = d.endpoint_provider
               AND o.is_openrouter AND NOT d.is_openrouter
              WHERE NOT d.is_openrouter AND d.bpm > 0 AND o.bpm > 0
                {p_where}
            ) t
            WHERE ABS(pct_diff) >= %s
            ORDER BY {sort_col} {direction}
        """
        cur.execute(sql, params)
        rows = cur.fetchall()
        return JSONResponse(content={
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "count": len(rows),
            "sort": sort,
            "order": order,
            "pairs": [
                {
                    "model_id": r[0],
                    "endpoint_provider": r[1],
                    "direct_blended": float(r[2]),
                    "openrouter_blended": float(r[3]),
                    "pct_diff": float(r[4]),
                    "direct_input": float(r[5]),
                    "direct_output": float(r[6]),
                    "openrouter_input": float(r[7]),
                    "openrouter_output": float(r[8]),
                }
                for r in rows
            ],
        }, headers={"Cache-Control": "no-store"})
    finally:
        cur.close()
        conn.close()


# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
