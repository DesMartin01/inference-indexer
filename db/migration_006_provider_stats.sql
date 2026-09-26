-- Migration: provider_stats matview for /v1/providers
-- Date: 2026-09-26
-- Purpose: /v1/providers was a 3-CTF live aggregate over 90K endpoint rows,
-- ~900ms in DB (cold: multi-second, and 96s once on a cold Supabase cache
-- after API restart). Precomputing hourly in the pipeline makes the endpoint
-- a single matview read (~10ms), same pattern as latest_prices.
--
-- NOTE: REFRESH MATERIALIZED VIEW CONCURRENTLY requires a unique index on
-- provider_name. Created below.
--
-- Run once in the Supabase SQL editor or via psql.

CREATE MATERIALIZED VIEW IF NOT EXISTS provider_stats AS
WITH endpoint_models AS (
    SELECT
        me.endpoint_provider AS provider_name,
        COUNT(DISTINCT me.model_id) AS endpoint_count
    FROM model_endpoints me
    JOIN models m ON me.model_id = m.id
    WHERE m.is_active = TRUE AND m.id NOT LIKE '%:batch'
    GROUP BY me.endpoint_provider
),
latest_ep AS (
    -- Current price of each distinct model as served by each endpoint
    -- provider (latest fetched within 3 days), so pricing reflects the
    -- models the provider actually serves - not just models it "owns".
    SELECT DISTINCT ON (endpoint_provider, model_id)
        endpoint_provider AS provider_name,
        model_id,
        blended_price_per_m AS bpm
    FROM model_endpoints
    WHERE fetched_at > NOW() - INTERVAL '3 days'
      AND blended_price_per_m > 0
    ORDER BY endpoint_provider, model_id, fetched_at DESC
),
direct_models AS (
    SELECT
        p.name AS provider_name,
        COUNT(DISTINCT csv.model_id) AS priced_models,
        ROUND(AVG(csv.bpm)::numeric, 4) AS avg_price,
        ROUND(MIN(csv.bpm)::numeric, 4) AS min_price,
        ROUND(MAX(csv.bpm)::numeric, 4) AS max_price,
        COUNT(DISTINCT CASE WHEN m.aa_index_score IS NOT NULL THEN csv.model_id END) AS with_aa
    FROM providers p
    LEFT JOIN latest_ep csv ON csv.provider_name = p.name
    LEFT JOIN models m ON m.id = csv.model_id
    GROUP BY p.name
)
SELECT
    p.name AS provider_name,
    p.is_zdr,
    p.is_eu_sovereign,
    p.zdr_notes,
    p.eu_notes,
    COALESCE(dm.priced_models, 0) AS model_count,
    dm.avg_price,
    dm.min_price,
    dm.max_price,
    COALESCE(dm.with_aa, 0) AS with_aa,
    COALESCE(em.endpoint_count, 0) AS endpoint_count
FROM providers p
LEFT JOIN direct_models dm ON p.name = dm.provider_name
LEFT JOIN endpoint_models em ON p.name = em.provider_name
WHERE COALESCE(dm.priced_models, 0) > 0 OR COALESCE(em.endpoint_count, 0) > 0;

CREATE UNIQUE INDEX IF NOT EXISTS idx_provider_stats_name
  ON provider_stats (provider_name);
