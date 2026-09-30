-- Schema for the Competitive Evidence Engine. Design notes: docs/ARCHITECTURE.md.
-- Applied automatically on the first start of an empty Docker volume.
-- Differences from the ARCHITECTURE.md draft:
--   * no chunks.embedding column yet (ADR-001: FTS first; add it with pgvector when a
--     comparison run justifies hybrid search)
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
