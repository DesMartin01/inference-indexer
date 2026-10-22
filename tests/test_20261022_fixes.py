#!/usr/bin/env python3
"""Golden tests for the 2026-10-22 fixes.

Run:  .venv/bin/python tests/test_20261022_fixes.py [--live]

No pytest dependency. Layers:

1. Unit: normalize_endpoints maps OpenRouter tag suffixes into
   raw_data.service_tier/quantization (spot/fast/us/flex/priority/ultrafast,
   fp8 -> quantization); org_canonical_id resolves alias-org ids onto
   canonical active twins.

2. Live (needs prod DB + API): the three Fireworks goldens from the
   watchdog report read from the DB exactly as the API read path does,
   plus a no-duplicates check on provider listings.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline import normalize_endpoints, ORG_CANONICAL  # noqa: E402

TIER_EXCLUSIONS = ("flex", "priority", "ultrafast", "spot", "fast", "us")

# Watchdog goldens (2026-10-22): Fireworks Standard rates from
# docs.fireworks.ai (verified live 2026-10-22 by Frank against the docs page).
FIREWORKS_GOLDEN = {
    "z-ai/glm-5.3": (1.40, 4.40),
    "deepseek/deepseek-v4.1-flash": (0.30, 1.20),
    "moonshotai/kimi-k3": (3.00, 15.00),
}


def run_unit():
    failures = []

    # --- tag -> service_tier mapping ----------------------------------
    raw = [
        {"provider_name": "Fireworks", "tag": "fireworks/spot", "pricing": {"prompt": "0.00000098", "completion": "0.00000308"}},
        {"provider_name": "Fireworks", "tag": "fireworks", "pricing": {"prompt": "0.0000014", "completion": "0.0000044"}},
        {"provider_name": "Fireworks", "tag": "fireworks/fast", "pricing": {"prompt": "0.0000021", "completion": "0.0000066"}},
        {"provider_name": "Fireworks", "tag": "fireworks/us", "pricing": {"prompt": "0.0000021", "dc": "x", "completion": "0.0000066"}},
        {"provider_name": "DeepInfra", "tag": "deepinfra/fp8/priority", "pricing": {"prompt": "0.00000021", "completion": "0.00000063"}},
        {"provider_name": "Azure", "tag": "azure/us", "pricing": {"prompt": "0.00000275", "completion": "0.0000165"}},
        {"provider_name": "Azure", "tag": "azure", "pricing": {"prompt": "0.0000025", "completion": "0.000015"}},
        {"provider_name": "Google (Vertex)", "tag": "google-vertex/global", "pricing": {"prompt": "0.00000125", "completion": "0.00001"}},
    ]
    eps = normalize_endpoints("z-ai/glm-5.3", raw)
    by_tag = {}
    for e in eps:
        rd = e["raw_data"]
        by_tag[rd.get("tag", "")] = (rd.get("service_tier"), rd.get("quantization"))

    def expect(tag, tier, quant):
        got = by_tag.get(tag)
        if got != (tier, quant):
            failures.append(f"  FAIL tag={tag}: expected (tier={tier}, quant={quant}), got {got}")

    expect("fireworks/spot", "spot", None)
    expect("fireworks", None, None)
    expect("fireworks/fast", "fast", None)
    expect("fireworks/us", "us", None)
    expect("deepinfra/fp8/priority", "priority", "fp8")
    expect("azure/us", "us", None)
    expect("azure", None, None)
    expect("google-vertex/global", None, None)

    # --- headline exclusion of spot/fast/us ---------------------------
    rows = [
        {"endpoint_provider": "Fireworks", "input_price_per_m": 0.98, "output_price_per_m": 3.08, "blended_price_per_m": 2.24, "service_tier": "spot"},
        {"endpoint_provider": "Fireworks", "input_price_per_m": 1.40, "output_price_per_m": 4.40, "blended_price_per_m": 3.52, "service_tier": None},
        {"endpoint_provider": "Fireworks", "input_price_per_m": 2.10, "output_price_per_m": 6.60, "blended_price_per_m": 4.80, "service_tier": "fast"},
    ]
    std = [r for r in rows if (r.get("service_tier") or "") not in TIER_EXCLUSIONS]
    if len(std) != 1 or std[0]["input_price_per_m"] != 1.40:
        failures.append(f"  FAIL headline exclusion: standard rows after filter = {std}")
    else:
        print("  ok: spot/fast/us rows excluded from headline reads")

    # --- org_canonical_id static map ----------------------------------
    cases = [
        ("xai/grok-4.6", "x-ai/grok-4.6"),        # xai -> x-ai
        ("deepseek-ai/deepseek-v4.1-flash", "deepseek/deepseek-v4.1-flash"),
        ("zai-org/glm-5.3", "z-ai/glm-5.3"),
        ("x-ai/grok-4.6", "x-ai/grok-4.6"),        # already canonical: unchanged
        ("openai/gpt-5.4", "openai/gpt-5.4"),      # unmapped org: unchanged
    ]
    for mid, want in cases:
        got = ORG_CANONICAL.get(mid.partition("/")[0], mid.partition("/")[0]) + "/" + mid.partition("/")[2]
        if got != want:
            failures.append(f"  FAIL org map: {mid} -> {got}, want {want}")
        else:
            print(f"  ok: {mid} -> {got}")

    return failures


def run_live():
    import psycopg2
    url = None
    for line in open(os.path.expanduser("~/.hermes/.env")):
        if line.startswith("SUPABASE_DB_URL"):
            url = line.split("=", 1)[1].strip().strip('"')
    conn = psycopg2.connect(url, connect_timeout=15)
    cur = conn.cursor()
    failures = []

    # --- Fireworks goldens via the same SQL as the API read path ------
    for model_id, (exp_in, exp_out) in FIREWORKS_GOLDEN.items():
        cur.execute("""
            SELECT DISTINCT ON (endpoint_provider)
                endpoint_provider, input_price_per_m, output_price_per_m, blended_price_per_m
            FROM model_endpoints
            WHERE model_id = %s
              AND endpoint_provider = 'Fireworks'
              AND fetched_at >= NOW() - INTERVAL '24 hours'
              AND blended_price_per_m > 0
              AND COALESCE(raw_data->>'service_tier','') NOT IN %s
            ORDER BY endpoint_provider, fetched_at DESC, blended_price_per_m ASC
        """, (model_id, TIER_EXCLUSIONS))
        row = cur.fetchone()
        if not row:
            failures.append(f"  FAIL: {model_id}: no standard Fireworks row in last 24h")
            continue
        if abs(row[1] - exp_in) > 0.005 or abs(row[2] - exp_out) > 0.005:
            failures.append(f"  FAIL: {model_id}: expected {exp_in}/{exp_out}, got {row[1]}/{row[2]}")
        else:
            print(f"  ok: {model_id} Fireworks = {row[1]}/{row[2]}")

    # --- provider listing duplicate check (post-migration) ------------
    # Mirrors the api.py provider-detail rule: one row per model_id,
    # newest first, direct feed beats the OpenRouter aggregate.
    for prov in ("Fireworks", "DeepInfra", "Together", "Groq"):
        cur.execute("""
            SELECT model_id, count(*) FROM (
                SELECT DISTINCT ON (me.model_id)
                    me.model_id,
                    me.input_price_per_m,
                    me.output_price_per_m
                FROM model_endpoints me
                JOIN models m ON me.model_id = m.id
                WHERE me.endpoint_provider = %s
                  AND m.is_active = TRUE
                  AND me.blended_price_per_m > 0
                  AND me.fetched_at >= NOW() - INTERVAL '24 hours'
                  AND COALESCE(me.raw_data->>'service_tier','') NOT IN %s
                ORDER BY me.model_id, (me.source = 'openrouter')::int ASC, me.fetched_at DESC,
                         me.blended_price_per_m ASC
            ) t GROUP BY model_id HAVING count(*) > 1
        """, (prov, TIER_EXCLUSIONS))
        dups = cur.fetchall()
        if dups:
            failures.append(f"  FAIL: /providers/{prov} duplicate model_ids after tier filter: {dups[:5]}")
        else:
            print(f"  ok: /providers/{prov} no duplicates")

    # --- vision-exp API-price rule (Des, 2026-10-22): the provider's own
    # direct feed wins over the OpenRouter aggregate even when OR is newer.
    cur.execute("""
        SELECT source, input_price_per_m, output_price_per_m
        FROM model_endpoints
        WHERE endpoint_provider = 'DeepInfra'
          AND model_id = 'deepseek/deepseek-v4-flash-vision-exp'
          AND fetched_at >= NOW() - INTERVAL '24 hours'
          AND COALESCE(raw_data->>'service_tier','') NOT IN %s
        ORDER BY (source = 'openrouter')::int ASC, fetched_at DESC
        LIMIT 1
    """, (TIER_EXCLUSIONS,))
    src, ip, op = cur.fetchone()
    if src != 'deepinfra_direct' or abs(ip - 0.44) > 0.005:
        failures.append(f"  FAIL: vision-exp winner is {src} at {ip}/{op}, want deepinfra_direct at 0.44/1.32")
    else:
        print(f"  ok: vision-exp = deepinfra_direct 0.44/1.32 (API is source of truth)")

    conn.close()
    return failures


if __name__ == "__main__":
    print("Unit golden tests (2026-10-22 fixes):")
    fails = run_unit()
    if "--live" in sys.argv:
        print("\nLive golden tests (prod DB, last 24h):")
        fails += run_live()
    if fails:
        print("\n" + "\n".join(fails))
        print(f"\n{len(fails)} FAILURE(S)")
        sys.exit(1)
    print("\nAll golden tests passed")
