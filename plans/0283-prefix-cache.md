# 0283 - Map prefix cache: shared byte-stable prefix per firm, identical tool schema

Issue: #283    Role: TL    Spec: specs/answer-citations.md (map step), ADR-021    Design: `docs/results/w13-prefix-cache.md` (written in step 7)

## Goal
Map calls of one firm in one question send one byte-identical prefix (system prompt, one tool schema for every map
call, question, firm, window, the firm's passage block); only "which sub-question to answer" comes last. Map
cache-hit share rises from 4% to >= 50%, $/question falls below #272's $0.52, adjudicated quality stays >= 24/30.

## Design (fixed before any call; estimates from the #272 test B map records, 0 calls)
- **Prefix = the firm call's message** (`map_specs` firm spec, as before #272 fan-out): question, firm, window, all
  of the firm's sub-questions, passages grouped by sub-question. **Suffix**: "answer only sub-question <id>
  [tags]: text; cite only passages under its heading and these pool ids: ...". `allowed` per cell is unchanged and
  `parse_output` still rejects any other chunk id (flag `unmatched_citation`). Mock outputs unchanged (mock reads
  the cell's `groups`).
- **Ceiling `MAP_PREFIX_TOKENS` (default 150000).** A firm block above it keeps today's per-cell layout (batches
  over `MAP_CALL_TOKENS` as now). Estimate: 4-5 of 75 firm groups (Q16-Q18, Q20 all-sources, Q21 SCHW), map hit share
  about 0.73, map input $9.95 -> about $5.50, per-call input p50 about 53k, max 147k. Without a ceiling: 0.90 but
  calls up to 372k tokens (slowest-call risk).
- **Tool schema identical for every map call**: no `enum` of cell ids (cell and derivation ref). Unknown ids are
  dropped by `parse_output` as today and flagged `unknown_cell` on the call's cells (new). System prompt: "one cell
  for each sub-question the message asks for" (prompt change) -> `EXTRACT_VERSION` extract-v1.3.
- **Concurrency remedy: leader first.** In `run_round`, each prefix group (>= 2 calls) submits one leader before
  all followers (FIFO, so every leader starts first; no deadlock). Followers wait for the leader's gate, then
  `MAP_PREFIX_WAIT_S` (default 5 s). `MAP_PREFIX_GATE` = `first_chunk` (default: leader's first streamed chunk, set
  through a context-variable hook in `llm.deepseek_create`) | `done` | `off`. A leader failure opens the gate.
  Records get `prefix_group`, `prefix_role` (leader / follower / solo / cell) and `gate_wait_s`; the latency
  report adds `gate_wait_s` to the critical path, so the remedy's cost is measured.
- **Request version bump**: map stage only, `ds-strict-2-map-low-c128000-s1` -> `...-s1-pf150000`; plan and reduce
  versions unchanged (plans reused from #272). Old map records never match (new version + extract-v1.3).

## TL conditions (review round 1, issuecomment-7091445276; binding)
- **B1 strict ids.** `parse_output` drops an output cell whose id is not this call's: `foreign_cell` (another
  sub-question of the question) or `unknown_cell` (no such id), flagged on the call's cells; the call's own cell
  stays `missing_cell` if absent. A derivation whose inputs name a cell outside the call is dropped
  (`derivation=None`, flag `unknown_ref`). Tests for all three.
- **B2 gate.** Leaders are chosen after the skip / `allow()` filter, from calls that really run. The gate opens in a
  `finally` however the leader ends (landed, invalid, failed, `ProviderStop`, `Cancelled`, cache hit, non-streamed:
  opens at done); a cached leader also skips `MAP_PREFIX_WAIT_S`. Followers wait with `Event.wait(0.1)` in a loop
  that checks `cancel.is_set()`; the extra wait uses `cancel.sleep`. Group key = sha256 of system + tool schema +
  prefix bytes, so batches and over-ceiling per-cell specs never group; a group of 1 is `solo`, nothing waits.
  No deadlock: all leaders and solos precede all followers in the FIFO queue, so a leader never waits for a free
  worker. Tests: cached leader, skipped leader, leader `ProviderStop`, Stop during a follower's wait,
  `first_chunk` with a non-streamed leader, concurrency 1 and concurrency < groups (must finish).
- **B3 layout check (0 calls).** `docs/results/w13-prefix-cache/cmp_cells.py` compares the new `report.json`
  with `w12-latency/b-fts/report.json` per cell (label changed, items lost / gained) and the per-item rates of
  `unmatched_citation`, `quote_not_found`, `number_not_found`. Trigger, fixed now: unmatched_citation rate more
  than 2x #272, or > 10% of model cells change label -> the results doc names the layout as the suspected cause
  before any score is read. No re-roll.
- **B4 probe rule.** Follower share = sum(`cache_hit_tokens`) / sum(prefix tokens) over Q10 follower records whose
  leader was not cached; prefix tokens of a record = `input_tokens` x `prefix_chars` / `request_chars` (both saved
  in the record: system + schema + prefix message, and the whole request). >= 0.50 -> `first_chunk`; < 0.50 ->
  `done`. Fewer than 5 such followers (inconclusive) -> `done`. The chosen value is pinned in `config.py` and the run
  scripts before the full run.
- **NB1** no-enum schema and firm-block layout apply to anthropic and openai requests too. **NB2** the prefix lists
  every sub-question of the firm spec, incl. cells with an empty allowed set (as the firm call did); test asserts it.
  **NB3** PR adds the mock `eval_run.py --as-of 2026-11-17 --baseline evalsaselines\corpus-2026-11-19eport.json`
  result. **NB4** if the gate moves to `done`, Q10 keeps its probe timings (noted in the doc). **NB6** `docs/RUN.md`
  gets both OS blocks for the new settings.

## Files to change
- `src/cee/answer/extract.py` - schema, prompt, prefix/suffix message, group + leader gate in `run_round`, flags, records.
- `src/cee/answer/llm.py` - map request-version suffix; first-chunk hook. `src/cee/config.py` - the three settings.
- `scripts/eval_run.py` - prefix fields in map records. `scripts/latency_report.py` - cache-hit share per stage
  and per map role; `gate_wait_s` in the critical path.
- Tests: `tests/test_extract.py`, `tests/test_llm_deepseek.py`, `tests/test_deepseek_stages.py`,
  `tests/test_eval_run.py`, `tests/test_latency_report.py` (fake clients only).
- Docs: `specs/answer-citations.md` (map section), `.env.example`, `docs/RUN.md`, `docs/results/w13-prefix-cache.md`
  + `docs/results/w13-prefix-cache/` (run scripts `run-prefix.ps1` + `.sh` copied from `w12-latency/run-latency.*`
  with the new settings pinned, mock compare, raw records, reports, verdicts).

## Steps
1. Mock baseline from clean `main` (0 calls): mock Q1-Q30 fts, rule plans and #272 plans (`w12-latency/run-mock.*`).
2. Schema + prompt + prefix/suffix layout + ceiling; tests: (a) a question with >= 3 cells in one firm: all its
   DeepSeek map requests are byte-identical in system, tools and the user message up to the suffix marker; (b)
   tool schema equal across every map call of a question; (c) an unknown cell id is dropped, `unknown_cell`
   flagged, an out-of-allowed chunk id still `unmatched_citation`; (d) block over the ceiling -> per-cell layout.
3. Leader gate + hook + settings + version bump; tests with fake clients: leaders start before followers, a
   follower waits for the gate, a failed leader opens it, `off` = today's order, map key changes, plan key does not.
4. Records + latency report (cache share per stage / role); tests on fixture records.
5. Mock compare: Q1-Q30 fts identical to step 1 (status, chunks, behavior, cell labels, claims); pytest green.
6. Real calls (below), probe then full run, from a clean worktree at the gate commit.
7. Results doc, scoring inputs, PR. verify-cee not run: the app shows nothing different (CLAUDE.md "Verification").

## Acceptance
- [ ] `pytest -q` -> all pass locally and `gh pr checks` green; tests (a)-(d) and step 3 present.
- [ ] Mock compare (step 5, `cmp_mock.py` method) -> 30/30 identical to clean `main`.
- [ ] Real run report: map cache-hit share of map input >= 50% (or the doc explains the measured ceiling); overall
  share; tokens and $ per question < $0.52 with the drop; map and critical-path p50 vs #272 test B; critical-path
  p50 <= 184 s + measured `gate_wait_s` p50.
- [ ] B3: `cmp_cells.py` table and trigger result in the results doc.
- [ ] Quality: blind + adjudicated per #272 "Scoring"; adjudicated >= 24/30. Every raw record saved; calls and $ in the PR.

## Paid calls (TL go-ahead 2026-11-22 on #283, incl. Gate 3)
Why: cache hits, cost, latency and answer quality exist only on DeepSeek. deepseek-v4-pro on `/beta`, settings as
#272 C1; plans reused from `ev272\cache-a` (`--reuse-plans deepseek:deepseek-v4-pro@ds-strict-2-plan-off-c8000-s1`).
- Probe: Q10 once (31 maps in 5 firms; about 39 calls). Decides the gate: followers' hit share of their prefix
  >= 50% keeps `first_chunk`, else `done` for the full run. Q10 is reused by key in the full run, never re-called.
- Full run: fts Q1-Q30 once each. #272 test B used 545 records (30 plan, 454 map, 31 re-map, 30 reduce); same plans
  -> same cells, so about 515 new calls (about 39 in the probe, about 476 after), re-map count may differ.
  `--max-calls` from the 0-call count phase. Expected about $11 (about $0.37/question) off-peak.
- Command (Win; `.sh` the same flags): `powershell -File docs\results\w13-prefix-cache\run-prefix.ps1 -Wt
  D:\ALLPROJECTS\EDJ\wt-283run -Out b-fts -Cache D:\ALLPROJECTS\EDJ\cache\ev283\cache -Phase run -GateSha <gate>
  -MaxCalls <count> -ReusePlans -PlanVersion ds-strict-2-plan-off-c8000-s1` (probe: `-Out probe -Questions Q10`),
  i.e. `eval_run.py --real --max-calls N --naive-tz America/Chicago --cache <dir> --questions Q1..Q30 --as-of
  2026-11-17 --baseline evals\baselines\corpus-2026-11-19\report.json --out <dir> --reuse-plans ...`.
- Scoring (0 API calls by me): I dump the 30 answers with cited passages the #272 way (`dump272.py`) into
  `ev283\blind-in-fts\` with `questions.yaml` and the #250 `verdict-rule.txt`, plus a sha256 hashes file. The
  coordinator launches fresh Sonnet blind scorers by range (Q1-Q10, Q11-Q16, Q17-Q21, Q22-Q30); the PR reviewer
  adjudicates. No output is re-rolled.

## Risks
- Each cell now sees sibling passages it cannot cite (about 56% of its block): more rejected citations or worse
  focus. Measured by `unmatched_citation` counts and the scored gate; if < 24/30 the PR reports it, no re-roll.
- Cache is best effort; the first follower may hit only fixed-interval units. Measured per role, not assumed.
- `first_chunk` may come before the prefix is stored; the probe decides. `done` costs about one leader wall time
  (map p50 34 s) on the critical path.
- Larger per-call input may slow the slowest map call; reported against #272.

## Progress log
- 2026-11-22 22:13 - plan written (start-task steps 1-6; DB up to date corpus-2026-11-19; 0 calls). Estimates
  from `w12-latency/b-fts/raw` map records.
- 2026-11-22 23:05 - review round 1 CHANGES REQUESTED; TL ruling: B1-B4 and NB1-4, NB6 binding, written in as
  "TL conditions". Build starts; full run waits for the coordinator after the Q10 probe.
- 2026-11-22 22:30 - built (e79ad3d): pytest 1192 passed; mock Q1-Q30 fts 30/30 identical to clean main (rule plans
  and #272 plans; `docs/results/w13-prefix-cache/mock-compare.txt`). Mock map calls 454 -> 442: firms under the
  ceiling are no longer batched (Q7, Q12, Q15, Q25), so the full run expects about 442 maps, not 454.
- 2026-11-22 22:47 - Q10 probe (41 new calls: 31 map, 9 re-map, 1 reduce; $0.67, peak hours; plan reused): map
  cache-hit share 0.769, followers 0.923; B4 share 0.929 over 25 followers -> `first_chunk` kept and pinned. Q10
  critical path 271 s (#272: 239 s; follower gate wait p50 10.8 s). Evidence `docs/results/w13-prefix-cache/probe/`.
- 2026-11-22 22:53 - full-run count phase at gate 8f36b7d (0 calls): 412 new round-1 maps (Q10 reused), usd.py
  ceiling `-MaxCalls 854`; expected about 460 new calls (412 maps + re-maps + 29 reduces), about $8 off-peak.
  Stopped here: the coordinator starts the full run.
