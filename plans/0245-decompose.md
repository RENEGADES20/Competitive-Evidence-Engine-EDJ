# 0245 - Sub-question decomposition: planner v3 (aspects), firms x aspects retrieval

Issue: #245    Role: TL    Spec: specs/retrieval.md (also specs/ui.md for the trace line,
specs/answer-citations.md for what the interim answer call receives)

Binding: ADR-021 (rule 6, rule 7), the ADR-019 and ADR-020 amendments of #244, ADR-018 (firm scope),
CLAUDE.md "Paid API calls". Builds on #244 (merged, PR #251). #246 (map step) and #247 (reduce step)
build on the data model and the re-search hook defined here.

## Goal
Every question is parsed literally into the aspects it asks about (planner v3, no merge, no cap).
Code, not the model, decides the firms (the resolved firms; for a home-firm market question the
competitors as real entities, the Q19 fix) and expands firms x aspects into
`SubQuestion(entity, aspect)`. Each sub-question is searched with every SQL filter and its own
token budget (`SUBQUESTION_TOKENS`), research once, through a loop that takes `search_fn` (so
exp/hybrid can drop its copy). A corrective re-search hook (extra words + exclude set, every SQL
filter kept) is exposed for #246. Until #246/#247 land, the single answer call (prompt v4.1) gets
the evidence grouped by sub-question. Calls per question stay planner 1 + answer 1 in this issue.

## Coordination with #242 (DeepSeek provider)
- #242 (`tl/242-deepseek`, build done, not merged) edits `planner.py`'s provider branches
  (`call_planner`, `model_for`, `planner_max_tokens`, `deepseek_plan_request`) and
  `llm.DEEPSEEK_PLANNER_MAX_TOKENS` / `request_version`.
- **This branch is rebased onto `origin/main` after #242 merges and before any build step.** Only
  this plan is committed before that. If #242 is still open when this plan is approved, I report
  that and wait (no build on a pre-#242 base, so no conflict to resolve twice).
- After the rebase, the deepseek path sends the v3 schema through #242's own helper:
  `deepseek_plan_request` -> `llm.deepseek_tool_request(PLAN_TOOL, ..., plan_schema(strict=True),
  system_prompt(), planner_message(q), planner_max_tokens("deepseek"))`. Only the schema, the
  prompt and the message change; #242's checks (cut, finish_reason, no tool call, bad JSON,
  ProviderStop) stay as they are.

