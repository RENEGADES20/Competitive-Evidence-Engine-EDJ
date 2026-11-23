# 0285 - Facts table: metric figures extracted once at ingest, served by SQL at query time

Issue: #285    Role: TL    Spec: specs/filings.md, specs/answer-citations.md    Design: ADR-022 (`docs/DECISIONS.md`, Proposed), `docs/results/w13-facts.md`

## Goal
Advisor headcount, net new assets and client assets are extracted once from the corpus by a model, code-checked, and
stored as data (`config/facts.jsonl` -> table `facts`). At query time a map cell that asks exactly one of these figures
for one firm is built by code from SQL, with no LLM call; every other cell runs the LLM map as today. Map calls and $
per question drop, critical-path p50 does not rise, adjudicated quality stays >= 24/30 (#272 test B: 24/30, $0.519/q
off-peak, p50 184 s, 454 map calls).

## Design (fixed before any call; numbers from the #272 records, 0 calls: `docs/results/w13-facts.md` "Estimate")
- **Storage, and main without a model (ADR-022).** Extraction is an offline ingest script, run once per snapshot or
  extraction version as a planned paid run. Its checked rows go to `config/facts.jsonl` (git, versioned); `cee.facts load`
  fills the `facts` table (schema + `db/upgrade.sql`) from it, run by `sync-db` and `ingest` (.ps1 + .sh) and so carried
  into the next snapshot. Query time is SQL + code only; the mock provider and tests read the same rows. No table or no
  rows -> every cell takes the LLM map (logged). Setting `FACTS=on|off`.
- **Rows** (entity and segment from the chunk, never the model): entity, segment, metric, label (the firm's words), scope,
  period (date / `YYYYQn` / `FYYYYY`), period_end, period_type, value (verbatim), value_num, unit, basis key (code:
  metric + label + scope), quote, chunk_id, doc_id, extract version, model. Kept only if: value is a substring of quote
  and quote of the chunk text (whitespace squashed), the model's firm = the document's entity and its segment = the
  chunk's (or empty), period parses. Failing rows are dropped and counted, never stored.
- **Target metrics from the data.** In the #272 plans, 95 cells name a target metric and got a figure from the map. Rule:
  a metric is targeted if registered (advisor_headcount, net_new_assets) or asked as a figure in >= 2 questions:
  client_assets (Q14, Q21, Q24). Revenue lines (only Q15) and attrition (only Q28) are not; gaps explained in the doc.
- **Serving rule (code, `config/facts.yaml`).** A cell is facts-served only if: firm row (not research / theme), aspect
  kind fact / series / recency, not proxy, the aspect text names the metric's figure and none of the non-figure words
  (define, include, exclude, disclose, how, why, strategy, attributable, recruit, retention, attrition, projected,
  mix, per, revenue, fee, rate, across / by model ...), and the SQL lookup returns >= 1 row (series: >= 2 periods). On the
  reused #272 plans that is 33 cells (Q3, Q4, Q7, Q11, Q22-Q24, Q26, Q27); the list is in the results doc. Empty
  lookup -> LLM map, so "not disclosed" / closest-figure cells (SCHW headcount, Merrill since 2023) stay with the model.
- **Lookup = a SQL retrieval pass** with the sub-question's own hard filters (the `fts` builders: entity + Merrill segment,
  window on `published_at`, Ask-page filters, doc-type scope). Its chunks join that sub-question's retrieved set (origin
  `facts`), so items cite only retrieved chunks. Selection: one row per basis and period (newest document first);
  series: the asked periods (last N quarters / years) if named, else the last 8; fact / recency: the latest per basis.
- **#283 lesson: LLM cells see exactly what they saw before.** Covered cells are removed *after* `fan_out`; the firm's
  groups, shared passages and allowed sets are untouched, so every uncovered request is byte-identical with `FACTS` on
  or off (test). Facts chunks are never put into any map message.
- **Log**: cells get `source=facts`; `counts()` and the run report give facts-served vs LLM cells per question.

## TL conditions (review round 1, issuecomment-7098594448 + TL rulings; binding, override the Design above)
- **B1 complete, not stale.** Series: served only if every asked period (`asked_periods`) is among the rows, else
  the whole cell -> map. Every served cell (series, fact, recency): no document in the sub-question's own SQL-filtered
  pool whose chunk matches the metric prefilter is newer (`published_at`) than the newest served row's document.
  Gate 5c per cell: the #272 map's newest-period figure and full period set must be among the served items; misses listed.
