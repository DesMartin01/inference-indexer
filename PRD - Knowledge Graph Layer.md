# InferenceIndexer Knowledge Graph Layer — Product Requirements Document

**Version:** 0.1 (Draft)
**Date:** 2026-08-18
**Author:** Des Martin
**Status:** Draft for review

---

## 1. Vision

### 1.1 The Opportunity

InferenceIndexer currently stores pricing data as flat relational tables: models, providers, price_snapshots. This works for "show me the price of model X." It breaks down for multi-dimensional queries like:

> *"Which providers offer vision-capable reasoning models under $2/M with HIPAA compliance and sub-2s latency?"*

That query requires joining across models, providers, endpoints, price snapshots, latency snapshots, and a compliance attribute that doesn't exist yet. In SQL, it's a 5-table join with subqueries. In a graph, it's a single traversal: Provider -> OFFERS -> Model -> HAS_CAPABILITY -> Vision, -> HAS_PRICE -> <$2/M, -> HAS_COMPLIANCE -> HIPAA, -> HAS_LATENCY -> <2s.

The knowledge graph layer doesn't replace the relational database. It sits on top, structuring the relationships that already exist implicitly and adding the ones that don't exist yet.

### 1.2 Why Now

Two things make this the right time:

1. **The data is already rich enough to start.** 840 active models, 77 providers, 206K price snapshots, 222K endpoint records with uptime/latency data in JSONB. The relationships exist, they're just not structured as a graph.

2. **Competitors can't do this easily.** PricePerToken.com and Infrabase.ai both have flat model lists. Neither has the endpoint-level granularity (per-provider pricing, quantization, uptime) that II already collects. A graph layer turns that existing data depth into a structural moat.

### 1.3 What This Is NOT

- **Not a replacement for PostgreSQL.** The relational DB remains the source of truth. The graph is a derived layer, rebuilt from it.
- **Not a separate product.** The graph powers better queries inside the existing II site and API. Users don't "see a graph," they see better filters and richer model pages.
- **Not a knowledge graph in the enterprise ontology sense.** No OWL, no SPARQL, no reasoning engine. This is a practical property graph (Neo4j or similar) optimized for traversal queries.
- **Not a one-shot build.** The graph starts with what we have and grows as we add data dimensions.

---

## 2. Current State Assessment

### 2.1 What We Have

| Table | Rows | What It Captures |
|-------|------|-----------------|
| `models` | 1,012 (840 active) | Model metadata: name, provider, tier, modality, context length, AA score, reasoning flag, creator country |
| `providers` | 77 | Provider name, ZDR status, EU sovereignty, integration status |
| `price_snapshots` | 206,033 | Hourly per-model prices (input/output/blended), SIT score, source, raw JSONB from OpenRouter |
| `model_endpoints` | 222,545 | Per-provider endpoints: price, context length, quantization, uptime, latency, throughput (in JSONB) |
| `provider_latency_snapshots` | 594 | TTFT and throughput for 4 providers only (sparse) |
| `usage_weights` | 587 | Weekly token/request counts for 312 models (sparse) |
| `sit_index_values` | Daily | SIT-Composite and tier index values |
| `daily_tier_medians` | Daily | Tier-level median prices |

### 2.2 Structured Data We Already Collect But Don't Surface

The `raw_data` JSONB in `price_snapshots` and `model_endpoints` contains rich attributes that are currently unstructured:

**In price_snapshots.raw_data:**
- `benchmarks` (ArtificialAnalysis coding index, agentic index, intelligence index, arena ELOs)
- `architecture.input_modalities` / `output_modalities` (structured modality lists, not the simplified string in models.modality)
- `supported_parameters` (tools, reasoning_effort, structured_outputs, etc.)
- `hugging_face_id` (link to HuggingFace)
- `knowledge_cutoff` (model knowledge cutoff date)
- `reasoning` (mandatory flag, default effort, supported effort levels)
- `top_provider` (context length, max completion tokens, moderation flag)
- `default_parameters` (top_p, temperature defaults)

