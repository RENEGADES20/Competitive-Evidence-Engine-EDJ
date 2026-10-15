# Decisions (ADRs)

Short architecture decision records. Ground rules and invariants: [CLAUDE.md](../CLAUDE.md).

## How to add an ADR

1. Copy the block below, give it the next number, set Status to `Proposed`.
2. Open a PR that changes only this file (plus the spec it affects). Tag the tech lead.
3. When merged, Status becomes `Accepted`. To reverse a decision, write a new ADR that
   supersedes the old one; do not edit history.

```
## ADR-NNN: Title
Status: Proposed | Accepted | Superseded by ADR-NNN | Open
Context: why this came up (link question IDs).
Decision: what we do.
Consequences: what gets easier, what gets harder.
```

---

## ADR-000: Licensed data terms
Status: Superseded by ADR-007 (2026-10-14)
Context: Capital IQ and Bloomberg (tier 1) are the highest-value sources, but extracting
data into a tool other people query differs from viewing it at a licensed seat. Trade-press
sites (tier 4) have terms of service that may forbid scraping or storing full text.
Decision: Get a written answer for Capital IQ, Bloomberg and each trade-press site we plan
to use: may we extract, store full text, show excerpts? Until then, nothing from tier 1 is
ingested, and the design must pass the acceptance bar using tiers 2-5 alone.
Consequences: If terms are restrictive, tier 1 stays out and trade press may be stored as
metadata + excerpt + link only. No code path may depend on tier 1.

## ADR-001: Postgres full-text search first
Status: Accepted
Context: The brief says prove the need before adding semantic search. Most questions name
firms, metrics and terms that FTS handles well with a synonym list.
Decision: Phase 1 uses Postgres `tsvector` + synonyms only. `chunks.embedding` exists but
stays NULL. Hybrid search (pgvector + RRF) needs a comparison run on the question bank
showing FTS misses.
Consequences: Simple, debuggable SQL for S1. Paraphrase-heavy thematic questions may lag
until the comparison justifies hybrid.

## ADR-002: Citation scheme
Status: Accepted
Context: Citations must point only at stored chunks and must work with Claude or OpenAI.
Decision: Primary format is our own Answer JSON (see ARCHITECTURE.md). Claude produces it via
tool use, OpenAI via Structured Outputs. Our own validator checks every `chunk_id` against the
retrieved set and runs the number check. Anthropic's Citations API is an optional, Claude-only
enhancement, never a dependency.
Consequences: Provider can be switched in `.env`. We own the validator code.

## ADR-003: One LLM call per answer by default
Status: Accepted
Context: Multi-step agent chains are slower, harder to debug and harder to cite.
Decision: Retrieval is deterministic; the answer comes from a single LLM call. Any
multi-call design (map-reduce, sub-question decomposition, LLM routing) needs a new ADR
with eval evidence.
Consequences: Reproducible answers; very large head-to-head questions may need tighter quotas.

## ADR-004: Hard filters in the retrieval layer, three modes, segment
Status: Accepted
Context: Trap questions Q4, Q27, Q30: BAC material presented as Merrill reads well and is wrong.
Decision: Entity, segment and time window are SQL filters. `chunks.segment` is tagged at
chunking time. Retrieval mode (`entity`, `theme`, `entity+theme`) is chosen by deterministic
rules. Per-entity quotas in multi-firm questions.
Consequences: The LLM cannot see ineligible chunks. Segment tagging quality (C1) becomes
critical and must be tested.

