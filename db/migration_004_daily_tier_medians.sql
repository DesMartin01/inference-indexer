-- ============================================
-- Migration 004: Daily-stable SIT tier medians
--
-- Per-model SIT scores divide by the tier median of SIT-adjusted prices.
-- When that median was recomputed from the transient hourly run set, catalog
-- churn moved the median and every score fluctuated within a single day with
-- no price change. This table persists ONE median per tier per UTC date, so
-- all hourly runs that day share the same reference and scores stay stable.
--
-- The pipeline computes+stores today's median on the first run of a UTC date
-- (or the 3am full run) and reads the stored value thereafter.
-- ============================================

CREATE TABLE IF NOT EXISTS daily_tier_medians (
  id BIGSERIAL PRIMARY KEY,
  date DATE NOT NULL,
  tier TEXT NOT NULL,
  sit_adjusted_median FLOAT NOT NULL,
  model_count INTEGER NOT NULL DEFAULT 0,
  calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(date, tier)
);

-- Public read access (consistent with other read-only data tables)
ALTER TABLE daily_tier_medians ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public can read daily tier medians"
  ON daily_tier_medians FOR SELECT
  USING (true);