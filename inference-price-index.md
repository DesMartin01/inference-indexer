# Inference Price Index — The CoinGecko Play

**Created:** 2026-08-03
**Status:** Brainstorming
**Author:** Frank Drebin for Des Martin

---

## The Concept

Become the price information layer for AI inference. Not an exchange. Not infrastructure. A data business: track, index, and publish inference pricing across all providers, becoming the reference point that everyone cites.

**CoinGecko for inference.**

---

## Why This Works

### The data is free and accessible

OpenRouter's API gives us 315+ models with live pricing in a single call. I tested it:

```
GET https://openrouter.ai/api/v1/models
→ 315 models with input/output prices per million tokens
```

Plus direct provider APIs (OpenAI, Anthropic, Google, DeepSeek, TensorX) for pricing that OpenRouter doesn't cover.

### Nobody owns this yet

- **ArtificialAnalysis.ai** tracks model intelligence, speed, latency, and price, but they're a benchmarking/comparison site. They're the "GPU Bench" of AI, not the CoinGecko.
- **Tokenizer.info** exists but is basic
- **aimodels.org** exists but basic
- **No one** publishes a daily inference price index that's cited as the reference

### The moat compounds

Day 1: "Where can I find inference prices?" → your site
Month 3: Researchers cite your index in papers (the Xing paper literally says "non-existent, proposed here")
Month 6: Architect or a competitor licenses your index for settlement
Month 12: Your index IS the inference price. Like how CoinGecko's CGC index became the crypto reference.

---

## What to Build

### Phase 1: The Index (0-2 months)

**A daily published index of inference token prices.**

Structure:
- **Granular:** Per-model, per-provider (315+ models tracked)
- **Tiered indices:** Aggregate indices by quality tier
  - IPI-Ultra (ultra-cheap, < $0.50/M)
  - IPI-Standard ($0.50-$10/M)
  - IPI-Premium ($10-$50/M)
  - IPI-Frontier (top-tier models, > $50/M)
  - **IPI-Composite** (market-wide, weighted)
- **Historical:** Full price history with charts
- **Free API:** Public endpoint for the index
- **Daily snapshot:** Published on a website + Twitter + Telegram

**Data sources:**
1. OpenRouter API (primary, 315+ models, free, no auth)
2. Direct provider pricing pages (OpenAI, Anthropic, Google AI Studio)
3. TensorX pricing (your existing relationship)
4. Community submissions (like CoinGecko's model)

**What the site looks like:**
- Homepage: Big number = today's IPI-Composite, with a chart
- Model pages: Individual model price history, like CoinMarketCap token pages
- Provider pages: Aggregate pricing by provider
- API: Free tier (daily snapshots), paid tier (real-time, historical)

### Phase 2: The Content Layer (2-4 months)

This is where Des's marketing DNA matters. The index alone is a data product. The content around it is what builds audience:

- **Weekly inference price report** (like CoinGecko's quarterly crypto report)
- **"Inflation/Deflation" tracking** — is inference getting cheaper or more expensive?
- **Model price drop alerts** — "DeepSeek V4 Flash just cut prices 30%"
- **Provider comparisons** — "Cheapest GPT-4-class inference: ranked"
- **Newsletter** — weekly inference market digest
- **Twitter/X** — daily index updates, price movement commentary

This is the audience-building play. The index gets you cited. The content gets you followed.

### Phase 3: The Business Model (4-6 months)

| Revenue Stream | Who Pays | Est. Revenue |
|---------------|----------|-------------|
| **API access** (real-time + historical) | Exchanges, funds, researchers, enterprises | $99-$999/mo per tier |
| **Premium data** (latency, throughput, quality metrics) | Institutional users | $499/mo |
| **Index licensing** (settlement reference) | Exchanges (Architect, others) | $5K-$50K/mo |
| **Sponsored placements** | Inference providers wanting visibility | $500-$5K/mo |
| **Content/ads** | AI companies wanting audience access | $1K-$10K/mo |

**CoinGecko comparison:** CoinGecko does ~$30M ARR with 20M+ monthly users. The inference market is smaller but growing 100%+ annually and has a much higher-value audience (enterprises, not retail crypto traders).

### Phase 4: The Derivatives Hook (6-12 months)

Once the index is cited and trusted, offer it as a settlement reference:
- License the IPI-Composite to Architect (or competitors) for their futures
- Or: partner with a DeFi protocol to offer onchain inference futures settling against your index
- You don't build the exchange. You own the index it settles against.

This is the CoinGecko/Bloomberg play: own the data, license it to everyone who builds on top.

---

## Competitive Analysis

| Player | What They Do | Gap |
|--------|-------------|-----|
| ArtificialAnalysis.ai | Model benchmarking (intelligence, speed, price) | Not an index. No historical price tracking. Not cited as reference. |
| OpenRouter | API aggregator with pricing | Not an index publisher. Pricing is incidental to their aggregation business. |
| Tokenizer.info | Basic token pricing | No indices, no history, no API |
| aimodels.org | Model comparison | Basic, no index |
| Architect | GPU-hour futures exchange | Has their own index but it's proprietary, not public |

**The gap:** No one publishes a transparent, citable, historical inference price index with a free API. That's the CoinGecko position.

---

## Why Des Should Do This

1. **Plays to strengths:** Data + marketing + distribution. Not heavy engineering.
2. **Audience overlap:** Agentic CMO audience are exactly the people who care about inference pricing
3. **Existing relationships:** TensorX, Nous Research, Hermes ecosystem
4. **Low capital requirement:** Data business, not infrastructure. A cron job + a website + content.
5. **Compounding moat:** Every day the index runs, the historical dataset gets more valuable. Switching cost for anyone who starts citing it.
6. **Optionality:** Index could lead to licensing, derivatives, a fund, or an acquisition. Multiple exits.

---

## What I'd Build First

A cron job that:
1. Pulls OpenRouter pricing every hour
2. Stores it in a database
3. Calculates the IPI-Composite and tier indices
4. Publishes a daily snapshot to a simple website + Twitter
5. Sends a daily Telegram alert with the index movement

Total build time: 1-2 days. I can prototype this on the VPS immediately.

The data is already flowing. The question is whether you want to be the one who names the index and starts publishing it.
