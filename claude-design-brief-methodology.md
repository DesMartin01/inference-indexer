# Claude Design Brief: InferenceIndexer.ai Methodology Page

**Project:** InferenceIndexer.ai
**Deliverable:** Methodology page HTML (single self-contained file)
**Date:** August 2026

---

## What This Page Is

The methodology page explains how the Standard Inference Token (SIT) is calculated, how models are tiered, how data is sourced, and how the index is governed. This is the trust page. Researchers, journalists, and exchange operators come here to verify that the index is sound and citable.

Think of it as the "About Our Data" page on CoinGecko or the methodology appendix on a financial index. Dense, authoritative, transparent. No marketing language.

---

## Design Direction

Same design system as other pages:
- Dark background (#0a0a0a)
- Surface/cards (#1a1a1a, border #2a2a2a)
- Gold accent (#C4A038) for section headings and key terms
- Monospace for formulas, code, and numbers (JetBrains Mono)
- Inter for body text

### Layout: Single Column with Sticky Table of Contents

Unlike the API docs page (two-column), the methodology page is a single-column long-form document. But it has a sticky table of contents on the right side (or top on mobile) for navigation.

```
┌──────────────────────────────────────────────────┬────────────────┐
│ MAIN CONTENT (single column, max-width 800px)     │ TOC (sticky)   │
│                                                  │                │
│  1. Overview                                     │ 1. Overview    │
│  ...                                             │ 2. Definition  │
│                                                  │ 3. Tiers       │
│  2. SIT Definition                               │ 4. Calculation │
│  ...                                             │ 5. Sources     │
│                                                  │ 6. Governance  │
│  3. Quality Tiers                                │ 7. Limitations │
│  ...                                             │                │
└──────────────────────────────────────────────────┴────────────────┘
```

- Main content: max-width 800px, centered with left alignment.
- TOC: width 200px, sticky top 60px. Hidden on mobile, replaced by a "Jump to section" dropdown.
- TOC items: 13px, monospace, muted grey. Active section: gold. Scrollspy.

---

## Page Structure

### 1. Top Bar (same as other pages)

```
[Logo: InferenceIndexer.ai]     [Search models...]     [API] [Methodology] [About] [Login] [Sign Up]  [LIVE ●]
```

### 2. Page Title

```
SIT Methodology

How the Standard Inference Token is defined, calculated, and governed.
```

- "SIT Methodology": 28px, white, bold.
- Subtitle: 14px, muted grey.
- Below subtitle: version and date line: "Version 0.1 - Last updated: August 3, 2026" in 12px monospace, muted grey.

### 3. Section 1: Overview

```
1. Overview

The Standard Inference Token (SIT) is a standardized unit of AI inference output
that enables price comparison across models and providers. It is to AI inference
what WTI is to crude oil: a single, trusted reference point.

The SIT serves four purposes:
- Price comparison across models on a like-for-like basis
- Composite indices that track inference price movements over time
- A reference price that futures contracts can settle against
- Benchmarking: "am I paying above or below market rate?"

InferenceIndexer is an independent price reporting agency. We do not provide
inference services, do not route API calls, and do not take positions in any
inference derivatives market. All data sources are public and verifiable.
```

- Section heading: 22px, white, bold. Number prefix in gold.
- Body text: 15px, white, line-height 1.7. Max-width 800px for readability.
- Bullet list: 15px, gold bullet points, 8px spacing between items.

### 4. Section 2: SIT Definition

```
2. Definition

2.1 Unit

1 SIT = 1 million tokens of inference at a defined quality standard.

"Tokens" refers to the standard industry unit of LLM inference, as measured by
each provider's tokenizer. While tokenizers differ between models, the "million
tokens" convention is universally adopted and provides sufficient standardization
for pricing purposes.

2.2 Pricing Components

Every SIT-eligible model has three published prices:

┌───────────────┬──────────────────────────────────────────────────────────┐
│ Component     │ Definition                                               │
├───────────────┼──────────────────────────────────────────────────────────┤
│ Input price   │ Cost per million input (prompt) tokens                   │
│ Output price  │ Cost per million output (completion) tokens              │
│ Blended price │ Weighted average: 40% input + 60% output                │
└───────────────┴──────────────────────────────────────────────────────────┘

Blended price formula:

┌────────────────────────────────────────────────────────────────────────┐
│ blended_price = (0.4 x input_price) + (0.6 x output_price)            │
└────────────────────────────────────────────────────────────────────────┘

The 60% output weighting reflects production workloads where output tokens
exceed input tokens (generation, coding, summarization). This ratio will be
refined as real-world usage data becomes available.

Note: Artificial Analysis uses a different blend (70% cached input, 20% uncached
input, 10% output) which assumes heavy prompt caching. Our 40/60 blend assumes
no caching, reflecting most production workloads. We also publish a SIT-Cached
variant using the 7:2:1 ratio for cached workloads.
```

- Sub-section headings: 18px, white, bold. "2.1", "2.2" numbering in gold.
- Definition table: 13px, same styling as homepage table.
- Formula: monospace, 14px, centered in a code block. Gold text for the formula itself.
- "Note" callout: 13px, italic, muted grey. Indented 16px. Left border: 2px gold.

### 5. Section 3: Quality Tiers

```
3. Quality Tiers

Models are grouped into quality tiers based on demonstrated capability, using
the Artificial Analysis Intelligence Index as an independent third-party benchmark.

┌──────────────┬───────────┬──────────────────────────────────────────────┐
│ Tier         │ AA Index  │ Description                                   │
├──────────────┼───────────┼──────────────────────────────────────────────┤
│ SIT-Frontier │ >= 50     │ Top-tier models from frontier labs            │
│ SIT-Standard │ 30 - 49   │ Mid-tier production models                    │
│ SIT-Budget   │ 15 - 29   │ Low-cost models for high-volume tasks         │
│ SIT-Micro    │ < 15      │ Ultra-cheap models for simple tasks           │
└──────────────┴───────────┴──────────────────────────────────────────────┘

Current tier examples (August 2026):

SIT-Frontier (8 models):
Claude Opus 5 (AA: 61), GPT-5.6 (AA: 57), Kimi K3 (AA: 54), Grok 4.5 (AA: 51),
GLM-5.2 (AA: 51), Muse Spark 1.1 (AA: 50), Gemini 3.6 Flash (AA: 50),
Llama 4 Behemoth (AA: 50)

SIT-Standard (156 models):
DeepSeek V4 Flash (AA: 44), Nemotron 3 Ultra (AA: 38), and 154 more

SIT-Budget (78 models):
Gemma 3 27B, Llama 4 8B, Mistral Small, and 75 more

SIT-Micro (73 models):
1B-8B parameter models without AA Index scores
```

- Tier table: 13px monospace. Tier names in gold.
- Example lists: 14px, model names in white, AA scores in monospace muted grey.
- Tier name prefix (SIT-Frontier, etc.) in gold.

### 6. Section 4: Index Calculation

```
4. Index Calculation

4.1 Tier Indices

Each quality tier has its own composite index:

┌──────────────────┬─────────────────────────────────────────────────────┐
│ Index            │ What it tracks                                      │
├──────────────────┼─────────────────────────────────────────────────────┤
│ SIT-Frontier     │ Average blended price of all Frontier-tier models  │
│ SIT-Standard     │ Average blended price of all Standard-tier models  │
│ SIT-Budget       │ Average blended price of all Budget-tier models     │
│ SIT-Composite    │ Blended index across all tiers                     │
│ SIT-Spread       │ Frontier price minus Budget price                  │
└──────────────────┴─────────────────────────────────────────────────────┘

4.2 Weighting Methodology

Phase 1 (Launch): Equal weighting across all models within each tier.

┌────────────────────────────────────────────────────────────────────────┐
│ SIT-Composite = Sum(blended_price_i x weight_i) / Sum(weight_i)       │
│ where weight_i = 1.0 (equal weight)                                   │
└────────────────────────────────────────────────────────────────────────┘

Phase 2 (3-6 months): Capacity-weighted. Models weighted by context window
and provider size.

Phase 3 (6-12 months): Volume-weighted. Models weighted by actual API
transaction volume, sourced from provider-reported volumes and OpenRouter
routing volumes.

4.3 Calculation Frequency

┌──────────────┬─────────────────────────────────────────────────────────┐
│ Frequency    │ What happens                                             │
├──────────────┼─────────────────────────────────────────────────────────┤
│ Hourly       │ Pull pricing from all sources, update database          │
│ Daily        │ Calculate SIT indices, publish at 00:00 UTC             │
│ Monthly      │ Review tier composition, add/remove models              │
└──────────────┴─────────────────────────────────────────────────────────┘

4.4 Base Date and Rebaselining

- Base date: August 3, 2026
- Base value: SIT-Composite = 1000 index points
- Rebaselining only on methodology changes. All rebaselining events are
  published with full explanation and 14-day public comment period.
```

- Formula in code block, gold text.
- Phase list: numbered, 15px, with phase label in gold.
- Tables: 13px, same styling throughout.

### 7. Section 5: SIT Variants

```
5. SIT Variants

Inference is not a single homogeneous commodity. The SIT supports attribute-based
filtering, similar to how CoinMarketCap filters by category (DeFi, Layer 1, etc.).

┌──────────────────────┬──────────────────────────────────────────────────┐
│ SIT Variant          │ Filter                                           │
├──────────────────────┼──────────────────────────────────────────────────┤
│ SIT-Composite        │ All models (headline number)                     │
│ SIT-Frontier         │ AA Index >= 50                                  │
│ SIT-Standard         │ AA Index 30-49                                  │
│ SIT-Budget           │ AA Index 15-29                                  │
│ SIT-EU-Sovereign     │ EU-hosted, zero data retention                  │
│ SIT-Open             │ Open weights models only                        │
│ SIT-Proprietary      │ Proprietary models only                         │
│ SIT-Cached           │ With prompt caching applied (7:2:1 blend)        │
└──────────────────────┴──────────────────────────────────────────────────┘

The SIT-Composite is always the headline number. Variant indices allow users
to track specific segments of the inference market.
```

### 8. Section 6: Data Sources

```
6. Data Sources

6.1 Primary Sources

┌──────────────────┬──────────────┬──────────┬───────────────────────────────┐
│ Source           │ Type         │ Models   │ Frequency                     │
├──────────────────┼──────────────┼──────────┼───────────────────────────────┤
│ OpenRouter API   │ Aggregator   │ 315+     │ Hourly                        │
│ Together AI API  │ Aggregator   │ ~80      │ Hourly                        │
│ Fireworks AI API │ Aggregator   │ ~50      │ Hourly                        │
│ Groq API         │ Aggregator   │ ~15      │ Hourly                        │
│ OpenAI pricing   │ Direct       │ ~15      │ Daily scrape                  │
│ Anthropic pricing│ Direct       │ ~10      │ Daily scrape                  │
│ Google AI Studio │ Direct       │ ~20      │ Daily scrape                  │
│ DeepSeek pricing │ Direct       │ ~5       │ Daily scrape                  │
│ TensorX          │ Direct       │ ~10      │ Daily                         │
└──────────────────┴──────────────┴──────────┴───────────────────────────────┘

6.2 Source Hierarchy

When a model is available from multiple sources, priority:
1. Direct provider (e.g. openai.com pricing for GPT-5.6)
2. Aggregator with lowest markup (e.g. OpenRouter base price)
3. Community submission (verified against at least one other source)

6.3 Data Quality

- Every price point stores: timestamp, source URL, raw price, normalized price
- Automated anomaly detection: if a price moves >50% in one hour, flagged
- Manual review of all tier additions and removals
- Full audit trail: every index calculation is reproducible from stored raw data
```

### 9. Section 7: Governance

```
7. Governance

7.1 Methodology Changes

Any change to this methodology triggers:
1. 14-day public comment period
2. Full version increment (0.1 -> 0.2)
3. Recalculation of historical indices using new methodology
4. Publication of both old and new values for 30-day overlap

7.2 Conflict of Interest

- InferenceIndexer is an independent price reporting agency
- InferenceIndexer does not provide inference services
- InferenceIndexer does not take positions in inference futures or derivatives
- All data sources are public and verifiable
- Methodology is fully transparent and reproducible
```

### 10. Section 8: Limitations

```
8. Limitations

8.1 Known Limitations

1. Tokenizer differences: Different models use different tokenizers. A "million
   tokens" from GPT-5.6 processes more text than a million tokens from Llama 3.2.
   This is analogous to different crude oil grades having different energy
   densities. The SIT accepts this imprecision as the cost of standardization.

2. Volume data: Phase 1 uses equal weighting because real-world transaction
   volumes are not publicly available. The index may over-represent niche models.

3. Aggregator dependency: Many prices are sourced via OpenRouter. If OpenRouter
   changes its pricing model, coverage may temporarily decrease.

4. Quality benchmark dependency: Tier assignments depend on the Artificial
   Analysis Intelligence Index. Changes to their methodology affect our tiers.

5. Excluded models: Per-request pricing, enterprise-only pricing, and
   deprecated models are not tracked.

8.2 Future Enhancements

- Volume weighting with real API call volumes
- Latency-adjusted pricing (tokens/second as a factor)
- Cache pricing tracked separately
- Batch pricing tracked separately
- Regional pricing (US, EU, Asia)
```

- Limitation list: numbered, 15px. Numbers in gold circles (same style as auth steps in API docs).
- "Future Enhancements" list: bullet points, gold bullets.

### 11. Section 9: Citing the SIT

```
9. Citing the SIT

When citing InferenceIndexer data in research, articles, or reports:

Text format:
  InferenceIndexer SIT-Composite, August 3, 2026. Available at: https://inferenceindexer.ai

Academic format:
  InferenceIndexer (2026). Standard Inference Token Methodology, v0.1.
  Retrieved from https://inferenceindexer.ai/methodology

BibTeX:
┌────────────────────────────────────────────────────────────────────────┐
│ @misc{inferenceindexer2026,                                            │
│   title  = {InferenceIndexer: Standard Inference Token Methodology},  │
│   author = {InferenceIndexer},                                         │
│   year   = {2026},                                                     │
│   url    = {https://inferenceindexer.ai/methodology},                 │
│   note   = {Version 0.1}                                               │
│ }                                                                     │
└────────────────────────────────────────────────────────────────────────┘
```

- Citation formats: 14px monospace, in code blocks for BibTeX.
- This section is important. Make it easy to copy. Add copy buttons to code blocks.

### 12. Footer (same as other pages)

---

## What NOT to Include

- No marketing language ("revolutionary", "cutting-edge", etc.)
- No testimonials
- No "Get Started" CTAs
- No charts or visualizations (this is a text document)
- No interactive calculators
- No FAQ section (the methodology IS the FAQ)
- No comparison to competitors

---

## Technical Constraints

1. Single self-contained HTML file. All CSS in `<style>`, all JS in `<script>`.
2. Same fonts and colors as other pages.
3. Single-column content (max-width 800px) with sticky TOC on right (200px).
4. On mobile: single column, TOC becomes a dropdown at top.
5. No JavaScript framework. Vanilla JS for scrollspy and copy buttons.
6. Dark theme only.
7. Code blocks have copy buttons (small "Copy" text, top-right, appears on hover).
8. Body text is readable: 15px, line-height 1.7, max-width 800px.
