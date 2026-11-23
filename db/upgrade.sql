-- Idempotent core schema additions, safe to run any number of times.
-- Runs after db/schema.sql on a new volume, and after every restore (restore.ps1 / restore.sh),
-- so a snapshot built before an addition still gets it.
--
-- Core only: no extension, no vector type (ADR-009). Vectors live in db/optional/vectors.sql,
-- applied only when CEE_VECTORS=on.

-- #289: the unused facts table of #285 (ADR-022, Deferred; code removed) is dropped from older volumes and dumps.
-- Remove this line if a facts table is revived.
DROP TABLE IF EXISTS facts;
