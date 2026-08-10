-- InferenceIndexer.ai - Provider Quality Snapshots Table
-- Phase 1 of the Quality Metrics Plan (latency + reliability probing)
-- Run this in the Supabase SQL Editor.
-- Date: 2026-08-09

-- ============================================
-- PROVIDER_LATENCY_SNAPSHOTS: per-probe latency + reliability data
-- ============================================
CREATE TABLE provider_latency_snapshots (
  id BIGSERIAL PRIMARY KEY,
  provider TEXT NOT NULL,                     -- endpoint_provider name, e.g. "TensorX"
  probe_model TEXT NOT NULL,                  -- canonical model id probed
  ttft_ms FLOAT,                              -- time to first token, milliseconds
  throughput_tps FLOAT,                       -- approximate output tokens/sec from stream
  http_status INT,                            -- HTTP status returned by the provider
  success BOOLEAN NOT NULL DEFAULT FALSE,     -- got at least one content token
  error_type TEXT,                            -- 'timeout'|'rate_limit'|'5xx'|'http_*'|'connection'|'no_content'
  probed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_provider_latency_provider_time
  ON provider_latency_snapshots (provider, probed_at DESC);

-- ============================================
-- ROW LEVEL SECURITY (same pattern as price_snapshots)
-- ============================================
ALTER TABLE provider_latency_snapshots ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public can read provider latency"
  ON provider_latency_snapshots FOR SELECT
  USING (true);