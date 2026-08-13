-- Migration 004: Add embedding_dimensions to models table
-- For embedding models, stores the vector dimension (e.g. 1536, 3072)
-- NULL for non-embedding models

ALTER TABLE models ADD COLUMN IF NOT EXISTS embedding_dimensions INTEGER;

-- Update existing Jina embedding models with known dimensions
UPDATE models SET embedding_dimensions = 768 WHERE id = 'jina-ai/jina-embeddings-v2-base-en';
UPDATE models SET embedding_dimensions = 768 WHERE id = 'jina-ai/jina-embeddings-v2-base-de';
UPDATE models SET embedding_dimensions = 768 WHERE id = 'jina-ai/jina-embeddings-v2-base-zh';
UPDATE models SET embedding_dimensions = 768 WHERE id = 'jina-ai/jina-embeddings-v2-base-es';
UPDATE models SET embedding_dimensions = 768 WHERE id = 'jina-ai/jina-embeddings-v2-base-code';
UPDATE models SET embedding_dimensions = 768 WHERE id = 'jina-ai/jina-embedding-b-en-v1';
UPDATE models SET embedding_dimensions = 1024 WHERE id = 'jina-ai/jina-embeddings-v3';
UPDATE models SET embedding_dimensions = 1024 WHERE id = 'jina-ai/jina-colbert-v2';
UPDATE models SET embedding_dimensions = 768 WHERE id = 'jina-ai/jina-colbert-v1-en';
UPDATE models SET embedding_dimensions = 384 WHERE id = 'jina-ai/jina-code-embeddings-0.5b';
UPDATE models SET embedding_dimensions = 768 WHERE id = 'jina-ai/jina-code-embeddings-1.5b';
UPDATE models SET embedding_dimensions = 1536 WHERE id = 'jina-ai/jina-embeddings-v5-text-small';
UPDATE models SET embedding_dimensions = 768 WHERE id = 'jina-ai/jina-embeddings-v5-text-nano';
