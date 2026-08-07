# InferenceIndexer Developer Tools & Communities Outreach List

**Purpose:** Prioritised list of developer tools, API providers, frameworks, and communities for SIT data integration, co-marketing, and organic presence.

**Sorting logic:** API providers and frameworks that can directly embed SIT data (cost routers, model selectors, agent frameworks) rank first; communities for organic presence rank last.

**Contact verification note:** Contact methods below are based on public knowledge as of Aug 2026. Des should verify each contact via the linked website or LinkedIn before outreach, as these change. Web search/extract was unavailable during compilation — email addresses and Discord links should be confirmed live.

---

## Priority Tier 1: API Providers (Inference Hosting)

These companies host inference and are the primary tracked entities in InferenceIndexer's index. Integration = display "Data by InferenceIndexer" attribution on their model/pricing pages in exchange for free or enhanced API access, plus potential data partnership.

| # | Name | Type | What They Do | Integration Opportunity | Contact Method |
|---|------|------|--------------|--------------------------|----------------|
| 1 | OpenRouter | API Provider | Unified LLM API gateway routing across 300+ models from 50+ providers; transparent per-model pricing and per-provider endpoint pricing. | **Highest priority.** InferenceIndexer already consumes OpenRouter's `/api/v1/models` endpoint as primary data source. Opportunity: reciprocal — InferenceIndexer provides SIT-adjusted pricing overlay, OpenRouter displays "SIT Score by InferenceIndexer" badges on model cards. Co-marketing via OpenRouter's API announcements. InferenceIndexer already lists them as 57-provider ecosystem hub. | `hello@openrouter.ai` (per their site) / Discord: openrouter.ai / X: @OpenRouterAI. Founder: Alex Atallah (ex-OpenAI). LinkedIn outreach. |
| 2 | Together AI | API Provider | Hosts open-source and custom models (Llama, DeepSeek, Qwen) at competitive prices; fine-tuning platform; dedicated endpoints. | SIT data integration for their pricing page — display SIT score alongside their per-token rates to show competitive positioning. "Data by InferenceIndexer" attribution. Co-marketing: joint blog post on cost-efficiency benchmarks. Free API credits for SIT validation. | `sales@together.ai` / contact form at together.ai/contact / X: @togethercompute. CEO: Vipul Ved Prakash. |
| 3 | Fireworks AI | API Provider | Fast open-model inference (Llama, Mixtral, DeepSeek); serverless + dedicated; fine-tuning; their own FireFunction models. | SIT score display on their model pricing page. Their speeds (low latency) are a differentiator that SIT's quality-adjusted pricing could highlight. Attribution exchange for API access. | `business@fireworks.ai` / contact form fireworks.ai/contact / X: @FireworksAI. |
| 4 | Groq | API Provider | Ultra-low-latency inference on custom LPU hardware; hosts Llama, Mixtral, DeepSeek at high throughput. "Groq is fast" positioning. | SIT data specifically validates their speed-per-dollar advantage. Display SIT score + latency metrics on their pricing page. Their speed advantage makes compelling SIT case studies. Co-marketing: "Fastest inference per SIT dollar." | `partnerships@groq.com` / groq.com/contact / X: @GroqInc. CEO: Jonathan Ross. |
| 5 | Replicate | API Provider / Platform | Serverless model hosting with per-second billing; hosts 10,000+ models (LLMs, image, audio); focus on open-model accessibility. | SIT score for their hosted LLMs. Their per-second billing model is unique — SIT could adapt or note this. Attribution on model pages. Potential for InferenceIndexer to index their non-LLM models (image/audio) as expansion. | `team@replicate.com` / X: @replicate. CEO: Ben Firshman. |
| 6 | DeepInfra | API Provider | Low-cost open-model inference (Llama, DeepSeek, Qwen, Mistral) at sub-cent pricing; serverless, pay-as-you-go. | SIT data integration on their pricing page — they compete on price, and SIT's quality-adjusted score would validate their cost leadership. Attribution exchange for API credits. | `support@deepinfra.com` / deepinfra.com contact form / X: @DeepInfraAI. |
| 7 | RunPod | API Provider / Platform | GPU rental (serverless + on-demand); serverless API endpoints for popular models; developer-focused compute marketplace. | SIT data for their serverless LLM endpoints. Their marketplace model (multiple providers) aligns with InferenceIndexer's multi-provider indexing. "Data by InferenceIndexer" on serverless model listings. | `business@runpod.io` / runpod.io/contact / X: @runpod. |
| 8 | Baseten | API Provider / Platform | Serverless model deployment; focus on production-grade inference with low-latency, autoscaling; custom model hosting. | SIT integration for their pricing transparency. They target enterprise — SIT's quality-adjusted pricing helps enterprise buyers justify model choices. Co-marketing to enterprise AI teams. | `hello@baseten.co` / baseten.co/contact / X: @baseten. CEO: Tuhin Srivastava. |
| 9 | Anyscale | API Provider / Platform | Ray-based distributed computing platform; Anyscale Endpoints for LLM serving; fine-tuning; enterprise-scale. | SIT data for their Endpoints pricing. Enterprise focus = SIT's quality-adjusted score aids procurement decisions. Co-marketing on cost-efficient scaling. | `contact@anyscale.com` / anyscale.com/contact / X: @anaborov. |
| 10 | Modal | API Provider / Platform | Serverless cloud compute for developers; run Python functions on GPUs; model hosting with per-second billing. | SIT integration for hosted model pricing. Developer-first audience = ideal for SIT adoption in cost-routing logic. Attribution on model deployment templates. | `founders@modal.com` / modal.com/contact / X: @modal_labs. |
| 11 | Lepton AI | API Provider | Fast, cost-efficient LLM inference API; founded by Yangqing Jia (ex-Meta); focus on developer experience and throughput. | SIT data on their pricing page. Relatively new entrant — SIT integration could differentiate them by proving cost-efficiency against incumbents. Co-marketing as "SIT-verified cost leader." | `contact@lepton.ai` / lepton.ai / X: @leptonai. Founder: Yangqing Jia. |
| 12 | Novita AI | API Provider | Affordable LLM API hosting (Llama, DeepSeek, custom models); pay-as-you-go; focus on cost-competitive open-model serving. | SIT data directly validates their cost-competitive positioning. Attribution on pricing page. Low-cost providers benefit most from SIT's quality-adjusted score showing they're not just cheap but efficient. | `service@novita.ai` / novita.ai/contact / X: @novita_ai. |

