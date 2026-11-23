-- Idempotent core schema additions, safe to run any number of times.
-- Runs after db/schema.sql on a new volume, and after every restore (restore.ps1 / restore.sh),
-- so a snapshot built before an addition still gets it.
--
-- Core only: no extension, no vector type (ADR-009). Vectors live in db/optional/vectors.sql,
-- applied only when CEE_VECTORS=on.

-- Facts table (#285, ADR-022): metric figures extracted once at ingest by a model, kept only after code checks,
-- stored in config/facts.jsonl and loaded by `python -m cee.facts load`. Entity and segment come from the chunk.
CREATE TABLE IF NOT EXISTS facts (
  fact_id         text PRIMARY KEY,
  chunk_id        text NOT NULL REFERENCES chunks ON DELETE CASCADE,
  doc_id          text NOT NULL,
  entity_id       text,
  segment         text,
  metric          text NOT NULL,
  label           text NOT NULL,
  scope           text NOT NULL DEFAULT '',
  period          text NOT NULL,
  period_end      date NOT NULL,
  period_type     text NOT NULL CHECK (period_type IN ('point', 'quarter', 'year')),
  value           text NOT NULL,
  value_num       double precision,
  unit            text NOT NULL,
  basis           text NOT NULL,
  quote           text NOT NULL,
  extract_version text NOT NULL,
  model           text NOT NULL
);
CREATE INDEX IF NOT EXISTS facts_metric_idx ON facts (metric, entity_id);
