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
Status: Accepted; its single-call default and its "multi-call design needs a new ADR" rule are superseded by ADR-012 (up to 5 LLM calls per user question, one by default). "Retrieval is deterministic" stands. ADR-012's cap is in turn superseded by ADR-021 (no fixed number).
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
Status: Accepted (tech lead decision 2026-11-16, #184); supersedes ADR-003's single-call default; its 0-5 call cap is superseded by ADR-021 (no fixed number, see the amendment below)
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
Amendment (#244, ADR-021): the 0-5 cap is relaxed with no fixed number (user decision 2026-11-19:
quality first, cost reduced later). Calls follow the question's sub-question decomposition
(map-reduce: planner 1, map one per firm plus research, re-extraction after a corrective re-search,
reduce 1; ADR-021 rule 7). Note (#272, W12 latency): the map is one call per firm x aspect cell (and one
re-extraction per re-searched cell), in parallel, so the slowest call is shorter; each cell call may cite the
same chunks it could in the firm call. Still no fixed number: the count follows the decomposition. Unchanged: SQL filters for every sub-question, citations only to retrieved
chunks, caveats by code, every call logged (now with input / output tokens; cost from a configured
price, #248), the mock covers every call so tests and CI make 0 real calls, and the work stays on
`main`. Paid-call testing: one run of a planned question through the full answer flow counts every call
the flow makes; the plan states the expected count before the first call; re-runs are planned; no
per-task total; the 30-question scored run (Gate 3) needs the tech lead; scored runs keep a run-level
`--max-calls`. Providers: the extra calls use the configured answer provider (`LLM_PROVIDER`: the
configured providers, `anthropic` and `openai`; `deepseek` once #242 lands).

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

Amendment (#247 part 2, TL ruling D1 on the plan review, issue #247 comment 7037522138): a chunk id
registered in `config/metric_definitions.yaml` (a definition `chunk_id`, its `see_also`, a
`populations` source) is fetched by ID for the sub-questions of a registered-metric or ratio-input
aspect even when its document type is `adv` (one curated Form ADV Part 1A figure crowds nothing out;
for Schwab it is the only firm-filed figure). The tier-4 exclusion, the window, the date range and the
entity / segment filters still apply to pinned ids.

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
Amendment (#245, ADR-021 rule 6, competitors as real entities): with a plan (token mode), the theme
peers of a home-firm market question (Q19) are sub-questions of their own, `SubQuestion(<peer>,
aspect)` with role competitor and a full sub-question budget, in place of `peer_pass`'s two slots
per peer. The safeguards stay: their firm pass is on the theme only (`Query.on_theme_only`, a SQL
AND of the theme's keywords; no answer turn attached), Merrill only through BAC GWIM/Merrill, and
the floor across the peers (FLOOR x the 2nd-best rank across the competitors of each aspect, applied
after select; dropped chunk ids logged, a sub-question it empties reads as "no passages found").
`Query.theme_peers` stays on the resolved query (coverage note, caveats, the eval's forbidden check);
`peer_pass` runs only without a plan. Mock `corpus-2026-11-19`: Q19 gets 11 Schwab passages on the
theme (was 2), Merrill's 4 on-theme chunks are cut by the floor, MS and RJF have none; it stays a
mock FAIL (1/5, its expected competitor press is not on the theme in this corpus).

## ADR-019: Retrieval budget in tokens; candidate pool from a grid
Status: Accepted (TL, #213, 2026-11-19); amended by ADR-021 (per-sub-question budget, see the amendment below); replaces ADR-013's passage count (k = 20, five firms 30)
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
Amendment (#230, answer output cap): `llm.MAX_TOKENS` 8000 -> **20000** for every answer call. In
the #229 real run Q22 (five firms, 209 passages, ~60k input tokens, prompt v4) came back with no
claims, adjacent items or gaps; the saved output kept neither `stop_reason` nor usage, so a cut at
8000 was likely but not provable. The request sends no `thinking` field; whether the model thinks
(and so spends part of the cap on thinking) shows in the saved content block types. One flat cap,
not a size rule: the cap is a ceiling billed only for tokens produced, and a size rule would still
miss a small input with a long answer. 20000 is the largest round value under the `anthropic` SDK's
non-streaming limit (1.9.0 refuses a non-streaming call above 21,333 tokens, its 600 s rule; a test
runs the SDK's own check). A cut at the cap, or an answer with no claims, adjacent items or gaps
(a refusal aside), is an invalid output (`llm.check_output`, specs/answer-citations.md), and every
real output saves `stop_reason` and usage. Cache: the cap joins the eval's answer key when it is not
8000, so outputs saved at 8000 keep their keys and are never reused at 20000; planner keys do not
contain it. The real clients get `max_retries=0` (TL decision), so a timeout at the larger cap is
never resent by the SDK. Real check in the #230 PR.
Amendment (#244, ADR-021, sub-question budget): in planned mode the per-question total is no longer
fixed. Each sub-question (firm x aspect, ADR-021 rule 6) gets its own token budget (a new setting
`SUBQUESTION_TOKENS`, value set and measured in #245), so the total grows with the decomposition and is
reported per question. Unchanged: the pool rule (`POOL_PER_GROUP = 30` per firm and document type),
research selected first (THEME_K), Merrill counted once (ADR-013), tokens as characters / 4, and
passage mode (`TOKEN_BUDGET = None`, an explicit k). Until #245 lands the code keeps the fixed total
described above.
Built (#245): `SUBQUESTION_TOKENS = 40000` (setting, env `SUBQUESTION_TOKENS`), chosen from a mock
grid by the rule fixed in plans/0245-decompose.md before it ran: points 12000, 20000, 40000
(`corpus-2026-11-19`, `--as-of 2026-11-17`, rule plan = one whole-question aspect per scoped firm);
eligible: refusal gap 5/5 and keyed 22/22, 0 forbidden, no PASS -> FAIL, recall@pool and
recall@final (all rows and tier 1) not below `evals/baselines/corpus-2026-11-19` (its 30
questions); pick: highest tier-1 recall@final, then all rows, ties to the smaller value.

  | SUBQUESTION_TOKENS | recall@pool | recall@final | tier 1 pool / final | PASS (30) | tokens median / max / total (35) | eligible |
  |---|---|---|---|---|---|---|
  | 12000 | 0.814 | 0.593 | 0.903 / 0.733 | 29 | 12,887 / 56,804 / 969,624 | no (recall@final) |
  | 20000 | 0.814 | 0.640 | 0.903 / 0.790 | 29 | 20,222 / 85,444 / 1,346,283 | no (recall@final) |
  | **40000** | 0.814 | 0.654 | 0.903 / 0.808 | 29 | 39,953 / 108,780 / 1,519,747 | **yes** |

  At 40000 every one of the 30 baseline questions is UNCHANGED (status, recall, coverage); one-firm
  questions return the same lists; multi-firm questions read more (Q15 60k -> 88k, Q22 60k -> 81k,
  Q24 60k -> 76k), since each firm now has its own 40k. Research stays THEME_K passages, outside the
  sub-question budgets. The grid runs the rule plan (one aspect per firm), so it cannot measure
  multi-aspect totals; the #245 real planner check reports the totals of real plans. Until #247
  replaces the single answer call, a temporary input guard trims that call's passages when they
  pass the model's limit (specs/answer-citations.md, "Interim answer input guard").

## ADR-020: Question planner: one planner call splits a question into parts, each part searched
Status: Accepted (TL, #214, 2026-11-19); amended by ADR-021 (no part cap, no fixed call count, see the amendment below); the first use of ADR-012's multi-call rule
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
  (`src/cee/retrieve/planner.py`, `PLANNER_VERSION = plan-v2` since #224, the answer model, tool
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
  range and keywords are not in the planner's schema, so it cannot change them. Since #224 code
  also removes from a part's words every `neighbour_phrases` entry (`config/entities.yaml`: a
  different figure that shares a word with the asked one, e.g. "payout ratio" = the dividend payout
  ratio) that the question does not name. Every part searches
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
- **Unused share is not handed back** to earlier parts (#224: "not now"). (1) No key row lost at
  select would be reached: a 0-call replay of #214's Q25 gave p1 (MS) its share plus the 6.7k +
  11.9k p2 / p3 left (15.0k -> 33.6k); p1 stopped at `select()`'s floor (68 passages, 21.9k; the
  same with no limit) and `MS-10K-2025#153` stayed in the pool. The other rows stuck at pool sat in
  parts with share left; Q7's parts used all of theirs. (2) In the mock it would change Q7, Q9 and
  Q12, none of which gains a key row (Q7's row is never a candidate). (3) Surplus spent in a weak
  part buys low-rank matches: the flow-forward gave #214's Q25 p4 twice its equal share, and that is
  how two dividend deck chunks got in. (4) A second pass would let each earlier part overshoot by
  one chunk again (ADR-019's bound restated). Revisit when a replay with the surplus added brings a
  lost key row into the final set.
- **Calls**: planner 1 + answer 1 = at most 2 per question (ADR-012 allows 5). 0 planner calls on
  the mock provider, with `PLANNER=off`, in passage mode, or when code skips search (only firms we
  hold no documents for; a firm filter that leaves no named firm). An unusable planner output (no
  tool call, wrong shape, cut at `max_tokens`) or a failed call (API / network error) falls back to
  the rule plan; it is logged and the call counts; it is never re-rolled. The answer call sees
  the parts (prompt v4, #215): its user message groups the evidence under each part, every claim,
  adjacent item and gap carries a `part_id`, and code gives a part with no cited claim or gap a
  gap flagged `part_gap` ("No evidence retrieved for" when the part's candidate pool was empty,
  else "Not answered from the evidence retrieved for"); no extra call. The eval's answer cache key
  includes the parts (specs/answer-citations.md, "Every part answered or named as a gap").
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
Amendment (#224, planner prompt v2): plan-v1 left out asked parts (Q3: one part, nothing on
competitive pressure or conceded ground; Q7: payout philosophy and training pipeline not for every
firm) and its Q25 Schwab + Raymond James part searched "payout ratio" (in this corpus the phrase
occurs in 11 chunks, 10 of them about dividends, none about advisors), which brought
`SCHW-DECK-2026Q3#47` / `SCHW-DECK-2026Q1#44` in. plan-v2 adds three prompt rules (list the asks
first, including what a question asks without naming it; give every ask a part or its own words;
same concept only) with examples on other units and activities, and code removes neighbour phrases
(above). The rule plan is unchanged: mock (`corpus-2026-11-17`, `--as-of 2026-11-17`) all 30 chunk
lists identical to the #214 baseline, 29 PASS / 1 FAIL (Q19), refusal gap 5/5, keyed 22/22, 0
forbidden. A 0-call replay of the six saved plan-v1 outputs reproduces #214's lists; with the guard
only Q25 p4 and Q15 p2 (both "payout ratio") change, Q25's two must-not chunks leave (refusal check
passes, recall unchanged) and Q15's recall and coverage are unchanged. Tests cannot reach a paid
API: `tests/conftest.py` stubs the two client builders and clears the credential environment.
Real check (#224, 10 calls: planner + answer for Q3, Q7, Q25, Q12, Q28, claude-sonnet-5-5, answer
prompt v3, planner plan-v2; no output rejected, no fallback): Q3 now has four Schwab parts, one of
them "competition Schwab names ... where it is losing ground or pulling back" (coverage 0.667 ->
1.0). Q7 has one part per firm; MS and Merrill get words for recruiting, compensation, training and
attrition, Raymond James's part has recruiting, transition assistance and attrition words but no
training or pay words (coverage 0.778 -> 0.889; `MS-10K-2025#153` still pool). Q12 keeps Schwab's
acquisition parts and an Edward Jones acquisition part, and spends a fourth part on how Edward Jones
could replicate the strategy (answer still `answer_with_boundary`). Q28 adds a part of its own for
the adjacent net headcount change (recall@final 0.75 -> 1.0). **Q25 still fails its refusal
check**: the planner wrote two parts (MS + Schwab, Edward Jones) and left Merrill and Raymond James
out (code added them back as a whole-question part), and the MS + Schwab part's words "payout grid
... production-based payout" plus the `pay` / `recruit` synonym "payout" matched
`SCHW-DECK-2026Q3#47` and `SCHW-DECK-2026Q2#45` (dividend payout range) on the one word "payout",
which the neighbour list does not cover. A finding, not re-run; the narrower rule for the bare word
in a Schwab part, or the budget / ranking, is the TL's call (with #215).
Amendment (#232, strict tools): on the Anthropic path both tools are sent with `strict: true` (a
top-level field of the tool definition; `anthropic` 1.9.0 `ToolParam.strict`), so the API enforces
the input schema of `submit_plan` and `submit_answer`: an input like #230's Q22 answer
`{"answer": null}` cannot come back. Strict mode accepts array `minItems` 0 or 1 and no `maxItems`,
so the planner tool's `parts` keeps `minItems: 1` and drops `maxItems`; the part cap stays in the
prompt ("in at most N parts", "Most parts: N") and code still cuts extra parts. `tool_choice` stays
`auto` (claude-sonnet-5-5 rejects forced tool choice), so strict does not force a call: no tool
call is an unusable output, as before (rule-plan fallback; answer invalid). An API `stop_reason`
`refusal` is also unusable, even with a tool input (strict's guarantee does not hold there). The
eval's plan and answer cache keys carry the request version `strict-1` for the anthropic provider
only (`llm.request_version`), so no non-strict output is reused by a strict request; OpenAI keys,
`PLANNER_VERSION` (plan-v2) and the prompt texts are unchanged. Offline: both tool schemas pass a
strict-rule check and are unchanged by the SDK's `anthropic.transform_schema`; mock
(`corpus-2026-11-17`, `--as-of 2026-11-17`) all 30 chunk lists identical, 29 PASS / 1 FAIL (Q19),
refusal gap 5/5, keyed 22/22, 0 forbidden.
Real check (#232, 10 calls: planner + answer for Q1, Q10, Q21, Q22, Q23, claude-sonnet-5-5, prompt
v4.1, plan-v2, request `strict-1`; no 400, no invalid output, no fallback, every call `tool_use`): Q22
(#230: `{"answer": null}`) now returns a valid `answer` (11,914 output tokens, 101k input) with NNA
by quarter and each firm's definition for MS, SCHW, EDJ and RJF, Merrill marked as not reporting
standalone (GWIM flows only as adjacent); its eval status fails only the retrieval must-not check
(`MS-PR-2026-04-15-01#15` retrieved, not cited, as in #230). Q1, Q10, Q21 `answer` PASS; Q23
`gap_with_adjacent` as at Gate 4. Evidence in the #232 PR.
Amendment (#244, ADR-021, sub-question decomposition): superseded are the part cap
(`PLANNER_MAX_PARTS = 4`), the rule plan's "five-firm questions stay one part", the equal split of a
fixed total and "planner 1 + answer 1 = at most 2 per question". One planner call remains. Planner v3
(#245) lists every aspect the question asks, literally, with no merge and no cap; code, not the planner,
sets the firms (the resolved firms; for a home-firm market question the competitors as real entities,
ADR-018) and expands firms x aspects into sub-questions, each with its own budget (ADR-019 amendment).
Unchanged: every sub-question searches a copy of the resolved query, so entity / segment, window, date
range, keywords and doc-type scope stay SQL filters; the `neighbour_phrases` guard; the window, themes
and filters stay out of the planner's schema; an unusable or failed planner call falls back to the rule
plan, is logged, counts and is never re-rolled; passage mode is one whole-question part with no
planner call. Until #245 lands the code keeps the part cap and the split described above.
Built (#245): `PLANNER_VERSION = plan-v3`, tool `submit_plan` with the strict schema
`{aspects: [{id, text, keyword_query, firms, metric, kind}]}` on the anthropic, openai and deepseek
paths (metric: a registered key of config/metric_definitions.yaml or ""; kind: fact | series |
recency | comparison); planner output cap 8000 (anthropic / openai; deepseek 8000 thinking off,
64000 on, TL decision after Q19's planner was cut at 16000). `PLANNER_MAX_PARTS` is removed; no aspect cap, no merge, no dedupe. **Per-aspect firm
subset** (TL decision D3, #245 plan review): an aspect may carry `firms`, a subset of the firms code
scoped, filled only when the question itself asks the aspect of some of them (Q12: Schwab's
acquisition aspects for SCHW only; Q15: "how an advisor-led model earns" for MS, EDJ, MER, RJF only);
code maps names and aliases, drops firms outside the scope with a note, an emptied list means all
scoped firms, and on a home-firm market question a list equal to the named firms counts as empty, so
the competitors stay (Q19). The planner message labels each scoped firm by how code found it (named,
through a peer phrase, competitor on the theme). Code expands each aspect over its firm set into
`SubQuestion(entity, aspect)` (ids `<aspect>.<firm>`), each searched through `search_fn` (default
fts.search; exp/hybrid passes its own) with its own budget (ADR-019 amendment); `corrective_search`
is the re-search hook for #246. The rule plan is one whole-question aspect for every scoped firm.
Calls stay planner 1 + answer 1 until #246 / #247; the answer call reads the evidence grouped by
sub-question (prompt v4.1 unchanged) behind a temporary, logged input guard. Real check in the #245 PR.
Amendment (#246, plan-v3.1): each aspect carries a required boolean `proxy` (a stand-in for the asked
quantity: the closest disclosed figure, a numerator or denominator); see ADR-021's #246 amendment.

## ADR-021: Answer behavior decided by code; definitions and comparability; sub-question decomposition with no fixed call cap
Status: Accepted (user decision 2026-11-19, #244); amends ADR-012, ADR-019 and ADR-020; built by #245
(decomposition), #246 (map step, evidence matrix, code rules) and #247 (reduce step); the eval scorer
reads `evals/behavior_supersede.yaml` from #248
Context: the W10 scored run (24/30 on `corpus-2026-11-19`, docs/results/w10-report.md) failed Q11,
Q19, Q20, Q23, Q24 and Q26 (NEXT items 1, 2, 3, 8). Q11 and Q23 chose `gap_with_adjacent` because the
prompt rule of #204 / #215 said "not disclosed for most of the firms asked about -> `gap_with_adjacent`",
and put the definitions and the series that exist into adjacent items. Q25 answered `answer` with its
undisclosed parts as gaps, against the bank's `gap_with_adjacent`, and the TL accepted it (#213). Q24
never answered the comparison itself; Q26 had no line on why each item matters; Q19's planner scoped
every part to Edward Jones, so no competitor move was searched. One answer call reading up to ~100k
tokens has to extract, compare and choose the behavior at once. On 2026-11-19 the user (project lead)
set the rules below.
Decision: the industry patterns are **sub-question decomposition** (LlamaIndex
SubQuestionQueryEngine, Least-to-Most, Self-Ask), **map-reduce** (structured extraction per firm, then
one synthesis), an **evidence matrix** (a comps table, firm x aspect) and **corrective retrieval**
(CRAG) for empty sub-questions. Rule 0 governs all answer text; rules 1-8 apply it. Each rule names
what enforces it and the questions it serves.
- **Rule 0. Evidence only, never opinions** (ground rules 1, 4, 6). Every sentence of an answer is a
  cited fact from a stored chunk, a figure computed from cited inputs (rule 2) or a gap. *Enforced by*
  code: citation check, number check, `withhold_normative` / `ensure_handoff` (existing,
  specs/answer-citations.md). *Questions*: every question.
- **Rule 1. Behavior decided by code from the sub-questions.** The map extraction call (prompt
  extract-v1, #246) labels every firm x aspect cell `fact`, `not_disclosed`, `not_found` or
  `different_quantity`, with cited chunk ids; **code** (#246 `EvidenceMatrix`) aggregates the labels
  into the behavior; the reduce call (#247) writes the answer for that behavior and cannot change it.
  (a) Question level: `answer` when any cell holds the asked quantity (`fact`). Aspect level: every cell
  without a fact is a named gap, and an aspect that no asked firm holds gets the gap "The database does
  not support this today: <aspect> (<firms>)." inside that answer.
  (b) No cell is a fact, but some cell holds a different related quantity: `gap_with_adjacent`. The
  answer says the database does not support the asked quantity today, then gives the labelled adjacent
  figure with `differs_because`.
  (c) No fact and no related quantity: `refuse` (`answerable` false) with that gap and the suggested
  sources.
  (d) Derived quantities: a quantity computable from cited inputs of the same firm on the same basis
  (rule 2, within-firm) counts as held (Q24: Edward Jones's assets and advisors in the same 10-Q).
  (e) Precedence: a request for the system's own forecast -> `refuse`; else a normative part ->
  `answer_with_boundary` (existing code adds the hand-off); else (a)-(c). Positions that others hold,
  attributed and dated, are facts (Q16).
  *Enforced by* code (#246) on labels from a prompt (#246). *Questions*: Q11, Q22, Q23, Q24, Q25, Q28,
  Q29, Q30, Q31-Q35; Q12, Q19 (boundary); Q16 (positions).
- **Rule 2. Definitions and comparability** from `config/metric_definitions.yaml`.
  Within-firm computation (a ratio, a sum, a per-advisor value): the inputs share period or date,
  entity / segment scope and compatible units; the answer shows the formula and cites both inputs.
  Cross-firm comparison or computation: only with the same definition, period and unit; otherwise each
  firm's figure is listed with its own definition, and code inserts the comparability caveat (standard
  wording, specs/answer-citations.md: the reporting risk). A metric not registered in the file (e.g.
  client assets): a within-firm computation is allowed when the within-firm test holds, marked
  "definition unverified"; it is never compared across firms, only listed. #246 adds three fields per
  definition (C1 reviews): `period` (point in time, quarter or year), `unit`, `basis` (a key naming the
  definition; equal keys mean the same basis). *Enforced by* code: comparability marks and caveats
  (#246), the number check on computed figures (#247). *Questions*: Q11, Q22, Q23, Q24, Q31.
- **Rule 3. Adjacent is only for a different quantity.** A partially covered asked quantity (some
  firms, some quarters, a narrower sample) is always a claim, with what it covers stated. A wider unit
  or a different measure (GWIM for Merrill, aggregate compensation expense for a payout grid, an
  industry survey for a firm) is adjacent. *Enforced by* the extraction labels (prompt, #246), their
  aggregation (code, #246) and the reduce prompt v5 (#247). *Questions*: Q25, Q11, Q23, Q28, Q29, Q30,
  Q31, Q33-Q35.
- **Rule 4. A comparison question carries one cited claim that answers the comparison itself**
  (valid or not, and why), cited to its inputs. *Enforced by* prompt v5 and a code check on
  sub-questions of `kind=comparison` (#247). *Questions*: Q24 (Q15, Q10 as checks).
- **Rule 5. The "why it might matter" line** of a recency item states only what the source says or a
  checkable fact, cited; never our judgement (ground rule 6). *Enforced by* prompt v5 (#247) and the
  existing citation, number and normative checks. *Questions*: Q26 (Q27 as check).
- **Rule 6. Sub-question decomposition, literal.** The question is parsed as it is written: N firms x
  M aspects are N x M sub-questions, with no merging and no cap. The planner (plan-v3, #245) lists the
  aspects; code sets the firms (the resolved firms; for a home-firm market question the competitors as
  real entities, ADR-018) and expands them. Research is searched once. Every sub-question keeps all SQL
  filters. A sub-question whose extraction finds nothing gets one corrective re-search (CRAG: widened
  words from `looked_in`, synonyms, adjacent periods; chunks already used excluded) and one
  re-extraction (#245 hook, #246). *Enforced by* code (#245, #246) and the planner prompt (#245).
  *Questions*: Q19, Q11, Q24, Q1, Q3, Q22.
- **Rule 7. Calls follow the decomposition; no fixed number** (amends ADR-012). Planner 1, map one
  per firm plus one for research (in parallel), re-extraction for re-searched sub-questions, reduce 1.
  Every question logs its calls and input / output tokens, and its cost from a configured price
  (#248); scored runs report them and keep a run-level `--max-calls` (CLAUDE.md "Paid API calls"); a
  plan states the expected call count before the first real call; the mock covers every call, so tests
  and CI make 0 real calls. Quality first; cost is reduced later. *Enforced by* code (#246, #247, #248)
  and the paid-call rule. *Questions*: every question.
- **Rule 8. Bank conflict, without rewriting the bank.** `evals/behavior_supersede.yaml` supersedes
  the expected behavior of Q24, Q25 and Q28 to `answer` (rule 1); the scorer reads it from #248; an
  entry never changes `passes_if`. Appended questions pin the rules: Q31 (partial disclosure is
  `answer`), Q32 (`refuse`: the database does not support it today), Q33-Q35 (`gap_with_adjacent`).
  From now on the CLAUDE.md gap / refuse share is held on both the bank's `expected_behavior` (raw:
  9/35) and the behavior after the supersede file (effective: Q29, Q30, Q32-Q35 = 6/35, 17.1%), each at
  least 5/30; `tests/test_behavior_supersede.py` checks both. *Questions*: Q24, Q25, Q28, Q31-Q35.

  Bank audit (every question expecting `gap_with_adjacent` or `refuse`, on `corpus-2026-11-19`):

  | Q | Asked, per firm x aspect | Corpus | Rule 1 | Bank |
  |---|---|---|---|---|
  | Q24 | client assets per advisor; is the comparison valid | EDJ assets and advisors in the same 10-Q | `answer` (derived, 1d) + comparison claim + caveats | superseded |
  | Q25 | what each firm discloses on advisor pay | MS, EDJ, RJF, SCHW disclosures (#213, #215) | `answer` + named gaps | superseded |
  | Q28 | EDJ and Merrill advisor attrition rates | EDJ discloses a rate; Merrill none | `answer` + Merrill gap + adjacent headcount change; also adjacent (#247): `BAC-DECK-2025-investor-day#34`, "Lower outflows from advisor attrition 26% year over year" (an asset-outflow change, not an attrition rate) | superseded |
  | Q29 | what MS pays its advisors (grid, payout) | aggregate compensation expense only | `gap_with_adjacent` | unchanged |
  | Q30 | Merrill standalone profitability | GWIM only (a wider unit) | `gap_with_adjacent` | unchanged |

  Every other expectation (Q1-Q23, Q26, Q27) agrees with rules 1-6.
Consequences: behavior becomes reproducible from the evidence matrix and testable on the mock; Q11 and
Q23 answer with each firm's definition or series and named gaps; Q24 can state the comparison and the
Edward Jones ratio. Calls and tokens per question grow with the decomposition (a five-firm,
three-aspect question: 1 planner + 6 map + up to 6 re-extractions + 1 reduce), which raises cost and
latency; the logs and scored-run reports make it visible, and cost reduction (caching, cheaper map
model) is later work. More calls mean more invalid outputs to save and more to debug. `config/
metric_definitions.yaml` gains `period`, `unit` and `basis` (#246) and only registered metrics are
compared across firms. Until #245-#247 land, the code, `specs/ui.md`, README and
`docs/ARCHITECTURE.md` describe the current flow (planner 1 + answer 1, prompt v4.1); the specs mark
each ADR-021 item with the issue that builds it.
Amendment (#246, map step; TL decisions on the #246 plan, issue #246 comments 7031387523 and
7031488115): the rules above are built in `src/cee/answer/extract.py` and `matrix.py` with these
settled details, which ADR-021's text did not fix:
- **Proxy aspects.** Plan-v3 lists "the closest disclosed figure" as its own aspect. Plan-v3.1 marks
  such aspects `proxy: true` (a stand-in: the closest figure, a numerator or denominator). A proxy
  aspect never fires rule 1(a): its cells count as a related quantity for rule 1(b) and feed the
  adjacent side, and get no gap of their own; they may be inputs of a within-firm derivation
  (rule 1d), whose cell on a non-proxy aspect does fire 1(a). Extract-v1 states one proxy text: the
  figure a proxy sub-question names, as the firm reports it, is a fact; a different measure
  (employees, full-time equivalents, compensation expense, client firms) is `different_quantity`.
  So Q29, Q30, Q33-Q35 keep `gap_with_adjacent`.
- **Undecided behavior.** No cell holds the asked quantity and an extraction failed (an invalid
  output or a failed call): the behavior is not decided (`behavior` None). The answer is shown plainly
  as incomplete ("This answer is incomplete: ..."), never as `refuse` and never with "The database
  does not support this today", because a failed extraction cannot show an absence.
- **Derivations** (rule 1d) are proposed by the extraction model and accepted by code only for cited
  fact items of the same firm with the same period and scope (the same unit for a sum or
  difference) and figures found in their chunks; code computes the value.
- **Retrieved set of a cell**: its sub-question's kept passages plus the chunks in its own candidate
  pool that a sibling sub-question of the same firm kept; an id outside it is rejected and flagged
  (never dropped silently). Rejection is per citation, not per output.
- **Comparison-kind aspects** decide nothing and get no corrective re-search and no gap; the reduce
  (#247) answers them (rule 4).
- **Failed calls** (timeout, 5xx, connection, a 401 / 429 outside DeepSeek's ProviderStop, a 400)
  make that call's cells `failed`; the eval saves a counted record, never called again; a 400 stops
  an eval run after the round.
- **`MAP` is off in the app until #247** shows the map's output (no user pays for calls whose output
  is not shown); the eval turns it on with `--map` / `--map-only`; #247 flips the default.
- The map call's output cap joins its own cache key; `llm.request_version` is unchanged.
- **Invalid-output rule, JSON parsing** (TL decision on #246 Q24, after the real check): DeepSeek's
  strict mode sometimes returns a complete JSON object followed by stray closing braces. One helper
  (`llm.loads_object`, used by the map, planner and answer paths on DeepSeek and OpenAI) takes the
  first complete object (`json.JSONDecoder().raw_decode`) and accepts it only when everything after it
  is whitespace and `}` / `]`; the record carries the flag `trailing_braces`. Any other trailing text
  stays invalid, and the object still goes through the strict schema validation and every code check
  (chunk ids, quotes, numbers). Saved records are re-checked under this rule at 0 calls.

Amendment (#247, reduce step; TL decisions on the #247 plan, issue #247 comments 7033895178,
7033988541 and the TL approval): rules 1, 3, 4 and 5 are completed in `src/cee/answer/reduce.py`
(prompt v5) with these settled details:
- **Answers built by code, 0 calls**: `refuse` (rule 1c), a forecast request (rule 1e), an undecided
  matrix and any matrix with no citable item (in practice a normative question with no fact:
  `answer_with_boundary` with the hand-off and the gaps). Undecided is shown with a code-only behavior
  value **`incomplete`** (no model schema offers it); the incomplete note is also shown on a boundary
  answer when an extraction failed.
- **The reduce schema is constrained by the matrix**: `behavior` is the one decided value, `part_id`
  and `chunk_ids` are enums of the matrix's cell / aspect ids and citable chunk ids (a field over the
  enum limits falls back to a plain string; the code check stays). Code checks citations against the
  matrix only (`outside_matrix`); the citable passages are the retrieval hits plus the corrective
  re-search hits, logged with their origin.
- **Rule 2 in the number check**: a figure equal to an accepted derivation's value is allowed only when
  the claim cites all its inputs (`computed`).
- **Rule 3**: extract-v1.1 labels the asked quantity for other periods a fact (partial coverage);
  code names the asked periods a firm does not cover ("last / past N quarters / years" only; a time
  window gives none; complete years only, matched by year); code flags an asked figure placed as
  adjacent and a different quantity placed as a claim.
- **Rule 4**: one comparison claim per comparison aspect, else the code gap "No cited claim answers
  the comparison asked: <aspect>."; comparison and proxy parts count as covered by their aspect's
  claim, item or gap.
- **Rule 5**: the why-line is inside the claim ("Why it might matter: ...", "the source does not say"
  allowed); with the question's own window or a recency aspect code re-sorts newest first by the cited
  documents' published date; an Ask-page date filter alone changes neither.
- **The comparability mark "definition unverified"** shows only on metric aspects (series, proxy, or
  holding a derived cell); scope labels are normalised before derivations compare them.
- **`MAP` is on by default**; `MAP=off` keeps the legacy single answer call (prompt v4.1) for
  comparison only; the eval maps unless `--legacy`. The #245 interim answer input guard is removed:
  an input over a provider's window is not sent, never trimmed.
- After a 400 in an eval run no further call is made (round 2 and the reduce included).

Amendment (#247 part 2; plan `plans/0247-reduce-2.md`, TL approval after review rounds 1-2, issue #247
comments 7037522138 and 7037650142; prompt v5.1):
- **Rule 2, populations**: a within-firm ratio (or sum, difference) is computed only when both inputs
  carry the same registered population (`config/metric_definitions.yaml` `populations`: what each
  input covers, in the firm's own words, with the chunk that states it and its date `valid_from`) and
  neither figure is approximate or a bound (matched next to the figure). Code tags each input item from
  the entry whose phrase stands nearest before its figure (when no phrase stands before it, the whole quote
  and the item text are read: "We had 8,943 ... financial advisors"), only when that entry's chunk is in the input
  cell's retrieved set. The population source chunks are pinned into the sub-questions that can hold
  an input, are citable, and every derivation proposal ends in one claim per firm saying whether the
  figure is computable, citing both inputs and the sources and quoting them (code writes it when the
  reduce does not; a source dated in another quarter than an input is labelled with its date).
- **Series coverage**: series aspects with asked periods get a per-period sub-search (one FTS search
  per asked period, a hard filter on the document's period end, kept chunks excluded before the cut);
  registered definition chunks are pinned (ADR-015 amendment above). Both add to the sub-question's
  passages; the main search lists are unchanged.
- **Basis breaks**: a firm's series whose items cover different scopes (or populations) gets a code
  caveat listing each basis with its periods; the reduce states each basis apart.
- **Noise**: code gaps only inside an aspect's planned firm subset (`asked_firms`, before the
  home-firm widening); empty competitor cells fold into one gap per aspect; duplicate claims (same
  chunks, the shorter held in the longer) are removed after the part check, then the comparison and
  computability checks run again; why-lines only on recency / window items, written from the cited
  passage's context, and a why-line that restates its claim is replaced by "the source does not say"
  (the model's sentence logged); without a window only the recency items are re-sorted newest first.
- **Revision after blind scoring** (prompt v5.2, TL comments on #247): a why-line is the source's own stated
  context or cited factual background from another retrieved passage; "the source does not say" only when
  no passage gives either, and code replaces only a restatement citing nothing beyond its item. Code
  inserts, from config and the matrix, each firm's definition (or that it publishes none) for a registered
  metric, a definition-wording change across one firm's documents, and where each firm's disclosed series
  starts and stops; a firm with only a different quantity has a gap naming that closest figure.

Amendment (#292, reduce prompt v7; plan `plans/0292-reduce-synthesis.md`, approved in issue #292 comment
7117074418; needs TL sign-off on the PR): **rule 5 applies to list-form answers.** Code picks the answer's form
(`reduce.list_form`, one rule for the reduce and the Ask page). Under a synthesis version (`REDUCE_PROMPT=v7`) the
list form is a question with its own window or with only recency aspects, and it keeps v5.2 unchanged
(one claim per item, a why-line on each, newest first). Every other question gets a direct first sentence and a
short cited synthesis: a recency aspect's items are dated in their sentences, with no why-line and no re-sort.
Under v5.2 / v5.3 the #291 rule stands (own window or any recency aspect -> list) and rule 5 is unchanged.
v8 (the brief form, #292 v8 amendment, approved in issue #292 comment 7118166000) keeps the #247 computability
commitment: code writes each `COMPUTED` / `NOT_COMPUTED` statement (both inputs and the population sources cited
and quoted) into a Computability box next to the caveats (`Answer.computations`), outside the answer's 5 sentences.


## ADR-022: Facts table: metric figures extracted once at ingest by a model, stored as data, served by SQL
Status: Deferred (#285, TL ruling 2026-11-23 at the go/no-go gate G0). The decision below is recorded; the path is
allowed only when a future extraction is run and adopted, and only then does the branch rule change (CLAUDE.md is
unchanged: no ingest-time model output lands on `main`). G0 finding: under the serving rule below, on the #272
test-B records at most 5 of 485 map and re-map calls would be saved (Q23 EDJ, MER, MS, RJF; Q26 RJF), below the
gate's 15, even with a perfect extraction (`docs/results/w13-facts.md`). The code shipped switched off with no rows (code removed by #289, 2026-11-23: a revival rebuilds from PR #288). Amends ADR-011 (branch rule) and ADR-021 rules 6-7 (map calls).
Context: the corpus is fixed (snapshot `corpus-2026-11-19`), yet every question has the LLM map re-read raw passages
to pull out the same figures again: #272 made 454 map calls for 30 questions (p50 34 s each) and nothing carried over
between questions. `config/metric_definitions.yaml` already holds hand-checked definitions, but the figures are
extracted per question. Pre-extracting structured attributes once and answering them by query is the pattern of
EVAPORATE, LOTUS and DocETL (RAG review section 6). ADR-011 keeps any model "besides the answer LLM calls" on a branch.
Decision:
- **Extraction is offline ingest work.** A one-time model pass (`scripts/extract_facts.py`, the answer stack's provider
  settings) reads only the chunks that can hold a target metric (code prefilter over tier 2-3 firm documents) and
  proposes rows. It runs once per snapshot or per extraction version, as a planned paid run with every raw output
  saved (CLAUDE.md "Paid API calls"); never in tests, CI or at query time.
- **Only code-checked rows are stored.** Entity and segment come from the chunk, never from the model. A row is kept
  only if its value is a verbatim substring of its quote, the quote a verbatim substring of the chunk text (whitespace
  squashed), the model's firm equals the document's entity and its segment the chunk's (or empty), and its period
  parses. Other rows are dropped and counted. An independent audit samples the stored rows (#285: 50 rows).
- **The facts are data, so `main` runs without a model.** Checked rows live in `config/facts.jsonl` (git, versioned by
  extraction version, with the model named per row); `cee.facts load` fills the `facts` table from it (run by
  `sync-db` and `ingest`, so the next snapshot carries it). Query time is SQL plus code. The mock provider, tests and
  CI read the same rows; with no table or no rows every cell takes the LLM map as before.
- **Serving rule** (`config/facts.yaml`, #285 TL conditions). A map cell is built from facts, with no LLM call, only
  when all hold: a firm row; the planner tagged the aspect with a registered metric whose registry status for that firm
  is `quoted`; kind fact, series or recency, not a proxy; no non-figure word (why, how, define, growth, change,
  guidance, ...) in the aspect text, the sub-question text or the question; the rows match the registered basis (its
  label phrases, whole basis, no part scope); a series has a row for every asked period; and no document in the
  sub-question's own filtered pool that mentions the metric is newer than the newest served row's document. Otherwise,
  and whenever the lookup is empty, the cell goes to the LLM map, so "not disclosed", closest-figure and gap paths are
  unchanged. Rows of other target metrics (client assets) are stored but not served until the metric is registered.
- **The lookup is a retrieval pass.** It applies the sub-question's own hard filters with the `fts` SQL builders
  (entity and Merrill segment, time window on `published_at`, Ask-page filters, document-type scope). It runs after the
  map fan-out; its chunks join that sub-question's retrieved set only in the finished matrix (never the map's inputs,
  the corrective search's exclusions or the plan's pools), so every served item cites a retrieved chunk and the LLM
  cells' requests, round 1 and re-maps, are byte-identical with facts on or off. Each served item is re-checked by SQL
  through the same filters and against the chunk text.
- **Calls (ADR-021 rule 7).** Map calls follow the decomposition minus the facts-served cells; the run log records
  facts-served and LLM cells per question.
- **Branch rule (ADR-011), to be lifted for the facts table only, when adopted.** Once an extraction is run and
  adopted, its output may land on `main` because it is stored, code-checked data and `main` needs no model beyond the
  answer LLM calls; CLAUDE.md changes then. Every other model work (embeddings, rerankers, any model in retrieval or
  validation, other ingest-time model work) stays on a branch until its own ADR. Until then (Deferred) no facts code or rows are on
  `main` (code removed by #289), and nothing on `main` was produced by a model at ingest.
Consequences: metric cells cost no call and no wait; the saving grows with how often questions ask registered figures.
The facts must be re-extracted (planned, paid) when the corpus or the target metrics change, and a stale file is
visible by its snapshot and version. Wrong rows would repeat in every answer that uses them, hence the checks and the
audit. Narrative cells, revenue lines and other one-question figures stay with the LLM map. Revisit when the question
mix asks registered figures without explanatory words often enough for the gate (at least 15 saved calls on a scored
run), or when more metrics are registered.