**In model_endpoints.raw_data:**
- `quantization` (fp4, fp8, etc.)
- `uptime_last_1d` / `uptime_last_5m` / `uptime_last_30m`
- `latency_last_30m` (TTFT in ms, mostly null)
- `throughput_last_30m` (tokens/sec, mostly null)
- `max_prompt_tokens` / `max_completion_tokens`
- `supports_implicit_caching`
- `supports_voice_cloning`

### 2.3 Data Gaps

| Gap | Current State | Impact on Graph |
|-----|---------------|-----------------|
| **Compliance certifications** (HIPAA, SOC2, GDPR, ISO 27001) | Not collected at all | Cannot filter by compliance, which is a primary enterprise use case |
| **Latency/throughput** | 4 providers only, mostly null in endpoints | Cannot power "sub-2s latency" queries meaningfully |
| **Model lineage** (GLM 5.2 -> GLM 5.3, GPT-5 -> GPT-5.1) | Not tracked | Cannot query "successor to" or "same family as" |
| **Provider relationships** (parent company, partnerships, white-label) | Not tracked | Cannot query "providers backed by same company" |
| **Structured capabilities** | Buried in JSONB | Cannot filter by capability without parsing JSON |
| **AA score coverage** | 33.6% of active models (282/840) | Most models have no quality signal |
| **Pricing context** (free tier, rate limits, volume discounts) | Not tracked | Cannot compare effective price including discounts |
| **Geographic availability** (regions, data residency) | Only EU sovereignty flag | Cannot filter by deployment region |
| **Model release dates** | `created` timestamp in raw_data, not structured | Cannot query "models released in last 30 days" |

---

## 3. Graph Schema

### 3.1 Node Types

```
(:Provider)
(:Model)
(:Modality)          // text, image, audio, video, file
(:Capability)         // reasoning, tool_use, structured_output, streaming, caching
(:Compliance)         // HIPAA, SOC2, GDPR, ISO27001, FedRAMP
(:Region)             // us-east, eu-west, ap-southeast, etc.
(:Tier)               // frontier, standard, budget, micro
(:PricingUnit)        // per_million_tokens, per_image, per_minute, per_character
(:Country)            // model creator country
(:Benchmark)          // ArtificialAnalysis, LMSYS Arena, etc.
```

### 3.2 Edge Types

```
(:Provider)-[:OFFERS]->(:Model)
(:Provider)-[:HOSTS]->(:Model)              // via endpoint, with quantization
(:Provider)-[:CERTIFIED_BY]->(:Compliance)
(:Provider)-[:OPERATES_IN]->(:Region)
(:Model)-[:HAS_MODALITY]->(:Modality)
(:Model)-[:HAS_CAPABILITY]->(:Capability)
(:Model)-[:IN_TIER]->(:Tier)
(:Model)-[:PRICED_IN]->(:PricingUnit)
(:Model)-[:CREATED_IN]->(:Country)
(:Model)-[:SCORED_BY]->(:Benchmark)          // with score as edge property
(:Model)-[:SUCCESSOR_OF]->(:Model)           // GLM 5.3 -> GLM 5.2
(:Model)-[:VARIANT_OF]->(:Model)            // quantized, distilled, etc.
(:Provider)-[:PARENT_OF]->(:Provider)        // org relationships
```

### 3.3 Edge Properties

Key edges carry properties that make queries useful:

**(:Provider)-[:OFFERS]->(:Model)**
- `input_price_per_m`, `output_price_per_m`, `blended_price_per_m`
- `source` (direct, aggregator, blended)
- `fetched_at` (timestamp, for temporal queries)
- `sit_adjusted_price`

**(:Provider)-[:HOSTS]->(:Model)**
- `quantization` (fp4, fp8, none, unknown)
- `uptime_1d` (percentage)
- `latency_ms` (TTFT)
- `throughput_tps` (tokens/sec)
- `max_context` (context length at this endpoint)
- `max_completion_tokens`

**(:Model)-[:SCORED_BY]->(:Benchmark)**
- `score` (numeric)
- `category` (coding, agentic, intelligence, overall)
- `date` (when measured)

