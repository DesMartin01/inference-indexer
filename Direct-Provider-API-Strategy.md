# InferenceIndexer Direct Provider API Strategy

**Created:** August 7, 2026
**Updated:** August 8, 2026
**Status:** 8 connectors live (5 no-auth + 3 priced/catalog direct incl. Fireworks), 11 connectors built (awaiting API keys)

## The Problem

OpenRouter is our sole data source for endpoint pricing. It only lists what each provider chooses to expose through their OpenRouter integration. We proved this with Venice: their API has 105 models, OpenRouter shows 31. That's 70% of Venice's catalog invisible.

## The Opportunity

Going direct to provider APIs gives us three things OpenRouter can never match:

1. **Completeness** - every model the provider offers, not just OpenRouter-listed ones
2. **Metadata depth** - capabilities, quantization, context limits, cache pricing, model provenance
3. **Performance data** - once we build probes, we measure TTFT/throughput/uptime per provider endpoint

## The Moat

Each provider has a different API format. Building and maintaining those connectors is work, but it's also the barrier to entry. Anyone can scrape OpenRouter. Nobody else is going direct to 70+ provider APIs.

## Live Pricing Scrapers (2026-08-08)

Some provider APIs return catalog-only data (no per-model pricing) even with a key. For those, the authoritative pricing lives on the provider's docs/marketing page. We now scrape those pages and feed the prices through the same direct-connector pipeline path:

| Provider | Scrape source | Models | Status |
|---|---|---|---|
| Fireworks | `docs.fireworks.ai/serverless/pricing.md` | 17 | LIVE |
| Groq | `console.groq.com/docs/models.md` | 8 | LIVE |
| Together | `docs.together.ai/docs/serverless/models.md` | 23 | LIVE |
| TensorX | `tensorx.ai/models/` (WordPress server HTML) | 18 | LIVE |

**Architecture note — canonical model IDs:** every direct connector must emit IDs in our **lowercase canonical form** (`moonshotai/kimi-k3`, `z-ai/glm-5.2`) via `canonical_model_id()`. Connectors that used provider-native mixed-case IDs (DeepInfra, Novita, Jina, SambaNova) created case-duplicate model rows; this was fixed by normalizing all connectors to lowercase and consolidating the dupes. A provider model id that already matches an existing canonical row merges onto it (source_count>1); genuinely-new models get created lowercase.

## API Key Management

Jentic One is installed on this VPS (`~/.jentic/`, port 8001). Admin account: frank@desmartin.io. Credential management helper: `jentic_credentials.py`. API keys are stored encrypted and injected at runtime via the Jentic broker. The pipeline's `get_provider_api_key()` function tries: env var -> ~/.hermes/.env -> Jentic One.

## Connectors

### Live (No Auth Required)

| Provider | API URL | Models | Pricing | Notes |
|----------|---------|--------|---------|-------|
| OpenRouter | openrouter.ai/api/v1/models | 400 | Yes | Primary source, all models |
| Venice | api.venice.ai/api/v1/models | 105 | Yes | 93 unique models, 21 not on OpenRouter. Hourly refresh. Self-hosted/proxied via privacy field. |
| DeepInfra | api.deepinfra.com/v1/openai/models | 98 | Yes | 85 exclusive models. Hourly refresh. All self-hosted. |
| Novita | api.novita.ai/v3/openai/models | 105 | Yes | Prices ÷10000 for $/M. All self-hosted. |
| SambaNova | api.sambanova.ai/v1/models | 6 | Yes | Per-token pricing (×1M for $/M). Self-hosted. |
| Jina | api.jina.ai/v1/models | 29 | Yes | Embeddings/rerankers/VLM. Per-token pricing. |
| Inference.net | api.inference.net/v1/models | 37 | No | Catalog only (no pricing endpoint). |
| AI/ML API | api.aimlapi.com/v1/models | 364 | No | Catalog only. 901 total models, 364 text/chat. Aggregator. |

