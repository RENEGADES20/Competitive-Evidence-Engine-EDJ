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

## ADR-013: Retrieval budget by number of firms; Merrill counted once
Status: Accepted (tech lead, 2026-11-17, #181); replaces the fixed k=20 of `specs/retrieval.md`
for questions that name several firms
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
