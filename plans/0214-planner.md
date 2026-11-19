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
  usable or the call failed, deterministic plan used). `Plan.to_log()` gives the JSON stored in `query_log` and the
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
8. The planner call itself fails (API or network error, timeout, any exception from the client):
   the same fallback (`rules_plan(q)`, `source = "fallback"`, `error` = the exception type and
   message), logged in the trace line and `query_log`, and the call still counts (it may have
   cost money). The question is still answered; only the answer stage can fail the question, as
   today.
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
- **Research and theme peers once per question, not per part** (fixed now; ADR-020). Today
  `search()` does three things after the firm pool: the tier 5 research part (entity+theme only;
  `select(research_rows, min(THEME_K, k))`, by passage count, its tokens then taken off the firm
  part), the firm part, and the theme peers (ADR-018, on top). They are factored out of `search()`
  into `fts.research_pass(q, trace)` and `fts.peer_pass(q, kept_ids, trace)`, and `search()` calls
  them exactly as today (so its output is unchanged). `search_parts` runs:
  1. `research_pass` once for the whole question (resolved query, the question's own words):
     at most THEME_K = 4 research passages per question, as ADR-019; R = their tokens;
  2. the parts, each with `search(part_q, tokens=share, exclude=kept, research=False,
     peers=False)`, sharing T - R (below);
  3. `peer_pass` once for the whole question (`q.theme_peers`, which only a home-firm-only
     question has; Q19), excluding every kept chunk, on top of the budget as today.
  Output order as today: part hits (in part order), then research, then peers; window questions
  re-sorted newest first over all of them, as today. Parts never add research passages, so a
  question has at most 4 research passages whatever its number of parts.
- `fts.search()` gets `tokens: float | None = None` (an explicit token budget; overrides
  `budget_tokens(q)`), `exclude: set[str] | None` (chunk ids already kept by earlier parts or
  the research pass, removed from the pools **and from the answer-turn map** before `select()`:
  a question turn in `exclude` is not pooled and an answer turn in `exclude` is never attached,
  so a later part never spends its share on a chunk that is already kept), and
  `research: bool = True`, `peers: bool = True` (the passes above; `search_parts` turns them off
  for parts).
- **Budget split** (fixed now; ADR-020): T = `budget_tokens(q)` of the whole question (ADR-019:
  40k, five firms 60k; unchanged caps). R = the research pass's tokens (0 outside entity+theme).
  Parts are searched in plan order; part i of n gets share_i = max(0, T - R - used) / (n - i),
  where used = estimated tokens of the hits kept by parts 1..i-1 (theme peers are never counted;
  they come after). Equal shares, and the share a part leaves unused flows to the parts after it.
  No separate minimum: the cap (4) keeps every first share >= (T - R)/4 (R is at most 4 chunks,
  so about 10k; about 15k for five firms). Each part ends at most one chunk past its share (the
  `select()` token rule) and the overshoot is taken off the next shares (a part whose share is 0
  keeps nothing), so the budgeted total (parts + research) is <= max(T, R) + the longest budgeted
  hit: the ADR-019 bound, per question (R < T at every question of the bank, so T + one chunk).
  A one-part plan gets research, then share = T - R with no exclude beyond the research ids, then
  peers: **identical to today's `search(q)`** (same research, same firm budget `T - R`, same
  order; test + step-3 diff).
- `Hit.part_id` (new field, default None) = the part that kept it (`p1`..`pn`), `research` for
  the research pass, `peers` for the theme peers; a chunk is kept once. The `PoolTrace` passed in
  collects every pass's pools (recall@pool over all of them); `search_parts` also returns, per
  part, its pool ids, share, passages and tokens, and R (eval / log).
- **Passage mode** (`TOKEN_BUDGET = None` without `--k`, or an explicit `k`): no share is defined,
  so the question is one whole-question part with today's passage rule (`search(q)` /
  `search(q, k)`), no planner call, as today.
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
  keyword_query, share, passages, tokens; research tokens R; source, provider, model, version,
  corrections, error) + `"llm_calls": {"planner": 0|1, "answer": 0|1}`. `llm_calls` counts paid
  provider calls (anthropic / openai): the mock answer and the rules plan are 0, so a mock row
  reads 0 / 0 while the trace still says "(mock, one call)" for the answer step (said in the
  `_log` docstring and ADR-020). Hits' `part_id` is in the plan's per-part chunk ids. No schema
  change.