### Built (Awaiting API Keys)

| Provider | API URL | Auth | Models (est.) | Pricing | Notes |
|----------|---------|------|---------------|---------|-------|
| Together AI | api.together.xyz/v1/models | Bearer | ~80 | Yes | Per-$M pricing. Connector built. |
| Groq | api.groq.com/openai/v1/models | Bearer | ~30 | No | Catalog only. Connector built. |
| Fireworks AI | api.fireworks.ai/inference/v1/models | Bearer | 20 | Docs page only | Connector LIVE (2026-08-08). API is catalog-only (20 models, NO pricing field). Prices sourced from docs.fireworks.ai/serverless/pricing.md via `fireworks_pricing.py` scraper. 17 priced endpoints + 20 catalog models. |
| Cerebras | api.cerebras.ai/v1/models | Bearer | ~10 | No | Catalog only. Connector built. |
| Mistral AI | api.mistral.ai/v1/models | Bearer | ~10 | No | Catalog only. Connector built. |
| SiliconFlow | api.siliconflow.cn/v1/models | Bearer | ~50 | Yes | Per-$M pricing. Connector built. |
| Perplexity | api.perplexity.ai/v1/models | Bearer | ~5 | No | Catalog only. Connector built. |
| OpenAI | api.openai.com/v1/models | Bearer | ~50 | No | Catalog only. Connector built. |
| Anthropic | api.anthropic.com/v1/models | x-api-key | ~10 | No | Catalog only. Connector built. |
| Hyperbolic | api.hyperbolic.xyz/v1/models | Bearer | ~20 | No | Catalog only. Connector built. |
| DeepSeek | api.deepseek.com/v1/models | Bearer | ~5 | No | Catalog only. Connector built. |
| Moonshot | api.moonshot.cn/v1/models | Bearer | ~5 | No | Catalog only. Connector built. |

### Signup Status

| Provider | Signup Method | Status |
|----------|--------------|--------|
| Together AI | Google/GitHub OAuth only | BLOCKED - no email signup |
| Groq | Email magic link | BLOCKED - needs email verification |
| Fireworks AI | Email/password | DONE - key active, connector LIVE |
| Cerebras | TBD | Pending |
| Mistral AI | TBD | Pending |
| SiliconFlow | TBD | Pending |
| Perplexity | TBD | Pending |
| OpenAI | TBD | Pending |
| Anthropic | TBD | Pending |

## Architecture

Each connector is a Python function in `pipeline.py` that:
1. Fetches from the provider's API (using `fetch_with_auth()` helper for auth-required providers)
2. Normalizes to our endpoint format (model_id, input/output/blended price)
3. Maps provider model IDs to our canonical model IDs
4. Returns endpoint dicts for `insert_endpoints()`

The `get_provider_api_key()` function resolves credentials in order:
1. Environment variable (e.g., `TOGETHER_API_KEY`)
2. Credentials file (`~/.hermes/.env`)
3. Jentic One (`jenticctl credential get`)

Called during the hourly pipeline run alongside OpenRouter, Venice, DeepInfra, Novita, SambaNova, Jina, Inference.net, and AI/ML API.

## Cron Schedule

- **Hourly**: OpenRouter prices + all no-auth direct providers (Venice, DeepInfra, Novita, SambaNova, Jina, Inference.net, AI/ML API)
- **Daily 03:00 UTC**: OpenRouter endpoints + Venice direct
- **Daily 04:00 UTC**: Auth-required direct providers (when keys available)

## Answer to "Why not just use OpenRouter?"

OpenRouter is a single aggregator that strips metadata and only lists what providers choose to expose. We go direct to source APIs for:
- 3x more models per provider (Venice: 105 vs 31)
- Richer metadata (capabilities, quantization, cache pricing)
- Model provenance (who made it vs who serves it)
- Future: latency, throughput, uptime per provider endpoint
