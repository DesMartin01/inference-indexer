#!/usr/bin/env python3
"""Audit: find all variant models whose AA match resolves to a WORSE-matching
record than a sibling variant of the same base model.

The Contributor bug: "Muse Spark 1.3 Contributor" fuzzy-matched AA's base
"Muse Spark" (score 31.3) instead of its own family "muse-spark-1-3" (48.2).
Root cause is match_aa_score Strategy 4 (substring containment on
alphanumeric-normalized names): "musspark13contributor" contains
"musespark"? No - the real failure: normalized "musspark..." containment
matches the SHORT base slug "Muse Spark" before the specific one.
"""
import pipeline
from collections import defaultdict

scores = pipeline.fetch_aa_scores()

# Fetch all active models
conn = pipeline.get_db_connection()
cur = conn.cursor()
cur.execute("SELECT id, name, aa_index_score FROM models WHERE is_active AND aa_index_score IS NOT NULL")
rows = cur.fetchall()
conn.close()

print(f"active models with scores: {len(rows)}")

def base_key(name):
    """Strip variants: batch suffix, Contributor, effort/precision parens."""
    import re
    n = name.lower()
    n = re.sub(r"\(batch\)|contributor", "", n)
    n = re.sub(r"[^a-z0-9]", "", n)
    return n

groups = defaultdict(list)
for model_id, name, score in rows:
    groups[base_key(name)].append((model_id, name, score))

problems = []
for key, members in groups.items():
    if len(members) < 2:
        continue
    scores_set = {round(s, 4) for _, _, s in members if s is not None}
    if len(scores_set) > 1:
        # Same base model, different AA scores. Check each member's match.
        for mid, name, s in members:
            m = pipeline.match_aa_score(mid, name, scores)
            matched_name = m["name"] if m else None
            matched_score = m["score"] if m else None
            problems.append({
                "group": name,
                "model_id": mid,
                "current_db": round(s, 1),
                "matched_aa_name": matched_name,
                "matched_score": round(m["score"], 1) if m else None,
            })

print(f"\nvariant groups with INCONSISTENT scores: {len(problems)}")
for p in problems:
    print(f"  {p['model_id']:50s} db={p['current_db']} matched='{p['matched_aa_name']}' score={p['matched_score']}")