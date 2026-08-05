# Claude Design Brief v2: InferenceIndexer.ai Model Detail Page

**Project:** InferenceIndexer.ai
**Deliverable:** Updated model detail page HTML (single self-contained file)
**Date:** August 2026
**Context:** This is an update to the model detail page. The first version was close but the header section was missing key elements. This brief focuses on fixing the header and adding missing comparison statements.

---

## What Changed From v1

| Element | v1 Status | v2 Requirement |
|---------|-----------|----------------|
| Header stats grid | MISSING | MUST ADD - see Header section below |
| Tier badge in header | MISSING | MUST ADD - gold border pill |
| Provider logo badge | MISSING | MUST ADD - single-letter colored circle |
| SIT comparison statements | MISSING | MUST ADD - two plain-English lines |
| "LIVE" indicator in nav | MISSING | MUST ADD - green dot + "LIVE" |
| Login/Sign Up in nav | Present | KEEP - user confirmed this stays |
| Price card | Working | KEEP AS-IS |
| Price chart with timeframe switching | Working | KEEP AS-IS, default to 30d view |
| SIT Score bar | Working | KEEP AS-IS |
| Tier ranking mini-table | Working | KEEP AS-IS |
| Data sources panel | Working | KEEP, add per-token pricing note |
| API access panel | Working | KEEP AS-IS |
| Raw API response | Working | ADD note: "Raw per-token prices. Multiply by 1,000,000 for $/M." |

---

## Page Structure (top to bottom)

### 1. Top Bar (sticky, same as homepage)

```
[Logo: InferenceIndexer.ai]     [Search models...]     [API] [Methodology] [About] [Login] [Sign Up]  [LIVE ●]
```

- Identical to homepage nav including Login, Sign Up, and the green "LIVE" dot indicator.
- Login and Sign Up stay in the nav (confirmed by user).

### 2. Breadcrumb

```
← All Models / GPT-5.6
```

- "← All Models" is a link back to the homepage.
- "/ GPT-5.6" is plain text, not a link (current page).

### 3. Model Header (THIS IS THE SECTION THAT NEEDS THE MOST WORK)

This is a two-column layout. The left column identifies the model. The right column shows technical specs in a stats grid.

**Use this exact layout:**

```
┌──────────────────────────────────────────────────┬────────────────────────────────────┐
│ LEFT COLUMN (model identity)                     │ RIGHT COLUMN (stats grid)           │
│                                                  │                                    │
│  [O] GPT-5.6                                     │  AA INDEX          57              │
│      openai/gpt-5.6    [FRONTIER]                │  CONTEXT          256K             │
│                                                  │  MODALITY         Text             │
│  Provider: OpenAI (clickable link)               │  OPENNESS         Proprietary     │
│                                                  │  ADDED            Jul 2025         │
│                                                  │  LAST PRICED      2 min ago        │
│                                                  │                                    │
└──────────────────────────────────────────────────┴────────────────────────────────────┘
```

**Left column specs:**

