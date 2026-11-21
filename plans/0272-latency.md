# 0272 - W12 answer latency: effort per stage, finer map fan-out, streaming, progressive Ask page

Issue: #272    Role: TL    Spec: specs/answer-citations.md, specs/retrieval.md, specs/ui.md

Owners (TL takeover): `src/cee/answer/*`, `specs/answer-citations.md` S2; `src/cee/retrieve/planner.py`,
`specs/retrieval.md` S1; `src/cee/app/views/ask_page.py`, `specs/ui.md` U1. Binding: ADR-021 and its #246 / #247
amendments, CLAUDE.md ground rules and "Paid API calls". TL ruling on plan review round 1:
issuecomment-7067044356 (conditions 1-3, written in below).

TL go-ahead on #272 (2026-11-21): the planned real calls of test A, and the Gate 3 full 30-question scored runs of
test B in both modes (fts on `main`, hybrid-norerank on `exp/hybrid`), including one planned re-run with reduce effort
`high` for a mode below its floor.

## Goal
An answer takes as little time as possible (target 30 s or less end to end), and the first cited evidence shows in
the Ask page within 30 s. Quality holds: adjudicated fts >= 18/30 and hybrid-norerank >= 22/30 (the W11 scores).

## Baseline (from the #250 raw records, 0 calls; checked 2026-11-21)
Critical path per question = plan + slowest round-1 map + slowest re-map + reduce (`wall_s`), from
`D:\ALLPROJECTS\EDJ\cache\ev250\{fts,hyb}-run\raw\*.json`:
- fts: median 415 s, min 139 s, max 1079 s (Q19). hybrid-norerank: median 522 s, min 178 s, max 997 s.
- Test A questions, fts: Q5 139 s, Q10 510 s, Q19 1079 s, Q21 816 s, Q24 913 s, Q26 879 s.
Step 1 reprints this with `scripts/latency_report.py` (per stage p50 / p90 / max and tokens) for the PR and report.

