# Claude Design Brief: InferenceIndexer.ai Model Detail Page

**Project:** InferenceIndexer.ai
**Deliverable:** Model detail page HTML (single self-contained file)
**Date:** August 2026
**Context:** This is page 2 of the InferenceIndexer site. The homepage is already designed. This page is what a user sees when they click a model name from the homepage table.

---

## What This Page Is

The model detail page for a single AI model. It shows the full price history, SIT comparison, provider info, and API access for one specific model. Think of it as the CoinMarketCap token detail page (e.g. coinmarketcap.com/currencies/bitcoin/) but for an AI model.

**The model used for this mockup:** GPT-5.6 by OpenAI
- Tier: Frontier
- Blended price: $11.00/M tokens
- SIT Score: 0.31 (69% below the Frontier tier average)
- This model is interesting because its price went UP 1.8% today while most models went down

---

## Design Direction

### Consistent with Homepage

This page MUST use the same design system as the homepage:
- Dark background (#0a0a0a)
- Surface/cards (#1a1a1a, border #2a2a2a)
- Gold accent (#C4A038) for the headline price
- Green for price decreases (cheaper = good), red for price increases
- Monospace for all numbers (JetBrains Mono or IBM Plex Mono)
- Sans-serif for text (Inter)
- Same nav bar, same footer

### New Elements for This Page

- **Large price chart:** The main visual element. Full-width, interactive.
- **SIT comparison panel:** Shows where this model sits relative to its tier.
- **API code block:** Dark code snippet with syntax highlighting.
- **Provider sidebar:** Compact info about the provider.

---

## Page Structure (top to bottom)

### 1. Top Bar (same as homepage, sticky)

```
[Logo: InferenceIndexer.ai]     [Search models...]     [API]  [Methodology]  [About]
```

- Identical to homepage nav. No Login/Sign Up.
- "LIVE" indicator with green dot.
- Breadcrumb below nav: `← All Models / GPT-5.6`

### 2. Model Header

Two-column layout. Left: model identity. Right: key stats.

```
┌──────────────────────────────────────────────┬──────────────────────┐
│                                              │                      │
│  [O logo] GPT-5.6                            │  AA Index: 57        │
│  openai/gpt-5.6                              │  Context: 256K       │
│                                              │  Modality: Text      │
│  [FRONTIER] tier badge                       │  Open: Proprietary   │
│                                              │                      │
│  Provider: [OpenAI] (clickable)              │  Added: Jul 2025     │
│                                              │  Last priced: 2m ago │
└──────────────────────────────────────────────┴──────────────────────┘
```

**Left column:**
- Provider logo: single-letter colored badge (O for OpenAI, same style as homepage table)
- Model name: 32px, white, bold
- Model ID: 14px, monospace, muted grey (openai/gpt-5.6)
- Tier badge: "FRONTIER" pill, gold border, transparent background (same as homepage)
- Provider: clickable text link, gold on hover

**Right column (stats grid):**
- 2 columns x 3 rows of key-value pairs
- Label: 12px, uppercase, muted grey
- Value: 16px, monospace, white
- AA Index score, context window, modality, openness, date added, last priced

### 3. Price Card

The current price, prominent. This is what people came to see.

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  CURRENT PRICE                                                       │
│                                                                      │
│  Input          Output          Blended                              │
│  $5.00 /M       $15.00 /M      $11.00 /M    ← gold, 28px, mono       │
│                                                                      │
│  24h: ↑ 1.8% (red)   7d: ↓ 5.0% (green)   30d: ↓ 8.2% (green)      │
│  90d: ↓ 14.1% (green)   All time: ↓ 21.0% (green)                  │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

- "CURRENT PRICE" label: 13px, uppercase, muted grey
- Three price columns: equal width. Label 12px grey, value 20px monospace white. Blended is gold and slightly larger (28px).
- Change row: 14px, monospace. Green for decreases, red for increases. Each change has a small arrow.
- Card background: #1a1a1a, border 1px #2a2a2a, border-radius 8px

### 4. Price History Chart

The main visual. Full-width below the price card.

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  Price History                          [1d] [7d] [30d] [90d] [All]  │
│                                                                      │
│  $14.00 ┤                                                             │
│         │                                                             │
│  $12.00 ┤      ╭╮                                                    │
│         │     ╭╯│                                                     │
│  $10.00 ┤─────╯  ╰────────────                                        │
│         │                                                            │
│   $8.00 ┤                                                            │
│         └────────────────────────────────────────────────────        │
│          Jul 5    Jul 12    Jul 19    Jul 26    Aug 2               │
│                                                                      │
│  Blended price ($/M tokens) · 90-day view                            │
│  Low: $10.20  ·  High: $13.80  ·  Average: $11.95                    │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

**Chart specs:**
- Full-width canvas or SVG. ~400px tall.
- Gold line (#C4A038), 2px stroke.
- Subtle area fill below the line at 8% opacity.
- Y-axis: price labels on the left, monospace, muted grey. Auto-scaled.
- X-axis: date labels, monospace, muted grey.
- Timeframe buttons (1d, 7d, 30d, 90d, All) top-right. Active button: gold background, dark text. Inactive: transparent, grey border.
- Hover: vertical line + tooltip showing date and exact price. Tooltip: dark background, white text, monospace.
- Below chart: "Low", "High", "Average" stats in a single row, 13px monospace, muted grey labels with white values.
- Card background: #1a1a1a, border 1px #2a2a2a, border-radius 8px.

### 5. SIT Comparison Panel

Shows where this model sits relative to its tier and the broader market. This is the unique value-add of InferenceIndexer.

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  SIT COMPARISON                                                      │
│                                                                      │
│  SIT Score: 0.31                                                     │
│  ████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  31%                │
│                                                                      │
│  This model is 69% below the Frontier tier average ($35.20/M)       │
│  This model is 287% above the SIT-Composite ($2.84/M)                │
│                                                                      │
│  Tier Ranking: #2 of 8 Frontier models (by SIT Score)                │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Frontier Tier Models (by SIT Score)                         │   │
│  │                                                             │   │
│  │ 1. DeepSeek V4 Reasoner  $1.53/M  Score: 0.04              │   │
│  │ 2. GPT-5.6               $11.00/M  Score: 0.31  ← YOU ARE   │   │
│  │ 3. GLM-5.2               $3.30/M   Score: 0.09             │   │
│  │ 4. Grok 4.5              $3.45/M   Score: 0.10             │   │
│  │ 5. Qwen3 Max             $4.08/M   Score: 0.12             │   │
│  │ ...   [View all 8]                                         │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

**SIT Score bar:**
- Horizontal bar, full width of the panel
- Filled portion: gold (#C4A038). Unfilled: #2a2a2a.
- Score number (0.31) above the bar, 16px monospace white.
- Percentage label (31%) at the end of the filled portion, 12px monospace.

**Comparison statements:**
- Two lines, 14px, white text.
- "69% below" in green (this model is cheaper than its tier average, which is good).
- "287% above" in amber/red (this model is more expensive than the overall market).

**Tier ranking mini-table:**
- Shows top 5 models in the same tier, sorted by SIT Score.
- Current model highlighted with gold left border and "← YOU ARE" label.
- Compact: 13px text, monospace numbers.
- Clickable model names (links to their detail pages).
- "View all 8" link at the bottom.

### 6. Data Sources Panel

Transparency: where does this price come from?

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  DATA SOURCES                                                        │
│                                                                      │
│  Source          Input $/M   Output $/M   Last Fetched               │
│  OpenRouter      $5.00       $15.00       2 min ago    [primary]     │
│  OpenAI direct   $5.00       $15.00       3 hours ago                │
│                                                                      │
│  Raw API response (OpenRouter):                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ {                                                             │   │
│  │   "id": "openai/gpt-5.6",                                   │   │
│  │   "pricing": {                                               │   │
│  │     "prompt": "0.005",                                      │   │
│  │     "completion": "0.015"                                   │   │
│  │   },                                                         │   │
│  │   "context_length": 256000                                  │   │
│  │ }                                                             │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

- Table: 13px, monospace, same dark styling as homepage table.
- "[primary]" badge: 11px, gold border pill.
- Code block: dark background (#0d0d0d), monospace 12px, green/gold syntax highlighting for keys and values.
- Card background: #1a1a1a, border 1px #2a2a2a, border-radius 8px.

### 7. API Access Panel

The developer hook. Show them exactly how to get this data programmatically.

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  API ACCESS                                                          │
│                                                                      │
│  Get this model's price via API:                                     │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ $ curl https://api.inferenceindexer.ai/v1/models/openai/gpt-5.6 │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  Response:                                                           │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ {                                                             │   │
│  │   "model_id": "openai/gpt-5.6",                             │   │
│  │   "name": "GPT-5.6",                                        │   │
│  │   "provider": "OpenAI",                                     │   │
│  │   "tier": "frontier",                                       │   │
│  │   "input_price_per_m": 5.00,                                │   │
│  │   "output_price_per_m": 15.00,                              │   │
│  │   "blended_price_per_m": 11.00,                             │   │
│  │   "sit_score": 0.31,                                        │   │
│  │   "context_length": 256000,                                 │   │
│  │   "fetched_at": "2026-08-03T15:00:00Z"                      │   │
│  │ }                                                             │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  → Sign up for a free API key for historical data and higher limits  │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

- Code blocks: dark background (#0d0d0d), monospace 12px.
- Command line: prefix with "$" in green.
- JSON response: keys in gold, strings in green, numbers in white.
- "Sign up for a free API key" link: 13px, gold, hover underline.
- Card background: #1a1a1a, border 1px #2a2a2a, border-radius 8px.

### 8. Footer (same as homepage)

```
InferenceIndexer.ai · Independent price index for AI inference

Methodology · API Docs · About · Contact · Privacy Policy

315 models · 47 providers · Last updated: 2026-08-03 15:00 UTC
```

---

## Sample Data

### Model: GPT-5.6

| Field | Value |
|-------|-------|
| Model ID | openai/gpt-5.6 |
| Name | GPT-5.6 |
| Provider | OpenAI |
| Tier | Frontier |
| Input price | $5.00/M |
| Output price | $15.00/M |
| Blended price | $11.00/M |
| SIT Score | 0.31 |
| AA Index | 57 |
| Context window | 256,000 |
| Modality | Text |
| Openness | Proprietary |
| Date added | Jul 2025 |
| Last priced | 2 min ago |

### Price changes
| Period | Change |
|--------|--------|
| 24h | +1.8% (up, red) |
| 7d | -5.0% (down, green) |
| 30d | -8.2% (down, green) |
| 90d | -14.1% (down, green) |
| All time | -21.0% (down, green) |

### SIT comparison
- Frontier tier average: $35.20/M
- SIT-Composite: $2.84/M
- Tier ranking: #2 of 8 Frontier models by SIT Score
- Below tier average by: 69%
- Above SIT-Composite by: 287%

### Frontier tier ranking (by SIT Score)
| # | Model | Blended $/M | SIT Score |
|---|-------|-------------|-----------|
| 1 | DeepSeek V4 Reasoner | $1.53 | 0.04 |
| 2 | GPT-5.6 (YOU ARE HERE) | $11.00 | 0.31 |
| 3 | GLM-5.2 | $3.30 | 0.09 |
| 4 | Grok 4.5 | $3.45 | 0.10 |
| 5 | Qwen3 Max | $4.08 | 0.12 |
| 6 | Llama 4 Behemoth | $6.14 | 0.17 |
| 7 | Gemini 2.5 Pro | $6.50 | 0.18 |
| 8 | Claude Opus 5 | $34.00 | 0.97 |

### Price history (90-day daily blended close, $/M)
```
13.80, 13.65, 13.50, 13.40, 13.30, 13.20, 13.10, 13.00, 12.90, 12.85,
12.80, 12.75, 12.70, 12.65, 12.60, 12.55, 12.50, 12.45, 12.40, 12.35,
12.30, 12.25, 12.20, 12.15, 12.10, 12.05, 12.00, 11.95, 11.90, 11.85,
11.80, 11.75, 11.70, 11.65, 11.60, 11.55, 11.50, 11.45, 11.40, 11.35,
11.30, 11.25, 11.20, 11.15, 11.10, 11.05, 11.00, 10.95, 10.90, 10.85,
10.80, 10.75, 10.70, 10.65, 10.60, 10.55, 10.50, 10.45, 10.40, 10.35,
10.30, 10.25, 10.20, 10.25, 10.30, 10.35, 10.40, 10.45, 10.50, 10.55,
10.60, 10.65, 10.70, 10.75, 10.80, 10.85, 10.90, 10.95, 11.00, 11.05,
11.00, 11.10, 11.05, 11.15, 11.10, 11.20, 11.15, 11.25, 11.20, 11.30
```

### Data sources
| Source | Input $/M | Output $/M | Last fetched |
|--------|-----------|------------|--------------|
| OpenRouter | $5.00 | $15.00 | 2 min ago |
| OpenAI direct | $5.00 | $15.00 | 3 hours ago |

---

## Technical Constraints

1. **Single self-contained HTML file.** All CSS in `<style>`, all JS in `<script>`. No external dependencies except Google Fonts.
2. **Same fonts as homepage.** Inter for text, JetBrains Mono or IBM Plex Mono for numbers.
3. **Same color palette as homepage.** Dark bg, gold accent, green/red for changes.
4. **No JavaScript framework.** Vanilla JS for chart rendering and timeframe switching.
5. **Responsive.** Works from 320px to 1920px. On mobile: two-column sections stack vertically, chart stays full-width.
6. **Chart renders from embedded data.** Price history is a JSON array in a `<script>` tag, rendered to canvas or SVG.
7. **Dark theme only.**
8. **Breadcrumb.** "← All Models / GPT-5.6" at the top. "All Models" is a link back to the homepage.

---

## What NOT to Include

- No hero image or illustration
- No testimonials or social proof
- No "related models" or "recommended" section
- No newsletter signup modal
- No cookie banner
- No login/signup form
- No advertisements
- No "powered by" badges
- No 3-column feature grid
- No animated entrance effects
- No "Most Popular" or "Editor's Choice" badges

---

## Deliverable

One HTML file. Self-contained. Dark theme. Same design system as the homepage. The page should feel like a Bloomberg stock quote page: dense, fast, authoritative. The price chart is the hero. The SIT comparison is the unique insight. The API snippet is the developer hook.
