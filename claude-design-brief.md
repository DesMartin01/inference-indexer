# Claude Design Brief: InferenceIndexer.ai Homepage

**Project:** InferenceIndexer.ai
**Deliverable:** Homepage HTML (single self-contained file)
**Date:** August 2026

---

## What This Product Is

InferenceIndexer is the CoinMarketCap for AI inference pricing. It tracks 300+ AI model prices across 40+ providers, normalizes them into a single index called the Standard Inference Token (SIT), and publishes a daily composite price that becomes the reference number everyone cites.

**The one-line pitch:** "The independent price index for AI inference. Tracking token costs across every provider."

**The headline number:** SIT-Composite: $2.84/M tokens

---

## Design Direction

### Vibe

Bloomberg terminal meets CoinMarketCap. Data-dense, fast, authoritative. NOT a SaaS landing page. No testimonials, no "Get Started" CTAs, no feature grids with icons. This is a financial data product.

### Color Palette

- **Background:** Near-black (#0a0a0a or #0d0d0d)
- **Surface/cards:** Slightly lighter dark (#1a1a1a or #161618)
- **Text primary:** Off-white (#e5e5e5)
- **Text secondary/muted:** Grey (#888 or #999)
- **Accent (headline number, links):** Gold/amber (#C4A038 or #D4A843)
- **Positive/price down (cheaper = good):** Green (#22c55e or #4ade80)
- **Negative/price up (more expensive = bad):** Red (#ef4444 or #f87171)

Note: In this product, green means prices went DOWN (inference got cheaper, good for consumers). Red means prices went UP. This is the opposite of stock markets. Make this convention clear with a small legend.

### Typography

- **Headline numbers (SIT price):** Large, monospace, tabular figures. 36-48px.
- **Section headings:** Sans-serif, bold, 16-20px.
- **Body text:** Sans-serif, 14px, good line-height.
- **Table data:** Monospace for all numbers (prices, percentages, token counts). Sans-serif for model names and provider names. 13px.
- **Labels/captions:** Sans-serif, 11-12px, muted grey.

Recommended fonts:
- Numbers: "JetBrains Mono" or "IBM Plex Mono" or system monospace
- Text: "Inter" or system sans-serif (-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif)

Load from Google Fonts. Keep weights minimal: 400, 500, 600.

### Layout Principles

1. **The number is the hero.** SIT-Composite price is the largest element on the page. Everything else supports it.
2. **Data density over decoration.** The model table is the core content. Pack information, don't pad it.
3. **Scannable.** A user should get the full picture in 3 seconds: index price, direction, tier breakdown, top movers.
4. **No wasted space.** Every pixel serves data. No hero images, no decorative gradients, no illustrations.
5. **Dark theme is default.** Not a toggle. Dark is the product.

---

## Page Structure (top to bottom)

### 1. Top Bar (sticky, minimal)

```
[Logo: InferenceIndexer.ai]     [Search models...]     [API]  [Methodology]  [About]
```

- Logo: text-based, not an image. "InferenceIndexer" in white, ".ai" in gold.
- Search: inline, expands on click. Placeholder: "Search 315 models..."
- Nav links: right-aligned, small, muted grey, hover to white.
- Background: transparent or very subtle dark, border-bottom 1px #222.

### 2. Hero Section: SIT-Composite

This is the headline. Takes roughly 30-40% of the viewport height.

```
                    SIT-Composite
                    $2.84 / M tokens
                              ↓ 1.2% today

         7d: ↓ 3.1%    30d: ↓ 12.4%    90d: ↓ 28.7%

              [30-day sparkline chart, ~600px wide]

    The Standard Inference Token (SIT) is a standardized unit for
    tracking AI inference prices across providers.
    → Read methodology
```

- "SIT-Composite" label: 14px, muted grey, uppercase, letter-spaced.
- "$2.84 / M tokens": 48px, monospace, gold/amber, tabular figures.
- "↓ 1.2% today": 18px, green (price went down = good).
- Period changes: 14px, monospace, green/red depending on direction.
- Sparkline: minimal, 1px line, gold color, no axes, no grid. Just the shape of the price over 30 days. Subtle area fill below the line at 10% opacity.
- Methodology link: 13px, gold, hover underline.

### 3. Tier Breakdown Cards

Three cards side by side, equal width. Below the hero.

```
┌─────────────────┬─────────────────┬─────────────────┐
│ SIT-Frontier    │ SIT-Standard    │ SIT-Budget      │
│ $35.20/M        │ $1.25/M         │ $0.42/M         │
│ ↓ 0.8%          │ ↓ 1.5%          │ ↓ 2.1%          │
│ 8 models        │ 156 models      │ 78 models       │
└─────────────────┴─────────────────┴─────────────────┘
```

- Card background: #1a1a1a, border 1px #2a2a2a, border-radius 8px.
- Tier name: 13px, uppercase, muted grey.
- Price: 24px, monospace, white.
- Change: 14px, monospace, green/red.
- Model count: 12px, muted grey.
- Hover: border brightens to #3a3a3a, subtle background shift.

Below the cards, a single line:

```
SIT-Spread (Frontier - Budget): $34.78/M  ↓ 1.9%
```

- 14px, monospace, muted. This shows whether the quality premium is widening or narrowing.

### 4. SIT Variant Filters

A horizontal row of filter pills, like CoinMarketCap category filters:

```
[All] [Frontier] [Standard] [Budget] [EU-Sovereign] [Open Weights] [Proprietary] [Cached]
```

- Active pill: gold background, dark text.
- Inactive: transparent, grey border, grey text. Hover: border brightens.
- Clicking a filter updates the table and the index number above it.
- 12px text, 6px horizontal padding, 4px vertical.

### 5. Model Table (the main content)

This is the CoinMarketCap table. Dense, sortable, filterable.

```
#  │ Model              │ Provider    │ Tier      │ Input $/M │ Output $/M │ Blended $/M │ 24h   │ 7d
───┼────────────────────┼─────────────┼───────────┼───────────┼────────────┼──────────────┼───────┼──────
1  │ DeepSeek V4 Flash  │ DeepSeek    │ Budget    │ $0.09     │ $0.18      │ $0.14       │ 0%    │ ↓2%
2  │ GPT-4o-mini       │ OpenAI      │ Standard  │ $0.15     │ $0.60      │ $0.42       │ 0%    │ 0%
3  │ Mistral Small      │ Mistral     │ Budget    │ $0.07     │ $0.20      │ $0.15       │ ↓2%   │ ↓5%
4  │ Gemini Flash       │ Google      │ Standard  │ $0.07     │ $0.30      │ $0.21       │ ↓8%   │ ↓12%
5  │ Claude Opus 5      │ Anthropic   │ Frontier  │ $10.00    │ $50.00     │ $34.00      │ ↓1%   │ ↓3%
   │ ...                                                                                 │
   │ 315 models tracked across 47 providers. Updated 2 min ago.           [Show all]
```

**Table specs:**
- Background: transparent (inherits page background).
- Header row: 12px, uppercase, muted grey. Bottom border 1px #2a2a2a. Sortable (click to sort, gold underline on active sort column).
- Row height: 40px. Border-bottom 1px #1a1a1a.
- Hover row: background #141414.
- Rank (#): 13px, muted grey, monospace.
- Model name: 14px, white. Clickable, links to model detail page. Provider logo (16px circle) before the name if available.
- Provider: 13px, muted grey.
- Tier: 12px, pill badge. Frontier = gold border, Standard = blue border, Budget = green border, Micro = grey border. Transparent background.
- All prices: 13px, monospace, tabular figures.
- 24h/7d changes: 13px, monospace, green (↓) or red (↑).
- "Updated 2 min ago": 12px, muted grey. A small green dot before it indicates data is fresh.
- "Show all": 13px, gold link. Expands or paginates.

**Table behavior:**
- Default sort: Blended $/M ascending (cheapest first).
- Click any column header to sort.
- Search box in the top bar filters this table in real-time.
- SIT variant filter pills above filter the table rows.
- Show 20 rows by default, "Show all" or pagination for the rest.
- Sticky header row on scroll.

### 6. Biggest Movers Today

Two-column layout below the table:

```
┌──────────────────────────────┬──────────────────────────────┐
│ ↑ Top Gainers (24h)          │ ↓ Top Losers (24h)           │
│                              │                              │
│ DeepSeek V4 Flash   +5.2%    │ Gemini Flash       -8.1%    │
│ Mistral Large      +2.1%    │ Groq Llama         -4.3%    │
│ GPT-4o             +1.8%    │ Claude Sonnet      -3.2%    │
│ ...                          │ ...                          │
└──────────────────────────────┴──────────────────────────────┘
```

- Card background: #1a1a1a, border 1px #2a2a2a.
- Heading: 13px, uppercase, muted grey.
- Model name: 13px, white, clickable.
- Percentage: 13px, monospace, green (gainers) or red (losers).
- Show top 5 in each column.

### 7. API CTA (subtle, not pushy)

A single line, centered, below the movers:

```
Get the data via API → Sign up for a free API key
```

- 14px, muted grey. "Sign up for a free API key" is a gold link.
- No box, no button, no card. Just a text link. This is not a SaaS landing page.

### 8. Footer

```
InferenceIndexer.ai · Independent price index for AI inference

Methodology · API Docs · About · Contact · Privacy Policy

315 models · 47 providers · Last updated: 2026-08-03 15:00 UTC
```

- Background: same as page (#0a0a0a) or slightly darker.
- Border-top: 1px #1a1a1a.
- Text: 12px, muted grey. Links: 12px, gold on hover.

---

## Interaction Notes

1. **Table sorting:** Click column header to sort ascending. Click again for descending. Show a small arrow indicator (↑/↓) on the active sort column. Gold underline on active column.

2. **Table filtering:** The SIT variant pills and the search box both filter the table. Pills filter by tier/attribute. Search filters by model name or provider. Both can be active simultaneously.

3. **Sparkline chart:** Use a lightweight canvas or SVG. 30-day price history. Gold line (#C4A038), 1.5px stroke. Optional: subtle area fill below at 8-10% opacity. No axes, no labels, no tooltip on hover (keep it minimal). The chart should render from data embedded in the page (JSON in a script tag), not from an API call.

4. **Variant filter behavior:** When a user clicks "EU-Sovereign", the SIT-Composite number at the top updates to show the SIT-EU-Sovereign index. The tier cards update. The table filters to EU-hosted models only. The URL updates with a query param (?variant=eu-sovereign) for shareability. The sparkline updates to show that variant's 30-day history.

5. **Mobile responsive:** Table scrolls horizontally on mobile. Hero scales down. Tier cards stack vertically. Sparkline stays full-width. Nav collapses to a hamburger.

6. **Performance:** No JavaScript framework. Vanilla JS for sorting, filtering, and chart rendering. Server-rendered HTML. The page should load in under 1 second.

---

## What NOT to Include

- No hero image or illustration
- No testimonials or social proof
- No pricing tiers or "Choose your plan"
- No feature comparison grid
- No "Powered by AI" badges
- No animated counters or entrance animations
- No gradient backgrounds (except possibly a very subtle radial gradient behind the hero number)
- No glassmorphism
- No emoji
- No newsletter signup modal
- No cookie banner (the product is privacy-first, no tracking cookies)
- No advertisements or sponsored placements
- No login/signup in the nav (API signup is a text link at the bottom)

---

## Sample Data

Use this realistic data for the mockup. All prices are per million tokens.

### SIT-Composite
- Price: $2.84/M
- 24h: -1.2%
- 7d: -3.1%
- 30d: -12.4%
- 90d: -28.7%

### Tier Indices
| Tier | Price | 24h | Models |
|------|-------|-----|--------|
| Frontier | $35.20/M | -0.8% | 8 |
| Standard | $1.25/M | -1.5% | 156 |
| Budget | $0.42/M | -2.1% | 78 |

### SIT-Spread
- Frontier - Budget: $34.78/M, -1.9%

### Model Table (top 15 rows)
| # | Model | Provider | Tier | Input $/M | Output $/M | Blended $/M | 24h | 7d |
|---|-------|----------|------|-----------|------------|-------------|-----|-----|
| 1 | DeepSeek V4 Flash | DeepSeek | Budget | $0.09 | $0.18 | $0.14 | 0% | -2% |
| 2 | Mistral Small 2603 | Mistral | Budget | $0.07 | $0.20 | $0.15 | -2% | -5% |
| 3 | Gemini 3.6 Flash | Google | Standard | $0.07 | $0.30 | $0.21 | -8% | -12% |
| 4 | GPT-4o-mini | OpenAI | Standard | $0.15 | $0.60 | $0.42 | 0% | 0% |
| 5 | GLM-5.2 | TensorX | Frontier | $1.50 | $4.50 | $3.30 | 0% | 0% |
| 6 | Mistral Large 2407 | Mistral | Standard | $2.00 | $6.00 | $4.40 | 0% | -3% |
| 7 | Grok 4.5 | xAI | Frontier | $3.45 | $3.45 | $3.45 | -1% | -2% |
| 8 | GPT-5.6 | OpenAI | Frontier | $5.00 | $15.00 | $11.00 | 0% | -5% |
| 9 | Claude Sonnet 5 | Anthropic | Standard | $3.00 | $15.00 | $10.20 | -2% | -4% |
| 10 | Claude Opus 5 | Anthropic | Frontier | $10.00 | $50.00 | $34.00 | -1% | -3% |

### Biggest Movers
| Gainers | % | Losers | % |
|---------|---|--------|---|
| DeepSeek V4 Flash | +5.2% | Gemini 3.6 Flash | -8.1% |
| Mistral Large | +2.1% | Groq Llama 3.2 | -4.3% |
| GPT-5.6 | +1.8% | Claude Sonnet 5 | -3.2% |
| GLM-5.2 | +0.9% | Gemini 2.5 Pro | -2.8% |
| Kimi K3 | +0.5% | Nemotron 3 | -2.1% |

### Sparkline Data (30-day SIT-Composite, daily close)
```
3.62, 3.58, 3.51, 3.49, 3.44, 3.40, 3.35, 3.31, 3.28, 3.30,
3.25, 3.21, 3.18, 3.15, 3.12, 3.08, 3.05, 3.02, 2.99, 2.96,
2.94, 2.91, 2.89, 2.87, 2.85, 2.84, 2.86, 2.85, 2.84, 2.84
```

---

## Technical Constraints

1. **Single self-contained HTML file.** All CSS in `<style>`, all JS in `<script>`. No external dependencies except Google Fonts.
2. **No JavaScript framework.** Vanilla JS only for table sorting, filtering, and sparkline rendering.
3. **Server-rendered friendly.** The HTML should work as a static page. Data is embedded in the page, not fetched via API.
4. **Dark theme only.** No light mode toggle.
5. **Responsive.** Works from 320px to 1920px.
6. **Fast.** No render-blocking resources. Google Fonts loaded with `font-display: swap`.
7. **Accessible.** Semantic HTML. ARIA labels on sortable table headers. Sufficient contrast (WCAG AA). Keyboard navigable table.

---

## Deliverable

One HTML file. Self-contained. Dark theme. Data-dense. Looks like a financial data product, not a SaaS landing page.

The page should feel like Bloomberg or a trading terminal: dark, dense, fast, authoritative. The gold accent on the headline number is the only decoration. Everything else is data.
