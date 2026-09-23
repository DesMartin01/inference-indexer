-- Migration 004: recommendation_stats
-- Powers the homepage engine receipts counter ("N recommendations served")
-- and anonymous demand measurement. PRIVACY RULE (V6-Homepage-PRD section 5):
-- structured constraint tuples ONLY. No free text, no query content, ever.
-- One row per /v1/recommend computation (cache MISS only; cache HITs are the
-- same answer and are not re-counted).

CREATE TABLE IF NOT EXISTS recommendation_stats (
  id           BIGSERIAL PRIMARY KEY,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  -- constraint tuple (all fields mirror RecommendRequest; NULL = not set)
  budget_max_usd_per_m NUMERIC,
  context_min          INTEGER,
  modality             TEXT,
  zdr                  BOOLEAN NOT NULL DEFAULT FALSE,
  eu_sovereign         BOOLEAN NOT NULL DEFAULT FALSE,
  reasoning            BOOLEAN,          -- NULL = any
  use_case             TEXT,
  providers_n          INTEGER NOT NULL DEFAULT 0,  -- count only, never names? no: names are not user data
  limit_n              INTEGER NOT NULL DEFAULT 5,
  -- outcome
  result_count         INTEGER NOT NULL DEFAULT 0,
  top_cost_iq          NUMERIC,
  served_via           TEXT NOT NULL DEFAULT 'public',  -- public | ssr | free | paid
  cache_hit            BOOLEAN NOT NULL DEFAULT FALSE
);

-- Counter reads: single-row aggregate index
CREATE INDEX IF NOT EXISTS idx_recommendation_stats_created ON recommendation_stats (created_at DESC);

-- Receipts counter helper (total recommendations served all-time)
CREATE OR REPLACE VIEW recommendation_stats_total AS
SELECT COUNT(*)::INT AS total_recommendations FROM recommendation_stats;
