# InferenceIndexer.ai — Product Requirements Document

**Version:** 1.0
**Date:** 2026-08-03
**Author:** Des Martin
**Status:** Draft for review

---

## 1. Product Vision & Goals

### 1.1 Mission Statement

Be the CoinMarketCap of AI inference. Inference is both a commodity and an asset that can be swapped and consumed. InferenceIndexer is the independent price information layer that tracks, indexes, and publishes inference pricing across every provider, becoming the reference point that everyone cites.

### 1.2 Problem

| Problem | Impact |
|---------|--------|
| No standard reference price for AI inference | Researchers, journalists, and analysts have no citable number. Papers like Xing (2026) note "futures market: non-existent." |
| Pricing is scattered across 10+ provider websites | A developer comparing GPT-5.6 vs Claude Opus 5 vs DeepSeek V4 must visit 3+ sites and do mental math |
| No historical price tracking | Nobody can answer "how much has inference fallen in price this year?" with data |
| Aggregators (OpenRouter) have pricing but aren't an index | They're a marketplace participant with a margin, not a neutral information layer |
| No futures settlement reference | Architect and future exchanges need an independent index to settle against |

### 1.3 Solution

A neutral, independent price index for AI inference built on the Standard Inference Token (SIT) methodology. The product has four layers:

1. **Index layer:** SIT-Composite and tier indices (Frontier, Standard, Budget), published daily
2. **Data layer:** Per-model pricing across 300+ models from 10+ sources, updated hourly
3. **API layer:** Free API (email signup) for developers, researchers, and businesses
4. **Distribution layer:** Daily alerts via Telegram and Twitter/X, building audience and citations

### 1.4 Primary Goals

| Goal | Metric | Target |
|------|--------|--------|
| Become the cited reference for inference pricing | Number of third-party citations | 10+ citations in first 6 months |
| Build audience of AI developers and traders | Monthly unique visitors | 10K MAU within 6 months |
| Build email list from day 1 | API key signups | 500 signups within 3 months |
| Establish historical dataset | Days of price history | 180 days by month 6 |

### 1.5 Non-Goals (what this is NOT)

- **Not an exchange.** InferenceIndexer does not facilitate trades or match buyers and sellers.
- **Not a benchmarking service.** Model quality/intelligence benchmarking is ArtificialAnalysis.ai's domain. We use their scores for tiering only.
- **Not an aggregator/router.** We don't route API calls. We publish prices.
- **Not a brokerage.** No buy/sell recommendations, no portfolio tracking, no trading features.
- **Not ad-supported.** Revenue comes from API licensing and index licensing, not display ads.
- **No futures trading in v1.** Futures are Phase 2. The index must be trusted first.

---

## 2. User Personas

### 2.1 Primary: AI App Developer (Sarah)

- **Who:** Backend engineer at a 20-person AI SaaS startup
- **Context:** Spends $8K/month on inference across OpenAI and DeepSeek
- **Frustration:** "I have no idea if I'm overpaying. I check OpenRouter sometimes but their prices include markup. I want to see raw provider prices side by side, and I want to know if prices are trending up or down before I commit to a provider."
- **Journey:** Google search "cheapest LLM API 2026" -> finds InferenceIndexer -> searches for her model -> sees the price, the 30-day trend, and the SIT-Standard tier average -> bookmarks the page -> signs up for API key to pull prices into her internal cost dashboard
- **Success:** Switches to a cheaper provider after seeing the data, saves 15% on monthly inference costs

### 2.2 Secondary: Crypto/AI Investor (Marcus)

- **Who:** Full-time crypto trader, tracks AI narrative
- **Context:** Manages a $200K portfolio, actively trades AI-related tokens
- **Frustration:** "I want directional exposure to AI inference as a commodity but there's no futures market yet. At minimum I want to track the price of inference like I track gas fees and ETH prices."
- **Journey:** Follows InferenceIndexer on Twitter -> sees daily SIT-Composite updates -> checks the homepage chart for trends -> uses the free API to pull historical data for his own analysis -> shares the index movement in trading groups
- **Success:** Uses the SIT-Composite trend as an input to investment decisions, refers other traders to the index

### 2.3 Tertiary: Model Provider Competitive Intelligence (Priya)

- **Who:** Product manager at a mid-tier inference provider
- **Context:** Responsible for pricing strategy at a company competing with OpenAI, DeepSeek, and Together AI
- **Frustration:** "I check competitor pricing manually every week. It's tedious and I miss changes. I want a single dashboard showing where our pricing sits relative to the market."
- **Journey:** Finds InferenceIndexer via a colleague -> filters by tier to see her company's models vs competitors -> checks historical chart to see if competitors have been dropping prices -> signs up for API to feed competitive pricing data into her internal dashboard
- **Success:** Catches a competitor price drop within 24 hours instead of 2 weeks, adjusts her pricing strategy

---

## 3. Core Design: Data Pipeline & Index Calculation

### 3.1 System Overview

