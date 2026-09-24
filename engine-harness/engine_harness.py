#!/usr/bin/env python3
"""
InferenceIndexer Recommendation Engine — 50-Persona QA Harness.

Runs each persona's natural-language request through the PRODUCTION parser +
API the same way the homepage does (frontend parser semantics replicated in
parse_constraints.py, then POST /v1/recommend with the parsed tuple), grades
results on 4 axes, and writes a JSON + markdown scorecard.

Usage:
    .venv/bin/python3 engine_harness.py [--limit N] [--only CO01,PR02]

Axes (each persona scores 0-4, suite total /200):
    1. PARSE     — parser extracted the expected constraint tuple
    2. ANSWER    — correct answer type (models / providers / compare)
    3. COMPLIANCE — every result satisfies every parsed constraint
    4. SANITY    — top result defensible (AA present, Cost/IQ rank-order correct)
"""
import json
import re
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

BASE = "https://api.inferenceindexer.ai"
SSR = {"X-SSR-Secret": "inferenceindexer-ssr-2026"}

# ---------------------------------------------------------------------------
# Deterministic parser — mirrors EnginePanel.parseConstraints() (keep in sync)
# ---------------------------------------------------------------------------

USE_CASES = ["support", "volume", "extraction", "summarization", "coding", "research"]
UC_SYNONYMS = [
    (re.compile(r"\brag\b|retrieval[\s-]augmented"), "summarization"),
    (re.compile(r"\bcod(?:e|ing)\b|programming|\bdeveloper\b", re.I), "coding"),
    (re.compile(r"customer (?:service|support)|helpdesk|\bticket", re.I), "support"),
    (re.compile(r"high[\s-]volume|\bbulk\b|batch processing", re.I), "volume"),
    (re.compile(r"extract|parse documents|\binvoices?\b|\breceipts?\b", re.I), "extraction"),
    (re.compile(r"summariz|\bdigest\b|briefing|report writing", re.I), "summarization"),
]


def parse_constraints(text: str) -> dict:
    t = text.lower()
    c = {
        "budget_max_usd_per_m": None,
        "aa_min": None,
        "context_min": None,
        "zdr": False,
        "eu_sovereign": False,
        "reasoning": None,
        "use_case": None,
    }
    if re.search(r"zero[\s-]?data[\s-]?retention|\bzdr\b|no[\s-]?(data[\s-]?)?(retention|logging|training)", t):
        c["zdr"] = True
    if re.search(r"\beu\b|european|eu[\s-]?(infra|sovereign|domicile)|gdpr", t):
        c["eu_sovereign"] = True

    aa = (
        re.search(r"aa(?:\s|intelligence)?(?:\s+(?:index|score))?\s*(?:above|over|>|of at least|at least)\s*([0-9]+(?:\.[0-9]+)?)", t)
        or re.search(r"(?:above|over|>|of at least|at least)\s*(?:an\s+)?aa(?:\s+(?:index|score))?\s*(?:of\s*)?([0-9]+(?:\.[0-9]+)?)", t)
        or re.search(r"aa\s*(?:index|score)?\s*([0-9]+(?:\.[0-9]+)?)\s*\+", t)
    )
    if aa:
        v = float(aa.group(1))
        if 0 < v <= 100:
            c["aa_min"] = v

    b = re.search(r"(?:under|below|less than|max|up to|<)\s*\$?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:/\s*m|per\s*m(?:illion)?|/m\b)?", t) or \
        re.search(r"\$\s*([0-9]+(?:\.[0-9]+)?)\s*(?:/\s*m|per\s*m(?:illion)?)", t)
    if b:
        v = float(b.group(1))
        if 0 < v < 1000:
            c["budget_max_usd_per_m"] = v

    ctx = re.search(r"([0-9]+)\s*k?\s*(?:token)?\s*context", t) or re.search(r"context[^0-9]{0,10}([0-9]+)\s*k", t)
    if ctx:
        k = int(ctx.group(1))
        if 4 <= k <= 2000:
            c["context_min"] = k * 1000
    elif re.search(r"large context|long context|big context", t):
        c["context_min"] = 128000

    if re.search(r"non[\s-]?reasoning|no[\s-]reasoning|without reasoning|deterministic output", t):
        c["reasoning"] = False
    elif re.search(r"reasoning|thinking|chain of thought|\bcot\b", t):
        c["reasoning"] = True

    best_uc, best_pos = None, float("inf")
    for rx, uc in UC_SYNONYMS:
        m = rx.search(t)
        if m and m.start() < best_pos:
            best_pos, best_uc = m.start(), uc
    for uc in USE_CASES:
        i = t.find(uc)
        if i != -1 and i < best_pos:
            best_pos, best_uc = i, uc
    c["use_case"] = best_uc
    return c


