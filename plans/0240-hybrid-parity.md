# 0240 - exp/hybrid: hybrid with planner parts and token budget, scored 30-question run vs #217 fts

Issue: #240    Role: TL    Spec: specs/retrieval.md (modes section), evals/questions.yaml
Base branch: `exp/hybrid` (ADR-011). Branch `tl/240-hybrid-parity` from `origin/exp/hybrid` 2ca4101
(PR #239, main synced after #238). The PR targets `exp/hybrid`, never `main`.

## Goal
On `exp/hybrid` the hybrid modes take the same question plan, the same per-part search loop, the
same token budget and the same pool rule as fts on `main` (ADR-019, ADR-020), so the only thing
left that differs between `fts` and `hybrid-norerank` is how candidates are found and ranked. Then
one scored real run of all 30 questions in `hybrid-norerank` on `corpus-2026-11-19`, answering from
the very same #217 planner outputs (reused from the cache, 0 planner calls), scored blind and
compared question by question with #217's fts verdicts (24/30, tier 1 14/18).

## Inputs read
Issue #240 (+ TL go-ahead comment 2026-11-19), `CLAUDE.md`, `PLANS.md`, `.claude/commands/tl-run.md`,
`start-task.md`, `finish-task.md`, `plans/0211-hybrid-retest.md`, `plans/0217-final-run.md`,
ADR-019 and ADR-020 (`docs/DECISIONS.md`), on the branch: `src/cee/retrieve/modes.py`, `hybrid.py`,
`planner.py`, `fts.py` (`search`, `research_pass`, `peer_pass`, `budget_tokens`, `select`),
`src/cee/ask.py`, `src/cee/config.py`, `scripts/eval_run.py` (`run_bank`, `RealRunner`,
`cache_key`, `plan_cache_key`), `scripts/verify_cee.py` (plan-parts / part-gap steps),
`tests/test_search_mode.py`. Evidence: `D:\ALLPROJECTS\EDJ\cache\ev217\` (run scripts, head log,
raw copies), `D:\ALLPROJECTS\EDJ\repo\.eval-runs\0217-real-2\report.json` (meta and per-question
plan / call counts only).
Not read, on purpose, until the blind hash is committed (step 9): `docs/results/w10-report.md` /
`.json`, `ev217\verdicts-blind.json`, `ev217\answers-*.txt`, the #238 review comments. While
planning I saw #217's per-question `behavior` field in `0217-real-2\report.json` (the model's
behavior label, not a verdict); stated here so the reviewer can weigh it.

## What differs today (exp/hybrid 2ca4101) between fts and the hybrid modes
| # | fts (= main) | hybrid modes today |
|---|---|---|
| D1 | `modes.plan_for` -> `planner.plan_question` (one planner call on a real provider, rule plan on mock) | one whole-question part, no planner call |
| D2 | `modes.search(plan=...)` -> `planner.search_parts`: research once, each part with `part_query(q, part)` (its firms, its words, the whole question's doc-type scope) under an equal share of the token budget, earlier parts' chunks excluded, peers once | one `hybrid.search(q)` on the whole question; every hit `part_id` "p1" |
| D3 | token budget `budget_tokens(q)` (40k, five firms 60k; research tokens off the firm part) | passage budget `budget(q) - peer_slots(q)` (20 / 30 passages) |
| D4 | pool: best `POOL_PER_GROUP` = 30 per (firm, document type) in every SQL pass | `RERANK_N x k / K` candidates per part (50 / 75), `THEME_RERANK_N` 20 for research, taken in (quota firm, type) turns |
| D5 | `eval_run.py`: token mode plans (`b_tokens` set, `plan_question` / `RealRunner.plan`) | `b_tokens` None for hybrid, so no plan; `plan_for` one-part plan only for the answer |
Same in both already (#211): every hard SQL filter, quota firm, floor base, theme slot, answer
turns, peers, slot order, `date_basis`, `PoolTrace`.

## Design (the code change)
1. **Plan (D1).** `modes.plan_for(q, provider, mode)` calls `planner.plan_question(q, provider)`
   for every mode; `mode` is only validated (`resolve_mode`). The mode is resolved once per
   request / run (`ask.ask`, `eval_run.main`) and passed down; nothing re-reads `RETRIEVAL_MODE`
   per part.
2. **Per-part search (D2).** New `hybrid.search_parts(q, plan, rerank, trace=None, part_pools=None)`,
   a line-for-line mirror of `planner.search_parts` (which stays byte-equal to `main`): passage
   mode / not searchable -> one whole-question `hybrid.search`; else `hybrid.research_pass(q)` once,
   then each part `hybrid.search(planner.part_query(q, part), text=part.text, tokens=share,
   exclude=kept, research=False, peers=False)` with the same share rule
   (`max(0, T - research - used) / parts left`), `plan.searched` / `plan.research_tokens` /
   `part_pools` / `trace` filled the same way, then `hybrid.peer_pass(q, kept)` once, window ->
   newest first. `planner.part_query` is reused, so each part keeps entity / segment (Merrill = MER
   or BAC GWIM/Merrill), window, firm filter, date range, keywords and the whole question's
   doc-type scope as SQL filters (CLAUDE.md invariant, ADR-012). `modes.search(q, mode, plan, k=None)`:
   fts unchanged; hybrid modes with a plan and k None -> `hybrid.search_parts(..., rerank=mode == "hybrid")`;
   an explicit k -> `hybrid.search(q, k)` (passage rule, the `--k` / grid path).
   Why a mirror and not a shared loop: `planner.py` is not a hybrid file and must equal `main`;
   a parity test (T3) pins the mirror to `planner.search_parts`.
3. **`hybrid.search` signature like `fts.search` (D3).** `search(q, k=None, scorer=None,
   timings=None, rerank=True, trace=None, tokens=None, exclude=None, research=True, peers=True,
   text=None)`. `tokens is None and k is None` -> `tokens = fts.budget_tokens(q)`; research is
   selected first and its tokens come off the firm part; `fts.select(..., tokens=firm_tokens,
   unattached=...)` as `fts.search` does; peers on top. `exclude` drops kept chunk ids from every
   pool and from the answer-turn map. `research_pass(q, rerank, trace)` and `peer_pass(q, kept,
   rerank, trace)` are the research and peer parts of `hybrid.search` on their own, from the whole
   question (as `fts.research_pass` / `fts.peer_pass`).
   `text` = the text the vector leg embeds (and the `hybrid` cross-encoder scores against); None ->
   `q.question`. In a part it is `part.text`, the planner's one-sentence statement of the part
   (for a rule-plan part that is the question itself). The keyword leg uses the part's
   `keyword_query` through `part_query` exactly as fts. Reason: the keyword words are a bag of
   filing terms; the embedding model was built for sentences, and the part's sentence is the
   part's ask. This is a "how candidates are found" choice, stated in the spec.
4. **Pool (D4).** The fused list (both legs, `LEG_K` 100 per quota firm and leg, RRF per quota
   firm, unchanged from #211) keeps the best `fts.POOL_PER_GROUP` (30) chunks per (quota firm,
   document type) group, for every part (firm, on-theme, research, peers), instead of
   `RERANK_N x k / K` / `THEME_RERANK_N` taken in turns. That is fts's ADR-019 pool rule applied to
   hybrid's ranking. `RERANK_N`, `THEME_RERANK_N` and `take_turns` go (no other user). Constants not
   retuned: `FLOOR[hybrid-norerank] 0.4`, `MAX_PER_DOC 3`, `hybrid` 0.4 / 4, `LEG_K`, `RRF_K`,
   `ON_THEME_SCALE`. The `hybrid` (rerank) mode gets the same pool; its cross-encoder then scores
   more passages (slower); it is a reference, never scored here.
5. **eval_run (D5).** `run_bank` plans in token mode for every retrieval mode (`b_tokens =
   budget_tokens(query)` when `--k` is not given, any mode); the warm-up plans the same way; the
   `retrieval_mode != "fts"` one-part-plan branch for the answer goes; `meta.token_budget` is set
   for every mode. The planner cache key (`plan_cache_key`) is unchanged; see "Planner-cache reuse".
   New `--reuse-plans PROVIDER:MODEL` (mock only): each question's plan comes from the saved planner
   output whose key the real run would compute for that provider / model / request version
   (`llm.request_version(provider)`); 0 calls ever (no client is built); a missing file stops the run
   before the first question is searched, listing the question IDs. `RealRunner.plan` and this flag
   share one key / path function, so a 30/30 hit here means the real run hits 30/30 too.
   `eval_compare.py --run` gets `--no-decision` (the #211 decision line is not printed; the tables
   stay), for the mock comparison of step 6.
6. **App and driver.** `ask.ask` already goes through `modes.plan_for` / `modes.search`; its
   docstring line about the one-part hybrid plan is corrected. `scripts/verify_cee.py`: in hybrid
   mode the two-firm question now expects the fts plan ("2 parts: p1 MS; p2 RJF", "in 2 parts",
   two part gaps checked as fts), the `(Smart search)` / mode suffix kept;
   `.claude/skills/verify-cee/features/search-mode.md` and `ask-progress.md` updated to match.
fts stays byte-identical: `fts.py`, `planner.py`, `config/`, `evals/expected_chunks.yaml` are not
touched; the fts branch of `modes.search` / `plan_for` keeps its calls.

## Files to change
All on the #211 hybrid file list (`plans/0211-hybrid-retest.md`, "Files to change"); nothing new
leaves it:
- `src/cee/retrieve/modes.py` - `plan_for` plans every mode; `search` routes hybrid plans to `hybrid.search_parts`; docstring.
- `src/cee/retrieve/hybrid.py` - `search` token budget / `tokens` / `exclude` / `research` / `peers` / `text`; per-group pool; `research_pass`, `peer_pass`, `search_parts`; docstring.
- `src/cee/ask.py` - docstring line only.
- `scripts/eval_run.py` - plans in every mode; `--reuse-plans`; shared plan-path helper.
- `scripts/eval_compare.py` - `--no-decision`.
- `scripts/verify_cee.py`, `.claude/skills/verify-cee/features/search-mode.md`, `features/ask-progress.md` - hybrid plan expectations.
- Tests: `tests/test_hybrid.py`, `tests/test_search_mode.py`, `tests/test_eval_run.py`, `tests/test_eval_compare.py`.
- Docs: `specs/retrieval.md` ("Retrieval modes" section only: per-part hybrid, pool rule, vector text, #240 result), `docs/RUN.md` ("Hybrid retrieval" section: the #240 mock and real commands, PowerShell + bash blocks).
- Evidence (`evals/hybrid-eval/` is a hybrid path): `evals/hybrid-eval/corpus-2026-11-19/mock/` (report.md, summary.json, inputs/*.json|md of the mock runs), `evals/hybrid-eval/corpus-2026-11-19/real/report.md`, `report.json`, `run-report.json` (the run's own report.json), `raw/*.json` (the 30 answer outputs and the 30 reused plan files the run copied; as #212 committed its raw folder).
- `plans/0240-hybrid-parity.md` - this plan.
Not changed: `fts.py`, `planner.py`, `config/`, `evals/questions.yaml`, `evals/expected_chunks.yaml`,
baselines, ADRs, `docs/results/`, `main`. No ADR: hybrid stays experimental on `exp/hybrid` and the
result goes back to the user (issue: out of scope).

## Tests (0 real calls; fake connection, fake embedder, fake planner client)
- T1 `test_search_mode.py`: `plan_for` calls `planner.plan_question` with the same arguments in all three modes (fake, call recorded); replaces `test_hybrid_plan_is_one_whole_question_part_without_a_call`. The fts test (`search` with a plan -> `planner.search_parts`) stays unchanged.
- T2 `test_search_mode.py`: `modes.search(mode="hybrid-norerank", plan=...)` calls `hybrid.search_parts` with that plan, `rerank=False` and the `part_pools` dict; `mode="hybrid"` -> `rerank=True`; explicit k -> `hybrid.search(q, k)`, no plan loop; vectors off -> `HybridUnavailable` before any import.
- T3 parity `test_hybrid.py`: one fake per-part searcher (returns fixed hits of known lengths per part, records `tokens`, `exclude`, the part query) plugged into both `planner.search_parts` (via `fts.search` / `research_pass` / `peer_pass`) and `hybrid.search_parts` (via `hybrid.search` / `research_pass` / `peer_pass`): same order of hits, same `part_id`s, same shares, same `exclude` sets, same `plan.searched` and `research_tokens`, for a 1-part, a 3-part, an entity+theme (research + peers) and a window plan (newest first).
- T4 hard filters per part `test_hybrid.py`: `hybrid.search(planner.part_query(q, part), ...)` with a fake connection: both legs' SQL and params carry only the part's firms (Merrill part: MER or BAC GWIM/Merrill via `entity_filter`), the window, the firm filter / date range / keywords (`filters_sql`), the whole question's doc-type scope (`q.scope`), and the keyword leg uses the part's `keyword_query` terms; the answer-turn query carries the same filters.
- T5 vector text: the fake embedder receives `part.text` for a part and `q.question` for the research and peer passes and for `text=None`.
- T6 token budget: k None -> `fts.select` receives `tokens = budget_tokens(q) - research tokens`; `tokens=share` is passed through; explicit k -> passage rule, `tokens` None.
- T7 exclude: an excluded chunk is in no pool, no answer-turn map, no hit.
- T8 pool: a fused list of 80 chunks over two document types of one quota firm keeps 30 + 30; MER and BAC GWIM chunks share one quota firm's groups.
- T9 `test_eval_run.py`: a hybrid-norerank mock run in token mode plans (rule plan) and passes the plan to `search`; the planner record path of a fake real run is the same in fts and hybrid-norerank (second run in the other mode reuses it: fake planner client called once in total).
- T10 `test_eval_run.py`: `--reuse-plans anthropic:claude-sonnet-5-5` loads saved plans with a planner client that fails if built; a missing plan stops the run with the question IDs listed, before any search.
- T11 `test_eval_compare.py`: `--no-decision` prints no decision line, tables unchanged.
- Existing hybrid tests that pinned `RERANK_N x k / K` or the one-part plan are updated to the new rule (named in the PR). The DB-backed hard-filter test (skipped unless `CEE_VECTORS=on` with every chunk embedded) also runs Q4 (Merrill) and Q26 (90-day window) through `hybrid.search_parts` with the rule plan.

## Steps
1. **Pre-checks, 0 calls.** `git status` clean; `scripts\sync-db.ps1 -Check` -> "corpus-2026-11-19";
   `SELECT count(*) FROM chunks` = `SELECT count(*) FROM chunk_embeddings` (= 21,161, PR #237);
   `cee.retrieve.hybrid --check` with `FASTEMBED_CACHE_PATH=D:\ALLPROJECTS\EDJ\cache\fastembed`
   loads both models from the cache (no fetch); versions print `v4.1 plan-v2 20000 strict-1`.
   Log to `D:\ALLPROJECTS\EDJ\cache\ev240\precheck.txt`.
2. **Code** (Design 1-6) **and tests** (T1-T11); pytest on the branch with `PYTHONPATH=<wt>\src`.
3. **Diff check.** `git diff origin/main --stat` lists only #211 hybrid-list files + this plan +
   `evals/hybrid-eval/`; `git diff origin/main -- src/cee/retrieve/fts.py src/cee/retrieve/planner.py config evals/expected_chunks.yaml evals/questions.yaml` is empty.
4. **Planner cache in the worktree.** `eval_run.py`'s cache is `<wt>\.eval-runs\cache` (gitignored),
   empty in a new worktree. Copy the 30 `Q*-plan-*.json` files of #217 from
   `D:\ALLPROJECTS\EDJ\repo\.eval-runs\cache` into it; check each one's sha256 equals its copy in
   `ev217\real\` or `ev217\real-2\` (30/30). No answer file is copied (an answer key contains the
   chunk ids, so no #217 answer could be reused by a hybrid run anyway; copying none makes that sure).
5. **Mock runs, 0 calls** (`LLM_PROVIDER=mock`, `CEE_VECTORS=on`, `PLANNER=on`, `PLANNER_MAX_PARTS=4`,
   `--as-of 2026-11-17`, `--baseline evals\baselines\corpus-2026-11-19\report.json`, outputs in
   `<wt>\.eval-runs\0240-*`):
   - M1 `--mode fts` (rule plans): 30/30 chunk lists identical (ids and order) to the baseline
     `evals/baselines/corpus-2026-11-19/` and to `repo\.eval-runs\0217-mock`. **Stop rule**: any
     difference -> no hybrid run, find the cause, fix, rerun M1; nothing later uses a commit that failed M1.
   - M2 `--mode hybrid-norerank` (rule plans, the same plans as M1): the issue's mock check.
   - M3 `--mode fts --reuse-plans anthropic:claude-sonnet-5-5` (#217's real plans, 0 calls): 30/30
     plans found (the planner-key check) and 30/30 chunk lists identical to
     `repo\.eval-runs\0217-real-2\report.json` (proves the reused plans and fts retrieval reproduce
     what #217's model read).
   - M4 `--mode hybrid-norerank --reuse-plans anthropic:claude-sonnet-5-5`: hybrid on #217's plans;
     its chunk lists are what the real run will send to the model.
   - M5 `--mode hybrid` (rerank, rule plans): reference smoke only (no crash, time); not scored.
   Each mode runs once; nothing is re-run to change a number.
6. **Mock report.** `eval_compare.py --run fts=M1 --run hybrid-norerank=M2 --run hybrid=M5 --no-decision`
   and the same for M3 / M4, into `evals/hybrid-eval/corpus-2026-11-19/mock/` (report.md, summary.json,
   inputs): per mode PASS/FAIL, recall@pool and recall@final (all rows and tier 1), tier-1 passage
   recall, refusal gap / keyed, forbidden hits, tokens and passages per question, search time; per
   question recall@pool / recall@final for hybrid vs fts on all 30. Labelled: recall@pool is now
   like-for-like in rule (30 per group in both modes) but not in what the groups hold.
   **Go / no-go for the real run**, fixed here: the real run goes ahead when M1 and M3 pass their
   identity checks, M3 finds 30/30 plans, and M2 and M4 finish all 30 questions with no error.
   Lower hybrid recall is a finding and never cancels the run (TL rule: mock recall never gates a
   real quality run). Refusal: M2 and M4 must show refusal gap 5/5 (acceptance item); if either is
   below 5/5, the numbers go to the coordinator before any paid call (the scored mode is then a TL
   decision), no call is made meanwhile. `hybrid-norerank` is the scored mode (#211 / #212 chose it;
   the reranker mode was slower and below it on #211); M5 never decides.
7. **Real run, last, one run** (Paid-call plan). Commit and push everything up to the mock report
   first; no commit between the HEAD log before and after the paid command.
8. **Save.** Copy `.eval-runs\0240-real\raw\*`, `report.json`, `report.md` and the log to
   `D:\ALLPROJECTS\EDJ\cache\ev240\real\` (attempt N >= 2: `ev240\real-N\`). Record `real_calls`,
   reused, per question `how` (called / cached / invalid / cap / no_call), plan source (must be
   `model` from the cache for all 30), `stop_reason`, input / output tokens from `usage`.
9. **Blind scoring** (mirrors #217 step 4). Dump the 30 answers (claims with cited passage text,
   adjacent, gaps, caveats, parts, part coverage) from the scored records to
   `ev240\answers-dump.txt` (adapted from `ev217\dump217.py`). Read each against its `passes_if` and
   expected behavior, before opening #217's verdicts, `w10-report.md/json`, `ev217\answers-*` or
   the #217 answers. Verdict rule as #217 / Gate 4: PASS only if the project lead would forward the
   answer with his name on it; no half credit; classes r / s / b / c / i; borderline named. Write
   `ev240\verdicts-blind.json` (verdict, class, borderline, one-line reason per question), add a
   Progress-log line with its time and sha256, **commit and push that line before step 10**. The
   file's exact bytes go into `real/report.json` (field `blind`) so the hash can be recomputed.
   Citation check: every cited chunk id is in its retrieved set and in the database; code
   number-check flags checked against their passages.
10. **Comparison with #217** (only now are #217's verdicts opened: `docs/results/w10-report.json`,
    final verdicts after the second read, 24/30, tier 1 14/18). Per question: hybrid verdict vs #217
    fts verdict; passage recall and recall@pool / recall@final of both real runs (`0240-real` vs
    `0217-real-2` report.json); the retrieved chunks only one mode had (counts, and every expected
    row of `expected_chunks.yaml` found by one mode only, by id); the cited chunks only one mode
    cited; for every verdict that differs, the cause: **retrieval** (a deciding passage was in one
    retrieved set only, chunk ids named) or **model** (the deciding passages were in both sets, the
    model chose or wrote differently); several allowed. Plans are identical by construction (M3), so
    a "planner" or "pipeline" label should not occur; if one does, it is a bug, reported. Blind
    verdicts are never edited; a reading error found here is logged beside them.
11. **Report** `evals/hybrid-eval/corpus-2026-11-19/real/report.md` and `report.json` (generated by
    a scratch script in `ev240\`, not committed): how it was run (commit, snapshot, as-of, model,
    prompt / planner / request versions, mode and constants, command, plans reused), score /30 and
    tier 1 /18 next to #217's, per-question table (tier, expected -> got behavior, #217 verdict,
    hybrid verdict, class, label, recall both modes, only-one-mode passages), borderline list, every
    differing question with its cause, cost (calls per attempt, reused, tokens), mock summary link.
    `report.json`: the scored records, `blind`, `verdicts` (first read; second read added in review),
    `comparison` per question. Plus `run-report.json` and `raw/`.
12. **Second read** (as #217 step 7): the borderline list = every question this scoring marks
    borderline + every question whose verdict differs from #217 + #217's borderline set (Q7, Q15,
    Q17, Q19, Q22, Q25, Q26, Q28). The PR-review reviewer reads those answers from
    `.eval-runs\0240-real\report.md` / `ev240\answers-dump.txt` against `passes_if` before opening
    `real/report.md`, and posts its verdicts as a PR comment. Review round 1 posts them and returns
    the PR with the "read twice" item open (planned, not a blocking return); the implementer adds a
    "Second read" table (both verdicts, differences discussed; the reported score stays the first
    scorer's with the range the second read implies); review round 2 checks it and merges.
13. **Docs, app check, finish.** `specs/retrieval.md` modes section, `docs/RUN.md` commands
    (PowerShell + bash). verify-cee: `run` (fts) and `run --mode hybrid` with `CEE_VECTORS=on`
    (Smart search, two-firm question in 2 parts); evidence folders under `<wt>\.verify-runs\`.
    pytest; `/finish-task`: PR into `exp/hybrid`, "Closes #240", Verification with the call count,
    the go-ahead quoted, the borderline list for the reviewer; `gh pr checks` green.

## Planner-cache reuse from #217
- Key (`eval_run.plan_cache_key`): question id, question text, `PLANNER_VERSION` (plan-v2),
  snapshot (corpus-2026-11-19), provider (anthropic), model (claude-sonnet-5-5), `max_parts` (4),
  `PLANNER_MAX_TOKENS` (2000), `asdict(query)` (the resolved query), request version (strict-1).
  **The retrieval mode is not in it**: `Query` has no retrieval-mode field (`mode` there is the
  question type entity / theme / entity+theme), and `RealRunner` takes no mode. So a hybrid run
  computes #217's keys if the resolved query is the same, which needs the same `--as-of 2026-11-17`
  (the window is in the query), the same `fts.py` / `config/` as #217's commit 99ac877 (equal to
  `main`; step 3 checks the diff is empty) and `PLANNER=on`, `PLANNER_MAX_PARTS=4` (set explicitly in
  the run's environment). `planner.py`'s version and output cap are main's. T9 pins mode-independence;
  M3 proves 30/30 before any call.
- Expected for the real run: **0 planner calls, 30 planner outputs reused** (all 30 #217 questions
  had a model plan, `0217-real-2` meta: planner 1 per question). **30 answer calls**: every question
  reaches the model in #217 (none had 0 hits); a hybrid question with 0 hits would be answered in
  code (`no_call`) and lower the count. No answer is reused (none copied; answer keys hold chunk ids).
- **Cap `--max-calls 30`.** If M3 finds fewer than 30 plans, no paid call is made: each missing key is
  explained (which field of the key differs and why) to the coordinator, and the cap rises by one per
  missing plan only with that explanation logged here first. With 30/30 found, a planner call in the
  real run cannot happen; if one did, it would take an answer's place under the cap (the last
  question then shows `cap`), a finding, never re-run.

## Paid-call plan (CLAUDE.md "Paid API calls")
- **Go-ahead**: TL comment on #240 (2026-11-19), quoted in the PR: "TL go-ahead for the scored
  30-question real run ... run only after every mock check passes. One answer per question. Reuse
  the #217 planner outputs. Set a --max-calls cap stated in the ExecPlan (about 30 answer calls, plus
  any planner calls whose key cannot match, each explained). No re-rolls. Save every raw output."
- **Questions**: Q1-Q30, one run each, `hybrid-norerank`. Same settings as #217: `claude-sonnet-5-5`,
  prompt v4.1, `llm.MAX_TOKENS` 20000, request `strict-1`, `max_retries=0`, as-of 2026-11-17,
  snapshot corpus-2026-11-19, token budget 40k / 60k, pool 30, planner plan-v2 (reused).
- **Why the mock cannot show it**: the mock always answers when retrieval finds something; the score
  is a reading of real answers against `passes_if`.
- **Command** (run from the worktree, one run, last; script `ev240\run-real.ps1`, as `ev217\run-real.ps1`):
  ```powershell
  Set-Location D:\ALLPROJECTS\EDJ\wt-240
  $h = 'D:\ALLPROJECTS\EDJ\cache\ev240\head-log.txt'
  "before $(Get-Date -Format s) HEAD $(git rev-parse HEAD) branch $(git branch --show-current)" | Add-Content $h
  Copy-Item D:\ALLPROJECTS\EDJ\repo\.env D:\ALLPROJECTS\EDJ\wt-240\.env   # key for the run only, never read or printed
  $env:LLM_PROVIDER='anthropic'; $env:LLM_MODEL='claude-sonnet-5-5'; $env:CEE_VECTORS='on'
  $env:PLANNER='on'; $env:PLANNER_MAX_PARTS='4'; $env:PYTHONPATH='D:\ALLPROJECTS\EDJ\wt-240\src'
  $env:FASTEMBED_CACHE_PATH='D:\ALLPROJECTS\EDJ\cache\fastembed'
  & D:\ALLPROJECTS\EDJ\repo\.venv\Scripts\python.exe scripts\eval_run.py --real --max-calls 30 --mode hybrid-norerank --as-of 2026-11-17 --baseline evals\baselines\corpus-2026-11-19\report.json --out .eval-runs\0240-real *> D:\ALLPROJECTS\EDJ\cache\ev240\real-run.log
  $code = $LASTEXITCODE
  Remove-Item D:\ALLPROJECTS\EDJ\wt-240\.env
  'LLM_PROVIDER','LLM_MODEL','CEE_VECTORS','PLANNER','PLANNER_MAX_PARTS' | ForEach-Object { Remove-Item "Env:$_" }
  "after $(Get-Date -Format s) HEAD $(git rev-parse HEAD) branch $(git branch --show-current) exit $code" | Add-Content $h
  ```
  `.env` is gitignored in the worktree; it is copied (as #217 read it from the repo root, where
  `cee.config` loads `REPO_ROOT/.env`), never opened, and removed right after the command, also on
  failure (the removal runs whatever the exit code). The explicit env vars override anything in it
  (`load_dotenv` does not override). No other agent writes in this worktree during the run.
- **Rough cost**: as #217 (~2.0M input / 0.26M output tokens over 60 calls, ~$6.65), minus the 30
  planner calls: about $5-7.
- **Saved**: every raw output (question, prompt / planner version, model, request version,
  `stop_reason`, `usage`, payload) in `<wt>\.eval-runs\0240-real\raw\` and `<wt>\.eval-runs\cache\`,
  copied to `ev240\real\` and committed under `evals/hybrid-eval/corpus-2026-11-19/real/raw/`.
- **No re-runs.** An invalid output or a failed planner call is a counted call and a finding
  (answer FAIL class i), never re-run.

## Resume rule if a run stops (mirrors #217)
Attempt N >= 2 runs on the same commit, `--out .eval-runs\0240-real-N`, log `ev240\real-run-N.log`,
HEAD logged before and after, the `.env` copy and removal as above.
- (a) **Stop outside a model call** (traceback not from a provider request): the same command for all
  30 questions; every answered question is reused from the cache at 0 calls (`how` = cached);
  `--max-calls` = 30 minus calls made so far.
- (b) **Stop raised by an answer call** (API / network error or the 600 s timeout; `RealRunner.answer`
  catches only `ModelOutputError`): that question's answer call counts, the question is a finding
  (FAIL, class i, traceback quoted in the report) and is **never called again**. Resume with
  `--questions` = every question except the stopped one(s); answered ones are reused at 0 calls;
  `--max-calls` = the number of questions not yet called. A further (b) stop repeats the rule.
- **Request refused before any model work** (e.g. #217's `400 credit balance is too low`): stop and
  report to the coordinator. #217's TL decision (issuecomment-7011133159) treated that case as a stop
  outside the model's work, the refused answer called again in the resume and counted as one call
  with 0 output; this run follows that precedent unless the coordinator decides otherwise.
- Counting: an attempt's calls = its new raw files (reused copies excluded; a refused / failed
  answer call has a log entry and no file). The report and PR give calls per attempt and the total
  (<= 30 + any explained extra).
- Scored records: the last attempt's `report.json` plus, per (b) stop, its log entry.

## Acceptance
- [ ] fts unchanged: M1 chunk lists = `evals/baselines/corpus-2026-11-19/` on 30/30 (ids and order); M3 = `0217-real-2` on 30/30.
- [ ] Hybrid modes use the planner parts and the token budget: T1-T8 pass (request path, fake clients, 0 real calls in tests).
- [ ] Every SQL filter per part in hybrid mode: T4 and the DB-backed Q4 / Q26 test pass.
- [ ] Planner cache: the retrieval mode is not in the key (T9); M3 finds 30/30 #217 plans.
- [ ] Mock hybrid run: M2 and M4 refusal gap 5/5, no crash, recall table against fts (M1 / M3) for all 30 in `evals/hybrid-eval/corpus-2026-11-19/mock/report.md`.
- [ ] Real: one answer per question; `real_calls` = new raw answer files = 30 (or fewer with named `no_call`s), 0 planner calls, 30 planner outputs reused (count stated); HEAD before = after.
- [ ] Report: blind hash committed and pushed before the comparison (commit order); 30 verdicts with class; score and tier-1 score next to #217's; every hybrid / fts verdict difference with its cause and chunk ids; borderline list; second read of borderline and differing questions in the PR review, "Second read" table filled.
- [ ] `git diff origin/main origin/exp/hybrid --stat` after merge (and the branch's `git diff origin/main --stat` before) lists only hybrid files; fts.py / planner.py / config / keys / questions diff empty.
- [ ] pytest green; verify-cee `run` and `run --mode hybrid` (Smart search) all PASS; `gh pr checks` green.
- [ ] `.env` copy removed after every run (checked: `Test-Path <wt>\.env` False, in the Progress log).

## Risks
- **fts drift** (stop rule): M1 or M3 not identical -> no hybrid run until fixed.
- **Hybrid search time**: per-part search and a larger pool mean more SQL legs and more embeddings
  (one per part); `hybrid-norerank` should stay in seconds per question; the `hybrid` reranker mode
  may take minutes per question on CPU with pools of several hundred (M5 is a smoke run; if it would
  run past about an hour it is stopped and reported, it decides nothing).
- **Per-group pool vs LEG_K**: a quota firm's legs stop at 100 each, so its groups together hold at
  most ~200 fused chunks; a firm with many document types may fill fewer than 30 per group. Reported
  (mean pool size per mode), not retuned.
- **Vector text choice**: `part.text` is a planner sentence; a part whose text is weak gets weak
  vector candidates. Its effect shows in the M3 / M4 comparison per part (`parts_pool`).
- **One sample per question**: a verdict change can be model variance; labelled "model" when the
  deciding passages were in both retrieved sets; never re-rolled.
- **Scorer bias**: blind first, hash committed first, second read by the reviewer; the implementer
  saw #217's behavior labels while planning (stated above).
- **Shared database**: read-only use of `cee-db`; no other run on it during the real run.

## Progress log
- 2026-11-19 14:43 - plan written on `tl/240-hybrid-parity` from `origin/exp/hybrid` 2ca4101 (worktree `D:\ALLPROJECTS\EDJ\wt-240`). Checked: `Query` has no retrieval-mode field and `plan_cache_key` takes none; the 30 #217 plan files are in `repo\.eval-runs\cache` and `ev217\real*` (30 names); `0217-real-2` meta: max_parts 4, pool 30, token budget 40000, plan-v2, as-of 2026-11-17, all 30 questions called. 0 calls. Waiting for the reviewer agent's approval before step 1.
