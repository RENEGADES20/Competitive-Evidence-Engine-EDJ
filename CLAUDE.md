# CLAUDE.md

Instructions for Claude Code in this repo. The ground rules and architecture invariants
live ONLY here; every other file links to this one.

Project: Competitive Evidence Engine, a prototype that answers strategic questions about
a small wealth-management competitive set, where every claim cites a stored document.
Read `docs/BRIEF.md` for scope and `docs/ARCHITECTURE.md` for design.

## Ground rules

These do not bend. Breaking one produces a prototype the reader cannot trust.

1. **Every claim cites a stored document.** No citation, no claim.
2. **Never compose a source that is not stored.** Citations reference documents and chunks
   by internal ID (`doc_id`, `chunk_id`), never by a URL the model writes.
3. **"No evidence" is a correct answer.** The gap path is tested as hard as the happy path.
4. **No figure that is not traceable to a filing or licensed source.** No estimated AUM,
   no inferred headcount, no numbers from memory.
5. **Every document is traceable to where it came from.** A manifest row with source and
   tier for each one; tier 1 (Bloomberg, Capital IQ) is labelled `licensed`. Source use is
   settled in ADR-007 (`docs/DECISIONS.md`): internal, non-commercial, all sources allowed.
6. **Nothing normative.** Never say what the home firm should do. Assemble evidence, then
   hand the "should" back to the strategist.

## Architecture invariants

- **Hard filters live in the retrieval layer, down to segment.** Entity and segment are
  SQL `WHERE` clauses, not prompt instructions. Merrill = `entity=MER` or
  (`entity=BAC` and `segment` in GWIM/Merrill).
