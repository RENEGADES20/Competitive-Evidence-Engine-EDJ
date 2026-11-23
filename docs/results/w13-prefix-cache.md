# W13 map prefix cache: shared firm prefix, one tool schema, leader-first gate (#283), fts

**Map cache-hit share 59.7% of map input (followers 89.4%, leaders 2.4%, over-ceiling per-cell calls 3.5%), up from
3.8% in #272 test B.** All 548 records: 58.3% (#272: 4%).
**Cost, like for like** (the same 30 answers' records re-priced at one tier, `cost.md`): off-peak **$0.398 per
question vs $0.519 (-23%)**; peak $0.796 vs $1.037. As billed $0.562 per question ($16.85): this run crossed into the
peak window (06:00 UTC), #272 was all off-peak.
**Latency: critical path p50 272 s, p90 470 s, max 586 s vs #272 184 / 251 / 3,750 s; follower gate wait p50 7.7 s.**
Acceptance "p50 <= 184 s + gate wait" is not met. DeepSeek's output speed was lower in this run (map 96 vs 138
tokens/s, reduce 121 vs 187 tokens/s at p50, measured after the first token), and the reduce, which #283 does not
change, went from 126 s to 158 s p50 with fewer output tokens; the provider slowdown and the layout cannot be told
apart from this one run.
**Cell check (TL condition B3) trigger: YES on both rules** (labels changed 18.0% > 10%; unmatched_citation 2.43% of
items vs 0.07%, > 2x). Before any score is read: **the shared-prefix layout is the suspected cause** of the cell
changes (each cell now sees its siblings' passages it may not cite).
**Scores: blind and adjudicated: pending** (fresh Sonnet scorers launched by the coordinator; the PR reviewer
adjudicates). Gate: adjudicated >= 24/30.

## How this was run

- Plan `plans/0283-prefix-cache.md` with the TL conditions of review round 1 (issuecomment-7091445276). Code under test:
  `tl/283-prefix-cache` gate 8f36b7d from the clean worktree `wt-283run`; run script `w13-prefix-cache/run-prefix.ps1`
  (`.sh` twin), every setting pinned: snapshot `corpus-2026-11-19`, as-of 2026-11-17, `deepseek-v4-pro` on `/beta`,
  #272 C1 (plan off, map low, reduce low, streaming, `MAP_CONCURRENCY=24`, `MAP_CALL_TOKENS=60000`), reduce `v5.2`,
  `PYTHONHASHSEED=0`, `MAP_PREFIX_TOKENS=150000`, `MAP_PREFIX_GATE=first_chunk`, `MAP_PREFIX_WAIT_S=5`. Extract
  `extract-v1.3`; map request version `ds-strict-2-map-low-c128000-s1-pf150000`. Plans reused from #272
  (`--reuse-plans deepseek:deepseek-v4-pro@ds-strict-2-plan-off-c8000-s1`), so the cells are the same as #272 test B.
- Mock checks before any call (0 calls): pytest 1192 passed; mock Q1-Q30 fts 30/30 identical to clean `main` with
  rule plans and with the #272 plans (`w13-prefix-cache/mock-compare.txt`).
- Q10 probe (TL condition B4), 2026-11-23 04:42 UTC (off-peak): 41 new calls, $0.67. Follower share of the prefix
  0.929 over 25 followers (>= 0.50) -> `first_chunk` kept (`probe/latency.md`). Q10 was reused by key in the full run
  and keeps its probe timings.
- Full run, 2026-11-23 04:54-07:16 UTC: `--max-calls 854` from the 0-call count. Exit 0, no interruption, cut 0,
  invalid 0, failed 0. No output was re-rolled.

## Cache hits (`b-fts-latency.md`)

| Calls | n | input tokens | cache-hit tokens | hit share | gate wait p50 / max s |
|---|---|---|---|---|---|
| map | 442 | 25,297,981 | 15,100,416 | 0.597 | 7.4 / 20.0 |
| map follower | 257 | 16,574,886 | 14,826,112 | 0.894 | 7.7 / 20.0 |
| map leader | 55 | 3,222,931 | 76,800 | 0.024 | 0 |
| map cell (firm over 150k: per-cell layout) | 123 | 5,357,518 | 186,752 | 0.035 | - |
| map solo | 7 | 142,646 | 10,752 | 0.075 | - |
| re-map / reduce / plan | 46 / 30 / 30 | 306,229 / 506,056 / 40,087 | | 0.186 / 0.099 / 0.805 | - |

The measured ceiling of this design is set by the leaders (one full miss per firm) and the firms over the ceiling
(all-sources groups of Q16, Q17, Q18, Q20; Q15 RJF; Q21 MS, RJF, SCHW; plus 5 research calls: 123 calls, 21% of
map input, almost no hits). Map input grew 15.66M -> 25.30M tokens (each
cell reads its firm's whole block).

## Cost (`cost.md`, prices `config/pricing.yaml`)

| Part | #272 off-peak $ | #283 off-peak $ | #283 tokens |
|---|---|---|---|
| map input cache-hit | 0.01 | 0.33 | 15,100,416 |
| map input cache-miss | 9.94 | 6.73 | 10,197,565 |
| map output | 3.87 | 3.27 | 1,652,835 |
| re-map (all) | 0.16 | 0.21 | |
| reduce (all) | 1.55 | 1.36 | |
| plan (all) | 0.04 | 0.04 | |
| **total, 30 answers** | **15.56 ($0.519/q)** | **11.95 ($0.398/q)** | |

All peak: #272 $31.12 ($1.037/q), #283 $23.89 ($0.796/q). As billed (each call at its own period): #272 $15.56 (545
off-peak calls); #283 $16.85 (320 off-peak, 228 peak). Map alone: $13.82 -> $10.33 off-peak (-25%).

## Latency

| | #272 test B | #283 |
|---|---|---|
| critical path p50 / p90 / max s | 184 / 251 / 3,750 | 272 / 470 / 586 |
| slowest map call per question, p50 s | 67 | 86 (incl. gate wait) |
| reduce p50 s | 126 | 158 |
| first evidence p50 / p90 s | 18 / 30 | 22 / 43 |
| output tokens/s after first token, map / reduce p50 | 138 / 187 | 96 / 121 |

Per question tables: `b-fts-latency.md`. Questions run later in the session (Q17-Q27, after 06:00 UTC) are the
slowest; map output speed by hour (Chicago): 22h 105, 23h 106, 0h 79, 1h 68 tokens/s.

## Cell comparison against #272 (TL condition B3, `cmp-cells.md`, 0 calls)

422 model cells in both runs. Labels changed: 76 (18.0%): fact -> not_found 26, not_found -> fact 13,
different_quantity -> not_found 12, fact -> different_quantity 10, not_found -> different_quantity 6,
different_quantity -> fact 6, fact -> not_disclosed 3. Items: 2,884 -> 2,307; items lost in 275 cells, gained in 213.

| Rate per item | #272 | #283 |
|---|---|---|
| unmatched_citation | 2 / 2,884 (0.07%) | 56 / 2,307 (2.43%) |
| quote_not_found | 577 (20.0%) | 517 (22.4%) |
| number_not_found | 28 (0.97%) | 28 (1.21%) |
| cells with unknown_ref / foreign_cell / unknown_cell | 0 / 0 / 0 | 3 / 0 / 0 |

Trigger fixed in the plan: YES (both rules). The layout is the suspected cause: the model cites sibling passages it
may not cite (rejected by code, never silently dropped) and returns fewer items, more often `not_found`. Q29 now
returns `answer` (expected `gap_with_adjacent`; #272: invalid).

## Scores

Pending. Inputs `D:\ALLPROJECTS\EDJ\cache\ev283\blind-in-fts\` made the #272 way: `answers-dump.txt` (dump272.py:
every claim with each cited passage), split by range into `answers-partA..D.txt` (Q1-Q10, Q11-Q16, Q17-Q21,
Q22-Q30), `questions.yaml`, the #250 `verdict-rule.txt` (same sha256 as #272); hashes `blind-in-fts-hashes.txt`.

## Calls

Probe 41 new calls ($0.67, off-peak). Full run 477 new calls ($16.15 as billed; 71 records reused: the 30 #272
plans and the 41 Q10 probe records). **Total new for #283: 518 calls, $16.81.** The 30 answers use 548 records (30
plans, 442 map, 46 re-map, 30 reduce); as billed they cost $16.85 (the reused plans at their #272 price).

## Findings

1. The shared prefix works where it applies: followers hit 89% of their input. The cost drop (-23% like for like) is
   capped by leaders and by the firms over the 150k ceiling.
2. Cells change more than the trigger allows. Seeing the whole firm block costs citation discipline (unmatched 35x)
   and items. The score decides whether this matters for answers.
3. Latency is worse, but the reduce, untouched by #283, slowed by the same factor: provider throughput was lower in
   this session. A like-for-like latency read needs both layouts in one session (follow-up, not run).

Evidence: `docs/results/w13-prefix-cache/` (raw records and reports of the probe and the full run, head logs,
latency, cost and cell comparison, mock compare, run scripts); working copies `D:\ALLPROJECTS\EDJ\cache\ev283\`.
