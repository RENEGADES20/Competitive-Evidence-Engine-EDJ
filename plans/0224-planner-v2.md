# 0224 - Planner prompt v2: a part for every asked part, same-concept search words

Issue: #224    Role: TL    Spec: specs/retrieval.md (S1; owner review waived, TL decision
2026-11-17, #187). ADR-020 amended (the reviewer escalates the PR to the TL for the merge).

## Goal
The question planner (ADR-020) gets prompt v2 (`PLANNER_VERSION = "plan-v2"`, so every planner
cache key changes): every asked part of a question gets its own part, or its own search words inside
a part, within the 4-part cap, and search words stay on the asked concept. A small code guard
removes configured neighbour-metric phrases from a part's search words when the question does not
name them. Tests can no longer reach a paid API (conftest removes the API keys). The rule plan, the
mock and the one-part identity are unchanged. FTS only, `main`; no new model, no new dependency.

## Facts (2026-11-19, read only)
- Base: `main` 42a96f7 (#214 merged in PR #223 at 9358af5, plus the PROGRESS log commit). DB `cee`
  = `corpus-2026-11-17` (`sync-db.ps1 -Check`: up to date).
- Mock baseline = `evals/baselines/corpus-2026-11-17/report.json` (the #214 mock run, copied in
  #223): 29 PASS / 1 FAIL (Q19), refusal gap 5/5, keyed 22/22, 0 forbidden, recall@pool 0.814 /
  recall@final 0.654, tier 1 0.903 / 0.808, tokens median 28,311 / max 60,322.
- The planner's words reach SQL through `fts.keyword_terms()`: the words are OR'ed lexemes
  (`plainto_tsquery` with `&` -> `|`), synonym values are phrases. So one shared word is enough for
  a chunk to be a candidate; a planner phrase is not searched as a phrase.
- `eval_run.plan_cache_key` hashes `PLANNER_VERSION`; `tests/test_eval_run.py` asserts the literal
  `"plan-v1"` twice (lines 682, 751).
- `tests/conftest.py` sets `LLM_PROVIDER=mock` only. `cee.config` calls `load_dotenv(.env)` at
  import, so a developer's API keys are in `os.environ` during tests. Every real client in `src/`
  is built by `cee.answer.llm.anthropic_client()` / `openai_client()` (callers: `llm._anthropic`,
  `llm._openai`, `planner.call_planner`; every test passes a fake client). The SDKs find
  credentials beyond the API-key variables: Anthropic 1.9.0 `default_credentials()`
  (`anthropic/lib/credentials/_chain.py`) goes on to `ANTHROPIC_AUTH_TOKEN`, an explicit profile
  (`ANTHROPIC_PROFILE` / `ANTHROPIC_CONFIG_DIR` / the `active_config` pointer), workload identity
  (`ANTHROPIC_FEDERATION_RULE_ID` + `ANTHROPIC_ORGANIZATION_ID` + `ANTHROPIC_IDENTITY_TOKEN[_FILE]`)
  and the on-disk default profile (`configs/default.json`), and a profile can carry its own base
  URL; OpenAI also reads `OPENAI_ADMIN_KEY`. So removing key variables alone does not stop a paid
  call on a machine with a profile (it only held here because this machine has none).
- Transport (checked in `.venv`, 2026-11-19): anthropic 1.9.0 and openai 3.22.1 send through
  **`httpx2`** 2.13.1: their client wrappers (`SyncHttpxClientWrapper` -> `_DefaultHttpxClient` ->
  `httpx2.Client`; async: `AsyncHttpxClientWrapper` -> `_DefaultAsyncHttpxClient` ->
  `httpx2.AsyncClient`) define no `send` of their own, so every request goes through
  `httpx2.Client.send` / `httpx2.AsyncClient.send`. `httpx2.Client` is not a subclass of
  `httpx.Client` (httpx 0.28.1 is installed too), so patching `httpx.Client.send` sees nothing.
- Probe (`D:\ALLPROJECTS\EDJ\cache\ev224\sdk_profile_probe.py`, output `sdk_profile_probe.txt`;
  run with `python -I`, every `ANTHROPIC_*` / `OPENAI_*` variable removed, `httpx2.Client.send`
  patched to record and raise `httpx2.ConnectError`, so nothing left the machine):
  - `ANTHROPIC_CONFIG_DIR` = an empty folder: `anthropic.Anthropic()` raises `CredentialsError`
    "Config file not found ... configs/default.json" at construction; 0 requests reach `send`.
  - `ANTHROPIC_CONFIG_DIR` = a folder with `configs/default.json`
    `{"authentication": {"type": "user_oauth"}, "base_url": "http://127.0.0.1:9"}` and
    `credentials/default.json` `{"type": "oauth_token", "access_token": "dummy-token",
    "expires_at": <now + 1 day>}`: `Anthropic(max_retries=0).messages.create(...)` sends exactly 1
    request to `http://127.0.0.1:9/v1/messages`, reaching `send` with `auth` = the SDK's
    `AccessTokenAuth` (the profile's token), then `APIConnectionError`. Same with no `base_url` in
    the profile and `ANTHROPIC_BASE_URL=http://127.0.0.1:9`. (The SDK allows plain http only for
    localhost / 127.0.0.1 / [::1].)
  - `openai.OpenAI()` with no key: `OpenAIError` at construction.

### What each #214 planner output missed (`.eval-runs/0214-real/raw/*-plan-*.json`, plan-v1)
| Q | Parts (v1) | Missed |
|---|---|---|
| Q3 | 1: "strategy for its RIA custody business"; words "Advisor Services independent registered investment advisors custody strategy RIA clients platform growth technology service model" | No part and no words for the competitive pressure management acknowledges or where it concedes ground; stated priorities only as "growth". Coverage 1.0 -> 0.667 (lost `SCHW:10-K#Advisor Services`). |
| Q7 | 4: one per firm on "recruiting and retention" (MS, MER, RJF) + p4 "competitive pressure" across all three | Payout philosophy only as compensation words ("deferred compensation", "recruiting packages", "compensation plan changes"); training pipeline only in Merrill's part ("training program"); p4 spends a part on an ask the question does not make (pressure) while two dimensions miss words for two firms. Coverage 0.889 -> 0.778 (MS and RJF trade press). All four parts used their full ~9.7k share. |
| Q12 | 2: p1 Schwab scale / acquisition channels / "low acquisition cost"; p2 Edward Jones acquisition model, costs, constraints | Nothing missed. Oddity: p1 carries two keys outside the schema (`keyword_query_note`, `keyword_query_x`, empty); code ignores them. |
| Q15 | 3: Schwab earnings on assets; advisor-led firms' earnings; drivers of the difference | Nothing missed (not re-run here). |
| Q25 | 4: MS, MER, EDJ, then p4 SCHW + RJF | p4's words "advisor compensation **payout ratio** affiliation transition assistance compensation and benefits expense salary bonus commissions independent advisors employee advisors". Checked on the DB: `SCHW-DECK-2026Q3#47` ("Common dividend payout range ... capital ratios") matches only the lexemes `payout` and `ratio`; `SCHW-DECK-2026Q1#44` only `payout`; neither contains compensation, benefit or expense. So the neighbour metric is **"payout ratio"** (the dividend payout ratio, already a `must_not_return` reason for RJF-10K-2025#652), not "compensation and benefits expense" as the issue says (10-K compensation expense is Q25's own expected evidence). Second cause: p2 and p3 left 6.7k + 11.9k of their shares unused, which flowed forward, so p4 had a 30.2k share (twice the equal share) and kept 111 passages, deep into low-rank matches. |
| Q28 | 2: p1 EDJ attrition / turnover / "net change in financial advisor count"; p2 Merrill attrition / retention / "advisor headcount departures" | Nothing missed (the adjacent net headcount change is in p1's words). |

### The issue's suggested guard, measured on the six v1 outputs
"A part's search words may not add a `metric_phrases` or synonym-key metric the question does not
name" fires on 14 of the 16 parts (synonym keys / metric phrases in the words, not in the question:
Q7 p1-p2 headcount, attrition, advisor headcount; Q7 p4 attrition; Q12 net new assets, advisor,
recruit; Q15 p2 net new assets; Q25 p1 recruit, p2 retention, pay, p3 pay, p4 independent advisor;
Q28 p1 retention, p2 headcount, retention, advisor headcount; Q3 advisor, technology) and **does not
fire on "payout ratio"** (not a key, not a metric phrase). It would strip Q7's retention words and
Q28's adjacent headcount words (Q28's `passes_if` asks for that adjacent figure) and still let the
Q25 deck chunks in. So the guard below uses an explicit list of neighbour phrases instead.

## Design

### Prompt v2 (`planner.py`: `PLANNER_PROMPT`, `PLANNER_VERSION = "plan-v2"`)
Schema, tool, `max_tokens` 2000, user message and validation steps 1-8 of ADR-020 unchanged. The
prompt keeps v1's intro and output fields and replaces the split rules with two rules. Draft (final
wording may tighten; it must pass the leak test below):

