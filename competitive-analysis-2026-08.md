# Competitive Analysis: Inference Pricing Indexes (Aug 9 2026)

**Status:** Snapshot / dossier. Revisit as competitors evolve.
**Context:** Des flagged new players appearing in the inference pricing space. Below is an honest, evidence-based read of each — what they are, what's differentiated, and what InferenceIndexer can take from them.

---

## The four competitors

### 1. tokenixindex.com — "Tokenix" (closest product mirror)

**What it is:** An "AI Compute Price Index" (ACPI) — quality-adjusted pricing across the OpenRouter model catalog. ~319 endpoints / 57 providers. Has an INDEX page, a live SCREENER (sortable/filterable table), and a METHODOLOGY section.

**The "copier" question — honest finding:** It looks like a mirror of InferenceIndexer, but it is **NOT scraping us**. Evidence:
- Its model IDs (`z-ai/glm-5.2`, `deepseek/deepseek-v4-flash-0731`, `inclusionai/ling-2.6-flash`) and the `~anthropic` / `~deepseek` anonymous-prefixed endpoints are **OpenRouter's exact catalog** (the `~` prefix is OpenRouter's signature for anonymized routing).
- Its methodology cites "provider documentation, verified daily" + HELM-aligned / Artificial Analysis benchmarks — the **same upstream data ecosystem** InferenceIndexer already scrapes (OpenRouter API + AA Intelligence Index).
- Prices match published **list prices**, not our endpoint-averaged medians.

**Conclusion:** Des and Tokenix independently built the same product on the same upstream (OpenRouter + AA). They are not copying us — they validated the thesis and shipped a clean, conceptually-identical index. Concept overlap: ACPI ≈ SIT-composite; S/A/B/C tiers ≈ our frontier/standard/budget/micro tiers; blended 75/25 in-out ≈ our approach.
- Their strength: clean one-liner framing ("the standard measure of AI compute value"), a working screener.
- Their weakness: static snapshot / weekly cadence, no real historical time-series, no agent-native access, no MCP, no public API for agents.

---

### 2. tokenpriceindex.com — "TPI" (the one to study hardest)

**What it is:** A curated, editorial, newsletter-led "AI Token Price Index." Covers ~21 frontier models / 10 providers (curated, not comprehensive). Single headline: "AVG BLENDED COST $2.29/M tokens."

**Differentiators (its strongest moves):**
- **Weekly editorial flywheel** — index changes explained in plain language ("OpenAI cuts, Opus 5 climbs: TPI falls to $2.24"), dated index events, a free weekly email newsletter.
- **Cost-Per-Task framing** — concrete workloads (email summary, blog post, code review, RAG query) with real $ costs, not just $/token.
- **Model Positioning Map** — price vs capability scatter (log-scale blended $ vs Fast/Mid/Frontier).
- **Floor-to-ceiling spread analysis** — how the gap between cheapest and priciest members widens over time.
- Uses **geometric mean** for its blend; references the AA Intelligence Index (same tooling ecosystem as us — we use AA for SIT).

**Conclusion:** TPI leads on **editorial trust + practical framing + attention**, not data breadth. It tells a story with the number. This is the biggest *marketing/positioning* gap in InferenceIndexer's current play.

---

### 3. ayautomate.com/resources/ai-model-price-index — "AY Automate" (SEO lead magnet)

**What it is:** A dated one-day snapshot (3 vendors / 11 models: Anthropic, OpenAI, Google) published by an **AI automation agency**, with prices "checked live against each vendor's own page today." Functionally a **lead magnet** for their fractional-CAIO / AI-strategy consulting (all CTAs → "Book a call").

**Conclusion:** Not a real index. Zero history, tiny coverage, no tooling. It's content-marketing dressed as a pricing page. **Not a competitive threat to data/completeness.** Lowest relevance of the four. Notable only for its explicit "checked today, source-linked, not copied from a roundup" trust signalling and its cost-per-task / FAQ structure.

---

### 4. inferenceindex.ai — "Inference Index" (broad editorial directory)

**What it is:** A curated "directory of the AI ecosystem" — 22 models / 21 providers PLUS interfaces, harnesses, benchmarks, plugins, datasets (7 directories). Has an "index pulse" (blends a cost index + intelligence index), a leaderboard (by LMSYS ELO), a frontier cost curve (log-scale, historical), a cost calculator, and an "intelligence" news section.

**Conclusion:** Broader editorial scope, lighter pricing depth than InferenceIndexer. Its "Inference Index" (intelligence + cost blended) is conceptually related but a different, curator-led product. Strength: breadth + editorial; weakness: tiny model coverage (22) vs our 318.

---

## What we can learn (actionable)

1. **Thesis confirmed, and it's a race not a moat.** Four products now compete on inference pricing. Our **differentiators that no competitor has**:
   - **Real historical time-series** (hourly pipeline, live + historical prices). Others are snapshots or weekly.
   - **Comprehensive coverage** (318 models / 71 providers) vs their curated ~21-22.
   - **Agent-native access** — MCP server, public read API, anonymous keys, llms.txt / structured data for AI agents. **None of the four has this.** This is our stated thesis (agents will seek complete inference pricing) and we are the only one shipping it.

2. **TPI's weekly editorial flywheel is the biggest gap in our play.** We have the superior data; they win *attention* with plain-language weekly analysis ("what moved in inference pricing"). Pairing our index with a regular editorial format is a growth lever — and Des owns the voice.

3. **Cost-per-task, not just $/token, is a positioning gap.** TPI and ayautomate lead with practical framing (what does this actually cost me). Meeting buyers where they budget (tasks, not tokens) is worth considering for site UX/copy.

4. **Nobody owns agent-discoverability.** The closer they get to us in concept, the more our agent-first architecture (MCP + instant anonymous keys + llms.txt) is the defensible edge.

## Proposed next actions (for Des to weigh)

- [ ] Weekly "inference pricing" editorial format (could layer onto the existing weekly usage-weight / composite update cadence).
- [ ] Consider a cost-per-task surface on the site (leading with practical workload costs).
- [ ] Reinforce agent-discoverability in public positioning (the only differentiated, uncopied layer).
- [ ] Re-run this competitor scan periodically (space is moving fast + new entrants emerging).

---

## Sources examined (2026-08-09)
- https://www.tokenixindex.com/ + /screener + /methodology (404; one-pager via #methodology)
- https://tokenpriceindex.com/
- https://www.ayautomate.com/resources/ai-model-price-index
- https://inferenceindex.ai/

*Analysis performed directly via live-site inspection (not secondary articles).*