InferenceIndexer is a deterministic data product, not an AI product. The core engine is a pipeline that fetches, normalizes, calculates, and publishes inference pricing data on a schedule.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                                  │
│  OpenRouter API │ OpenAI │ Anthropic │ Google │ DeepSeek │ Together │
│  Fireworks API  │ Groq   │ TensorX   │ Community submissions        │
└──────────┬──────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    INGESTION LAYER                                   │
│  Cron job (hourly) → fetch pricing from each source                 │
│  → normalize to $/M tokens (input, output, blended)                │
│  → store raw + normalized in Supabase                               │
│  → anomaly detection (>50% change = flag for review)               │
└──────────┬──────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    INDEX CALCULATION LAYER                           │
│  Daily at 00:00 UTC → calculate SIT indices                         │
│  → SIT-Frontier, SIT-Standard, SIT-Budget, SIT-Composite            │
│  → equal-weighted (Phase 1) → capacity-weighted (Phase 2)           │
│  → store index values in Supabase                                   │
│  → publish to website, API, Telegram, Twitter                       │
└──────────┬──────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                                │
│  Next.js frontend (Claude Design HTML)                              │
│  → Homepage: SIT-Composite + tier breakdown + model table           │
│  → Model pages: price history, charts, provider info               │
│  → Provider pages: aggregate pricing per provider                   │
│  → API: REST endpoints (free with email signup)                    │
│  → Telegram bot: daily index alert                                  │
│  → Twitter/X: daily index post                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 Data Fetching Specification

| Source | Endpoint | Method | Frequency | Models |
|--------|----------|--------|-----------|--------|
| OpenRouter | `GET https://openrouter.ai/api/v1/models` | API, no auth | Hourly | 315+ |
| Together AI | `GET https://api.together.xyz/v1/models` | API, no auth | Hourly | ~80 |
| Fireworks AI | `GET https://api.fireworks.ai/inference/v1/models` | API, no auth | Hourly | ~50 |
| Groq | `GET https://api.groq.com/openai/v1/models` | API, no auth | Hourly | ~15 |
| OpenAI | `https://openai.com/api/pricing/` | Web scrape | Daily | ~15 |
| Anthropic | `https://www.anthropic.com/pricing` | Web scrape | Daily | ~10 |
| Google AI Studio | `https://ai.google.dev/pricing` | Web scrape | Daily | ~20 |
| DeepSeek | `https://api.deepseek.com/pricing` | Web scrape/API | Daily | ~5 |
| TensorX | Direct relationship | Manual/API | Daily | ~10 |

### 3.3 Normalization Rules

Every fetched price point is normalized to:

```json
{
  "model_id": "openai/gpt-4o",
  "model_name": "GPT-4o",
  "provider": "OpenAI",
  "source": "openrouter",
  "source_url": "https://openrouter.ai/api/v1/models",
  "input_price_per_m": 2.50,
  "output_price_per_m": 10.00,
  "blended_price_per_m": 7.00,
  "currency": "USD",
  "context_length": 128000,
  "fetched_at": "2026-08-03T14:00:00Z",
  "raw_data": { }
}
```

**Blended price formula:** `0.4 * input_price + 0.6 * output_price`

Note: Artificial Analysis uses a different blend: 70% cached input, 20% uncached input, 10% output (7:2:1 ratio). This assumes heavy prompt caching. Our SIT blend (40/60) assumes no caching, which reflects most production workloads. We should publish both SIT-Blended (40/60) and SIT-Cached (7:2:1) to align with both use cases. See SIT methodology doc for full rationale.

### 3.3.1 SIT as the Comparison Standard (CoinMarketCap Model)

The SIT solves the core CoinMarketCap problem: how do you compare 300+ models from 40+ providers on a single page?

| Without SIT | With SIT |
|------------|----------|
| Raw prices in a table, no context | Models grouped by quality tier (like CMC categories) |
| Can't tell if a model is cheap for its quality | SIT Tier shows the quality band |
| No normalized comparison metric | SIT blended price ($/M) normalized across all providers |
| No composite index number | SIT-Composite is "the number" that gets cited |

### 3.3.2 SIT Variants: Filtering by Inference Attributes

Like CoinMarketCap's category filters (DeFi, Layer 1, Meme, AI), InferenceIndexer supports SIT variant filters. Users click a filter and the table + index recalculate for that subset.

| SIT Variant | Filter | What It Tracks |
|-------------|--------|---------------|
| **SIT-Composite** | All models | Market-wide inference price (headline number) |
| **SIT-Frontier** | AA Index >= 50 | Top-tier inference cost |
| **SIT-Standard** | AA Index 30-49 | Production-grade inference |
| **SIT-Budget** | AA Index 15-29 | High-volume low-cost inference |
| **SIT-EU-Sovereign** | EU-hosted, zero retention | EU data sovereignty compliant |
| **SIT-Open** | Open weights models only | Open-source inference cost |
| **SIT-Proprietary** | Proprietary models only | Closed-model inference cost |
| **SIT-Cached** | With prompt caching | Cached input pricing applied (7:2:1 blend) |

The SIT-Composite is always the headline number. But a user who cares about EU sovereignty can filter to SIT-EU-Sovereign and see that specific index + only EU-hosted models. This is the filtering mechanism Des described: Zero Knowledge Retention, EU Sovereign Infra, etc.

**Tier assignment:** Based on Artificial Analysis Intelligence Index score (see Section 3.3.3 for research):
- SIT-Frontier: AA >= 50
- SIT-Standard: 30 <= AA < 50
- SIT-Budget: 15 <= AA < 30
- SIT-Micro: AA < 15 or no score

### 3.3.3 AA Intelligence Index Research

The Artificial Analysis Intelligence Index is a weighted composite of multiple benchmark results. Key findings from their methodology page and model leaderboard:

