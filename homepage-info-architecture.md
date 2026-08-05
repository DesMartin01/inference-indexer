# InferenceIndexer Homepage — Core Information Grouping

**Date:** 2026-08-03
**Status:** Draft for review

---

## The Question

If all listings follow the same structure, what is the core grouping of key information that appears on the homepage?

This is not a design question. It's an information architecture question. What data points does a user need to see, and in what priority order?

---

## User Personas (who arrives at the homepage)

| Persona | What they want | What they do first |
|---------|---------------|-------------------|
| **Developer** | "Am I overpaying for inference?" | Search for the model they're using, check the price |
| **Trader/Investor** | "Is inference getting cheaper or more expensive?" | Look at the index number, check the chart |
| **Provider** | "How does my pricing compare to competitors?" | Filter by tier, compare their model to peers |
| **Researcher/Journalist** | "What's the SIT price for citation?" | Find the headline number, grab the citation |
| **Casual visitor** | "What is this?" | Understand what the SIT is, see the big number |

---

## Core Information Hierarchy

### Tier 1: The Headline (above the fold)

This is what every visitor sees first. It must answer "what is this and what's the number?"

| Element | What | Why |
|---------|------|-----|
| **SIT-Composite price** | The one number. e.g. "$2.84/M" | This is the WTI price. The reference point. |
| **Daily change** | "↓ 1.2% today" | Direction matters. Is inference getting cheaper? |
| **Period changes** | 7-day, 30-day, 90-day change | Trend context. One day is noise. 30 days is signal. |
| **Sparkline chart** | 30-day price chart, inline | Visual trend without taking space. Like a stock ticker. |
| **"What is SIT?"** | One-line definition + link to methodology | New visitors need context. Don't make them guess. |

### Tier 2: Tier Breakdown (immediately below headline)

The composite is one number. The tiers show what's behind it.

| Element | What | Why |
|---------|------|-----|
| **SIT-Frontier** | Price + daily change | "What does top-tier inference cost?" |
| **SIT-Standard** | Price + daily change | "What does production-grade inference cost?" |
| **SIT-Budget** | Price + daily change | "What does cheap inference cost?" |
| **SIT-Spread** | Frontier minus Budget | "Is the quality premium widening or narrowing?" |

The spread is a derivative metric but it's the most interesting one. If the spread is narrowing, cheap models are catching up to expensive ones. If widening, frontier models are pulling ahead.

### Tier 3: Model Listings (the table)

This is the CoinMarketCap part. Every model, sortable and filterable.

| Column | What | Why | Sortable? |
|--------|------|-----|-----------|
| **Rank** | Position by blended price (cheapest first by default) | Quick orientation | Yes |
| **Model** | Name + provider logo | Identification | Yes (alpha) |
| **Provider** | OpenAI, Anthropic, DeepSeek, etc. | Filter by provider | Yes |
| **Tier** | Frontier, Standard, Budget, Micro | Filter by quality | Yes |
| **Input $/M** | Price per million input tokens | Cost comparison | Yes |
| **Output $/M** | Price per million output tokens | Cost comparison | Yes |
| **Blended $/M** | 40/60 weighted average | Head-to-head comparison | Yes (default) |
| **24h change** | Price change in last 24 hours | Did a provider just change pricing? | Yes |
| **7d change** | Price change in last 7 days | Short-term trend | Yes |
| **Context** | Context window (tokens) | Capability proxy | Yes |
| **Quality** | AA Intelligence Index score | Quality benchmark | Yes |

### Tier 4: Supporting Information (below the fold or sidebar)

| Element | What | Why |
|---------|------|-----|
| **Biggest movers** | Top 5 price increases + decreases today | "What changed?" |
| **New models** | Recently added models | "What's new in the market?" |
| **Provider count** | "Tracking X providers, Y models" | Establishes coverage and authority |
| **Last updated** | Timestamp of last data pull | Trust. Stale data kills credibility. |
| **Methodology link** | "How is the SIT calculated?" | Transparency = trust = citations |
| **API link** | "Get this data via API" | Developer hook |

---

## What's NOT on the Homepage