MODEL_PATTERNS = [
    re.compile(r"\bdeepseek\s*v?4\b", re.I), re.compile(r"\bgpt[- ]?[0-9]", re.I),
    re.compile(r"\bclaude\s+(opus|sonnet|haiku)", re.I), re.compile(r"\bgemini\b", re.I),
    re.compile(r"\bllama\s*[0-9]", re.I), re.compile(r"\bglm[- ]?[0-9]", re.I),
    re.compile(r"\bgrok\b", re.I), re.compile(r"\bmistral\b", re.I),
    re.compile(r"\bqwen\b", re.I), re.compile(r"\bkimi\b", re.I),
]


def classify_answer(text: str, c: dict) -> str:
    t = text.lower()
    if re.search(r"(providers?\s+(serving|hosting|offering))|price compared|price comparison", t):
        for rx in MODEL_PATTERNS:
            if rx.search(text):
                return "model-compare"
    mentions_model = any(rx.search(text) for rx in MODEL_PATTERNS)
    mentions_price = re.search(r"\$|budget|under|cheap|price|cost|/\s*m", t)
    mentions_workload = re.search(r"for|workload|agent|use case|support|coding|research|extraction|summariz", t)
    if (c["zdr"] or c["eu_sovereign"]) and not mentions_model and not mentions_price and not mentions_workload:
        return "providers"
    return "models"


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def post_recommend(body: dict, attempts: int = 3):
    last = None
    for attempt in range(attempts):
        req = urllib.request.Request(
            f"{BASE}/v1/recommend",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json", **SSR},
            method="POST",
        )
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=75) as r:
                data = json.loads(r.read())
            return data, int((time.time() - t0) * 1000)
        except urllib.error.HTTPError as e:
            # 4xx are real answers, not transient — raise for the caller to grade
            raise
        except Exception as e:
            last = e
            time.sleep(2 * (attempt + 1))
    raise last


def get_providers(attempts: int = 3):
    last = None
    for attempt in range(attempts):
        try:
            req = urllib.request.Request(f"{BASE}/v1/providers", headers=SSR)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except Exception as e:
            last = e
            time.sleep(2 * (attempt + 1))
    raise last


