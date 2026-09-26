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


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"All {len(fns)} tests passed")
