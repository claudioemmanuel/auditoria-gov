-- pgvector extension is required for embedding storage.
-- This is installed on the official pgvector image automatically;
-- the explicit CREATE is kept here as a safety net for custom images.
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