- **B2 registry.** Served only when the (entity, metric) registry status is `quoted` and the row's basis matches the
  registered basis (`config/facts.yaml`: label phrases per registered basis, scope empty). So SCHW headcount and NNA,
  BAC NNA are never served (test); client_assets (unregistered) is extracted but not served. 5b compares labels with #272.
- **B3 positive rule.** The planner's `a.metric` in the target set AND kind fact/series/recency AND not proxy AND no
  non-figure word in the aspect text, `sq.text` or the question (list extended: growth, change, trend, driver, reason,
  because, outlook, guidance, target, goal, expect, forecast, explain, impact, organic, acquisition, commentary, ...).
  Adversarial tests expect the map. The results doc lists every metric-named cell not served, with the reason.
- **B4 placement.** The lookup runs after `fan_out`; facts chunks go only into `by_id` (after round 2), `m.hits`,
  `m.pools`, never into `hits`, `used` or `plan.pools`. Byte-identical test + 5b replay: round-1 cell requests,
  shared-prefix messages and remap requests, FACTS on vs off, on the stage-1 questions plus Q3 and Q26.
- **B5 item fields.** `Item.scope` = "" (only whole-basis rows are served); `definition` = ""; `population` set by
  `tag_populations` as for map items; `text` = label + value + unit + period. 5b diffs `m.caveats`, `gaps`, `breaks`,
  cell flags and comparability marks between matrices from the saved #272 map outputs and the facts-served ones;
  every difference explained before any paid answer call.
- **B6 independent check.** Every served item is re-verified by SQL through the `fts` filters (chunk exists; entity +
  Merrill segment via `entity_filter`, never `facts.entity`; `published_at` in window; doc type in scope) and its value
  and quote again against the chunk text. Report the share of served chunks already in the plan's retrieved set. Tests:
  a Merrill cell never gets a non-GWIM BAC row; an EDJ cell never gets another firm's row.