> **List the asks first.** Before writing parts, list for yourself everything the question asks for:
> - each named firm or group of firms whose evidence must be found separately;
> - each "and" joining two asks, each item of a list, each metric or dimension it names;
> - what the question asks without naming it. Example: "What is Firm X's plan for its retirement-plan
>   unit?" also asks how management describes the unit, the priorities it states, the competition it
>   names, and where it says it is losing ground or pulling back. Example: "How do Firm X and Firm Y
>   each handle branch staffing?" asks, for each firm, whom it hires, how it pays them, how it trains
>   them, and the results it reports (staff numbers, departures). A figure that may not be disclosed
>   also asks for the closest figure that is disclosed, as its own part. A firm set against the home
>   firm also asks for the home firm's own comparable figures.
>
> **Cover every ask.** Every ask gets its own part. With more asks than {max_parts} parts, merge
> asks into one part and give each merged ask its own words in that part's keyword_query; no ask is
> left without words. With several firms and several dimensions, write one part per firm with words
> for every dimension, or one part per dimension with every firm; either way every firm gets words
> for every dimension. Do not spend a part on something the question does not ask.
>
> **Same concept only.** Search words name the asked concept: the words filings and calls use for it
> and its exact synonyms. Never add a different figure that shares a word with it, even as context
> (a ratio paid to shareholders is not staff pay; company-wide staff turnover is not one unit's
> turnover; deposits are not client assets). The closest disclosed figure for an undisclosed one goes
> in its own part, never into the words of the asked figure's part.

