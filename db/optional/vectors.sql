-- Optional vectors module (ADR-009), off by default. Applied only when CEE_VECTORS=on, by
-- scripts/restore.*, scripts/build-snapshot.* and `python -m cee.retrieve.embed --missing`;
-- never by the Docker init mount. Idempotent: safe to run any number of times.
-- Needs the pgvector extension (the database image in docker-compose.yml has it).
-- 384 dims = BAAI/bge-small-en-v1.5 (#124).

BEGIN;

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS chunk_embeddings (
  chunk_id   text PRIMARY KEY REFERENCES chunks ON DELETE CASCADE,
  embedding  vector(384) NOT NULL
);
CREATE INDEX IF NOT EXISTS chunk_embeddings_hnsw_idx
  ON chunk_embeddings USING hnsw (embedding vector_cosine_ops);

-- One-time move (#144): databases and snapshots from before #144 keep their vectors in
-- chunks.embedding. Copy them, check none is missing, then drop the column (and its index).
DO $$
DECLARE
  missing bigint;
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.columns
             WHERE table_schema = current_schema() AND table_name = 'chunks'
               AND column_name = 'embedding') THEN
    EXECUTE 'INSERT INTO chunk_embeddings (chunk_id, embedding)
             SELECT chunk_id, embedding FROM chunks WHERE embedding IS NOT NULL
             ON CONFLICT (chunk_id) DO NOTHING';
    EXECUTE 'SELECT count(*) FROM chunks c
             WHERE c.embedding IS NOT NULL
               AND NOT EXISTS (SELECT 1 FROM chunk_embeddings e WHERE e.chunk_id = c.chunk_id)'
      INTO missing;
    IF missing > 0 THEN
      RAISE EXCEPTION 'vectors.sql: % chunks.embedding rows were not copied; nothing changed', missing;
    END IF;
    EXECUTE 'ALTER TABLE chunks DROP COLUMN embedding';
    RAISE NOTICE 'vectors.sql: moved chunks.embedding into chunk_embeddings and dropped the column';
  END IF;
END
$$;

COMMIT;