**Scale:** The AA Intelligence Index is NOT a percentile or standardized score. It's a weighted composite of multiple benchmark results. Current models range from roughly 10 to 61.

**Current score distribution (from AA leaderboard, Aug 2026):**

| Score Range | Models | Examples |
|-------------|--------|----------|
| 55-61 | 3 models | Claude Opus 5 (61), Claude Opus 5 xhigh (60), Claude Fable 5 (59) |
| 50-54 | 5 models | GPT-5.6 (57), Kimi K3 (54), Grok 4.5 (51), GLM-5.2 (51), Muse Spark (50) |
| 44-49 | 1 model | DeepSeek V4 Flash (44), Gemini 3.6 Flash (50) |
| 38-43 | 1 model | Nemotron 3 Ultra (38) |
| 24-37 | 1 model | gpt-oss-120b (24) |
| <24 | Many | Budget and micro models (not shown on leaderboard) |

**Industry standard for tiers:** There is no single "industry standard" for quality tiering. Different platforms use different approaches:

| Platform | Method | Tiers |
|----------|--------|-------|
| Artificial Analysis | AA Intelligence Index (composite) | No explicit tiers, just scores |
| OpenRouter | None | No quality tiering |
| Together AI | Parameter count | 7B, 13B, 70B, etc. |
| Hugging Face | Downloads + likes | Community-driven |
| LMSYS Chatbot Arena | Elo rating | Arena score |

**Recommendation:** Use AA Intelligence Index as the tiering source because:
1. It's the most widely cited independent benchmark
2. It covers both proprietary and open-weight models
3. It uses OpenAI tokens as a standard unit (consistent with our pricing normalization)
4. It's actively maintained and updated

**Revised tier thresholds (based on current score distribution):**

| Tier | AA Index | Rationale | Current Examples |
|------|---------|-----------|-----------------|
| SIT-Frontier | >= 50 | Top quintile of benchmarked models. These are the models businesses pay a premium for. | Claude Opus 5, GPT-5.6, Kimi K3, Grok 4.5, GLM-5.2 |
| SIT-Standard | 30-49 | Mid-tier production models. The workhorses of most AI apps. | DeepSeek V4, Gemini 3.6 Flash, Nemotron 3 Ultra |
| SIT-Budget | 15-29 | Low-cost models for high-volume tasks. | Smaller open models, specialized fine-tunes |
| SIT-Micro | < 15 | Ultra-cheap, simple tasks. | 1B-8B parameter models |

**Why 50 instead of 55 for the Frontier threshold:** The current distribution shows a natural cluster at 50-51 (Grok 4.5, GLM-5.2, Muse Spark, Gemini 3.6). Setting the threshold at 50 captures this cluster as Frontier rather than Standard. This aligns with the market perception: these are top-tier models that command premium pricing.

### 3.4 Index Calculation

```
SIT-Composite = Σ(blended_price_i * weight_i) / Σ(weight_i)

Phase 1: weight_i = 1.0 (equal weight)
Phase 2: weight_i = f(context_length, provider_size)
Phase 3: weight_i = actual_volume_i
```

**Base date:** 2026-08-03
**Base value:** SIT-Composite = 1000 index points (NOT a dollar price)

**Two published numbers:**
1. **SIT Price ($/M):** The dollar-weighted average price per million tokens
2. **SIT Index Points:** Rebased to 1000 at base date, for tracking relative movement

### 3.5 Anomaly Detection

- If any model's blended price changes >50% in one hour, it is flagged
- Flagged prices are stored but excluded from index calculation until reviewed
- Review happens via a simple admin endpoint (or manual DB update in Phase 1)
- All anomaly events are logged

---

## 4. UI/UX Specification

### 4.1 Design Direction

