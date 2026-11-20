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
class Aspect:            # what the question asks (planner v3 or the rule plan)
    id: str              # a1..aM, set by code in order
    text: str            # one sentence, what is asked
    keyword_query: str | None   # search words; None = the question's own words
    metric: str | None = None   # a key of config/metric_definitions.yaml, or None
    kind: str = "fact"          # fact | comparison | recency | series
    firms: list[str] = []       # TL decision D3: the subset of firm_scope(q) the question asks this
                                #   aspect of; empty = every scoped firm (validated by code)

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
    subquestions: list[SubQuestion]      # built by code: each aspect x its firm set
    source / provider / model / version / corrections / error / raw / calls   # as today
    searched: list[dict]                 # per sub-question: id, entity, aspect, role, budget,
                                         #   passages, tokens, pool, chunk_ids, floor_dropped
    research_tokens: float
    competitor_floor: dict[str, float]   # aspect id -> the rank floor used across competitors
                                         #   (home-firm market questions only; read by the hook)
    @property parts -> list[Part]        # one Part per sub-question (id, text, [entity], words)
    @classmethod from_parts(parts, **kw) # test/replay constructor: one aspect per Part (below)
```
- `Part` stays as the view the answer side already reads (`llm.generate(plan=...)` prompt v4.1,
  `validate.check_parts`, `part_coverage`, `eval_run.parts_of`, verify-cee's `filters->plan->parts`),
  so the interim answer path needs no change; `Plan.parts` is derived, never stored separately.
- `Plan.from_parts(parts)` keeps the existing fixtures that build `Plan(parts=[...])` working with a
  one-line change (`tests/test_part_check.py`, `tests/test_prompt.py`, `tests/test_ask_progress.py`,
  `tests/test_eval_run.py`): each Part becomes one aspect with `firms = part.firms` and one
  sub-question per firm, ids kept as given (non-blocking note 6).
- `Plan.to_log()` adds `aspects` (with `firms`), `subquestions` (id, entity, aspect id, role),
  `competitor_floor`, and keeps `parts`.
- `PLANNER_MAX_PARTS`, `max_parts()`, `Settings.planner_max_parts` and every `cap` argument are
  removed (ADR-020 amendment).

## Planner v3 (`PLANNER_VERSION = "plan-v3"`)
### Prompt (draft; final wording in the build, same rules)
```
You plan the document search for a question about wealth-management firms. Code searches every
aspect you list once for each of its firms (the firms are chosen by code and listed below, each
with how it was found) and applies the firm filters, the time window and every other filter; you
only list the aspects, their search words and, when the question restricts an aspect, its firms.

List the aspects literally. An aspect is one thing the question asks about. List every one, in the
order the question asks them:
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
names in an aspect's text or words.

Firms of an aspect. Leave firms empty when the question asks the aspect of every listed firm (code
then searches it for all of them). Fill firms with IDs from the list only when the question itself
asks the aspect of some of them: "how Firm X earns on client assets and how an advisor-led model
earns" asks the first of Firm X only and the second of the firms found through "an advisor-led
model". Competitors on the theme are searched for every aspect unless the question restricts it.

Same concept only (plan-v2 rule kept): search words name the asked concept ...

For each aspect give:
- id: a short label (code renumbers);
- text: what the aspect asks, in one sentence, without firm names;
- keyword_query: 5 to 25 words the documents themselves would use (filing and earnings-call
  vocabulary, synonyms, metric and disclosure names), no firm names, no dates;
- firms: firm IDs from the list when the question restricts the aspect to them, else [];
- metric: one of {metric keys} when the aspect asks for exactly that registered metric, else "";
- kind: fact (a disclosed fact or figure), series (a figure over several periods), recency (what is
  new inside the time window), comparison (judging or ranking across firms or periods).
