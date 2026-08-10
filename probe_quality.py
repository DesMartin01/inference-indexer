#!/usr/bin/env python3
"""
InferenceIndexer - Provider Quality Probe Runner (Phase 1)

Measures per-provider latency + reliability by sending a tiny streaming chat
request to each provider's OpenAI-compatible /chat/completions endpoint.

For each provider (Tier A = providers we can reach without extra setup):
  - TTFT (time to first token, ms)
  - Throughput (tokens/sec from the stream)
  - Success / failure
  - HTTP status + error type (timeout / rate_limit / 5xx / connection)

Writes one row per probe into the `provider_latency_snapshots` table.

Design decisions (Des, Aug 9 2026):
  - Probe model: cheapest widely-hosted Llama/gemma-class per provider
    (cost-minimal, apples-to-apples across providers).
  - Cadence: hourly (cron). This script probes ALL registered providers once.
  - Coverage: Tier A first (reachable), expanded later.
  - Storage: separate table, never touches price_snapshots / models.
  - 429-aware: on rate limit, record it and don't hammer.

Run:  python3 probe_quality.py            (probe all Tier A)
      python3 probe_quality.py --dry-run  (print plan, no network)
      python3 probe_quality.py --once     (alias for default)
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

import requests

# ---------------------------------------------------------------------------
# DB connection (same as pipeline.get_db_connection)
# ---------------------------------------------------------------------------
def _read_env(url_var="SUPABASE_DB_URL"):
    # Check ~/.hermes/.env FIRST — Hermes masks secrets in os.environ
    # (e.g. SUPABASE_DB_URL gets *** in the password), but the .env
    # file on disk has the real value.  Same pattern as pipeline.py
    # and api.py for the TensorX API key.
    env_path = os.path.expanduser("~/.hermes/.env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith(f"{url_var}="):
                    return line.split("=", 1)[1]
    # Fall back to environment variable
    val = os.environ.get(url_var)
    if val and "***" not in val:
        return val
    return None


def get_db_connection():
    import psycopg2
    db_url = _read_env()
    if not db_url:
        print("ERROR: SUPABASE_DB_URL not found")
        sys.exit(1)
    return psycopg2.connect(db_url, connect_timeout=15)


# ---------------------------------------------------------------------------
# Provider API key resolution (mirrors pipeline.get_provider_api_key)
# ---------------------------------------------------------------------------
def get_provider_api_key(provider_env_var):
    """Return the API key for a provider env var name, or None if absent."""
    # Check ~/.hermes/.env FIRST — Hermes masks secrets in os.environ.
    env_path = os.path.expanduser("~/.hermes/.env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith(f"{provider_env_var}="):
                    val = line.split("=", 1)[1]
                    if val and "***" not in val:
                        return val
    # Fall back to environment variable
    val = os.environ.get(provider_env_var)
    if val and "***" not in val:
        return val
    # Jentic One
    try:
        r = subprocess.run(
            ["jenticctl", "credential", "get", "--name", provider_env_var],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


# ---------------------------------------------------------------------------
# Provider registry (Tier A)
#
# Each entry: canonical provider name, chat base URL (OpenAI-compatible),
# auth env var (or None for no-auth), and the probe model that provider serves.
# Probe models are chosen as cheap, widely-hosted Llama/gemma-class models.
# ---------------------------------------------------------------------------
PROVIDERS = [
    # name, chat_url, key_env, probe_model
    {
        "name": "TensorX",
        "chat_url": "https://api.tensorx.ai/v1/chat/completions",
        "key_env": "TENSORX_API_KEY",
        "probe_model": "z-ai/glm-5.2",
    },
    {
        "name": "Mistralai",
        "chat_url": "https://api.mistral.ai/v1/chat/completions",
        "key_env": "MISTRAL_API_KEY",
        "probe_model": "mistral-large-latest",
    },
    {
        "name": "DeepInfra",
        "chat_url": "https://api.deepinfra.com/v1/openai/chat/completions",
        "key_env": "DEEPINFRA_API_KEY",
        "probe_model": "meta-llama/Llama-3.1-8B-Instruct",
    },
    {
        "name": "Novita",
        "chat_url": "https://api.novita.ai/v3/openai/chat/completions",
        "key_env": "NOVITA_API_KEY",
        "probe_model": "meta-llama/llama-3.1-8b-instruct",
    },
    {
        "name": "Together",
        "chat_url": "https://api.together.xyz/v1/chat/completions",
        "key_env": "TOGETHER_API_KEY",
        "probe_model": "meta-llama/Llama-3.1-8B-Instruct-Turbo",
    },
    {
        "name": "Groq",
        "chat_url": "https://api.groq.com/openai/v1/chat/completions",
        "key_env": "GROQ_API_KEY",
        "probe_model": "llama-3.1-8b-instant",
    },
    {
        "name": "Fireworks",
        "chat_url": "https://api.fireworks.ai/inference/v1/chat/completions",
        "key_env": "FIREWORKS_API_KEY",
        "probe_model": "accounts/fireworks/models/gpt-oss-20b",
    },
    {
        "name": "SambaNova",
        "chat_url": "https://api.sambanova.ai/v1/chat/completions",
        "key_env": "SAMBANOVA_API_KEY",
        "probe_model": "meta-llama/Llama-3.1-8B-Instruct",
    },
    {
        "name": "Inference.net",
        "chat_url": "https://api.inference.net/v1/chat/completions",
        "key_env": "INFERENCE_NET_API_KEY",
        "probe_model": "meta-llama/Llama-3.1-8B-Instruct",
    },
]

PROMPT = {"role": "user", "content": "Reply with OK."}
MAX_TOKENS = 8
CONNECT_TIMEOUT = 10    # seconds to establish connection
READ_TIMEOUT = 25       # seconds to first+last byte
MIN_STREAM_TOKENS = 1   # require at least this many tokens to count as success


def probe_provider(p):
    """Probe a single provider. Returns a snapshot dict (or None to skip)."""
    key_env = p["key_env"]
    api_key = get_provider_api_key(key_env) if key_env else None
    now = datetime.now(timezone.utc)

    snapshot = {
        "provider": p["name"],
        "probe_model": p["probe_model"],
        "ttft_ms": None,
        "throughput_tps": None,
        "http_status": None,
        "success": False,
        "error_type": None,
        "probed_at": now,
    }

    # Track total number of output tokens received from the stream
    total_chunks = 0
    total_content_len = 0
    first_token_at = None
    stream_started_at = time.monotonic()

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    body = {
        "model": p["probe_model"],
        "messages": [PROMPT],
        "max_tokens": MAX_TOKENS,
        "stream": True,
        "stream_options": {"include_usage": True},
    }

    request_started_at = time.monotonic()
    try:
        r = requests.post(
            p["chat_url"],
            headers=headers,
            json=body,
            stream=True,
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
        )
        snapshot["http_status"] = r.status_code

        if r.status_code == 429:
            snapshot["error_type"] = "rate_limit"
            return snapshot
        if r.status_code >= 500:
            snapshot["error_type"] = "5xx"
            return snapshot
        if r.status_code != 200:
            snapshot["error_type"] = f"http_{r.status_code}"
            return snapshot

        # Stream the SSE response line by line
        for raw_line in r.iter_lines(decode_unicode=True):
            if not raw_line:
                continue
            if not raw_line.startswith("data:"):
                continue
            data = raw_line[len("data:"):].strip()
            if data == "[DONE]":
                break
            try:
                chunk = json.loads(data)
            except json.JSONDecodeError:
                continue
            choices = chunk.get("choices") or []
            if choices:
                delta = choices[0].get("delta") or {}
                # Capture both visible content and reasoning_content (reasoning
                # models like GLM emit CoT in `reasoning_content`, not `content`).
                content = delta.get("content") or ""
                reasoning = delta.get("reasoning_content") or ""
                if content or reasoning:
                    total_content_len += len(content) + len(reasoning)
                    if first_token_at is None:
                        first_token_at = time.monotonic()

        stream_ended_at = time.monotonic()

        # Determine success: got at least one content token
        if total_content_len > 0:
            snapshot["success"] = True
            # TTFT = time from request start to first token
            if first_token_at is not None:
                snapshot["ttft_ms"] = round((first_token_at - request_started_at) * 1000, 1)
            # Throughput = content length / stream duration.
            # Approximate tokens ~ chars; good enough for a relative signal.
            stream_seconds = stream_ended_at - stream_started_at
            if stream_seconds > 0:
                snapshot["throughput_tps"] = round(total_content_len / stream_seconds, 1)
        else:
            snapshot["error_type"] = "no_content"
    except requests.exceptions.Timeout:
        snapshot["error_type"] = "timeout"
    except requests.exceptions.ConnectionError:
        snapshot["error_type"] = "connection"
    except requests.exceptions.RequestException:
        snapshot["error_type"] = "request_error"

    return snapshot


def insert_snapshots(conn, snapshots):
    cur = conn.cursor()
    for s in snapshots:
        cur.execute(
            """
            INSERT INTO provider_latency_snapshots
              (provider, probe_model, ttft_ms, throughput_tps, http_status,
               success, error_type, probed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (s["provider"], s["probe_model"], s["ttft_ms"], s["throughput_tps"],
             s["http_status"], s["success"], s["error_type"], s["probed_at"]),
        )
    conn.commit()
    cur.close()


