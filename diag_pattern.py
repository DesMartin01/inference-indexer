#!/usr/bin/env python3
"""Verify dedupe behaviour of the new slug->score pattern."""
import requests, re
html = requests.get("https://artificialanalysis.ai/leaderboards/models",
                    timeout=30, headers={"User-Agent": "InferenceIndexer/1.0"}).text
pattern = r'\\"slug\\":\\"([^"]+)\\"[^}]*?\\"intelligenceIndex\\":([0-9.]+),\\"intelligenceIndexIsEstimated\\":(true|false)'
m = re.findall(pattern, html, re.DOTALL)
print("raw matches:", len(m))
vals = [float(sc) for s, sc, e in m if s == "claude-opus-5"]
print("claude-opus-5 occurrences:", len(vals), "distinct:", sorted(set(vals)))
best = {}
for s, sc, est in m:
    sc, est = float(sc), est == "true"
    if s not in best or sc > best[s][0]:
        best[s] = (sc, est)
print("unique slugs:", len(best))
top = sorted(best.items(), key=lambda kv: -kv[1][0])[:8]
for s, (sc, est) in top:
    print(f"  {s:35s} {sc:.1f} est={est}")