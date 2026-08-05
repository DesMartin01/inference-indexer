-- InferenceIndexer.ai - Migration: Add model_endpoints table for multi-provider pricing
-- Date: 2026-08-05
-- Purpose: Store per-provider prices so we can compute median price across all providers

-- ============================================
-- MODEL_ENDPOINTS: per-provider pricing for each model
-- ============================================
CREATE TABLE IF NOT EXISTS model_endpoints (
  id BIGSERIAL PRIMARY KEY,
  model_id TEXT NOT NULL REFERENCES models(id),
  endpoint_provider TEXT NOT NULL,        -- "Together AI", "Groq", "Fireworks" etc.
  input_price_per_m FLOAT,
  output_price_per_m FLOAT,
  blended_price_per_m FLOAT,
  context_length INTEGER,
  source TEXT NOT NULL DEFAULT 'openrouter',  -- API source
  raw_data JSONB,                            -- full endpoint response
  fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_model_endpoints_model_time ON model_endpoints(model_id, fetched_at DESC);
CREATE INDEX IF NOT EXISTS idx_model_endpoints_model_latest ON model_endpoints(model_id, endpoint_provider);

-- Enable RLS (public read)
ALTER TABLE model_endpoints ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public can read model endpoints"
  ON model_endpoints FOR SELECT
  USING (true);

-- ============================================
-- Add source_count to price_snapshots
-- ============================================
ALTER TABLE price_snapshots ADD COLUMN IF NOT EXISTS source_count INTEGER DEFAULT 1;
