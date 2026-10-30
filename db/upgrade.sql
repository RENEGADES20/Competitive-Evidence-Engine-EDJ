-- Idempotent schema additions, safe to run any number of times.
-- Runs after db/schema.sql on a new volume, and after every restore (restore.ps1 / restore.sh),
-- so a snapshot built before the addition still gets it.

-- #123: vectors for hybrid retrieval (ADR-001 revisit). 384 dims = BAAI/bge-small-en-v1.5 (#124).
CREATE EXTENSION IF NOT EXISTS vector;
ALTER TABLE chunks ADD COLUMN IF NOT EXISTS embedding vector(384);
CREATE INDEX IF NOT EXISTS chunks_embedding_idx ON chunks USING hnsw (embedding vector_cosine_ops);