- **Time windows are filtered in SQL**, not judged by the LLM.
- **LLM calls follow the question's decomposition; no fixed number.** Firms x aspects, every
  sub-question keeps the SQL filters; every call is logged with tokens and cost (cost: #248). See
  ADR-021 (amends ADR-012).
- **Model-based work is developed on a branch, not `main`.** Anything that needs a model at
  query time besides the answer LLM calls (embeddings, rerankers, any local or hosted model in
  retrieval or validation) is built and tested there (today `exp/hybrid`). See ADR-011. An offline
  ingest extraction whose output is stored, code-checked data (the facts table) may land on `main`:
  query time then needs no other model (ADR-022).
- **Chunks never cross a section boundary.** PDFs keep page numbers.
- **Citations point only at `chunk_id`s** that were in the retrieved set; unmatched
  citations are flagged, never silently dropped.
- **Caveats are inserted by code** from `config/entities.yaml` (e.g. GWIM is not Merrill),
  never left to the prompt.
- **The question bank is append-only.** Never delete a question, never rewrite a trap,
  keep the share of gap/refuse questions at least where it is (`evals/questions.yaml`).
- Adding a firm is config + source list, not new code.

## Which spec to read before touching what

| Area you are changing | Read first | Owner |
|---|---|---|
| EDGAR, Form ADV, supplements, metric definitions, segment tagging | `specs/filings.md` | C1 |
| Entity config, aliases, source registry | `config/entities.yaml`, `specs/filings.md` | C1 |
| Earnings calls, investor-day PDFs, press releases, trade press | `specs/transcripts-ir.md` | C2 |
| Thematic research, topics taxonomy | `specs/thematic.md` | C3 |
| Search, synonyms, filters, retrieval modes, quotas, dedupe | `specs/retrieval.md` | S1 |
| Prompt, Answer JSON, citation/number checks, caveats, gaps | `specs/answer-citations.md` | S2 |
| Streamlit UI, source viewer, coverage view, feedback | `specs/ui.md` | U1 |
| Eval questions and scoring | `evals/questions.yaml`, `docs/PROGRESS.md` | C1 |
| Schema, shared corpus, snapshots | `docs/ARCHITECTURE.md`, `docs/DECISIONS.md` | Tech lead |

If your change touches two areas, read both specs and mention both in the PR.

## Branch and PR rules

- **Never commit or push to `main`.** A hook in `.claude/hooks/guard-main.py` blocks it;
  do not try to work around it.
- One issue -> one branch `<role>/<issue#>-<slug>` (e.g. `s1/14-synonyms`) -> one
  ExecPlan -> one PR.
- Start with `/start-task <issue#>`; finish with `/finish-task`. See
  `.claude/commands/start-task.md` and `.claude/commands/finish-task.md`.
- ExecPlans follow `PLANS.md` and are saved in `plans/NNNN-slug.md`. Tiny config/data-only
  tasks may skip the ExecPlan. A plan is one page; design detail goes in a results doc or an
  ADR and the plan links to it. Write each fact once and link to it elsewhere.
- **Two tracks.** *Delivery* (code that lands on `main`): the full flow above. *Experiment*
  (a question to settle with data, e.g. "does reduce effort off keep 24/30?"; issue label
  `type:experiment`): branch `exp/<issue#>-<slug>`, never merged; no ExecPlan, plan review,
  verify-cee or PR review. It starts with an experiment note (`PLANS.md`) and ends with a results
  doc that lands on `main` in a docs-only PR. A winning change is then built on the delivery track
  under its own issue. Paid-call rules apply on both tracks.
- PRs use `.github/pull_request_template.md` and include "Closes #N" (or "Part of #N" with
  the open items listed, when the issue is only partly done).
- The tech lead reviews and merges. Do not merge your own PR. Exception (TL only): PRs for
  `role:tl` issues are reviewed and merged by an independent reviewer agent through `/tl-run`
  and `/tl-review` (`.claude/commands/tl-run.md`, `.claude/commands/tl-review.md`; see
  `docs/DASHBOARD.md` section 3b). The plan gets its own review only when it carries risk
  (paid calls, an ADR or ground-rule change, schema / corpus / snapshot changes, deleted data);
  otherwise the PR review is the one review. Teammate PRs: the tech lead reviews and merges.

## Verification

- **Prove it in the running app.** Before `/finish-task`, any change a user could see in the
  app (UI, answer content or behavior, retrieval results, the database or the corpus) runs the
  `verify-cee` skill (`.claude/skills/verify-cee/`). Tests passing or "it compiles" is not proof.
  A change the app cannot show (request assembly, cache keys, logging, scripts, eval tooling)
  is proved by pytest plus the mock eval instead; the PR says why verify-cee was not run.
- **Each check has one owner.** CI runs pytest; the implementer runs verify-cee and the eval and
  keeps the evidence; the reviewer reads that evidence and re-runs only what is missing, failed,
  stale or in doubt (`.claude/commands/tl-review.md`, "Check rule").
- **Evidence, not opinion.** Report what was run, the result, and where the evidence is.
  A claim with no evidence is unverified; say "not verified" rather than guess.
- **A changed user feature updates its recipe** in `.claude/skills/verify-cee/features/`
  and the driver in `scripts/verify_cee.py` in the same PR.
- **The mock provider proves the pipeline, not answer quality.** It always answers when
  retrieval finds something.
- New teammates: follow `docs/WORKFLOW-SETUP.md` once.

## Paid API calls (money)

Every real model call (`LLM_PROVIDER=anthropic`, `openai` or `deepseek`) and every other paid API costs the
team money. The default is zero calls. Follow these steps whenever a task might call one.

1. **Not necessary, not called.** Building, debugging, UI, ingestion, retrieval and tests run on
   the mock provider (`LLM_PROVIDER=mock`) and fake clients. A real model is necessary only to
   judge answer quality (wording, behavior choice, whether claims match their sources).
2. **Plan before the first call.** Write down which question IDs, why the mock cannot show it,
   and how many runs of each. Use the fewest questions that prove the point.
   One run of a planned question through the full answer flow (every call the flow makes,
   ADR-021; the plan states the expected count) needs no tech-lead approval. Running the same question again (e.g. a second prompt version)
   is planned in the ExecPlan (or the experiment note) before the first call. There is no per-task total.
   The 30-question scored run (Gate 3) needs an explicit go-ahead from the tech lead.
3. **Make each call count.** Call only on finished code, after every mock check passes. Run the
   planned questions together in one run. Save every raw response (question, prompt version,
   model, output) in the run's evidence folder, so nobody pays for the same answer twice;
   reuse saved outputs before calling again.
4. **No loops.** Never call a paid API inside tests, CI, or a retry-until-it-passes loop. A
   wrong answer is a finding: report it, do not re-roll it.
5. **Report it.** The PR's Verification section states the number of real calls, the model,
   and why each was needed ("0 real calls" when none).

## Working rules for Claude

- Explain what you are doing in plain language; most teammates are not software engineers.
- Keep changes inside the files your ExecPlan lists. Ask before widening scope.
- Never read, print or commit `.env` files or API keys. Copy `.env.example` instead.
- Never commit raw documents or database dumps (`data/raw/`, `*.dump`); only
  `data/manifest.csv` goes into git.
- Do not invent entity facts (CIKs, segment names). Mark unknowns `TODO-verify`.
- When a question ID is relevant, cite it (e.g. Q30) and check it against
  `evals/questions.yaml`.
- Log what landed in the PR description under `## Progress line` (one line:
  `What landed | Blockers | Next`). A bot copies it into `docs/PROGRESS.md` when the PR is
  merged. Never edit the Status log in `docs/PROGRESS.md` by hand.
- Out of scope this term: alerts, live web-browsing agents, recommendations, forecasts,
  any internal or client data, SSO, multi-user, mobile, decks, reports.