### 3.4 Temporal Dimension

Every price and latency edge is timestamped. The graph supports temporal queries:
- "Show me all providers whose price for model X dropped >10% in 7 days"
- "Which models had latency degradation in the last 24 hours?"
- "Trace the price history of GLM 5.2 across all providers"

---

## 4. Data We Need to Add

### 4.1 Priority 1: Unstructured Data We Already Have

Extract from existing JSONB into structured graph properties. Zero new collection needed.

| Source | What to Extract | Effort |
|--------|----------------|-------|
| `price_snapshots.raw_data.architecture` | Structured input/output modalities | Low — parse existing JSON |
| `price_snapshots.raw_data.supported_parameters` | Capability nodes (tool_use, reasoning, structured_output, etc.) | Low |
| `price_snapshots.raw_data.reasoning` | Reasoning capability with effort levels | Low |
| `price_snapshots.raw_data.benchmarks` | Benchmark score nodes with category breakdown | Low |
| `price_snapshots.raw_data.knowledge_cutoff` | Model knowledge cutoff date | Low |
| `price_snapshots.raw_data.hugging_face_id` | Link to HuggingFace entity | Low |
| `model_endpoints.raw_data.quantization` | Quantization on HOSTS edge | Low |
| `model_endpoints.raw_data.uptime_*` | Uptime on HOSTS edge | Low |
| `model_endpoints.raw_data.latency_last_30m` | Latency on HOSTS edge | Low (but mostly null) |
| `model_endpoints.raw_data.throughput_last_30m` | Throughput on HOSTS edge | Low (but mostly null) |
| `model_endpoints.raw_data.max_completion_tokens` | Max output on HOSTS edge | Low |

### 4.2 Priority 2: New Data Collection Required

These are the data gaps that make the graph genuinely useful for enterprise queries.

#### 4.2.1 Compliance Certifications

**What:** HIPAA, SOC2 Type II, GDPR, ISO 27001, FedRAMP, PCI DSS

**Source:** Provider websites, public compliance registries, provider API documentation. Most providers publish their compliance posture on a trust/security page.

**Collection method:** Manual research for top 30 providers initially, then a scraper that checks provider trust pages quarterly. Could also accept self-attestation via the existing provider submission form.

**Effort:** Medium. ~2 days manual research for top 30 providers, plus a recurring scraper.

**Why it matters:** Compliance is the #1 enterprise filter. "Is this provider HIPAA-compliant?" is a question every healthcare/finance buyer asks. No inference price comparison site currently structures this.

#### 4.2.2 Latency and Throughput (Structured Probing)

**What:** Time-to-first-token (TTFT) and tokens-per-second (TPS) per provider per model.

**Current state:** `provider_latency_snapshots` has data for 4 providers only. `model_endpoints.raw_data` has latency/throughput fields but they're mostly null (OpenRouter doesn't populate them consistently).

**Collection method:** Active probing. Send a standardized prompt (e.g., "Summarize the following:" + 500-token input) to each provider's API and measure TTFT and TPS. Run hourly. This requires API keys for each provider or use of OpenRouter as a proxy.

**Effort:** Medium-high. Need API access (keys or OpenRouter credits), a probe script, and storage. ~3-5 days to build, then ongoing API cost (~$50-100/month for probing).

**Why it matters:** "Sub-2s latency" is a real production constraint. Without this data, the graph can answer price and capability queries but not performance queries.

#### 4.2.3 Model Lineage

**What:** Parent/successor relationships between models. GLM 5.3 succeeds GLM 5.2. DeepSeek V4 Flash succeeds V3. GPT-5.1 succeeds GPT-5.

**Source:** Provider release notes, model documentation pages, HuggingFace model cards.

**Collection method:** Semi-automated. Parse model names for version patterns (X.Y.Z), cross-reference with provider release notes. Manual verification for ambiguous cases.

**Effort:** Low-medium. ~1-2 days to build the initial lineage for the top 100 models, then maintain on new releases.

