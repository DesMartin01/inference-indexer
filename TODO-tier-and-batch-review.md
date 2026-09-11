# II: Unranked Tier & Batch Model Pages

Created: 2026-08-13
Status: 🟡 Parked

## Context
Found while investigating `openai/gpt-chat-latest` alias page.

## Issue 1: Price-Fallback Tier Assignment
`assign_tier()` in `pipeline.py` uses AA score as primary, but falls back to blended price when AA is null:
- `> $10/M → frontier`
- `> $1/M → standard`
- `> $0.15/M → budget`
- `else → micro`

6 of 37 frontier models have `aa_index_score: null` (tier assigned by price proxy only):
- anthropic/claude-opus-4.7-fast ($102/M)
- anthropic/claude-opus-4 ($51/M)
- anthropic/claude-opus-4.1 ($51/M)
- anthropic/claude-opus-4.8-fast ($37.40/M)
- anthropic/claude-opus-4.1:batch ($25.50/M)
- sakana/fugu-ultra ($20/M)

These have `sit_score: null`, don't participate in SIT properly, but pull up tier averages.

**552 of 830 active models have null AA scores** across all tiers (budget: 62, frontier: 6, micro: 445, standard: 39).

**Decision needed:** Keep price fallback or introduce an "unranked" tier for models without AA scores?

## Issue 2: Active `:batch` Model Pages
10 active `:batch` models exist in DB. Filtered from homepage list (`NOT LIKE '%:batch'`) but detail pages are live:
- google/gemini-3.5-flash:batch (frontier)
- google/gemini-3.6-flash:batch (frontier)
- anthropic/claude-opus-5:batch (frontier)
- openai/gpt-5:batch (standard)
- openai/gpt-5-mini:batch (budget)
- openai/gpt-5-nano:batch (standard)
- openai/o4-mini:batch (budget)
- google/gemini-2.5-flash:batch (budget)
- google/gemini-3.5-flash-lite:batch (standard)
- moonshotai/kimi-k2.7-code:batch (budget)

**Decision needed:** Are batch pages intentional (separate pricing) or should they be deactivated?

## Related Fix (Done)
Fixed single-model detail endpoint missing `is_active = TRUE` filter. Commit `a72d3c4`. Deployed to prod.