- **Vibe:** Bloomberg terminal meets CoinMarketCap. Data-dense, fast, authoritative.
- **Color palette:** Dark background (#0a0a0a or similar), green for decreases (inference getting cheaper = good for consumers), red for increases. Gold/amber accent for the SIT-Composite number (matches Des's existing brand).
- **Typography:** System fonts for speed. Monospace for numbers.
- **No JavaScript frameworks for the main page.** Server-rendered HTML. Client-side JS only for table sorting/filtering and chart rendering.

### 4.2 Homepage Wireframe

```
┌─────────────────────────────────────────────────────────────────────────┐
│  InferenceIndexer.ai                    [Search models] [API] [Method]   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  SIT-Composite                                                           │
│  $2.84 / M tokens                          ↓ 1.2% today                  │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│  7d: ↓ 3.1%   30d: ↓ 12.4%   90d: ↓ 28.7%                               │
│                                                                          │
│  [30-day sparkline chart]                                                │
│                                                                          │
│  The Standard Inference Token (SIT) is a standardized unit for tracking  │
│  AI inference prices across providers. → Read methodology                │
│                                                                          │
├────────────────────┬────────────────┬────────────────────────────────────┤
│ SIT-Frontier       │ SIT-Standard   │ SIT-Budget                         │
│ $35.20/M  ↓ 0.8%   │ $1.25/M ↓ 1.5% │ $0.42/M ↓ 2.1%                   │
│ 12 models          │ 156 models     │ 78 models                         │
├────────────────────┴────────────────┴────────────────────────────────────┤
│ SIT-Spread (Frontier - Budget): $34.78/M  ↓ 1.9%                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  All Models  [Tier ▾] [Provider ▾] [Search...]    Sort: Blended ↑↓      │
│                                                                          │
│  #  Model            Provider    Tier     Input   Output  Blended  24h  │
│  1  DeepSeek V4 Fl   DeepSeek    Budget   $0.09   $0.18   $0.14    0%   │
│  2  GPT-4o-mini     OpenAI      Standard $0.15   $0.60   $0.42    0%   │
│  3  Mistral Small    Mistral     Budget   $0.07   $0.20   $0.15   ↓2%   │
│  4  Gemini Flash     Google      Standard $0.07   $0.30   $0.21   ↓8%   │
│  5  Claude Opus 5    Anthropic   Frontier $10.00  $50.00  $34.00   ↓1%  │
│  ...                                                                    │
│  315 models tracked across 47 providers. Updated 2 min ago.              │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│  Biggest Movers Today                                                    │
│  ↑ DeepSeek V4 Flash  +5.2%    │    ↓ Gemini Flash  -8.1%              │
│  ↑ Mistral Large     +2.1%    │    ↓ Groq Llama    -4.3%              │
├─────────────────────────────────────────────────────────────────────────┤
│  Get the data via API → Sign up for free API key                        │
├─────────────────────────────────────────────────────────────────────────┤
│  InferenceIndexer.ai · Independent price index for AI inference         │
│  Methodology · API Docs · Contact                                       │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.3 Page Inventory

| Page | URL | Purpose |
|------|-----|---------|
| Homepage | `/` | SIT-Composite, tier breakdown, model table, biggest movers |
| Model detail | `/models/{model_id}` | Price history chart, provider info, SIT comparison |
| Provider page | `/providers/{provider}` | All models from one provider, aggregate stats |
| Tier page | `/tier/{tier}` | All models in a tier, tier index chart |
| Methodology | `/methodology` | Full SIT methodology document |
| API docs | `/api/docs` | API endpoint documentation, signup form |
| API signup | `/api/signup` | Email signup, API key generation |
| About | `/about` | What InferenceIndexer is, independence statement |

### 4.4 Model Detail Page Layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ← Back to all models                                                    │
│                                                                          │
│  GPT-4o                                    [OpenAI logo]                 │
│  Tier: SIT-Standard    Context: 128K    Quality: AA Index 48             │
├─────────────────────────────────────────────────────────────────────────┤
│  Current Price                                                           │
│  Input: $2.50/M   Output: $10.00/M   Blended: $7.00/M                  │
│  24h: 0%   7d: ↓ 2%   30d: ↓ 8%   90d: ↓ 15%                           │
├─────────────────────────────────────────────────────────────────────────┤
│  [Price chart: 1d | 7d | 30d | 90d | All]                               │
│  Full interactive chart showing blended price over time                 │
├─────────────────────────────────────────────────────────────────────────┤
│  SIT Comparison                                                          │
│  This model is 460% above the SIT-Standard tier average ($1.25/M)       │
│  This model is 185% above the SIT-Composite ($2.84/M)                   │
├─────────────────────────────────────────────────────────────────────────┤
│  Data Sources                                                            │
│  • OpenRouter API (last fetched: 2 min ago)                             │
│  • OpenAI pricing page (last fetched: 3 hours ago)                      │
│  Raw JSON: { "pricing": { "prompt": "0.0025", ... } }                  │
├─────────────────────────────────────────────────────────────────────────┤
│  API Access                                                              │
│  curl https://api.inferenceindexer.ai/v1/models/openai/gpt-4o/history   │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.5 Performance Targets

| Metric | Target |
|--------|--------|
| Homepage load time | < 1 second (server-rendered) |
| API response time | < 200ms (p95) |
| Data freshness | < 1 hour (models), < 24 hours (daily index) |
| Uptime | 99.5% (Phase 1), 99.9% (Phase 2) |

---

## 5. Data Specification (Supabase Schema)

### 5.1 Database Schema

```sql
-- Models table: master list of tracked models
CREATE TABLE models (
  id TEXT PRIMARY KEY,              -- e.g. "openai/gpt-4o"
  name TEXT NOT NULL,               -- "GPT-4o"
  provider TEXT NOT NULL,           -- "OpenAI"
  tier TEXT NOT NULL,               -- "frontier" | "standard" | "budget" | "micro"
  context_length INTEGER,
  aa_index_score FLOAT,             -- Artificial Analysis score
  modality TEXT,                    -- "text" | "multimodal"
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  is_active BOOLEAN DEFAULT TRUE
);

-- Price snapshots: hourly price data per model
CREATE TABLE price_snapshots (
  id BIGSERIAL PRIMARY KEY,
  model_id TEXT NOT NULL REFERENCES models(id),
  source TEXT NOT NULL,             -- "openrouter" | "openai_direct" | etc.
  input_price_per_m FLOAT NOT NULL,
  output_price_per_m FLOAT NOT NULL,
  blended_price_per_m FLOAT NOT NULL,
  raw_data JSONB,
  fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  is_anomalous BOOLEAN DEFAULT FALSE,
  reviewed_at TIMESTAMPTZ
);

CREATE INDEX idx_price_snapshots_model_time ON price_snapshots(model_id, fetched_at DESC);
CREATE INDEX idx_price_snapshots_time ON price_snapshots(fetched_at DESC);

-- SIT index values: daily calculated indices
CREATE TABLE sit_index_values (
  id BIGSERIAL PRIMARY KEY,
  date DATE NOT NULL,
  tier TEXT NOT NULL,               -- "composite" | "frontier" | "standard" | "budget"
  sit_price FLOAT NOT NULL,         -- dollar price ($/M tokens)
  sit_index_points FLOAT NOT NULL,  -- rebased to 1000 at base date
  model_count INTEGER NOT NULL,
  calculation_method TEXT NOT NULL, -- "equal_weight" | "capacity_weight" | "volume_weight"
  calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(date, tier)
);

-- API users: email signup for API keys
CREATE TABLE api_users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT NOT NULL UNIQUE,
  api_key TEXT NOT NULL UNIQUE,
  plan TEXT NOT NULL DEFAULT 'free', -- "free" | "paid"
  created_at TIMESTAMPTZ DEFAULT NOW(),
  last_accessed_at TIMESTAMPTZ,
  request_count INTEGER DEFAULT 0,
  rate_limit_per_day INTEGER DEFAULT 1000
);

