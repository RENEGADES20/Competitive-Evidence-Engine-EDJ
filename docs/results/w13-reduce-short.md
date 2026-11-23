# W13 shorter reduce output: item refs rendered by code (#284)

**Code removed by #289 (2026-11-23):** the v6 path (`REDUCE_PROMPT=v6`, rendering, mock, tests) is no longer in `src/`; this doc, its evidence and `plans/0284-reduce-short.md` stay as the record. The scripts here that drive or import the v6 code (`run-short.*`, `render_check.py`) no longer run.

Plan: `plans/0284-reduce-short.md` (TL conditions B1-B5 after plan review round 1). Evidence:
`docs/results/w13-reduce-short/` (committed copies) and `D:\ALLPROJECTS\EDJ\cache\ev284\` (working copies).

**Result: stage 1 stopped under rule B1, so the default stays v5.2 (a finding, not adopted).** v6 roughly halved what
the model writes as answer text. But its reasoning grew, so total reduce output did not fall. On the six heaviest
questions:
- output tokens: p50 24,518 against 23,618 for #272 (the rule needed at most 14,171);
- reasoning: p50 20,460 against 16,931;
- answer text: p50 4,153 against 7,875.

Wall time was p50 281 s against 134 s (the rule needed at most 93.8 s). Part of that is the service: these calls
streamed at about 88 tokens/s, against about 180 tokens/s in #272. Even at #272's speed, 24,518 tokens would take
about 136 s, so the wall miss is not only the service. One unknown ref came back (Q24), which the rule also counts.
The other 24 calls, the blind scoring and the 30-question run were not made. `REDUCE_PROMPT=v6` stays in the code
for later experiments; the default is v5.2.

## What changed (reduce prompt v6, behind `REDUCE_PROMPT`)
- The model no longer copies the evidence. A claim names matrix items by ref (`a1.MS/2`, `a2.MS/derived`); code writes
  `[<Firm>: ]Per the <source label>, published <date>: <item text> (scope; period; value when the text lacks them).`
  and appends the model's one-sentence why-line where one is required. The model writes its own words only for
  comparison and computation claims, position labels, and items without a ref. Effort stays `low`.
- Guards (TL B2): an unknown ref is dropped (`unknown_ref`); a ref outside the claim's part is dropped
  (`ref_part_mismatch`); a claim whose refs were all dropped is removed (`dropped`), so the part check names the
  cell as a gap. The firm prefix comes from the ref's own cell.
- Items code never renders (no ref): those the map flagged `number_not_found`, and (found in step 5, below) those
  whose rendered text fails the claim number check against their own chunks.
- Streaming: each streamed claim is rendered by the same code before the per-claim checks; a run-cache reuse keeps the
  rendered answer. Quotes are not rendered (spec note).
- Spec: `specs/answer-citations.md` (#284 block). Default unchanged (v5.2) until the adoption rule says otherwise.

## Checks before any paid call (0 calls)
| Check | Result | Evidence |
|---|---|---|
| pytest | 1221 passed locally; CI `pytest` pass on PR #287 | `tests/test_reduce_v6.py` (27 tests) |
| Mock compare, default v5.2, rule plans and #272 plans | 30/30 identical to clean main b32d1f2 (status, chunks, behavior, cell labels, claims) | `g-mock-v52-*`, `cmp_mock.py` |
| Mock compare, `REDUCE_PROMPT=v6` | 30/30 equal in status, chunks, behavior, cell labels and (part, chunk ids) per claim | `g-mock-v6-*`, `cmp_mock6.py` |
| Render fidelity, mock matrices (B4) | 74 + 374 items, 0 problems; 0 no_citation / outside_matrix / number_not_found / unknown_ref | `g-mock-v6-*-check.json` |
| Render fidelity + rules, the #272 fts matrices (step 5) | 322 items, 0 fidelity problems; 0 no_citation, 0 outside_matrix, 0 rendered number_not_found, 0 rendered figures outside the matrix; ref enum fallback on Q15 only (chunk ids, 871 values) | `g-render-272-check.json` |
| Count phase at gate 1c9aca2 | 515 records reused (30 plan, 454 map, 31 re-map), 0 new; 30 new reduce keys; Q21 plan and maps reused (NB4) | `g-v6-count.head-log.txt` |
| verify-cee, mock, `REDUCE_PROMPT=v6` | ask-answer, ask-progress, ask-stop-retry PASS; "Read the rendered claims (#284)" `v6|1|0|0|1`; the streamed card reads "Per the EDJ 10-K ..." before the final answer (ask-progress "Look while the answer streams (#275)") | `ev284\verify\20261123-022132-1c9aca2` |

**Step 5 finding, fixed before any call (a deviation from the plan's B2 enum, confirmed by the TL).** The first render check (gate d9d621f) found 4 rendered claims flagged
`number_not_found` on the #272 matrices (Q9, Q21, Q23, Q24): map items whose text states a figure the passage writes
another way ("more than 15,000" for a deck's "15K+", "$37 Trillion"), with no map flag, and one value rendered in a
form the checker cannot parse. Fix: such items get no ref (`reduce.referable`, a stricter B2 enum) and a value is
rendered only when its figures are not already in the text. Re-run at gate 1c9aca2: rendered number_not_found 0. The
4 remaining final flags there come from the mock's own text claims for those items (the mock writes the item text;
the v6 prompt forbids the figure in model text).

## Options weighed (fixed in the plan before any call)
- **Item refs rendered by code (chosen).** In #272 test B the reduce wrote 22,375 output tokens at p50: 13,302 reasoning
  and 6,260 answer. The reasoning drafts each claim's sentence, and that sentence is mostly the map item's own text
  plus a date phrase, which code can write. The risk named in the plan: answer tokens are only 28 % of the output, so
  the 50 % target needs the reasoning itself to shrink by about a third.
- **v5.3's length rule at `low`.** It cuts about 15 % (the repeats, `w12-reduce.md`), cannot reach 50 %, and the model
  still copies every figure.
- **A short planning step plus parallel per-part writers.** 1 + parts calls, the matrix sent once per part, and the
  comparison claims and newest-first order span parts; more streaming changes.
- **What a miss means (NB2).** If v6 shortens the answer but not the reasoning (for example 15,000 tokens / 90 s at
  p50), the remaining lever is the reasoning itself: v5.3's rule at `low` on top of v6, or the split design, each its
  own issue. If v6 keeps speed but loses quality, the default stays v5.2.

## Stage 1 (6 paid calls, the only paid calls of #284)
- **Setup.** Gate 1c9aca2, clean worktree `wt-284run`, run with `run-short.ps1 -Phase run -MaxCalls 6 -ReducePrompt v6
  -Questions Q5,Q10,Q19,Q21,Q24,Q26`.
- **Pinned settings.** `deepseek-v4-pro` on `/beta`, effort plan off / map low / reduce low, streaming,
  `DEEPSEEK_IDLE_S=120`, `PYTHONHASHSEED=0`, as-of 2026-11-17, snapshot corpus-2026-11-19.
- **Records reused.** Every plan, map and re-map record is reused from #272 test B (copy of `ev272\cache-a` in
  `ev284\cache`). Why #272's records and not #283's (NB3): like for like with the baseline, and #283's prefix cache
  ships off.
- **Window.** UTC 10:00:20-10:29:48 on Monday 2026-11-23, after the stage launcher waited for off-peak. Every call is
  priced `off_peak` by `cost.py`.
- **Evidence.** `w13-reduce-short/s1/`: the 6 raw records with reasoning, `report.json`, the head log, and
  `stage1.md` / `.json` made by `analyze.py --stage1`. The baseline is `ev272\a-c1` (the #272 test-A C1 records of
  the same six).

| Q | Output tokens (#272) | Reasoning (#272) | Answer tokens (#272) | Wall s (#272) | First claim s | Refs | Unknown / mismatch / dropped | Text claims | number_not_found model / rendered (#272) | Model-text figures outside the matrix |
|---|---|---|---|---|---|---|---|---|---|---|
| Q5 | 5,377 (7,272) | 3,983 (4,142) | 1,394 (3,130) | 72 (39) | 62 | 33 | 0 / 0 / 0 | 0 | 0 / 0 (0) | 3 |
| Q10 | 22,555 (24,330) | 15,409 (17,733) | 7,146 (6,597) | 254 (137) | 202 | 90 | 0 / 0 / 0 | 1 | 0 / 0 (1) | - |
| Q19 | 26,481 (21,036) | 21,821 (12,064) | 4,660 (8,972) | 310 (117) | 277 | 85 | 0 / 0 / 0 | 7 | 0 / 0 (0) | - |
| Q21 | 42,063 (57,498) | 29,492 (36,357) | 12,571 (21,141) | 449 (303) | 358 | 212 | 0 / 0 / 0 | 5 | 3 / 0 (5) | - |
| Q24 | 27,468 (27,328) | 23,823 (17,824) | 3,645 (9,504) | 308 (153) | 283 | 64 | 1 / 0 / 1 | 2 | 0 / 0 (2) | - |
| Q26 | 21,890 (22,906) | 19,098 (16,128) | 2,792 (6,778) | 248 (131) | 230 | 54 | 0 / 0 / 0 | 0 | 0 / 0 (0) | 900, 900, 40 |
| **p50** | **24,518 (23,618)** | **20,460 (16,931)** | **4,153 (7,875)** | **281 (134)** | 253 | | | | | |

**Rule B1, as fixed before the call:**

| Check | Value | Pass |
|---|---|---|
| unknown_ref = 0 | 1 (Q24 `a2.MER/1`) | no |
| ref_part_mismatch = 0 | 0 | yes |
| no_citation before the move = 0 | 0 | yes |
| outside_matrix = 0 | 0 | yes |
| cut / invalid / failed = 0 | 0 | yes |
| number_not_found in model text <= 8 | 3 | yes |
| number_not_found in rendered text = 0 | 0 | yes |
| output p50 <= 14,171 (0.60 x 23,618) | 24,518 | **no** |
| wall p50 <= 93.8 s (0.70 x 134.0) | 281 s | **no** |

**What the six show:**
- **Where the tokens went.** Answer tokens fell by about half (sum 32,208 against 57,122). That is the part code now
  writes.
  - The reasoning did not shrink. Q19, Q24 and Q26 reasoned 18-81 % longer.
  - Q26's reasoning (69,101 characters, 264 mentions of "why") is mostly why-line drafting for its 8 recency
    aspects: the model still writes and rejects candidate why-sentences ("restate", then another try).
  - The rest is re-reading items to choose refs.
  - The main risk named in the plan (the 50 % target needs the reasoning to shrink too) is what happened.
- **Service speed.** The calls streamed at about 75-94 tokens/s, against 175-190 in #272. TTFT p50 was 3.1 s.
  - #272 ran Saturday off-peak; this ran Monday at the start of off-peak.
  - So the wall times are not like for like, but the token miss alone fails the rule.
- **Guards worked on real output:**
  - **Q24 unknown ref.** It cites `a2.MER/1`, the "more than 15,000 wealth advisors" item that step 5 made unreferable.
    The message listed it as "(no ref)", and the strict enum had no fallback (`schema_fallback` empty), yet the ref
    came back. This is the same strict-enum leak #275 saw with a chunk id. Code dropped it (`unknown_ref`, then
    `dropped`), the claim was never shown, and rule 1 held.
  - 0 shown claims without a citation, 0 `outside_matrix`, 0 `ref_part_mismatch`, and 0 rendered figures outside the
    matrix or missing from their passage.
- **Model-text figures:**
  - **number_not_found in model text: 3, all on Q21.** These are text claims for no-ref items that kept the item's
    figure ("446 advisors", "$37 Trillion", "$1.92 trillion"), which the v6 prompt forbids. They are flagged as in
    v5.2; #272 had 8 on the six.
  - **Figures outside the matrix: 4, in why-lines.** The "3%" of Q5 and the "900" and "40%" of Q26 come from the
    items' context passages. Those are cited and the number check passes, but they are not in a matrix item.
- **Streaming.**
  - 381 claims were shown early, 170 held.
  - The first claim arrived at p50 253 s after the reduce start, because with `low` the claims stream after the
    reasoning.
  - Early claims missing from the final answer are only duplicates `dedupe_claims` removed: equal on five questions;
    on Q26 3 of the 8 removed had been shown.

## Calls and cost
| Run | Real calls | USD (priced by eval_run, all off-peak) | #272, same six reduce calls (off-peak) |
|---|---|---|---|
| g-v6-s1 (stage 1) | 6 | 0.394 | 0.413 |

The only paid calls were these 6 `deepseek-v4-pro` reduce calls: none failed or were retried, and there were no
plan, map or re-map calls. The 24 stage-2 calls were not made, because rule B1 stopped the run.

## Decision (TL, 2026-11-23)
The stage-1 stop stands: v6 is not adopted, the default stays v5.2, and no more paid calls are made under #284. v6
ships behind `REDUCE_PROMPT=v6`, off by default. The default request is unchanged: mock v5.2 is 30/30 identical to
main, and the test asserts the v5.2 system prompt and schema.

## Findings
- The reasoning grew while the answer tokens halved.
- Why-line drafting drives the reasoning in recency-heavy questions.
- The strict enum leaked twice, with code catching it both times: #275 returned a chunk id, and here Q24 returned a
  ref.
- The provider ran at about 88 tokens/s against about 180 in #272, so wall-time comparisons need the day and hour, or
  tokens/s, next to them.
- Quality was not scored: the run stopped before the 30-question run.

## Next levers
Three levers remain, all aimed at the reasoning:
- a cheaper why-line;
- v5.3's "state each fact once" on top of v6;
- the split design (a short planning step plus parallel per-part writers).

These six questions do not rank them. No issue is opened here.