- Settings (`cee.config`, `.env.example`): `PLANNER` = on (default) | off; `PLANNER_MAX_PARTS`
  (int, default 4, 1-5).

### Eval (`scripts/eval_run.py`)
- Without `--k` and with `TOKEN_BUDGET` set: `rules_plan` (mock) or the planner (real), then
  `search_parts`; with `--k`, or `TOKEN_BUDGET = None`: one whole-question part, passage rule,
  no planner call (as today).
- Record per question: `plan` (`to_log()`), `parts` (count), `research_passages` /
  `research_tokens` (hits with `part_id` `research`), `llm_calls` (`planner`, `answer`: paid
  provider calls the question's flow used, made now or reused from the cache; mock 0 / 0), per
  expected row the ids of the parts whose pool / final set held it (`score_key(...,
  part_pools=...)`), plus every existing field (`budget_tokens` = T).
- A planner call that raises (API / network) in a real run is saved as a failed plan in the
  plan cache (error, request meta) and reused like an invalid output: the fallback plan, never
  re-called; a retry would need a new entry in the paid-call plan.
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
  `keyword_terms()` / `doc_type_scope_sql()` read them; `research_pass()` and `peer_pass()`
  factored out of `search()` (called by it as today); `search(..., tokens=None, exclude=None,
  research=True, peers=True)` (`exclude` filters the pools and the answer-turn map); docstrings.
  Defaults leave every current call unchanged.
- `src/cee/answer/llm.py` (S2; waiver) - shared `anthropic_client()` / `openai_client()` helpers
  (the answer path calls them; behavior unchanged), module docstring (ADR-012/020 call count).
- `src/cee/ask.py` - plan stage, `search_parts`, `_log` with plan and call count, docstring.
- `src/cee/config.py`, `.env.example` - `PLANNER`, `PLANNER_MAX_PARTS`.
- `scripts/eval_run.py` (TL file; the #187 waiver covers any teammate file below as well) -
  planner in the run, record / meta fields (incl. `research_passages`), plan cache, call count.
- `scripts/verify_cee.py` - ask-progress driver: seven step lines, plan line, a two-firm question.
- `.claude/skills/verify-cee/features/ask-progress.md` - recipe: plan stage, seven steps,
  `plan-parts` sub-feature.
- Tests (#187 waiver for the S1 / S2 / U1 ones): `tests/test_planner.py` (new: validation, rules
  plan, prompt leak check, fake-client Anthropic / OpenAI calls, fallback on invalid output and on
  a client exception), `tests/test_retrieval_parts.py` (new: per-part search on a throwaway fixture
  schema in the style of `tests/test_retrieval_themes.py`), `tests/test_ask_progress.py`,
  `tests/test_ask_page_trace.py` (7 steps), `tests/test_eval_run.py` (plan cache, calls, fields).
- `docs/DECISIONS.md` - ADR-020 (Proposed); ADR-012 consequences note the feature landed.
- `specs/retrieval.md` - planner and per-part search section, ADR-020 link.
- `specs/answer-citations.md` - purpose line: one answer call after at most one planner call.
- `specs/ui.md` (U1; #187 waiver) - the trace lists the plan line; "the trace adds no extra LLM call" stays (the
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
One run each, no re-rolls. A planner output that is truncated or invalid, or a planner call that
fails, falls back to the rule plan (logged, the call counted, a finding, not re-run); an invalid answer output is `INVALID_OUTPUT` (a finding, not
re-run). No other call path. Any new call needs a new entry here first.

## Steps
1. **Plumbing, defaults = today.** `fts` fields, `research_pass` / `peer_pass` factored out, and
   `search(tokens, exclude, research, peers)` hooks (one-part identity test first); `planner.py`
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
   - multi-part questions (2-4 firms; e.g. Q7, Q8, Q9, Q12, Q28; the list from the run): every hit
     with a part id `p1`..`pn` belongs to that part's firms (entity check per hit: the firm, or BAC
     with segment GWIM/Merrill for MER; hits with `part_id` `research` / `peers` are checked by the
     existing forbidden check, not this one); no chunk twice; per-part share / passages / tokens
     tabled;
   - every question (one part or several): budgeted chars (all hits except theme peers) <= 4 x
     max(T, R) + `max_hit_chars`; research passages <= 4; research passages per question old
     (baseline: research ids from the #213 run's hits with no firm in entity+theme questions) vs
     new (`research_passages`) tabled; in one-part questions they are equal (identical lists);
   - summary vs baseline: 30 questions, refusal gap 5/5, keyed 22/22, 0 forbidden, no PASS -> FAIL,
     recall@final all rows >= 0.654 and tier 1 >= 0.808 (recall@pool reported); tokens per question
     median / max (all hits) old vs new;
   - per Gate 4 missed passage (Q7 `MS-10K-2025#153`, Q15 `SCHW-10K-2025#27`, Q17 `BAC-TR-2026Q2#21`,
     Q19 `EDJ-10K-2025#88`, Q20 `FIDELITY-III-2025#0`, `UBS-NEXTGEN-2026#119`/`#13`, Q25
     `RJF-PR-web-affiliation-options#1`, `MS-10K-2025#153`): stage (none / pool / final) and part,
     vs the baseline.
   A failed summary check is a finding: stop, report per question to the reviewer / TL (no tuning
   loop; no real calls on failing code). If any list changed and all checks pass, copy the run to
   `evals/baselines/corpus-2026-11-17/`.
4. **Docs.** ADR-020: when a question is split (every question that reaches retrieval: model plan
   with a real provider and `PLANNER=on`, rules plan otherwise); the rules plan and why five-firm
   questions stay one part there (the part cap 4 is below five firms; the issue's "one part per
   named firm" holds for 2-4 firms); part cap 4; research (at most THEME_K = 4 passages per
   question, selected once before the parts, as ADR-019) and theme peers once per question; budget
   split rule and bound (parts share T - R, budgeted total <= max(T, R) + one chunk); passage mode
   is one part; call count planner 1 + answer 1, 0 planner calls when code skips search,
   `PLANNER=off` or mock; `llm_calls` counts paid provider calls (mock 0); fallback on invalid
   output and on a failed call (the call counts); plan stored in `query_log.filters`; mock numbers;
   real results after step 6. ADR-012 consequence note, specs, ARCHITECTURE, RUN, ui spec.
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
- **Research once per question**: research keeps the whole question's words, so a planner part
  about a dimension does not pull research of its own; the research share stays as ADR-019
  (<= 4 passages). A per-part research rule is a later change if the real plans show a need.
- **One-part identity**: depends on `research_pass` using today's `min(THEME_K, k)` with
  k = `budget(q) - peer_slots(q)` and on the factored `search()` keeping its order (firm, research,
  peers); checked by a unit test and the step-3 diff before anything else.
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
  change nothing; a one-part plan gives exactly `search(q)` (same ids, same order; entity+theme and
  peer fixtures too); the benchmark scope holds in a one-firm part; no chunk in two parts,
  including an answer turn already kept by an earlier part (`exclude` filters the answer map);
  `Hit.part_id` set (`p1`..`pn`, `research`, `peers`); **research fixture**: an entity+theme
  question split into 3-4 parts with a small T so that a part's share is smaller than THEME_K
  research chunks -> research passages <= THEME_K for the whole question, none with a part id,
  and budgeted tokens (parts + research) <= max(T, R) + the longest budgeted hit; invalid /
  truncated planner output and a client exception -> rules plan with `source = "fallback"`, the
  call counted; passage mode (`TOKEN_BUDGET = None`, explicit k) -> one part, no planner call;
  prompt names no question ID and no `passes_if` text.
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
- 2026-11-19 00:50 - plan revised after review (issuecomment-7001801459, 1st blocking return):
  research (<= THEME_K = 4 per question) and theme peers run once per question, factored out of
  `search()`; parts share T - R, bound max(T, R) + one chunk; research fixture test (3-4 parts,
  share below the research tokens) and research passages old vs new in step 3; `exclude` also
  filters the answer-turn map; planner call failure falls back (call counted); `llm_calls` counts
  paid provider calls (mock 0); passage mode = one part; five-firm reason repeated for ADR-020;
  #187 waiver noted for `eval_run.py`, `specs/ui.md` and tests. Re-read: step-3 per-part entity
  check now skips research / peer hits; the bound check covers every question.
