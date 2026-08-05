# Claude Design Brief: InferenceIndexer.ai API Docs Page

**Project:** InferenceIndexer.ai
**Deliverable:** API documentation page HTML (single self-contained file)
**Date:** August 2026

---

## What This Page Is

The API documentation page. Developers come here to get an API key, see available endpoints, read response formats, and copy code examples. Think Stripe API docs or CoinGecko API docs, not a wall of text. Clean, scannable, code-first.

**The audience:** developers who want to pull inference pricing data programmatically. They need to find the endpoint, see the response shape, copy a curl command, and go.

---

## Design Direction

Same design system as homepage and model detail page:
- Dark background (#0a0a0a)
- Surface/cards (#1a1a1a, border #2a2a2a)
- Gold accent (#C4A038) for headings and links
- Monospace for all code and endpoint URLs (JetBrains Mono)
- Inter for body text
- Green (#4ade80) for success/status codes, red (#ef4444) for errors

### Layout: Two-Column with Sticky Sidebar

Unlike the homepage (single column) and model detail (single column), the API docs page uses a two-column layout:
- **Left sidebar:** Navigation. List of sections. Sticky, scrolls independently. Like Stripe docs.
- **Right main content:** The actual documentation content. Scrolls normally.

---

## Page Structure

### 1. Top Bar (same as other pages)

```
[Logo: InferenceIndexer.ai]     [Search models...]     [API] [Methodology] [About] [Login] [Sign Up]  [LIVE ●]
```

### 2. Page Title

```
API Documentation
Free inference pricing data. 1,000 requests/day with a free API key.
```

- "API Documentation": 28px, white, bold.
- Subtitle: 14px, muted grey.
- Below subtitle: a "Get API Key" button. Gold background (#C4A038), dark text, 14px, padding 8px 16px, border-radius 6px. Links to signup.

### 3. Two-Column Layout

```
┌──────────────────┬──────────────────────────────────────────────────────────────┐
│ SIDEBAR (sticky) │ MAIN CONTENT                                                 │
│                  │                                                              │
│ Authentication   │  ─── Authentication ───                                      │
│ Endpoints        │  ...                                                         │
│  /sit/composite  │                                                              │
│  /sit/tier/{t}   │  ─── Endpoints ───                                           │
│  /models         │  ...                                                         │
│  /models/{id}    │                                                              │
│  /providers/{p}  │  ─── Rate Limits ───                                         │
│ Rate Limits      │  ...                                                         │
│ Response Format  │                                                              │
│ Errors           │  ─── Response Format ───                                     │
│                  │  ...                                                         │
│                  │                                                              │
│                  │  ─── Errors ───                                              │
│                  │  ...                                                         │
└──────────────────┴──────────────────────────────────────────────────────────────┘
```

**Sidebar specs:**
- Width: 240px on desktop. Hidden on mobile (replaced by a horizontal scroll of section links).
- Sticky: position sticky, top 60px (below nav bar).
- Background: transparent (inherits page #0a0a0a).
- Border-right: 1px #1a1a1a.
- Section headings: 11px, uppercase, letter-spaced, muted grey (#666). Not clickable.
- Endpoint links: 13px, monospace, muted grey (#888). Hover: white. Active: gold (#C4A038).
- Active section highlighted as user scrolls (scrollspy). Gold left border on active item.

### 4. Authentication Section

```
Authentication

API keys are required for all requests. Sign up with your email to get a free key.

1. Click "Get API Key" or go to the Sign Up page
2. Enter your email address
3. Click the magic link in the email
4. Your API key is displayed on the dashboard

Pass your API key in the Authorization header:

┌────────────────────────────────────────────────────────────────────────┐
│ Authorization: Bearer your_api_key_here                               │
└────────────────────────────────────────────────────────────────────────┘

Example:

┌────────────────────────────────────────────────────────────────────────┐
│ $ curl -H "Authorization: Bearer ii_sk_abc123" \                       │
│        https://api.inferenceindexer.ai/v1/sit/composite/latest         │
└────────────────────────────────────────────────────────────────────────┘
```

- Step list: numbered, 14px, white text. Numbers in gold circles (20px diameter, gold background, dark text).
- Code blocks: dark background (#0d0d0d), monospace 12px, border 1px #2a2a2a, border-radius 6px, padding 12px 16px.
- Header name "Authorization" in gold, value in green.
- curl command: "$" prefix in green, URL in white.

### 5. Endpoints Section

Each endpoint is a card. Card has: method badge, path, description, parameters table, example request, example response.

#### Endpoint 1: SIT-Composite Latest

```
GET /v1/sit/composite/latest

Returns the current SIT-Composite index value, including tier breakdowns.

Parameters: None

Example Request:
┌────────────────────────────────────────────────────────────────────────┐
│ $ curl -H "Authorization: Bearer ii_sk_abc123" \                       │
│        https://api.inferenceindexer.ai/v1/sit/composite/latest         │
└────────────────────────────────────────────────────────────────────────┘

Example Response (200 OK):
┌────────────────────────────────────────────────────────────────────────┐
│ {                                                                     │
│   "date": "2026-08-03",                                               │
│   "composite": {                                                      │
│     "price_per_m": 2.84,                                              │
│     "index_points": 784.5,                                            │
│     "change_24h": -1.2,                                               │
│     "change_7d": -3.1,                                                │
│     "change_30d": -12.4                                               │
│   },                                                                  │
│   "tiers": {                                                          │
│     "frontier": { "price_per_m": 35.20, "change_24h": -0.8, "models": 8 }, │
│     "standard": { "price_per_m": 1.25, "change_24h": -1.5, "models": 156 }, │
│     "budget": { "price_per_m": 0.42, "change_24h": -2.1, "models": 78 } │
│   },                                                                  │
│   "spread": { "price_per_m": 34.78, "change_24h": -1.9 }              │
│ }                                                                     │
└────────────────────────────────────────────────────────────────────────┘
```

- Method badge "GET": green background (#22c55e), white text, 11px, bold, padding 2px 8px, border-radius 4px.
- Path: 16px, monospace, white. The `/v1/sit/composite/latest` part is clickable, gold on hover.
- Description: 14px, muted grey, below the path.
- "Parameters: None" in 13px muted grey.
- Code blocks: same styling as auth section.
- JSON response: keys in gold (#C4A038), strings in green, numbers in white. 12px monospace.

#### Endpoint 2: SIT-Composite History

```
GET /v1/sit/composite/history?days=30

Returns historical SIT-Composite values.

Parameters:
┌────────────────────┬──────────┬───────────┬──────────────────────────────────┐
│ Parameter          │ Type     │ Required  │ Description                      │
├────────────────────┼──────────┼───────────┼──────────────────────────────────┤
│ days               │ integer  │ No        │ Number of days to return (default: 30, max: 365) │
│ tier               │ string   │ No        │ Filter to a specific tier: frontier, standard, budget │
└────────────────────┴──────────┴───────────┴──────────────────────────────────┘

Example Response (200 OK):
┌────────────────────────────────────────────────────────────────────────┐
│ {                                                                     │
│   "history": [                                                        │
│     { "date": "2026-08-03", "price_per_m": 2.84, "index_points": 784.5 }, │
│     { "date": "2026-08-02", "price_per_m": 2.87, "index_points": 792.8 }, │
│     ...                                                               │
│   ]                                                                   │
│ }                                                                     │
└────────────────────────────────────────────────────────────────────────┘
```

- Parameter table: 13px, monospace for parameter names and types, sans-serif for descriptions.
- Header row: dark background (#222), white text, 12px uppercase.
- "Required" column: "Yes" in gold, "No" in muted grey.

#### Endpoint 3: List Models

```
GET /v1/models?tier=standard&sort=blended

Returns all tracked models with current pricing.

Parameters:
┌────────────────────┬──────────┬───────────┬──────────────────────────────────┐
│ Parameter          │ Type     │ Required  │ Description                      │
├────────────────────┼──────────┼───────────┼──────────────────────────────────┤
│ tier               │ string   │ No        │ Filter by tier: frontier, standard, budget, micro │
│ provider           │ string   │ No        │ Filter by provider name          │
│ sort               │ string   │ No        │ Sort by: blended, input, output, sit_score (default: sit_score) │
│ limit              │ integer  │ No        │ Max results (default: 50, max: 315) │
└────────────────────┴──────────┴───────────┴──────────────────────────────────┘

Example Response (200 OK):
┌────────────────────────────────────────────────────────────────────────┐
│ {                                                                     │
│   "count": 315,                                                       │
│   "models": [                                                         │
│     {                                                                  │
│       "model_id": "deepseek/deepseek-v4-reasoner",                    │
│       "name": "DeepSeek V4 Reasoner",                                 │
│       "provider": "DeepSeek",                                         │
│       "tier": "frontier",                                              │
│       "input_price_per_m": 0.55,                                      │
│       "output_price_per_m": 2.19,                                     │
│       "blended_price_per_m": 1.53,                                    │
│       "sit_score": 0.04,                                               │
│       "context_length": 128000,                                      │
│       "change_24h": -3.0,                                              │
│       "change_7d": -8.0                                                │
│     },                                                                 │
│     ...                                                                │
│   ]                                                                   │
│ }                                                                     │
└────────────────────────────────────────────────────────────────────────┘
```

#### Endpoint 4: Single Model

```
GET /v1/models/{model_id}

Returns detailed pricing and metadata for a single model.

Parameters:
┌────────────────────┬──────────┬───────────┬──────────────────────────────────┐
│ Parameter          │ Type     │ Required  │ Description                      │
├────────────────────┼──────────┼───────────┼──────────────────────────────────┤
│ model_id           │ string   │ Yes       │ The model ID (e.g. openai/gpt-5.6) │
└────────────────────┴──────────┴───────────┴──────────────────────────────────┘

Example: GET /v1/models/openai/gpt-5.6
```

#### Endpoint 5: Model Price History

```
GET /v1/models/{model_id}/history?days=90

Returns historical price data for a single model.

Parameters:
┌────────────────────┬──────────┬───────────┬──────────────────────────────────┐
│ Parameter          │ Type     │ Required  │ Description                      │
├────────────────────┼──────────┼───────────┼──────────────────────────────────┤
│ model_id           │ string   │ Yes       │ The model ID                     │
│ days               │ integer  │ No        │ Days of history (default: 30, max: 365 on free tier) │
└────────────────────┴──────────┴───────────┴──────────────────────────────────┘
```

### 6. Rate Limits Section

```
Rate Limits

┌──────────────────┬───────────────┬────────────────────┬────────────────────┐
│ Plan             │ Requests/day  │ Requests/minute    │ History access     │
├──────────────────┼───────────────┼────────────────────┼────────────────────┤
│ Public (no key)  │ 100           │ 10                 │ 7 days             │
│ Free (email)     │ 1,000         │ 30                 │ 30 days            │
│ Paid (future)    │ 50,000        │ 100                │ 365 days           │
└──────────────────┴───────────────┴────────────────────┴────────────────────┘

Rate limit headers are included in every response:

┌────────────────────────────────────────────────────────────────────────┐
│ X-RateLimit-Limit: 1000                                                │
│ X-RateLimit-Remaining: 987                                             │
│ X-RateLimit-Reset: 1691078400                                         │
└────────────────────────────────────────────────────────────────────────┘
```

- Table: same styling as homepage model table. Header dark, alternating rows, 13px monospace.
- Code block: header names in gold, numbers in white.

### 7. Response Format Section

```
Response Format

All responses are JSON. Timestamps are ISO 8601 UTC. Prices are in USD per million tokens.

Successful response (200 OK):
┌────────────────────────────────────────────────────────────────────────┐
│ {                                                                     │
│   "data": { ... },                                                    │
│   "meta": {                                                           │
│     "request_id": "req_abc123",                                       │
│     "timestamp": "2026-08-03T15:00:00Z"                               │
│   }                                                                   │
│ }                                                                     │
└────────────────────────────────────────────────────────────────────────┘

Pagination (for list endpoints):
┌────────────────────────────────────────────────────────────────────────┐
│ {                                                                     │
│   "count": 315,                                                       │
│   "page": 1,                                                          │
│   "per_page": 50,                                                     │
│   "total_pages": 7,                                                   │
│   "next": "/v1/models?page=2"                                        │
│ }                                                                     │
└────────────────────────────────────────────────────────────────────────┘
```

### 8. Errors Section

```
Errors

┌──────────────────┬──────────────────────────────────────────────────────────┐
│ Status Code      │ Meaning                                                   │
├──────────────────┼──────────────────────────────────────────────────────────┤
│ 200 OK           │ Success                                                   │
│ 400 Bad Request  │ Invalid parameter (check the error message)              │
│ 401 Unauthorized │ Missing or invalid API key                                │
│ 404 Not Found    │ Model or endpoint doesn't exist                           │
│ 429 Too Many     │ Rate limit exceeded. Check X-RateLimit-Reset header       │
│ 500 Server Error │ Something went wrong on our end. Retry after a few seconds│
└──────────────────┴──────────────────────────────────────────────────────────┘

Error response format:
┌────────────────────────────────────────────────────────────────────────┐
│ {                                                                     │
│   "error": {                                                          │
│     "code": "rate_limit_exceeded",                                    │
│     "message": "Rate limit of 1000 requests/day exceeded. Resets at 2026-08-04T00:00:00Z.", │
│     "documentation_url": "https://inferenceindexer.ai/api/docs#rate-limits" │
│   }                                                                   │
│ }                                                                     │
└────────────────────────────────────────────────────────────────────────┘
```

- Status code table: 200 and 200-series in green. 400/401/404 in amber (#fbbf24). 429/500 in red (#ef4444).
- Error JSON: keys in gold, strings in green.

### 9. Code Examples (Language Tabs)

Below the errors section, a tabbed code block showing the same request in multiple languages:

```
[curl] [Python] [JavaScript] [Go]

┌────────────────────────────────────────────────────────────────────────┐
│ # Python                                                               │
│ import requests                                                        │
│                                                                        │
│ headers = {"Authorization": "Bearer ii_sk_abc123"}                     │
│ response = requests.get(                                               │
│     "https://api.inferenceindexer.ai/v1/sit/composite/latest",         │
│     headers=headers                                                    │
│ )                                                                      │
│ data = response.json()                                                 │
│ print(f"SIT-Composite: ${data['composite']['price_per_m']}/M")        │
└────────────────────────────────────────────────────────────────────────┘
```

- Language tabs: 13px, monospace. Active tab: gold underline, white text. Inactive: muted grey.
- Code block: dark background (#0d0d0d), monospace 12px. Comments (#) in muted grey. Strings in green. Keywords (import, from) in gold.

### 10. Footer (same as other pages)

---

## What NOT to Include

- No testimonials
- No "Why choose us" section
- No pricing comparison table (rate limits table covers this)
- No video tutorials
- No interactive "try it now" console (Phase 2)
- No SDK download links (Phase 2)
- No changelog (Phase 2)
- No status page indicator

---

## Technical Constraints

1. Single self-contained HTML file. All CSS in `<style>`, all JS in `<script>`.
2. Same fonts and colors as homepage and model detail page.
3. Two-column layout with sticky sidebar on desktop. Single column on mobile.
4. No JavaScript framework. Vanilla JS for tab switching and scrollspy.
5. Code blocks should have a copy button (small "Copy" text that appears on hover, top-right of each code block).
6. Dark theme only.