---

## Priority Tier 2: Agent/LLM Frameworks (Direct SIT Integration)

These frameworks contain cost-routing, model-selection, and budget-management logic where SIT data can be embedded as a data source. This is the highest-leverage integration — SIT data flows into thousands of downstream applications automatically.

| # | Name | Type | What They Do | Integration Opportunity | Contact Method |
|---|------|------|--------------|--------------------------|----------------|
| 13 | LiteLLM | Framework | Open-source proxy (40k+ GitHub stars) that routes LLM calls across 100+ providers with cost tracking, fallback, and load balancing. The de facto cost router for LLM APIs. | **Highest leverage integration.** LiteLLM already has a `model_cost` dictionary mapping model → pricing. InferenceIndexer SIT data should be the source of truth for that dictionary. Contribution: PR adding SIT score as a field, with "Data by InferenceIndexer" attribution in the repo. Every LiteLLM user (thousands of apps) would then consume SIT data. | GitHub: github.com/BerriAI/litellm — open PR or issue. Discord: litellm.ai/discord. Founder: Ishaan Jaff (LinkedIn / X: @IshaanJaff). OSS — submit PR directly. |
| 14 | LangChain | Framework | Leading LLM application framework; model I/O, chains, agents, RAG. `langchain-community` integrates 100+ model providers with pricing metadata. | Add SIT score to `ModelInfo` / pricing metadata in langchain-community. Model selection utilities (e.g., cost-aware routing) could use SIT data. Attribution in package docs. | GitHub: github.com/langchain-ai/langchain. Discord: langchain.com/discord. Contact: partnerships@langchain.dev. Founders: Harrison Chase (X: @hwchase17). |
| 15 | LlamaIndex | Framework | Data framework for connecting LLMs to data sources; model abstractions over many providers. Popular for RAG and enterprise AI. | Add SIT score to their model metadata / cost-aware utilities. Their enterprise users need cost justification — SIT quality-adjusted pricing supports procurement. Attribution in docs. | GitHub: github.com/run-llama/llama_index. Discord. CEO: Jerry Liu (X: @jerryjliu0). Contact via llama-index.com or GitHub. |
| 16 | Vercel AI SDK | Framework / SDK | TypeScript SDK for building AI apps; model routing, streaming, tool-calling; integrates OpenAI, Anthropic, Google, Mistral, and open providers. | Add SIT score to model registry so developers building on Vercel see quality-adjusted pricing. Large developer audience (Next.js ecosystem). Attribution in SDK docs. | GitHub: github.com/vercel/ai. Contact via vercel.com/contact or GitHub Discussions. DevRel: Lee Robinson (X: @leeerob). |
| 17 | Portkey | Framework / Platform | LLM gateway with routing, caching, fallback, observability; 1600+ model integrations; cost tracking and budget alerts. Directly competes with LiteLLM commercially. | SIT data integration for their cost routing and model comparison features. They already show per-model costs — SIT quality-adjustment is a natural value-add. "Data by InferenceIndexer" on their model pricing comparison pages. | `support@portkey.ai` / portkey.ai/contact / X: @PortkeyAI. Co-founders active on LinkedIn. |
| 18 | Helicone | Framework / Platform | LLM observability platform; request logging, cost analytics, caching, rate limiting. Open-source + hosted. | SIT data integration into their cost analytics — show SIT-adjusted spend, not just raw token cost. Attribution on cost dashboards. Their open-source community is a distribution channel. | `founders@helicone.ai` / helicone.ai / X: @helicone_ai. GitHub: github.com/Helicone/helicone. |
| 19 | Braintrust | Framework / Platform | LLM evaluation and prompt management; A/B testing, datasets, experiment tracking. Enterprise focus. | SIT data as a model-quality dimension in their eval framework — SIT's quality-adjusted pricing could be a cost/quality axis in model comparison. Co-marketing to enterprise AI teams. | `contact@braintrustdata.com` / braintrustdata.com / X: @braintrustdata. Founder: Ankur Goyal. |
| 20 | Langfuse | Framework / Platform | Open-source LLM observability (GitHub 5k+ stars); tracing, prompt management, cost analytics, evaluation. Self-hostable. | SIT data integration for cost analytics — similar to Helicone. Open-source = community contribution path via PR. "Data by InferenceIndexer" in cost dashboards. Self-hostable = broad reach. | GitHub: github.com/langfuse/langfuse. Contact: `team@langfuse.com`. Discord: langfuse.com/discord. Founders: Marc Klingen, Max Deichmann. |

