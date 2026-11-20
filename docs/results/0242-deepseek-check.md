# DeepSeek real check (#242)

Run on 2026-11-19, snapshot `corpus-2026-11-19`, commit f604ab2 (code = mock-run sha 6b76881,
gate logged), model `deepseek-v4-pro` on `https://api.deepseek.com/beta`, prompt v4.1, planner
plan-v2, `PLANNER_MAX_PARTS=4`, `--as-of 2026-11-17`. Plan: `plans/0242-deepseek.md`.

- **R-off** (`DEEPSEEK_THINKING=off`, request `ds-strict-1-think-off-a20000-p2000`): 6 calls.
- **R-on** (`DEEPSEEK_THINKING=on`, request `ds-strict-1-think-on-a64000-p16000`): 6 calls.
- 12 real calls in total, plus 2 for the app check below (14, the plan's cap). There was no
  401 / 402 / 429, no timeout and no re-run. Raw records (every planner
  and answer output, usage, `wall_s`, `tokens_per_s`, `reasoning_content`) are in
  [`0242-deepseek-raw/off/`](0242-deepseek-raw/off/) and [`0242-deepseek-raw/on/`](0242-deepseek-raw/on/).

## Decision: thinking on

The plan's rule, fixed before the calls:

- **Cap findings:** none. No output stopped at its cap. The fullest calls were R-on's Q22 answer
  (33,166 of 64,000 tokens, 52%) and Q22 planner (8,288 of 16,000, 52%).
- **No-output drops:** none. Every call returned, and no planner fell back to the rule plan.
  So all three questions count.
- **Criterion 1, valid outputs:** off **5/6**, on **6/6**. On wins here, and the rule stops.

The later criteria are shown for the record only.

| Criterion | off | on |
|---|---|---|
| 1. Valid outputs (3 plans + 3 answers) | 5/6 | **6/6** |
| 2. Behavior = expected | 1/2 answers (Q24 `answer`, expected `gap_with_adjacent`) | 3/3 |
| 3. Citation problems (unmatched + uncited + number flags + code part gaps) | 0 over 2 answers | 4 `number_not_found` over 3 answers |

`DEEPSEEK_THINKING` now defaults to on (`config.DEEPSEEK_THINKING_DEFAULT`, `.env.example`).

## Per question

| Q | Mode | Plan | Answer | Behavior (expected) | Claims / adjacent / gaps | Flags |
|---|---|---|---|---|---|---|
| Q1 | off | model, 4 parts | valid | answer (answer) | 32 / 2 / 3 | none |
| Q1 | on | model, 1 part | valid | answer (answer) | 14 / 0 / 0 | none |
| Q22 | off | model, 4 parts | **invalid**: arguments are not JSON | - (answer) | - | - |
| Q22 | on | model, 4 parts | valid | answer (answer) | 27 / 3 / 3 | 3 `number_not_found` |
| Q24 | off | model, 4 parts | valid | **answer** (gap_with_adjacent) | 18 / 3 / 4 | none |
| Q24 | on | model, 4 parts | valid | gap_with_adjacent (gap_with_adjacent) | 19 / 3 / 11 | 1 `number_not_found` |

### Reading the answers
- **R-off Q22, invalid.** The call stopped with `finish_reason` `tool_calls`, with 2,923 output
  tokens, far under the 20,000 cap. But the strict-mode arguments end mid-string after 8,926
  characters (`... "suggested_source": "Merrill-sp`). DeepSeek's docs warn that arguments "may not
  be valid JSON" even in strict mode, and this is that case. The output was saved as invalid and
  not re-rolled.
- **R-off Q24** answers the comparison although it names the comparability problem in four gaps.
  The question asks "is that comparison even valid?", and the bank expects `gap_with_adjacent`.
  **R-on Q24** sets `answerable` false, gives each firm's numerator and denominator as cited
  claims, and lists per firm that "client assets per advisor" is not found. That is the expected
  trap behavior.
- **R-on number flags.** These are code checks, not wrong figures by assumption:
  - Q22 has 3 flags. One example is EDJ 2Q25 "$17 billion ... down 10% from $19 billion": the
    figure in the cited passage is not matched character for character.
  - Q24 has 1 flag: the "20,514 / 19,647 / 867" advisor counts.
  - Each flag is shown on the Ask page, as for any provider.
- **Q1:**
  - R-off made 4 plan parts and 32 claims from 42,748 input tokens.
  - R-on's planner made 1 part, so the answer read 23,634 input tokens and made 14 claims. All are
    cited quarterly call and filing statements on net new asset drivers.
  - Both answers are valid and on the question.
- **Retrieval-level refusal check:** R-off Q22 and Q24 and R-on Q22 show `refusal FAIL (1)` in the
  eval report. That check runs on the retrieved set (a `must_not_return` chunk came back through
  the model plan's parts), not on the model. It is not part of the thinking comparison.

## Calls, tokens and time

The `Cap used` column is output tokens (reasoning included) out of the cap. Times are the wall
time of each call; tokens/s is output tokens divided by that time.

| Q | Mode | Call | Input (cache hit) | Output (reasoning) | Cap used | Wall s | Tokens/s |
|---|---|---|---|---|---|---|---|
| Q1 | off | planner | 1,008 (0) | 281 (-) | 14% of 2,000 | 6.2 | 45.6 |
| Q1 | off | answer | 42,748 (0) | 3,327 (-) | 17% of 20,000 | 34.5 | 96.5 |
| Q22 | off | planner | 1,056 (896) | 283 (-) | 14% of 2,000 | 4.6 | 62.2 |
| Q22 | off | answer | 68,560 (0) | 2,923 (-) | 15% of 20,000 | 31.4 | 93.1 |
| Q24 | off | planner | 1,050 (896) | 441 (-) | 22% of 2,000 | 6.4 | 68.8 |
| Q24 | off | answer | 62,565 (2,560) | 2,639 (-) | 13% of 20,000 | 31.8 | 83.0 |
| Q1 | on | planner | 1,080 (0) | 1,661 (1,474) | 10% of 16,000 | 25.7 | 64.6 |
| Q1 | on | answer | 23,634 (0) | 10,264 (8,679) | 16% of 64,000 | 99.1 | 103.6 |
| Q22 | on | planner | 1,128 (1,024) | 8,288 (7,779) | 52% of 16,000 | 102.5 | 80.9 |
| Q22 | on | answer | 65,673 (0) | 33,166 (30,250) | 52% of 64,000 | 308.8 | 107.4 |
| Q24 | on | planner | 1,122 (1,024) | 3,189 (2,764) | 20% of 16,000 | 37.3 | 85.6 |
| Q24 | on | answer | 62,611 (2,688) | 25,409 (22,565) | 40% of 64,000 | 244.7 | 103.8 |

**Totals:**
- **off:** 176,987 input tokens (4,352 cache hit), 9,894 output tokens, 115 s.
- **on:** 155,248 input tokens (4,736 cache hit), 81,977 output tokens (73,511 of them reasoning), 818 s.
- **Both modes:** 332,235 input tokens and 91,871 output tokens.

Thinking on produces about 8 times the output tokens and takes about 7 times the wall time
(Q22's answer took 5 minutes). Measured speed was 46-107 tokens/s, far above the 18 tokens/s the
3600 s read timeout assumes.

## App check (2 calls)

After the default was set (commit c210bed, its own code gate logged), Q1 was asked once on the Ask
page:
- **Setup:** Streamlit on a copy of the database, `LLM_PROVIDER=deepseek`, thinking on (the new
  default), driven by a one-off Playwright script.
- **Result:** the answer rendered after 142.6 s ("How this answer was built: 7 steps").
  - Behavior `answer`, with numbered claims that each link to a stored MS transcript chunk.
  - The footer reads `Query #1 | firms: MS | ... | model: deepseek | LLM called: True`.
  - Screenshot: [`0242-deepseek-app-q1.png`](0242-deepseek-app-q1.png).
- **Not verified:** the script's read-back of the query_log row failed, because of a SQL error in
  the script (`json_array_length` on a `jsonb` column). The database copy was dropped before the
  row could be read. The row's `model` and `llm_calls` were therefore not read back. The footer
  shows the query was logged (query #1). `model_name("deepseek")` is covered by a unit test. No
  call was repeated to get the row.

**Cost:** the DeepSeek pages fetched on 2026-11-19 list no prices (the "Models & Pricing" page did
not render its table), so this report gives tokens, not dollars.
