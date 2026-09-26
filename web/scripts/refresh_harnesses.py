"""Weekly refresh for the /harnesses page data.

Fetches harnesses.json from best-of-Agent-Harnesses (CC-BY-SA-4.0), applies the
II category rubrics, writes web/public/harnesses-data.json.

Usage:
  python3 refresh_harnesses.py                 # live fetch + write
  python3 refresh_harnesses.py --source PATH   # read local file instead (tests)
  python3 refresh_harnesses.py --include-research  # also emit research table (D2: off)
  python3 refresh_harnesses.py --cron          # cron mode: write if changed, log, exit 0

Rubric source of truth: Harness-Page-PRD.md sections 3.1-3.5.
Do not change rubric logic without updating the PRD first.
"""
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SOURCE_URL = "https://ryanalberts.github.io/best-of-Agent-Harnesses/harnesses.json"
OUT_PATH = Path(__file__).resolve().parent.parent / "public" / "harnesses-data.json"
LOG_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "harnesses-refresh.log"
ATTRIBUTION = "Data: best-of-Agent-Harnesses (https://ryanalberts.github.io/best-of-Agent-Harnesses/), CC-BY-SA-4.0"

SB_RUNTIME_CATS = {"personal-agent-runtimes", "coding-agent-products", "frameworks",
                   "multi-agent", "research-task", "libraries-sdks"}
SB_EXCLUDED = {"coding-harness-configs", "progressive-disclosure",
               "plugins-mcp-cli", "evaluation", "observability", "memory"}


def _sandbox_rank(p):
    d = p.get("deep_dive") or {}
    a = d.get("tooling_sandboxing") or {}
    return a.get("rank")


def _buy_tier(p):
    d = p.get("deep_dive") or {}
    b = d.get("build_vs_buy") or {}
    return b.get("tier")


def rubric_personal(projects):
    return [entry_to_row(p) for p in projects
            if p.get("category") == "personal-agent-runtimes"]


def rubric_research(projects):
    return [entry_to_row(p) for p in projects
            if p.get("category") == "research-task"]


def rubric_enterprise(projects):
    rows = []
    for p in projects:
        if p.get("license_signal") != "open-source":
            continue
        if _sandbox_rank(p) == 3 or p.get("recovery") == "durable":
            rows.append(entry_to_row(p))
    return rows


def rubric_small_business(projects):
    rows = []
    for p in projects:
        cat = p.get("category")
        if cat not in SB_RUNTIME_CATS or cat in SB_EXCLUDED:
            continue
        stars = p.get("stars") or 0
        buy = _buy_tier(p)
        is_managed = (buy == 3)
        is_simple = (p.get("tier_rank") or 9) <= 2
        if stars >= 100 and (is_managed or is_simple):
            rows.append(entry_to_row(p))
    return rows


def entry_to_row(p):
    d = p.get("deep_dive") or {}
    buy = d.get("build_vs_buy") or {}
    sand = d.get("tooling_sandboxing") or {}
    return {
        "name": p.get("name"),
        "url": p.get("url"),
        "page_url": p.get("page_url"),
        "description": (p.get("description") or "")[:140],
        "stars": p.get("stars") or 0,
        "tier": p.get("tier"),
        "tier_rank": p.get("tier_rank"),
        "autonomy": p.get("autonomy"),
        "recovery": p.get("recovery"),
        "license": p.get("license_signal"),
        "source_category": p.get("category"),
        "sandbox": {3: "strong", 2: "basic", 1: "none", 0: "unknown"}.get(sand.get("rank"), "unknown"),
        "buy": {3: "managed", 2: "blueprint", 1: "build"}.get(buy.get("tier"), "unknown"),
    }


def build_payload(projects, meta_in, include_research=False):
    personal = sorted(rubric_personal(projects), key=lambda r: -r["stars"])
    research = sorted(rubric_research(projects), key=lambda r: -r["stars"])
    enterprise = sorted(rubric_enterprise(projects), key=lambda r: -r["stars"])
    small_business = sorted(rubric_small_business(projects), key=lambda r: -r["stars"])
    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "attribution": ATTRIBUTION,
        "license": "CC-BY-SA-4.0",
        "source_meta": {
            "project_count": meta_in.get("project_count"),
            "stars_captured": meta_in.get("stars_captured"),
            "deep_dive_researched": sum(1 for p in projects if p.get("deep_dive")),
        },
        "tables": {
            "personal": {"title": "Personal agents", "rows": personal},
            "enterprise": {"title": "Enterprise harnesses", "rows": enterprise},
            "small_business": {"title": "Small business harnesses", "rows": small_business},
        },
    }
    if include_research:
        payload["tables"]["research"] = {"title": "Research harnesses", "rows": research}
    return payload


def log(message):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a") as f:
        f.write(f"{datetime.now(timezone.utc).isoformat()} {message}\n")


def main():
    include_research = "--include-research" in sys.argv
    cron_mode = "--cron" in sys.argv
    src_arg = sys.argv[sys.argv.index("--source") + 1] if "--source" in sys.argv else None
    if src_arg:
        src = json.loads(Path(src_arg).read_text())
    else:
        src = json.loads(urllib.request.urlopen(SOURCE_URL, timeout=60).read().decode())
    projects = src["projects"]
    payload = build_payload(projects, src.get("meta", {}), include_research)
    counts = {k: len(v["rows"]) for k, v in payload["tables"].items()}

    if cron_mode:
        try:
            current = json.loads(OUT_PATH.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            current = None
        if current and current.get("tables") == payload["tables"]:
            log(f"cron: no change {counts}")
            print(f"No change: {counts}")
            return
        OUT_PATH.write_text(json.dumps(payload, indent=1))
        log(f"cron: wrote snapshot {counts} (source stars_captured {payload['source_meta'].get('stars_captured')})")
        print(f"Wrote (cron): {counts}")
        return

    OUT_PATH.write_text(json.dumps(payload, indent=1))
    print(f"Wrote {OUT_PATH} with {counts} (generated_at {payload['generated_at']})")


if __name__ == "__main__":
    main()