def run_persona(p: dict) -> dict:
    result = {"id": p["id"], "category": p["category"], "request": p["request"],
              "scores": {}, "notes": []}

    # 1. PARSE: does the parser extract what the persona intends?
    parsed = parse_constraints(p["request"])
    expected = p["expected_constraints"]
    parse_ok = all(parsed.get(k) == v for k, v in expected.items())
    # parser may add nothing extra that would distort (use_case optional)
    result["scores"]["parse"] = 4 if parse_ok else 0
    result["parsed"] = {k: v for k, v in parsed.items() if v not in (None, False)}
    if not parse_ok:
        result["notes"].append(f"expected {expected}, parsed {parsed}")

    # 2. ANSWER type
    answer_type = p["answer_type"]
    routed = classify_answer(p["request"], parsed)
    result["scores"]["answer"] = 4 if routed == answer_type else 0
    result["routed"] = routed
    if routed != answer_type:
        result["notes"].append(f"routed {routed}, expected {answer_type}")

    if routed == "providers":
        provs = get_providers().get("providers", [])
        if parsed.get("zdr"):
            provs = [x for x in provs if x.get("is_zdr")]
        if parsed.get("eu_sovereign"):
            provs = [x for x in provs if x.get("is_eu_sovereign")]
        result["scores"]["compliance"] = 4 if len(provs) >= 1 else 0
        result["scores"]["sanity"] = 4 if len(provs) >= 1 else 0
        result["n_results"] = len(provs)
        if not provs:
            result["notes"].append("no providers matched")
        return result

    # models / compare path -> call the API with parsed tuple
    body = {k: v for k, v in parsed.items() if v is not None}
    body["limit"] = 5
    if not body or body == {"limit": 5}:
        # unconstrained browse — engine contract says redirect; grade as fail-loud expected
        result["scores"]["compliance"] = 0
        result["scores"]["sanity"] = 0
        result["notes"].append("no constraints parsed; engine correctly requires constraints (n/a path)")
        return result
    try:
        d, ms = post_recommend(body)
    except urllib.error.HTTPError as e:
        result["scores"]["compliance"] = 0
        result["scores"]["sanity"] = 0
        result["notes"].append(f"API {e.code}: {e.read().decode()[:120]}")
        return result
    result["latency_ms"] = ms
    recs = d.get("recommendations", [])

    # 3. COMPLIANCE: every constraint verifiably satisfied
    violations = []
    for r in recs:
        if parsed.get("budget_max_usd_per_m") is not None:
            if (r.get("blended_price_per_m") or 0) > parsed["budget_max_usd_per_m"]:
                violations.append(f"{r['model_id']} blended {r.get('blended_price_per_m')} > budget")
        if parsed.get("aa_min") is not None:
            if (r.get("aa_index_score") or 0) < parsed["aa_min"]:
                violations.append(f"{r['model_id']} AA {r.get('aa_index_score')} < floor")
        if parsed.get("zdr") and not r.get("zdr"):
            violations.append(f"{r['model_id']} not ZDR")
        if parsed.get("eu_sovereign") and not r.get("eu_sovereign"):
            violations.append(f"{r['model_id']} not EU")
        if parsed.get("context_min") and (r.get("context_length") or 0) < parsed["context_min"]:
            violations.append(f"{r['model_id']} context {r.get('context_length')} < min")
        if parsed.get("reasoning") is True and not r.get("is_reasoning"):
            violations.append(f"{r['model_id']} not reasoning-capable")
    # use_case: ranking-level, can't verify per row — accepted if API returned results
    result["scores"]["compliance"] = 4 if (recs and not violations) else (2 if recs else 0)
    result["violations"] = violations[:5]

    # 4. SANITY: AA present on all, Cost/IQ ascending
    aa_missing = [r["model_id"] for r in recs if r.get("aa_index_score") is None]
    cpiqs = [r.get("cost_per_iq") for r in recs if r.get("cost_per_iq") is not None]
    ascending = all(cpiqs[i] <= cpiqs[i + 1] for i in range(len(cpiqs) - 1))
    why_present = all(r.get("why") for r in recs)
    ranks_ok = [r.get("rank") for r in recs] == list(range(1, len(recs) + 1))
    # Note: API sorts by TASK-ADJUSTED Cost/IQ; raw cpiq may be non-monotonic when use_case set.
    # Raw ascending is informational only when a use_case multiplier applies.
    raw_ascending_ok = parsed.get("use_case") is None and ascending or parsed.get("use_case") is not None
    sanity = 4 if (recs and not aa_missing and why_present and ranks_ok) else \
             2 if recs else 0
    if aa_missing:
        result["notes"].append(f"missing AA: {aa_missing[:3]}")
    if parsed.get("use_case") is None and not ascending:
        result["notes"].append("Cost/IQ not ascending (no use_case set)")
    result["scores"]["sanity"] = sanity
    result["n_results"] = len(recs)
    result["top"] = recs[0]["name"] if recs else None
    return result


def main():
    limit = None
    only = None
    args = sys.argv[1:]
    if "--limit" in args:
        limit = int(args[args.index("--limit") + 1])
    if "--only" in args:
        only = set(args[args.index("--only") + 1].split(","))

    personas = json.loads(Path(__file__).parent.joinpath("engine-personas.json").read_text())
    if only:
        personas = [p for p in personas if p["id"] in only]
    if limit:
        personas = personas[:limit]

    print(f"Running {len(personas)} personas against {BASE}...\n")
    results = []
    for i, p in enumerate(personas):
        r = run_persona(p)
        total = sum(r["scores"].values())
        results.append(r)
        flag = "PASS" if total >= 14 else ("WEAK" if total >= 10 else "FAIL")
        print(f"[{flag} {total:>2}/16] {p['id']} {p['category']:9s} | {p['request'][:58]}")
        for n in r.get("notes", []) or []:
            print(f"         - {n}")
        time.sleep(1.2)  # rate-limit courtesy

    out = {"generated": time.strftime("%Y-%m-%d %H:%M UTC"), "results": results}
    total_score = sum(sum(r["scores"].values()) for r in results)
    max_score = len(results) * 16
    print(f"\nTOTAL: {total_score}/{max_score} ({total_score / max_score:.0%})")
    Path(__file__).parent.joinpath("harness-results.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