-- Alert subscribers: Telegram/Twitter distribution
CREATE TABLE alert_subscribers (
  id BIGSERIAL PRIMARY KEY,
  platform TEXT NOT NULL,           -- "telegram" | "twitter"
  chat_id TEXT,                     -- Telegram chat ID
  created_at TIMESTAMPTZ DEFAULT NOW(),
  is_active BOOLEAN DEFAULT TRUE
);

-- Anomaly log
CREATE TABLE anomalies (
  id BIGSERIAL PRIMARY KEY,
  model_id TEXT NOT NULL REFERENCES models(id),
  previous_price FLOAT,
  new_price FLOAT,
  change_pct FLOAT,
  detected_at TIMESTAMPTZ DEFAULT NOW(),
  resolved_at TIMESTAMPTZ,
  resolution TEXT                   -- "confirmed" | "reverted" | "error"
);
```

### 5.2 Data Retention

- **Price snapshots:** Retained indefinitely (this is the core asset)
- **SIT index values:** Retained indefinitely
- **API request logs:** 90 days
- **Anomaly logs:** Retained indefinitely

### 5.3 Initial Data Load

On first deployment, the system will:
1. Fetch all models from OpenRouter API (~315 models)
2. Create model records in Supabase
3. Assign tiers based on AA Index scores (manual lookup for Phase 1)
4. Fetch pricing for all models (first snapshot)
5. Calculate first SIT index values
6. Backfill is not possible (no historical data exists yet). Day 1 = base date.

---

## 6. Technical Architecture

### 6.1 Tech Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Frontend** | Next.js 14+ (App Router) with Claude Design HTML | Server-rendered for speed, API routes for backend, Claude Design for visual quality |
| **Database** | Supabase (managed Postgres) | Free tier, built-in REST API, auth, real-time, no server management |
| **Data pipeline** | Python 3.11 script, cron-scheduled | Already proven with OpenRouter fetching. Simple, reliable. |
| **Charts** | Chart.js or lightweight canvas | Client-side, no framework dependency |
| **API** | Supabase REST API (auto-generated) + Next.js API routes for custom endpoints | Supabase handles CRUD, Next.js handles auth/rate-limiting |
| **Auth** | Supabase Auth (email magic link) | No passwords, minimal friction, builds email list |
| **Hosting (frontend)** | Vercel (Next.js frontend + API) | Free tier covers initial traffic. Separated from personal VPS. |
| **Hosting (pipeline + bots)** | Hetzner Cloud CX22 (EUR 4.50/mo) | Standalone infra for InferenceIndexer. EU-based, clean separation from personal projects. See Section 6.6. |
| **DNS** | Cloudflare | Free, fast, DDoS protection |

### 6.2 Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                        DUBLIN VPS                                     │
│                                                                       │
│  ┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐  │
│  │ Python cron     │    │ Telegram bot     │    │ Twitter poster  │  │
│  │ (hourly fetch)  │    │ (daily alert)    │    │ (daily post)    │  │
│  └────────┬────────┘    └────────┬─────────┘    └────────┬────────┘  │
│           │                      │                       │           │
│           │    fetch + write     │  read + post          │  post     │
│           ▼                      ▼                       ▼           │
│      Supabase DB          Supabase DB              Twitter/X API      │
│      (price_snapshots,    (sit_index_values)       (daily SIT post)   │
│       sit_index_values)                                                │
│           │                                                            │
└───────────┼────────────────────────────────────────────────────────────┘
            │
            │ REST API (auto-generated by Supabase)
            ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     VERCEL (Next.js)                                   │
│                                                                       │
│  ┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐  │
│  │ Homepage        │    │ Model pages      │    │ API routes      │  │
│  │ (SSR, <1s load) │    │ (SSG, charts)    │    │ (/api/v1/...)   │  │
│  └─────────────────┘    └──────────────────┘    └─────────────────┘  │
│                                                                       │
│  Supabase Auth (email magic link → API key)                          │
└───────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     USER                                              │
│                                                                       │
│  Browser → inferenceindexer.ai                                        │
│  API call → api.inferenceindexer.ai/v1/sit/composite/latest           │
│  Telegram → daily SIT alert                                           │
│  Twitter → daily SIT post                                             │
└───────────────────────────────────────────────────────────────────────┘
```

### 6.3 Data Flow

**Hourly cycle (data collection):**
1. Python script on VPS runs via cron (top of every hour)
2. Fetches pricing from OpenRouter, Together, Fireworks, Groq APIs
3. Normalizes to $/M tokens (input, output, blended)
4. Writes to Supabase `price_snapshots` table
5. Anomaly check: compares to previous hour's price, flags if >50% change

