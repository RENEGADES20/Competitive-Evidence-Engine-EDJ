# 0127 - Hybrid retrieval decision record (ADR-010): core stays FTS-only

Issue: #127    Role: TL    Spec: docs/DECISIONS.md (ADR-001, ADR-003, ADR-009), specs/retrieval.md (S1), docs/ARCHITECTURE.md

## Goal
`main` records, in one new ADR, what the hybrid experiment (#124-#126) measured and what was
decided: `fts` stays the default and only retrieval mode on `main`, the hybrid code stays on the
long-lived branch `exp/hybrid`, and the conditions under which the question would be reopened.
Documentation only: no code, config, `.env.example`, fts constant or answer-key change on `main`.

## Facts (checked read-only, 2026-11-05)
- `origin/main` = 9dc4c9b; `origin/exp/hybrid` = 3449cc52171406a45dfd4d13e39e227adbecd1e3 (PR #160
  merged into it). #126 stays open only for S1's after-merge review of `fts.py` / `specs/retrieval.md`
  on `exp/hybrid`; its report is final, so #127 can use the numbers.
- ADR numbers on `main`: 000-007 and 009. ADR-008 was reserved for hybrid in the first #125 plan
  and dropped in its revision 2; it never landed on any branch. The new ADR is **ADR-010** (next
  after ADR-009), so the dropped ADR-008 is not reused for a different decision (open question 1).
- Sponsor portability spec v1.0 (2026-10-29), EJ-10 (Tier 1 constraint): no pgvector, embeddings or
  embedding model, no PostgreSQL extension, no query-time external service incl. rerankers on
  `main`; "If you want to explore semantic retrieval, do it on a branch and document the results."
  Section 4 Non-goals: "Changing retrieval ranking ... for portability reasons." The spec is not in
  the repo; the ADR cites it by name, version and section.
- TL decision on #125 (comment 2026-11-05): hybrid stays off `main`; decision ADR moves to #127;
  ADR-009's line "hybrid retrieval (#125) reads `chunk_embeddings` and stays behind `CEE_VECTORS`"
  describes the design on `exp/hybrid`, not `main`.
- #126 report `evals/hybrid-eval/corpus-2026-10-29/report.md` and `summary.json` at 3449cc5
  (snapshot `corpus-2026-10-29`, as of 2026-10-29, k=20, mock, 0 real calls, Windows CPU, 12
  threads). Numbers verified against `summary.json` (`chosen`, `default`):

  | Mode (constants FLOOR / MAX_PER_DOC) | PASS / FAIL | Tier-1 docs | Tier-1 passages | Refusal gap / all keyed | Forbidden | Median search s |
  |---|---|---|---|---|---|---|
  | `fts` at main's defaults (0.3 / 3) | 28 / 2 | 0.796 | 0.402 | 5/5, 10/10 | 0 | 0.34 |
  | `fts` tuned pick (0.2 / 3) | 27 / 3 | 0.782 | 0.474 | 5/5, 10/10 | 0 | 0.34 |
  | `hybrid-norerank` pick (0.4 / 3) | 28 / 2 | 0.715 | 0.405 | 5/5, 10/10 | 0 | 0.31 |
  | `hybrid` + MiniLM rerank pick (0.4 / 4) | 28 / 2 | 0.738 | 0.402 | 5/5, 10/10 | 0 | 5.1 |

  - Cross-encoder vs RRF order, same candidates: tier-1 passage recall lower at all 12 grid points
    (0.402 vs 0.405 at the pick; 0.317 vs 0.389 at MAX_PER_DOC 2).
  - Q29: MiniLM scores the guarantee note `MS-10K-2025#702` 0.95 and the answer passages
    `MS-10K-2025#153` / `#170` 0.0000 / 0.0001; Q29 passes at the pick only through `#163`.
  - Hybrid fixes Q17 (FAIL -> PASS); loses passages on Q4, Q28, Q29. One passage = about 0.02
    recall; tuned and scored on the same 30 questions (no held-out set).
- **Caveat the ADR must state:** the `fts` rows above are `fts` mode on `exp/hybrid`, which equals
  `main`'s fts except the `synonym_only: [pay]` config added in #125 (only Q29 differs, 29/30
  identical chunk_ids). `main`'s own fts on the same snapshot (`p125r-fts-main`, recorded in the
  Progress log of `plans/0125-hybrid-retrieval.md` on `exp/hybrid`): PASS 27 / FAIL 3 (Q15, Q19,
  Q29), docs 0.796, passages 0.347, refusal gap 4/5. Q29 on `main` is handled by the TL
  separately (#125 decision comment); this ADR does not move `synonym_only` to `main`.
- `.env.example` on `main` has no retrieval-mode key (only `CEE_VECTORS=off`); `RETRIEVAL_MODE`
  exists only on `exp/hybrid`. So "default mode set in `.env.example`" holds already: there is one
  mode and nothing to set.
- Stale text on `main`: `docs/ARCHITECTURE.md` line 176 "Postgres FTS first; later
  Grounded-Rag-Analyst RRF" and `specs/retrieval.md` line 17 "Postgres FTS; RRF later" read as
  planned for `main`; `specs/retrieval.md` line 67 open question "When would hybrid search be
  justified? Needs a comparison run (ADR-001)." Nothing else on `main` (outside `plans/` and the
  PROGRESS log) says hybrid is coming. `docs/RUN.md` "Vectors (optional)" stays correct (ADR-009).