- **B7 pass rule (TL, reinterprets the issue's "$ and p50 not higher").** Expected effect is within provider drift.
  Pass for cost/speed: map calls per question strictly lower, and map-stage $ (off-peak) lower. Total $/q and
  critical-path p50 are reported against #272 with drift explained by the speed leg. S3 / S4 read map-stage $ and wall.
- **G0 go/no-go (TL).** After the extraction and all 0-call gates, before any paid answer call: recompute coverage on the
  #272 records under these rules. Map calls saved over Q1-Q30 < 15 -> STOP: ship `FACTS=off` by default with table,
  loader and code merged, record the finding; no stage 1 or 2. >= 15 -> stages 1 and 2 (list re-derived at count phase).
- **Non-blocking, accepted.** CLAUDE.md: only the facts table lands on `main` as ingest extraction; S1 and S6 apply in
  stage 2 too; extraction stops at > 10% failed / invalid calls or $3; period end not after `published_at` (and equal to
  the document's `period_end` when set for a point/quarter row of that period type) and a unit word in the chunk or
  prefix; estimate labelled an upper bound with per-item membership; input tokens reported; `FACTS` default stated
  (on only if G0 and Gate 3 pass), mock/CI read `config/facts.jsonl`, RUN.md blocks for both OSes; ADR-022 Accepted at merge.

## Files to change
- `db/schema.sql`, `db/upgrade.sql`, `config/facts.yaml` (metrics, phrases, words, doc types), `config/facts.jsonl`.
- `src/cee/facts.py` (extract prompt/schema/checks, load, lookup, serving rule), `src/cee/answer/extract.py` (`run_map`),
  `src/cee/answer/matrix.py` (counts), `src/cee/config.py`, `scripts/extract_facts.py`, `scripts/sync-db.*`, `ingest.*`,
  `scripts/eval_run.py` + `latency_report.py` (facts counts, tokens/s), `.env.example`, `docs/RUN.md`.
- Tests: `tests/test_facts.py` (+ touched `test_extract.py`, `test_eval_run.py`). Docs: `docs/DECISIONS.md` (ADR-022),
  `CLAUDE.md` invariant, `docs/ARCHITECTURE.md`, `specs/answer-citations.md`, `specs/filings.md`, results doc + run scripts.

## Steps
1. Mock baseline from clean `main` (Q1-Q30 fts, rule plans and #272 plans). 2. Schema, loader, lookup, serving rule,
`run_map` hook; tests. 3. Extraction script, mock-tested with a fake client. 4. Extraction run (paid), code checks, load.
5. Offline gates (0 calls): (a) 100% of rows pass the checks; (b) replay the #272 plans on mock: covered cells, rule
checks, uncovered requests identical to step 1; (c) golden: on the covered #272 cells, the map's figures (value + period,
from candidate chunks) found among the served items >= 90%, misses read and listed. Fail -> stop, report, no paid run.
6. Audit sample: 50 random rows (seeded) with chunk text for the coordinator's Sonnet auditor. 7. verify-cee on mock
(ask-answer, open-citation on Q23). 8. Staged real run. 9. Blind inputs (`dump272.py` + `split_parts.py`), results doc,
`/finish-task`. I do not score or audit.

## Acceptance
- [ ] pytest green (CI); mock Q1-Q30 not worse than baseline; uncovered map requests byte-identical (test + replay).
- [ ] 100% of stored rows pass the checks; audit 50 rows >= 48 correct (coordinator's auditor).
- [ ] Coverage of #272 metric cells reported with gaps explained (estimate 28/95, 28 of the 33 servable).
- [ ] G0: map calls saved on #272 under the TL rules >= 15, else stop with `FACTS=off` default (finding recorded).
- [ ] If G0 passes - real fts Q1-Q30: map calls/q strictly lower, map-stage $ lower (B7); total $/q and p50 reported
  with the speed leg; adjudicated >= 24/30.
- [ ] B6 SQL re-check passes for every served item; 5b caveat/gap/break/flag/mark diff explained.
- [ ] verify-cee mock: ask-answer and open-citation PASS on a facts-served answer. ADR-022 Accepted; CLAUDE.md updated.

## Paid calls (TL go-ahead 2026-11-22, incl. Gate 3). deepseek-v4-pro, map stage settings, off-peak only
- **Extraction**: 76 calls, one per document holding candidate chunks (719 chunks of 10-K, 10-Q, supplement, press,
  monthly, deck; trade, transcripts and ADV excluded), ~370k input + ~270k output tokens, ~$0.8 (cap $3). Once; no repair.
- **Stage 1**: Q4, Q7, Q11, Q22, Q23, Q24, Q27 (every question with a covered cell), once. #272: 125 non-plan calls;
  expect ~96 (plans reused from `ev272\cache-a`, 0 plan calls). **Stop rules** (any -> stop, report, coordinator decides):
  S1 any served item fails a rule check; S2 map calls on these questions not below #272's; S3 $ off-peak not below
  #272's for them; S4 critical-path p50 on them > 1.10 x #272's; S5 a behavior differs from #272; S6 reduce output
  tokens mean > 1.15 x #272 (the #284 lesson).
- **Speed leg (0 extra calls)**: the run's map calls whose request key equals a #272 record (uncovered cells; checked
  on mock first) give tokens/s and wall against #272, reported next to every wall time; it explains S4 / p50 drift.
- **Stage 2**: the other 23 questions, once (#272: 390 calls). Total ~562 calls, ~$15.5 off-peak. `--max-calls` from
  the 0-call count phase. Every raw record saved under `D:\ALLPROJECTS\EDJ\cache\ev285\`; no re-rolls.

## Risks
- Small effect: ~6% fewer calls, $0.519 -> ~$0.49/q, p50 184 -> ~175 s estimated; provider speed drift (#283: reduce
  126 -> 158 s) can hide it, hence the speed leg. A served series may miss a period the map would find: gate 5c.

## Progress log
- 2026-11-23 04:45 - plan written; worktree `wt-285` on `tl/285-facts` from origin/main cda5ebf (#287 merged). 0 calls.
- 2026-11-23 - review round 1 CHANGES REQUESTED; TL rulings folded in as "TL conditions" (B1-B7, G0, non-blocking).
  Build starts. Expectation, 0 calls: the question-text words leave few servable cells (Q23, Q26), so G0 may stop.
