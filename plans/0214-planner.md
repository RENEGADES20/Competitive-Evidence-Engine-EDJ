# 0214 - Question planner: split a question into parts and retrieve each part (ADR-020)

Issue: #214    Role: TL    Spec: specs/retrieval.md (S1; owner review waived, TL decision
2026-11-17, #187), specs/answer-citations.md (S2, call count and purpose line only)

## Goal
Before search, one planner call (through the configured provider) splits the question into at most
`PLANNER_MAX_PARTS` (default 4) parts, each with its own firms and rewritten search words; code
validates the plan (firms, window, themes from `resolve()` can never be dropped), each part is
searched with every hard SQL filter inside a share of the question's ADR-019 token budget, the
hits carry their `part_id`, and the answer stays one call (at most 2 calls per question). The
mock provider uses a deterministic plan (`resolve()`, one part per named firm), so tests, CI and
the mock eval make 0 calls. ADR-020 records the rule. FTS only, `main`; no new model, no new
dependency.

## Facts (2026-11-19, read only)
- Base: `main` 43c68ed (#213 merged in PR #220). DB `cee` = `corpus-2026-11-17`
  (`sync-db.ps1 -Check`: up to date; the #211 vector tables are ignored by fts).
- Baseline = the #213 pick, `evals/baselines/corpus-2026-11-17/report.json` (commit 1da1890, mock,
  `--as-of 2026-11-17`, pool 30, `TOKEN_BUDGET` 40000): 29 PASS / 1 FAIL (Q19); recall@pool 0.814 /
  recall@final 0.654 (21 questions with rows), tier 1 0.903 / 0.808 (17); refusal gap 5/5, keyed
  22/22; 0 forbidden; 3,458 passages, ~988k tokens; tokens per question median 33,643, max 60,322.
- Linked questions in the baseline (stage of each expected row: final / pool = lost in select /
  none = never a candidate):
  - Q3 (SCHW, 1 part in the mock): 6/6 rows final (document-level key); Gate 4 FAIL: "nothing on
    ground management concedes and no gap naming that part".
  - Q7 (MS, MER, RJF): `MS-10K-2025#153` none. Gate 4: only two of four dimensions (payout
    philosophy, training pipeline missing).
  - Q12 (SCHW, EDJ; no answer-key rows): Gate 4: EDJ's cost structure not set alongside.
  - Q15 (five firms through "an advisor-led model"): `SCHW-10K-2025#27` pool.
  - Q25 (five firms): `RJF-10K-2025#10/#11` pool, `EDJ-10K-2025#30/#264` pool, `MS-10K-2025#153`
    none, `RJF-PR-web-affiliation-options#1` none, `SCHW-10Q-2026Q2#25` final. Behavior `answer`
    with empty gaps at the #213 pick: accepted by the TL, gap naming is #215 (not this issue).
  - Q28 (EDJ, MER): rows 1-3 final, `EDJ-10K-2025#130` / `EDJ-10Q-2026Q2#60` none. Gate 4: net
    headcount change and its difference from attrition missing.
  - #213's conclusion: the remaining "none" rows (Q7, Q15's selection aside, Q20, Q25) point to the
    query wording, which is what the planner's per-part `keyword_query` changes.
- Code today: `ask()` = resolve -> `search(query)` -> `answer_for()` (one call) -> `_log()`;
  `STAGES = ("resolve", "search", "model", "check", "caveats", "log")`; the Ask page divides its
  bar by `len(STAGES)` and labels the box "How this answer was built: N steps".
  `fts.search(q, k=None, trace=None)` builds its terms from `q.question` (`keyword_terms()`), its
  doc-type scope from `q.question` / `q.themes` / `q.window` / `len(q.entities)`
  (`doc_type_scope()`: the benchmark rule needs 2+ firms), and its theme peers from `q.theme_peers`.
- `query_log` has `filters jsonb` (today `asdict(query)`) and `answer jsonb`; the filters recipe
  reads `firm_filter`, `date_range`, `keywords` from `filters`. Storing the plan under a new key
  `plan` in `filters` needs no schema change (no `db/upgrade.sql`, no restore-script change).
- `llm.py`: Anthropic `MAX_TOKENS` 8000 for the answer, tool `submit_answer`, `ModelOutputError`
  with `raw` and `stop_reason`; OpenAI via `json_schema` strict. `eval_run.py` `RealRunner` caches
  every answer under `cache_key(q, prompt_version, snapshot, provider, model, chunk_ids,
  max_tokens)`, counts a call before making it, saves invalid outputs and never re-calls them.
- verify-cee: `ANSWERABLE_Q` names one firm (Edward Jones); the ask-progress driver checks "six
  step lines" and `tests/test_ask_page_trace.py` checks "6 steps".

## Design

### Plan schema (`src/cee/retrieve/planner.py`)
- `Part(id, text, firms: list[str], keyword_query: str | None)`; `Plan(parts, source, provider,
  model, version, corrections: list[str], error: str | None, raw, calls: int)`. `source` is
  `rules` (deterministic), `model` (validated model output) or `fallback` (model output not
  usable, deterministic plan used). `Plan.to_log()` gives the JSON stored in `query_log` and the
  eval record.
- Model output schema (tool `submit_plan`, Anthropic; `json_schema` strict, OpenAI):
  `{parts: [{id: str, text: str, firms: [str], keyword_query: str}]}`, `maxItems` =
  `PLANNER_MAX_PARTS`. Nothing else: the window, themes, firm filter, date range and keywords are
  not in the schema, so the planner cannot change them; extra keys are ignored.
- Prompt (`PLANNER_PROMPT`, `PLANNER_VERSION = "plan-v1"`), general rules only (no question ID,
  no `passes_if` text: the same 6-word leak check as `tests/test_prompt.py`): split the question
  into the parts it asks (each named firm or group of firms, each "and", each metric or dimension
  it names, and a part the question implies, such as where a firm concedes ground or the home
  firm's own figures when it is set against a peer); a part may cover several firms; at most N
  parts; `firms` only from the listed firm IDs; `keyword_query` = the words the evidence would use
  (filing / call vocabulary, e.g. "advisors who left or retired" for attrition), no firm names
  or dates (code adds those filters). The user message lists the question, the resolved firm IDs
  with names, the window (if any), the themes and N.
- Calls: Anthropic `max_tokens` `PLANNER_MAX_TOKENS = 2000`, same model setting as the answer
  (`LLM_MODEL` / `OPENAI_MODEL`), client built by a shared helper in `llm.py`.

### Deterministic plan (mock provider, `PLANNER=off`, fallback)
`rules_plan(q)`: n = len(q.entities) covered firms (after the Ask page firm filter; Merrill once).
- n <= 1, or n > `PLANNER_MAX_PARTS`: one part `p1` = the whole question, all firms,
  `keyword_query` None (today's terms). Five-firm questions (Q10, Q11, Q15, Q21-Q25) therefore stay
  one part in the mock: one part per firm would break the part cap.
- 2 <= n <= `PLANNER_MAX_PARTS`: one part per firm in `q.entities` order, text = the question,
  `keyword_query` None.

### Validation (code, every model plan)
1. Firm strings map to config IDs (ID, name or alias via `_mentions`); a firm not in
   `config/entities.yaml` is dropped ("unknown firm X"); a known firm not in `q.entities` is dropped
   ("not asked: X"; firm scope stays with `resolve()`, ADR-018); unmapped firms (no documents) are
   dropped (nothing to search; the gap path still reads `q.unmapped`).
2. A part left with no firm in a question that names firms gets all of `q.entities` ("no asked
   firm: all firms"); in a theme question (no firms) firms stay empty, as today.
3. More than N parts: the first N are kept ("cut to N parts").
4. A resolved firm in no part: a code part (whole question, those firms, `keyword_query` None) is
   added when there is room, else the firms join the part with the fewest firms (first such)
   ("added firm X"). Checked after step 3, so no resolved firm is ever dropped.
5. `keyword_query` stripped; empty -> the part's text, else the question ("no search words");
   longer than 400 characters -> cut at a word boundary ("search words cut").
6. Part ids are set by code (`p1`..`pn`, in output order).
7. Not usable at all (no tool call, invalid JSON / schema, zero parts, `stop_reason` `max_tokens`)
   -> `rules_plan(q)`, `source = "fallback"`, `error` set, the raw payload kept, the call counted.
   A finding, never a re-roll.
Every correction is listed in `Plan.corrections` (trace line, `query_log`, eval record).

### Per-part search (`planner.search_parts(q, plan, trace=None)` + small `fts` hooks)
- Each part searches a copy of the resolved query (`dataclasses.replace`) with
  `entities = part.firms` and `terms = part.keyword_query`; `question`, `window`, `themes`,
  `mode`, `firm_filter`, `date_range`, `keywords`, `unmapped` are the resolved ones, so every hard
  filter (entity/segment incl. Merrill = MER or BAC GWIM/Merrill, window, date range, keywords,
  doc-type scope) is applied in SQL in every part.
- `fts.Query` gets two optional fields: `terms: str | None` (search words; `keyword_terms()` uses
  them in place of the question text, through the same clean-up: firm names, peer phrases, time
  phrases, question words; synonyms, `synonym_only`, `RECENCY_TERMS` as today) and
  `scope: tuple[list[str], list[int]] | None` (`doc_type_scope_sql()` uses it when set). The part
  builder sets `scope = doc_type_scope(q)` of the whole question, so a one-firm part of a benchmark
  question keeps its tier-4 exclusion and the Form ADV rule is decided on the user's question.
- Theme peers (ADR-018): only the first part whose firms include the home firm keeps
  `q.theme_peers`; the others get none (peers are searched once, on top of the budget as today).
- `fts.search()` gets `tokens: float | None = None` (an explicit token budget; overrides
  `budget_tokens(q)`) and `exclude: set[str] | None` (chunk ids already kept by earlier parts,
  removed from the pools before `select()`, so a later part never spends its share on them).
- **Budget split** (fixed now; ADR-020): T = `budget_tokens(q)` of the whole question (ADR-019:
  40k, five firms 60k; unchanged caps). Parts are searched in plan order; part i of n gets
  share_i = (T - used) / (n - i), where used = estimated tokens (theme peers excluded) of the hits
  kept by parts 1..i-1. Equal shares, and the share a part leaves unused flows to the parts after
  it. No separate minimum: the cap (4) keeps every first share >= T/4 (10k; 15k for five firms).
  Each part ends at most one chunk past its share and the overshoot is taken off the next shares,
  so the budgeted total is <= T + the longest budgeted hit (the ADR-019 bound, per question).
  A one-part plan gets share = T, no exclude: **identical to today's `search(q)`** (test + step-3
  diff).
- Hits keep part order (window questions: re-sorted newest first over all parts, as today);
  `Hit.part_id` (new field, default None) = the part that kept it; a chunk is kept once (first
  part). The `PoolTrace` passed in collects every part's pools (recall@pool over all parts);
  `search_parts` also returns, per part, its pool ids, share, passages and tokens (eval / log).
- `build_user_message()` is not changed (no part labels in the prompt; prompt v4 is #215), so the
  answer prompt version stays v3.

### App (`ask.py`) and log
- `STAGES = ("resolve", "plan", "search", "model", "check", "caveats", "log")`.
- Plan stage: "Planning the search (rules, no model call): N parts: p1 MS; p2 RJF" / "Planning the
  search (anthropic, one call): N parts: ..." / fallback "Planning the search (anthropic, one
  call): output not usable (<reason>), using the rule plan: N parts". No planner call (0 calls) when
  code returns no hits without searching (unmapped firms only; firm filter leaves no firm), with
  `PLANNER=off`, or on the mock provider.
- Search line: "Searching the corpus: N passages from M documents in K parts" (the footer count
  check is unchanged). Model line unchanged ("(<provider>, one call)").
- `_log`: `filters` = `asdict(query)` + `"plan": plan.to_log()` (parts with firms, text,
  keyword_query, share, passages, tokens; source, provider, model, version, corrections, error) +
  `"llm_calls": {"planner": 0|1, "answer": 0|1}`. Hits' `part_id` is in the plan's per-part
  chunk ids. No schema change.
- Settings (`cee.config`, `.env.example`): `PLANNER` = on (default) | off; `PLANNER_MAX_PARTS`
  (int, default 4, 1-5).

### Eval (`scripts/eval_run.py`)
- Without `--k`: `rules_plan` (mock) or the planner (real), then `search_parts`; with `--k`: one
  whole-question part, passage rule (as today).
- Record per question: `plan` (`to_log()`), `parts` (count), `llm_calls` (`planner`, `answer`:
  calls made or reused from the cache), per expected row the ids of the parts whose pool / final
  set held it (`score_key(..., part_pools=...)`), plus every existing field (`budget_tokens` = T).
  Meta: `planner` (on/off), `max_parts`, `planner_version`.
- Real runs: `RealRunner.plan(q, query)` caches the planner output like an answer:
  `.eval-runs/cache/<qid>-plan-<key>.json`, key = sha256 of [qid, question, `PLANNER_VERSION`,
  snapshot, provider, model, max_parts, `PLANNER_MAX_TOKENS`, the resolved query as JSON]; copied to
  the run's `raw/`; the request meta and the raw output (valid or not, with `stop_reason`) saved. A
  cached plan (valid, or invalid -> fallback) is always reused, so an answer re-run never
  re-calls the planner; the answer cache key (chunk ids) then also hits. Planner and answer calls
  both count against `--max-calls` (counted before each call). A question whose planner call
  would pass the cap is "not run: --max-calls reached" (no answer call either).

## Files to change
- `src/cee/retrieve/planner.py` (new) - `Part`, `Plan`, `rules_plan`, prompt + schema
  (`PLANNER_PROMPT`, `PLANNER_VERSION`, `PLANNER_MAX_TOKENS`), `plan(q, provider, client=None)`
  (Anthropic / OpenAI / mock), `validate_plan`, `PlannerOutputError`, `search_parts`.
- `src/cee/retrieve/fts.py` (S1; waiver above) - `Query.terms`, `Query.scope`, `Hit.part_id`;
  `keyword_terms()` / `doc_type_scope_sql()` read them; `search(..., tokens=None, exclude=None)`;
  docstrings. Defaults leave every current call unchanged.
- `src/cee/answer/llm.py` (S2; waiver) - shared `anthropic_client()` / `openai_client()` helpers
  (the answer path calls them; behavior unchanged), module docstring (ADR-012/020 call count).
- `src/cee/ask.py` - plan stage, `search_parts`, `_log` with plan and call count, docstring.
- `src/cee/config.py`, `.env.example` - `PLANNER`, `PLANNER_MAX_PARTS`.
- `scripts/eval_run.py` - planner in the run, record / meta fields, plan cache, call count.
- `scripts/verify_cee.py` - ask-progress driver: seven step lines, plan line, a two-firm question.
- `.claude/skills/verify-cee/features/ask-progress.md` - recipe: plan stage, seven steps,
  `plan-parts` sub-feature.
- Tests: `tests/test_planner.py` (new: validation, rules plan, prompt leak check, fake-client
  Anthropic / OpenAI calls, fallback), `tests/test_retrieval_parts.py` (new: per-part search on the
  fixture schema of `tests/test_retrieval_themes.py` style), `tests/test_ask_progress.py`,
  `tests/test_ask_page_trace.py` (7 steps), `tests/test_eval_run.py` (plan cache, calls, fields).
- `docs/DECISIONS.md` - ADR-020 (Proposed); ADR-012 consequences note the feature landed.
- `specs/retrieval.md` - planner and per-part search section, ADR-020 link.
- `specs/answer-citations.md` - purpose line: one answer call after at most one planner call.
- `specs/ui.md` - the trace lists the plan line; "the trace adds no extra LLM call" stays (the
  planner call is not a trace call).
- `docs/ARCHITECTURE.md` - flow diagram line (planner before retrieval).
- `docs/RUN.md` - real-model line: about two calls per question.
- `evals/baselines/corpus-2026-11-17/report.json`, `report.md` - replaced by the final mock run
  (old one in git history at 5058259) if any chunk list changed.
- `plans/0214-planner.md` (this file).
Not changed: `db/schema.sql`, `db/upgrade.sql`, restore scripts (plan in `filters` jsonb), the
answer prompt (`prompt.py` v3), `evals/questions.yaml`, `evals/expected_chunks.yaml`, UI code
other than through `STAGES`.

## Paid-call plan (CLAUDE.md "Paid API calls"; TL pre-approval comment on #214, 2026-11-18)
Everything that decides the change runs on mock. Last, on finished code after every mock check and
verify-cee: **6 real runs, one each, planner + answer = 2 calls each = 12 calls**: Q3, Q7, Q12,
Q15, Q25, Q28. Model `claude-sonnet-5-5`, answer prompt v3, planner `plan-v1`, `--as-of 2026-11-17`:
`$env:LLM_PROVIDER='anthropic'; python scripts\eval_run.py --real --max-calls 12 --questions
Q3,Q7,Q12,Q15,Q25,Q28 --as-of 2026-11-17 --baseline evals/baselines/corpus-2026-11-17/report.json
--out .eval-runs/0214-real` (the script's "more than 10 calls" note is expected; the run is the
approved plan). Raw outputs (planner and answer, request meta, `stop_reason`) in the run's `raw/`
and copied to `D:\ALLPROJECTS\EDJ\cache\ev214\real`.
Why the mock cannot show it: the mock plan is a fixed rule (one part per firm, the question's own
words), so it never writes a part for "where they concede ground" (Q3), "Edward Jones's cost
structure" (Q12), "net headcount is not attrition" (Q28) or Q7's dimensions (payout philosophy,
training pipeline), and never rewrites the search words that #213 found to be the reason Q7, Q15
and Q25's named passages are not candidates. Only a model plan shows (a) whether the parts cover
every asked part and (b) whether its search words bring those passages into the pool / final set
and the answer cites them.
One run each, no re-rolls. A planner output that is truncated or invalid falls back to the rule
plan (logged, a finding, not re-run); an invalid answer output is `INVALID_OUTPUT` (a finding, not
re-run). No other call path. Any new call needs a new entry here first.

## Steps
1. **Plumbing, defaults = today.** `fts` fields and `search(tokens, exclude)` hooks; `planner.py`
   (rules plan, validation, `search_parts`, prompt / schema, fake-client calls); `config`
   settings; `llm.py` client helpers. Unit tests (below). `pytest -q`. Work happens in
   `D:\ALLPROJECTS\EDJ\repo` on `tl/214-planner` (the #212 agent works in `wt-212`; never touched).
2. **App.** `ask.py` plan stage, `_log` plan + calls; trace tests (7 steps, plan line, 2-call cap
   with counting fakes, fallback line). `pytest -q`.
3. **Mock eval.** `eval_run.py` changes + tests; then
   `python scripts\eval_run.py --as-of 2026-11-17 --baseline evals/baselines/corpus-2026-11-17/report.json
   --out .eval-runs/0214-mock`. Scratch diff / check scripts in `D:\ALLPROJECTS\EDJ\cache\ev214\`
   (not committed), output kept for the PR:
   - every question whose rules plan is one part (0-1 firm, or more firms than the cap): chunk list
     identical, same order, to the baseline; any difference stops the work;
   - multi-part questions (2-4 firms; e.g. Q7, Q8, Q9, Q12, Q28; the list from the run): every part's
     hits are its firms' (entity check per hit: firm, or BAC GWIM/Merrill for MER); budgeted chars
     <= 4 x T + `max_hit_chars`; no chunk twice; per-part share / passages / tokens tabled;
   - summary vs baseline: 30 questions, refusal gap 5/5, keyed 22/22, 0 forbidden, no PASS -> FAIL,
     recall@final all rows >= 0.654 and tier 1 >= 0.808 (recall@pool reported); tokens per question
     median / max (all hits) old vs new, five-firm questions <= 60k + one chunk;
   - per Gate 4 missed passage (Q7 `MS-10K-2025#153`, Q15 `SCHW-10K-2025#27`, Q17 `BAC-TR-2026Q2#21`,
     Q19 `EDJ-10K-2025#88`, Q20 `FIDELITY-III-2025#0`, `UBS-NEXTGEN-2026#119`/`#13`, Q25
     `RJF-PR-web-affiliation-options#1`, `MS-10K-2025#153`): stage (none / pool / final) and part,
     vs the baseline.
   A failed summary check is a finding: stop, report per question to the reviewer / TL (no tuning
   loop; no real calls on failing code). If any list changed and all checks pass, copy the run to
   `evals/baselines/corpus-2026-11-17/`.
4. **Docs.** ADR-020 (when a question is split: every question that reaches retrieval, model plan
   with a real provider and `PLANNER=on`, rules plan otherwise; part cap 4; budget split rule and
   bound; call count planner 1 + answer 1, 0 planner calls when code skips search, `PLANNER=off` or
   mock; fallback; plan stored in `query_log.filters`; mock numbers; real results after step 6),
   ADR-012 consequence note, specs, ARCHITECTURE, RUN, ui spec.
5. **verify-cee**: recipe + driver updated; `python scripts\verify_cee.py run`, all features PASS
   (ask-progress shows the plan line: "rules, no model call", 1 part for `ANSWERABLE_Q`; a two-firm
   question "How do Morgan Stanley and Raymond James approach advisor recruiting?" shows 2 parts
   and its newest `query_log` row (`cee_verify`) has `filters->'plan'` with 2 parts, source `rules`,
   and `llm_calls` planner 0, answer 0 (the mock makes no model call).
6. **Real runs last** (paid-call plan). Per question: the saved plan (parts, corrections, fallback
   or not), behavior vs expected, per named missed passage its stage and part and whether cited,
   calls (planner + answer).
7. `/finish-task`: PR "Closes #214" with the mock tables, the real-run table, call count (12) and
   model; the reviewer escalates to the TL for ADR-020.

## Risks
- **Mock recall for 2-4 firm questions**: a fixed equal share per firm can leave one firm's share
  unused while another runs out; the flow-forward only helps later parts. Seen in step 3; a drop is
  a finding (stop), not tuned.
- **Research per part**: in entity+theme each part fetches up to THEME_K research chunks; the
  exclude set removes repeats, the part's share pays for them.
- **Planner rewrites words badly**: a part whose `keyword_query` matches little returns few
  passages and leaves its share to the next parts; seen in the real plans, not re-rolled.
- **Cost / latency**: one more call per question (small input, <= 2000 output tokens); answer input
  stays inside ADR-019's caps (T + one chunk).
- **Five-firm questions in the mock stay one part** (cap 4), so the mock does not exercise their
  split; the real runs (Q15, Q25) do, and unit tests cover cap and firm merging.

## Acceptance
- [ ] Tests (fixture schema / fake clients, 0 calls): a part with firms [MER] returns only MER or
  BAC GWIM/Merrill-tagged chunks; a window question applies the window in every part (no hit outside
  it, `date_basis = source` only); a planner output naming an unknown firm drops it, one naming an
  asked-but-not-resolved firm drops it, one dropping a resolved firm gets it back (code part or
  merge), more than N parts is cut, empty `keyword_query` is replaced, extra `window` / `themes` keys
  change nothing; a one-part plan gives exactly `search(q)`; the benchmark scope holds in a one-firm
  part; budget shares sum to <= T + one chunk; no chunk in two parts; `Hit.part_id` set; invalid /
  truncated planner output -> rules plan with `source = "fallback"`; prompt names no question ID
  and no `passes_if` text.
- [ ] Mock: all 30 questions (`.eval-runs/0214-mock`), refusal gap 5/5, keyed 22/22, 0 forbidden,
  no PASS -> FAIL, recall@final >= 0.654 (tier 1 >= 0.808); one-part questions identical to the
  baseline (step 3 diff); Gate 4 missed passages' stage reported.
- [ ] Real: `.eval-runs/0214-real`, 12 calls, claude-sonnet-5-5: the saved plans have a part for
  every asked part, judged from each part's text / `keyword_query` and listed in the PR:
  Q3 (Schwab's framing of the RIA custody / advisor services business, stated priorities,
  competitive pressure, where it concedes ground); Q7 (recruiting posture, payout philosophy,
  training pipeline, disclosed retention results, and MS, MER, RJF each in some part); Q12 (Schwab's
  acquisition channels and scale economics, management's claims on cost of acquisition, Edward
  Jones's cost structure); Q28 (EDJ attrition rate and definition, Merrill's attrition / retention
  disclosure, net advisor headcount change). A missing part is a finding in the PR (the issue item
  stays open: "Part of #214"). For Q7, Q15, Q25 each named Gate 4 passage is reported as cited /
  retrieved, not cited / in pool / not in pool, with its part, against the #213 pick.
- [ ] At most 2 LLM calls per question, logged: test with counting fakes (planner 1 + answer 1;
  0 + 0 on mock; 0 planner calls when code skips search); `query_log.filters->'llm_calls'`
  (verify-cee); per-question `llm_calls` in the real report, all <= 2.
- [ ] ADR-020 written in `docs/DECISIONS.md` (the reviewer escalates the PR to the TL for the
  merge); `pytest -q` passes; `python scripts\verify_cee.py run` all features PASS with the
  ask-progress recipe and driver updated for the plan stage.

## Progress log
- 2026-11-19 00:32 - plan written. Branch `tl/214-planner` from `main` 43c68ed; DB
  `corpus-2026-11-17` up to date (`sync-db.ps1 -Check`).
