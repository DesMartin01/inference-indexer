# InferenceIndexer Future-Proofing Plan

**Created:** August 6, 2026
**Status:** Planning (no website changes)
**Goal:** Reduce single-source dependencies, deepen data quality, and build credibility as an independent price index

---

## The Three Dependencies

| Dependency | What We Use It For | Risk | Current State |
|-----------|-------------------|------|---------------|
| OpenRouter | Pricing + usage weights | Single aggregator, not the market | 378 models, hourly refresh |
| Artificial Analysis | Intelligence scores + reasoning token data | Black box, no API, scrape-dependent | 257 models, scores on 0-100 scale |
| Flat reasoning multipliers | SIT-Adjusted Price calculation | No empirical basis, same for all models in a tier | Frontier 4.0, Standard 3.0, Budget 2.5, Micro 2.0 |

---

## Phase 1: Extract More From Existing Sources (Weeks 1-2)

No new dependencies. Just pull richer data from what we already access.

### 1A. OpenRouter Enhanced Fields

OpenRouter's API already exposes fields we're not capturing:

| Field | Models | What It Gives Us |
|-------|--------|-----------------|
| `reasoning` config | 269 | Reasoning support, effort levels (xhigh/high/medium/low/minimal), default effort |
| `internal_reasoning` pricing | 28 | Per-token cost of reasoning tokens (separate from output price) |
| `input_cache_read` | 235 | Cached input discount pricing |
| `input_cache_write` | 71 | Cache write pricing |
| `input_cache_write_1h` | 32 | 1-hour cache tier pricing |
| `web_search` | 154 | Web search tool pricing |
| `image` | 27 | Image input pricing |

**Action:** Extend `pipeline.py` to capture these fields. Store in a new `pricing_details` JSON column on `price_snapshots`.

### 1B. Artificial Analysis RSC Data Extraction

AA embeds far more data than we're pulling. Currently we only extract `intelligence_index`. The RSC payload also contains:

| Field | Available For | Value |
|-------|---------------|-------|
| `reasoningTokens` | 25 reasoning models | **Actual thinking token counts per task** (replaces flat multipliers) |
| `contextWindowTokens` | All models | Context window size (for context pricing analysis) |
| `parameters` | All models | Model parameter count |
| `isReasoning` | All models | Boolean reasoning flag |
| `outputTokensPerTask` | All evaluated models | Total output tokens (incl. reasoning) per standardized task |
| `costPerTask` | All evaluated models | USD cost per standardized task |
| `license` | All models | Open vs proprietary |
| `releaseDate` | All models | Model age for trend analysis |

**Action:** Build an AA scraper that extracts the full RSC payload. Store in a new `aa_enriched` table. Refresh weekly.

**Key finding:** AA's `reasoningTokens` field shows most models use ~2,000 thinking tokens per task. Range: 1,736 (Gemma 4 31B) to 2,409 (Qwen3.7 Max). Adaptive reasoning models (GPT-5.6 Luna, Claude Opus 5, Gemini 3.6 Flash) show 0 because their token counts vary per query. This is still better than flat 4.0x multipliers.

### 1C. Aider Leaderboard Token Data

The Aider coding benchmark provides empirical token consumption per model under a standardized workload:

| Data Point | Example |
|------------|---------|
| Prompt tokens | GPT-5 high: 2,675,561 |
| Completion tokens | GPT-5 high: 2,623,429 |
| Total cost | GPT-5 high: $29.08 |
| Reasoning effort levels | high/medium/low (can compute overhead ratio) |
| Seconds per case | Latency proxy |

**Action:** Scrape Aider leaderboard weekly. Use token ratios to validate or replace flat multipliers.

---

## Phase 2: Multi-Source Pricing (Weeks 3-6)

Add direct provider pricing and secondary aggregators to reduce OpenRouter dependency.

### 2A. Direct Provider Pricing Pages

| Provider | URL | API? | Extraction | Priority |
|----------|-----|------|------------|----------|
| OpenAI | platform.openai.com/docs/pricing | Scrape | HTML | HIGH |
| Anthropic | anthropic.com/pricing | Scrape | HTML | HIGH |
| Google | ai.google.dev/pricing | Scrape | HTML | HIGH (context tiers!) |
| DeepSeek | api-docs.deepseek.com/quick_start/pricing | Scrape | HTML (Docusaurus, clean) | MEDIUM |
| Mistral | mistral.ai/products/la-plateforme | Scrape + API (auth) | HTML | MEDIUM |
| Cohere | cohere.com/pricing | Scrape + API (auth) | HTML | LOW |
| xAI | docs.x.ai/docs/models | Scrape + API (auth) | HTML | LOW |