**Daily cycle (index calculation + publication):**
1. Python script runs at 00:00 UTC via cron
2. Fetches all model prices from Supabase (latest snapshot per model)
3. Groups by tier (Frontier, Standard, Budget)
4. Calculates SIT-Frontier, SIT-Standard, SIT-Budget, SIT-Composite
5. Stores in `sit_index_values` table
6. Triggers publication:
   - Telegram bot sends alert with today's SIT-Composite + tier changes
   - Twitter poster sends tweet with SIT-Composite + chart image
   - Next.js homepage rebuilds with new data (on-demand ISR)

### 6.4 API Endpoints

**Public (no auth, rate-limited by IP):**
```
GET /api/v1/sit/composite/latest          → today's SIT-Composite
GET /api/v1/sit/composite/history?days=30  → 30-day history
GET /api/v1/sit/tier/{tier}/latest        → today's tier index
GET /api/v1/models?tier=standard&sort=blended → model listings
GET /api/v1/models/{model_id}             → single model detail
```

**Authenticated (API key, higher rate limit):**
```
GET /api/v1/sit/composite/history?days=365  → full history
GET /api/v1/sit/tier/{tier}/history?days=365 → tier history
GET /api/v1/models/{model_id}/history?days=90 → model price history
GET /api/v1/providers/{provider}/models    → all models by provider
GET /api/v1/export?format=csv&tier=standard → CSV export
```

**Rate limits:**
- Public (no key): 100 requests/day, 10 requests/minute
- Free (email signup): 1,000 requests/day, 30 requests/minute
- Paid (future): 50,000 requests/day, 100 requests/minute

### 6.5 Security

- API keys stored as SHA-256 hashes in Supabase (never plaintext)
- Supabase Row Level Security (RLS) on all tables
- API keys passed via `Authorization: Bearer {key}` header
- CORS restricted to inferenceindexer.ai in production
- No user-generated content (no XSS surface)
- No payment processing in Phase 1 (no PCI scope)

### 6.6 Hosting Recommendation: Separate VPS for InferenceIndexer Pipeline

The Dublin Lightsail VPS is Des's personal machine (Hermes, Warren Bluffet, Elena's bot, Obsidian sync). InferenceIndexer needs its own infrastructure. Three options:

| Option | Provider | Spec | Cost/mo | Pros | Cons |
|--------|----------|------|---------|------|------|
| **A: Hetzner Cloud (recommended)** | Hetzner CX22 | 2 vCPU, 4GB RAM, 40GB SSD | EUR 4.50 | Cheapest, EU-based (Falkenstein/HEL), reliable, clean separation from personal infra | New provider account, manual setup |
| **B: DigitalOcean Droplet** | Basic Droplet | 1 vCPU, 2GB RAM, 50GB SSD | $12 | Established provider, simple UI, good docs | 2.5x cost of Hetzner for similar specs |
| **C: AWS Lightsail (separate instance)** | Lightsail 2GB | 2 vCPU, 2GB RAM, 60GB SSD | $12 | Same provider as personal VPS (familiar), easy snapshot/backup | Same provider as personal infra (not truly separate), higher cost |

**Recommendation: Option A (Hetzner CX22).** Reasons:
1. **Clean separation.** Different provider entirely. If InferenceIndexer grows, it scales independently. If it fails, no impact on personal infra.
2. **Cost.** EUR 4.50/month gets 2 vCPU and 4GB RAM. The pipeline is Python scripts + cron. This is overkill, not underkill.
3. **EU-based.** Falkenstein (Germany) or Helsinki. Low latency to Supabase (also EU), aligned with TensorX EU sovereignty preference.
4. **What runs there:** Python data pipeline (cron hourly), Telegram bot (daily), Twitter poster (daily), Umami analytics. Nothing user-facing. The frontend is on Vercel.
5. **Scaling path:** If traffic grows, the VPS is only running background jobs. Scale vertically (CX32, CX42) or split pipeline from bots. The frontend scales independently on Vercel.

**Architecture with separate VPS:**

```
┌──────────────────────────────────────────────────────────────────────┐
│                  HETZNER VPS (EUR 4.50/mo)                            │
│                  inferenceindexer-pipeline                            │
│                                                                       │
│  ┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐  │
│  │ Python cron     │    │ Telegram bot     │    │ Twitter poster  │  │
│  │ (hourly fetch)  │    │ (daily alert)    │    │ (daily post)    │  │
│  └────────┬────────┘    └────────┬─────────┘    └────────┬────────┘  │
│  ┌─────────────────┐                                                  │
│  │ Umami analytics │                                                  │
│  └─────────────────┘                                                  │
└───────────┼──────────────────────────────────────────────────────────┘
            │
            │ HTTPS to Supabase REST API
            ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     SUPABASE (free tier)                              │
│                     Managed Postgres + Auth                           │
│  (price_snapshots, sit_index_values, models, api_users, anomalies)  │
└───────────┼──────────────────────────────────────────────────────────┘
            │
            ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     VERCEL (free tier)                                │
│                     Next.js + Claude Design HTML                      │
│  Homepage / Model pages / API routes / Auth                          │
└──────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     USER (browser, API, Telegram, Twitter)            │
└──────────────────────────────────────────────────────────────────────┘
```

