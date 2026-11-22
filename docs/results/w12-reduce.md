# W12 reduce speed (#275): thinking off, streamed claims, stream idle timeout

Plan: `plans/0275-reduce-speed.md`. Evidence: `docs/results/w12-reduce/` (committed copies) and
`D:\ALLPROJECTS\EDJ\cache\ev275\` (working copies).

**Result: R2 (reduce off, prompt v5.3) fails the quality floor, so the reduce stays `low`.** Test B fts scored
**20/30 blind** against the floor of 24/30 (the #272 `low` run scored 22/30 blind and 24/30 adjudicated), so
`DEEPSEEK_EFFORT_REDUCE` stays `low` and v5.3 stays behind `REDUCE_PROMPT` (default v5.2). The speed is real:

| | End to end p50 / p90 / max | Reduce wall p50 / p90 / max | First claim on the page p50 / p90 |
|---|---|---|---|
| R2, Q1-Q30 | 108 / 193 / 224 s | 35 / 107 / 117 s | 80 / 97 s |
| #272 `low` | 184 / 251 / 3,750 s | 126 / 160 / 3,660 s | - |

How the decision was reached:
- Test A first found no eligible config under the plan's fixed rule (step 11). R1 broke three quality guards; R2
  broke one, a single invented chunk id that code flagged.
- The TL overrode that rule and sent R2 to test B (see "TL override"). Test B then failed the floor.

What landed regardless (code, 0 calls to prove): the stream idle timeout (`DEEPSEEK_IDLE_S`, default 120 s, no
automatic retry), streamed claims with per-claim checks on the Ask page (with any effort), the 64000-token cap for a
streamed off reduce, prompt v5.3 behind `REDUCE_PROMPT`, and the first-claim time in `latency_report`.

## TL override (2026-11-22)
The TL chose option (b): R2 (reduce off, prompt v5.3) is adopted as the candidate, overriding the pre-fixed test-A
rule, and test B fts runs with it. Reason: R2's only flag was one invented chunk id on Q21, which code caught and never
showed early (the ground-rule path working); R2 cuts the reduce p50 from 134 s to 45 s; test B's floor (fts
adjudicated >= 24/30) is the real quality judge. Open item, not investigated now: the invented id
`SCHW-TR-2025Q5#11` passed the strict chunk-id enum (the request carried it; `schema_fallback` empty).

## Setup
- Gate f19816a (worktree `D:\ALLPROJECTS\EDJ\wt-275gate`), `run-latency.ps1` with every setting pinned
  (`deepseek-v4-pro` `/beta`, plan off, map low, stream on, `DEEPSEEK_IDLE_S=120`, `PYTHONHASHSEED=0`, `--as-of
  2026-11-17 --naive-tz America/Chicago`).
- Cache `D:\ALLPROJECTS\EDJ\cache\ev272\cache-a`: the #272 C1 plans and maps, so the runs are reduce-only.
- Baseline C1 = the #272 test-A records (`docs/results/w12-latency/a-c1`), with reduce `low`.

## Before paying: the reduce answer sizes (#272 records, 0 calls)
Answer tokens = output tokens minus reasoning tokens (`baseline-sizes.txt`, `redsize.py`):

| Run | Reduce calls | Answer tokens p50 / p90 / max | Reasoning share |
|---|---|---|---|
| fts test B | 29 (Q29 failed) | 6,260 / 16,651 / 22,726 | 0.63 |
| hybrid test B | 30 | 5,978 / 18,376 / 23,833 | 0.67 |

- Repeats (`repeats.py`, `trim.py`): about 17 % of the answer text repeats an earlier item. Removing repeats while
  keeping one claim per cell saves 15 %. Cross-firm claims are 3 % of the text, so no rule for them.
- The old off-mode cap of 20000 tokens would have cut 4 answers. The streamed off reduce therefore gets 64000; the
  API allows 1-384K in both modes, and the Q5 probe confirmed 64000 is accepted.

