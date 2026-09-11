#!/usr/bin/env python3
"""
Surgical recompute of the Sep 10, 2026 composite TPI row.

On Sep 10 the AA leaderboard scrape broke (zero records returned; no
aa_daily_ingest row exists for that date). The hourly pipeline still wrote a
composite row, but the relative P60 gate saw a crippled scored population
(threshold 26.32 instead of ~22) and the basket collapsed to 11 providers,
producing $2.8676 vs ~$1.58 either side.

Fix: recompute Sep 10 from that day's stored snapshots (real prices) with
each model's CURRENT v4.3 AA score, applying the same method as every other
day (equal weight per provider, 30% cap, P60 relative gate). This matches
the backfill philosophy: "what the index would have said under today's
rules" - the Sep 10 snapshots' own sit_adjusted_price is the corrupted
output of the broken scrape, so it is NOT used.

Only the 2026-09-10 composite row is touched. Dry-run by default.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import dotenv_values
import psycopg2

DRY_RUN = "--apply" not in sys.argv
DAY = "2026-09-10"

vals = dotenv_values(os.path.expanduser("~/.hermes/.env"))
conn = psycopg2.connect(vals["SUPABASE_DB_URL"], connect_timeout=10)
cur = conn.cursor()

# Last snapshot per model on the target day (same shape the backfill uses)
cur.execute("""
    SELECT DISTINCT ON (ps.model_id) ps.model_id, ps.blended_price_per_m
    FROM price_snapshots ps
    JOIN models m ON m.id = ps.model_id
    WHERE ps.fetched_at::date = %s
      AND ps.blended_price_per_m > 0
      AND m.is_active = TRUE
      AND ps.model_id NOT LIKE '%%:batch'
      AND m.modality NOT IN ('embedding','tts','stt','reranker','reader',
                             'image-generation','video-generation')
    ORDER BY ps.model_id, ps.fetched_at DESC
""", (DAY,))
snapshots = cur.fetchall()
print(f"priced snapshots on {DAY}: {len(snapshots)}")

# Current AA scores
cur.execute("SELECT id, aa_index_score FROM models WHERE is_active AND aa_index_score IS NOT NULL")
aa_by_id = dict(cur.fetchall())

# GPT-4-Turbo reference: cost per IQ = blended * 40 / aa; eligibility via P60
# of the scored population (same relative gate as the live pipeline).
scored = [(mid, p, aa_by_id[mid]) for mid, p in snapshots if mid in aa_by_id]
print(f"with current AA score: {len(scored)}")
if len(scored) < 50:
    print("ABORT: scored population too small for a relative gate")
    sys.exit(1)

saa = sorted(a for _, _, a in scored)
def pct(p):
    k = (len(saa) - 1) * p
    f, c = int(k), min(int(k) + 1, len(saa) - 1)
    return saa[f] + (saa[c] - saa[f]) * (k - f)

threshold = pct(0.60)
print(f"P60 threshold: {threshold:.4f}")

# Cheapest qualifying model per provider
best = {}
for mid, price, aa in scored:
    if aa < threshold:
        continue
    sit_adj = price * 40.0 / aa
    prov = mid.split("/")[0]
    if prov not in best or sit_adj < best[prov][1]:
        best[prov] = (mid, sit_adj)

providers = sorted(best)
print(f"basket: {len(providers)} providers -> {providers}")

weights = [min(1.0 / len(providers), 0.30) for _ in providers]
scale = 1.0 / sum(weights)
tpi = sum(w * scale * best[p][1] for p, w in zip(providers, weights))
tpi = round(tpi, 6)

# Anchor: Sep 4 = 1000
cur.execute("""SELECT sit_price FROM sit_index_values
WHERE tier='composite' AND date='2026-09-04' AND calculation_method='tpi_equal_weight_provider_capped'""")
base = cur.fetchone()[0]
points = round(tpi / base * 1000.0, 2)
print(f"recomputed TPI {DAY}: ${tpi} | index {points} | {len(providers)} providers")

cur.execute("""SELECT sit_price, sit_index_points, provider_count FROM sit_index_values
WHERE tier='composite' AND date=%s AND calculation_method='tpi_equal_weight_provider_capped'""", (DAY,))
old = cur.fetchone()
print(f"current row:      ${old[0]} | index {old[1]} | {old[2]} providers")

if DRY_RUN:
    print("DRY RUN: nothing written. Re-run with --apply to write.")
    sys.exit(0)

cur.execute("""
    UPDATE sit_index_values
    SET sit_price = %s, sit_index_points = %s, model_count = %s, provider_count = %s,
        eligibility_threshold = %s
    WHERE tier='composite' AND date=%s AND calculation_method='tpi_equal_weight_provider_capped'
""", (tpi, points, len(providers), len(providers), round(threshold, 4), DAY))
conn.commit()
print("WRITTEN.")
cur.close()
conn.close()