**Total monthly cost at MVP:** EUR 4.50 (Hetzner) + $0 (Vercel free) + $0 (Supabase free) + $0 (Cloudflare free) = **~EUR 4.50/month**

---

## 7. Lead Capture & User Handoff

### 7.1 Email List Strategy

The email list is the primary business asset. Every API signup is an email capture.

| Touchpoint | What's captured | How |
|------------|----------------|-----|
| API key signup | Email address | Supabase Auth magic link |
| Model page "Get price alerts" | Email + model_id | Inline form on model page |
| Homepage newsletter | Email | Footer signup form |

### 7.2 API Signup Flow

1. User clicks "Get free API key" on homepage or API docs page
2. Enters email address
3. Receives Supabase magic link email
4. Clicks link, lands on dashboard page with API key
5. API key displayed once with copy button
6. User can regenerate key from dashboard
7. Rate limit: 1,000 requests/day on free tier

### 7.3 GDPR Compliance

- Email is the only PII collected
- No tracking cookies (privacy-first, like the product positioning)
- Privacy policy linked in footer
- One-click unsubscribe on all emails
- Data export available via API (user can pull their own data)
- Data deletion: user can delete account and all associated data from dashboard

---

## 8. Analytics & Success Metrics

### 8.1 KPIs

| Category | Metric | Target (6 months) | Tool |
|----------|--------|-------------------|------|
| **Funnel** | Monthly unique visitors | 10K | Privacy-friendly analytics (Umami or Plausible) |
| **Funnel** | API key signups | 500 | Supabase auth records |
| **Funnel** | API key activation (first API call within 7 days) | 60% of signups | API request logs |
| **Growth** | Third-party citations of SIT index | 10 | Manual tracking / Google Alerts |
| **Growth** | Telegram channel subscribers | 1,000 | Telegram |
| **Growth** | Twitter followers | 2,000 | Twitter |
| **Quality** | Data freshness (median age of latest model price) | < 1 hour | DB query |
| **Quality** | Index uptime (daily calculation completed on time) | 99% | Cron monitoring |
| **Technical** | Homepage load time (p95) | < 1.5s | Vercel analytics |
| **Technical** | API response time (p95) | < 200ms | Supabase logs |

### 8.2 Analytics Stack

| Tool | Purpose | Cost |
|------|---------|------|
| Umami (self-hosted on VPS) | Privacy-friendly web analytics | Free |
| Supabase logs | API usage, query performance | Included |
| Vercel analytics | Frontend performance, Core Web Vitals | Free tier |
| Simple cron monitor (e.g. healthchecks.io) | Alert if cron job fails | Free tier |

### 8.3 Event Taxonomy

```javascript
// Events tracked in Umami
page_view              // any page load
model_view             // model detail page viewed
provider_view          // provider page viewed
tier_view              // tier page viewed
methodology_view       // methodology page viewed
api_docs_view          // API docs viewed
api_signup_start       // user entered email on signup form
api_signup_complete    // magic link clicked, key generated
api_key_copied         // user clicked "copy API key" button
chart_interact         // user changed chart timeframe
table_sort             // user sorted the model table
table_filter           // user filtered the model table
```

---

## 9. MVP Scope vs Phase 2

### 9.1 MVP (Phase 1) — In Scope

| Feature | Status | Notes |
|---------|--------|-------|
| SIT-Composite daily index | In scope | Published at 00:00 UTC |
| SIT tier indices (Frontier, Standard, Budget) | In scope | |
| SIT-Spread metric | In scope | Frontier minus Budget |
| Model listings table (300+ models) | In scope | Sortable, filterable |
| Model detail pages with price history charts | In scope | 1d, 7d, 30d, 90d, All |
| Provider pages | In scope | Aggregate per-provider pricing |
| Tier pages | In scope | All models in a tier + tier index chart |
| Methodology page | In scope | Full SIT methodology document |
| Free API (email signup) | In scope | 5 endpoints, 1K req/day |
| API docs page | In scope | Interactive docs |
| Homepage (Claude Design) | In scope | Full homepage with index, tiers, table |
| Daily Telegram alert | In scope | SIT-Composite + tier changes |
| Daily Twitter post | In scope | SIT-Composite + chart image |
| Hourly data pipeline | In scope | OpenRouter + 4 API sources |
| Daily data pipeline | In scope | 5 web scrape sources |
| Anomaly detection | In scope | Flag >50% changes |
| Privacy-friendly analytics (Umami) | In scope | |
| API key dashboard | In scope | View key, copy, regenerate |

### 9.2 Phase 2 — Out of Scope for MVP

| Feature | Phase | Notes |
|---------|-------|-------|
| Paid API tier ($99-499/mo) | Phase 2 | After 500 free signups |
| Inference futures tracking | Phase 2 | When futures markets exist (Architect etc.) |
| Volume-weighted indices | Phase 2 | When volume data is available |
| Capacity-weighted indices | Phase 2 | 3-6 months post-launch |
| Provider competitive intelligence dashboard | Phase 2 | B2B SaaS product |
| Email newsletter (weekly) | Phase 2 | After audience is built |
| Model comparison tool | Phase 2 | Side-by-side price + quality comparison |
| Webhook alerts | Phase 2 | Push notifications for price changes |
| Index licensing to exchanges | Phase 2 | When exchanges approach us |
| Regional pricing tracking | Phase 2 | US/EU/Asia pricing differentiation |
| Latency-adjusted pricing | Phase 2 | Factor in tokens/second |
| Cache pricing tracking | Phase 2 | OpenAI/Google cache discount tiers |
| Batch pricing tracking | Phase 2 | Batch API pricing (typically 50% cheaper) |

