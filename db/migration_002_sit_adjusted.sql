-- InferenceIndexer.ai - Migration: SIT-Adjusted (v0.3)
-- Date: 2026-08-05
-- Purpose: Add reasoning multiplier and SIT-adjusted price columns to price_snapshots
--          SIT score now reflects cost per unit of intelligence, adjusted for reasoning overhead.

-- ============================================
-- Add SIT-Adjusted columns to price_snapshots
-- ============================================
ALTER TABLE price_snapshots ADD COLUMN IF NOT EXISTS reasoning_multiplier FLOAT DEFAULT 1.0;
ALTER TABLE price_snapshots ADD COLUMN IF NOT EXISTS sit_adjusted_price FLOAT;

-- ============================================
-- Update latest_prices view to include new columns
-- ============================================
CREATE OR REPLACE VIEW latest_prices AS
SELECT DISTINCT ON (model_id)
  model_id,
  input_price_per_m,
  output_price_per_m,
  blended_price_per_m,
  sit_score,
  reasoning_multiplier,
  sit_adjusted_price,
  source,
  source_count,
  fetched_at
FROM price_snapshots
ORDER BY model_id, fetched_at DESC;

-- ============================================
-- Update price_changes_24h view to include new columns
-- Baselines against the snapshot closest to exactly 24h ago (within a 6h-48h
-- search window) so the change window is a stable rolling 24h - not "newest
-- snapshot older than 20h", which made movers drop off before a day elapsed.
-- ============================================
CREATE OR REPLACE VIEW price_changes_24h AS
WITH latest AS (
  SELECT DISTINCT ON (model_id)
    model_id,
    blended_price_per_m,
    sit_score,
    sit_adjusted_price,
    fetched_at
  FROM price_snapshots
  ORDER BY model_id, fetched_at DESC
),
previous AS (
  SELECT DISTINCT ON (model_id)
    model_id,
    blended_price_per_m AS prev_price,
    sit_adjusted_price AS prev_adjusted_price
  FROM price_snapshots
  WHERE fetched_at BETWEEN NOW() - INTERVAL '48 hours' AND NOW() - INTERVAL '6 hours'
  ORDER BY model_id, ABS(EXTRACT(EPOCH FROM (fetched_at - (NOW() - INTERVAL '24 hours'))))
)
SELECT
  l.model_id,
  l.blended_price_per_m,
  l.sit_score,
  l.sit_adjusted_price,
  p.prev_price,
  p.prev_adjusted_price,
  ROUND(
    CASE WHEN p.prev_price > 0 AND p.prev_price IS NOT NULL
      THEN CAST(((l.blended_price_per_m - p.prev_price) / p.prev_price) * 100 AS NUMERIC(10,2))
      ELSE 0
    END
  ) AS change_24h_pct
FROM latest l
LEFT JOIN previous p ON l.model_id = p.model_id;

-- ============================================
-- SECURITY FIX: Enable RLS on anomalies table
-- ============================================
ALTER TABLE anomalies ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role manages anomalies"
  ON anomalies FOR ALL
  USING (auth.role() = 'service_role');

-- ============================================
-- SECURITY FIX: Recreate views with SECURITY INVOKER
-- (Supabase flags SECURITY DEFINER views as a risk)
-- ============================================
-- latest_prices already recreated above via CREATE OR REPLACE,
-- but we need to ensure it uses SECURITY INVOKER.
-- Supavisor pooler doesn't support ALTER VIEW, so we recreate.
-- The views above are already clean (no SECURITY DEFINER in the CREATE statement).
-- But if they were previously created with SECURITY DEFINER by Supabase, we force it:

ALTER VIEW latest_prices SET (security_invoker = true);
ALTER VIEW price_changes_24h SET (security_invoker = true);