## Files to change
- `docs/DECISIONS.md` (TL)
  - New `## ADR-010: Hybrid retrieval evaluated; core stays FTS-only`, Status `Accepted (tech lead
    decision 2026-11-05, #127)` (the PR is escalated to the TL, who confirms by merging):
    - Context: ADR-001 required a comparison run before hybrid; #124-#126 built and measured it on
      `exp/hybrid`; EJ-10 (sponsor spec v1.0) asks for no embeddings/pgvector/rerankers on `main`
      and for branch exploration with documented results; ADR-003 is untouched (the reranker is a
      local model, no LLM call).
    - The numbers table above (four rows), the reranker finding (12/12 grid points, Q29 example),
      the `main`-fts caveat with the `p125r-fts-main` numbers, the 30-question / no-held-out
      caveat. Link to the report and summary pinned to commit 3449cc5:
      `https://github.com/RENEGADES20/Competitive-Evidence-Engine-EDJ/blob/3449cc52171406a45dfd4d13e39e227adbecd1e3/evals/hybrid-eval/corpus-2026-10-29/report.md`
      (and `summary.json` in the same folder).
    - Decision: `fts` is the default and only retrieval mode on `main`. The hybrid code
      (`hybrid.py`, mode switch, `RETRIEVAL_MODE`, `synonym_only`) stays on `exp/hybrid` and is not
      merged. The cross-encoder is not reliable on this corpus (lower passage recall than RRF order
      everywhere, wrong top passage on Q29, ~15x slower). The comparison does not show FTS misses
      that hybrid fixes beyond noise (Q17 is one question, about 0.02 recall). The fts tuning pick
      (FLOOR 0.2) is reported, not adopted; any fts constant change is a separate S1 issue with its
      own eval (pointer for #159-type follow-ups). The optional vectors module of ADR-009 is not
      changed by this ADR (open question 2).
    - Revisit when (any one): the sponsor agrees in writing to embeddings on `main`; or a larger or
      held-out question set shows paraphrase questions that fts misses and hybrid finds, by more
      than a few passages, with refusal and forbidden-hit numbers no worse; or a reranker that beats
      RRF order on tier-1 passage recall on this corpus. Any such change needs a new ADR that
      supersedes this one.
    - Consequences: `main` keeps one debuggable SQL path and meets EJ-10; teammates install nothing
      new and no reinstall/new snapshot is needed; paraphrase-heavy theme questions (Q17) may still
      lag; `exp/hybrid` is kept as the record and can be rebased if the question reopens.
  - ADR-001 Status line only: `Accepted (vectors: optional module, off by default, see ADR-009;
    hybrid evaluated, not adopted, see ADR-010)`. Body untouched.
  - ADR-009 Status line only: append `; hybrid retrieval lives on exp/hybrid only, see ADR-010`.
    Body untouched (its #125 bullet is explained by ADR-010, per the #125 decision comment).
- `specs/retrieval.md` (**S1 reviews**)
  - Open question line 67: strike through and answer, the same style as the settled #49 item:
    "~~When would hybrid search be justified?~~ Compared in #126 on `exp/hybrid`: not on this
    question bank; `main` stays FTS-only (ADR-010, EJ-10). Report: <pinned link>."
  - Reference line 17 "Postgres FTS; RRF later" -> "Postgres FTS; RRF evaluated on `exp/hybrid`,
    not adopted (ADR-010)."
  - Header "Decisions:" line: add ADR-010.
- `docs/ARCHITECTURE.md` (TL) - line 176 Retrieval row: "Postgres FTS first; later
  Grounded-Rag-Analyst RRF" -> "Postgres FTS (ADR-001, ADR-010); Grounded-Rag-Analyst RRF evaluated
  on `exp/hybrid`, not adopted". Nothing else in the file is wrong (the `chunk_embeddings` block is
  ADR-009's optional module and stays).
- `plans/0127-hybrid-adr.md` - this plan, Progress log.

Not changed: any file under `src/`, `config/`, `db/`, `scripts/`, `evals/` (answer key, questions),
`.env.example`, `docs/RUN.md`, `docs/PROGRESS.md` (bot only), the bodies of ADR-001 and ADR-009,
`exp/hybrid`.

## Steps
1. Write ADR-010 and the two Status-line pointers in `docs/DECISIONS.md`. Copy every number from
   `git show 3449cc5:evals/hybrid-eval/corpus-2026-10-29/summary.json` (fts main-code numbers from
   the 0125 plan's Progress log), never retype from memory.
2. Edit `specs/retrieval.md` (three lines) and `docs/ARCHITECTURE.md` (one row).
3. Run the checks in Acceptance; log results in the Progress log.
4. `/finish-task`: PR into `main`, "Closes #127", S1 requested as reviewer for `specs/retrieval.md`,
   PR body states the acceptance mapping below, 0 real calls, no verify-cee (docs-only: no `src/`,
   `config/`, database or corpus change, CLAUDE.md Verification), and that the ADR change escalates
   the PR to the TL (expected). Progress line for the bot.

## Issue acceptance -> this plan
- "ADR merged with the #126 numbers and the default mode" -> ADR-010 (numbers table, `fts` default
  and only mode on `main`), merged by the TL after escalation.
- "Only if hybrid is adopted on `main`: every teammate reports `cee.smoke` PASS ..." and the
  reinstall note in RUN.md / to the team -> **does not apply**: hybrid is not adopted, `main`'s
  install, `.env.example` and snapshot do not change. Stated in ADR-010 Consequences and the PR.
- "PROGRESS.md row" -> PR `## Progress line`; the bot writes the row on merge into `main`.
- Verification "Default mode set in `.env.example`" -> nothing to set: `main` has one mode and no
  mode key; "verify-cee all features PASS on the new snapshot" -> no new snapshot and no code
  change, so not run (docs-only), stated in the PR.

## Acceptance
- [ ] Linked questions: Q1-Q30 numbers quoted only from #126 `summary.json` at 3449cc5; Q17, Q29
      named as in the report. No question or answer-key change.
- [ ] Only allowed files changed: `git diff --name-only origin/main...HEAD` -> exactly
      `docs/DECISIONS.md`, `docs/ARCHITECTURE.md`, `specs/retrieval.md`, `plans/0127-hybrid-adr.md`.
- [ ] ADR-001 and ADR-009 bodies untouched: `git diff origin/main -- docs/DECISIONS.md` shows, outside
      the new ADR-010 block, only the two `Status:` lines changed (`-`/`+` lines counted: 2 / 2).
- [ ] Numbers match: a `python -c` that loads `summary.json` from `git show 3449cc5:...` and checks
      that each of the 12 values in the table (PASS/FAIL, docs, passages for the four rows) appears
      in the ADR-010 block -> prints `all numbers found`. PowerShell and bash forms in the Progress log.
- [ ] Pinned links resolve: `gh api repos/RENEGADES20/Competitive-Evidence-Engine-EDJ/contents/evals/hybrid-eval/corpus-2026-10-29/report.md?ref=3449cc52171406a45dfd4d13e39e227adbecd1e3 --jq .sha`
      (and `summary.json`) -> a sha, no 404.
- [ ] No stale "RRF later" on `main`: `git grep -n -i "RRF later\|later Grounded-Rag-Analyst RRF"` -> nothing.
- [ ] No code/config change: `git diff --stat origin/main...HEAD -- src config db scripts evals .env.example` -> empty.
- [ ] 0 paid calls; no eval run needed (numbers come from the committed #126 report).

## Open questions (for the plan reviewer / TL)
1. ADR number: **ADR-010** (as the brief says) leaves ADR-008 as a permanent gap; alternative is to
   fill ADR-008. Plan: ADR-010, with one sentence in ADR-010 that ADR-008 was never used.
2. EJ-10 also lists "pgvector, embeddings or any embedding model" on `main`; ADR-009's optional
   vectors module (`db/optional/vectors.sql`, `cee.retrieve.embed`, `requirements-vectors.txt`) is
   still on `main`, off by default. Out of #127's scope; ADR-010 only notes that it is unchanged.
   Whether to move it to `exp/hybrid` too is a TL/sponsor call (possible follow-up issue).
3. The fts headline differs by code: #126's fts (exp/hybrid, with `synonym_only`) 28/2 vs `main`'s
   fts 27/3 (Q29 FAIL, refusal gap 4/5). The ADR states both; bringing `synonym_only` to `main`
   stays with the TL's separate Q29 decision.

## Progress log
- 2026-11-05 20:36 - plan written on `tl/127-hybrid-adr` from `origin/main` 9dc4c9b. Read #125/#126/#127
  and comments, ADR-001/003/009, EJ-10 and section 4 of the sponsor spec, #126 report and
  `summary.json` at 3449cc5 (all quoted numbers verified), plans 0125/0126 on `exp/hybrid`.
