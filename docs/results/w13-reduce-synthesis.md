# W13 reduce prompts v7 and v8: direct answer plus short cited synthesis (#292)

Plan: `plans/0292-reduce-synthesis.md` (approved, issue #292 comments 7117074418 and, for v8, 7118166000). Evidence:
`docs/results/w13-reduce-synthesis/` (committed copies) and `D:\ALLPROJECTS\EDJ\cache\ev292\` (working copies).

**Result: v8 is the new default (`REDUCE_PROMPT` default `v8`).** At the current reduce effort (`low`) it passed the
plan's rule on all four questions: 1-5 short sentences, the first one cited. Reduce effort `off` failed Q24 (no
comparison claim), so it is reported, not proposed. v7 failed and stays behind the flag (first part of this doc).
Latency: at `low`, Q5 and Q8 fell to 15 s and 25 s (v5.2: 39 s and 85 s). Q22 and Q24 still reason 20-26k tokens.
Their wall time was 260 s and 343 s, at peak-hour service speed (78 tokens/s against 179-189 for v5.2). At `off`,
every reduce took 6-14 s. Details: "v8" below.

## v7 (first try, not adopted)

**Result: v7 stays behind `REDUCE_PROMPT=v7`; the default stays v5.2 (the plan's default rule failed on 3 of 4).**
v7 cut the answer from 26-70 claims to 5-15 sentences, and every first sentence answers the question. But:
- Q5 wrote 10 sentences, most of them lists of items. The cap was 5.
- Q24's first sentence has no citation (`no_citation`).
- Q22 has no synthesis sentence at all, only one sentence per firm per aspect.

Reduce output grew on all four questions, by 7-69 % (reasoning by 40-165 %). Cost rose 21 % and wall time rose 12-91 %,
at the same service speed.

## Design (v7, behind `REDUCE_PROMPT`)
- **One form rule** (`reduce.list_form(aspects, query, version)`). The reduce (prompt, message, mock, checks), the
  streamed answer and the final answer on the Ask page all read it.
  - **List form:** the question's own window; or, under v5.2 / v5.3, any recency aspect (#291); or, under v7, every
    aspect recency.
  - Under v7, a list-form question is answered by v5.2 byte for byte: prompt, message, mock, version label and cache
    key (Q26, Q27).
  - Why not #291's rule under v7: 15 of the 30 #272 plans have a recency aspect, Q5 among them.
  - ADR-021 rule 5 is amended (why-lines in list-form answers only; `docs/DECISIONS.md`).
- **Prompt v7, synthesis form:**
  - Claim 1 answers the question directly, in one sentence.
  - Then 2-4 synthesis sentences (a comparison across firms, a pattern, a change, a tension or a gap), never a
    restatement item by item.
  - One claim is one sentence. It may cite several cells and cites every chunk it rests on.
  - Every cell holding a fact is cited by some sentence; more than 4 synthesis sentences are allowed only for that.
  - Asked figures are kept, at most one sentence per firm for a series.
  - Kept from v5.2: dating, attribution, the comparison and computation claims, adjacent items and the standard
    wording. No why-lines.
  - The message drops the why-line notes and the `context` / `related` lines.
- **Code checks, synthesis form only** (spec `specs/answer-citations.md`, #292 block):
  - Coverage: a claim with an aspect id covers each cell of that aspect whose chunks it cites (`part_coverage` state
    `aspect`).
  - A computation claim with the aspect id counts.
  - `dedupe_claims` keeps claim 1.
  - A claim with an aspect id that cites only adjacent-only cells is flagged `claim_from_adjacent`.
  - No why-line check and no newest-first re-sort.
- **Mock v7:** claim 1 is "In short: <first holding item>.". Then each non-proxy, non-comparison aspect gets one
  sentence joining the first item of every holding cell. Derived cells, comparison claims and adjacent items are as in
  v5.2.

## Checks before the paid call (0 calls)
| Check | Result | Evidence |
|---|---|---|
| pytest | 1210 passed locally (1200 + 10 new in `tests/test_reduce_synthesis.py`); CI on the PR | - |
| Mock fts Q1-Q30, rule plans and #272 plans: v5.2 (branch) vs main 558ee94 | 30/30 identical on both | `mock-compare.txt` |
| Same, v7 vs v5.2 | Q26, Q27 byte-identical; 28 changed; 0 new flag kinds; 0 higher part_gap / comparison_missing / outside_matrix / number_not_found / no_citation | `mock-compare.txt` |
| verify-cee on mock, `REDUCE_PROMPT=v7`, ask-answer / ask-layout / ask-progress | PASS (see the PR for the final head and folder) | `.verify-runs/` |
| Count phase at gate 8e5172c (`--max-calls 0`) | 42 reused (4 plans, 38 maps), 0 re-maps, 4 new reduce keys: exactly the plan's count | `g-count.head-log.txt` |

## Paid run (4 calls, the only paid calls of #292)
- **Run:** `run-synthesis.ps1 -Phase run -MaxCalls 4`, gate 8e5172c, clean worktree.
- **Settings:** `deepseek-v4-pro` on `/beta`, effort plan off / map low / reduce low, stream on, MAP_PREFIX off, fts,
  as-of 2026-11-17, `corpus-2026-11-19`.
- **When:** Monday 2026-11-23, 23:50-23:59 UTC, off-peak.
- **Calls:** 4 new `deepseek-v4-pro` reduce calls, none failed or retried. The 42 plan and map records were reused
  from `ev272\cache-a` (#272 test B).
- **Cost:** $0.221 for the 4 new calls; the full flow would be $1.252 with the reused records.
- **Baseline:** v5.2, the saved #272 test B records `docs/results/w12-latency/b-fts/raw/Q{5,8,22,24}-reduce-*.json`
  (Saturday 2026-11-21, off-peak, same settings). They were not re-called.
- **Raw records:** `w13-reduce-synthesis/g-v7/raw/Q*-reduce-*.json` (question, version, model, usage, reasoning,
  output) and `g-v7/report.json`. The map and plan records equal the committed b-fts ones and are not copied again.
- **Full tables and every claim text:** `compare.md` (made by `analyze.py`).

| Q | Version | Sentences (claims) | Uncited | Adjacent | part_gap | comparison_missing | number_not_found | Reduce out / reasoning tokens | Reduce $ | Wall s | Tokens/s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Q5 | v5.2 | 26 | 0 | 0 | 0 | 0 | 0 | 7,272 / 4,142 | 0.0195 | 38.6 | 188 |
| Q5 | v7 | 10 | 0 | 0 | 0 | 0 | 0 | 12,295 / 10,995 | 0.0287 | 73.6 | 167 |
| Q8 | v5.2 | 21 | 0 | 0 | 0 | 0 | 0 | 15,146 / 12,596 | 0.0350 | 85.3 | 178 |
| Q8 | v7 | 5 | 0 | 0 | 0 | 0 | 0 | 23,113 / 22,055 | 0.0517 | 138.2 | 167 |
| Q22 | v5.2 | 49 | 0 | 8 | 0 | 0 | 0 | 24,824 / 19,791 | 0.0582 | 131.7 | 189 |
| Q22 | v7 | 11 | 0 | 0 | 0 | 0 | 0 | 29,547 / 27,681 | 0.0675 | 167.6 | 176 |
| Q24 | v5.2 | 70 | 0 | 36 | 0 | 0 | 2 | 27,328 / 17,824 | 0.0692 | 152.7 | 179 |
| Q24 | v7 | 15 | **1** | 13 | 0 | 0 | 2 | 29,141 / 26,028 | 0.0728 | 170.4 | 171 |
| **Sum** | v5.2 / v7 | 166 / 41 | | | | | | 74,570 / 94,096 out | 0.182 / 0.221 | | |

**First sentences (v7):**
- Q5: "Morgan Stanley is investing in technology for its advisors through ongoing investments in its world-class
  platform to support its advisors, a build-out of E*TRADE capabilities, and expansion of its workplace channel, ..."
- Q8: "Schwab and Raymond James both describe their value proposition to independent advisors as a broad platform of
  capabilities plus dedicated support, ... Schwab emphasizes scale, breadth and a custodial support ecosystem ...,
  while Raymond James emphasizes culture and independence ..."
- Q22: "Morgan Stanley (Wealth Management net new assets), Schwab (core net new assets), Edward Jones (net new
  assets), Merrill as reported within Bank of America's GWIM (net client AUM flows), and Raymond James (Domestic
  Private Client Group net new assets) each disclose the metric by quarter under its own definition, ..."
- Q24: "No client-assets-per-advisor figure is directly disclosed by any of the five firms, so that ratio cannot be
  stated for any of them and the side-by-side comparison is not valid." This sentence came back with no chunk ids
  and part_id "", and code flagged it `no_citation`.

**v5.2 first sentences** restate one item each (e.g. Q5: "Morgan Stanley: On the 2Q25 earnings call ..., the firm
says it is making ongoing investments in its world-class platform ..."). None answers the question as a whole.

## Default rule (fixed in the plan), per question
| Check | Q5 | Q8 | Q22 | Q24 |
|---|---|---|---|---|
| Every shown sentence cited (no_citation 0, outside_matrix 0) | pass | pass | pass | **fail** (claim 1) |
| Sentence 1 answers the question | pass | pass | pass (lists who discloses what, no figure) | pass (uncited) |
| No item-by-item restatement: sentences <= 5 + comparison + computation + per-firm figure sentences | **fail**: 10 > 5; sentences 2-10 list items | pass: 5 <= 6 | **fail**: 11 > 10, and no synthesis sentence; 5 series + 5 definition sentences | pass on count (15 <= 16), but sentences 11-15 restate definition items |
| No more part_gap / comparison_missing / number_not_found than v5.2 | pass | pass | pass | pass (2 = 2) |
| Not invalid or cut | pass | pass | pass | pass |

**Decision by the rule: not adopted.** `REDUCE_PROMPT` stays `v5.2` by default; v7 ships behind the flag. The
30-question scored run is not proposed.

## Findings
- **Shorter answers, a direct opening.** The claim count fell 75 % (166 to 41), and each first sentence speaks to the
  question as a whole, which no v5.2 opening does. Q8 is what the issue asked for: 5 sentences, a cross-firm
  comparison first, each firm in its own terms (custody vs independence kept apart, Q8's passes_if).
- **The coverage rule turns into lists.** "Every holding cell cited" plus "keep asked figures" lets the model write one
  long list sentence per cell (Q5 sentences 2-10, Q22 and Q24 per firm). Q22 has no cross-firm sentence at all. The
  issue asked for 2-4 synthesis sentences; the model obeys coverage over brevity.
- **Uncited first sentence (Q24).** It is a verdict the model drew from the whole matrix, with no item to cite.
  Code flagged it (ground rule 1 held), but it is the sentence a reader reads first. A verdict sentence needs the
  comparison aspect's items as its citations; the prompt says so for the comparison claim, not for claim 1.
- **Cost and time rose, as #284 predicted.** Output tokens +7 % to +69 % and reasoning +40 % to +165 %: answer text
  fell, reasoning grew (choosing what to merge). Reduce cost $0.182 to $0.221 (+21 %); wall +12 % to +91 % at about
  the same tokens/s (167-176 against 178-189), so this is not the service. The reduce is still about 18 % of these
  four questions' full-flow cost ($1.252).
- **Fewer code flags.** Q22 v5.2 had 8 `adjacent_is_fact` (GWIM flows put in adjacent while the map labelled the
  Merrill cell a fact) and 4 `date_mismatch`; v7 has none. Q24's 8 `date_mismatch` went to 0. Shorter sentences carry
  fewer dates to get wrong. Q22 v7 states GWIM flows as Merrill's cell, matching the map's label; the GWIM caveat
  is added by code.
- **What would need to change** (not done here, no issue opened): require claim 1 to cite the items it rests on; cap
  the synthesis at a fixed count and let the evidence list carry coverage (that is, relax `part_gap` in the
  synthesis form); or write the opening and the synthesis as a short extra block above the v5.2 list.

## v8 (TL decision 2026-11-23: "the time is too long; the answer need not include or list everything")
- **Prompt v8**, brief synthesis form; window and all-recency questions keep v5.2:
  - claim 1 answers directly and must cite;
  - at most 5 short sentences in total (aim for 35 words or fewer), with no lists inside a sentence;
  - only the most important evidence, because the evidence list under the answer shows every item;
  - the one comparison sentence per comparison aspect stays.
- **Code, v8 only:**
  - A holding cell the answer does not cite gets no part gap (`part_coverage` state `evidence_list`). Every fact
    cell's items are evidence lines; tested in `test_every_uncited_holding_cell_is_in_the_evidence_list`.
  - Each `COMPUTED` / `NOT_COMPUTED` statement goes to `Answer.computations`, shown as a "Computability" box next to
    the caveats, with footnotes. This happens always, also when a model sentence states the verdict (tested).
- **Derivation proposals.** None of the four questions' #272 matrices has a derivation proposal: not Q5, not Q22,
  not Q24 (and not Q8). v5.2's `code_computability` was empty for all four too. So no Computability box appears in
  these runs. No matrix in the mock eval has one either, so verify-cee cannot drive the box on mock. It is proven by
  tests: the Q24-shaped matrix gives a `NOT_COMPUTED` box citing both inputs and the population source, and the page
  draws it with a resolving footnote.

### Checks before the paid calls (0 calls)
| Check | Result | Evidence |
|---|---|---|
| pytest | 1217 passed at gate 1718230 (7 v8 tests added) | - |
| Mock fts Q1-Q30, rule and #272 plans: v5.2 vs main | 30/30 identical on both | `m8-compare.txt` |
| Same, v8 vs v5.2 | Q26, Q27 byte-identical; 0 new flag kinds; 0 higher watched counts | `m8-compare.txt` |
| Mock claim counts | <= 5 everywhere except Q19 (5 + the code hand-off of a boundary answer) and Q26 (list form, v5.2) | `m8-*` reports |
| verify-cee on mock, `REDUCE_PROMPT=v8` | ask-answer, ask-layout, ask-progress PASS; Q5, Q8, Q24 log v8, Q26 v5.2; box step 0 = 0 logged (`.verify-runs/20261123-184714-1718230`) | - |
| Count phases at gate 1718230 | `low`: 42 reused + 4 new reduce keys; `off`: 42 reused + 4 new (= plan) | `g8-count-*.head-log.txt` |

### Paid runs (8 calls)
- **Runs:** `g8-low` (reduce effort `low`, cap 128000) and `g8-off` (thinking off, streamed cap 64000), both with
  `run-synthesis.ps1 -ReducePrompt v8 -MaxCalls 4`, gate 1718230.
- **When:** Tuesday 2026-11-24, 02:25-02:37 UTC, **peak** pricing. The TL said not to wait for off-peak (about CNY 2 of
  difference on 8 calls).
- **Calls:** 8 `deepseek-v4-pro` reduce calls, none failed. The plan and map records were reused.
- **Cost:** `low` $0.267, `off` $0.013, both at peak price.
- **v5.2 and v7 rows** are the saved records (off-peak, 2026-11-21 and 2026-11-23). Their tokens/s (167-189) are not
  like-for-like with the peak runs (50-94).

| Q | Run | Sentences | Sentence 1 cited | Rule | Reduce out / reasoning tokens | Reduce $ | Wall s | Tokens/s |
|---|---|---|---|---|---|---|---|---|
| Q5 | v5.2 | 26 | yes | - | 7,272 / 4,142 | 0.0195 (off-peak) | 38.6 | 188 |
| Q5 | v7 | 10 | yes | fail: 10 sentences, 7 over 45 words | 12,295 / 10,995 | 0.0287 (off-peak) | 73.6 | 167 |
| Q5 | v8-low | 4 | yes | pass | 990 / 610 | 0.0121 (peak) | 14.6 | 68 |
| Q5 | v8-off | 4 | yes | pass | 383 / 0 | 0.0019 (peak) | 7.7 | 50 |
| Q8 | v5.2 | 21 | yes | - | 15,146 / 12,596 | 0.0350 (off-peak) | 85.3 | 178 |
| Q8 | v7 | 5 | yes | fail: 5 over 45 words | 23,113 / 22,055 | 0.0517 (off-peak) | 138.2 | 167 |
| Q8 | v8-low | 3 | yes | pass | 2,120 / 1,771 | 0.0197 (peak) | 24.7 | 86 |
| Q8 | v8-off | 5 | yes | pass | 443 / 0 | 0.0023 (peak) | 6.0 | 74 |
| Q22 | v5.2 | 49 | yes | - | 24,824 / 19,791 | 0.0582 (off-peak) | 131.7 | 189 |
| Q22 | v7 | 11 | yes | fail: 11 sentences, 5 list sentences | 29,547 / 27,681 | 0.0675 (off-peak) | 167.6 | 176 |
| Q22 | v8-low | 5 | yes | pass | 20,181 / 19,684 | 0.0979 (peak) | 259.7 | 78 |
| Q22 | v8-off | 5 | yes | pass | 558 / 0 | 0.0029 (peak) | 5.9 | 94 |
| Q24 | v5.2 | 70 | yes | - | 27,328 / 17,824 | 0.0692 (off-peak) | 152.7 | 179 |
| Q24 | v7 | 15 | no | fail: sentence 1 uncited, 15 sentences | 29,141 / 26,028 | 0.0728 (off-peak) | 170.4 | 171 |
| Q24 | v8-low | 1 | yes | pass | 27,064 / 25,972 | 0.1373 (peak) | 343.0 | 79 |
| Q24 | v8-off | 5 | yes | **fail**: comparison_missing 0 -> 1 (no sentence with the comparison aspect's id) | 1,154 / 0 | 0.0058 (peak) | 14.0 | 83 |

Flags in the v8 answers: number_not_found is in adjacent items only, Q24 `low` 2 and `off` 1 (v5.2 had 2). Q22 `off`
has 1 `adjacent_is_fact` (v5.2 had 8). There are 0 part_gap and 0 outside_matrix. Full texts and flags:
`compare-v8.md` (made by `analyze.py`).

**Q24, where the comparison is invalid and why** (the plan's extra item):
- `low`: its one sentence, "Client assets per advisor cannot be validly compared across the five firms, because their
  advisor-headcount and client-asset measures are each defined differently", carries part_id `a4` (the comparison
  aspect). It cites 9 chunks, the client-asset and headcount items of all five firms. Pass.
- `off`: it states the same verdict under part_id `a1`. Code found no comparison claim and added the
  `comparison_missing` gap. Fail.

### Default decision (plan rule)
- **v8 becomes the default:** all four questions pass at `low`.
  - Code: `REDUCE_PROMPT_DEFAULT = "v8"`.
  - Tests that pin v5.2 behavior now set `REDUCE_PROMPT=v5.2`.
  - Window and all-recency questions keep v5.2.
- **Reduce effort `off` is not proposed:** it failed Q24. It is still the clear latency lever, at 6-14 s per reduce
  against 15-343 s at `low`. Q22 and Q24 at `low` still reason about 20-26k tokens: v8 fixed the answer length, not
  their reasoning.
- **Gate 3 proposed:** a 30-question scored run on v8 needs the TL's go-ahead (the PR asks for it). A follow-up could
  test `off` with a code-side comparison fallback, because the miss was a part_id, not the content.

### Findings (v8)
- **Length.** v8 writes what the issue asked for: 1-5 sentences, the first one cited and answering the question. There
  are no list sentences and no sentence over 45 words (v7: 2-7 per question).
- **Reasoning depends on the question.** At `low`, Q5 and Q8 reasoned 0.6k and 1.8k tokens, against 4.1k and 12.6k
  for v5.2. Q22 and Q24 still reasoned 19.7k and 26.0k: the model still reads the whole matrix to choose.
- **Q24 `low` gives a one-sentence answer.** It is the comparison verdict, which is what the question's second half
  asks. The asked figures are only in the evidence list.
- **Q22.** At `low`, it opens with a non-comparability verdict and states 3 firms' latest figures. At `off`, it states
  4 firms' latest figures. Neither gives "by quarter" in the answer text; the evidence list carries the series.
