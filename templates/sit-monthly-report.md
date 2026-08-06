# SIT Monthly Report Template

> **Purpose:** Establish InferenceIndexer as the authoritative, citable benchmark for AI inference pricing. Published the first Tuesday of every month. Distributed as PDF + web page + email/Substack. Every chart and table is downloadable with attribution: "Source: InferenceIndexer.ai / SIT."

---

## Report Structure (4-6 pages)

### Page 1: Executive Summary

**[MONTH] SIT Monthly: [HEADLINE STATISTIC]**

The Standard Inference Token (SIT) composite closed at **$[COMPOSITE_PRICE]/M** on [DATE], [CHANGE_DIR] [CHANGE_PCT]% from [PREV_MONTH_PRICE]/M last month.

**Key numbers at a glance:**

| Metric | This Month | Last Month | Change |
|--------|-----------|------------|--------|
| SIT-Composite (all tiers) | $[PRICE]/M | $[PRICE]/M | [PCT]% |
| SIT-Frontier | $[PRICE]/M | $[PRICE]/M | [PCT]% |
| SIT-Standard | $[PRICE]/M | $[PRICE]/M | [PCT]% |
| SIT-Budget | $[PRICE]/M | $[PRICE]/M | [PCT]% |
| SIT-Micro | $[PRICE]/M | $[PRICE]/M | [PCT]% |
| Models tracked | [COUNT] | [COUNT] | +[COUNT] |
| Providers | [COUNT] | [COUNT] | +[COUNT] |
| Models with AA scores | [COUNT] | [COUNT] | +[COUNT] |