def main():
    dry_run = "--dry-run" in sys.argv
    print(f"[{datetime.now(timezone.utc).isoformat()}] Probe runner start (dry_run={dry_run})")

    snapshots = []
    for p in PROVIDERS:
        key_env = p["key_env"]
        has_key = bool(get_provider_api_key(key_env)) if key_env else True
        status = "key-present" if has_key else "NO-KEY (skip)"
        print(f"  - {p['name']}: model={p['probe_model']} | {status}")
        if not has_key:
            continue
        if dry_run:
            continue
        s = probe_provider(p)
        if s is None:
            continue
        status_msg = "OK" if s["success"] else f"FAIL({s['error_type']})"
        ttft = f"{s['ttft_ms']}ms" if s["ttft_ms"] is not None else "-"
        tps = f"{s['throughput_tps']} tok/s" if s["throughput_tps"] is not None else "-"
        print(f"    -> {status_msg} | TTFT={ttft} | TPS={tps} | http={s['http_status']}")
        snapshots.append(s)

    if dry_run:
        print("DRY RUN: no rows inserted. Providers reachable:", len(snapshots))
        return

    if not snapshots:
        print("No probes succeeded / no keys; nothing inserted.")
        return

    conn = get_db_connection()
    try:
        insert_snapshots(conn, snapshots)
        print(f"Inserted {len(snapshots)} snapshot rows.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()