**Why it matters:** "Show me the successor to GLM 5.2" and "show me all models in the GLM family" are natural discovery queries.

#### 4.2.4 Provider Organization Relationships

**What:** Parent company, acquisitions, partnerships, white-label arrangements. Example: Together AI hosts models from multiple creators. Alibaba hosts Zhipu models.

**Source:** Provider about pages, Crunchbase, public announcements.

**Collection method:** Manual research for top 30 providers. Low volume, low frequency.

**Effort:** Low. ~1 day initial, quarterly review.

**Why it matters:** "Show me all providers backed by the same parent company" and "which providers actually host Zhipu models?" are organizational queries.

#### 4.2.5 Geographic Regions

**What:** Which regions each provider operates in (us-east, eu-west, ap-southeast, etc.).

**Source:** Provider documentation, API base URLs, existing `is_eu_sovereign` flag.

**Collection method:** Manual research for top 30 providers, then scrape provider docs.

**Effort:** Low. ~1 day.

**Why it matters:** Data residency requirements constrain provider choice for EU and regulated industries.

### 4.3 Priority 3: Nice-to-Have

| Data | Source | Effort | Why |
|------|--------|--------|-----|
| Volume discount tiers | Provider pricing pages | Medium | "Effective price at 100M tokens/month" |
| Free tier limits | Provider docs | Low | "Which models have a free tier?" |
| Rate limits | Provider docs | Low | "Which providers allow 100K req/min?" |
| Model release dates | Provider release notes | Low | "Models released in last 30 days" |
| Context caching pricing | Provider pricing pages | Low | "Which models support prompt caching?" |
| Fine-tuning availability | Provider docs | Low | "Which models support fine-tuning?" |
| Function calling quality benchmarks | Public benchmarks | Medium | Beyond yes/no capability, how well does it work? |

---

## 5. Query Examples (What Becomes Possible)

### 5.1 Enterprise Procurement

```
"Which providers offer vision-capable reasoning models under $2/M 
with HIPAA compliance and sub-2s TTFT?"
```

Graph traversal: Provider -> CERTIFIED_BY -> HIPAA, -> HOSTS -> Model -> HAS_MODALITY -> vision, -> HAS_CAPABILITY -> reasoning, WHERE blended_price < $2 AND latency < 2000ms

### 5.2 Model Discovery

```
"Show me all successors to GLM 5.2 and their current cheapest provider"
```

Graph traversal: Model(GLM 5.2) <- SUCCESSOR_OF - Model(?), then Model -> OFFERS <- Provider ORDER BY price

### 5.3 Competitive Analysis

```
"Which providers host DeepSeek V4 Flash, and what's the price spread?"
```

Graph traversal: Model(DeepSeek V4 Flash) <- HOSTS - Provider, with price on edge, ORDER BY price, compute spread

### 5.4 Compliance Scoping

```
"Show me all models from EU-sovereign providers that support structured output"
```

Graph traversal: Provider -> OPERATES_IN -> Region(EU) -> <- HOSTS - Model -> HAS_CAPABILITY -> structured_output

### 5.5 Price Intelligence

```
"Which models had >20% price drops in the last 7 days, and which 
providers dropped first?"
```

Temporal traversal: Model -> OFFERS -> Provider, compare price at T-7d vs T, filter >20%, order by first change timestamp

### 5.6 Capability Matrix

```
"What can I get for under $0.50/M? Show all models, their capabilities, 
and which providers offer them at that price point."
```

Graph traversal: Model WHERE min_price(blended) < $0.50 -> HAS_CAPABILITY -> ? -> OFFERS <- Provider

---

## 6. Technical Approach

### 6.1 Graph Database Selection

| Option | Pros | Cons | Fit |
|--------|------|------|-----|
| **Neo4j** | Purpose-built, Cypher query language, rich ecosystem, good Python driver | Separate DB to maintain, resource overhead | Best for pure graph queries |
| **Apache AGE** (PostgreSQL extension) | Runs inside existing Postgres, no new infra, SQL + Cypher | Newer, less mature, smaller community | Best for incremental adoption |
| **PostgreSQL with JSONB + recursive CTEs** | No new tech, already have the data | Recursive CTEs are slow for deep traversals, not a real graph | Good enough for shallow queries |
| **DuckDB in-memory** | Fast analytics, embedded, handles graph-like queries well | Not persistent, rebuild on each run | Good for batch analytics |

