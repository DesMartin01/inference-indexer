#!/usr/bin/env python3
"""Diagnose the AA matcher: which slugs exist for Opus, why opus-5-fast missed."""
import requests, re

html = requests.get(
    "https://artificialanalysis.ai/leaderboards/models",
    timeout=30,
    headers={"User-Agent": "InferenceIndexer/1.0"},
).text

pattern = r'\\"name\\":\\"([^"]+)\\"[^}]*?\\"slug\\":\\"([^"]+)\\"[^}]*?\\"modelCreatorCountry\\":\\"([a-z]{2})\\"[^}]*?\\"intelligenceIndex\\":([0-9.]+)'
matches = re.findall(pattern, html, re.DOTALL)
print(f"total matches: {len(matches)}")

opus = [(n, s, sc) for n, s, _, sc in matches if "opus" in s.lower() or "opus" in n.lower()]
print("opus entries:")
for n, s, sc in opus:
    print(f"  {s:35s} score={float(sc):.1f} name={n}")

# Simulate match_aa_score for the fast variant
mid = "anthropic/claude-opus-5-fast"
model_part = mid.split("/")[-1]
base = re.sub(r"-\d{4}$", "", model_part).replace(".", "-").replace("_", "-")
print(f"\nslug derived for opus-5-fast: '{base}' -> direct match: {base in {s for _, s, _ in opus}}")
base_no_version = re.sub(r"-\d{3,4}$", "", base)
print(f"no-version: '{base_no_version}' -> in slugs: {base_no_version in {s for _, s, _ in opus}}")