## ADR-005: PDF parsing tool
Status: Accepted (install check: TL machine done 2026-09-30; other six machines in #14)
Context: Investor-day decks and supplements are PDFs with tables; page numbers are needed.
Decision: Use docling. plans/0001 verifies it installs on all 7 team machines (Windows);
where it does not, fall back to pymupdf. EDGAR documents come via edgartools.
Consequences: One parser interface; the fallback may lose table structure.
Install check (`src/cee/ingest/pdf.py`, `parse_pdf(path) -> [(section, page, text)]`):
- TL machine (Windows 11, Python 3.11.9, docling 2.131.0, CPU only): installs from
  `requirements-ingest.txt`; a 10-page PDF parsed in ~2 min on first run (model download,
  ~0.5 GB, goes to `HF_HOME`), every item carries its page number. pymupdf fallback: 8 s,
  page numbers kept, no table structure.
- Only corpus owners need docling (`requirements-ingest.txt`); everyone else installs the core
  `requirements.txt` and works from snapshots, so a failed docling install blocks nobody.

## ADR-006: Shared corpus
Status: Accepted
Context: Seven laptops must see the same corpus without a paid server.
Decision:
- Raw files in the team WashU OneDrive/Box folder: `raw/<entity>/<doc_id>.<ext>`.
- `data/manifest.csv` in git (one row per document, with sha256).
- Weekly, the tech lead rebuilds the database from `main` and publishes
  `snapshots/corpus-YYYY-MM-DD.dump` (pg_dump) to the shared folder.
- One `restore` command loads it into each person's local Docker Postgres.
- Corpus owners debug ingestion locally; changes go through PR and appear in the next snapshot.
Consequences: Zero cost, reproducible scoring (scores record the snapshot). Corpus changes
reach others with up to a week of lag.
Implementation (plans/0001, 2026-09-30):
- Only the tech lead runs Box Drive (`CORPUS_SHARE_PATH`). Teammates use two Box links shared
  in the team chat, never in this public repo: a download link and an upload link (File Request).
- `raw/` is flat (`raw/<doc_id>.<ext>`) because File Request cannot target subfolders;
  manifest `storage_path` is relative (`raw/<doc_id>.<ext>`). Dumps live in `snapshots/`.
- File lookup order: `$CORPUS_SHARE_PATH/<storage_path>` (skipped when empty), then
  `data/<storage_path>` in the repo, else an error that points to the Box link.
- `scripts\build-snapshot.ps1` checks sha256 for every row before touching the database and
  stamps the snapshot name on the database (shown by `python -m cee.smoke`);
  `scripts\restore.ps1` loads the newest dump from Box Drive or `snapshots\`.

## ADR-007: Source use for an internal, non-commercial prototype
Status: Accepted (2026-10-14, tech lead; supersedes ADR-000)
Context: ADR-000 waited for written terms. The C2 source matrix (PR #19, `docs/SOURCE_MATRIX.md`)
listed the open terms questions T-01 to T-09 (#9). This is a personal, internal, non-commercial
student project. It is not an Edward Jones deliverable; if they ever use it, their own staff
review it for compliance first.
Decision:
- T-01 Use: internal and non-commercial. No permission requests are needed.
- T-02 Permission: none. Firm sites (edwardjones.com included) may be collected.
- T-03 EDGAR copies: when a document is also filed with the SEC (e.g. 8-K exhibit 99.1), take
  the EDGAR copy; otherwise the IR site. C1 owns 10-K/10-Q/supplements; C2 owns IR, press and
  8-K exhibits.
- T-04 Transcripts: any third-party source or the company IR page; if none exists, we
  transcribe the call ourselves (webcast audio).
- T-05 Tier: transcripts are tier 3 (`IR`) whoever published them.
- T-06 Trade press: full text may be stored. It stays tier 4, "indicative only".
- T-07 LLM: stored passages may be sent to the LLM at answer time.
- T-08 Automated access: scraping is allowed, including behind robots.txt disallows and bot
  walls; manual download is fine too. Be polite (honest user agent, a delay per site) so we
  are not blocked.
- T-09 Undated pages: `published_at` comes from the source, in this order: a date printed on
  the page, page metadata (modified/updated), the HTTP `Last-Modified` header, the earliest
  Wayback Machine capture. Only when none exists use the download date, and mark the document
  `date_basis = retrieved` (field added in W5). Such pages are excluded from recency windows
  (Q26, Q27), and answers say "page content as of <date>".
- Tier 1: Bloomberg terminal (and Capital IQ) exports may be ingested when the team downloads
  them; they are stored as tier 1 `licensed` with a manifest row like any other document.
- Cerulli and other library research (C3) may be stored in full.
Consequences: No ingestion waits on terms. The design no longer has to clear the bar with
tiers 2-5 alone. Unchanged: raw documents and dumps never go into this public repository
(Box only), every document has a manifest row, and every citation shows its tier label.

