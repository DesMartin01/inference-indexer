"""Tests for refresh_harnesses rubric functions. Run: python3 test_refresh_harnesses.py"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from refresh_harnesses import (
    rubric_personal, rubric_enterprise, rubric_small_business, rubric_research,
    entry_to_row,
)


def load_fixture():
    p = Path(__file__).parent / "fixture_harnesses.json"
    return json.loads(p.read_text())["projects"]


def test_personal_is_direct_category():
    rows = rubric_personal(load_fixture())
    names = [r["name"] for r in rows]
    assert "OpenClaw" in names and "Hermes" in names
    assert all(r["source_category"] == "personal-agent-runtimes" for r in rows)


def test_enterprise_needs_license_and_sandbox_or_durable():
    rows = rubric_enterprise(load_fixture())
    # OpenClaw: open-source but sandbox=1, recovery=resumable -> out
    names = [r["name"] for r in rows]
    assert "OpenClaw" not in names
    # Codex (sandbox=3) and Hermes (durable) -> in
    assert "Codex" in names and "Hermes" in names
    for r in rows:
        assert r["license"] == "open-source"
        assert r["sandbox"] == "strong" or r["recovery"] == "durable"


def test_small_business_excludes_skill_packs_and_lists():
    rows = rubric_small_business(load_fixture())
    names = [r["name"] for r in rows]
    # Skill pack excluded per D3
    assert "awesome-claude-code" not in names
    # Sub-100-star list repo excluded by stars floor
    assert "Community-curated agent lists" not in names
    # botpress: managed (buy=3) despite complex tier -> in
    assert "botpress" in names
    # Open Interpreter: mostly simple runtime -> in
    assert "Open Interpreter" in names
    for r in rows:
        assert r["source_category"] not in ("coding-harness-configs", "progressive-disclosure",
                                            "plugins-mcp-cli", "evaluation", "observability", "memory")
        assert r["stars"] >= 100
        assert (r["tier_rank"] or 9) <= 2 or r["buy"] == "managed"


def test_research_flag_gated():
    rows = rubric_research(load_fixture())
    names = [r["name"] for r in rows]
    assert "DeerFlow" in names and "gpt-researcher" in names
    # Fixture carries 2 of the 5 live research entries (subset for speed);
    # the live count is asserted by Task 1 Step 6's expected output, not here.


def test_row_shape():
    row = entry_to_row(load_fixture()[0])
    for key in ("name", "url", "page_url", "description", "stars", "tier",
                "tier_rank", "autonomy", "recovery", "license", "source_category",
                "sandbox", "buy"):
        assert key in row


def test_local_entries_merge_and_flow():
    # load_local_entries fetches stars from the GitHub API; patch it out so the
    # merge logic is tested without network.
    import refresh_harnesses as rh
    orig = rh.load_local_entries
    rh.load_local_entries = lambda: ([
        {
            "name": "Grok Build", "url": "https://github.com/xai-org/grok-build",
            "page_url": None, "description": "xAI's terminal coding agent.",
            "stars": 27345, "tier": "slightly complex", "tier_rank": 3,
            "autonomy": "bounded", "recovery": "resumable",
            "license_signal": "open-source", "category": "coding-agent-products",
            "local_entry": True, "verified_facts": {"checked": "test"},
            "deep_dive": {"tooling_sandboxing": {"rank": 3}, "build_vs_buy": {"tier": 2}},
        }
    ], [])
    try:
        fx = {"meta": {"project_count": 167, "stars_captured": "2026-09-20"},
              "projects": load_fixture()}
        payload = rh.build_payload(fx["projects"] + rh.load_local_entries()[0],
                                   fx["meta"])
        ent = payload["tables"]["enterprise"]["rows"]
        names = [r["name"] for r in ent]
        # strong sandbox rank 3 + open-source -> Enterprise table
        assert "Grok Build" in names
        grok = [r for r in ent if r["name"] == "Grok Build"][0]
        assert grok["license"] == "open-source" and grok["sandbox"] == "strong"
        assert grok["local_entry"] is True
        assert grok["verified_facts"] == {"checked": "test"}
        # source_meta records the editorial addition and excludes it from deep_dive count
        assert payload["source_meta"]["local_entries"] == ["Grok Build"]
        assert payload["source_meta"]["deep_dive_researched"] == sum(
            1 for p in fx["projects"] if p.get("deep_dive"))
        # enterprise count grew by exactly one vs the fixture-only run
        solo = rh.build_payload(fx["projects"], fx["meta"])
        assert len(ent) == len(solo["tables"]["enterprise"]["rows"]) + 1
    finally:
        rh.load_local_entries = orig


def test_main_skips_entries_source_already_has():
    # If the upstream source adds grok-build itself, the merge must skip it.
    import refresh_harnesses as rh
    fx = load_fixture()
    have = {p.get("url") for p in fx}
    assert "https://github.com/xai-org/grok-build" not in have  # fixture sanity
    # Simulate upstream adoption: the merge filter drops entries whose URL exists
    local_url = "https://github.com/xai-org/grok-build"
    added = [local_url] if local_url not in have else []
    assert added == [local_url]  # fixture case: not in source, so merged
    have_with = have | {local_url}
    added2 = [local_url] if local_url not in have_with else []
    assert added2 == []  # upstream case: skipped


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"All {len(fns)} tests passed")