## Data model (`src/cee/retrieve/planner.py`)
```python
KINDS = ("fact", "comparison", "recency", "series")

@dataclass
class Aspect:            # what the question asks, firm-free (planner v3 or the rule plan)
    id: str              # a1..aM, set by code in order
    text: str            # one sentence, what is asked
    keyword_query: str | None   # search words; None = the question's own words
    metric: str | None = None   # a key of config/metric_definitions.yaml, or None
    kind: str = "fact"          # fact | comparison | recency | series

@dataclass
class SubQuestion:       # industry term: sub-question decomposition (ADR-021 rule 6)
    id: str              # "<aspect id>.<entity>", e.g. "a2.EDJ"; theme mode "a1.all"
    entity: str | None   # one covered firm id; None in theme mode (no firm named)
    aspect: Aspect
    role: str            # "named" (resolved firm) | "competitor" (home-firm market question) | "all"
    @property text -> "<firm name>: <aspect text>" (theme mode: the aspect text)

@dataclass
class Plan:
    aspects: list[Aspect]
    subquestions: list[SubQuestion]      # built by code: firm_scope(q) x aspects
    source / provider / model / version / corrections / error / raw / calls   # as today
    searched: list[dict]                 # per sub-question: id, entity, aspect, role, budget,
                                         #   passages, tokens, pool, chunk_ids, floor_dropped
    research_tokens: float
    @property parts -> list[Part]        # one Part per sub-question (id, text, [entity], words)
```
- `Part` stays as the view the answer side already reads (`llm.generate(plan=...)` prompt v4.1,
  `validate.check_parts`, `part_coverage`, `eval_run.parts_of`, verify-cee's `filters->plan->parts`),
  so the interim answer path needs no change; `Plan.parts` is derived, never stored separately.
- `Plan.to_log()` adds `aspects`, `subquestions` (id, entity, aspect id, role) and keeps `parts`.
- `PLANNER_MAX_PARTS`, `max_parts()`, `Settings.planner_max_parts` and every `cap` argument are
  removed (ADR-020 amendment).

## Planner v3 (`PLANNER_VERSION = "plan-v3"`)
### Prompt (draft; final wording in the build, same rules)
```
You plan the document search for a question about wealth-management firms. Code searches every
aspect you list once for each firm (the firms are chosen by code and given below for context) and
applies the firm filters, the time window and every other filter; you only list the aspects and
their search words.

List the aspects literally. An aspect is one thing the question asks about, the same for every
firm. List every one, in the order the question asks them:
- each item of a list, each "and" joining two asks, each metric or dimension the question names;
- what the question asks without naming it (plan-v2 examples kept: "plan for its retirement-plan
  unit" also asks how management describes the unit, its stated priorities, the competition it
  names and where it says it is losing ground; "how they handle branch staffing" asks whom they
  hire, how they pay, how they train and the results they report);
- a figure that may not be disclosed also asks for the closest disclosed figure, as its own aspect;
- a comparison the question asks to judge ("is that comparison valid", "which is most") is its own
  aspect of kind comparison.
Never merge two aspects into one, never drop one, and do not stop at any number: a question with
twelve asks has twelve aspects. Do not add an aspect the question does not ask. Write no firm
names in an aspect; code pairs every aspect with every firm.

Same concept only (plan-v2 rule kept): search words name the asked concept ...

For each aspect give:
- id: a short label (code renumbers);
- text: what the aspect asks, in one sentence, without firm names;
- keyword_query: 5 to 25 words the documents themselves would use (filing and earnings-call
  vocabulary, synonyms, metric and disclosure names), no firm names, no dates;
- metric: one of {metric keys} when the aspect asks for exactly that registered metric, else "";
- kind: fact (a disclosed fact or figure), series (a figure over several periods), recency (what is
  new inside the time window), comparison (judging or ranking across firms or periods).
Return the plan by calling the {tool} tool; do not answer the question.
```
- `planner_message(q)`: the question; "Firms (searched for every aspect by code): EDJ (Edward
  Jones)" plus, for a home-firm market question, "competitors on the theme: MS, SCHW, MER, RJF"; the
  window and themes as today; no "Most parts" line.

