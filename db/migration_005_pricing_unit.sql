-- Migration 005: Add pricing_unit to models and price_snapshots
-- Supports different pricing units for non-token modalities
-- Default: 'per_million_tokens' (existing text/embedding models)
-- Other: 'per_minute' (TTS/STT), 'per_image' (image gen), 'per_second' (video gen)

ALTER TABLE models ADD COLUMN IF NOT EXISTS pricing_unit TEXT DEFAULT 'per_million_tokens';
ALTER TABLE price_snapshots ADD COLUMN IF NOT EXISTS pricing_unit TEXT DEFAULT 'per_million_tokens';