**Recommendation:** Start with Apache AGE (PostgreSQL extension). It keeps everything in one database, uses the existing Supabase connection, and Cypher queries work alongside SQL. If query complexity outgrows AGE, migrate to Neo4j. The graph schema is the same either way.

### 6.2 Build Pipeline

```
PostgreSQL (source of truth)
    |
    v
ETL Script (Python, scheduled hourly)
    |
    v
Graph Tables (Apache AGE or Neo4j)
    |
    v
API Layer (new /v1/graph/ endpoints)
    |
    v
Frontend (new filter UI, model relationship views)
```

### 6.3 ETL Design

The ETL script runs hourly (aligned with the existing price snapshot cron) and:

1. Reads latest prices from `price_snapshots` (via `latest_prices` matview)
2. Reads endpoint data from `model_endpoints`
3. Extracts structured attributes from `raw_data` JSONB
4. Reads compliance/region data from new tables (to be created)
5. Rebuilds/updates graph nodes and edges
6. Marks stale edges as inactive (don't delete, preserve history)

The ETL is idempotent: running it twice produces the same graph state.

### 6.4 API Design

New API endpoints that expose graph queries:

| Endpoint | Purpose |
|----------|---------|
| `GET /v1/graph/search` | Multi-dimensional filter query (the "which providers offer..." query) |
| `GET /v1/graph/model/:id/relationships` | Model lineage, variants, same-family models |
| `GET /v1/graph/provider/:name/models` | All models from a provider with capabilities and prices |
| `GET /v1/graph/compare` | Side-by-side model comparison across all dimensions |
| `GET /v1/graph/matrix` | Capability matrix at a given price point |

### 6.5 Frontend Changes

- **Advanced filter panel** on `/models` page: multi-select for modality, capability, compliance, region, price range, latency range, reasoning support. Each filter narrows the graph traversal.
- **Model relationship view** on model detail pages: visual showing predecessor/successor, variants, same-family models, and their current prices.
- **Provider comparison view**: table showing providers side-by-side with their compliance posture, regions, latency, and price range.

---

## 7. Phasing

### Phase 0: Data Extraction (Week 1-2)

**Goal:** Extract structured data from existing JSONB into proper columns/tables.

- Extract `architecture.input_modalities` / `output_modalities` into a `model_modalities` table
- Extract `supported_parameters` into a `model_capabilities` table
- Extract `reasoning` config into model fields (mandatory, default_effort, supported_efforts)
- Extract `benchmarks` into a `model_benchmarks` table (benchmark_name, category, score, date)
- Extract `knowledge_cutoff` and `hugging_face_id` into model columns
- Extract endpoint `quantization`, `uptime_*`, `latency`, `throughput` into `model_endpoints` columns

**Deliverable:** All existing JSONB data available as structured columns/tables. No new collection. The relational DB now has the same data, but queryable.

### Phase 1: Compliance and Region Data (Week 2-3)

**Goal:** Collect the missing high-value enterprise data.

- Create `provider_compliance` table (provider, certification, verified_at, source_url)
- Create `provider_regions` table (provider, region, endpoint_url)
- Manual research for top 30 providers by model count
- Add compliance/region fields to provider submission form

**Deliverable:** Compliance and region data for 30+ providers, collected and structured.

### Phase 2: Graph Layer (Week 3-5)

**Goal:** Build the graph from structured data and expose it via API.

- Install Apache AGE on Supabase (or stand up Neo4j instance)
- Build ETL script: relational -> graph, scheduled hourly
- Implement `GET /v1/graph/search` endpoint (the flagship multi-dimensional query)
- Implement `GET /v1/graph/model/:id/relationships` endpoint

**Deliverable:** Working graph API that answers the example queries from Section 5.

### Phase 3: Model Lineage (Week 5-6)

**Goal:** Add model relationship edges.

- Build lineage detection script (version pattern matching + manual verification)
- Create `model_relationships` table (model_id, related_model_id, relationship_type)
- Add `SUCCESSOR_OF` and `VARIANT_OF` edges to graph
- Implement `GET /v1/graph/model/:id/relationships` endpoint

**Deliverable:** Model family trees and successor queries working.

### Phase 4: Latency Probing (Week 6-8)

**Goal:** Fill the biggest data gap with active measurement.

- Build probe script: standardized prompt to each provider's API, measure TTFT and TPS
- Need API keys or OpenRouter credits for probing
- Run hourly, store in `provider_latency_snapshots` (expand beyond current 4 providers)
- Add latency data to HOSTS edges in graph

**Deliverable:** Latency/throughput data for 20+ providers, feeding into graph queries.

### Phase 5: Frontend Integration (Week 8-10)

**Goal:** Surface graph queries in the UI.

- Advanced filter panel on `/models` page (modality, capability, compliance, price, latency)
- Model relationship view on model detail pages
- Provider comparison view

**Deliverable:** Users can filter models by multiple dimensions without writing Cypher.

---

## 8. Success Metrics

| Metric | Target (6 months) | How to Measure |
|--------|-------------------|----------------|
| Graph query API usage | 20% of total API calls | API request log |
| Advanced filter adoption | 30% of /models page visitors use multi-filter | Frontend analytics |
| Compliance data coverage | 50+ providers with at least 3 certifications | provider_compliance table |
| Latency data coverage | 30+ providers with hourly TTFT | provider_latency_snapshots |
| Model lineage coverage | 200+ models with successor/variant relationships | model_relationships table |
| Enterprise API signups | 10+ from companies citing compliance filtering | API user registrations |

---

## 9. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Apache AGE maturity | Queries may hit bugs or performance limits | Design ETL to be graph-DB-agnostic. Can swap to Neo4j if needed. |
| Latency probing cost | API charges for probing 30+ providers hourly | Use OpenRouter credits (already have access). Probing at off-peak hours. Start with 10 providers. |
| Compliance data accuracy | Wrong compliance data could mislead buyers | Source from official provider trust pages. Add "verified_at" date. Link to source URL. Accept self-attestation via submission form with "pending verification" status. |
| Graph query performance | Deep traversals could be slow | Limit traversal depth. Cache common queries. Use matviews for pre-computed subgraphs. |
| Data staleness | Graph edges go stale between ETL runs | Run ETL hourly aligned with price snapshots. Add "last_synced" timestamp to graph metadata. |

---

## 10. Open Questions

1. **Graph DB choice:** Apache AGE (in Postgres) vs Neo4j (separate instance)? AGE keeps things simple but may hit limits. Neo4j is purpose-built but adds infrastructure. Decision needed before Phase 2.

2. **Latency probing access:** Do we use OpenRouter as a proxy for all providers, or get direct API keys? OpenRouter is simpler but measures OpenRouter's routing latency, not the provider's direct latency. Direct keys are more accurate but require 30+ accounts.

3. **Compliance data sourcing:** Manual research only, or build a scraper? Manual is more accurate but doesn't scale. Scraper risks collecting outdated info. Hybrid: manual for top 30, scraper for the rest.

4. **Frontend scope:** Full visual graph explorer, or just better filter panels? A visual graph explorer (nodes and edges rendered) is impressive but expensive to build and may confuse non-technical users. Filter panels are more practical. Could do both: filter panels as default, graph view as a toggle.

5. **API pricing:** Are graph query endpoints free (like current API) or premium? The multi-dimensional query is more valuable than a simple price lookup. Could be a paid tier differentiator.

6. **Competitive response:** If PricePerToken or Infrabase add similar filtering, what's the moat? Answer: depth of data. The graph is only as good as the edges. II already has endpoint-level pricing and uptime data that competitors don't. The graph makes that depth accessible. The moat is data collection, not the graph structure itself.
