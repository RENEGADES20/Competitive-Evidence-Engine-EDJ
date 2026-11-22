# 0275 - Reduce speed: thinking off, streamed claims on the page, stream idle timeout

Issue: #275    Role: TL    Spec: specs/answer-citations.md, specs/ui.md

Owners (TL takeover): `src/cee/answer/*`, `specs/answer-citations.md` S2; `src/cee/app/views/ask_page.py`,
`specs/ui.md` U1; `scripts/latency_report.py`, `scripts/eval_run.py`, run scripts and `docs/DECISIONS.md` Tech lead.
Binding: ADR-021 and its #246 / #247 amendments, CLAUDE.md ground rules (rule 1: no claim without a checked
citation is shown) and "Paid API calls".

TL go-ahead on #275 (issue comment, 2026-11-22; real calls pre-approved): test A reduce-only on Q5, Q10, Q19, Q21,
Q24, Q26 (fts), and the reduce-only 30-question scored re-runs (Gate 3) in fts and hybrid-norerank, plans and maps
reused.

## Goal
The reduce (synthesis) call stops being the long pole: thinking off for the reduce, its claims shown on the Ask page
as they stream (each after the per-claim checks), a smaller answer where the prompt can trim it without dropping a
required part, and a stalled stream that fails in seconds. Quality holds: adjudicated fts >= 24/30 and
hybrid-norerank >= 23/30 (the #272 scores).

## Baseline (from the #272 raw records, 0 calls; measured 2026-11-21)
Reduce at effort `low`: wall p50 126 s fts / 153 s hybrid; it is 63-67 % reasoning. Records:
`docs/results/w12-latency/b-fts/raw/*-reduce-*.json` (fts test B, also `D:\ALLPROJECTS\EDJ\cache\ev272\cache-a`)
and `exp/hybrid:docs/results/w12-latency-hybrid/hb-run/raw/*-reduce-*.json` (also `...\ev272\cache-h`).
Answer tokens = `output_tokens - reasoning_tokens` (what a thinking-off reduce still has to write):

| Run | reduce calls | output p50 / p90 / max | reasoning share | **answer tokens p50 / p90 / max** | answer tokens total | claims p50 / max | answer tokens per claim (median) |
|---|---|---|---|---|---|---|---|
| fts test B (Q29 failed, 29 calls) | 29 | 22,375 / 29,953 / 57,498 | 0.63 | **6,260 / 16,651 / 22,726** (Q16) | 221,926 | 52 / 253 | 113 |
| hybrid test B | 30 | 22,800 / 34,104 / 50,344 | 0.67 | **5,978 / 18,376 / 23,833** (Q21) | 227,949 | 54 / 221 | 111 |
| fts test A six (C1) | 6 | 23,618 med. | 0.65 | **7,875 / 9,504 / 21,141** (Q21) | 56,122 | - | 128 |
| hybrid test A six (C1) | 6 | 31,635 med. | 0.68 | **7,756 / 10,521 / 27,059** (Q21) | 61,956 | - | 129 |

Per question, test A six, answer tokens fts / hybrid: Q5 3,130 / 3,270; Q10 6,597 / 5,595; Q19 8,972 / 8,463;
Q21 21,141 / 27,059; Q24 9,504 / 10,521; Q26 6,778 / 7,048. Above 20,000 (the current off-mode reduce cap): fts Q7
20,056, Q16 22,726, Q21 21,141; hybrid Q21 23,833 (test A 27,059).

Decode rate of the #272 reduce calls (output / wall) is about 150-190 tokens/s, so with thinking off the expected
reduce wall is about answer tokens / 175: p50 about 35 s, p90 about 95-105 s, max about 130-155 s (an estimate,
measured by test A). TTFT p50 is 2.5 s.

What the answers repeat (scripts in the step-2 evidence; heuristic: a claim or adjacent item that shares a cited
chunk with an earlier one, states no figure the earlier one lacks, and shares >= 50 % of its content words):
- fts: 366 of 2,236 items are repeats, 17.1 % of the answer text; hybrid 391 of 2,359, 17.4 %. Worst: Q19 41 %
  (fts) and Q5 43 % (hybrid) of the text. Hybrid Q26 states "8,943 advisors", "$538 million recruited production"
  and the Private Client Group quarter under 3-4 aspects each (a1, a3, a7, a8).
- Removing repeats while keeping at least one claim per cell (so no part loses its claim): 15.1 % (fts) / 15.4 %
  (hybrid) of the answer text, about 33k / 34k answer tokens of 222k / 228k.
- Cross-firm claims (part_id = an aspect id, the comparison claims that could "restate the matrix"): 3 % of the text.
  Not worth a rule.
- Why-lines: 7.9 % / 8.6 % of the text; required by rule 5, not trimmed.
- Exact duplicates are already rare (code `dedupe_claims` removes same-chunk-set duplicates): 0-7 per question.

## Design decisions (fixed before any call)

### 1. Reduce effort `off`
- `DEEPSEEK_EFFORT_REDUCE=off` already exists (#272): thinking disabled, the forced tool choice, request version
  `ds-strict-2-reduce-off-c<cap>-s1`.
- **Cap.** The off-mode reduce cap is 20000 (`llm.DEEPSEEK_OFF_CAPS`); the measured answers reach 27,059 tokens, so
  20000 would cut fts Q7, Q16, Q21 and hybrid Q21 (a cut is an invalid output). New: the reduce off cap is 64000 when
  the stage streams (the SDK's 21,333 limit is for non-streamed calls only), 20000 when it does not. The DeepSeek
  non-thinking output limit is `TODO-verify` at step 1 in the API docs (models and pricing page); if it is below
  64000 the cap is that limit, written in the Progress log. The cap is in the request version, so the key changes
  with it.

### 2. Stream idle timeout (`DEEPSEEK_IDLE_S`, default 120 s)
- Applies to every streamed DeepSeek call (plan, map, reduce), in `llm.deepseek_create` / `assemble_stream`.
- A "chunk" = any streamed chunk with a delta (content, reasoning, tool-call name or arguments), a finish_reason or
  usage. Two guards: (a) a watchdog thread per streamed call that closes the stream (`stream.close()`) when no chunk
  arrived for `DEEPSEEK_IDLE_S`, so keep-alive lines (which the SDK does not yield) do not keep a stalled call
  alive; (b) the httpx read timeout of a streamed request is `DEEPSEEK_IDLE_S + 5` (passed as `timeout=` to
  `create`, outside the request dict), for a stall with no bytes at all. Either one raises `StreamIdle` with the
  partial message assembled so far (content, reasoning, tool arguments), `output_seen` (any delta arrived) and
  the seconds since the last chunk. A non-streamed call keeps the 3600 s read timeout.
- **Save.** `scripts/eval_run.py` saves the call as failed (`failed_call`, `idle_timeout: true`, `partial` = the
  partial message, `output_seen`, `wall_s`, `ttft_s`), never re-called, like any failed call. `ask.py` logs it in
  the call log.
- **No automatic retry (TL ruling on review round 1, condition 3).** The idle timeout only makes a stalled call fail
  fast. Ask page: the failure shows an error with a manual "Try again" button (the user's own click, not a loop).
  Eval: a stalled call is a failed call; re-running it happens only when a plan states it in advance, as before.
  `max_retries=0` stays; no ADR and no CLAUDE.md change. The `llm.py` comments on the read timeout are updated to
  say the streamed read timeout is `DEEPSEEK_IDLE_S`.
- The setting is not part of any request version or cache key (it does not change the request or the output).

### 3. Streamed answer on the page
- **Incremental parse** (`reduce.StreamItems`): fed each tool-argument delta as it arrives (DeepSeek: tool-call
  argument deltas; other providers are not streamed and keep today's path). A character scanner tracks string /
  escape state and the bracket stack; it notes the top-level key (`claims`, `adjacent`, `gaps`, ...); when an object
  inside the top-level `claims` or `adjacent` array closes, the object's text is `json.loads`-ed and emitted as one
  item. It does not rely on key order, survives deltas split anywhere (inside an escape, a `\uXXXX`, a chunk id),
  and never emits an incomplete item (a cut or stalled stream emits only finished objects). Gaps are not streamed
  (code places and merges them at the end).
- **Adjacent items are never shown early (TL condition 1).** The parser emits them, but they are held until the
  final answer and never shown as claims; only `claims` items can be shown early. Test: an adjacent item arriving
  first in the stream is not shown.
- **`check_item(item, m, query)` (TL condition 2).** Builds `Answer(behavior="answer", claims=[item])` from a copy of
  the item, with `hits` = the matrix's hits (`m.hits`) for the citable ids, and runs the per-item checks below
  (`check_citations`, which also runs `withhold_normative`, `move_uncited_cells` and `ensure_handoff`; then the
  outside-matrix check, `clean_why_lines`, `check_adjacent`, `check_why_lines` on that one-item answer). The item is
  shown only if, after the checks, it is still in `claims` with identical text, `withheld` and `gaps` are empty, no
  hand-off claim was appended, and its `flags == []` (so `computed`, `why_line_removed`, `why_line_restated`,
  `claim_from_adjacent`, `number_not_found` and the rest all hold it back). Unit tests, one per held-back path:
  normative (moved to `withheld`), uncited cell (moved to `gaps`), unmatched id (`unmatched_citation`); plus
  outside-matrix id and a figure not in its chunk.
- **Per-claim checks before display** (the same functions `finish_answer` runs):

  | Check (today's function) | Per item, before display | Only at the end |
  |---|---|---|
  | Schema of the item (`Claim` / `Adjacent`) | yes | full `Answer` validation |
  | Citations: non-empty `chunk_ids`, every id in `citable(m)` (`outside_matrix`) and in the hits (`unmatched_citation`, `no_citation`) | yes | |
  | Number check `check_numbers` (with `derived_values(m)`: `number_not_found`, `computed`) | yes | |
  | Date check `check_dates` (`date_mismatch`) | yes | |
  | Normative (`is_normative`; withheld) | yes (held back) | behavior re-judged to `answer_with_boundary` |
  | Why-line scope / restated (`clean_why_lines` on the one item) and missing (`check_why_lines`) | yes | |
  | Rule 3 (`check_adjacent`: `claim_from_adjacent`, `adjacent_is_fact`) | yes | |
  | Cut at the cap, empty output (`check_output`), not JSON | | yes (the whole answer) |
  | Duplicates (`dedupe_claims`, pairs of claims) | | yes |
  | Newest-first order (`order_newest_first`) | | yes |
  | Comparison claim per comparison aspect (`check_comparisons`), computability claims (`check_computability`) | | yes |
  | Hand-off sentence (`ensure_handoff`), part coverage (`check_parts`), gaps (`place_gaps`), caveats, suggested sources, coverage note, behavior set by code | | yes |

  An item is shown early only when it passes every per-item check **with no flag at all**; a flagged item waits for
  the final answer (where it is shown as today). So rule 1 holds: every early item cites only checked chunk ids from
  the retrieved matrix, with its figures and dates found in them.
- **Events.** `call_reduce(..., on_item)` calls `on_item(kind, item)` in the calling thread (the reduce runs in the
  main thread, so Streamlit can draw). `ask()` passes `("claim", {...})` events, then `("answer", ...)` as today.
- **Page.** Under the evidence, an "Answer (in progress: checks running)" block lists the early claims in arrival
  order, each with its chunk chips, and a note that the order and duplicates may change when the checks finish. When
  the final answer is ready, the block is replaced by the answer as today (code order, newest first where it
  applies, duplicates removed, gaps, caveats, hand-off). If the call ends invalid, failed or stalled, the block is
  replaced by the failure notice the page shows today (a stall adds a "Try again" button); no early claim stays on
  screen without a final answer. `specs/ui.md` states arrival order vs final order.
- **Mock.** The mock reduce serializes its deterministic output as tool JSON and feeds it through the same parser in
  pieces (sleeping `MOCK_DELAY_S` / items between items, total delay unchanged), so the mock exercises the parse, the
  per-item checks and the page; the final answer is unchanged, so mock 30/30 is unchanged.
- **Records.** `eval_run` passes `on_item` too and stores `first_claim_s` (reduce start -> first item shown) and
  `stream_items {shown, held}`; `finish` adds `shown_not_final` (early items whose text is not in the final answer:
  only `dedupe_claims` may remove one; any other cause is a bug).

### 4. Reduce output size: prompt v5.3 (trim), behind a setting
- Measured above: the only trim worth a rule is repeats (about 15 % of answer tokens). Proposed rule, added to the
  "What goes where" section as v5.3: "State each fact once in the whole answer. When an item gives a fact (the same
  figure, event or statement from the same passage) that you already wrote under an earlier cell, do not write it
  again; but every cell that holds a fact keeps at least one claim of its own, and every comparison aspect keeps its
  comparison claim." The "keeps at least one claim" clause is what stops a part losing its claim (otherwise
  `check_parts` adds "Not answered from the evidence retrieved for ..." gaps).
- `REDUCE_PROMPT` = `v5.2` (default) | `v5.3`; `prompt.reduce_prompt()` returns (version, system text). The version
  goes into the record and the reduce key (the key already hashes the system prompt), so R1 and R2 never share a
  record; the map prompt and `EXTRACT_VERSION` do not change, so no map key changes.
- 0-call check before adopting (step 2): applying the "keep one per cell" removal to the #272 outputs and running
  `check_parts` / `check_comparisons` on them adds no gap (simulation with the saved outputs; evidence file).
- Adopted only by the test-A rule below (no extra part gaps, comparison or why-line flags against R1).

### 5. latency_report: first answer claim
- New column / stat `first claim s` = plan + slowest round-1 map + slowest re-map + reduce `first_claim_s` (`-` for
  records without it, e.g. #272's). Reduce TTFT stays. Summary line adds first-claim p50 / p90.

### 6. Reduce-only re-runs reuse every plan and map record (how the keys guarantee it)
- Plan key (`plan_path`): question, `PLANNER_VERSION`, snapshot, provider, model, planner cap, the registered metric
  keys, the resolved query (as-of, naive tz) and `plan_version` = `request_version("deepseek", "plan")` =
  `ds-strict-2-plan-off-c8000-s1`; it holds no reduce setting.
- Map / re-map key (`map_cache_key`): question, `EXTRACT_VERSION`, snapshot, provider, map model, map cap,
  `map_version` (`ds-strict-2-map-low-c128000-s1`), call id, cells, the call's chunk ids, window. No reduce setting.
  This plan does not touch the planner, the extract prompt, `EXTRACT_VERSION`, retrieval or the map settings, and the
  database is the same snapshot (`sync-db -Check`: up to date, corpus-2026-11-19), so retrieval returns the same
  chunk ids and every key is the same.
- Reduce key (`reduce_cache_key`): `REDUCE_VERSION`, cap, `reduce_version` (`...-reduce-off-c64000-s1` instead of
  `...-reduce-low-c128000-s1`), sha of the system prompt (v5.2 / v5.3) and of the rendered message and schema. So
  each question gets exactly one new reduce call (none when the answer is code-built: none of the 30 in #272).
- **Proof before paying (0 calls; TL condition 4):** every count phase shows 0 new plan, map and re-map calls for
  every question (count-log file names checked, `plan_origin` all "cached"). (a) Count with `-EffortReduce low`
  (the #272 settings) on the new gate commit: reduce new calls 0, except Q21 fts, the named exception (its reduce
  message was not byte-stable across processes in #272), with its cause recorded. (b) Before any paid run, Q21 is
  counted twice in two separate processes: the two reduce shas (message and key) and the two map file lists are
  shown, proving the instability sits in the reduce message only, not in the map specs or chunk-id order.
  (c) Count with the run's config: new calls = reduce only, one per question (`Q<n>-reduce-*`). Any other new call
  in any count: stop and find why before any paid call.
- **`PYTHONHASHSEED=0`** is pinned in the run scripts (non-blocking note 1): set iteration order may be the cause of
  the Q21 (and #250 Q12) instability; what the two-process check finds with and without it is recorded.
- Q29 fts (failed `low` reduce, never re-called) gets its first `off` reduce under the new key.

## Files to change
- `src/cee/config.py` - `DEEPSEEK_IDLE_S` (float, default 120), `REDUCE_PROMPT` (`v5.2` | `v5.3`).
- `src/cee/answer/llm.py` - reduce off cap 64000 when streamed; `StreamIdle`; idle watchdog and streamed read
  timeout in `deepseek_create` / `assemble_stream` (no automatic retry); comments on the read timeout updated.
- `src/cee/answer/prompt.py` - v5.3 trim rule; `reduce_prompt()`.
- `src/cee/answer/reduce.py` - `StreamItems` parser, `check_item`, `on_item` in `call_reduce` (DeepSeek streamed
  path; feeds argument deltas), mock streamed through the parser; `finish_answer` reuses the per-item helpers.
- `src/cee/ask.py` - `claim` events; call log `first_claim_s`, idle failure.
- `src/cee/app/views/ask_page.py` (+ `src/cee/app/components.py` if a helper is needed) - the in-progress answer
  block; the stall error with a "Try again" button.
- `scripts/eval_run.py` - `idle_timeout` / `partial` / `output_seen` in failed records, `first_claim_s`,
  `stream_items`, `shown_not_final`; reduce prompt version in the record.
- `scripts/latency_report.py` - first-claim column and stats.
- `scripts/verify_cee.py`, `.claude/skills/verify-cee/features/ask-progress.md` - early claims step.
- Run scripts: `docs/results/w12-latency/run-latency.ps1` + `.sh` - add `-IdleS` / `IDLE_S` (default 120) and
  `-ReducePrompt` / `REDUCE_PROMPT` (default v5.2), both pinned and cleared like the other settings, and
  `DEEPSEEK_IDLE_S`, `REDUCE_PROMPT` in the cleared list; `PYTHONHASHSEED=0` pinned. Evidence folder `-EvDir D:\ALLPROJECTS\EDJ\cache\ev275`.
- Tests (fake clients only; `tests/test_no_paid_calls.py` stays green): `tests/test_llm_deepseek.py` (cap, idle;
  fake streams block on a `threading.Event`, so the watchdog path really runs), new `tests/test_reduce_stream.py` (parser, per-item checks, early ⊆ final), `tests/test_ask_progress.py`,
  `tests/test_ask_page_trace.py`, `tests/test_eval_run.py`, `tests/test_latency_report.py`, `tests/test_reduce.py`
  (prompt versions).
- Docs: `specs/answer-citations.md` (reduce streaming, per-item checks table, idle timeout, v5.3),
  `specs/ui.md` (in-progress answer, arrival vs final order, "Try again"), `docs/RUN.md` and `.env.example`
  (new settings; Windows and Mac blocks), `docs/ARCHITECTURE.md` (reduce row: streamed).
- Evidence: `D:\ALLPROJECTS\EDJ\cache\ev275\<run>\` (working copies); committed copies of raw records, tables and
  verdicts under `docs/results/w12-reduce/`; report `docs/results/w12-reduce.md`. Hybrid evidence under
  `docs/results/w12-reduce-hybrid/` on the hybrid PR.

## Steps
1. Read the DeepSeek API docs for the non-thinking output limit; set the off reduce cap (64000 or the documented
   limit), Progress log line. Then `DEEPSEEK_IDLE_S`: watchdog, streamed read timeout, `StreamIdle`, records
   (`eval_run`, `ask.py`). Unit tests with fake streams that block on a `threading.Event` (released only by
   `close()`): a stall before any delta and a stall after output both raise `StreamIdle` within the idle limit,
   with `partial` and `output_seen`; exactly one `create` call (no retry); the eval saves a failed record; byte
   silence (read-timeout path) also gives `StreamIdle`; non-streamed calls keep 3600 s.
2. Measurement evidence (0 calls): the scripts that made the baseline tables above and the step-4 0-call trim
   simulation (`check_parts` / `check_comparisons` on the #272 outputs with repeats removed, one per cell kept) saved
   under `docs/results/w12-reduce/`; output tables in the report.
3. `StreamItems` + `check_item` + `on_item` in `call_reduce`; mock through the parser. Unit tests: deltas split at
   every character give the same items as `json.loads` of the whole; escaped quotes / braces / `\u` in text; key
   orders (adjacent before claims, gaps first); a cut stream emits only complete items; an adjacent item arriving
   first is not shown; per-item checks hold back (one test each) a normative claim, an uncited cell, an unmatched
   id, an outside-matrix id, a figure not in its chunk, a wrong date, a misplaced why-line; early items ⊆ final claims (same text) for a fake stream with a duplicate (only
   dedupe may differ, `shown_not_final` 1).
4. `ask()` claim events and the page block; tests: event order plan -> evidence -> claims -> answer; an early claim
   only with chunk chips from the citable set; failure replaces the block.
5. Prompt v5.3 and `REDUCE_PROMPT`; tests: the version and system sha differ, map key unchanged, default v5.2.
6. `latency_report` first-claim column + tests.
7. Docs, `.env.example`, run scripts (.ps1 + .sh, both blocks in `docs/RUN.md`).
8. Mock checks (0 calls): `pytest -q` green; mock eval Q1-Q30 fts (rule plans and the #250 plans, `run-mock`)
   before and after: 30/30 identical behavior, cells, labels, claims and claim chunk ids; `verify-cee` on mock with
   `MOCK_DELAY_S` -> screenshots: plan, evidence, early claims with the in-progress mark, final answer.
9. Commit; gate = that commit; worktree `D:\ALLPROJECTS\EDJ\wt-275run` at the gate. Docker Desktop running
   (`docker info`; start it if it fails), `sync-db -Check` up to date. 0-call key proofs (section 6): count phase
   `-EffortReduce low` on Q1-Q30 with `cache-a` -> 0 new plan / map / re-map calls, 0 new reduce calls except Q21
   (cause recorded); Q21 counted twice in separate processes (reduce shas, map file lists); count phase with each
   run's config -> one new reduce call per question, nothing else.
10. **Test A, fts, reduce-only (real).** Cache `D:\ALLPROJECTS\EDJ\cache\ev272\cache-a` (C1 plans and maps; the
    reduce records are written next to them under new keys). Settings pinned as #272 C1 (`deepseek-v4-pro` `/beta`,
    plan off, map low, `PLANNER=on`, `SUBQUESTION_TOKENS=40000`, `MAP=on`, `MAP_CONCURRENCY=24`,
    `MAP_CALL_TOKENS=60000`, `--as-of 2026-11-17 --naive-tz America/Chicago`, stream on, `DEEPSEEK_IDLE_S=120`).
    - 10a. Probe: R1 on Q5 alone (1 reduce call). A 400 (cap over the limit) stops the run (bad_request); then set
      the cap to the documented limit, record why, and repeat Q5 once (1 call, new request version; planned here).
    - 10b. R1 (`-EffortReduce off`, `-ReducePrompt v5.2`) on Q10, Q19, Q21, Q24, Q26: 5 calls (Q5 reused).
    - 10c. R2 (`-EffortReduce off`, `-ReducePrompt v5.3`) on the six: 6 calls.
    - Each: count phase first (0 calls), `--max-calls` = counted reduce calls (no retry headroom: no automatic retry).
    - After the Q5 probe, if the cap changed, the cost ceilings below are recomputed and written in the Progress log.
    - Outputs per config: `latency_report` table (reduce wall, TTFT, first claim, end to end) against #272 C1
      (`low`); cut / invalid / failed (must be 0); answer tokens; per question flag counts from the run report
      (`part_gap`, `comparison_missing`, `why_line_missing`, `number_not_found`, `date_mismatch`, `outside_matrix`)
      against C1; `shown_not_final`; behavior vs `expected_behavior`.
11. **Choose the config (rule fixed now).** Eligible: 0 cut, 0 invalid, 0 failed outputs (a stalled call is a
    failed call); behavior = `expected_behavior` on at least C1's 6/6 of the six; summed over the
    six, no more `part_gap`, `comparison_missing` or `why_line_missing` flags than C1, and no more `number_not_found`,
    `date_mismatch` or `outside_matrix` than C1; `shown_not_final` only from dedupe. R2 is chosen when eligible and
    its median reduce wall is at least 10 % below R1's (run-to-run noise; non-blocking note 4); else R1 when eligible; else none: stop, keep `low`, report to the TL, no
    test B. Defaults set to the chosen config in `src/cee/config.py` (one commit; step 8 mock checks again, 0 calls).
12. **Test B, fts (Gate 3, real).** Chosen config, Q1-Q30, gate = the step-11 commit, cache `cache-a`. Count phase
    (0 calls): new calls = reduce only; the six test-A questions reuse their test-A record of the chosen config
    (Q21 may need a new one, see section 6), so 24-25 new reduce calls expected. `--max-calls` = counted.
    Blind scoring as #272 (four fresh Sonnet scorers by range, `verdict-rule.txt`, dump of each answer with each
    cited passage), second read by the PR reviewer, adjudicated score. Floor 24/30. Below it: the default for fts
    stays `low` (the #272 records stand; no re-run) and it is reported.
13. Report `docs/results/w12-reduce.md`: baseline vs R1 / R2 / chosen (reduce wall, TTFT, first claim, end to end,
    answer tokens, cost), the trim measurement, test B score, idle events. PR to `main` (`Part of #275`, hybrid open),
    `/finish-task`, `/tl-review`, merge.
14. **Hybrid sync.** PR `main` -> `exp/hybrid` on `tl/275-hybrid-sync` (worktree `D:\ALLPROJECTS\EDJ\wt-275h`).
    Checks before merge: pytest green; `gh pr checks` green; `git diff main <sync> -- src/cee/answer src/cee/app
    src/cee/ask.py config` empty except the hybrid-only files that differed before the sync; mock hybrid-norerank
    Q1-Q30 with the #250 plans: same behavior, cells and claim chunk ids as the pre-sync `exp/hybrid` mock run.
15. **Test B, hybrid-norerank (Gate 3, real),** from `tl/275-hybrid` on the merged sync commit, cache
    `D:\ALLPROJECTS\EDJ\cache\ev272\cache-h` (the #272 hybrid plans and maps), `--mode hybrid-norerank`,
    `CEE_VECTORS=on`, `FASTEMBED_CACHE_PATH=D:\ALLPROJECTS\EDJ\cache\fastembed`, chosen config. 0-call key proofs as
    step 9 on `cache-h` (`low`: 0 new; chosen: 30 reduce calls, nothing else). Run `--max-calls` = counted (30). Scored blind the
    same way, floor 23/30; below it, `exp/hybrid` keeps reduce `low` (a hybrid-only default) and it is reported.
    Report section; PR to `exp/hybrid` (`Closes #275`), `gh pr checks` green before its merge.

## Expected real calls (DeepSeek `deepseek-v4-pro`, reduce only)
Plans, maps and re-maps: 0 in every run (reused by key; the count phases prove it before paying).

| Run | Questions | New reduce calls | `--max-calls` | USD expected (peak, all input as cache miss, output = #272 answer tokens) | USD ceiling (peak, every call at the 64000 cap) |
|---|---|---|---|---|---|
| Test A probe R1 | Q5 | 1 (+1 if the cap is refused) | 1 | 0.03 | 0.32 |
| Test A R1 | Q10, Q19, Q21, Q24, Q26 | 5 | 5 | 0.39 | 1.45 |
| Test A R2 | the six | 6 | 6 | 0.42 (less with the trim) | 1.72 |
| Test B fts | Q1-Q30 | 24-25 (30 at most) | counted | 1.25-1.66 | 8.14 |
| Test B hybrid | Q1-Q30 | 30 | 30 | 1.68 | 8.38 |
| **Total** | | **66-72 (+1 probe repeat)** | | **about 4.2** | **about 20** |

Expected = input tokens of the #272 reduce calls (fts 595k / 30, hybrid 589k / 30, six 151k) x 1.32 USD/M + answer
tokens x 3.96 USD/M (`config/pricing.yaml`, `deepseek-v4-pro` peak); off-peak halves it. Before each paid run the
count phase's input estimate and the cap are priced the same way and the ceiling is written in the Progress log.
Every raw response (and every failed / idle record with its partial output) is saved; no call is repeated except the
planned probe repeat (no automatic retry). Test A is three runs, not one (probe for the cap, then two prompt
versions); the PR says so.

## Acceptance
- [ ] Unit tests: incremental parse of streamed tool JSON (fake client), per-item checks before display (early items
      ⊆ final), idle timeout (watchdog and read-timeout paths; one `create` call, no retry); off reduce cap; the adjacent-first and
      the held-back-path tests (normative, uncited cell, unmatched id). `pytest -q` and
      `tests/test_no_paid_calls.py` green.
- [ ] Mock Q1-Q30 fts unchanged (30/30 behavior, cells, labels, claims and chunk ids against the pre-change run);
      verify-cee on mock shows early claims with the in-progress mark, then the final answer; recipe
      `ask-progress.md` and `scripts/verify_cee.py` updated.
- [ ] Reduce answer tokens measured from the #272 records (table above) and the trim decided by the 0-call
      simulation and the step-11 rule.
- [ ] 0-call key proofs: every count phase shows 0 new plan, map and re-map calls. Reduce new calls are 0 in the
      `low` count, except Q21 fts, named as the exception with its cause recorded; before any paid run Q21 is counted
      in two separate processes, with the reduce shas and map file lists shown. Each run's own count = one reduce per
      question, nothing else.
- [ ] Test A fts (Q5, Q10, Q19, Q21, Q24, Q26), R1 and R2: latency table (reduce wall, TTFT, first claim, end to
      end), 0 cut / invalid outputs, config chosen by the step-11 rule.
- [ ] Test B reduce-only Q1-Q30: fts >= 24/30 and hybrid-norerank >= 23/30 adjudicated (blind); below a floor that
      mode keeps `low`, reported.
- [ ] `latency_report` prints the first-claim time per question and p50 / p90.
- [ ] A stalled stream fails within `DEEPSEEK_IDLE_S` and is saved as failed with its partial output, no automatic
      retry; the Ask page shows an error with a "Try again" button (unit tests; any real idle event reported).
- [ ] `gh pr checks` green on the main PR, the sync PR and the hybrid PR; real call counts and USD per run in each PR.

## Progress log
- 2026-11-21 23:51 - plan written on `tl/275-reduce-speed` from `main` 99c6569. Reduce answer tokens measured from the
  #272 records (0 calls): fts p50 6,260 / p90 16,651 / max 22,726; hybrid 5,978 / 18,376 / 23,833; reasoning share
  0.63 / 0.67; repeats about 15 % of the answer text removable with one claim kept per cell. Finding: the off-mode
  reduce cap 20000 would cut 4 of the #272 answers, so the plan raises it (design 1). `sync-db -Check`: up to date
  (corpus-2026-11-19); Docker running.
- 2026-11-22 00:20 - TL ruling on plan review round 1 (issuecomment-7075039296): APPROVED with conditions, now written
  in: (1) adjacent items never shown early, test with an adjacent item first; (2) `check_item` on a one-item Answer
  with `m.hits`, shown only if still in `claims` with the same text, no `withheld` / `gaps` / hand-off, `flags == []`,
  one test per held-back path; (3) no automatic retry (no ADR-022, no CLAUDE.md change): a stall fails fast and is
  saved as failed, the app offers "Try again"; (4) count-phase acceptance: 0 new plan / map / re-map calls, reduce 0
  except Q21 fts named with its cause, Q21 counted in two processes before any paid run. Notes applied:
  `PYTHONHASHSEED=0` pinned; ceiling recomputed after the probe if the cap changes; R2 needs a >= 10 % lower median
  reduce wall; arrival vs final order in `specs/ui.md`; fake streams block on an event; plan-key text corrected.
