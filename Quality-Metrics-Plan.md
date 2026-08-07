# InferenceIndexer Quality Metrics Plan

**Created:** August 6, 2026
**Status:** Planning (no implementation yet)
**Goal:** Capture latency, reliability, and hardware data to complement price-only index

## Problem

Current index is 1D: price per million tokens. But a developer choosing between two providers offering the same model at the same price is really choosing on:

1. **Latency** - Time to First Token (TTFT), tokens per second
2. **Reliability** - Uptime %, error rate, latency consistency (p50 vs p99)
3. **Hardware** - GPU generation (H100 vs B300 vs TPU v6)

A model at $1.50/M with 98% uptime and 3s TTFT is not cheaper than the same model at $2/M with 99.9% uptime and 200ms TTFT.

## Data Sources

| Metric | Source | Effort | Status |
|--------|--------|--------|--------|
| TTFT | Own probes (send prompt, measure) | Medium | Not started |
| Tokens/sec | Same probe (measure stream rate) | Medium | Not started |
| Uptime | Own probes + provider status pages | Medium | Not started |
| Error rate | Probe failures (429s, 500s, timeouts) | Medium | Not started |
| GPU type | Inferred from throughput, or provider docs | Hard | Not started |
| Latency p99 | Own probes (need enough samples) | Medium | Not started |

Artificial Analysis already measures latency and throughput per model, but not per provider. Provider-level granularity is the gap.

## Implementation Phases

### Phase 1: Probe Runner (Weeks 1-3)
- Build a simple probe that sends `"Hello"` to every provider endpoint hourly
- Records: TTFT, tokens/sec, success/failure, HTTP status
- Store in `provider_latency_snapshots` table
- 30 days of data needed before surfacing publicly

### Phase 2: Surface on Model Detail Pages (Weeks 4-5)
- Each endpoint row gets latency and uptime columns
- Show 7-day and 30-day averages
- Low effort once data exists, high signal for users

### Phase 3: Provider Quality Score (Weeks 6-8)
- Composite score weighting price, intelligence, latency, reliability
- `Value Score = f(price, intelligence, ttft, throughput, uptime)`
- Adjusted price: cheaper provider with 98% uptime penalised vs 99.9% uptime provider

### Phase 4: GPU Tracking (Future)
- Infer GPU generation from throughput patterns
- Cross-reference with provider documentation
- Surface as metadata, not a scored metric

## Future Formula Direction

Current: `Cost / IQ = Blended Price x (40 / AA Score)`

Future multi-dimensional:
```
Value Score = f(price, intelligence, ttft, throughput, uptime, hardware)
```

A model at $2/M with 99.9% uptime and 200ms TTFT beats $1.50/M with 98% uptime and 3s TTFT. The index should reflect that.

## Key Decisions Needed

- Probe frequency (hourly vs every 15 min)
- How many providers to probe (all 70+ or top 20 by traffic)
- Whether to publish raw latency data or only aggregated scores
- How to weight reliability vs price in the composite
- Whether GPU type is a filter or a score component

## Dependencies

- Probe infrastructure (can run on existing API server)
- 30 days minimum data before publishing (credibility floor)
- Provider rate limits (some may block frequent probing)