## Design decisions (fixed before any call)
- **Effort per stage.** `DEEPSEEK_EFFORT_PLAN`, `DEEPSEEK_EFFORT_MAP`, `DEEPSEEK_EFFORT_REDUCE`, each
  `off | low | high | max`. `off` = `extra_body {"thinking": {"type": "disabled"}}` and the forced tool choice (as
  today); `low | high | max` = thinking enabled, `tool_choice auto`, and `reasoning_effort=<value>` sent in the request.
  Interim default `high` (today's behaviour, now explicit) until step 10 sets the defaults from test A.
  `DEEPSEEK_THINKING` stays for the legacy `MAP=off` answer call only.
- **Model per stage.** `DEEPSEEK_MODEL_MAP` (empty = `DEEPSEEK_MODEL`), so C3 can send the map to `deepseek-flash`
  (priced already in `config/pricing.yaml`). The map record and cache key carry the map model.
- **Caps.** Thinking-mode cap 64000 -> 128000 for planner, map and reduce; off-mode caps and timeouts unchanged.
- **Request version per stage.** `llm.request_version(provider, stage)` returns e.g.
  `ds-strict-2-map-low-c128000-s1` (stage, effort, cap, stream on). Each stage's cache key carries only its own stage's
  version, so a plan made with plan effort `off` is reused across C1 / C2 / C3 and test B, and a reduce-only re-run
  reuses every map record. Old `ds-strict-1-...` records are never matched.
- **Streaming.** Every DeepSeek call is sent with `stream=True` and `stream_options {"include_usage": true}`; the
  chunks are assembled into the same message shape (`content`, `reasoning_content`, `tool_calls`, `finish_reason`,
  `usage`), so every check after the call is unchanged. `ttft_s` (first chunk with any delta) is stored next to
  `wall_s` in the eval records and the Ask call log. With streaming the 3600 s read timeout applies per chunk, so a
  128000-token output (about 7100 s at 18 tokens/s) is not cut by it; a unit test checks the client timeout settings. Fallback: `DEEPSEEK_STREAM` = `on | off | nothink`
  (`nothink` streams only thinking-off calls). Streaming of strict tools is not documented, so the Q5 probe (step 9a)
  decides; the setting is part of the request version (`s1` / `s0` / `sn`).
- **Map fan-out.** Round 1: one call per sub-question (firm x aspect cell) with passages, id `map.<cell id>`, instead
  of one per firm; research stays one call (`map.research`, 2-4 passages in #250). A cell whose passages exceed
  `MAP_CALL_TOKENS` (default 40000 = `SUBQUESTION_TOKENS`, so a cell's normal budget fits one call) is split, in input
  order, into batches `map.<cell id>.b<n>`. Round 2: one re-map per re-searched cell with new chunks
  (`remap.<cell id>`). Batch merge per cell: items concatenated (input order, duplicates by chunk id dropped); label
  `fact` if any batch has a fact, else `different_quantity`, else `not_disclosed`, else `not_found`; any failed batch
  with no fact -> `failed`. The merged result is the same per-firm `Cell` set and `EvidenceMatrix` shape as today, so
  `finish()` and the reduce input are unchanged. `MAP_CONCURRENCY` default 6 -> 24. `EXTRACT_VERSION` is bumped
  (call shape changed; the new call ids change the keys anyway).
- **Per-cell citation sets (TL condition 1).** The firm's call spec is built exactly as today (`map_specs`, unchanged
  rule), then split into one spec per cell:
  - (a) passages of a cell call = the cell's own passages (`groups[cell]`, as today) plus, listed separately under
    the same sub-question as "also in this sub-question's search pool (listed for a sibling)", the firm input
    passages in `plan.pools[cell] & input_ids` that are not its own. `allowed[cell]` is today's rule unchanged: own
    chunk ids | (`plan.pools[cell]` & the firm's `input_ids`), per cell. So a cell can see and cite exactly the set it
    could cite in the firm call; it no longer sees sibling passages it could never cite.
  - (b) A firm with no passages: code cells as today (`not_found`, reason "no passages retrieved", flag
    `no_passages`). A cell inside a firm with passages whose own passages are empty: when its pool overlap is not
    empty it gets a call, rendered with today's `KEPT_ELSEWHERE` line plus the pool passages; when its `allowed` set
    is empty (today rendered `NO_PASSAGES` or `KEPT_ELSEWHERE` with nothing citable) it becomes the same code cell
    (`not_found`, "no passages retrieved", `no_passages`) and no call is made. Stated difference: today the model
    labels such a cell, but with nothing citable it can only return a label with no cited item; a code `not_found`
    says the same without a paid call. On the mock the label is `not_found` either way (mock reads `groups` only).
  - (c) Unit test: one firm, two cells sharing a chunk (cell A lists it, cell B has it in its pool, `KEPT_ELSEWHERE`);
    the same per-cell fake model outputs parsed against the firm spec and against the split specs give the same
    labels and claim chunk ids; and a cell with an empty `allowed` set gives the code cell above.
- **Progressive Ask page.** `run_map(on_call=...)` fires in the main thread inside `run_round`'s `as_completed` loop
  (never in a worker thread, so Streamlit can draw). `ask()` passes three events to the page: plan ready (the
  decompose text), cells landed (that call's validated cells), answer ready. The page shows the plan first, then
  under "Evidence so far" one line per `fact` item: quote/value + its chunk chip (chunk ids already checked by
  `parse_output` against the cell's retrieved set, so rule 1 and the citation invariant hold), then the answer.
- **No direct-answer path** in this plan (issue item 7b): if the fts median critical path is still above 60 s after
  test B, it becomes a follow-up issue with an ADR-021 amendment first.

## Files to change
- `scripts/latency_report.py` (new) - per question critical path; per stage p50 / p90 / max of `wall_s`, `ttft_s`,
  output and reasoning tokens; reads a run's `raw/` folder (stage from the record's file-name prefix and `call_id`).
- `src/cee/config.py` - effort, model-map, stream, `MAP_CALL_TOKENS` settings; `MAP_CONCURRENCY_DEFAULT` 24.
- `src/cee/answer/llm.py` - caps, `deepseek_tool_request(..., stage)`, `request_version(provider, stage)`, streaming
  in `deepseek_create` + chunk assembly, `ttft_s`.
- `src/cee/retrieve/planner.py`, `src/cee/answer/extract.py`, `src/cee/answer/reduce.py` - pass the stage; map
  fan-out, batches, merge, `on_call`.
- `src/cee/ask.py` - progress events (plan ready, cells landed); call log gets `ttft_s`.
- `src/cee/app/views/ask_page.py`, `src/cee/app/components.py` (if a helper is needed) - plan, evidence lines, answer.
- `scripts/eval_run.py` - per-stage request versions and map model in the keys; `ttft_s` in records; summary line.
- `scripts/verify_cee.py`, `.claude/skills/verify-cee/features/ask-progress.md` (+ `ask-answer.md` if its shots
  change) - progressive screenshots on mock.
- Tests: `tests/test_llm_deepseek.py`, `tests/test_extract.py`, `tests/test_planner.py`, `tests/test_reduce.py`,
  `tests/test_eval_run.py`, `tests/test_ask_progress.py`, `tests/test_ask_page_trace.py`, new
  `tests/test_latency_report.py`. Fake clients only (`tests/test_no_paid_calls.py` stays green).
- Docs: `specs/answer-citations.md` (map calls per cell, batches, merge), `specs/ui.md` (progressive page),
  `docs/ARCHITECTURE.md` (extract row, call count), `docs/DECISIONS.md` (ADR-021 note: map per cell), `docs/RUN.md`
  and `.env.example` (new settings).
- Run scripts (new): `docs/results/w12-latency/run-latency.ps1` + `.sh` (phases `plan | count | run`; `-Config
  C1|C2|C3|chosen|rerun`; pins every setting, clears the env vars in `finally`, code gate on `-GateSha`, refuses a
  dirty tree / `.env` in the worktree / existing out dir, like `w11-run/run-scored.*`); `run-mock.ps1` + `.sh`.
- Evidence: `D:\ALLPROJECTS\EDJ\cache\ev272\<run>\` (working copies, caches); committed copies of raw records,
  reports and verdicts under `docs/results/w12-latency/`; report `docs/results/w12-latency.md`.
- Hybrid side (later PR to `exp/hybrid`): sync merge only, plus `docs/results/w12-latency/` hybrid evidence.

## Steps
0. Before any code change: mock eval Q1-Q30 fts from a clean `main` worktree (rule plans and #250 plans), saved as
   the step-7 "before" run (0 calls).
1. `scripts/latency_report.py` + tests; print the #250 fts and hybrid baseline tables (0 calls).
2. Effort per stage, model per stage, caps 128000, per-stage request versions in every cache key (planner, map,
   reduce, legacy answer). Unit tests on the built request with a fake client: effort / thinking / tool_choice /
   `reasoning_effort` / model / cap per stage; keys differ when any of them differs; a plan key ignores map / reduce
   effort.
3. Streaming: `stream=True`, chunk assembly (reasoning, content, tool-call argument deltas by index, finish_reason,
   usage), `ttft_s`, `DEEPSEEK_STREAM` fallback. Unit tests with a fake streamed response, including a cut
   (`finish_reason length`) and a stream without usage.
4. Map fan-out per cell, batches over `MAP_CALL_TOKENS`, merge, re-map per cell, `MAP_CONCURRENCY` 24. Unit tests:
   merged cells equal the per-firm result for the same outputs; batch merge precedence; a failed batch; remap ids;
   the condition-1 test (c).
5. Progressive Ask page: `on_call`, `ask()` events, page sections. Tests: events order (plan -> cells -> answer); an
   evidence line only for a `fact` item with a chunk id in the retrieved set.
6. Docs and `.env.example` (step "Files to change").
7. Mock checks (0 calls): `pytest -q` green; mock eval Q1-Q30 fts (`run-mock`, rule plans and the #250 saved plans via
   `--reuse-plans`) before and after the change: per question the same behavior, cells and labels, claim chunk ids
   (only map call ids / call counts change); `verify-cee` on mock with `MOCK_DELAY_S` -> screenshots plan, evidence,
   answer in that order.
8. Run scripts `.ps1` + `.sh`, with Windows and Mac blocks for `run-latency` and `run-mock` in `docs/RUN.md`; 0-call dry run (`-Phase count`) of C1 on the six test-A questions.
9. **Test A, fts (real calls; code fixed and committed first, gate = that commit).** Settings pinned:
   `deepseek-v4-pro` (`/beta`), `PLANNER=on`, `SUBQUESTION_TOKENS=40000`, `MAP=on`, `MAP_CONCURRENCY=24`, `--as-of
   2026-11-17 --naive-tz America/Chicago`, questions Q5, Q10, Q19, Q21, Q24, Q26.
   - C1: plan off, map low, reduce low. C2: plan off, map off, reduce low. C3: C1 with map model `deepseek-flash`.
   - 9a. Stream probe: C1 on Q5 alone (plan off = thinking off; map / reduce low = thinking on): 3 calls. If a streamed
     call fails (400, or no assembled tool call although the stream ended with `tool_calls`), stop, set
     `DEEPSEEK_STREAM` to `nothink` (or `off` if the thinking-off call failed), record why, and repeat Q5 once (3 calls,
     a new request version; planned here). Not a quality re-roll. The stream setting is pinned before 9b; if the plan
     call's version changed, Q5's plan is re-made (1 call).
   - 9b. C1 plan phase (5 new planner calls), count phase (0 calls), run with `--max-calls` = counted round-1 maps +
     one re-map per round-1 cell (a ceiling, not a target) + 6 reduces.
   - 9c. C2 and C3: count phase then run, plans reused from C1 (0 planner calls).
   - Outputs per config: `latency_report` table, cut outputs (must be 0), invalid / failed calls, behaviors, cost.
10. **Choose the config (rule fixed now).** Eligible: 0 cut outputs, 0 invalid outputs, and the number of the six
    whose behavior equals `expected_behavior` in `evals/questions.yaml` is at least the #250 fts run's number on the
    same six: **4/6** (`docs/results/w11-report.md`: Q5 answer, Q19 answer_with_boundary, Q24 answer, Q26 answer
    match; Q10 gap_with_adjacent and Q21 none do not). Pick the eligible config with the lowest median critical path; C3 only if it beats the best of C1 / C2.
    None eligible: stop, report to the TL, no test B. If C3 is chosen and a mode is still below its floor after the
    reduce-`high` re-run (step 11 / 14), flash is not adopted: the defaults go to the best eligible non-flash config,
    and any further paid run needs a new TL go-ahead. Set the defaults to the chosen config (one commit; mock checks of
    step 7 re-run, 0 calls).
11. **Test B, fts (Gate 3, real).** Chosen config, Q1-Q30, from this branch at the commit of step 10 (code gate).
    Plan phase (new planner calls only for the 24 questions without a test-A plan), count, run. Blind scoring by fresh
    Sonnet scorers (the #250 method: `verdict-rule.txt`, dump of answers with each cited passage, split in four parts),
    second read by the PR reviewer, adjudicated score. Below 18/30: one planned re-run with `DEEPSEEK_EFFORT_REDUCE=high`
    (reduce calls only; maps and plans reused by key), scored the same way.
12. Report `docs/results/w12-latency.md`: baseline vs C1 / C2 / C3 / chosen tables (critical path p50 / p90 / max, per
    stage, TTFT, tokens), first-evidence time (plan + first map call landed), cost per question, test B score. PR to
    `main` (`Part of #272`, hybrid open items listed), `/finish-task`, `/tl-review`, merge.
13. **Hybrid (later step, after the main PR merges).** Sync PR: `main` -> `exp/hybrid` on `tl/272-hybrid-sync`
    (worktree `D:\ALLPROJECTS\EDJ\wt-272h`). Checks before merge: pytest green; `gh pr checks` green;
    `git diff main <sync> -- src/cee/answer src/cee/retrieve/planner.py src/cee/retrieve/fts.py src/cee/app config` empty
    except the hybrid-only files that differed before the sync; mock hybrid-norerank Q1-Q30 with the #250 plans: same
    behavior, cells and claim chunk ids as the pre-sync `exp/hybrid` mock run; fts parity on the branch (fts mock
    report equals main's).
14. **Hybrid test A then test B (real), from `tl/272-hybrid` on the merged sync commit.** `--mode hybrid-norerank`,
    `CEE_VECTORS=on`, `FASTEMBED_CACHE_PATH=D:\ALLPROJECTS\EDJ\cache\fastembed`, chosen config, plans reused from the
    fts runs (0 planner calls). Test A: six questions, output latency table and 0 cut outputs; any cut output: stop and
    report to the TL, no hybrid test B. Test B: Q1-Q30, scored
    blind the same way, floor 22/30; below it, one re-run with reduce `high`. Report section added; PR to `exp/hybrid`
    (`Closes #272`). Before its merge: `gh pr checks` green on the hybrid PR.

## Expected real calls (DeepSeek `deepseek-v4-pro`; C3 maps on `deepseek-flash`)
Per question: 1 planner + one map call per cell with passages (+ batches) + research (when present) + 0..1 re-map per
re-searched cell + 1 reduce (0 when the answer is code-built). Ceilings from the #250 fts plans (cells = firms with
passages x aspects); the count phase gives the exact round-1 number before each paid run:

| Q | #250 shape | planner | round-1 maps | re-maps (ceiling) | reduce |
|---|---|---|---|---|---|
| Q5 | 1 firm x 1 aspect | 1 | 1 | 1 | 1 |
| Q10 | 5 firms x 2 + research | 1 | <= 11 | <= 10 | 1 |
| Q19 | 3 firms x 13 + research | 1 | <= 40 | <= 39 | 1 |
| Q21 | 5 firms x 16 + research | 1 | <= 81 | <= 80 | 1 |
| Q24 | 5 firms x 4 | 1 | <= 20 | <= 20 | 1 |
| Q26 | 1 firm x 8 | 1 | <= 8 | <= 8 | 1 |

(Plans made with plan effort `off` may have other aspect counts; the counts above are not a promise.)
- Test A fts: planner 6 (C1 only; Q5's in the probe), per config <= 161 round-1 maps + re-maps + 6 reduces;
  probe repeat <= 3 if needed.
- Test A hybrid: 0 planner, <= 161 round-1 maps + re-maps + 6 reduces.
- Test B: fts 24 new planner calls + round-1 maps (count phase) + re-maps + <= 30 reduces; hybrid 0 planner + maps +
  <= 30 reduces; a re-run with reduce `high`: <= 30 reduce calls per mode, nothing else.
Cost: a call per cell repeats the system prompt, firm list and window (about 3-4k tokens per call, mostly DeepSeek
cache hits), so input cost rises with the call count (Q21: about 81 round-1 calls vs 6); output tokens should fall
with lower effort. The count phase prints `input_tokens_est` per call, and the report gives cost per question per
config against #250.
USD ceiling: before each paid run the count phase's estimated input tokens and the output caps are priced with
`config/pricing.yaml` (peak rates) and the ceiling is written in the Progress log before the run starts.
Every raw response is saved in the run's evidence folder; no call is repeated except the planned ones above.

## Acceptance
- [ ] Effort, cap, model and streaming settings are in the built request and in the stage's cache key (unit tests on
      the request, fake client); `pytest -q` green, `tests/test_no_paid_calls.py` green.
- [ ] Map split and merge: merged cells equal the per-firm shape (unit tests); mock Q1-Q30 fts (rule plans and #250
      plans) unchanged in behavior, cells, labels and claim chunk ids (30/30) against the pre-change run.
- [ ] Ask page shows plan, then evidence lines (each with a chunk chip from the retrieved set), then the answer:
      verify-cee screenshots on mock, recipe `ask-progress.md` and `scripts/verify_cee.py` updated.
- [ ] `python scripts/latency_report.py <run>/raw` prints the #250 baseline (fts median 415 s) and every run's table.
- [ ] Test A fts: Q5, Q10, Q19, Q21, Q24, Q26 under C1, C2, C3: latency table, 0 cut outputs for the chosen config,
      config chosen by the step-10 rule. Hybrid: the same six with the chosen config, 0 cut outputs.
- [ ] Test B: Q1-Q30 fts >= 18/30 and hybrid-norerank >= 22/30 adjudicated (blind), with latency p50 / p90 and score
      per mode in `docs/results/w12-latency.md`; a mode below its floor re-run once with reduce `high`.
- [ ] First cited evidence time (plan `wall_s` + first landed round-1 map call, from the records) and end-to-end p50
      reported per mode (target 30 s; reported, not gated).
- [ ] `gh pr checks` green on the main PR, the sync PR and the hybrid PR; real call counts per run in each PR.

## Progress log
- 2026-11-21 12:05 - plan written. Baseline recomputed from #250 raw records (fts median 415 s, hybrid 522 s).
  `sync-db -Check` exit 1 (Docker not running); to start before step 7.
- 2026-11-21 12:20 - plan review (Sonnet reviewer agent, one round): APPROVE WITH NOTES. Blocking 1 (flash not
  adopted if a mode stays below its floor) and notes 2, 4-9 applied; note 3 answered with the cost paragraph.
- 2026-11-21 12:40 - TL ruling on review round 1 (issuecomment-7067044356): approved with conditions 1-3, now written
  in (Owners line; per-cell citation sets; hybrid `gh pr checks`; USD ceiling; eligibility baseline 4/6).
- 2026-11-21 12:50 - steps 0-8 done, 0 real calls. Commits be94cd6 (effort/cap/model/stream per stage, stage request
  versions), c91fa94 (map per cell, batches, merge, progressive Ask page, latency_report), 2172170 (docs, run scripts,
  verify steps). Decisions made while building: (1) `MAP_CALL_TOKENS` default 60000, not 40000: at 40000 the mock run
  with the #250 plans batched Q17's whole-corpus cells (the cell budget 40000 plus prompt, schema and pool passages is
  over 40000); (2) a streamed request whose client returns a whole response is used as is (fake clients, and any
  provider that ignores `stream`); (3) the legacy `MAP=off` answer call keeps its old request (no stream, no effort),
  it is not in the W11 flow; (4) `--reuse-plans PROVIDER:MODEL@VERSION` reads plans saved under another planner
  request version (the #250 plans for the mock check). Checks: `pytest -q` 1093 passed; mock Q1-Q30 fts vs clean
  `main` 7657d64 (`D:\ALLPROJECTS\EDJ\cache\ev272\{main,br}-{rule,plans250}`, `cmp_mock.py`): rule plans 30/30
  identical, #250 plans 30/30 identical (status, retrieved chunk ids, behavior, every cell label, every claim and its
  chunk ids); map calls on the mock 75 -> 436 with the #250 plans. verify-cee all 10 features PASS
  (`.verify-runs/20261121-124310-c91fa94`; ask-progress steps 1-2: plan first, then an Edward Jones evidence card with
  a chip, no answer yet). `latency_report` on #250: fts p50 415 s, p90 822 s; hybrid p50 522 s.
- 2026-11-21 12:54 - 9a stream probe: Q5 planner call (plan off, streamed): tool_calls, valid plan, wall 5.3 s, TTFT 2.0 s (1 call). Q5 count: 4 round-1 map calls; run max-calls 9, USD ceiling 4.97 (expected about 0.38).
- 2026-11-21 12:55 - 9a probe passed: streaming works with strict tools in both modes (4 map calls low + 1 reduce low, all tool_calls, TTFT 1.4-3.8 s; 5 calls, USD 0.128). Q5 critical path 91.5 s (W11 139 s). DEEPSEEK_STREAM stays on; no repeat.
- 2026-11-21 13:00 - C1 plan phase: 5 planner calls (Q10, Q19, Q21, Q24, Q26), USD 0.007. C1 count (0 calls): round-1 map calls Q5 4 (saved), Q10 31, Q19 25, Q21 46, Q24 20, Q26 8 = 130 new; input est 3.82M tokens (each cell call repeats its pool passages). C1 run --max-calls 266 (130 + 130 re-map ceiling + 6 reduces); USD hard ceiling 145 (every call at its cap, peak), expected about 9.
- 2026-11-21 13:23 - C1 run (gate 2172170, worktree wt-272run at c024d21): 152 new calls (map 133 incl. Q5's 4 saved
  from the probe, re-map 18, reduce 6; plans reused), USD 3.60 new (off-peak, Saturday). 0 cut, 0 invalid, 0 failed;
  behavior matches expected on 6/6. Critical path p50 209 s, p90 313 s, max 383 s (Q21); first evidence p50 17 s.
  Reduce is now the long pole (p50 134 s, 23.6k output tokens at effort low); map p50 29 s.
- 2026-11-21 13:28 - C2 and C3 counts (0 calls): 134 round-1 map calls each (Q5's 4 now new: other map keys); --max-calls 274 each. USD hard ceiling C2 35 / C3 47, expected about 9 / 3 (peak).
- 2026-11-21 13:50 - C2 run: 156 new calls, USD 0.83 new. Critical path p50 172 s, p90 289 s; first evidence p50 9 s; map p50 8.7 s (C1 29 s). 1 invalid output: Q19 map.a1.EDJ arguments not JSON (thinking off, strict; the #242 finding). Behavior 6/6. Not eligible by the step-10 rule (0 invalid required).
- 2026-11-21 14:15 - C3 run (map on deepseek-flash): 149 new calls, USD 1.31 new. Critical path p50 206 s, p90 361 s;
  first evidence p50 10 s. 3 invalid outputs, all flash maps with arguments that are not JSON (Q10 map.research, Q19
  map.a6.EDJ, Q21 map.a5.SCHW). Not eligible. Test A fts total: 1 + 5 (probe) + 5 + 152 + 156 + 149 = 468 new calls,
  USD about 5.87 (off-peak). Step 10 rule (`D:\ALLPROJECTS\EDJ\cache\ev272\testa.py`): eligible = C1 only (0 cut,
  0 invalid, behavior 6/6 >= 4/6) -> **C1 chosen: plan off, map low, reduce low, map on deepseek-v4-pro**. Flash is not
  adopted. Defaults set in `src/cee/config.py`; tests updated; pytest 1093 passed.
- 2026-11-21 14:27 - step 10 mock recheck at 4a64f79 (0 calls): #250 plans 30/30 identical to clean main. Test B gate 4a64f79, worktree wt-272run, cache cache-a (the six test-A questions reuse their C1 records).
- 2026-11-21 14:40 - test B fts plan phase: 24 new planner calls (USD 0.026), 6 reused from test A. Count (0 calls): 321 new round-1 map calls (the six test-A questions reuse every C1 record), input est 12.9M tokens; run --max-calls 672 (321 + 321 re-map ceiling + 30 reduces). USD hard ceiling 377 (every call at its cap, peak), expected about 28 peak / 14 off-peak.
- 2026-11-21 15:42 - test B fts run 1 (b-fts) stopped at Q25 with DeepSeek 429 (rate limit; ProviderStop, nothing saved for the refused call, the run stops as designed). Q1-Q24 done, 474 records saved, 0 invalid so far. Resumed after a pause with the same settings and cache as b-fts-r2 (saved outputs reused; not a re-roll; RUN.md: wait, then run again).
- 2026-11-21 15:51 - BLOCKED: the resumed test B run (b-fts-r2) stopped at its first new call with DeepSeek 402
  "insufficient balance". Nothing was saved for the refused call; no further call is possible until the account is
  topped up. State: test B fts Q1-Q24 complete (474 records, 0 cut, 0 invalid, 0 failed); Q25 has 7 of its map records;
  Q26-Q30 not run. Test B new calls so far 322 (24 planner + 298 map / re-map / reduce), USD 10.26 off-peak; all test
  B and test A records saved (`docs/results/w12-latency/`, `D:\ALLPROJECTS\EDJ\cache\ev272\cache-a`). Interim latency
  Q1-Q24: critical path p50 173 s, p90 241 s, max 285 s; first evidence p50 18 s, p90 25 s (W11 #250: p50 415 s,
  p90 822 s; first evidence p50 204 s). Finding: Q21's reduce key differed between test A and test B although every
  plan and map record was reused (same behavior, same 138 citable chunks), so one extra reduce call was made; the
  reduce message is not byte-stable across processes (as Q12 in the #250 replay). Not in this plan's scope; noted.
  Resume after top-up: the same command with `-Out b-fts-r3` (cache-a, gate 4a64f79, --max-calls 672); every saved
  record is reused, so only Q25-Q30's remaining calls are made.