| Excluded | Why |
|----------|-----|
| Latency/speed benchmarks | That's ArtificialAnalysis's territory. Don't compete on benchmarks. |
| Model quality scores (beyond tier assignment) | Same reason. We're the price layer, not the quality layer. |
| Provider reviews/ratings | Not our role. We report prices, not opinions. |
| News/articles | Lives on a separate /blog or /reports page. Homepage is data. |
| Sign-up walls | All index data is free. Premium is API access, not homepage content. |
| Ads | Kills credibility. Revenue comes from API licensing, not display ads. |

---

## The Listing Card (model detail)

When a user clicks a model, they see a model page. The model page shows:

| Section | What |
|---------|------|
| **Header** | Model name, provider, logo, tier badge |
| **Price card** | Current input, output, blended prices + 24h/7d/30d changes |
| **Price chart** | Historical blended price, selectable timeframe (1d, 7d, 30d, 90d, all) |
| **Provider info** | Provider name, link to provider page showing all their models |
| **Specifications** | Context window, AA Index score, modality (text, multimodal) |
| **SIT comparison** | "This model is X% above/below the SIT-Standard tier average" |
| **Data sources** | Where this price comes from (OpenRouter, direct provider, etc.) |
| **API** | JSON snippet to fetch this model's price programmatically |

---

## Homepage Layout (text wireframe)

```
┌─────────────────────────────────────────────────────────────────┐
│  InferenceIndexer                          [Search] [API] [About] │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  SIT-Composite                                                   │
│  $2.84/M tokens                          ↓ 1.2% today             │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│  7d: ↓ 3.1%   30d: ↓ 12.4%   90d: ↓ 28.7%                       │
│                                                                  │
│  [30-day sparkline chart]                                        │
│                                                                  │
│  What is SIT? The Standard Inference Token is a standardized    │
│  unit for tracking AI inference prices. → Read methodology       │
│                                                                  │
├─────────────────────┬───────────────┬────────────────────────────┤
│ SIT-Frontier        │ SIT-Standard  │ SIT-Budget                 │
│ $35.20/M  ↓ 0.8%    │ $1.25/M ↓ 1.5%│ $0.42/M ↓ 2.1%            │
├─────────────────────┴───────────────┴────────────────────────────┤
│ Spread (Frontier - Budget): $34.78/M  ↓ 1.9%                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  All Models  [Filter: Tier ▾] [Filter: Provider ▾] [Search]     │
│                                                                  │
│  # │ Model          │ Provider  │ Tier    │ Input  │ Output │ Blended │ 24h  │ 7d   │
│  1 │ DeepSeek V4    │ DeepSeek  │ Standard│ $0.09  │ $0.18  │ $0.14   │ 0%   │ ↓2%  │
│  2 │ GPT-4o-mini    │ OpenAI    │ Standard│ $0.15  │ $0.60  │ $0.42   │ 0%   │ 0%   │
│  3 │ Claude Opus 5  │ Anthropic │ Frontier│ $10.00 │ $50.00 │ $34.00  │ ↓1%  │ ↓3%  │
│  ...│               │           │         │        │        │         │      │      │
│  315 models tracked across 47 providers. Last updated: 2 min ago│
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  Biggest Movers Today                                            │
│  ↑ DeepSeek V4 Flash  +5.2%  │  ↓ Gemini Flash  -8.1%           │
│  ↑ Mistral Large     +2.1%  │  ↓ Groq Llama    -4.3%           │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  InferenceIndexer · Independent price index for AI inference     │
│  Methodology · API · Contact                                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Design Principles

1. **The number first.** The SIT-Composite is the headline. Everything else supports it.
2. **Data density over decoration.** This is a financial data product, not a SaaS landing page. Think Bloomberg, not Stripe.
3. **Free and open.** No paywalls on index data. The API and licensing are the business, not the homepage.
4. **Citable.** Every number has a timestamp and a methodology link. Researchers and journalists need to cite a source.
5. **Fast.** The homepage loads in under 1 second. No JavaScript frameworks. Server-rendered HTML with minimal client-side interactivity (sorting, filtering).
6. **No opinions.** Prices, changes, and rankings. No "recommended" or "best value" badges. Let the data speak.