### Strict schema, every provider
One aspect object for all paths: every property required, `additionalProperties: false`:
`id` string, `text` string, `keyword_query` string, `metric` string `enum: ["", <registered metric
keys from config/metric_definitions.yaml, today advisor_headcount, net_new_assets>]`, `kind`
string `enum: KINDS`. Top level `{"aspects": [aspect]}`, required, no extra properties.
- **anthropic** (`strict: true` tool `submit_plan`, #232): `aspects` with `minItems: 1`, no
  `maxItems` (Anthropic strict accepts minItems 0/1 only).
- **openai** (`response_format json_schema strict`): no array limits.
- **deepseek** (#242 strict function on `/beta`): the same as openai: every property required,
  `additionalProperties: false`, no `minItems`/`maxItems`; `metric` uses `""` for "none" instead
  of a nullable type, so no `anyOf`/`null` is needed on any path. `enum` is listed as supported in
  DeepSeek's strict-mode docs; re-checked at build (WebFetch of the function-calling page). If it is
  not, `metric` and `kind` become plain strings on that path and code validation (below) does the
  rest; this is recorded in the PR.
- Tests run the existing strict-rule check on all three schemas and `anthropic.transform_schema`
  leaves the anthropic one unchanged.
- **Output caps**: v3 has no aspect cap, so the planner output can be long (100 aspects ~ 6-8k
  tokens). `PLANNER_MAX_TOKENS` 2000 -> 8000 (anthropic, openai); deepseek thinking off
  `DEEPSEEK_PLANNER_MAX_TOKENS[False]` 2000 -> 8000 (thinking on stays 16000). A cut output stays an
  unusable output (rule plan, logged, counted, never re-rolled).

### `validate_plan(raw, q) -> (aspects, notes)`
- Not a dict with a non-empty `aspects` list, or an item not a dict -> `PlannerOutputError`.
- text empty -> the question (note); keyword_query: empty -> the text (note), cut at 400 chars
  (note), `strip_neighbours` against the question (notes unchanged), emptied -> None (note).
- metric: `""`/missing -> None; not a registered key -> None + note "aspect N: unknown metric X".
- kind not in KINDS -> "fact" + note (strict prevents it; covers replays and openai fallbacks).
- ids `a1..aM` by code; the model's ids stay in `raw` only.
- **No cap, no merge, no dedupe** (rule 6): 100 aspects stay 100; two identical aspects stay two.
- There is no `firms` field: a v2-shaped output (`parts`) is unusable -> rule plan.

## Firm scope by code (`firm_scope(q) -> list[(entity | None, role)]`)
- Named: `q.entities` in resolve order (after the Ask page firm filter; Merrill once, as today;
  firms we hold no documents for are not searched, the gap path names them as today).
- Competitors: a home-firm market question = ADR-018's home-firm theme rule, i.e. `q.theme_peers`
  is non-empty (entity+theme, the home firm is the only named firm). In today's bank that is Q19
  only (checked: resolve() on all 35 questions). Its `theme_peers` (MS, SCHW, MER, RJF) become
  sub-question entities with role `competitor`. A firm filter clears `theme_peers` (as today), so
  then no competitors.
- Theme mode (no firm named, Q16-Q18, Q20): one entity `None`, role `all` (the whole corpus as
  today's theme search).
- `subquestions(q, aspects)`: firm-major order (each firm, then its aspects a1..aM), N x M, no cap.

### Competitors as real entities vs ADR-018 peers
- Each competitor sub-question searches its own firm with its own budget (not 2 peer slots).
- It keeps ADR-018's safeguards: **on the theme only** (new `Query.on_theme_only`, a SQL `AND` of
  `on_theme_filter(q.themes)` on the firm pass; no answer-turn attachment, since an answer turn is
  fetched without the word match and may be off the theme), every other hard filter, Merrill only
  through BAC GWIM/Merrill; and the **floor across competitors**: after the competitor
  sub-questions of one aspect are searched, `fts.peer_floor` (FLOOR x 2nd-best rank across all of
  them) drops low chunks (BAC's "Top 40 Advisors Under 40" rankings, ADR-018), released from the
  exclude set and logged as `floor_dropped`. A post-select cut keeps the loop independent of
  `search_fn` (hybrid ranks are its own scores, the cut is relative).
- `peer_pass` is not run in planned mode (the competitors are sub-questions); `search()` without a
  plan (passage mode, tests) keeps it unchanged. `Query.theme_peers` stays on the resolved query, so
  the coverage note, `theme_gaps`, caveats and the eval's `_peer_on_theme` forbidden check work as
  today.

## Sub-question loop (`search_subquestions`, replaces `search_parts`)
```python
def search_subquestions(q, plan, search_fn=fts.search, research_fn=fts.research_pass,
                        trace=None, part_pools=None, tokens=None) -> list[Hit]
```
- Passage mode (`fts.budget_tokens(q) is None`) or not searchable: one whole-question
  `search_fn(q)` as today (part_id `p1`; no planner call happens there anyway).
- Research once: `research_fn(q, trace=trace)` from the whole question (THEME_K passages,
  part_id `research`), **outside** the sub-question budgets.
- Each sub-question, in plan order: `search_fn(subquestion_query(q, sq), trace=sub_trace,
  tokens=budget, exclude=kept, research=False, peers=False, text=sq.text)`; budget =
  `tokens or settings().subquestion_tokens` for every sub-question (no shares, no flow-forward;
  the total is the sum, reported per question). `subquestion_query` = today's `part_query` with
  `entities=[sq.entity]` (or `[]` in theme mode), `terms=aspect.keyword_query`, the question's
  doc-type scope, `theme_peers=[]`, `on_theme_only = role == "competitor"`; window, themes, mode,
  firm filter, date range and keywords come from the question unchanged. Hits get
  `part_id = sq.id`.
- Chunks kept earlier are excluded from later pools and the answer-turn map (as today), so a chunk
  appears once, under its first sub-question.
- `fts.search` gains `text: str | None = None`, ignored (FTS ranks on words); hybrid's `search`
  already has it (embedding text). exp/hybrid later passes
  `search_fn=partial(hybrid.search, rerank=..., scorer=..., checked=True)` and
  `research_fn=partial(hybrid.research_pass, ...)` after its one `check_vectors`, and must honour
  `Query.on_theme_only` (noted in the PR for the hybrid sync; hybrid code is out of scope).
- Window questions: the whole list sorted newest first (Q26), as today.
- ADR-019 pool rule unchanged (`POOL_PER_GROUP = 30` per firm and document type), tokens as
  characters / 4, Merrill counted once.
- Dropped invariant: "a one-part plan returns exactly `search(q)`" (research now sits outside the
  sub-question budget). The tests that pinned it are rewritten to the new rule.

## `SUBQUESTION_TOKENS` (setting, env `SUBQUESTION_TOKENS`)
Chosen from a mock grid by a rule fixed here, before it runs (as ADR-019):
- Grid: 12000, 20000, 40000 (12k = today's five-firm per-firm share 60k/5; 40k = today's one-firm
  total).
- Run: mock, `corpus-2026-11-19`, `--as-of 2026-11-17`, baseline
  `evals/baselines/corpus-2026-11-19/report.json` (30 questions; Q31-Q35 are reported as NEW and
  are not in the comparison).
- Eligible: refusal gap 5/5 and keyed 22/22, 0 forbidden, no PASS -> FAIL, recall@pool and
  recall@final (all rows and tier 1) not below the baseline.
- Pick: the highest tier-1 recall@final, then all-row recall@final, ties to the smaller value.
- If no point is eligible: stop and report to the TL with the table (no value is picked by me).
- Reported per point: tier-1/all recall@pool/@final, PASS/FAIL, tokens per question (median, max,
  total) and sub-questions per question.

## Re-search hook (for #246, CRAG)
```python
def corrective_search(q, plan, sq_id, extra_words: str, exclude: set[str],
                      search_fn=fts.search, tokens=None) -> list[Hit]
```
- Searches `subquestion_query(q, sq)` with `terms = aspect words + " " + extra_words`, after
  `strip_neighbours(..., q.question)` (the guard also covers widened words), `exclude` = the given
  set (the caller passes every chunk already used), budget `tokens or SUBQUESTION_TOKENS`,
  `research=False, peers=False`. Competitor sub-questions keep `on_theme_only` and the same
  competitor floor the loop used for that aspect (the loop stores each aspect's floor value in
  `plan.competitor_floor[aspect_id]`; the hook drops hits below it).
- Every SQL filter is kept (entity/segment, window, date range, keywords, doc-type scope).
  "Adjacent periods" (ADR-021 rule 6) enter only as words (e.g. "fourth quarter 2025"); the hook
  never widens the SQL window.
- Hits carry `part_id = sq.id`. One call = one search; "once per not_found sub-question" is #246's
  rule, not enforced here. 0 model calls.

## Rule plan and mock
- `rules_plan(q)`: one aspect `a1` = the whole question (words None = the question's own words),
  `kind = "recency"` when the question has a window else `"fact"`, `metric` = the registered key
  whose words (underscores as spaces) the question contains (Q22 net_new_assets, Q11/Q23
  advisor_headcount), else None. Sub-questions = firm_scope(q) x [a1]: deterministic, so a
  five-firm question is now 5 sub-questions (was 1 part), Q19 is 5 (EDJ + 4 competitors).
- Used for the mock provider, `PLANNER=off`, an unsearchable question and every fallback.
- Passage mode and unsearchable questions are unchanged (one whole-question search / no search).
- The mock answer is unchanged (cites its top passages; part gaps per sub-question as today).

## Effect on `ask()` and the answer turn until #246 / #247
- `ask()` runs resolve -> plan (0 or 1 planner call) -> `search_subquestions` -> one answer call
  (prompt v4.1, unchanged) -> checks -> log. Calls stay planner 1 + answer 1 in this issue.
- The answer call receives every hit, grouped by sub-question through `Plan.parts` (each part: id
  `a2.EDJ`, text "Edward Jones: <aspect>", firms [EDJ]); research passages as today.
  `check_parts` adds a `part_gap` per sub-question with no cited claim or gap (a five-firm,
  three-aspect question can show up to 15 code gaps on the mock: expected, recorded in verify).
- The input grows with the decomposition and has no cap (ADR-021 quality first). The real planner
  check below reports the retrieved tokens of every real plan (search only, 0 extra calls), so the
  TL sees the interim answer input before any real answer run; a call above the model's context
  fails as an error (logged), never truncated by code.
- Trace: plan line "Planning the search (rules, no model call): 1 aspect x 2 firms = 2
  sub-questions: a1.MS; a1.RJF"; search line "... in 2 sub-questions". `describe_plan` and
  `plan_text` updated; verify-cee driver and recipes updated in the same PR.

## Cache keys (`scripts/eval_run.py`)
- `plan_cache_key`: drops `max_parts`; keeps question, `PLANNER_VERSION` (plan-v3, so no v2 output
  is ever reused), snapshot, provider, model, the planner output cap for the provider
  (`planner_max_tokens(provider)`), the resolved query (includes `theme_peers`), the request version
  (#232/#242); adds the sorted registered metric keys (they are in the schema's enum).
- Answer `cache_key`: unchanged code; its `plan_parts` are now the sub-questions, so every key
  changes with the decomposition (no v2-part answer is reused).
- Run meta: `subquestion_tokens` replaces `max_parts`; records gain `aspects`, `subquestions`,
  per-sub-question budget / tokens / pool.
- New flag `--plan-only` (with `--real`): planner calls only, then the 0-call search of each plan;
  no answer call; `--max-calls` counts planner calls.

## Files to change
- `src/cee/retrieve/planner.py` - data model, prompt v3, schemas, validate_plan, firm_scope,
  subquestions, rules_plan, search_subquestions, corrective_search, describe_plan; cap removed.
- `src/cee/retrieve/fts.py` - `Query.on_theme_only` (firm pass AND on-theme, no answer turns),
  `search(text=...)` ignored kwarg. Nothing else.
- `src/cee/config.py` - `subquestion_tokens` (env `SUBQUESTION_TOKENS`); `planner_max_parts` removed.
- `src/cee/answer/llm.py` - `DEEPSEEK_PLANNER_MAX_TOKENS[False]` 2000 -> 8000 (after the rebase;
  #242's constant).
- `src/cee/ask.py` - `search_subquestions`, trace text, docstrings.
- `scripts/eval_run.py` - cache keys, meta, records, `--plan-only`.
- `scripts/verify_cee.py`, `.claude/skills/verify-cee/features/ask-progress.md`, `ask-answer.md` -
  the plan / search lines and part-gap expectations.
- `tests/test_planner.py`, `tests/test_retrieval_parts.py` (renamed `test_subquestions.py`),
  `tests/test_retrieval_themes.py` (on_theme_only), `tests/test_eval_run.py`,
  `tests/test_ask_progress.py`, `tests/test_ask_page_trace.py`, deepseek planner tests from #242.
- `.env.example` - `SUBQUESTION_TOKENS`, `PLANNER_MAX_PARTS` removed.
- `specs/retrieval.md` (sketch rewritten for #245), `specs/ui.md` (trace line, call count wording),
  `docs/ARCHITECTURE.md` (planner box), `docs/RUN.md` (planner-only real check commands, Windows and
  Mac blocks), `docs/DECISIONS.md` (ADR-019 / ADR-020 amendments: SUBQUESTION_TOKENS value and grid,
  "built" marks).
- No new OS-specific script (eval_run.py is Python); every command below has a Windows and a Mac line.

## Steps
0. Wait for #242 to merge; `git -C D:\ALLPROJECTS\EDJ\wt-245 fetch origin; git rebase origin/main`.
1. fts: `on_theme_only`, `text` kwarg; tests.
2. planner: data model, firm_scope, subquestions, rules_plan; tests (no DB).
3. planner v3: prompt, three schemas (DeepSeek enum re-check), validate_plan, output caps; tests
   with fake clients for anthropic, openai, deepseek (0 real calls).
4. search_subquestions with search_fn / research_fn, competitor floor; corrective_search; DB tests.
5. ask(), eval_run (keys, meta, `--plan-only`), verify driver and recipes; tests.
6. Mock grid for SUBQUESTION_TOKENS, pick by the rule above; set the default.
7. Mock 35-question run at the pick; explain every PASS -> FAIL and every changed question.
8. pytest (full), verify-cee, docs/specs/ADR text.
9. Real planner check (last, after every mock check passes).
10. /finish-task, PR, `gh pr checks` green.

## Tests (0 real calls; `tests/conftest.py` stubs every client)
- Schemas: all three pass the strict-rule check; anthropic unchanged by `transform_schema`;
  `metric` enum = registered keys + ""; no `minItems` on openai/deepseek.
- validate_plan: 100 aspects -> 100 (no cap), duplicates kept, ids a1..aM, unknown metric / kind
  corrected with notes, neighbour phrase dropped, empty words -> text, v2-shaped output unusable.
- firm_scope / subquestions: Q7 3 named; Q22 5 x M; Q19 EDJ named + MS, SCHW, MER, RJF competitor;
  firm filter -> no competitors; theme mode -> one `None` entity; unmapped firm not searched;
  8 firms x 100 aspects = 800 sub-questions with a patched entity config (no cap).
- rules_plan: deterministic, kind recency with a window, metric detection, 5 sub-questions for Q22.
- Every sub-question query carries the SQL entity/segment/window/date-range/keywords/doc-type
  filters (captured `search_fn` + a DB test: MER sub-question returns no BAC chunk outside
  GWIM/Merrill; benchmark tier-4 exclusion kept in a one-firm sub-question; window kept).
- Budget: every sub-question gets SUBQUESTION_TOKENS; research_fn called once; earlier chunks
  excluded; `search_fn` injection used for every sub-question and `text` passed.
- Competitors: on-theme only (no off-theme chunk, no answer turn), floor across competitors drops
  the low firm's chunks, Merrill only via BAC GWIM/Merrill.
- corrective_search: keeps every filter, appends and neighbour-strips the extra words, never
  returns an excluded chunk, keeps on_theme_only for competitors.
- eval_run: plan key changes with version / metric keys and no longer has max_parts;
  `--plan-only` makes 0 answer calls and counts planner calls against `--max-calls`.
- ask trace lines; `test_no_paid_calls` still green.

## Acceptance
- [ ] Real: Q19's decomposition includes MS, SCHW, MER, RJF as competitor sub-questions; Q24 and
      Q11 list every asked aspect for all five firms; all seven plans quoted in the PR.
- [ ] Every sub-question query carries the SQL entity/segment/window filters (tests).
- [ ] Re-search hook keeps all SQL filters and the exclude set (tests).
- [ ] Mock run at the pick: refusal 5/5 (keyed 22/22), recall@final (all and tier 1) not lower
      than `evals/baselines/corpus-2026-11-19`; every PASS -> FAIL explained; grid table in the PR.
- [ ] pytest, verify-cee and `gh pr checks` green.

## Mock checks (commands)
Windows (from `D:\ALLPROJECTS\EDJ\wt-245`, `$env:PYTHONPATH="D:\ALLPROJECTS\EDJ\wt-245\src"`):
```
$env:SUBQUESTION_TOKENS="12000"; D:\ALLPROJECTS\EDJ\repo\.venv\Scripts\python.exe scripts\eval_run.py --as-of 2026-11-17 --baseline evals\baselines\corpus-2026-11-19\report.json --out D:\ALLPROJECTS\EDJ\cache\ev245\grid-12000
(same for 20000, 40000)
```
Mac: `PYTHONPATH=$PWD/src SUBQUESTION_TOKENS=12000 .venv/bin/python scripts/eval_run.py --as-of
2026-11-17 --baseline evals/baselines/corpus-2026-11-19/report.json --out
../cache/ev245/grid-12000` (same for 20000, 40000).
`LLM_PROVIDER=mock` is forced for these runs (no `--real`, 0 calls).

## Real check (planner calls only; last)
- Why the mock cannot show it: the rule plan has one aspect by construction; whether plan-v3 lists
  every asked aspect literally (Q11, Q24), keeps the implicit asks (Q3), the series/recency kinds
  (Q22, Q23) and does not merge (Q1, Q19) needs the real planner.
- Questions: Q19, Q11, Q23, Q24, Q1, Q3, Q22; one run each; **7 calls** (planner only, no answer
  call), provider DeepSeek (`LLM_PROVIDER=deepseek`, #242's model and thinking default), after #242
  merges. An unusable output or failed call is a finding (rule-plan fallback, counted), never
  re-run. Raw outputs, stop_reason and usage saved by `RealRunner` in the run folder and the cache.
- Command (Windows): `D:\ALLPROJECTS\EDJ\repo\.venv\Scripts\python.exe scripts\eval_run.py --real
  --plan-only --max-calls 7 --questions Q19,Q11,Q23,Q24,Q1,Q3,Q22 --as-of 2026-11-17 --out
  D:\ALLPROJECTS\EDJ\cache\ev245\real-plan`; Mac: the same with `.venv/bin/python` and
  `../cache/ev245/real-plan`.
- Reported in the PR: each plan (aspects with kind/metric, the sub-question list), corrections,
  and the 0-call search of each real plan (sub-questions, passages, tokens per question: the
  interim answer input).

## Open design decisions (for the reviewer / TL)
- D1 `SUBQUESTION_TOKENS` grid {12k, 20k, 40k} and the pick rule above (quality first: highest
  tier-1 recall@final). 40k makes a five-firm, three-aspect interim answer input up to ~600k
  tokens before pool exhaustion.
- D2 Competitors (Q19): full sub-question budget each, on the theme only, floor across competitors
  applied after select (ADR-018's safeguards kept; its 2-slot limit dropped).
- D3 Full N x M product even when an aspect names one firm (Q12 "how could Edward Jones
  replicate", Q15 "how Schwab earns"): rule 6 literal; no per-aspect firm hint from the model.
- D4 Prompt v3 keeps plan-v2's implicit asks and "closest disclosed figure" as aspects (needed for
  Q3 and the gap_with_adjacent questions) while forbidding merges and caps.
- D5 Interim answer input has no cap; real-plan token totals are reported before any real answer
  run.
- D6 Planner output caps raised to 8000 (anthropic/openai and deepseek thinking off; the latter is
  #242's constant).
- D7 `metric` as an enum with "" for none (strict-safe on all three paths) instead of nullable.
- D8 Sub-question ids `a<j>.<ENTITY>` (`a1.all` in theme mode), firm-major order, a chunk kept once
  under its first sub-question.
- D9 `Query.theme_peers` stays on the resolved query (coverage note, caveats, eval forbidden
  check); `peer_pass` runs only without a plan.

## Progress log
- 2026-11-19 21:44 - plan written (worktree `D:\ALLPROJECTS\EDJ\wt-245`, branch
  `tl/245-decompose` from `origin/main` 0c161ac; DB up to date `corpus-2026-11-19`; resolve() on
  all 35 questions: only Q19 has theme_peers). Build waits for #242 to merge and a rebase.