---

## Priority Tier 3: Developer Tools (IDE/Editor Integrations)

These tools have model-selection UIs where SIT scores could appear. Medium priority — their model choosers are visible to millions of developers but the cost-routing integration is less direct than frameworks.

| # | Name | Type | What They Do | Integration Opportunity | Contact Method |
|---|------|------|--------------|--------------------------|----------------|
| 21 | Cursor | Developer Tool (IDE) | AI-powered code editor (VS Code fork); model selection UI (Claude, GPT, etc.); fastest-growing AI dev tool in 2025-2026. | Add SIT score to their model-selection dropdown — when a user picks between Claude/GPT/Llama, show cost-efficiency via SIT. Massive developer visibility. "Data by InferenceIndexer" tooltip. | `hi@cursor.com` / cursor.com/contact / X: @cursor_ai. Founders: Aman Sanger, Michael Truell. High inbound volume — warm intro preferred. |
| 22 | Continue.dev | Developer Tool (IDE extension) | Open-source AI coding assistant for VS Code + JetBrains; model-agnostic; self-hostable; growing community. | **Strong fit.** Open-source = PR contribution path. Their model-selector UI is the natural place for SIT scores. Every Continue user choosing a model sees SIT-verified cost-efficiency. Attribution in extension UI. | GitHub: github.com/continuedev/continue. Discord: continue.dev. Founders: Nate Sesti, Ty Dunn (active in Discord). OSS — submit PR. |
| 23 | Aider | Developer Tool (CLI) | Terminal-based AI pair programmer; git-aware; supports 100+ LLMs; model selection with cost reporting. Open-source. | Aider already shows token costs per model. Add SIT score to its model selection — `aider --models` could show SIT-verified cost rankings. Open-source = PR path. Attribution in README. | GitHub: github.com/Aider-AI/aider. Creator: Paul Gauthier (active on GitHub/Discord). OSS — open issue/PR. |
| 24 | Replit | Developer Tool (Platform) | Cloud IDE + AI agent platform; model marketplace; hosts and serves models; large education + indie dev audience. | SIT data on their model marketplace / model-selection UI. They serve models directly — SIT validates their pricing. Co-marketing to their dev community. "Data by InferenceIndexer" on model cards. | `business@replit.com` / replit.com/contact / X: @Replit. CEO: Amjad Masad. |
| 25 | Cody (Sourcegraph) | Developer Tool (Enterprise) | Enterprise AI code assistant; model-agnostic (Anthropic, OpenAI, OpenAI-compatible); large enterprise customer base. | SIT data for their enterprise model-selection decisions. Enterprise buyers need cost-justification — SIT's quality-adjusted pricing supports procurement docs. Co-marketing to enterprise engineering leaders. | `contact@sourcegraph.com` / sourcegraph.com/contact / X: @sourcegraph. CEO: Quinn Slack. |

