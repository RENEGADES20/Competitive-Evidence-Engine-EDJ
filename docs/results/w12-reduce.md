# W12 reduce speed (#275): thinking off, streamed claims, stream idle timeout

Plan: `plans/0275-reduce-speed.md`. Evidence: `docs/results/w12-reduce/` (committed copies) and
`D:\ALLPROJECTS\EDJ\cache\ev275\` (working copies).

**Result: test A found no eligible config, so by the plan's fixed rule (step 11) the reduce stays at effort `low`
and test B was not run.** Thinking off cuts the reduce from p50 134 s to 32-45 s on the six questions, and the first
checked claim shows about 4-6 s after the reduce starts. But each off config breaks one quality guard against the
#272 `low` answers:
- R1 (prompt v5.2): 2 part gaps (Q10), 1 missing comparison claim (Q19) and 13 missing why-lines (Q5, Q10).
- R2 (prompt v5.3): every guard holds except one claim with an invented chunk id (Q21, `SCHW-TR-2025Q5#11`, no such
  quarter). Code flagged it `outside_matrix`, and it was never shown early.

The TL decides whether to change the rule or the config before any test B.

What landed regardless (code, 0 calls to prove): the stream idle timeout (`DEEPSEEK_IDLE_S`, default 120 s, no
automatic retry), streamed claims with per-claim checks on the Ask page (with any effort), the 64000-token cap for a
streamed off reduce, prompt v5.3 behind `REDUCE_PROMPT`, and the first-claim time in `latency_report`.

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
| **Total** | **12** | **0.256** |

- Every call is a `deepseek-v4-pro` reduce. No plan, map or re-map calls; no repeats or retries; no idle events.
- Test B was not run, so the Gate 3 go-ahead was not used.

## Open for the TL
1. Test B (fts, then the hybrid sync and hybrid): not run, because no config is eligible.
2. Options the TL may choose:
   - **(a) Keep `low`.** The reduce stays the long pole, at p50 134 s on these six.
   - **(b) Accept R2.** Its one failed guard is an invented id that code flagged and never showed. Then run test B
     fts with R2, about 24-30 reduce calls, as planned.
   - **(c) A follow-up.** Find out why the strict chunk-id enum did not hold on R2's Q21 output (thinking off,
     strict tool, `/beta`), then rerun R2 on Q21 only.
