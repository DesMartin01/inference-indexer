# Standard Inference Token (SIT) — Methodology Specification

**Version:** 0.1 (Draft)
**Date:** 2026-08-03
**Author:** Des Martin, InferenceIndexer
**Status:** Draft for review

---

## 1. Purpose

The Standard Inference Token (SIT) is a standardized unit of AI inference output that enables:

1. **Price comparison** across models and providers on a like-for-like basis
2. **Composite indices** that track inference price movements over time
3. **Futures settlement** — a reference price that derivatives contracts can settle against
4. **Benchmarking** — "am I paying above or below market rate for inference?"

The SIT is to AI inference what WTI is to crude oil, what the CPI is to consumer prices, and what the S&P 500 is to equities: a single, trusted reference point.

---

## 2. Core Definition

### 2.1 Unit

**1 SIT = 1 million tokens of inference at a defined quality standard.**

"Tokens" refers to the standard industry unit of LLM inference, as measured by each provider's tokenizer. While tokenizers differ between models, the "million tokens" convention is universally adopted and provides sufficient standardization for pricing purposes.

### 2.2 Pricing Components

Every SIT-eligible model has three published prices:

| Component | Definition |
|-----------|-----------|
| **Input price** | Cost per million input (prompt) tokens |
| **Output price** | Cost per million output (completion) tokens |
| **Blended price** | Weighted average: 40% input + 60% output |

**Rationale for 40/60 blend:** Most production inference workloads generate more output tokens than input tokens (generation tasks, coding, summarization). The 60% output weighting reflects this. This ratio is configurable and will be refined as real-world usage data becomes available.

### 2.3 Quality Standard

The SIT does not assume all tokens are equal. Models are grouped into **quality tiers** based on demonstrated capability:

| Tier | Definition | Intelligence Threshold | Current Examples |
|------|-----------|----------------------|-----------------|
| **SIT-Frontier** | Top-tier models from frontier labs | AA Index 55+ | GPT-5.6, Claude Opus 5, Gemini 3.6, Grok 4.5 |
| **SIT-Standard** | Mid-tier models suitable for production | AA Index 30-55 | GPT-4o, DeepSeek V4, GLM-5.2, Mistral Large |
| **SIT-Budget** | Low-cost models for high-volume tasks | AA Index < 30 | Gemma 3, Llama 3.2, Qwen Flash, Mistral Small |
| **SIT-Micro** | Ultra-cheap models for simple tasks | Below benchmark | 1B-8B parameter models |