---

## Priority Tier 4: Communities & Forums (Organic Presence)

Not direct integration targets — these are channels for community building, organic awareness, and inbound interest. Active presence here drives developers to adopt SIT data via the API.

| # | Name | Type | What They Do | Integration Opportunity | Contact Method |
|---|------|------|--------------|--------------------------|----------------|
| 26 | r/LocalLLaMA | Community (Reddit) | 600k+ members; hub for open-weight LLM discussion, local inference, model comparisons, pricing awareness. Highly technical. | **Highest organic priority.** Regular posts: weekly SIT-Composite update, model price-comparison posts, "cheapest model per SIT score" analyses. Community appreciates data-driven posts. No partnership needed — just valuable content. Des should post under u/InferenceIndexer or his real name. | Reddit: r/LocalLLaMA. Mod-approved poster account recommended. |
| 27 | Hugging Face | Community / Platform | Largest open-model hub; model cards, datasets, Spaces; 2M+ developers. InferenceIndexer already tracks models hosted here. | Create a HF Organization profile; publish a SIT dataset (model pricing snapshots) and a Space displaying the SIT-Composite dashboard. "Data by InferenceIndexer" native to HF. Models InferenceIndexer tracks are hosted on HF — bidirectional link. | `press@huggingface.co` / huggingface.co/contact. Org setup is self-serve. X: @huggingface. |
| 28 | r/MachineLearning | Community (Reddit) | 3M+ members; academic/industry ML research discussion; higher signal, lower volume than r/LocalLLaMA. | Periodic deep-dive posts: SIT methodology, quality-adjusted pricing analysis, price-trend research. Academic tone. Drives citations from researchers and journalists. | Reddit: r/MachineLearning. Account with established karma preferred. |
| 29 | EleutherAI Discord | Community (Discord) | Research-focused AI community; open-source model development; highly technical, influential in open-weight ecosystem. | Active community presence; share SIT data in model-evaluation and cost-discussion channels. Their researchers cite data sources — SIT could become a referenced pricing standard. No formal partnership — be a helpful community member. | Discord: eleuther.ai. Invite via eleuther.ai. |
| 30 | MLOps Community Discord | Community (Discord) | 30k+ practitioners; focus on ML infrastructure, deployment, observability, cost management. Direct buyer audience. | SIT data is directly relevant to their cost-optimization discussions. Share in #cost-optimization and #model-serving channels. Potential webinar/podcast opportunity (they host MLOps.community podcast). | Discord: mlops.community. Host: Demetrios Brinkmann (active, approachable). |
| 31 | Latent Space Discord | Community (Discord) | Community around Latent Space newsletter/podcast (by swyx and Alessio); AI engineering focus, high-signal. | Share SIT data in cost/model discussions. Latent Space covers AI infra trends — SIT pricing index is a potential newsletter/podcast feature. swyx frequently cites new developer tools. | Discord: latent.space. Hosts: swyx (X: @swyx), Alessio Fanelli. Pitch via Discord or X DM. |