**The headline:** [One sentence summarizing the month's most important price movement. Example: "Micro-tier prices surged 17% as new entrants failed to offset rising demand for sub-1B models."]

**Three things to know:**

1. [BULLET 1: biggest tier move with context]
2. [BULLET 2: notable model launch or price cut]
3. [BULLET 3: quality-adjusted value shift or methodology note]

---

### Page 2: Index Performance & Tier Analysis

**SIT-Composite: $[PRICE]/M ([CHANGE_PCT]% MoM)**

[Brief narrative on what drove the composite. 2-3 sentences connecting the numbers to real events: model launches, price cuts, new providers entering.]

**Tier breakdown:**

| Tier | Price/M | MoM Change | Models | Median SIT Score | Notable Move |
|------|---------|-----------|--------|-----------------|--------------|
| Frontier | $[PRICE] | [PCT]% | [COUNT] | [SCORE] | [MODEL] [DIRECTION] [PCT]% |
| Standard | $[PRICE] | [PCT]% | [COUNT] | [SCORE] | [MODEL] [DIRECTION] [PCT]% |
| Budget | $[PRICE] | [PCT]% | [COUNT] | [SCORE] | [MODEL] [DIRECTION] [PCT]% |
| Micro | $[PRICE] | [PCT]% | [COUNT] | [SCORE] | [MODEL] [DIRECTION] [PCT]% |

**Tier narrative:** [One paragraph per tier explaining what happened. What moved, why, and what it means. Be specific: name models, name providers, cite percentages.]

**30-day SIT-Composite trend:**

```
[ASCII CHART OR EMBEDDED SVG]

$[HIGH] |        *
        |      *   *
$[MID]  |    *       *    *
        |  *           *
$[LOW]  |*
        +----------------------
         [DATE]          [DATE]
```

---

### Page 3: Biggest Movers

**Top 5 price increases (30-day, blended $/M):**

| Rank | Model | Provider | Tier | Price/M | Change | SIT Score |
|------|-------|----------|------|---------|--------|-----------|
| 1 | [NAME] | [PROVIDER] | [TIER] | $[PRICE] | +[PCT]% | [SCORE] |
| 2 | [NAME] | [PROVIDER] | [TIER] | $[PRICE] | +[PCT]% | [SCORE] |
| 3 | [NAME] | [PROVIDER] | [TIER] | $[PRICE] | +[PCT]% | [SCORE] |
| 4 | [NAME] | [PROVIDER] | [TIER] | $[PRICE] | +[PCT]% | [SCORE] |
| 5 | [NAME] | [PROVIDER] | [TIER] | $[PRICE] | +[PCT]% | [SCORE] |

**Top 5 price decreases (30-day, blended $/M):**

| Rank | Model | Provider | Tier | Price/M | Change | SIT Score |
|------|-------|----------|------|---------|--------|-----------|
| 1 | [NAME] | [PROVIDER] | [TIER] | $[PRICE] | -[PCT]% | [SCORE] |
| 2 | [NAME] | [PROVIDER] | [TIER] | $[PRICE] | -[PCT]% | [SCORE] |
| 3 | [NAME] | [PROVIDER] | [TIER] | $[PRICE] | -[PCT]% | [SCORE] |
| 4 | [NAME] | [PROVIDER] | [TIER] | $[PRICE] | -[PCT]% | [SCORE] |
| 5 | [NAME] | [PROVIDER] | [TIER] | $[PRICE] | -[PCT]% | [SCORE] |

**Movers narrative:** [Why did these models move? New model launches undercutting incumbents? Providers running promotions? Supply constraints? Be specific and data-driven. This is the section journalists will quote.]

---

### Page 4: Quality-Adjusted Value Leaders

The SIT Score adjusts raw price for reasoning capability and intelligence (AA Index). A score of 100 = tier median. Below 100 = cheaper than the typical model in that tier, adjusted for quality.

**Best value by tier (lowest SIT Score = cheapest per unit of intelligence):**

| Tier | Model | Provider | Blended $/M | SIT-Adjusted $/M | SIT Score | What it means |
|------|-------|----------|-------------|------------------|-----------|---------------|
| Frontier | [NAME] | [PROVIDER] | $[PRICE] | $[PRICE] | [SCORE] | [X]% below tier median |
| Standard | [NAME] | [PROVIDER] | $[PRICE] | $[PRICE] | [SCORE] | [X]% below tier median |
| Budget | [NAME] | [PROVIDER] | $[PRICE] | $[PRICE] | [SCORE] | [X]% below tier median |
| Micro | [NAME] | [PROVIDER] | $[PRICE] | $[PRICE] | [SCORE] | [X]% below tier median |

**Premium plays (highest SIT Score = most expensive per unit of intelligence):**

| Tier | Model | Provider | Blended $/M | SIT-Adjusted $/M | SIT Score | What it means |
|------|-------|----------|-------------|------------------|-----------|---------------|
| Frontier | [NAME] | [PROVIDER] | $[PRICE] | $[PRICE] | [SCORE] | [X]% above tier median |
| Standard | [NAME] | [PROVIDER] | $[PRICE] | $[PRICE] | [SCORE] | [X]% above tier median |
| Budget | [NAME] | [PROVIDER] | $[PRICE] | $[PRICE] | [SCORE] | [X]% above tier median |
| Micro | [NAME] | [PROVIDER] | $[PRICE] | $[PRICE] | [SCORE] | [X]% above tier median |

**Value analysis:** [What's the story? Is the gap between cheapest and most expensive widening or narrowing? Are frontier models getting cheaper per unit of intelligence? Is a new entrant disrupting the value rankings? This is where the SIT methodology earns its keep: you can say things no raw-price index can say.]

**Coverage note:** [COUNT] of [TOTAL] models ([PCT]%) have AA Intelligence Index scores and therefore SIT Scores. Models without AA scores are excluded from quality-adjusted analysis but remain in the spot-price index.

---

### Page 5: Price Spread & Market Structure

**The frontier spread:** [RATIO]x

The gap between the cheapest and most expensive frontier model is **[RATIO]x** ([CHEAPEST_MODEL] at $[PRICE]/M vs [MOST_EXPENSIVE_MODEL] at $[PRICE]/M). This is [WIDER/NARROWER] than last month's [RATIO]x.

[Paragraph explaining what this means. A widening spread suggests premium models are commanding higher prices while budget options push down. A narrowing spread suggests commoditization.]

**Provider landscape:**

| Provider | Models | Avg Blended $/M | Tiers present | Notable |
|----------|--------|-----------------|----------------|---------|
| [PROVIDER] | [COUNT] | $[PRICE] | [TIERS] | [NOTE] |
| [PROVIDER] | [COUNT] | $[PRICE] | [TIERS] | [NOTE] |
| [PROVIDER] | [COUNT] | $[PRICE] | [TIERS] | [NOTE] |
| [PROVIDER] | [COUNT] | $[PRICE] | [TIERS] | [NOTE] |
| [PROVIDER] | [COUNT] | $[PRICE] | [TIERS] | [NOTE] |

**New entrants this month:**

| Model | Provider | Tier | Price/M | SIT Score | Context |
|-------|----------|------|---------|-----------|---------|
| [NAME] | [PROVIDER] | [TIER] | $[PRICE] | [SCORE] | [WHY IT MATTERS] |
| [NAME] | [PROVIDER] | [TIER] | $[PRICE] | [SCORE] | [WHY IT MATTERS] |
| [NAME] | [PROVIDER] | [TIER] | $[PRICE] | [SCORE] | [WHY IT MATTERS] |

---

### Page 6: Methodology & Forward Look

**Methodology summary:**

- **SIT-Composite:** Median blended price per million tokens across all tracked models
- **SIT Score:** Quality-adjusted comparison metric. Formula: `(Blended Price x Reasoning Multiplier) / AA Intelligence Index Score`, then scaled against tier median (100 = median). Lower = cheaper per unit of intelligence.
- **Reasoning multipliers:** Frontier 4x, Standard 3x, Budget 2.5x, Micro 2x. Non-reasoning models: 1.0x
- **Data source:** OpenRouter API (338 models, 57 providers). Prices are per-million-token, weighted 70% input / 30% output for blended price.
- **Update frequency:** Daily. This report reflects the close on [DATE].
- **Full methodology:** inferenceindexer.ai/methodology

**Forward look:**

[Bullet list of what to watch next month. Upcoming model launches? Expected price cuts? Regulatory changes? Provider expansion? This is where you demonstrate forward visibility, not just backward reporting. 3-5 bullets.]

- [FORWARD POINT 1]
- [FORWARD POINT 2]
- [FORWARD POINT 3]

**Citation:**

When citing this report, please use: "InferenceIndexer SIT Monthly Report, [MONTH] [YEAR]. Source: inferenceindexer.ai"

**Archive:** All past reports available at inferenceindexer.ai/reports

**Data access:** Free API at inferenceindexer.ai/api. Embeddable widgets and CSV downloads available.

---

## Distribution Checklist

- [ ] Generate PDF from this template
- [ ] Publish web version at inferenceindexer.ai/reports/[YEAR]-[MONTH]
- [ ] Send email/Substack version to subscriber list
- [ ] Post executive summary thread on X
- [ ] Post summary on LinkedIn
- [ ] Send personalized notes to target journalists with relevant cuts
- [ ] Update press kit with latest charts
- [ ] Archive in public report archive
- [ ] Update embeddable widgets with latest data

## Report Generation Instructions

Run the data generation script:
```bash
cd /home/ubuntu/obsidian-vault/10-Projects/inference-futures-exchange
.venv/bin/python generate_monthly_report.py --month YYYY-MM
```

This queries the DB and outputs a populated markdown file with all `[PLACEHOLDER]` values filled in. The narrative sections require manual writing by Des.