**Strategy:** Build a provider scraper module that fetches direct pricing. When a model exists in both OpenRouter and the direct provider, store both and flag discrepancies. This gives us:
- Price verification (catch OpenRouter errors)
- Provider-direct pricing (what users pay without a router markup)
- Context tier pricing (Google's <128K vs >128K tiers)

### 2B. Secondary Aggregators

| Aggregator | Models | API Access | Unique Value |
|-----------|--------|------------|--------------|
| DeepInfra | 100+ | Model API (no auth!) | Only aggregator besides OpenRouter with free model API |
| Together AI | 80+ | API (auth) | Large open-weight hosting |
| Fireworks AI | 50+ | API (auth) | Open-weight hosting |
| Groq | 15 | API (auth, free tier) | Fastest inference (LPU) |
| llmprice.com | Unknown | Unknown | Independent comparison site |

**Strategy:** Add DeepInfra first (no auth needed). Add Together and Fireworks for open-weight model price verification. Use median of available sources as the "verified price" alongside OpenRouter's price.

### 2C. Price Source Blending

Once we have 2+ sources per model:

```
blended_price = weighted_median(
  openrouter_price,    weight=0.5,  # broadest coverage
  provider_direct,     weight=0.3,  # authoritative source
  aggregator_price,    weight=0.2   # market rate
)
```

Show "sources: 3" in the table (we already have a Sources column). Add a `price_sources` table tracking which sources contributed to each price.

---

## Phase 3: Benchmark Independence (Weeks 4-8)

Replace single-source AA dependency with a composite intelligence score.

### 3A. Available Benchmarks

| Benchmark | Scope | Data Access | Key Metric | Coverage |
|-----------|-------|-------------|------------|----------|
| Artificial Analysis | All models | Scrape RSC | Intelligence Index (0-100) | 257 models |
| LMSYS Chatbot Arena | All models | HF .pkl files | Elo rating | 100+ models |
| HuggingFace Open LLM | Open-weight only | HF datasets API | Multi-task avg | Open models only |
| Aider | All models | HTML scrape | Code editing pass rate | ~30 models |
| Scale AI SEAL | All models | HTML scrape (JS-rendered) | Multi-category | Growing |
| LiveBench | All models | HTML scrape (JS-rendered) | Multi-task (anti-contamination) | Growing |
| OpenCompass | All (CN focus) | Unknown | Multi-task | Chinese models |

### 3B. Composite Intelligence Score

Build a blended intelligence score from multiple benchmarks:

```
composite_iq = weighted_average(
  aa_intelligence_index,  weight=0.40,  # broadest model coverage
  lmsys_elo_normalized,   weight=0.30,  # human preference signal
  aider_pass_rate,        weight=0.15,  # coding ability
  hf_open_llm_avg,        weight=0.15   # open model standardized evals
)
```

**Weighting rationale:**
- AA has the best model coverage (257 models) but is a black box
- LMSYS is the most widely cited human-preference signal but only covers ~100 models
- Aider provides practical coding ability + token consumption data
- HF Open LLM only covers open weights but uses reproducible methodology

**Missing model handling:** When a benchmark doesn't cover a model, redistribute its weight proportionally across available benchmarks. Document which benchmarks contributed to each model's score.

### 3C. Transparency Layer

Add a "benchmark sources" breakdown on model detail pages:

> **Intelligence Score: 51.2 / 100**
> Sources: AA Intelligence Index (51.2), LMSYS Elo (1284, normalized 48.3), Aider pass rate (72%, normalized 55.0)
> Composite weighted average of 3 benchmarks

This directly addresses the "AA black box" critique. Visitors see the score is derived from multiple sources, not one.

---

## Phase 4: Real Reasoning Adjustment (Weeks 6-10)

Replace flat tier multipliers with empirical per-model data.

### 4A. Data Sources for Reasoning Overhead

| Source | Data | Coverage | Quality |
|--------|------|----------|---------|
| AA RSC `reasoningTokens` | Actual thinking tokens per task | 25 reasoning models | High (standardized) |
| AA `outputTokensPerTask` | Total output tokens (incl. reasoning) | All evaluated | High |
| Aider leaderboard | Token consumption by effort level | ~30 models | High (real workload) |
| OpenRouter API `reasoning` config | Effort levels, default effort | 269 models | Medium (config only, no counts) |
| OpenRouter `internal_reasoning` pricing | Per-token reasoning price | 28 models | Medium (pricing, not counts) |
| Empirical API testing | Run standardized prompts, measure | Any model with API access | Highest (but requires API spend) |

### 4B. Per-Model Reasoning Multiplier

Instead of `tier → flat multiplier`, calculate per model:

```
reasoning_multiplier = 1 + (reasoning_tokens / output_tokens)
```

Using AA data:
- If a model uses 2,000 thinking tokens and 1,000 output tokens per task, multiplier = 3.0
- If a model uses 2,000 thinking tokens and 500 output tokens, multiplier = 5.0
- Non-reasoning models: multiplier = 1.0

For adaptive reasoning models (showing 0 in AA), use Aider data or default to tier average.

### 4C. Fallback Hierarchy

```
1. AA reasoningTokens (if available and non-zero)
2. Aider token ratio (if model is on Aider leaderboard)
3. Tier average of available per-model multipliers
4. Current flat multiplier (last resort)
```

### 4D. Documentation

On the methodology page, replace "flat tier multipliers" with:

> Reasoning multipliers are calculated per model using actual thinking token counts from Artificial Analysis and the Aider coding benchmark. For models without empirical data, the tier average multiplier is used as a fallback. See the [reasoning data table] for each model's multiplier and source.

---

## Phase 5: Better Blended Weighting (Weeks 8-12)

Move beyond the arbitrary 40/60 input/output split.

### 5A. Workload Profiles

Different use cases have different input/output ratios:

| Workload | Input % | Output % | Example |
|----------|---------|---------|---------|
| Chat | 40% | 60% | Current default |
| Coding (agent) | 20% | 80% | Aider-style |
| RAG / search | 90% | 10% | Embedding + retrieval |
| Classification | 95% | 5% | Batch classification |
| Summarization | 70% | 30% | Document compression |

### 5B. Data Sources for Workload Ratios

- **Aider leaderboard:** Actual prompt/completion token ratios per model (coding workload)
- **AA `outputTokensPerTask`:** Output token share per standardized task
- **LMSYS conversations:** Average conversation lengths (chat workload)
- **OpenRouter usage data:** If they expose aggregate input/output ratios

### 5C. Implementation Options

**Option A: Multiple blended prices** (recommended)
Show 2-3 blended prices per model:
- Blended (chat): 40/60 — current default
- Blended (coding): 20/80 — agent workloads
- Blended (RAG): 90/10 — retrieval workloads

The headline composite uses the chat blend. Other blends shown on model detail pages.

**Option B: User-adjustable blend**
Let users set their own input/output ratio with a slider. The blended price updates live. More interactive but harder to maintain a headline number.

**Option C: Usage-weighted blend**
If we can get workload distribution data, compute a market-weighted blend:
```
market_blend = 0.3 * chat_blend + 0.4 * coding_blend + 0.3 * rag_blend
```

---

## Phase 6: Context Length Pricing (Future)

### 6A. Current State

Google is the only major provider with explicit context-length-tiered pricing:
- Prompts <= 128K tokens: standard rate
- Prompts > 128K tokens: ~2x rate

Most others use flat per-token pricing regardless of context length.

### 6B. Potential Approaches

1. **Capture context tier pricing** from Google's page and surface it on model detail pages
2. **Compute context-adjusted price** for models where tier data exists
3. **Flag models with context pricing** in the table (like ZDR/EU flags)
4. **Add a "context cost" metric** showing price for max-context queries vs typical queries

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| AA changes RSC format | Lose intelligence scores + reasoning data | Phase 3 (multi-benchmark) eliminates single point of failure |
| OpenRouter changes API | Lose pricing + usage weights | Phase 2 (multi-source pricing) distributes risk |
| Provider blocks scraping | Lose direct pricing source | Rotate user agents, use API where available, maintain multiple sources |
| AA goes paid/closed | Lose all AA data | Phase 3 composite score works without AA (reduced coverage) |
| Benchmark gaming/contamination | Intelligence scores unreliable | Use anti-contamination benchmarks (LiveBench, SEAL) in the composite |

---

## Priority Order

1. **AA RSC extraction** (Phase 1B) — Biggest immediate win. Gets reasoning token counts, model parameters, cost-per-task. Replaces flat multipliers with real data.
2. **OpenRouter enhanced fields** (Phase 1A) — Easy win, same API, more data.
3. **Direct provider pricing** (Phase 2A) — Reduces OpenRouter dependency, adds price verification.
4. **Per-model reasoning multipliers** (Phase 4) — Uses data from 1B to replace flat multipliers.
5. **LMSYS Elo integration** (Phase 3A) — First step toward benchmark independence.
6. **Aider token data** (Phase 1C) — Validates reasoning data, adds coding workload blend.
7. **DeepInfra as secondary source** (Phase 2B) — Free, no auth, easy to add.
8. **Composite intelligence score** (Phase 3B) — Full benchmark independence.
9. **Workload-aware blends** (Phase 5) — Better blended pricing.
10. **Context length pricing** (Phase 6) — Nice to have, limited data.

---

## Full Data Source Catalog

See `inferenceindexer-data-sources-research.md` in the project root for the complete research document with every source, URL, API status, and extraction method.
