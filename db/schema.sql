-- InferenceIndexer.ai - Database Schema
-- Run this in the Supabase SQL Editor
-- Version: 1.0
-- Date: 2026-08-04

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================
-- 1. MODELS: master list of tracked models
-- ============================================
CREATE TABLE models (
  id TEXT PRIMARY KEY,                          -- e.g. "openai/gpt-5.6"
  name TEXT NOT NULL,                           -- "GPT-5.6"
  provider TEXT NOT NULL,                       -- "OpenAI"
  tier TEXT NOT NULL,                           -- "frontier" | "standard" | "budget" | "micro"
  context_length INTEGER,
  aa_index_score FLOAT,                         -- Artificial Analysis Intelligence Index
  modality TEXT,                                -- "text" | "text+image->text" etc.
  tokenizer TEXT,
  is_reasoning BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  is_active BOOLEAN DEFAULT TRUE
);

-- ============================================
-- 2. PRICE_SNAPSHOTS: hourly price data per model
-- ============================================
CREATE TABLE price_snapshots (
  id BIGSERIAL PRIMARY KEY,
  model_id TEXT NOT NULL REFERENCES models(id),
  source TEXT NOT NULL,                         -- "openrouter" | "openai_direct" etc.
  input_price_per_m FLOAT NOT NULL,             -- USD per million input tokens
  output_price_per_m FLOAT NOT NULL,            -- USD per million output tokens
  blended_price_per_m FLOAT NOT NULL,           -- 0.4 * input + 0.6 * output
  sit_score FLOAT,                              -- blended / tier avg (calculated in SIT job)
  raw_data JSONB,                               -- full API response for this model
  fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  is_anomalous BOOLEAN DEFAULT FALSE,
  reviewed_at TIMESTAMPTZ
);

CREATE INDEX idx_price_snapshots_model_time ON price_snapshots(model_id, fetched_at DESC);
CREATE INDEX idx_price_snapshots_time ON price_snapshots(fetched_at DESC);
-- CREATE INDEX idx_price_snapshots_fetched_date ON price_snapshots((fetched_at::date));

-- ============================================
-- 3. SIT_INDEX_VALUES: daily calculated indices
-- ============================================
CREATE TABLE sit_index_values (
  id BIGSERIAL PRIMARY KEY,
  date DATE NOT NULL,
  tier TEXT NOT NULL,                           -- "composite" | "frontier" | "standard" | "budget"
  sit_price FLOAT NOT NULL,                     -- dollar price ($/M tokens)
  sit_index_points FLOAT NOT NULL,              -- rebased to 1000 at base date (2026-08-03)
  model_count INTEGER NOT NULL,
  provider_count INTEGER NOT NULL,
  calculation_method TEXT NOT NULL DEFAULT 'equal_weight',
  calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(date, tier)
);

-- ============================================
-- 4. API_USERS: email signup for API keys
-- ============================================
CREATE TABLE api_users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT NOT NULL UNIQUE,
  api_key TEXT NOT NULL UNIQUE,
  plan TEXT NOT NULL DEFAULT 'free',            -- "free" | "paid"
  created_at TIMESTAMPTZ DEFAULT NOW(),
  last_accessed_at TIMESTAMPTZ,
  request_count INTEGER DEFAULT 0,
  rate_limit_per_day INTEGER DEFAULT 1000
);

-- ============================================
-- 5. ALERT_SUBSCRIBERS: Telegram/Twitter distribution
-- ============================================
CREATE TABLE alert_subscribers (
  id BIGSERIAL PRIMARY KEY,
  platform TEXT NOT NULL,                       -- "telegram" | "twitter"
  chat_id TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  is_active BOOLEAN DEFAULT TRUE
);

-- ============================================
-- 6. ANOMALIES: flagged price movements
-- ============================================
CREATE TABLE anomalies (
  id BIGSERIAL PRIMARY KEY,
  model_id TEXT NOT NULL REFERENCES models(id),
  previous_price FLOAT,
  new_price FLOAT,
  change_pct FLOAT,
  detected_at TIMESTAMPTZ DEFAULT NOW(),
  resolved_at TIMESTAMPTZ,
  resolution TEXT                               -- "confirmed" | "reverted" | "error"
);

-- ============================================
-- VIEWS
-- ============================================

-- Latest price per model (for API + homepage)
CREATE OR REPLACE VIEW latest_prices AS
SELECT DISTINCT ON (model_id)
  model_id,
  input_price_per_m,
  output_price_per_m,
  blended_price_per_m,
  sit_score,
  source,
  fetched_at
FROM price_snapshots
ORDER BY model_id, fetched_at DESC;

-- 24h change per model
-- Baselines against the snapshot closest to exactly 24h ago (within a 6h-48h
-- search window) so the change window is a stable rolling 24h - not "newest
-- snapshot older than 20h", which made movers drop off before a day elapsed.
CREATE OR REPLACE VIEW price_changes_24h AS
WITH latest AS (
  SELECT DISTINCT ON (model_id)
    model_id,
    blended_price_per_m,
    fetched_at
  FROM price_snapshots
  ORDER BY model_id, fetched_at DESC
),
previous AS (
  SELECT DISTINCT ON (model_id)
    model_id,
    blended_price_per_m AS prev_price
  FROM price_snapshots
  WHERE fetched_at BETWEEN NOW() - INTERVAL '48 hours' AND NOW() - INTERVAL '6 hours'
  ORDER BY model_id, ABS(EXTRACT(EPOCH FROM (fetched_at - (NOW() - INTERVAL '24 hours'))))
)
SELECT
  l.model_id,
  l.blended_price_per_m,
  p.prev_price,
  ROUND(
    CASE WHEN p.prev_price > 0 AND p.prev_price IS NOT NULL
      THEN CAST(((l.blended_price_per_m - p.prev_price) / p.prev_price) * 100 AS NUMERIC(10,2))
      ELSE 0
    END
  ) AS change_24h_pct
FROM latest l
LEFT JOIN previous p ON l.model_id = p.model_id;

-- ============================================
-- ROW LEVEL SECURITY
-- ============================================

-- Public read access on prices and SIT values
ALTER TABLE price_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE sit_index_values ENABLE ROW LEVEL SECURITY;
ALTER TABLE models ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public can read latest prices"
  ON price_snapshots FOR SELECT
  USING (true);

CREATE POLICY "Public can read SIT values"
  ON sit_index_values FOR SELECT
  USING (true);

CREATE POLICY "Public can read models"
  ON models FOR SELECT
  USING (true);

-- API users table: only service role can read/write
ALTER TABLE api_users ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role manages API users"
  ON api_users FOR ALL
  USING (auth.role() = 'service_role');

-- Alert subscribers: only service role
ALTER TABLE alert_subscribers ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role manages subscribers"
  ON alert_subscribers FOR ALL
  USING (auth.role() = 'service_role');