The examples are written new (retirement-plan unit, branch staffing; no bank firm, question or
rubric wording). Tests: the prompt names no question ID; no 6-word run shared with any bank
`passes_if` **or question text** (`tests/test_prompt._grams`; the v1 test only checked `passes_if`).

### Code guard: neighbour phrases (`planner.py` + `config/entities.yaml`)
- New config list `neighbour_phrases` (S1 config, next to `synonyms`, under the same rule "a
  neighbour metric is never a synonym"; each entry commented with the figure it really names and
  the stored chunk that shows it):
  - `payout ratio` - the dividend payout ratio (RJF-10K-2025#652, SCHW-DECK-2026Q1#44 / Q3#47
    "dividend payout range"); advisor pay is "payout", "payout rate", "payout grid";
  - `dividend payout` - same;
  - `maximum potential payout` - guarantees / credit protection (MS-10K-2025#574 ...);
  - `employee turnover` - firm-wide staff turnover (BAC-10K-2025#19), not advisor attrition;
  - `client attrition` - clients leaving (BAC-10K-2025#60, #97), not advisor attrition.
- `planner.neighbour_phrases()` reads it; `strip_neighbours(words, question) -> (words, dropped)`
  removes every listed phrase found in a part's `keyword_query` that the **question** does not name.
  Matching = the synonym-key rule (`fts._synonym_pattern`: any case, hyphen or spaces between words,
  inflected last word), so "payout-ratios" is caught; whitespace collapsed after removal.
- Called in `validate_plan` after step 5 (empty / too-long words) on every model part; correction
  `part N: dropped neighbour phrase <phrase>` in `Plan.corrections` (trace, `query_log`, eval
  record). Words left empty -> the question's own words (`keyword_query` None) with the correction
  `part N: no search words left`. The rule plan (mock, fallback, `PLANNER=off`) has no planner words
  and is never touched.
- ADR-020's "Code decides the scope" bullet gets one sentence for it; `specs/retrieval.md` too.

### Part order and unused budget: **not now** (documented in ADR-020 and `specs/retrieval.md`)
A second pass that hands a later part's unused share back to earlier parts is not built. Reasons:
1. No answer-key row lost at select would be reached by more share. Real #214: the one row lost
   in a part whose share ran out while later parts left share unused is Q25's `MS-10K-2025#153`
   (p1 MS used 15.1k of 15.0k; p2 / p3 left 6.7k / 11.9k). A 0-call replay
   (`D:\ALLPROJECTS\EDJ\cache\ev224\q25_p1_flowback.py`, output `q25_p1_flowback.txt`; the saved v1
   plan, `fts.search` on the DB, no model call) reproduces #214's p1 list exactly at 15.0k, then
   gives p1 its share plus the surplus (33.6k): p1 keeps 68 passages / 21.9k tokens and stops there
   (`select()`'s floor, not the share; the same 68 with an unlimited share), and `MS-10K-2025#153`
   stays in the pool, not final (firm-pool position 25 of 227). The other rows stuck at "pool"
   (`EDJ-10K-2025#30/#264` in p3, which used 6.5k of 18.3k; `SCHW-10Q-2026Q2#25` in p4 with 30.2k)
   sat in parts that had share left. Q7's four parts all used their full share (no surplus); Q12
   and Q28 have coverage 1.0. Mock: Q7's key row `MS-10K-2025#153` is never a candidate ("none",
   #213 / #214 stage table), so more share cannot reach it; recall@final unchanged since #213.
2. In the mock it changes Q7 (p1 used its full 13.0k share while p2 left 6.9k), Q9 and Q12 (p2
   left 12.8k / 12.7k while p1 used its full share), none of which gains a key row (Q9 and Q12 have
   no rows; Q7's row is never a candidate), and breaks this issue's "mock as on main" check.
3. Q25 shows the cost of surplus share: the flow-forward gave p4 twice its equal share and the
   extra 15k went to low-rank matches, which is how the dividend deck chunks got in. A flow-back
   spends surplus the same way in earlier parts.
4. A second pass lets every earlier part overshoot by one chunk again, so ADR-019's per-question
   bound (T + one chunk) would need restating.
The one-part identity holds either way (one part has no later part). Revisit when a key row is lost
at select in a part whose share ran out while a later part left share unused **and** a replay with
the surplus added brings it into the final set (Q25's `MS-10K-2025#153` meets the first condition,
not the second). The ADR-020 and `specs/retrieval.md` text states reasons 1-4 as above, reason 1
with the replay numbers, and names Q7, Q9, Q12 in reason 2.

### Tests cannot reach a paid API (`tests/conftest.py`)
The guard must not depend on where the SDK finds credentials (Facts). The autouse fixture, in
addition to `LLM_PROVIDER=mock`:
1. **Stubs the only two client builders** (primary guard): `monkeypatch.setattr` of
   `cee.answer.llm.anthropic_client` and `cee.answer.llm.openai_client` to a function that raises
   `RuntimeError("paid API call blocked in tests: pass a fake client")`. `planner.call_planner` and
   `llm._anthropic` / `_openai` look them up on the module at call time, so any test path without a
   fake client raises before an SDK client exists (the planner falls back to the rule plan with that
   error; the answer path raises). Tests that pass a fake client are unaffected. A test that fails
   after this change is one that built a real client: it gets a fake client, not an exemption.
2. **Clears the credential environment** (defence in depth, for code that builds an SDK client
   directly): `delenv` of every variable whose name starts with `ANTHROPIC_` or `OPENAI_` (covers
   the API keys, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_PROFILE`, the workload-identity set,
   `OPENAI_ADMIN_KEY`, org / project ids), then `ANTHROPIC_CONFIG_DIR` = an empty `tmp_path`
   folder and `ANTHROPIC_BASE_URL` / `OPENAI_BASE_URL` = `http://127.0.0.1:9` (a closed local
   port). `ANTHROPIC_CONFIG_DIR` is set, not unset, on purpose: set to an empty folder it is an
   explicit profile selection, so a directly built `anthropic.Anthropic()` fails at construction
   with `CredentialsError` (config file not found) instead of falling back to the user's on-disk
   default profile (probe above). That is the safe direction.
Docstring states both layers, the `ANTHROPIC_CONFIG_DIR` reason, and why (CLAUDE.md "Paid API
calls" rule 4).

## Files to change
- `src/cee/retrieve/planner.py` - prompt v2, `PLANNER_VERSION = "plan-v2"`, `neighbour_phrases()`,
  `strip_neighbours()`, the guard in `validate_plan`, module docstring.
- `config/entities.yaml` (S1; #187 waiver) - `neighbour_phrases` with comments.
- `tests/conftest.py` - stub the two client builders; clear the `ANTHROPIC_*` / `OPENAI_*`
  environment, empty `ANTHROPIC_CONFIG_DIR`, closed-port base URLs.
- `tests/test_no_paid_calls.py` (new) - the guard's tests, incl. a fake on-disk profile.
- `tests/data/planner_v1_0214.json` (new) - the six saved plan-v1 outputs (`raw` of each
  `.eval-runs/0214-real/raw/*-plan-*.json`, keyed by question ID; `.eval-runs/` is not in git).
- `tests/test_planner.py` - guard tests on the saved outputs, v2 prompt tests (leak check over
  `passes_if` and question text).
- `tests/test_retrieval_parts.py` - fixture-schema test: a dividend-payout chunk is a candidate with
  the unguarded words and not with the guarded ones.
- `tests/test_eval_run.py` - the two `"plan-v1"` literals -> `planner.PLANNER_VERSION`.
- `specs/retrieval.md` (S1; waiver) - planner section: plan-v2, the guard and its config key, the
  part-order "not now".
- `docs/DECISIONS.md` - ADR-020: plan-v2, guard, "not now" with reasons, #224 mock and real results.
- `plans/0224-planner-v2.md` (this file).
Not changed: `fts.py`, `ask.py`, `eval_run.py` code, the answer prompt (v3), `evals/questions.yaml`,
`evals/expected_chunks.yaml`, the mock baseline (lists stay identical), the verify-cee recipes and
driver (no user-visible feature changes: the plan line, steps and mock plan are the same).

## Paid-call plan (CLAUDE.md "Paid API calls"; TL pre-approval comment on #224, 2026-11-19)
Last, on finished code after every mock check, the replay and verify-cee pass: **5 real runs, one
each, planner + answer = 2 calls each = at most 10 calls**: Q3, Q7, Q25 (targets), Q12, Q28
(regression). Model `claude-sonnet-5-5`, answer prompt v3, planner `plan-v2`, `--as-of 2026-11-17`:
`$env:LLM_PROVIDER='anthropic'; $env:LLM_MODEL='claude-sonnet-5-5'; .venv\Scripts\python.exe
scripts\eval_run.py --real --max-calls 10 --questions Q3,Q7,Q12,Q25,Q28 --as-of 2026-11-17
--baseline evals/baselines/corpus-2026-11-17/report.json --out .eval-runs/0224-real`.
Raw outputs (planner and answer, request meta, `stop_reason`) in the run's `raw/`, copied to
`D:\ALLPROJECTS\EDJ\cache\ev224\real`. The new planner version misses every plan cache entry, so 5
planner calls are made; an answer whose chunk list equals a cached #214 answer is reused (fewer than
10 calls is fine; the report's `real_calls` / `reused` are quoted).
Why the mock cannot show it: the mock uses the rule plan (one part per firm, the question's own
words) and never reads the prompt, so prompt v2 is not exercised at all; the guard is proven
offline on the saved v1 outputs (unit tests, DB replay), but only a model call shows whether v2's
parts cover every asked part (Q3, Q7), whether its Q25 words stay clear of the `must_not_return`
passages, and whether Q12 and Q28 keep their parts.
One run each, no re-runs. A truncated / invalid planner output or a failed call falls back to the
rule plan (logged, the call counted, a finding); an invalid answer is `INVALID_OUTPUT` (a finding).
A missed acceptance item is reported, not re-rolled. No other call path.

## Steps
1. **Guard against paid calls.** `tests/conftest.py` stubs + environment; `tests/test_no_paid_calls.py`
   with a fixture that patches `httpx2.Client.send` and `httpx2.AsyncClient.send` (also
   `httpx.Client.send` / `httpx.AsyncClient.send`, which the SDKs do not use today) to record the
   request and raise `httpx2.ConnectError`; the fake profile is the probe's (Facts), with
   `base_url` `http://127.0.0.1:9` in `configs/default.json`. `pytest -q`.
2. **Guard.** `neighbour_phrases` config; `strip_neighbours` + `validate_plan` hook; the saved
   outputs as `tests/data/planner_v1_0214.json`; unit tests and the fixture-schema test. `pytest -q`.
3. **Prompt v2** + version; leak test over `passes_if` and question text; `test_eval_run.py`
   literals. `pytest -q`.
4. **Offline replay (0 calls).** Scratch script `D:\ALLPROJECTS\EDJ\cache\ev224\replay.py` (not
   committed): for the six saved v1 outputs, build the query as `eval_run.py` does (`resolve(text,
   today=2026-11-17)`), `planner.from_output(q, raw, "anthropic", 4)` + `search_parts`.
   (a) With `neighbour_phrases` patched to `[]`: chunk lists identical (same order) to
   `.eval-runs/0214-real/report.json` for all six (the replay reproduces the real run).
   (b) With the guard: Q3, Q7, Q12, Q15, Q28 identical to (a); Q25 p1-p3 identical, p4 without
   "payout ratio" in its words, and no `must_not_return` id of Q25 in its hits. Q25's
   recall@final, recall@pool, coverage and per-row stage tabled for (a) vs (b), so a recall loss
   from dropping "payout ratio" is visible (reported, not tuned).
   (c) The part-order evidence: `q25_p1_flowback.py` (already run for the plan, output above) kept
   with the replay output for the PR.
   Output saved to `...\ev224\replay.txt`. A difference outside Q25 p4 stops the work (finding to
   the reviewer).
5. **Mock eval.** `.venv\Scripts\python.exe scripts\eval_run.py --as-of 2026-11-17 --baseline
   evals/baselines/corpus-2026-11-17/report.json --out .eval-runs/0224-mock`; scratch diff
   `...\ev224\mock-diff.py`: all 30 chunk lists identical, same order, to the baseline; 29 PASS /
   1 FAIL (Q19), refusal gap 5/5, keyed 22/22, 0 forbidden, no PASS -> FAIL, recall unchanged.
   Any difference stops the work. The baseline file is not replaced (only `planner_version` in meta
   and plan records would differ).
6. **Docs.** ADR-020 amendment, `specs/retrieval.md`.
7. **verify-cee**: `.venv\Scripts\python.exe scripts\verify_cee.py run` (port 8599 checked free;
   never touches `wt-212` / `wt-213`), all features PASS.
8. **Real runs last** (paid-call plan): judge each saved plan against the acceptance items below;
   Q25 refusal check and the `must_not_return` ids in its hits; behaviors and coverage vs #214;
   calls per question. Table in `...\ev224\real-table.txt`; ADR-020 real line.
9. `/finish-task`: PR "Closes #224" (or "Part of #224" with the missed item named) with the guard
   table, the replay, the mock diff, the real table with the planner outputs quoted, calls (<= 10)
   and model.

## Risks
- **The model still writes a bare "payout" for Schwab** (advisor pay is a legitimate word). One
  shared word can make the dividend deck a candidate (`SCHW-DECK-2026Q1#44` matches on `payout`
  alone); it was kept in #214 only because p4 had a 30k share. If the real Q25 still retrieves a
  must-not passage it is a finding (not re-run); the fix would then be the budget flow or ranking
  (out of scope here) or a narrower rule for the bare word, decided by the TL.
- **Synonyms add "payout" as a phrase** (a second path the guard does not see; it strips planner
  words, not expansions): a part whose words contain `pay` (`synonyms.pay`) or a form of `recruit`
  (`synonyms.recruit`) searches the phrase "payout", which matches the dividend-payout chunks in a
  Schwab / RJF part. The real Q25 judgement names which path (planner word, synonym expansion or
  neither) brought any must-not chunk in, from the saved plan and `keyword_terms()` of each part.
- **In-sample prompt**: Q3, Q7 and Q25 drove the v2 rules (the branch-staffing example mirrors Q7's
  four dimensions; the same-concept examples paraphrase must-not reasons), so their real results
  are in-sample; the PR says so. Q12 and Q28 are the regression checks.
- **Prompt v2 makes plans longer or splits differently**: the cap and validation are unchanged, so
  the bound and SQL filters hold; Q12 / Q28 losing a part is a regression finding.
- **Teaching to the test**: examples use other units and activities; the leak test checks 6-word
  overlap with every `passes_if` and question text. The "strategy" and "approach" decompositions are
  general analyst checklists, written without bank wording.
- **The neighbour list grows into a stop-list**: only phrases that name a different reported figure
  and have a stored chunk to show it go in; each is commented. Same review rule as synonyms.

## Acceptance
- [ ] Tests (0 calls): `tests/test_no_paid_calls.py`, with `httpx2.Client.send` and
  `httpx2.AsyncClient.send` (the transport of anthropic 1.9.0 / openai 3.22.1; also `httpx.*.send`)
  patched to record each request and raise `httpx2.ConnectError`, so any request attempt is seen
  and none leaves the machine:
  - inside a test `LLM_PROVIDER` is `mock`; no `ANTHROPIC_*` / `OPENAI_*` variable is set except
    `ANTHROPIC_CONFIG_DIR` (an existing, empty folder) and `ANTHROPIC_BASE_URL` /
    `OPENAI_BASE_URL` = `http://127.0.0.1:9`; a directly built `anthropic.Anthropic()` raises
    `CredentialsError` (no profile in that folder) and `openai.OpenAI()` raises `OpenAIError`;
    0 requests recorded;
  - `llm.anthropic_client()` and `llm.openai_client()` raise the "paid API call blocked" error;
  - **fake on-disk profile** (one test, one profile, one patched `send`): `ANTHROPIC_CONFIG_DIR`
    = a tmp folder with the probe's `configs/default.json` (`"base_url": "http://127.0.0.1:9"`)
    and `credentials/default.json` (dummy token, expiry one day ahead). Control:
    `anthropic.Anthropic(max_retries=0).messages.create(...)` built directly records **exactly 1**
    request, to `http://127.0.0.1:9/v1/messages`, whose `auth` is the SDK's `AccessTokenAuth`
    (the profile was used), and raises `APIConnectionError`. Guard, same setup:
    `planner.plan_question(q, "anthropic")` (no client, `PLANNER=on`) returns `source =
    "fallback"` with the blocked error in `plan.error`; `llm.generate("question", [],
    provider="anthropic")` and `provider="openai"` raise the blocked error; the requests recorded
    across the guard calls: **0**.
- [ ] Tests: on the saved v1 outputs, `validate_plan` drops "payout ratio" from Q25 p4 only (words
  otherwise unchanged, correction `part 4: dropped neighbour phrase payout ratio`), and leaves every
  part of Q3, Q7, Q12, Q15, Q28 and Q25 p1-p3 unchanged; a question that names "payout ratio" keeps
  it; "payout-ratios" is caught; words left empty -> question words with the correction; the rule
  plan is never touched; fixture schema: a "dividend payout range" chunk is a candidate for the
  unguarded p4 words and not for the guarded words.
- [ ] Tests: `PLANNER_VERSION == "plan-v2"` and `plan_cache_key` differs from the v1 key for the
  same inputs; the v2 prompt names no question ID and shares no 6-word run with any bank
  `passes_if` or question text.
- [ ] Replay (step 4): (a) reproduces the six #214 chunk lists (a mismatch here is a replay-script
  fault, fixed in the script to build the query exactly as `eval_run.py` does, before (b) is
  judged; the Q25 p1 replay already matched); (b) only Q25 p4 changes and Q25's hits hold no
  `must_not_return` id; Q25 recall@final / coverage (a) vs (b) tabled.
- [ ] Mock (`.eval-runs/0224-mock`): all 30 chunk lists identical to the baseline (rule plan
  unchanged), refusal gap 5/5, keyed 22/22, 0 forbidden, no PASS -> FAIL.
- [ ] `pytest -q` passes (mock forced, client builders stubbed and credential environment cleared
  by `tests/conftest.py`); verify-cee all PASS.
- [ ] Real (`.eval-runs/0224-real`, <= 10 calls, claude-sonnet-5-5), planner outputs quoted in the
  PR: Q3's plan has a part or search words for where Schwab concedes ground (and for competitive
  pressure); Q7's plan gives each of MS, MER, RJF words for recruiting posture, payout philosophy,
  training pipeline and retention results; Q25 retrieves none of its `must_not_return` passages
  (refusal check OK); Q12 keeps a Schwab acquisition part and an Edward Jones cost part, Q28 an EDJ
  attrition part, a Merrill part and the adjacent net headcount words (in any part, or a part of
  their own; #214 had them in p1's words). The PR states that Q3, Q7, Q25 are in-sample for the
  prompt.
- [ ] ADR-020 amended (plan-v2, guard, part order "not now" with reasons, #224 results);
  `specs/retrieval.md` updated.

## Progress log
- 2026-11-19 01:22 - plan written. Branch `tl/224-planner-v2` from `main` 42a96f7; DB
  `corpus-2026-11-17` up to date (`sync-db.ps1 -Check`). Read: the six #214 planner outputs, the Q25
  record (p4 share 30.2k, 111 passages) and the two must-not chunks on the DB (matched by `payout`
  / `ratio` only); the issue's guard measured on the six outputs (fires on 14 of 16 parts, misses
  "payout ratio"), so the plan uses an explicit neighbour-phrase list. Part-order flow-back: not now.
- 2026-11-19 01:30 - plan revised after review (issuecomment-7002702166, 1st blocking return):
  (1) the paid-call guard now stubs `llm.anthropic_client` / `openai_client` and clears the whole
  `ANTHROPIC_*` / `OPENAI_*` environment (empty `ANTHROPIC_CONFIG_DIR`, closed-port base URLs),
  with a fake on-disk profile test counting requests; facts on the SDK credential chain corrected.
  (2) Part-order reason 1 restated: 0-call replay `ev224\q25_p1_flowback.py` reproduces #214's Q25
  p1 list, and with the p2/p3 surplus (33.6k) p1 stops at 68 passages / 21.9k (floor), so
  `MS-10K-2025#153` stays in the pool; "not now" kept, revisit trigger sharpened. Non-blocking:
  Q7 in reason 2, synonym "payout" path and in-sample note in Risks, Q25 recall / coverage (a) vs
  (b) in the replay, Q28 adjacent words in any part, log time.
- 2026-11-19 01:45 - plan revised after review (issuecomment-7002783229, 2nd blocking return): the
  SDKs send through `httpx2` (anthropic 1.9.0, openai 3.22.1; `httpx2.Client` is not an
  `httpx.Client`), so the request counter patches `httpx2.Client.send` / `AsyncClient.send`.
  Probe `ev224\sdk_profile_probe.py` (0 paid calls, `send` patched to raise): empty config dir ->
  `CredentialsError`, 0 requests; fake profile -> exactly 1 request to 127.0.0.1:9 with the
  profile's `AccessTokenAuth`. Acceptance uses those exact checks; the fake `default.json` carries
  `base_url` `http://127.0.0.1:9`; conftest docstring explains why `ANTHROPIC_CONFIG_DIR` is set to
  an empty folder. Re-read Acceptance: answer-path guard named as `llm.generate(...,
  provider=...)` (no early return on empty hits); replay (a) mismatch = script fault; pytest line
  names both conftest layers.