## Key proofs (0 calls; `key-proofs.txt`, `countcheck.py`)
- **Reduce `low`, Q1-Q30 (`cnt-low-all`):**
  - Every plan, map and re-map record was reused (0 not reused).
  - 29 reduce records were reused, plus Q29's failed record.
  - Q21 needed no new reduce.
- **Q21 in three processes:** two with `PYTHONHASHSEED=0` and one with 4242.
  - All three give the same reduce file, the same message sha `ed4b956ab0e22e36` and the same 54 map files.
  - The #272 test-B Q21 record `5feac3a2...` is not reproduced, and the hash seed is not its cause. The cause was
    not found.
- **R1 and R2 counts:** exactly 6 new reduce calls each, and no plan, map or re-map call.

## Test A (fts, reduce-only, the six questions)

| Config | Reduce wall p50 / max s | TTFT p50 s | First claim p50 s (after reduce start) | End to end p50 / max s | First claim on page p50 s | Answer tokens p50 / sum | Cut / invalid / failed | Behavior = expected | part_gap | comparison_missing | why_line_missing | number_not_found | date_mismatch | outside_matrix |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C1 (#272, reduce low) | 134 / 303 | 2.7 | - | 209 / 383 | - | 7,875 / 56,122 | 0 / 0 / 0 | 6/6 | 0 | 0 | 0 | 8 | 8 | 0 |
| R1 off, v5.2 | 32 / 69 | 1.8 | 3.8 | 104 / 150 | 73 | 4,926 / 31,512 | 0 / 0 / 0 | 6/6 | **2** | **1** | **13** | 3 | 2 | 0 |
| R2 off, v5.3 | 45 / 107 | 3.2 | 5.8 | 113 / 187 | 76 | 6,786 / 47,299 | 0 / 0 / 0 | 6/6 | 0 | 0 | 0 | 3 | 2 | **1** |

End to end = plan + slowest map + slowest re-map + reduce, from the records. First claim on page = the same, with the
reduce's `first_claim_s` in place of its wall time. Per question tables: `latency-testa.md`, `testa-tables.md`.

Per question, reduce wall in seconds (C1 / R1 / R2): Q5 38.6 / 19.9 / 21.2; Q10 137 / 28.3 / 62.1; Q19 117 / 35.7 /
44.5; Q21 303 / 69.4 / 106; Q24 153 / 22.6 / 32.0; Q26 131 / 39.4 / 44.7.

**Rule (step 11, fixed before the calls).** A config is eligible when it has:
- 0 cut, invalid or failed outputs;
- behavior equal to the expected behavior on at least C1's 6/6;
- no more part_gap, comparison_missing, why_line_missing, number_not_found, date_mismatch or outside_matrix flags
  than C1, summed over the six;
- `shown_not_final` from dedupe only.

R2 is chosen when it is eligible and at least 10 % faster than R1; else R1 when eligible; else none.

**Applied:**
- **R1: not eligible.**
  - Q10: Merrill's two parts are left as "Not answered from the evidence retrieved for ..." gaps.
  - Q19: no comparison claim.
  - Q5 and Q10: 13 items with no why-line.
- **R2: not eligible.** Q21 has one claim citing `SCHW-TR-2025Q5#11`. That id is invented: no such quarter, and it
  is not in the matrix. The request carried the chunk-id enum (`schema_fallback` empty), so the strict schema did
  not hold on this output. Code flagged the claim `unmatched_citation` and `outside_matrix`; rule 1 held, and it was
  never shown early.
- `shown_not_final` equals the duplicates `dedupe_claims` removed in every question (for example, R2 Q19 27 of 28):
  - In both configs, early claims that are missing from the final answer are only duplicates.
  - Arrival order differs from the final order, as `specs/ui.md` states.
- **Chosen: none. The reduce stays `low`, and prompt v5.2 stays the default.**

## Test B (fts, Q1-Q30, reduce-only with R2; Gate 3)
- **Calls and checks:**
  - Count `cnt-b-r2` (0 calls): 0 plan, map or re-map calls not reused; 24 new reduce calls; the six test-A
    questions reused their R2 records.
  - Run `b-r2` (gate f19816a, `--max-calls 24`): 24 real calls, USD 0.599 as priced by eval_run.
  - 0 cut, invalid or failed outputs; 0 idle events.
  - Q29, which stalled in #272, answered in 21.9 s.
- **Latency** (`b-r2-tables.md`):
  - End to end: p50 108 s, p90 193 s, max 224 s (#272 `low`: 184 / 251 / 3,750 s).
  - Reduce wall: p50 35 s, p90 107 s, max 117 s; TTFT p50 2.6 s.
  - First checked claim on the page: p50 80 s, p90 97 s.
  - First cited evidence: p50 18 s, unchanged.
- **Blind scoring**, the #272 method:
  - Four fresh Sonnet scorers by range (Q1-Q10, Q11-Q16, Q17-Q21, Q22-Q30), each reading its part in full.
  - Inputs: only `ev275\blind-in-b-r2\` (the dump made by `dump272.py`, `questions.yaml`, the #250
    `verdict-rule.txt`; hashes in `blind-in-b-r2-hashes.txt`).
  - Merged verdicts: `verdicts-b-r2-full.json`, sha256
    `5c200a23bec9a0bd436aa41d77520241c52f52862635a7f459ff227c61842d40`.
- **Score: 20/30 blind** (8 + 4 + 4 + 4), tier 1 10/18. #272 `low` scored 22/30 blind and 24/30 adjudicated, tier 1
  11/18 blind.
- **Changes against the #272 blind verdicts:**
  - Q7, Q15, Q25 and Q26 went PASS -> FAIL, all class s and borderline. Q7 and Q26 state RJF's FY2025 headcount
    8,943 as FY2026. Q15 gives no mechanism. Q25 leans on trade-press reconstructions.
  - Q8 and Q17 went FAIL -> PASS, both borderline.
- **Decision:** the floor is 24/30, and 20/30 blind is below it. Even if the PR reviewer's second read flips the 4
  borderline FAILs, the result is 24 at most, and that needs every one of them. Per the TL's instruction the reduce
  stays `low`, and v5.3 stays behind `REDUCE_PROMPT`.

## Streamed claims (what the page gains with any effort)
- With thinking off, the first checked claim arrived 3.0-6.6 s after the reduce started.
- R1 showed 180 claims early and held 46. R2 showed 349 early and held 96. Every adjacent item and every flagged
  claim was held.
- With `low`, claims stream after the reasoning ends, so the first claim comes at about the reasoning time.

## Calls and cost
| Run | Real calls | USD (new, priced by eval_run) |
|---|---|---|
| a-r1-q5 (probe) | 1 | 0.006 |
| a-r1 | 5 | 0.060 |
| a-r2 | 6 | 0.190 |
| b-r2 (test B fts) | 24 | 0.599 |
| **Total** | **36** | **0.855** |

- Every call is a `deepseek-v4-pro` reduce. No plan, map or re-map calls; no repeats or retries; no idle events.
- Test B used the Gate 3 go-ahead on the issue, after the TL's override.

## Open for the TL
1. **Strict enum.** `SCHW-TR-2025Q5#11` passed the strict chunk-id enum on R2 Q21 (thinking off, `/beta`). Not
   investigated (TL).
2. **Hybrid.** No sync and no hybrid test B, because R2 failed fts.
3. **Answer quality with thinking off.** The test-B FAILs are answer shape and accuracy: a FY2025 figure stated as
   FY2026, missing mechanisms, and reliance on trade press. A faster reduce with the same quality would need another
   approach, e.g. a cheaper reduce with thinking `low` but a shorter output (prompt v5.3 at `low`). Each would need a
   new plan.
