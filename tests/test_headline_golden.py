#!/usr/bin/env python3
"""Golden-file test for the deterministic, tier-aware read path (N7/N14/K1).

Run:  .venv/bin/python tests/test_headline_golden.py
  (or with a --live flag) .venv/bin/python tests/test_headline_golden.py --live

No pytest dependency. Two layers:

1. Unit: the headline selection logic (1P-first, Standard-only median,
   deterministic tiebreak) evaluated against a golden table of
   (endpoint rows -> expected headline). Fails loudly on any mismatch.

2. Live (--live): queries the real DB and asserts today's headline prices
   for a fixed list of flagship models equal their official Standard rates.
   This is the test that would have caught the 09:00Z regression.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline import (  # noqa: E402
    FIRST_PARTY_HOSTS, compute_median, apply_median_pricing,
)

NON_STANDARD_TIERS = ("flex", "priority", "ultrafast")


def _std(rows):
    """Standard rows only, as the read path sees them after the SQL filter."""
    return [r for r in rows if (r.get("service_tier") or "") not in NON_STANDARD_TIERS]


def select_headline(model_id, endpoint_rows):
    """Mirror of the read-path headline rule, in Python.

    endpoint_rows: [{"endpoint_provider": str, "input_price_per_m": float,
                     "output_price_per_m": float,
                     "blended_price_per_m": float,
                     "service_tier": str|None}, ...]
    Rows must be pre-sorted the way the SQL delivers them:
    (endpoint_provider, fetched_at DESC, blended ASC) with DISTINCT ON taken.
    """
    std = _std(endpoint_rows)
    use = std or endpoint_rows  # never zero out: fallback to all rows
    fp = FIRST_PARTY_HOSTS.get(model_id.split("/")[0].lower())
    fp_rows = [r for r in use if r["endpoint_provider"] == fp and r["blended_price_per_m"] > 0] if fp else []
    if fp_rows:
        return fp_rows[0]["input_price_per_m"], fp_rows[0]["output_price_per_m"], fp_rows[0]["blended_price_per_m"]
    blended = [r["blended_price_per_m"] for r in use if r["blended_price_per_m"] > 0]
    ins = [r["input_price_per_m"] for r in use if r["input_price_per_m"] > 0]
    outs = [r["output_price_per_m"] for r in use if r["output_price_per_m"] > 0]
    if not blended:
        return None
    return compute_median(ins), compute_median(outs), compute_median(blended)


# ---------------------------------------------------------------------------
# Golden table: (description, model_id, rows, expected (in, out, blended))
# Each row dict: provider, in, out, blended, service_tier (None = standard)
# ---------------------------------------------------------------------------
GOLDEN = [
    (
        "1P Standard wins over Batch/Fast variants of the same 1P provider",
        "openai/gpt-5.4",
        [
            {"endpoint_provider": "OpenAI", "input_price_per_m": 1.25, "output_price_per_m": 7.5,  "blended_price_per_m": 5.0, "service_tier": None},
            {"endpoint_provider": "OpenAI", "input_price_per_m": 2.5,  "output_price_per_m": 15.0, "blended_price_per_m": 10.0, "service_tier": None},
            {"endpoint_provider": "OpenAI", "input_price_per_m": 5.0,  "output_price_per_m": 30.0, "blended_price_per_m": 20.0, "service_tier": "flex"},
            {"endpoint_provider": "OpenAI", "input_price_per_m": 2.5,  "output_price_per_m": 15.0, "blended_price_per_m": 10.0, "service_tier": "priority"},
            {"endpoint_provider": "Azure",  "input_price_per_m": 2.75, "output_price_per_m": 16.5, "blended_price_per_m": 11.0, "service_tier": None},
        ],
        (1.25, 7.5, 5.0),  # first standard OpenAI row (DISTINCT ON, blended ASC)
    ),
    (
        "No 1P row: median over Standard rows only (Batch excluded)",
        "some-vendor/model-x",
        [
            {"endpoint_provider": "HostA", "input_price_per_m": 1.0, "output_price_per_m": 2.0, "blended_price_per_m": 1.6, "service_tier": None},
            {"endpoint_provider": "HostB", "input_price_per_m": 2.0, "output_price_per_m": 4.0, "blended_price_per_m": 3.2, "service_tier": None},
            {"endpoint_provider": "HostC", "input_price_per_m": 0.5, "output_price_per_m": 1.0, "blended_price_per_m": 0.8, "service_tier": "flex"},
            {"endpoint_provider": "HostD", "input_price_per_m": 0.4, "output_price_per_m": 0.8, "blended_price_per_m": 0.64, "service_tier": "priority"},
        ],
        (1.5, 3.0, 2.4),
    ),
    (
        "All rows non-standard: falls back to median over what exists (never 0)",
        "some-vendor/model-y",
        [
            {"endpoint_provider": "HostA", "input_price_per_m": 1.0, "output_price_per_m": 2.0, "blended_price_per_m": 1.6, "service_tier": "flex"},
            {"endpoint_provider": "HostB", "input_price_per_m": 2.0, "output_price_per_m": 4.0, "blended_price_per_m": 3.2, "service_tier": "priority"},
        ],
        (1.5, 3.0, 2.4),  # median of two: (1.6, 3.2) -> 2.4
    ),
    (
        "Global standard row beats +10% regional twin on the same provider",
        "anthropic/claude-opus-5",
        [
            {"endpoint_provider": "Anthropic",       "input_price_per_m": 5.0,  "output_price_per_m": 25.0, "blended_price_per_m": 17.0, "service_tier": None},
            {"endpoint_provider": "Anthropic",       "input_price_per_m": 10.0, "output_price_per_m": 50.0, "blended_price_per_m": 34.0, "service_tier": "priority"},
            {"endpoint_provider": "Azure",           "input_price_per_m": 5.0,  "output_price_per_m": 25.0, "blended_price_per_m": 17.0, "service_tier": None},
            {"endpoint_provider": "Azure",           "input_price_per_m": 5.5,  "output_price_per_m": 27.5, "blended_price_per_m": 18.7, "service_tier": None},
            {"endpoint_provider": "Amazon Bedrock",  "input_price_per_m": 5.5,  "output_price_per_m": 27.5, "blended_price_per_m": 18.7, "service_tier": None},
        ],
        (5.0, 25.0, 17.0),
    ),
    (
        "Unknown 1P prefix maps to nothing (no accidental first-party hit)",
        "unknownco/model-z",
        [
            {"endpoint_provider": "Unknownco Direct", "input_price_per_m": 9.0, "output_price_per_m": 9.0, "blended_price_per_m": 9.0, "service_tier": None},
            {"endpoint_provider": "OpenAI",           "input_price_per_m": 1.0, "output_price_per_m": 1.0, "blended_price_per_m": 1.0, "service_tier": None},
        ],
        (5.0, 5.0, 5.0),  # median of two hosts: (9.0, 1.0) -> 5.0
    ),
]


def run_unit():
    failures = []
    for desc, model_id, rows, expected in GOLDEN:
        got = select_headline(model_id, rows)
        if got != expected:
            failures.append(f"  FAIL: {desc}\n    expected {expected}\n    got      {got}")
        else:
            print(f"  ok: {desc}")
    return failures


# Official Standard rates re-checked against provider pricing pages 2026-10-21
# (Grokbot's independent check, same values). If a provider changes a real
# price, update BOTH sides and note the date.
LIVE_GOLDEN = {
    "openai/gpt-5.4":                 (2.5, 15.0),
    "openai/gpt-5.5":                 (5.0, 30.0),
    "openai/gpt-5.4-mini":            (0.75, 4.50),
    "openai/gpt-5.5-pro":             (30.0, 180.0),
    "openai/gpt-5.6-sol":             (4.0, 20.0),
    "openai/gpt-5.6-terra":           (2.0, 12.0),
    "openai/gpt-5.6-luna":            (0.2, 1.2),
    "anthropic/claude-opus-5":        (5.0, 25.0),
    "anthropic/claude-opus-4.8":      (5.0, 25.0),
    "anthropic/claude-sonnet-5":      (2.0, 10.0),
    "anthropic/claude-haiku-4.5":     (1.0, 5.0),
    "google/gemini-2.5-pro":          (1.25, 10.0),
    "google/gemini-2.5-flash":        (0.30, 2.50),
    "google/gemini-2.5-flash-lite":   (0.10, 0.40),
    "google/gemini-3.1-flash-lite":   (0.25, 1.50),
}


def run_live():
    import psycopg2
    url = None
    for line in open(os.path.expanduser("~/.hermes/.env")):
        if line.startswith("SUPABASE_DB_URL"):
            url = line.split("=", 1)[1].strip().strip('"')
    conn = psycopg2.connect(url, connect_timeout=15)
    cur = conn.cursor()
    failures = []
    for model_id, (exp_in, exp_out) in LIVE_GOLDEN.items():
        cur.execute("""
            SELECT DISTINCT ON (endpoint_provider)
                endpoint_provider, input_price_per_m, output_price_per_m, blended_price_per_m
            FROM model_endpoints
            WHERE model_id = %s
              AND fetched_at >= NOW() - INTERVAL '24 hours'
              AND blended_price_per_m > 0
              AND COALESCE(raw_data->>'service_tier','') NOT IN ('flex','priority','ultrafast')
            ORDER BY endpoint_provider, fetched_at DESC, blended_price_per_m ASC
        """, (model_id,))
        rows = cur.fetchall()
        endpoints = [
            {"endpoint_provider": r[0], "input_price_per_m": r[1],
             "output_price_per_m": r[2], "blended_price_per_m": r[3], "service_tier": None}
            for r in rows
        ]
        got = select_headline(model_id, endpoints)
        if got is None:
            failures.append(f"  FAIL: {model_id}: no standard endpoint rows in last 24h")
            continue
        if abs(got[0] - exp_in) > 0.005 or abs(got[1] - exp_out) > 0.005:
            failures.append(f"  FAIL: {model_id}: expected {exp_in}/{exp_out}, got {got[0]}/{got[1]}")
        else:
            print(f"  ok: {model_id} = {got[0]}/{got[1]}")
    conn.close()
    return failures


if __name__ == "__main__":
    print("Unit golden tests:")
    fails = run_unit()
    if "--live" in sys.argv:
        print("\nLive golden tests (real DB, last 24h):")
        fails += run_live()
    if fails:
        print("\n".join(fails))
        print(f"\n{len(fails)} FAILURE(S)")
        sys.exit(1)
    print("\nAll golden tests passed.")