### 9.3 Tech Stack Summary (Confirmed)

| Pipeline VPS | Hetzner Cloud CX22 | EUR 4.50/mo |
| Frontend | Vercel free tier | $0 |
| Database | Supabase free tier | $0 |
| Analytics | Umami (self-hosted on Hetzner) | $0 |
| DNS/CDN | Cloudflare free | $0 |
| **Total monthly cost** | | **~EUR 4.50/mo** |

---

## 10. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| OpenRouter changes API or starts charging | Medium | High | Multi-source architecture. 7+ data sources, OpenRouter is one of many. Pipeline degrades gracefully, doesn't break. |
| ArtificialAnalysis.ai changes methodology | Low | Medium | Tier assignments are our use of their data, not a dependency. We can re-tier on any benchmark. |
| Supabase free tier limits hit | Medium | Low | 500MB DB is enough for years of price data. 50K MAU auth is enough for first year. Paid tier is $25/mo if needed. |
| Nobody cites the index | Medium | High | Daily Telegram + Twitter distribution. Active outreach to researchers, AI newsletters, and journalists. The data is free and citable. |
| Competitor launches similar index | Medium | Medium | First-mover advantage. Historical data compounds. Once cited, switching cost is high. Brand and methodology are the moat. |
| Provider blocks scraping | Low | Low | API sources are primary (OpenRouter, Together, Fireworks, Groq). Scraping is secondary. If one provider blocks, coverage drops slightly, not catastrophically. |
| Cron job fails silently | Medium | Medium | Healthchecks.io monitor on cron. Alert to Telegram if job doesn't run on schedule. |
| Vercel free tier limits hit | Low | Low | 100GB bandwidth/month on free tier. Sufficient for 10K MAU. Can upgrade to Pro ($20/mo) if needed. |

---

## 11. Open Questions

| # | Question | Owner | Needed by |
|---|----------|-------|-----------|
| 1 | What is the right input/output blend ratio? Currently 40/60. Needs empirical validation with real production workload data. | Des | Phase 2 |
| 2 | Should image generation models be included (priced per image, not per token)? | Des | Phase 2 |
| 3 | Should embedding models be tracked (priced per token but no "output")? | Des | Phase 2 |
| 4 | Should the SIT-Spread (Frontier minus Budget) be a headline metric or supporting data? | Des | Before launch |
| 5 | Should we publish a "SIT inflation/deflation rate" (annualized % change) as a CPI-equivalent? | Des | Phase 2 |
| 6 | How to handle providers who offer both token pricing and per-second pricing? | Frank | Phase 2 |
| 7 | Should we weight by provider reliability/uptime? | Frank | Phase 2 |
| 8 | Exact AI Intelligence Index threshold scores for tier boundaries. Currently using 55/30/15. Need to validate against current model landscape. | Frank | Before launch |
| 9 | Twitter API: free tier allows 1 post/day. Is that sufficient, or do we need Basic ($100/mo)? | Frank | Before launch |
| 10 | Should the API return JSON only, or also support CSV/XML for enterprise users? | Frank | Phase 2 |

---

## Appendix A: SIT Methodology Summary

The full SIT methodology is documented in `sit-methodology.md` in the project vault. Key points:

- **1 SIT = 1 million tokens at a defined quality standard**
- Four tiers: Frontier (AA >= 55), Standard (30-55), Budget (15-30), Micro (< 15)
- Blended price: 40% input + 60% output
- Phase 1 weighting: equal. Phase 2: capacity-weighted. Phase 3: volume-weighted.
- Base date: 2026-08-03. Base value: 1000 index points.
- Full reproducibility: every index value can be recalculated from stored raw data.
- Governance: 14-day public comment period for methodology changes.

## Appendix B: Competitive Landscape

| Player | What They Do | Gap InferenceIndexer Fills |
|--------|-------------|---------------------------|
| ArtificialAnalysis.ai | Model benchmarking (intelligence, speed, price) | Not an index. No historical price tracking. Not cited as reference. |
| OpenRouter | API aggregator with pricing | Market participant, not neutral. No index, no history, no content. |
| Tokenizer.info | Basic token pricing | No indices, no history, no API. |
| Architect.co | GPU-hour futures exchange | Has proprietary index, not public. GPU-hours, not inference tokens. |
| aimodels.org | Model comparison | Basic, no index, no API. |

**The gap:** No one publishes a transparent, citable, historical inference price index with a free API. InferenceIndexer occupies the CoinGecko position.

## Appendix C: Revenue Model (Phase 2+)

| Revenue Stream | Who Pays | Est. Revenue |
|---------------|----------|-------------|
| Paid API (real-time + full history) | Exchanges, funds, researchers, enterprises | $99-999/mo per tier |
| Premium data (latency, quality metrics) | Institutional users | $499/mo |
| Index licensing (settlement reference) | Exchanges (Architect, others) | $5K-50K/mo |
| Sponsored placements | Inference providers | $500-5K/mo |
| Content/ads (selective) | AI companies | $1K-10K/mo |

CoinGecko comparison: ~$30M ARR with 20M+ monthly users. The inference market is smaller but growing 100%+ annually with a higher-value audience (enterprises, not retail crypto traders).