- **Provider logo badge:** A single-letter colored circle, 40px diameter, positioned to the left of the model name. The letter is the first letter of the provider name. Each provider has a fixed color:
  - OpenAI = green (#10a37f)
  - DeepSeek = blue (#4d6bfe)
  - Google = blue (#4285f4)
  - Anthropic = orange (#d97757)
  - TensorX = purple (#8b5cf6)
  - xAI = dark grey (#1d1d1d, white text)
  - Meta = blue (#0668e1)
  - Others = grey (#666)
  - Circle has no border, letter is white, bold, 18px, centered.

- **Model name:** 32px, white, bold. Positioned to the right of the logo badge, vertically centered with it.

- **Model ID:** 14px, monospace, muted grey (#888). Below the model name. Shows the full ID: `openai/gpt-5.6`

- **Tier badge:** Positioned to the RIGHT of the model ID, on the same line. A pill shape with:
  - "FRONTIER" text, 11px, uppercase, bold, letter-spaced
  - Gold border (1px #C4A038), transparent background
  - Gold text color (#C4A038)
  - Padding: 2px 8px, border-radius: 4px
  - Same style as tier badges in the homepage table

- **Provider link:** Below the model ID line. 14px. "Provider: " in muted grey, then "OpenAI" as a clickable link in white (gold on hover).

**Right column specs (stats grid):**

- A 2-column grid with 6 rows. Label on the left, value on the right.
- Grid takes up roughly 35-40% of the header width on desktop. Stacks below the left column on mobile.
- **Labels:** 12px, uppercase, letter-spaced, muted grey (#888). Right-aligned.
- **Values:** 16px, monospace, white. Left-aligned.
- Row height: 28px. Border-bottom: 1px #1a1a1a (subtle separator between rows).
- No border on the last row.

**The 6 stats and their values for GPT-5.6:**

| Label | Value | Notes |
|-------|-------|-------|
| AA INDEX | 57 | Artificial Analysis Intelligence Index score |
| CONTEXT | 256K | Context window in tokens. Use K/M abbreviations. |
| MODALITY | Text | Text, Multimodal, or Code |
| OPENNESS | Proprietary | Proprietary or Open Weights |
| ADDED | Jul 2025 | Month and year the model was first tracked |
| LAST PRICED | 2 min ago | Relative time since last price fetch |

**IMPORTANT:** This stats grid is the part that was completely missing from v1. It must be present and visible without scrolling on desktop. The header section (both columns) should fit within the first viewport on a 1080px screen height.

**Header card styling:**
- Background: #1a1a1a
- Border: 1px #2a2a2a
- Border-radius: 8px
- Padding: 24px
- Two columns separated by a 1px #2a2a2a vertical divider on desktop. Single column on mobile (stats grid goes below identity).

### 4. Price Card (keep as-is from v1)

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  CURRENT PRICE                                                       │
│                                                                      │
│  Input          Output          Blended (40/60)                      │
│  $5.00 /M       $15.00 /M      $11.00 /M                             │
│                                                                      │
│  24H: ↑ 1.80%   7D: ↓ 5.00%   30D: ↓ 8.20%   90D: ↓ 14.10%          │
│  ALL TIME: ↓ 21.00%                                                  │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

- Blended price in gold (#C4A038), 28px, monospace.
- Input and Output in white, 20px, monospace.
- Changes: 14px monospace. Red for increases (↑), green for decreases (↓).
- "(40/60)" blend label next to "Blended" - already present in v1, keep it.
- Card: #1a1a1a background, 1px #2a2a2a border, 8px radius.

### 5. Price History Chart (keep as-is from v1, change default view)

```
┌──────────────────────────────────────────────────────────────────────┐
│  PRICE HISTORY                          [1d] [7d] [30d] [90d] [All]  │
│                                                                      │
│  [Full-width line chart, gold line, area fill]                       │
│                                                                      │
│  Low: $10.20  ·  High: $13.80  ·  Average: $11.95                    │
│  Blended price ($/M tokens) · 30-day view, daily close               │
└──────────────────────────────────────────────────────────────────────┘
```

- **Change from v1:** Default to 30d view (not 90d or All). The 30d button should be active on page load.
- Everything else stays the same: gold line, area fill, timeframe buttons, low/high/average stats, hover tooltip.
- Chart height: ~400px. Full card width.
- Card: #1a1a1a background, 1px #2a2a2a border, 8px radius.

### 6. SIT Comparison Panel (ADD MISSING ELEMENTS)

This panel has three parts. Parts 1 and 2 were in v1. Part 3 is NEW and must be added.

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  SIT COMPARISON                                                      │
│                                                                      │
│  ─── PART 1: SIT SCORE BAR (keep from v1) ──────────────────────     │
│                                                                      │
│  SIT Score: 0.31                                                     │
│  ████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  31%                │
│  0.00 · free                    1.00 · tier average                  │
│                                                                      │
│  ─── PART 2: TIER RANKING TABLE (keep from v1) ────────────────     │
│                                                                      │
│  Tier ranking: #7 of 8 Frontier models by SIT Score                 │
│  #  MODEL                    BLENDED $/M   SIT SCORE                 │
│  1  DeepSeek V4 Reasoner     $1.53         0.04                     │
│  2  GLM-5.2                   $3.30         0.09                     │
│  3  Grok 4.5                  $3.45         0.10                     │
│  4  Qwen3 Max                 $4.08         0.12                     │
│  5  Llama 4 Behemoth          $6.14         0.17                     │
│  6  Gemini 2.5 Pro            $6.50         0.18                     │
│  7  GPT-5.6 (this model)      $11.00        0.31    ← YOU ARE HERE  │
│  8  Claude Opus 5              $34.00        0.97                     │
│  [View all 8 Frontier models →]                                      │
│                                                                      │
│  ─── PART 3: COMPARISON STATEMENTS (NEW - MUST ADD) ──────────     │
│                                                                      │
│  This model is 69% below the Frontier tier average ($35.20/M)       │
│  This model is 287% above the SIT-Composite ($2.84/M)                │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

**Part 3 specs (the new addition):**

- Two text lines, placed BELOW the tier ranking table, inside the same SIT Comparison card.
- Each line is 15px, left-aligned.
- Line 1: "This model is " in white, then "69% below" in green (#4ade80), then " the Frontier tier average ($35.20/M)" in white.
- Line 2: "This model is " in white, then "287% above" in amber (#fbbf24), then " the SIT-Composite ($2.84/M)" in white.
- 8px gap between the two lines.
- 12px gap between the tier ranking table and these statements.
- These statements are the plain-English translation of the SIT Score. They tell the user immediately: "this model is cheap for its tier but expensive vs the overall market." Without them, the 0.31 score is just a number.

### 7. Data Sources Panel (keep from v1, add one note)

```
┌──────────────────────────────────────────────────────────────────────┐
│  DATA SOURCES                                                        │
│                                                                      │
│  SOURCE        INPUT $/M   OUTPUT $/M   LAST FETCHED                 │
│  OpenRouter    $5.00       $15.00       2 min ago     [primary]      │
│  OpenAI direct $5.00       $15.00       3 hours ago                   │
│                                                                      │
│  Raw API response (OpenRouter):                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ {                                                               │ │
│  │   "id": "openai/gpt-5.6",                                     │ │
│  │   "pricing": {                                                 │ │
│  │     "prompt": "0.000005",                                      │ │
│  │     "completion": "0.000015"                                   │ │
│  │   },                                                            │ │
│  │   "context_length": 256000                                    │ │
│  │ }                                                               │ │
│  └────────────────────────────────────────────────────────────────┘ │
│  Raw per-token prices. Multiply by 1,000,000 for $/M.               │
└──────────────────────────────────────────────────────────────────────┘
```

- Everything same as v1.
- **ADD:** Small note below the code block: "Raw per-token prices. Multiply by 1,000,000 for $/M." in 11px, muted grey (#888), italic.

### 8. API Access Panel (keep as-is from v1)

```
┌──────────────────────────────────────────────────────────────────────┐
│  API ACCESS                                                          │
│                                                                      │
│  Get this model's price via API:                                     │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ $ curl https://api.inferenceindexer.ai/v1/models/openai/gpt-5.6 │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  Response:                                                           │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ {                                                               │ │
│  │   "model_id": "openai/gpt-5.6",                                │ │
│  │   ... (full JSON)                                               │ │
│  │ }                                                               │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  → Sign up for a free API key for historical data and higher limits  │
└──────────────────────────────────────────────────────────────────────┘
```

- Keep exactly as v1. No changes needed.

### 9. Footer (same as homepage)

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
| Provider logo letter | O |
| Provider logo color | #10a37f (green) |
| Tier | Frontier |
| Input price | $5.00/M |
| Output price | $15.00/M |
| Blended price | $11.00/M |
| SIT Score | 0.31 |
| AA Index | 57 |
| Context window | 256,000 (display as "256K") |
| Modality | Text |
| Openness | Proprietary |
| Date added | Jul 2025 |
| Last priced | 2 min ago |

### Price changes
| Period | Change | Color |
|--------|--------|-------|
| 24h | +1.80% | Red (price went up) |
| 7d | -5.00% | Green |
| 30d | -8.20% | Green |
| 90d | -14.10% | Green |
| All time | -21.00% | Green |

### SIT comparison
- SIT Score: 0.31 (31% of tier average)
- Frontier tier average: $35.20/M
- SIT-Composite: $2.84/M
- Tier ranking: #7 of 8 Frontier models by SIT Score
- Below tier average by: 69%
- Above SIT-Composite by: 287%

### Frontier tier ranking (by SIT Score, ascending)
| # | Model | Blended $/M | SIT Score |
|---|-------|-------------|-----------|
| 1 | DeepSeek V4 Reasoner | $1.53 | 0.04 |
| 2 | GLM-5.2 | $3.30 | 0.09 |
| 3 | Grok 4.5 | $3.45 | 0.10 |
| 4 | Qwen3 Max | $4.08 | 0.12 |
| 5 | Llama 4 Behemoth | $6.14 | 0.17 |
| 6 | Gemini 2.5 Pro | $6.50 | 0.18 |
| 7 | GPT-5.6 (this model) | $11.00 | 0.31 |
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

### Raw OpenRouter API response
```json
{
  "id": "openai/gpt-5.6",
  "pricing": {
    "prompt": "0.000005",
    "completion": "0.000015"
  },
  "context_length": 256000
}
```

---

## Technical Constraints

1. **Single self-contained HTML file.** All CSS in `<style>`, all JS in `<script>`. No external dependencies except Google Fonts.
2. **Same fonts as homepage.** Inter for text, JetBrains Mono or IBM Plex Mono for numbers.
3. **Same color palette as homepage.** Dark bg (#0a0a0a), gold accent (#C4A038), green (#4ade80) for price decreases, red (#ef4444) for price increases.
4. **No JavaScript framework.** Vanilla JS for chart rendering and timeframe switching.
5. **Responsive.** Works from 320px to 1920px. On mobile: header two columns stack, stats grid goes below model identity, chart stays full-width.
6. **Chart renders from embedded data.** Price history is a JSON array in a `<script>` tag.
7. **Dark theme only.**
8. **Default chart view: 30d.** Not 90d, not All.

---

## What NOT to Include

- No hero image or illustration
- No testimonials or social proof
- No "related models" or "recommended" section
- No newsletter signup modal
- No cookie banner
- No advertisements
- No "powered by" badges
- No 3-column feature grid
- No animated entrance effects
- No "Most Popular" or "Editor's Choice" badges

---

## Summary of Changes From v1

| Change | Priority |
|--------|----------|
| Add provider logo badge (colored circle with letter) to header | HIGH |
| Add tier badge (FRONTIER pill) next to model name | HIGH |
| Add 6-row stats grid (AA Index, Context, Modality, Openness, Added, Last Priced) | HIGH |
| Add "LIVE" indicator to nav | MEDIUM |
| Add two SIT comparison statements below tier ranking table | HIGH |
| Change default chart view to 30d | MEDIUM |
| Add per-token pricing note below raw API response | LOW |
| Keep Login/Sign Up in nav | NO CHANGE |

The header section is the critical fix. In v1, the header was just a model name and a provider link. It needs to be a proper two-column layout with the logo, tier badge, model ID, and a full stats grid. Think of it as the "spec sheet" for the model, visible without scrolling.
