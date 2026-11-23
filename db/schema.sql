-- Schema for the Competitive Evidence Engine. Design notes: docs/ARCHITECTURE.md.
-- Applied automatically on the first start of an empty Docker volume.
-- Differences from the ARCHITECTURE.md draft:
--   * No vector column and no extension (ADR-009): the core runs on plain PostgreSQL.
--     Vectors are an optional module, off by default: db/optional/vectors.sql (CEE_VECTORS=on)
--     adds the separate table chunk_embeddings.
--   * chunks.prefix holds the context prefix; chunks.text holds only the source text,
--     so the source viewer and the number check see the original words.

CREATE TABLE entities (
  entity_id     text PRIMARY KEY,
  name          text NOT NULL,
  parent_id     text REFERENCES entities,
  reported_as   text,
  equivalence   text,
  caveat        text
);

CREATE TABLE documents (
  doc_id        text PRIMARY KEY,
  entity_id     text NULL REFERENCES entities,
  doc_type      text NOT NULL,
  source_tier   int  NOT NULL CHECK (source_tier BETWEEN 1 AND 6),
  published_at  date NOT NULL,
  date_basis    text NOT NULL DEFAULT 'source' CHECK (date_basis IN ('source', 'retrieved')),  -- ADR-007 T-09
  period_end    date,
  url           text,
  storage_path  text NOT NULL,
  sha256        text NOT NULL
);

CREATE TABLE chunks (
  chunk_id      text PRIMARY KEY,
  doc_id        text NOT NULL REFERENCES documents ON DELETE CASCADE,
  seq           int  NOT NULL,
  section       text,
  segment       text NULL,
  page          int,
  prefix        text NOT NULL,
  text          text NOT NULL,
  tsv           tsvector GENERATED ALWAYS AS (to_tsvector('english', prefix || ' ' || text)) STORED
);
CREATE INDEX chunks_tsv_idx ON chunks USING gin (tsv);
CREATE INDEX chunks_doc_idx ON chunks (doc_id);

CREATE TABLE topics       (topic_id text PRIMARY KEY, label text, parent_id text);
CREATE TABLE chunk_topics (chunk_id text REFERENCES chunks ON DELETE CASCADE,
                           topic_id text REFERENCES topics,
                           PRIMARY KEY (chunk_id, topic_id));

CREATE TABLE source_registry (
  entity_id text, doc_type text, source_name text, url_pattern text, expected_cadence text,
  PRIMARY KEY (entity_id, doc_type, source_name)
);

CREATE TABLE query_log      (query_id serial PRIMARY KEY, asked_at timestamptz DEFAULT now(),
                             question text, mode text, filters jsonb, chunk_ids text[],
                             answer jsonb, snapshot text, model text);
CREATE TABLE query_feedback (query_id int REFERENCES query_log, rating int, comment text,
                             created_at timestamptz DEFAULT now());

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