**Quality threshold source:** The Artificial Analysis Intelligence Index (https://artificialanalysis.ai) is used as an independent, third-party benchmark. Models without a published AA Index score are excluded from SIT-tiered indices but may be tracked individually.

---

## 3. Index Calculation

### 3.1 Tier Indices

Each quality tier has its own composite index:

| Index | What It Tracks | Current Median Price |
|-------|---------------|---------------------|
| **SIT-Frontier** | Average blended price of all Frontier-tier models | ~$35-50/M |
| **SIT-Standard** | Average blended price of all Standard-tier models | ~$1.25-4.40/M |
| **SIT-Budget** | Average blended price of all Budget-tier models | ~$0.10-0.42/M |
| **SIT-Composite** | Volume-weighted blend of all tiers | ~$2-5/M |

### 3.2 Weighting Methodology

**Phase 1 (Launch — current):** Equal weighting across all models within each tier.

**Phase 2 (3-6 months):** Capacity-weighted. Models weighted by:
- Context window (proxy for capability)
- Provider size (proxy for market share)

**Phase 3 (6-12 months):** Volume-weighted. Models weighted by actual API transaction volume, sourced from:
- Provider-reported volumes (where available)
- OpenRouter routing volumes (where available)
- Estimation model (where data is unavailable)

### 3.3 Calculation Frequency

| Frequency | What happens |
|-----------|-------------|
| **Hourly** | Pull pricing from all sources, update database |
| **Daily** | Calculate daily SIT indices, publish at 00:00 UTC |
| **Monthly** | Review tier composition, add/remove models, publish methodology report |

### 3.4 Daily Index Price

The published SIT-Composite price is:

```
SIT-Composite = Σ(blended_price_i × weight_i) / Σ(weight_i)

where:
  blended_price_i = 0.4 × input_price_i + 0.6 × output_price_i
  weight_i = 1.0 (Phase 1: equal weight)
```

### 3.5 Base Date and Rebaselining

- **Base date:** 2026-08-03 (first publication)
- **Base value:** SIT-Composite = 1000 index points
- **Rebaselining:** Only on methodology changes (tier redefinition, weighting change). All rebaselining events published with full explanation.

---

## 4. Data Sources

### 4.1 Primary Sources

| Source | Type | Coverage | Frequency |
|--------|------|----------|-----------|
| OpenRouter API | Aggregator | 315+ models | Hourly |
| OpenAI pricing page | Direct provider | ~15 models | Daily scrape |
| Anthropic pricing page | Direct provider | ~10 models | Daily scrape |
| Google AI Studio | Direct provider | ~20 models | Daily scrape |
| DeepSeek pricing page | Direct provider | ~5 models | Daily scrape |
| Together AI API | Aggregator | ~80 models | Hourly |
| Fireworks AI API | Aggregator | ~50 models | Hourly |
| Groq API | Aggregator | ~15 models | Hourly |

### 4.2 Source Hierarchy

When a model is available from multiple sources, priority order:
1. **Direct provider** (e.g. openai.com pricing for GPT-5.6)
2. **Aggregator with lowest markup** (e.g. OpenRouter base price, excluding their routing fee)
3. **Community submission** (verified against at least one other source)

### 4.3 Data Quality

- Every price point stores: timestamp, source URL, raw price, normalized price, model ID, tier
- Automated anomaly detection: if a price moves >50% in one hour, flagged for review
- Manual review of all tier additions/removals
- Full audit trail: every index calculation is reproducible from stored raw data

---

## 5. Model Eligibility

### 5.1 Inclusion Criteria

A model is eligible for SIT tracking if:

1. **Publicly priced** — pricing is published on a public webpage or API without authentication
2. **Pay-per-token** — priced per million tokens (not per second, per image, per request)
3. **Text or multimodal** — text generation, code generation, or multimodal (text+image) output
4. **Accessible** — available via API to any developer (not private/internal only)
5. **Benchmarked** — has a published Artificial Analysis Intelligence Index score (for tiering)

### 5.2 Exclusion Criteria

A model is excluded if:

1. **Free only** — no paid tier (cannot be priced)
2. **Per-request pricing** — priced per API call, not per token
3. **Private/bespoke** — pricing requires enterprise sales contact
4. **Deprecated** — provider has announced end-of-life
5. **Image/audio-only** — no text generation capability

### 5.3 Tier Assignment

Models are assigned to tiers based on their Artificial Analysis Intelligence Index score:

```
SIT-Frontier: AA Index >= 55
SIT-Standard: 30 <= AA Index < 55
SIT-Budget:   15 <= AA Index < 30
SIT-Micro:    AA Index < 15 or no score
```

Tier assignments are reviewed monthly. A model that improves its benchmark score may move up; a model that is superseded may move down.

---

## 6. Historical Data

- All price snapshots stored from first publication (2026-08-03)
- Full reproducibility: every historical SIT index value can be recalculated from stored raw data
- Historical data available via API:
  - Free tier: Daily SIT-Composite close, 30-day history
  - Paid tier: All tiers, hourly granularity, full history, all raw model prices

---

## 7. Publication

### 7.1 What Gets Published

| Output | Frequency | Channel | Access |
|--------|-----------|---------|--------|
| SIT-Composite close | Daily | Website, API, Telegram | Free |
| Tier index closes (Frontier, Standard, Budget) | Daily | Website, API | Free |
| Per-model prices | Hourly | Website, API | Free |
| Historical chart data | Daily | Website, API | Free (30 days) |
| Full historical data | On request | API | Paid |
| Methodology report | Monthly | Website | Free |
| Tier composition changes | As needed | Website | Free |

### 7.2 API Endpoints (proposed)

```
GET /api/v1/sit/composite/latest
GET /api/v1/sit/composite/history?days=30
GET /api/v1/sit/tier/frontier/latest
GET /api/v1/sit/tier/standard/latest
GET /api/v1/sit/tier/budget/latest
GET /api/v1/models?tier=standard&sort=price
GET /api/v1/models/{model_id}/history
```

---

## 8. Governance

### 8.1 Methodology Changes

Any change to this methodology document triggers:
1. 14-day public comment period
2. Full version increment (0.1 → 0.2)
3. Recalculation of historical indices using new methodology
4. Publication of both old and new values for 30-day overlap

### 8.2 Conflict of Interest

- InferenceIndexer is an independent price reporting agency
- InferenceIndexer does not provide inference services
- InferenceIndexer does not take positions in inference futures or any related derivatives
- All data sources are public and verifiable
- Methodology is fully transparent and reproducible

---

## 9. Limitations

### 9.1 Known Limitations

1. **Tokenizer differences:** Different models use different tokenizers. A "million tokens" from GPT-5.6 processes more text than a million tokens from Llama 3.2. This is a known imprecision, analogous to different crude oil grades having different energy densities. The SIT accepts this imprecision as the cost of standardization.

2. **Volume data:** Phase 1 uses equal weighting because real-world transaction volumes are not publicly available. This means the index may over-represent niche models with low usage.

3. **Aggregator dependency:** Many prices are sourced via OpenRouter. If OpenRouter changes its pricing model or goes offline, coverage may temporarily decrease.

4. **Quality benchmark dependency:** Tier assignments depend on the Artificial Analysis Intelligence Index, which is a third-party benchmark. Changes to their methodology affect our tier composition.

5. **Excluded models:** Models with per-request pricing (e.g. some fine-tuning endpoints) or enterprise-only pricing are not tracked. The SIT covers the pay-per-token market only.

### 9.2 Future Enhancements

1. **Volume weighting:** Incorporate real API call volumes as data becomes available
2. **Latency-adjusted pricing:** Factor in response speed (tokens/second) into the index
3. **Cache pricing:** Track cached input token pricing separately (OpenAI, Google offer discount tiers)
4. **Batch pricing:** Track batch API pricing (typically 50% cheaper than real-time)
5. **Regional pricing:** Track pricing by region (US, EU, Asia) where providers differentiate

---

## 10. Open Questions

- [ ] Should image generation models be included (priced per image, not per token)?
- [ ] Should embedding models be tracked (priced per token but no "output")?
- [ ] How to handle providers who offer both token pricing and per-second pricing?
- [ ] Should we weight by provider reliability/uptime?
- [ ] What is the right input/output blend ratio? (Currently 40/60, needs empirical validation)
- [ ] Should we publish a "SIT-spread" (Frontier vs Budget) as a separate metric?
