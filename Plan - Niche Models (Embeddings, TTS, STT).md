# Plan: Niche Model Types (Embeddings, TTS, STT, etc.)

## Strategy

Two-part approach:

### Part 1: Collect All Model Pricing Data
Scrape and store pricing for ALL model types we can find, regardless of whether they appear on the website:
- Embeddings (Jina, Voyage, OpenAI, Google, Cohere, Nomic)
- TTS (text-to-speech)
- STT (speech-to-text)
- Rerankers
- Image generation
- Any other niche modalities

**Purpose:** Makes the API more valuable as a comprehensive data layer. Gives us options to surface new categories later without rebuilding the pipeline. The data collection is decoupled from the website display.

### Part 2: Website Display - /model-type/ Directory
- Add "Model Type" link in the footer → `/model-type/`
- This page is a directory of model categories (like a category index)
- Initially has one link: "Embedding Models" → `/embeddings`
- As new categories are ready (TTS, STT, etc.), they get added to `/model-type/`
- Main nav stays clean - no clutter

## Phase 1: Embeddings (First Category)

### Data Collection
**Already have:**
- Jina direct API connector: 13 embedding models, $0.05/M tokens, scraped hourly
- Jina models in DB with `modality = 'embedding'`

**Need to build scrapers for:**
| Provider | Models | Source | $/M tokens | Scraping Method |
|----------|--------|--------|------------|-----------------|
| Voyage AI | ~15 | docs.voyageai.com/docs/pricing | $0.02-$0.18 | Markdown table parser (like Fireworks/Groq pattern) |
| Google | 2 | ai.google.dev/gemini-api/docs/pricing | $0.15 | Server-rendered HTML |
| OpenAI | 3 | platform.openai.com/api/pricing | $0.02-$0.13 | Cloudflare blocked - manual entry or browser scrape |
| Cohere | ~3 | cohere.com/pricing | ~$0.10 | JS-rendered - browser scrape or manual |
| Nomic | 2 | nomic.ai/pricing | ~$0.08 | JS-rendered - browser scrape or manual |

**Total: ~35-40 embedding models across 6 providers**

### Privacy Data (Differentiator)
- Populate ZDR/EU sovereign flags for embedding providers
- Jina should be EU=True (German company, currently False in DB)
- Research ZDR offerings from Cohere, Voyage, Nomic
- This is the key differentiator vs other pricing sites

### /model-type/ Page
Simple directory page:
- Heading: "Model Types"
- Intro: "InferenceIndexer tracks pricing across multiple model types. Not all are displayed on the homepage."
- Link: "Embedding Models →" → /embeddings
- (Future: TTS, STT, Rerankers, Image, etc.)

### /embeddings Page
- Heading: "Embedding Models"
- Intro: "Live pricing for AI embedding models. Prices per million tokens."
- Table columns: Model | Creator | Dimensions | Max Context | $/M tokens | Sources | ZDR | EU Infra
- No SIT Score, no AA Score, no tiers, no medals
- Sortable by price, dimensions, context
- Same dark theme, same card aesthetic
- Footer link back to /model-type/

### /embeddings Data Pipeline
- New DB table or filter on existing `models` table by `modality = 'embedding'`
- New API endpoint: `GET /v1/embeddings` or filter on existing `/v1/models?modality=embedding`
- Price stored as `input_price_per_m` (no output price for embeddings)
- No SIT calculations, no tier assignment

## Implementation Order (when ready)
1. Build embedding pricing scrapers (Voyage, Google, OpenAI, Cohere, Nomic)
2. Populate privacy data for embedding providers
3. Add API endpoint for embeddings
4. Build /model-type/ directory page
5. Build /embeddings table page
6. Add "Model Type" to footer

## Key Decisions
- Unit: $/M tokens (standard across all embedding providers)
- No SIT-Composite for embeddings (no quality-adjusted pricing without intelligence benchmark)
- No AA Score (no equivalent for embeddings)
- No tiers (pricing doesn't stratify the same way)
- Privacy columns are front and centre - this is the differentiator
- Collect ALL modalities in the pipeline, even if not displayed on the site