Return the plan by calling the {tool} tool; do not answer the question.
```
- `planner_message(q)`: the question; "Firms (chosen by code; IDs to use in firms)", one line per
  scoped firm labelled by how code found it (`firm_origins(q)`, from `resolve`'s own rules):
  - `named` - the question names it (alias match);
  - `through "<phrase>"` - a peer phrase (`fts._peer_members` per phrase: "an advisor-led model" ->
    MS, EDJ, MER, RJF in Q15; "the five" -> all five in Q22); a firm both named and in a phrase is
    labelled named;
  - `competitor on the theme` - a home-firm market question's `theme_peers` (Q19).
  Then the window and themes as today; no "Most parts" line. Example (Q15): "SCHW (Charles Schwab):
  named; MS (Morgan Stanley): through \"an advisor-led model\"; EDJ ...; MER ...; RJF ...".

### Strict schema, every provider
One aspect object for all paths: every property required, `additionalProperties: false`:
`id` string, `text` string, `keyword_query` string, `firms` array of strings (no array limits on
any provider; empty = all scoped firms), `metric` string `enum: ["", <registered metric keys from
config/metric_definitions.yaml, today advisor_headcount, net_new_assets>]`, `kind` string
`enum: KINDS`. Top level `{"aspects": [aspect]}`, required, no extra properties.
- **anthropic** (`strict: true` tool `submit_plan`, #232): `aspects` with `minItems: 1`, no
  `maxItems` (Anthropic strict accepts minItems 0/1 only).
- **openai** (`response_format json_schema strict`): no array limits.
- **deepseek** (#242 strict function on `/beta`): the same as openai: every property required,
  `additionalProperties: false`, no `minItems`/`maxItems`; `metric` uses `""` for "none" instead
  of a nullable type, so no `anyOf`/`null` is needed on any path. `enum` is listed as supported in
  DeepSeek's strict-mode docs; re-checked at build (WebFetch of the function-calling page). If it is
  not, `metric` and `kind` become plain strings on that path and code validation (below) does the
  rest; this is recorded in the PR.
- **A 400 on a planner call** (the provider rejects the schema itself) is not a planner finding but
  a request bug: every planned call would fail the same way and fall back to the rule plan. In
  `RealRunner.plan`, an HTTP 400 (`BadRequestError` of the openai/anthropic SDKs, which #242's
  deepseek client also raises) stops the run with a clear error after saving the response, like
  #242's `ProviderStop` (counted as 1 call); in the app (`plan_question`) it stays the logged
  fallback as today. Expected outcome stated in the PR either way (non-blocking note 4).
- Tests run the existing strict-rule check on all three schemas (with `firms`) and
  `anthropic.transform_schema` leaves the anthropic one unchanged.
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
- **firms** (TL decision D3): each entry mapped with `_firm_id` (ID, name or alias); unknown or
  outside `firm_scope(q)` -> dropped with a note ("aspect N: firm X not in scope"); duplicates
  dropped. Empty after the drops (and the model wrote some) -> all scoped firms, with a note.
  **Home-firm market question guard:** a list equal to all named firms (`q.entities`, e.g.
  `["EDJ"]` in Q19) counts as empty, so the competitors stay (note "aspect N: named firms only on a
  home-firm market question, competitors kept"). A list naming the home firm and some competitors
  stays as written.
- **No cap, no merge, no dedupe** (rule 6): 100 aspects stay 100; two identical aspects stay two.
- A v2-shaped output (`parts`) is unusable -> rule plan.

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
- `subquestions(q, aspects)`: each aspect over its own firm set (`aspect.firms` or every scoped
  firm), firm-major order (each scoped firm in scope order, then the aspects that include it, a1..aM),
  no cap. Without restrictions this is N x M.

### Competitors as real entities vs ADR-018 peers
- Each competitor sub-question searches its own firm with its own budget (not 2 peer slots).
- It keeps ADR-018's safeguards: **on the theme only** (new `Query.on_theme_only`, a SQL `AND` of
  `on_theme_filter(q.themes)` on the firm pass; no answer-turn attachment, since an answer turn is
  fetched without the word match and may be off the theme), every other hard filter, Merrill only
  through BAC GWIM/Merrill; and the **floor across competitors**: after the competitor
  sub-questions of one aspect are searched, `fts.peer_floor` (FLOOR x 2nd-best rank across all of
  them) drops low chunks (BAC's "Top 40 Advisors Under 40" rankings, ADR-018), released from the
  exclude set and logged as `floor_dropped`; the floor value goes to `plan.competitor_floor`. A
  post-select cut keeps the loop independent of `search_fn` (hybrid ranks are its own scores, the
  cut is relative).
- After the cut, the sub-question's `searched` entry is updated (passages, tokens, chunk_ids after
  the floor; `floor_dropped` ids). A competitor sub-question the floor empties gets
  `floor_emptied: true`; `validate._part_pools` and `llm.build_user_message` read its pool as 0, so
  the answer prompt says no evidence was found for it (not `KEPT_ELSEWHERE`) and `check_parts` words
  its gap "No evidence retrieved for" - its candidates were below the floor across competitors, the
  same reading ADR-018's coverage note gives a peer with nothing on the theme (non-blocking note 3).
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
- Base terms = `aspect.keyword_query or fts.keyword_terms(q)[0]` (a rule-plan or fallback aspect
  has words None = the question's own words; #246's mock map runs on the rule plan, so the
  re-search must keep them; non-blocking note 1).
- Searches `subquestion_query(q, sq)` with `terms = base terms + " " + extra_words`, after
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
  advisor_headcount), else None, `firms = []` (all scoped firms; the rule plan never restricts).
  Sub-questions = firm_scope(q) x [a1]: deterministic, so a
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
- **#245 makes 0 real answer calls** (TL decision D5). The interim single answer call is temporary
  until #246 (map) and #247 (reduce) replace it.
- **Risk (named):** retrieval has no cap, so the interim answer input grows with the decomposition:
  a five-firm, three-aspect question at 40k per sub-question can reach ~600k input tokens before
  the pools run out, above the answer models' context windows (DeepSeek's and Claude's limits are
  looked up in their docs at build and recorded in the spec). Without a guard, the interim app with
  a real provider would fail on exactly the multi-firm questions this work targets (Q11, Q22-Q25);
  the mock never shows it.
- **Temporary input guard (interim answer call only; removed when #247 wires the reduce step):**
  - Setting `ANSWER_INPUT_MAX_TOKENS` (env; `.env.example` and `specs/answer-citations.md`).
    Default per provider: the documented context window minus the provider's answer output cap
    (`llm.answer_max_tokens`) minus the measured prompt overhead (system prompt + the user
    message's fixed text, characters / 4, measured at build), rounded down to 1k. Mock: no default
    limit (unset = no guard), so the mock eval and verify are unchanged unless a test sets it.
  - In `ask.answer_for`, before the model call: estimated input = overhead + the passages' tokens
    (characters / 4, as everywhere). Over the limit -> `fit_input(hits, plan, limit)` (new, in
    `validate.py`) keeps research passages first, then passages round-robin over the sub-questions
    in plan order, each sub-question's best rank first. **Stop rule (greedy, stated in the spec):**
    a passage that would pass the limit is skipped and the round-robin continues with the next
    sub-question, so one long passage does not end the trim while shorter ones still fit; the trim
    ends when a full round adds nothing. The kept list keeps the original order.
  - Never silent: a trace line ("Input over the model's limit: kept N of M passages, ~X of ~Y
    tokens"), a code-built sentence appended to the coverage note ("The answer read N of M retrieved
    passages: the input was trimmed to the model's limit; the passages left out are listed in the
    log."), and `input_guard` {limit, before, after, dropped chunk ids} in `query_log.filters` and in
    the eval record.
  - The model and the citation checks see the trimmed list (a citation must point at a passage the
    model was given); `query_log.chunk_ids`, retrieval recall and the eval status are measured on
    the full retrieved list, before the guard.
  - **Which list the post-answer steps read** (stated in `specs/answer-citations.md`):
    `check_citations`, `check_parts` and the number check read the trimmed list (what the model
    saw). `insert_caveats`, `fill_suggested_sources` and the per-firm lines of `coverage_note` read
    the **trimmed** list too, so a caveat or a "passages from" line never refers to evidence the
    answer did not read; the guard's coverage-note sentence names the trim and points to the log
    for the left-out passages.
  - **Answer cache key** (`scripts/eval_run.py`): when the guard trims, the key also gets
    `{"input_guard": [limit, kept chunk ids]}`, so an output made under one limit is never reused
    under another; an untrimmed call keeps today's key.
  - Tests (mock, 0 calls): no trim under the limit (identical hits, no note, `input_guard` absent);
    over it: research kept, round-robin order, trace line, note, log entry, citation of a dropped
    chunk flagged as unmatched.
- The real planner check reports each real plan's interim input tokens (0-call search) against the
  DeepSeek default limit (blocking 2d).
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
  per-sub-question budget / tokens / pool, and `input_guard` when a real answer was trimmed.
- `prompt_size` (non-blocking note 7): in planned runs `budget_tokens` is the sum of the
  sub-question budgets (`SUBQUESTION_TOKENS` x sub-questions; research and nothing else outside it)
  and `fill` = sub-question tokens / that sum; passage-mode and `--k` runs keep today's fields.
- New flag `--plan-only` (with `--real`): planner calls only, then the 0-call search of each plan;
  no answer call; `--max-calls` counts planner calls.

## Files to change
- `src/cee/retrieve/planner.py` - data model, prompt v3, schemas, validate_plan, firm_scope,
  subquestions, rules_plan, search_subquestions, corrective_search, describe_plan; cap removed.
- `src/cee/retrieve/fts.py` - `Query.on_theme_only` (firm pass AND on-theme, no answer turns),
  `search(text=...)` ignored kwarg. Nothing else.
- `src/cee/config.py` - `subquestion_tokens` (env `SUBQUESTION_TOKENS`); `planner_max_parts` removed.
- `src/cee/config.py` also - `answer_input_max_tokens` (env `ANSWER_INPUT_MAX_TOKENS`).
- `src/cee/answer/llm.py` - `DEEPSEEK_PLANNER_MAX_TOKENS[False]` 2000 -> 8000 (after the rebase;
  #242's constant); provider context-window constants and `answer_input_limit(provider)`;
  `build_user_message` reads a floor-emptied sub-question's pool as 0.
- `src/cee/answer/validate.py` - `fit_input` (interim guard), `_part_pools` reads `floor_emptied`.
- `src/cee/ask.py` - `search_subquestions`, the interim input guard in `answer_for`, `Result` /
  `log_filters` `input_guard`, trace text, docstrings.
- `scripts/eval_run.py` - cache keys, meta, records, `prompt_size` in planned runs, `--plan-only`,
  a 400 on a planner call stops the run.
- `scripts/verify_cee.py`, `.claude/skills/verify-cee/features/ask-progress.md`, `ask-answer.md` -
  the plan / search lines and part-gap expectations.
- `tests/test_planner.py`, `tests/test_retrieval_parts.py` (renamed `test_subquestions.py`),
  `tests/test_retrieval_themes.py` (on_theme_only), `tests/test_eval_run.py`,
  `tests/test_ask_progress.py`, `tests/test_ask_page_trace.py`, `tests/test_part_check.py` and
  `tests/test_prompt.py` (fixtures move to `Plan.from_parts`), new `tests/test_input_guard.py`,
  deepseek planner tests from #242.
- `.env.example` - `SUBQUESTION_TOKENS`, `ANSWER_INPUT_MAX_TOKENS` (temporary), `PLANNER_MAX_PARTS`
  removed.
- `specs/retrieval.md` (sketch rewritten for #245), `specs/ui.md` (trace lines incl. the guard line,
  call count wording), `specs/answer-citations.md` (the interim input guard, marked temporary until
  #247), `docs/ARCHITECTURE.md` (planner box), `docs/RUN.md` (planner-only real check commands,
  Windows and Mac blocks), `docs/DECISIONS.md`:
  - ADR-019 amendment: the SUBQUESTION_TOKENS value and grid table;
  - ADR-020 amendment: plan-v3 aspects with the **optional per-aspect firm subset** (`firms`,
    validated by code as a subset of the code-scoped firms, empty = all; the home-firm guard), the
    cap removed, the interim input guard;
  - ADR-018 amendment (non-blocking note 5): in planned mode competitor sub-questions replace
    `peer_pass`'s two slots per peer; on the theme only, the floor across competitors and Merrill via
    GWIM/Merrill are kept; `peer_pass` stays for unplanned search.
- No new OS-specific script (eval_run.py is Python); every command below has a Windows and a Mac line.

## Steps
0. Wait for #242 to merge; `git -C D:\ALLPROJECTS\EDJ\wt-245 fetch origin; git rebase origin/main`.
1. fts: `on_theme_only`, `text` kwarg; tests.
2. planner: data model, firm_scope, subquestions, rules_plan; tests (no DB).
3. planner v3: prompt, three schemas (DeepSeek enum re-check), validate_plan, output caps; tests
   with fake clients for anthropic, openai, deepseek (0 real calls).
4. search_subquestions with search_fn / research_fn, competitor floor; corrective_search; DB tests.
5. ask() (incl. the interim input guard), eval_run (keys, meta, prompt_size, `--plan-only`, 400
   stop), verify driver and recipes; tests.
6. Mock grid for SUBQUESTION_TOKENS, pick by the rule above; set the default.
7. Mock 35-question run at the pick; explain every PASS -> FAIL and every changed question.
8. pytest (full), verify-cee, docs/specs/ADR text.
9. Real planner check (last, after every mock check passes).
10. /finish-task, PR, `gh pr checks` green.

## Tests (0 real calls; `tests/conftest.py` stubs every client)
- Schemas: all three pass the strict-rule check, `firms` included (array of strings, required, no
  array limits); anthropic unchanged by `transform_schema`; `metric` enum = registered keys + "";
  no `minItems` on openai/deepseek.
- Per-aspect firms (D3), fake planner outputs through `validate_plan` + `subquestions`:
  - Q12: Schwab's scale / acquisition aspects `firms: ["SCHW"]` -> SCHW sub-questions only; the
    Edward Jones cost / replicate aspect `firms: ["EDJ"]` -> EDJ only;
  - Q15: Schwab earnings `["SCHW"]` -> SCHW only; advisor-led earnings `["MS","EDJ","MER","RJF"]`
    -> those four only; planner_message labels SCHW named and the four through "an advisor-led model";
  - Q19: `firms: ["EDJ"]` on every aspect -> EDJ + MS, SCHW, MER, RJF kept (home-firm guard, note);
  - an out-of-scope firm (e.g. "Vanguard", or MS on Q12) dropped with a note; all dropped -> all
    scoped firms with a note; names and aliases mapped to IDs.
- Floor-emptied competitor sub-question: `searched` updated after the cut, `floor_emptied`, gap
  worded "No evidence retrieved for", no `KEPT_ELSEWHERE` line.
- 400 on a planner call in `RealRunner.plan` stops the run (fake client), counted once.
- `prompt_size` in a planned run reports the sum of sub-question budgets.
- corrective_search on a rule-plan aspect keeps the question's words plus the extra words.
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
- [x] Real: Q19's decomposition includes MS, SCHW, MER, RJF as competitor sub-questions; Q24 and
      Q11 list every asked aspect for all five firms; all nine plans quoted in the PR. (Q19's own
      planner output was cut at the 16000 thinking-on cap and fell back to the rule plan; the four
      competitors come from code either way; finding, not re-run.)
- [x] Real + tests: Q12's and Q15's restricted aspects are searched only for their firms (Q12:
      Schwab's acquisition aspects SCHW, Edward Jones's aspect EDJ; Q15: Schwab earnings SCHW,
      advisor-led earnings MS, EDJ, MER, RJF), and Q19 still holds the four competitors.
- [x] Interim input guard: mock tests (no trim under the limit; trim + trace + note + log over it);
      0 real answer calls in #245; each real plan's interim input tokens reported against the limit.
- [x] Every sub-question query carries the SQL entity/segment/window filters (tests).
- [x] Re-search hook keeps all SQL filters and the exclude set (tests).
- [x] Mock run at the pick: refusal 5/5 (keyed 22/22), recall@final (all and tier 1) not lower
      than `evals/baselines/corpus-2026-11-19`; every PASS -> FAIL explained (none); grid table in the PR.
- [x] pytest, verify-cee and `gh pr checks` green (pytest 761 passed, verify-cee PASS, PR #255 pytest check pass).

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
  (Q22, Q23), does not merge (Q1, Q19) and restricts an aspect to its firms only when the question
  does (Q12, Q15) needs the real planner.
- Questions: Q19, Q11, Q23, Q24, Q1, Q3, Q22, Q12, Q15; one run each; **9 calls** (planner only, no
  answer call), provider DeepSeek (`LLM_PROVIDER=deepseek`, #242's model and thinking default),
  after #242 merges. An unusable output or failed call is a finding (rule-plan fallback, counted),
  never re-run. A 400 stops the run (above); the stop and its saved response are reported, and the
  remaining calls wait for the TL. Raw outputs, stop_reason and usage saved by `RealRunner` in the
  run folder and the cache.
- Command (Windows): `D:\ALLPROJECTS\EDJ\repo\.venv\Scripts\python.exe scripts\eval_run.py --real
  --plan-only --max-calls 9 --questions Q19,Q11,Q23,Q24,Q1,Q3,Q22,Q12,Q15 --as-of 2026-11-17 --out
  D:\ALLPROJECTS\EDJ\cache\ev245\real-plan`; Mac: the same with `.venv/bin/python` and
  `../cache/ev245/real-plan`.
- Reported in the PR: each plan (aspects with firms/kind/metric, the sub-question list),
  corrections, and the 0-call search of each real plan (sub-questions, passages, tokens per
  question = the interim answer input, against the DeepSeek `ANSWER_INPUT_MAX_TOKENS` default, and
  how many passages the guard would drop).

## Design decisions (settled by the TL in the plan review, issuecomment-7029889400)
- D1 accepted: `SUBQUESTION_TOKENS` grid {12k, 20k, 40k} and the pick rule above. The grid runs the
  rule plan (one aspect per firm), so it cannot measure multi-aspect totals and may pick 40k; the
  real-plan token report is where those show (non-blocking note 9).
- D2 accepted: competitors (Q19) get a full sub-question budget each, on the theme only, floor
  across competitors after select (ADR-018's safeguards kept; its 2-slot limit dropped, ADR-018
  amendment).
- D3 **changed**: "literal" also means an aspect the question asks of one firm (or a subset) is
  searched for those firms only. `Aspect.firms` is an optional subset, validated by code against
  `firm_scope(q)`, empty = all scoped firms; the prompt fills it only when the question restricts
  the aspect; the planner message labels each firm by how code found it; on a home-firm market
  question a list equal to all named firms counts as empty. Q12, Q15 (and Q19's guard) are the
  test cases; the real check grows to 9 calls; ADR-020 amendment records it.
- D4 accepted: prompt v3 keeps plan-v2's implicit asks and "closest disclosed figure" as aspects
  while forbidding merges and caps.
- D5 **settled**: 0 real answer calls in #245; the interim single answer call is temporary; token
  totals reported (grid points and real plans); a temporary, logged `ANSWER_INPUT_MAX_TOKENS` guard
  on the interim answer call only, removed when #247 lands.
- D6 accepted: planner output caps raised to 8000 (anthropic/openai and deepseek thinking off; the
  latter is #242's constant).
- D7 accepted: `metric` as an enum with "" for none (strict-safe on all three paths), not nullable.
- D8 accepted: sub-question ids `a<j>.<ENTITY>` (`a1.all` in theme mode), firm-major order, a chunk
  kept once under its first sub-question.
- D9 accepted: `Query.theme_peers` stays on the resolved query (coverage note, caveats, eval
  forbidden check); `peer_pass` runs only without a plan.

## Review notes (non-blocking, all adopted)
1. corrective_search base terms = `aspect.keyword_query or fts.keyword_terms(q)[0]` (Re-search hook).
2. `Plan.competitor_floor` in the data model and `to_log()`.
3. Floor-emptied competitor sub-question: `searched` updated, `floor_emptied`, pool read as 0 for
   the prompt and the gap wording (Competitors section).
4. A 400 on a planner call stops `RealRunner` runs (Strict schema section); DeepSeek WebFetch
   re-check at build kept.
5. ADR-018 amendment added to the DECISIONS.md edits.
6. `Plan.from_parts` test constructor; `test_part_check.py`, `test_prompt.py` and the fixtures in
   `test_ask_progress.py` / `test_eval_run.py` in the file list.
7. `prompt_size` reports the sum of sub-question budgets in planned runs.
8. Hybrid sync: the next main -> exp/hybrid sync replaces `hybrid.search_parts` (hash pin) with the
   `search_fn` seam and honours `on_theme_only`; noted in the PR, no issue (out of scope).
9. The grid cannot measure multi-aspect budgets; the real-plan report covers it (D1).
10. The mock cites only the first sub-question's top 3, so up to N x M - 1 code part gaps on the
    mock in verify-cee: expected, recorded in the recipes.

## Progress log
- 2026-11-19 21:44 - plan written (worktree `D:\ALLPROJECTS\EDJ\wt-245`, branch
  `tl/245-decompose` from `origin/main` 0c161ac; DB up to date `corpus-2026-11-19`; resolve() on
  all 35 questions: only Q19 has theme_peers). Build waits for #242 to merge and a rebase.
- 2026-11-19 - plan review 1: PLAN CHANGES REQUESTED (issuecomment-7029889400). Revised: blocking 1
  (D3 per-aspect `firms` subset: data model, schema on all three providers, prompt rule, firm-origin
  labels in the planner message, validate_plan incl. the home-firm guard, subquestions per aspect
  firm set, Q12/Q15/Q19 tests, real check 7 -> 9 planner calls, ADR-020 amendment text); blocking 2
  (D5: risk named, 0 real answer calls, temporary logged `ANSWER_INPUT_MAX_TOKENS` guard with mock
  tests and a per-plan report); all 10 non-blocking notes adopted. #242 still not merged: build
  still waits for it and a rebase.
- 2026-11-19 - plan review 2: APPROVED at 02e8a1e (issuecomment-7029953602). Adopted its
  non-blocking notes: (1) the guard's limit and kept ids join the answer cache key when it trims;
  (2) the trimmed list feeds the citation, part, number and caveat checks, suggested sources and the
  coverage note (stated in the spec); (3) greedy stop rule: skip a passage that does not fit and
  continue, stated in the spec; (4) duplicate D6-D9 line folded into the items. Build waits for
  #242 to merge, then a rebase onto main.
- 2026-11-19 22:20 - #242 merged (739cb3c, PR #253); rebased onto origin/main eac02d1. Adapted to
  #242's code: the deepseek planner path keeps #242's `deepseek_tool_request` / `deepseek_create` /
  `deepseek_tool_call` checks and only gets the v3 schema, prompt and message; thinking on is the
  default (planner cap 16000, unchanged), thinking off 2000 -> 8000 as planned (request version
  `...-p8000`); `plan_cache_key` keeps #242's design (the constant `PLANNER_MAX_TOKENS`, now 8000,
  in the key, the deepseek cap through the request version) instead of `planner_max_tokens(provider)`
  (the reviewer called it redundant); the OpenAI planner request still sends no output cap (unchanged
  from main). Differences from the plan text: `corrective_search`'s base words for a rule-plan
  aspect are the question itself (`q.question`), which `fts` cleans exactly as `keyword_terms(q)[0]`
  is built, without adding the recency words twice; the 400 stop also covers anthropic/openai SDK
  errors (any exception with `status_code == 400`). DeepSeek strict docs re-checked
  (`guides/tool_calls`): enum supported, empty-string enum values not mentioned (the 400 stop covers it).
- 2026-11-19 22:30 - build done (890e716): pytest 761 passed. Context windows checked: DeepSeek
  deepseek-v4-pro 1M (Models & Pricing), Claude Sonnet 5.5 1M; guard default for deepseek 933,000.
- 2026-11-19 22:35 - grid (0 calls): 12000 and 20000 lose recall@final; 40000 eligible and picked
  (all 30 baseline questions UNCHANGED). Final mock at 9cae90e: same lists, 33 PASS / 2 FAIL (Q19 as
  baseline; Q33 fails on main too: research not searched without a theme). verify-cee PASS
  (open-citation / download-document UNREACHABLE: no raw files in the worktree, a precondition).
- 2026-11-19 22:54 - real planner check: 9 DeepSeek calls (thinking on), 0 answer calls, no 400, no
  ProviderStop, ~0.87 CNY off-peak. Q19 cut at max_tokens (16000 reasoning) -> rule-plan fallback
  (finding, not re-run). Q11/Q22/Q24 real plans retrieve must-not chunks (finding for #246).
  Evidence: docs/results/0245-planner-check.md.
- 2026-11-19 23:00 - PR #255 opened; gh pr checks: pytest pass.
