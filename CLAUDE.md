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
5. **Licensed data stays inside its license.** Until ADR-000 closes, design so source
   tiers 2-5 alone clear the bar (see `docs/DECISIONS.md`).
6. **Nothing normative.** Never say what the home firm should do. Assemble evidence, then
   hand the "should" back to the strategist.

## Architecture invariants

- **Hard filters live in the retrieval layer, down to segment.** Entity and segment are
  SQL `WHERE` clauses, not prompt instructions. Merrill = `entity=MER` or
  (`entity=BAC` and `segment` in GWIM/Merrill).
- **Time windows are filtered in SQL**, not judged by the LLM.
- **One LLM call per answer by default.** Multi-call designs need a new ADR.
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
  tasks may skip the ExecPlan.
- PRs use `.github/pull_request_template.md` and include "Closes #N".
- The tech lead reviews and merges. Do not merge your own PR.

## Working rules for Claude

- Explain what you are doing in plain language; most teammates are not software engineers.
- Keep changes inside the files your ExecPlan lists. Ask before widening scope.
- Never read, print or commit `.env` files or API keys. Copy `.env.example` instead.
- Never commit raw documents or database dumps (`data/raw/`, `*.dump`); only
  `data/manifest.csv` goes into git.
- Do not invent entity facts (CIKs, segment names). Mark unknowns `TODO-verify`.
- When a question ID is relevant, cite it (e.g. Q30) and check it against
  `evals/questions.yaml`.
- Log what landed in `docs/PROGRESS.md`.
- Out of scope this term: alerts, live web-browsing agents, recommendations, forecasts,
  any internal or client data, SSO, multi-user, mobile, decks, reports.