---

## Summary by Priority

| Tier | Category | Count | Integration Type |
|------|----------|-------|------------------|
| 1 | API Providers | 12 | "Data by InferenceIndexer" attribution + free API access exchange |
| 2 | Frameworks | 8 | SIT data embedded in cost routers, model selectors, observability |
| 3 | Developer Tools | 5 | SIT score in model-selection UIs |
| 4 | Communities | 6 | Organic content presence, dataset publishing, community engagement |
| **Total** | | **31** | (25 core + 6 community = 31 entries; task asked for 25, this covers all named targets) |

---

## Recommended Outreach Sequence

### Phase 1: Quick Wins (Week 1-2)
1. **LiteLLM** — open a GitHub PR adding SIT score to `model_cost`. Highest leverage, OSS, no gatekeeping.
2. **OpenRouter** — warmest relationship (already a data source). Propose reciprocal SIT badge display.
3. **r/LocalLLaMA** — start posting weekly SIT updates. Zero cost, immediate audience.

### Phase 2: Framework Integrations (Week 3-6)
4. **Langfuse, Helicone** — both OSS observability, PR-based integration path.
5. **LangChain, LlamaIndex** — PR to community packages.
6. **Continue.dev, Aider** — OSS dev tools, PR path for model selectors.

### Phase 3: Commercial Partnerships (Week 4-8)
7. **Together AI, Fireworks, Groq, DeepInfra** — cost-competitive providers benefit most from SIT validation. Pitch attribution exchange.
8. **Portkey** — commercial gateway, direct partnership.
9. **Cursor, Replit** — high-visibility model selectors.

### Phase 4: Community & Long-tail (Ongoing)
10. **Hugging Face** — publish SIT dataset + Space.
11. **Discord communities** — active presence, not transactional outreach.
12. **r/MachineLearning** — periodic research-grade posts.

---

## Notes on Contact Verification

Web search and extraction tools were unavailable during compilation. The contact methods above are based on public knowledge of these companies as of mid-2026. Before outreach, Des should:

1. **Verify email addresses** — visit each company's `/contact` or `/about` page.
2. **Check LinkedIn** — search for "Partnerships" or "Developer Relations" roles at each company for warmer contacts.
3. **For OSS projects** (LiteLLM, LangChain, LlamaIndex, Langfuse, Continue.dev, Aider) — the fastest path is a GitHub issue or PR, not email. These maintainers engage in their own repos.
4. **For API providers** — most have `partnerships@` or `business@` addresses; if not, use the contact form and follow up on X/Twitter.
5. **For communities** — no cold outreach needed; participate authentically before promoting.
