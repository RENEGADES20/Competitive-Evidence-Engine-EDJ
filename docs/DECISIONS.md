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
Status: Accepted (vectors: optional module, off by default, see ADR-009; hybrid evaluated, not adopted, see ADR-010)
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
Status: Accepted; its single-call default and its "multi-call design needs a new ADR" rule are superseded by ADR-012 (up to 5 LLM calls per user question, one by default). "Retrieval is deterministic" stands.
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
See ADR-018: a home-firm theme question also searches the other covered firms, on the theme only.

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
- Parse cache (#82, plans/0082, `cee.ingest.parse_cache`): docling takes 4-7 min per PDF and
  edgartools seconds per filing, so their output is stored as
  `parsed/<sha256>-<library><version>-v<N>.json` next to `raw/` (Box Drive; `data/parsed/` when
  `CORPUS_SHARE_PATH` is empty) and reused. A changed file (new sha256), a library pin bump or a
  bump of `PARSER_VERSION` (`pdf.py`) / `HTML_PARSER_VERSION` (`load.py`) gives a new name, so that
  file is parsed again; bump the constant with any change to parser output (e.g. #84). Section
  splitting and chunking run after the cache, so they need no bump.
  `python -m cee.ingest.load --no-parse-cache` forces a fresh parse. The pymupdf fallback is not
  cached. Old cache files are never read again and may be deleted.
- Pages from every provenance span (#84, plans/0084, `PARSER_VERSION` 2): a docling item whose
  provenance covers two pages (a text block running onto the next slide) is cut at the charspan
  where the page changes, and each part is stored under its own page. Tables keep their first
  page. docling's own output (the DoclingDocument) is cached as well, as
  `parsed/<sha256>-docling<version>-doc.json`, so a `PARSER_VERSION` bump re-runs our code on it in
  seconds instead of re-running docling. That name does not hold the pipeline options
  (`do_ocr=False`); changing them needs a new name. `scripts/page_sweep.py` checks every PDF chunk
  against the PDF page text.

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

## ADR-009: Core retrieval stays extension-free and model-free; vectors are optional
Status: Accepted (tech lead decision 2026-10-30, #144; hybrid retrieval lives on exp/hybrid only, see ADR-010)
Context: #123/#124 made pgvector, an embedding model and its runtime part of every install:
`db/upgrade.sql` created the `vector` extension and `chunks.embedding` on every new volume and
restore, the snapshot build had to embed every chunk, `requirements.txt` required fastembed and
onnxruntime, and the model downloaded itself when the cache was empty. The sponsor asked that
the core prototype run on plain PostgreSQL with no extension, no embedding model and no model
download at runtime. Vector search may exist, but only as something that can be left out.
Decision: The core (schema, snapshot build, app, eval in `fts` mode) needs none of the vector
work. Vectors are an optional module, off by default, switched on with `CEE_VECTORS=on`:
- core SQL (`db/schema.sql`, `db/upgrade.sql`) has no extension and no vector type; the
  module's SQL is `db/optional/vectors.sql` (pgvector + table `chunk_embeddings`), applied only
  when on, never by the Docker init mount;
- `fastembed`/`onnxruntime` live in `requirements-vectors.txt` and the `[vectors]` extra; CI
  installs `requirements.txt` only;
- the model loads from the cache only; it is downloaded only by the explicit
  `python -m cee.retrieve.embed --fetch`;
- hybrid retrieval (#125) reads `chunk_embeddings` and stays behind `CEE_VECTORS`.
Consequences: A teammate with plain Postgres and no network for models can build, run and
evaluate the prototype. Turning vectors on is a documented set of steps (docs/RUN.md). The
database image keeps pgvector so switching on needs no new image. Snapshots built with vectors
off restore on plain Postgres; older snapshots still carry `chunks.embedding`, which the core
ignores and `vectors.sql` moves into `chunk_embeddings`.

## ADR-010: Hybrid retrieval evaluated; core stays FTS-only
Status: Accepted (tech lead decision 2026-11-05, #127); its EJ-10 parts are superseded by ADR-011: the EJ-10 reason in Context, the ranking limit in Decision, the "Scope of EJ-10 here" bullet, the sponsor-agreement revisit trigger and the Consequences "meets EJ-10" line. The outcome (`main` FTS-only, hybrid code on `exp/hybrid`) stands, now under the branch rule.
Context: ADR-001 allowed hybrid search (pgvector + RRF) only after a comparison run on the
question bank showed FTS misses. The sponsor portability spec (v1.0, 2026-10-29, EJ-10) asks
for no pgvector, embeddings, embedding model, PostgreSQL extension or reranker on `main`;
semantic retrieval may be explored on a branch with the results documented. So #124-#126 built
and measured hybrid retrieval on the long-lived branch `exp/hybrid`: keyword + vector legs fused
by RRF per firm (`hybrid-norerank`), and the same candidates reordered by a local cross-encoder,
Xenova/ms-marco-MiniLM-L-12-v2 (`hybrid`). ADR-003 is unaffected: the cross-encoder is a local
model, not an LLM call. (ADR-008 was reserved for this decision in an early #125 plan and never
used.)

Results (#126 report, snapshot `corpus-2026-10-29`, as of 2026-10-29, k=20, mock provider,
0 real calls, all 30 questions; [report](https://github.com/RENEGADES20/Competitive-Evidence-Engine-EDJ/blob/3449cc52171406a45dfd4d13e39e227adbecd1e3/evals/hybrid-eval/corpus-2026-10-29/report.md),
[summary.json](https://github.com/RENEGADES20/Competitive-Evidence-Engine-EDJ/blob/3449cc52171406a45dfd4d13e39e227adbecd1e3/evals/hybrid-eval/corpus-2026-10-29/summary.json),
both at `exp/hybrid` 3449cc5):

| Mode (FLOOR / MAX_PER_DOC) | PASS / FAIL | Tier-1 docs | Tier-1 passages | Refusal gap / all keyed | Forbidden | Median search |
|---|---|---|---|---|---|---|
| `fts` at `main`'s constants (0.3 / 3) | 28 / 2 | 0.796 | 0.402 | 5/5, 10/10 | 0 | 0.34 s |
| `fts`, tuned pick (0.2 / 3), not adopted | 27 / 3 | 0.782 | 0.474 | 5/5, 10/10 | 0 | 0.34 s |
| `hybrid-norerank`, tuned pick (0.4 / 3) | 28 / 2 | 0.715 | 0.405 | 5/5, 10/10 | 0 | 0.31 s |
| `hybrid` with MiniLM rerank, tuned pick (0.4 / 4) | 28 / 2 | 0.738 | 0.402 | 5/5, 10/10 | 0 | 5.1 s |

- The `fts` rows are `fts` mode on `exp/hybrid`, which equals `main`'s code except the
  `synonym_only: [pay]` config from #125 (only Q29 differs). `main`'s own `fts` on the same
  snapshot (`p125r-fts-main`, Progress log of `plans/0125-hybrid-retrieval.md` on `exp/hybrid`):
  PASS 27 / FAIL 3 (Q15, Q19, Q29), docs 0.796, passages 0.347, refusal gap 4/5. Q29 on `main`
  is a separate TL item; this ADR does not move `synonym_only` to `main`.
- No question that `fts` at `main`'s constants fails is passed by hybrid: both fail Q15 and Q19.
  `fts` has the higher tier-1 doc recall and about the same passage recall. Q17 fails only at
  the `fts` tuned pick (coverage 3/7), which is not adopted.
- The cross-encoder is not reliable on this text. With the same candidates, its tier-1 passage
  recall is lower than plain RRF order at all 12 grid points (0.402 vs 0.405 at the pick; 0.317
  vs 0.389 at MAX_PER_DOC 2). On Q29 it scores a guarantee note (`MS-10K-2025#702`) 0.95 and
  the answer passages `MS-10K-2025#153` and `#170` near 0. It is about 15 times slower on CPU.
- Tuned and scored on the same 30 questions, with no held-out set: one passage is about 0.02
  of passage recall, so small differences are weak evidence.

Decision:
- `fts` is the default and only retrieval mode on `main`. There is no retrieval-mode setting
  on `main`.
- The hybrid code (`hybrid.py`, the mode switch, `RETRIEVAL_MODE`, `synonym_only`) stays on
  `exp/hybrid` and is not merged.
- The `fts` tuned pick (FLOOR 0.2) is reported only. Any change to `fts` constants is a separate
  S1 issue with its own eval; EJ-10 Tier 2 item 3 ("Don't change ranking") and section 4 of the
  sponsor spec (Non-goals: no ranking changes for portability reasons) apply to it.
- Scope of EJ-10 here: `main`'s retrieval path (one mode, no extension, no embedding model, no
  reranker) meets EJ-10. ADR-009's optional vectors module is still on `main`, off by default
  (`db/optional/vectors.sql` with `CREATE EXTENSION vector`, `src/cee/retrieve/embed.py`,
  `requirements-vectors.txt`, `CEE_VECTORS`). Whether it stays is an open decision, tracked by
  the TL, outside this ADR.
- ADR-001's sentence "`chunks.embedding` exists but stays NULL" was already superseded by
  ADR-009 (vectors in `chunk_embeddings`, optional); ADR-001's body stays as written.
- Revisit when any of these holds, with a new ADR that supersedes this one: the sponsor agrees
  in writing to embeddings on `main`; a larger or held-out question set shows questions that
  `fts` misses and hybrid finds, by more than a few passages, with refusal and forbidden hits no
  worse; a reranker beats RRF order on tier-1 passage recall on this corpus.
Consequences: `main` keeps one debuggable SQL retrieval path, and that path meets EJ-10.
Teammates install nothing new; no reinstall and no new snapshot are needed. Questions that need
paraphrase matching may lag if a larger question set shows them (none in this bank at `main`'s
constants). `exp/hybrid` stays as the record and can be brought up to date if the question
reopens.

## ADR-011: Sponsor portability spec no longer binds main; model-based work on a branch
Status: Accepted (tech lead decision 2026-11-16, #182)
Context: ADR-010 gave the sponsor portability spec (v1.0, 2026-10-29, EJ-10) as a reason `main`
stays FTS-only, applied its Tier 2 item 3 and section 4 ("Don't change ranking") to any change
of the `fts` constants, measured `main` against EJ-10 ("Scope of EJ-10 here", Consequences
"meets EJ-10") and named sponsor agreement as one revisit trigger. On 2026-11-16 the tech lead
decided the spec is not a requirement of this project; only model-dependent development is to
stay off `main`.
Decision:
- The portability spec is history. It is not a rule for `main` and not a reason to refuse a
  change. ADR-010's EJ-10 parts (the Context reason, the ranking limit, the "Scope of EJ-10
  here" bullet, the sponsor-agreement revisit trigger, the Consequences "meets EJ-10" line) no
  longer apply.
- The ranking limit is lifted: a change to ranking or the `fts` constants is an ordinary S1
  issue with its own eval.
- Branch rule (CLAUDE.md "Architecture invariants"): work that needs a model besides the single
  answer LLM call (embeddings, rerankers, any local or hosted model in retrieval or validation)
  is developed on a branch, not `main`.
- ADR-010's outcome stands for this reason: `fts` is the only retrieval mode on `main`, and the
  hybrid code stays on `exp/hybrid`.
- Moving model-based work to `main` needs a tech-lead decision recorded in a new ADR that lifts
  the branch rule; sponsor agreement is no longer the trigger. ADR-010's other two revisit
  triggers (a larger or held-out question set where hybrid finds what `fts` misses; a reranker
  that beats RRF order) remain evidence such an ADR would cite.
- ADR-009 (optional vectors module, off by default) is unchanged. Code built for the spec stays.
Consequences: Ranking changes on `main` need only their own eval, not a spec check. Retrieval
work that needs a model still costs a branch and a comparison run before it can reach `main`.
Teammates install nothing new.

## ADR-012: Up to 5 LLM calls per user question
Status: Accepted (tech lead decision 2026-11-16, #184); supersedes ADR-003's single-call default
Context: ADR-003 set a single-call default per answer and asked for a new ADR before any
multi-call design. Some questions split into parts: a comparison ("How do Edward Jones and
Morgan Stanley price advice?") needs evidence per firm, and one retrieval and one call over all
firms can let one firm crowd out the other. On 2026-11-16 the tech lead decided an answer may
use more than one call when the question splits into parts.
Decision:
- One user question uses 0 to 5 LLM calls. One is the default; 0 when the system refuses
  before calling. More only when the question splits into parts; comparisons across firms are
  the first case (one part per firm, each retrieved separately, then a final call writes the
  answer from the parts). The rule that decides when to split belongs to the feature issue and
  is measured by eval, not assumed.
- Unchanged invariants: entity, segment and time filters stay in SQL for every part;
  citations point only at `chunk_id`s retrieved for that question; caveats are built by code;
  every call is logged; the mock provider covers every call, so tests and CI make 0 real calls.
- The extra calls use the configured answer model and provider (`LLM_PROVIDER`), so this is
  not model-based work: it is developed on `main`. ADR-011's branch rule does not apply; it
  now reads "besides the answer LLM calls" (CLAUDE.md "Architecture invariants").
- Paid-call testing counts by question run: one run of a planned question through the full
  answer flow (up to 5 real calls) needs no tech-lead approval; re-running the same question
  is planned before the first call; no per-task total; the 30-question scored run (Gate 3)
  needs the tech lead (CLAUDE.md "Paid API calls").
Consequences: Cost and latency per question can grow up to 5x for split questions. Answers
must stay reproducible on the mock provider. More calls mean more to log and debug per
answer. README, `docs/ARCHITECTURE.md`, `specs/answer-citations.md`, `specs/ui.md` and code
docstrings still describe the one-call code until the feature issue changes them.
The first feature that uses it is the question planner (#214, ADR-020): one planner call and one
answer call, at most 2 per question.

## ADR-013: Retrieval budget by number of firms; Merrill counted once
Status: Accepted (tech lead, 2026-11-17, #181); replaces the fixed k=20 of `specs/retrieval.md`
for questions that name several firms. Its passage count is replaced by ADR-019's token budget
(#213); Merrill counted once and the per-firm growth (now in tokens) stay
Context: k=20 was the skeleton's default (2026-09-28) and was never measured against larger
budgets. On the freeze snapshot `corpus-2026-11-16` (#120) the mock eval fell from 28 to 26 PASS
(Q22, Q24 fail; Q10, Q11, Q23 lose recall). The cause was the slot budget, not ranking: the
quota split k=20 evenly over the firms in the pool, and Merrill filled two groups (its own `MER`
documents and BAC chunks in GWIM), so the other four firms of a five-firm question dropped to 3
passages each. The hybrid re-run (ADR-010, 126 documents) reached the same conclusion.
Decision:
- Merrill counted once: with MER named and BAC not, BAC GWIM/Merrill chunks share MER's quota
  turns and relevance floor (`fts.quota_firms`, read from `parent` / `reported_as` in
  `config/entities.yaml`). `entity_id`, the SQL filters and citations are unchanged.
- Budget by question (`fts.budget`): k = 20 for a question naming 0 or 1 firm; for n >= 2 named
  firms k = max(20, 6 x n), so 2-3 firms keep 20 and the five get 30. n counts covered firms
  after the firm filter; firms with no documents take no slots. The existing over-fetch and
  quota rules (firm and document-type turns, MAX_PER_DOC, near-duplicate removal, FLOOR) fill it.
- Measured, mock, `--as-of 2026-10-29`, Merrill rule in place, against the freeze report: rules
  max(20, 6n) / max(20, 7n) / max(20, 8n) / 20 + 5(n - 1) (k for the five: 30 / 35 / 40 / 40)
  all gave 28 PASS, 0 forbidden, refusal 5/5 and 19/19, no REGRESSED; tier-1 recall documents
  0.652 / 0.653 / 0.657 / 0.666, passages 0.460 / 0.465 / 0.472 / 0.472; 648 / 684 / 722 / 748
  passages over the 30 questions. The smallest rule was chosen. Per-firm alias / segment terms in
  the rank were tried and dropped (Q23 gained, Q11 lost a passage). Evidence in the #181 PR.
Consequences: Questions naming one firm get the same passages as before (0 changed lists,
except Merrill-only Q4 / Q27, through the Merrill rule). Five-firm prompts grow from 20 to 30
passages (median characters about +45%), so cost per answer grows for them. `THEME_K` stays 4,
so tier 5 research's share in five-firm entity+theme questions (Q10, Q21) falls from 1/5 to
1/7.5; Q21's theme slot is #190. The rule is revisited when the next snapshot (#178 Form ADV,
#150 speaker-turn transcripts) pushes evidence out again: a larger PER_FIRM is a one-line change.
See ADR-018: a home-firm theme question's peers (2 slots each) come on top of this budget.

## ADR-014: Rank floor measured from a firm's 2nd-best chunk; the theme slot ignores the floor
Status: Accepted (tech lead, 2026-11-17, #166 and #190); changes the relevance floor in
`specs/retrieval.md`
Context: `select()` gives no slot to a chunk ranked below FLOOR (0.3) x its firm's best chunk.
With PR #150's speaker-turn transcript chunks (#107) one short, dense answer can rank far above
the rest of its firm: for Q28 the Merrill answer `BAC-TR-2026Q2#63` ranks 10.65, Merrill's floor
rises to 3.20 and `BAC-10K-2025#246` (2.77, the only `BAC:10-K#GWIM` passage) drops, so Q28
goes PASS -> FAIL (coverage 0.667 -> 0.333). Separately (#190), in entity+theme the floor was
applied before the THEME_FIRST slot, so a firm's only chunk on the theme below the floor was
never a candidate and the firm was reported as a theme gap (Q21: `MS-DECK-2026-strategic-update#22`
at 2.32 vs Morgan Stanley's best 11.66).
Decision:
- The floor is FLOOR (0.3) x the firm's 2nd-best rank (`FLOOR_BASE = 2`; a firm with one chunk
  uses that chunk). One outlier no longer lifts the floor for the whole firm; a firm's two best
  chunks always pass. Merrill's base is taken over MER and BAC GWIM/Merrill chunks together
  (ADR-013). The research part of entity+theme keeps the best chunk as its base.
- The THEME_FIRST slot takes the firm's best chunk on the theme whether or not it clears the
  floor; rank-order turns keep the floor.
- Measured (mock, `--as-of 2026-10-29`) on the freeze `corpus-2026-11-16` and on a copy with
  #150's transcripts re-ingested and #150's answer key. Grid: FLOOR 0.25 / 0.2, floor base 2nd /
  3rd best, transcript MAX_PER_DOC 4 / 5, and combinations. Every floor rule brought Q28 back
  with no PASS -> FAIL; the per-document cap alone did not bring Q28 back. The 2nd-best base had
  the fewest recall drops and is the only one that keeps `BAC-TR-2026Q2#63` (the target of #107)
  in Q4 on the #150 copy. Grid and per-question delta in the #166 PR.
Consequences: Freeze corpus: 28 PASS unchanged, 0 forbidden, refusal 5/5; coverage up on Q7,
Q24, recall up on Q30; Q17 coverage 0.625 -> 0.5 (still PASS: a Schwab 10-K chunk now clears
the floor and takes the turn that held a Schwab transcript chunk). #150 copy: 27 -> 28 PASS (Q28),
Q5 back to the freeze corpus's 0.833. Q21 no longer reports Morgan Stanley as a theme gap. The
recall drops PR #150 causes on Q6, Q13 and Q27 are not floor effects (the chunks clear the floor
and lose the transcript type's turns at k = 20) and are unchanged here.

## ADR-015: Document-type scope per question: Form ADV only for fee questions, no trade press for benchmarks
Status: Accepted (tech lead, 2026-11-17, #179); adds a doc-type filter to `specs/retrieval.md`
Context: retrieval searched every document type for every question. PR #178 adds five Form ADV
Part 2A brochures (1,156 chunks) and PR #186 adds 77 trade-press articles (tier 4, 327 chunks).
Measured on the freeze `corpus-2026-11-16` plus those documents with `main` (after ADR-013 /
ADR-014), mock, `--as-of 2026-10-29`: brochure chunks entered 29 of 30 retrievals and tier-1
document recall fell 0.646 -> 0.601 (Q1, Q22, Q28, Q30 recall and Q7, Q9, Q11, Q22, Q24
coverage down); with the trade press too, trade chunks entered all 30, recall fell to 0.533 and
Q28 went PASS -> FAIL. At `--as-of 2026-11-17` Q26 passed only because RJF brochure chunks filled
its 90-day window (a brochure revision is not news).
Decision:
- A hard SQL filter per question (`fts.doc_type_scope`, config `doc_type_scope` in
  `config/entities.yaml`), on every retrieval pass, like the firm and window filters.
- `adv` is searched only when the question names the `fees_pricing` theme (its topic keywords)
  or one of "Form ADV", "ADV", "brochure(s)", "compensation" (the brochures disclose how
  advisors are paid; Q25 expects three `*:adv` sources), and never in a question with a time
  window (Q26, Q27).
- A benchmark question (at least 2 covered firms and a metric phrase: "advisor headcount",
  "net new assets", "assets per advisor", "attrition rate"; Q11, Q22-Q24, Q28) does not search
  tier 4. Trade press stays for every other question, recency windows included (Q2, Q4, Q5, Q7,
  Q17, Q26, Q29 keep their `*:trade` hits).
- Measured (mock, both as-of dates) on scratch copies of the freeze with the brochures and with
  brochures + trade press, against `main` on the same copies. Grid: adv trigger {theme + ADV
  terms; + "compensation"; + "pay"} x benchmark phrases {none; Q22-Q24; Q22-Q24 without Q11;
  + "attrition rate"}. "compensation" brought Q25's `*:adv` coverage back (0.625 -> 1.0); "pay"
  only added brochures to Q29, which does not expect them; "attrition rate" brought Q28 back with
  the trade press loaded. Chosen: the smallest cell meeting #179's acceptance.
Consequences: Brochures + trade-press copy, `--as-of 2026-10-29`: 28 PASS (main 27), tier-1
recall 0.593 / 0.457 (main 0.533 / 0.423), Q18 5/5 `*:adv`, Q22-Q24 coverage back to the freeze
level. Brochures-only copy: recall equals the freeze without brochures (0.646 / 0.481). The freeze
`cee` gets the same passages as before (no `adv`, no tier 4 documents). Q2, Q5, Q6 and Q30 still
lose a passage each to trade chunks compared with the freeze (trade takes the document type's
turns at k = 20); a fee question worded without any configured term or theme keyword does not
see the brochures, and the term lists are the place to widen it. Evidence in the #179 PR.

## ADR-016: Slot order inside a firm: trade press last, a new document before a second chunk
Status: Accepted (tech lead, 2026-11-17, #198 / #199); adds slot-order rules to `specs/retrieval.md`
Context: the final snapshot `corpus-2026-11-17` adds 77 trade-press articles (tier 4, #57) and
cuts the 32 earnings calls at speaker turns (#107: 1,689 -> 2,852 transcript chunks). Inside a
firm's share, document types took turns in rank order and each type gave its next-best chunk.
Mock eval (app budget) on that snapshot: tier-1 document recall 0.573 at `--as-of 2026-10-29` and
0.547 at 2026-11-17, against 0.646 / 0.625 on `corpus-2026-11-16` (no trade press, length-cut
calls). Trade articles ranked first took the trade turn every round and pushed filings, releases
and calls out (Q2 `RJF-TR-2025Q4`, Q5 `MS-TR-2026Q1`, Q30 `BAC-PR-2026-01-14-01`), and the
transcript turn went to a second and third turn of the firm's best call instead of its other calls
(Q6 `RJF-TR-2025Q2`, Q11 `SCHW-TR-2026Q1`, Q13 `MS-TR-2026Q3`, Q27 `BAC-TR-2026Q3`; Q4 missed the
Merrill answer `BAC-TR-2026Q2#63` by one slot).
Decision: `fts.select()` orders slots inside a firm's turn (theme and rank turns alike; never in
the tier 5 research part):
- **Trade last** (`TIER_LAST = 0`): a tier 4 document type takes the firm's turn only when no other
  type of the firm can give a chunk. If the list is then full and the firm has no trade chunk,
  its best trade chunk replaces its last second chunk of a document, else of a document type
  (`TRADE_KEEP`); a firm's only chunk of a type is never given up. Off inside a time window
  (Q26 reads its 90 days of news as ranked).
- **New document first** (`NEW_DOC_FIRST`): a document type gives a document not yet in the list
  before a second chunk of a used one; among unused documents whose chunk ranks within 0.9 of the
  type's best unused chunk, the newest wins (`NEWEST_BAND = 0.9`; Q11's 1Q26 call at 6.31 vs the
  4Q25 call at 6.64). Also inside a window (Q27 "since the start of the year").
- Chosen from a mock grid on `corpus-2026-11-17` at both as-of dates (`D:\ALLPROJECTS\EDJ\cache\ev198\grid*`):
  trade {no rule, last, first 1 or 2 in turn then last, cap 1 or 2} x new document first {off, on}
  x newest band {off, 0.95, 0.9} x keep one trade {off, on}. Only "last" brought Q30 back to 1.0;
  caps lowered Q17/Q25; Q11 needed the newest band; pure "last" took every trade chunk out of
  Q2, Q5, Q7, Q29 (their `*:trade` coverage fell), which the keep-one rule restored without losing
  Q30's release or Q18's brochure. Chosen: the cell meeting every #198 / #199 acceptance item at
  both dates with the highest tier-1 recall.
Consequences: mock, `corpus-2026-11-17`: 28 PASS / 2 FAIL unchanged (Q15, Q19), refusal 5/5 and
19/19, 0 forbidden; tier-1 document recall 0.573 -> 0.742 (2026-10-29) and 0.547 -> 0.727
(2026-11-17), above the no-trade level; passage recall 0.453 -> 0.550 and 0.420 -> 0.523. Q2 0.556,
Q5 1.0, Q30 1.0, Q6 0.667, Q11 1.0, Q13 0.833, Q27 0.667; Q4 gets `BAC-TR-2026Q2#63`; Q26 still
reads 15 RJF trade chunks inside its window. Every keyed question's document recall is at or
above `main` before speaker-turn chunking (#107). Cost: a firm's trade press now mostly fills what
filings and IR leave; Q17 loses one MS trade chunk (coverage 0.6 -> 0.5, recall unchanged), and
Q6 holds 0.667 rather than its no-trade 0.833 (the newest band prefers RJF's later calls). A newer
document of the same type can displace an older one ranked up to 10% higher. Evidence in the
#198 PR.

## ADR-017: Answer turn with its question turn; vocabulary keys match inflected and as phrases
Status: Accepted (tech lead, 2026-11-18, #203); adds an answer-turn rule and key-matching rules to
`specs/retrieval.md`
Context: Gate 4 R1 (#121, real run on `corpus-2026-11-17`, 15/30) had answers that said "not in the
evidence" for passages the corpus holds. Q6: the analyst's question turn `RJF-TR-2026Q1#45` was kept
for the question's words, but the CEO's answer `#46` is a second chunk of the same call, and
new-document-first (ADR-016) gave the slot to other calls. Q13, Q17, Q22: the passages use other
words than the question ("channel migration", "originating from workplace", "AI-powered", the table
label "Net new assets for the period"); the key `stock plan` never fired on "stock-plan", nor
`recruiting` on "recruit"; and a multi-word key such as "net new assets" was searched only through
its values, so its own adjacency counted for nothing.
Decision:
- **Answer turn with its question turn** (`PAIR_TURNS = "attach"`): a kept transcript chunk that is
  a question turn (an operator hand-off or Bloomberg "Q - " label, or a last paragraph ending in "?"
  under a speaker label with no executive title) brings the next chunk of the same call, kept right
  after it in the same firm's turn, inside MAX_PER_DOC, near-duplicate removal and k. The answer
  turn is fetched with every hard filter of the main pass (entity/segment, window, date range,
  keywords, doc-type scope) and no word match, so a turn the filters exclude never comes in (a BAC
  consumer turn in a Merrill question). A next chunk that is itself a question turn is not an
  answer. TRADE_KEEP does not give up an answer turn kept with its question. `"replace"` (the
  answer in the question's place) was built as the fallback and not needed.
- **Key matching**: a lower-case synonym key matches with a hyphen or spaces between its words and
  an inflected last word (s, es, ed, ing); all-caps keys keep exact case. Keys in config
  `synonym_exact` keep the plain match: `compensation structure`, so gap question Q25 ("advisor
  compensation structures") does not pull "payout grid" in (it brought `RJF-TR-2026Q1#44`, a
  payout-grid call turn).
- **Multi-word key as a phrase**: a multi-word key found in the question is searched as a phrase
  too, ahead of its values.
- **Vocabulary** (`config/entities.yaml`): `recruit` (was `recruiting`) += payout, affiliation
  options; `convert` -> channel migration, originating from; `workplace` -> originating from
  workplace, workplace channel; `AI` += AI-powered, AI-enabled, AI tools, AI-driven; `under 40` ->
  next generation, younger investors, younger clients, millennials, Gen Z; `net new assets` += the
  EDJ table label "net new assets for the period".
- Ranking table rows that carry the asked metric (lever 3 of #203) was not built: the table label
  brought `EDJ-10Q-2026Q2#60` into Q22.
Consequences: mock, `corpus-2026-11-17`, app budget: 28 PASS / 2 FAIL unchanged (Q15, Q19) at
`--as-of` 2026-11-17 and 2026-10-29, 0 forbidden, refusal 5/5 and 19/19; tier-1 document recall
0.727 -> 0.788 (2026-11-17) and 0.742 -> 0.800 (2026-10-29), passage recall 0.523 -> 0.607 and
0.550 -> 0.629. In the retrieved set now: Q6 `RJF-TR-2026Q1#46`, Q13 `MS-TR-2025Q4#20` and
`MS-TR-2026Q1#24`, Q17 `MS-TR-2025Q3#8`, Q22 `EDJ-10Q-2026Q2#60`. Not reached: Q2
`RJF-PR-web-affiliation-options#1` (its page is in through `#0`; `#1` is a second chunk behind
other press documents, rank 43 at k=80) and Q20 `FIDELITY-III-2025#0` / `UBS-NEXTGEN-2026#81`
(outside the research part's 3-4 slots in a theme question; `UBS-NEXTGEN-2026#83` stays in).
The answer-turn rule fires on one question of the bank (Q6); the key matching changes the keys of
Q2, Q5, Q6, Q7, Q8, Q10, Q13, Q20, Q29 (`advisor` now fires on "advisors"). Cost: Q5 document recall
1.0 -> 0.833 (PASS kept). Merrill traps Q4, Q27, Q30 unchanged. Evidence in the #203 PR.

## ADR-018: Firm scope: a peer phrase for the advisor-led model; home-firm theme questions also search competitors on the theme
Status: Accepted (TL, #205, 2026-11-18)
Context: Gate 4 R1 (#121) failed Q15 and Q19 because retrieval searched the wrong firms. Q15 ("how
Schwab earns ... and how an advisor-led model earns") names only Schwab, so every passage was
Schwab's. Q19 ("How should the preferences of younger investors shape Edward Jones's offerings?")
names only the home firm, so no competitor move aimed at the cohort could be cited (`passes_if`
asks for them). ADR-004 limits firm documents to the firms a question names.
Decision:
- **Peer phrase** (config `peer_sets`, `advisor_led`): "an advisor-led model", "advisor-led models",
  "advisor-led firms", "an advisor-led firm" (and "adviser-led") mean MS, EDJ, MER and RJF, by how
  each reports (MS advisor-led vs self-directed client assets; EDJ only through its advisors;
  Merrill = GWIM's advisor business; RJF's Private Client Group). Schwab is not one. Indefinite and
  plural phrases only, so "Edward Jones's advisor-led model" names one firm; the plural "Edward
  Jones's and Morgan Stanley's advisor-led models" names the group (deliberate).
- **Home-firm theme rule** (config `home_firm: {id: EDJ, theme_peers: core_five}`): an entity+theme
  question whose only named firm, covered or not, is the home firm gets `Query.theme_peers` = the
  other members of `core_five`. One more SQL pass returns their chunks with the theme's keywords
  (the #117 on-theme filter) and every other hard filter (entity/segment - Merrill only through
  BAC GWIM/Merrill -, window, date range, keywords, doc-type scope) plus the word match. That pool
  is cut at FLOOR (0.3) x its 2nd-best rank across all peers, inside a time window too, then each
  peer firm gets at most `PEER_THEME_PER_FIRM` = 2 slots (Merrill counted once). The home firm and
  research parts are computed as before; the peers' slots come on top (`budget()` + 2 per peer,
  also on top of an explicit k). A firm filter on the Ask page clears the peers. The coverage note
  says "on the theme also ..." and names peers with nothing on the theme; caveats cover peers.
- The eval's forbidden check accepts a peer hit only when its firm is a peer (BAC only through the
  GWIM/Merrill segment for MER) and its text matches the theme's keyword pattern rebuilt from
  config, not the flag `search()` sets.
- Rejected: a per-firm floor for the peers (BAC's "Top 40 Advisors Under 40" footnotes are BAC's
  own best, so they would stay); 3 slots per peer (adds a Schwab deck slide, no new firm).
Consequences: only Q15 and Q19 of the bank change. Mock, `corpus-2026-11-17`: Q15 FAIL -> PASS
(coverage 1/5 -> 4/5: `MS-10K-2025#166`, `EDJ-10K-2025#20/#23`, `RJF-10K-2025#9` next to
`SCHW-10K-2025#13`; 20 -> 30 passages). Q19 gets `SCHW-TR-2026Q3#11` and `SCHW-TR-2025Q3#11`
(Gen Z / millennial share of new accounts) and no advisor-ranking chunk; its EDJ and research
passages are unchanged; it stays a mock FAIL (1/5) because its expected sources are competitor
press, and no MS, SCHW or RJF press chunk is on the theme (TL decision D-Q19). MS and RJF have no
chunk on the younger-investor theme; Merrill's are advisor rankings, cut by the floor. Evidence in
the #205 PR.

## ADR-019: Retrieval budget in tokens; candidate pool from a grid
Status: Proposed (TL, #213, 2026-11-19); replaces ADR-013's passage count (k = 20, five firms 30)
with a token budget; Merrill counted once (ADR-013) stays
Context: the model read 20 passages (30 for five firms), about 6k tokens per question (median
6,001, max 9,544, characters / 4), out of 21,143 chunks, and `select()` saw only the best 15
chunks per (firm, document type). #210 measured recall by stage on `corpus-2026-11-17`: recall@pool
0.686 / recall@final 0.484 (tier 1 0.803 / 0.597), and 7 of the 8 passages Gate 4 named as
missed were never candidates. Current models read 30-40k tokens easily.
Decision:
- **Token budget** (`fts.TOKEN_BUDGET = 40000`, `fts.budget_tokens`): `select()` fills the list
  until its estimated tokens (passage characters / 4, summed in `select()` order) reach the
  budget, not a passage count. ADR-013's growth in tokens: B for 0 or 1 named firm, max(B,
  B x 6 x n // 20) for n firms (2-3 firms 40k, the five 60k). The research part (THEME_K = 4
  passages) is selected first and its tokens come off the firm part; theme peers (ADR-018, Q19)
  keep 2 passages per peer on top, outside the budget. An answer turn is attached only while the
  list is not full; TRADE_KEEP swaps only for a trade chunk no longer than the pick it replaces;
  so the list ends at most one chunk past the budget (largest overshoot at the pick: 323 tokens).
  An explicit k (`search(q, k=...)`, `eval_run.py --k`) keeps the passage rule; `TOKEN_BUDGET =
  None` restores it.
- **Pool** (`fts.POOL_PER_GROUP = 30`): every SQL pass keeps the best 30 chunks per (firm,
  document type), was 15.
- **Chosen from a grid by a rule fixed before it ran** (plans/0213-pool-budget.md): pool {15, 30,
  50} x budget {passage rule, 20k, 30k, 40k}, mock, `--as-of 2026-11-17`, against the #210
  baseline. Eligible: refusal gap 5/5, keyed 22/22, 0 forbidden, no PASS -> FAIL, recall@pool and
  recall@final (all rows and tier 1) not below the baseline. Pick: highest tier-1 recall@final,
  ties to the smaller budget, then the smaller pool. All 12 points were eligible (29 PASS, 0
  forbidden, refusal 5/5 and 22/22 everywhere). Tier-1 recall@pool / recall@final:

  | Pool \ budget | passages | 20k | 30k | 40k |
  |---|---|---|---|---|
  | 15 | 0.803 / 0.597 | 0.803 / 0.720 | 0.803 / 0.739 | 0.803 / 0.752 |
  | 30 | 0.903 / 0.597 | 0.903 / 0.764 | 0.903 / 0.783 | **0.903 / 0.808** |
  | 50 | 0.942 / 0.597 | 0.942 / 0.764 | 0.942 / 0.783 | 0.942 / 0.802 |

  All rows: recall@final 0.484 -> 0.654 at the pick (recall@pool 0.686 -> 0.814). Pool 50 reaches
  more candidates, but at 40k its larger pool lets more mid-rank chunks of other documents take
  the slots (0.802 < 0.808).
- Tokens are characters / 4 estimates everywhere (budget, reports, this ADR), not tokenizer counts.
Consequences: mock, `corpus-2026-11-17`: 29 PASS / 1 FAIL (Q19) unchanged, no question REGRESSED,
14 IMPROVED; tier-1 document recall 0.785 -> 0.937. Passages per question grow from 20-30 to
23-216 (675 -> 3,458 in total); tokens per question median 6,001 -> 33,643, max 9,544 -> 60,322
(~988k over the 30, ~5x), so input cost per answer grows about 5x and five-firm answers read
~60k tokens. 20 of 30 questions stop below the budget because their eligible pool runs out
(MAX_PER_DOC 3, the floor; e.g. Q4 at 25 passages, Q19 at 23); that is reported, not padded.
No question turn lost its answer turn to the budget at the pick. Search time per question
(mock eval, run while another agent used the same database) median 0.50 -> 0.78 s, max 1.0 ->
2.3 s: `rank_sql`'s count query is independent of the pool; the cost is more rows and more
`select()` work. Of the Gate 4 missed passages, Q17 `BAC-TR-2026Q2#21` is now retrieved and Q15
`SCHW-10K-2025#27` is a candidate lost in `select()`; Q7 `MS-10K-2025#153`, Q19 `EDJ-10K-2025#88`,
Q20 (Fidelity, UBS sample) and Q25 (`RJF-PR-web-affiliation-options#1`, `MS-10K-2025#153`) are
still not candidates at pool 30 (pool 50 makes most of them candidates but does not select
them): a query problem (#214). The answer call's `max_tokens` (8000, `llm.MAX_TOKENS`) joins the
eval's cache key when it changes. Real check at the pick (8 calls, claude-sonnet-5-5, prompt v3,
no truncated output): Q24, Q28, Q29, Q30 keep `gap_with_adjacent`. Q25 answers `answer` with cited
disclosures (Form ADV, 10-Q and recruiting-page text on how each firm pays its advisors) and empty
`gaps` at the pick (`gap_with_adjacent` in Gate 4 at the old setting); accepted by the TL
2026-11-19 (#213 issuecomment-7001410341), naming the undisclosed parts as gaps moves to #215.
Q7, Q15, Q20 answer; no question cites its own Gate 4 missed passage (none of them is retrieved
for its question), while Q7, Q20 and Q29 cite other questions' missed passages
(`RJF-PR-web-affiliation-options#1`, `EDJ-10K-2025#88`, `MS-10K-2025#153`). Grid and real-run
evidence in the #213 PR.

## ADR-020: Question planner: one planner call splits a question into parts, each part searched
Status: Proposed (TL, #214, 2026-11-19); the first use of ADR-012's multi-call rule
Context: #210 and #213 showed that 7 of the 8 passages Gate 4 named as missed were never
candidates, and that a larger pool and budget (ADR-019) still left Q7, Q15, Q20 and Q25's own
missed passages out: the question's words do not match the words of the passage. Four Gate 4
failures are a part of the question that disappears (Q3 "where they concede ground", Q12 "Edward
Jones's cost structure", Q28 "net headcount is not attrition", Q7's dimensions), and in multi-firm
questions one firm's passages crowd out another's (Q7, Q25). One search over the whole question
cannot target each part.
Decision:
- **When a question is split**: every question that reaches retrieval gets a plan. With a real
  provider (`LLM_PROVIDER` anthropic / openai) and `PLANNER=on` (default), one planner call
  (`src/cee/retrieve/planner.py`, `PLANNER_VERSION = plan-v1`, the answer model, tool
  `submit_plan`, `max_tokens` 2000) writes `parts: [{id, text, firms, keyword_query}]`. Otherwise
  (mock provider, `PLANNER=off`) the **rule plan**: one part per named covered firm when the
  question names 2-4 firms, else one whole-question part. Five-firm questions (Q10, Q11, Q15,
  Q21-Q25) stay one part in the rule plan because five firms exceed the part cap of 4; the issue's
  "one part per named firm" holds for 2-4 firms. Passage mode (`TOKEN_BUDGET = None`, an explicit
  k) is one whole-question part, no planner call.
- **Part cap**: `PLANNER_MAX_PARTS = 4` (setting, 1-5).
- **Code decides the scope**: firms must be ones `resolve()` found (unknown firms, firms not asked
  and firms we hold no documents for are dropped; a resolved firm the plan left out comes back as a
  whole-question part, or joins the part with the fewest firms at the cap); extra parts are cut;
  empty search words become the part's text; ids are `p1..pn`. The window, themes, firm filter, date
  range and keywords are not in the planner's schema, so it cannot change them. Every part searches
  a copy of the resolved query with its firms and words, so entity / segment (Merrill = MER or BAC
  GWIM/Merrill), window, date range, keywords and the whole question's doc-type scope are SQL
  filters in every part.
- **Budget split** (ADR-019's caps unchanged: T = 40k, five firms 60k): the research part (tier 5
  on the theme, at most THEME_K = 4 passages per question, as ADR-019) is selected **once per
  question** before the parts, R = its tokens; the parts are searched in order, part i of n gets
  max(0, T - R - used) / (n - i) (equal shares; what a part leaves flows to the parts after it);
  a chunk kept earlier is excluded from later pools and from the answer-turn map; the theme peers
  (ADR-018) are searched once, after the parts, on top of the budget. Budgeted total (parts +
  research) <= max(T, R) + one chunk. A one-part plan returns exactly what `search()` returned
  before. Hits carry `part_id` (`p1..pn`, `research`, `peers`).
- **Calls**: planner 1 + answer 1 = at most 2 per question (ADR-012 allows 5). 0 planner calls on
  the mock provider, with `PLANNER=off`, in passage mode, or when code skips search (only firms we
  hold no documents for; a firm filter that leaves no named firm). An unusable planner output (no
  tool call, wrong shape, cut at `max_tokens`) or a failed call (API / network error) falls back to
  the rule plan; it is logged and the call counts; it is never re-rolled. The answer prompt is
  unchanged (v3, no part labels; the per-part answer check is #215).
- **Log**: `query_log.filters` holds the resolved query plus `plan` (parts, corrections, source,
  error, per-part share / passages / tokens) and `llm_calls` {planner, answer}; `llm_calls` counts
  paid provider calls, so a mock row reads 0 / 0 although the trace names the mock's answer step
  "(mock, one call)". No schema change. The Ask page trace has a "plan" stage (7 steps). The eval
  caches planner outputs apart from answers (key: question, planner version, snapshot, provider,
  model, part cap, planner `max_tokens`, resolved query) and counts both calls against `--max-calls`.
Consequences: mock, `corpus-2026-11-17`, `--as-of 2026-11-17`, against the #213 pick: 25 one-part
questions return identical lists; Q7, Q8, Q9, Q12, Q28 (2-3 firms) are split per firm. 29 PASS / 1
FAIL (Q19) unchanged, refusal gap 5/5, keyed 22/22, 0 forbidden, no PASS -> FAIL; recall@pool
0.814 / recall@final 0.654, tier 1 0.903 / 0.808, all unchanged; research passages per question
unchanged (Q7, Q19, Q21, Q28: 4; Q10: 2). Tokens per question median 33,643 -> 28,311, max 60,322
unchanged: Q12's Edward Jones part stops at 7k of its 20k share (its eligible pool runs out) while
Schwab, searched first, keeps its 20k share; the share Edward Jones leaves is not handed back to an
earlier part. A real provider pays one more, small call per question (about 1k input, up to 2k
output tokens).
Real check (#214, 12 calls: planner + answer for Q3, Q7, Q12, Q15, Q25, Q28, claude-sonnet-5-5,
answer prompt v3, planner plan-v1; no output truncated or rejected, no fallback, no correction by
code): every question used 2 calls. Q12 (Schwab's acquisition channels and economics, its claims on
acquisition cost, Edward Jones's costs) and Q28 (EDJ attrition and its definition, Merrill's
attrition, net advisor headcount change in the search words) got a part or search words for every
asked part; Q3 got one part with no words for competitive pressure or conceded ground, and Q7's four
parts (one per firm plus competitive pressure) name the payout philosophy only as compensation words
and the training pipeline only for Merrill. Named passages: Q15 `SCHW-10K-2025#27` is now retrieved
and cited (was lost in select); Q25 `RJF-PR-web-affiliation-options#1` and `RJF-10K-2025#10/#11` are
now retrieved and cited, `MS-10K-2025#153` became a candidate (Q7 and Q25) but is not selected,
`EDJ-10K-2025#30/#264` stay candidates and `SCHW-10Q-2026Q2#25` dropped from the final set to the
pool. Q25's Schwab-and-Raymond-James part brought two `must_not_return` Schwab deck chunks into the
retrieved set (not cited), so its refusal check fails at retrieval; Q3 lost its Advisor Services
10-K passage and Q7 its MS and RJF trade-press passages; Q28 reads 20k tokens (was 12.7k) with
Merrill's part searching "attrition ... departures". Behaviors: Q3, Q7, Q15 `answer`, Q12
`answer_with_boundary`, Q28 `gap_with_adjacent`, Q25 `answer` with empty gaps (as at the #213 pick;
#215). Evidence in the #214 PR.
