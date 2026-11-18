# 0203 - Gate 4 retrieval fix: answer turns, vocabulary, multi-word metric phrases

Issue: #203    Role: TL    Spec: specs/retrieval.md (S1 area; the TL owns teammate files, #187 comment)

## Goal
Passages the corpus holds, and that Gate 4 R1 (#121) answered "not in the evidence" without,
reach the retrieved set of their questions through deterministic retrieval changes on `main`
(ADR-011: no model in retrieval). Each change keeps the SQL filters (entity, segment, time window,
doc-type scope, Ask page filters) and the per-firm quotas, and is a general rule or vocabulary
entry, never a rule for one question.

## Diagnosis (2026-11-18, read-only, DB `cee` = `corpus-2026-11-17`, `main` a886741, as of 2026-11-17)
Probe scripts `diag203.py`, `proto203.py`, `group203.py`, `probes203.py` kept in
`D:\ALLPROJECTS\EDJ\cache\ev203\probes\` (run from the worktree root with PYTHONPATH=`wt-203\src`);
config mutated in memory only.

| Q | Named passage | Why it misses today | Lever that reaches it (probe) |
|---|---|---|---|
| Q6 | `RJF-TR-2026Q1#46` (CEO: "pretty good uptick in the employee affiliation option") | The analyst's question turn `#45` (same words: affiliation, mix shift) is kept; the answer turn is a second chunk of the same call, so new-document-first gives the slot to other calls (rank 24 at k=80) | L1 answer turn comes with its question turn |
| Q13 | `MS-TR-2025Q4#20` ("Advisor-led assets originating from workplace and E*TRADE relationships accelerated") | Matches only client, manag(ement), workplace; "convert", "participants", "stock-plan" never appear. Not in the pool (59 hits). `MS-TR-2026Q1#24` ("channel migration") likewise. Also: the key `stock plan` never fires on "stock-plan" | L2c `convert` -> "channel migration"; `workplace` -> "originating from workplace", "workplace channel": both in (probe D) |
| Q17 | `MS-TR-2025Q3#8` ("LeadIQ, our AI-powered lead distribution platform") / `MS-TR-2025Q4#35` | Only "AI" and "firm" match; question words "saying", "claiming", "delivery" do not | L2c `AI` += "AI-powered", "AI-enabled", "AI tools", "AI-driven": `MS-TR-2025Q3#8` in (rank 4) |
| Q22 | `EDJ-10Q-2026Q2#60` (table row "Net new assets for the period ($ billions)") / `EDJ-10Q-2026Q1#66` | The question's own phrase "net new assets" is a synonym key, but only its values (NNA, core net new assets) are phrase probes; the table row scores three common words and loses to prose with "definition", "firm", "metric" (rank 69) | L2b a multi-word key is also searched as a phrase: `#60` in (rank 2) |
| Q2 | `RJF-PR-web-affiliation-options#1` (payout per model) | Matches only "advisor"; "recruit", "wirehouses" never appear in it. Even with `recruit` -> "payout", "affiliation options" it reaches the press pool (5th of RJF press) but its own page's `#0` (header + choice/autonomy list) ranks higher, so the page is already in the list and `#1` waits behind other press documents (rank 43 at k=80) | L2c `recruit` synonyms; expected **not** reached, see "Can't reach" |
| Q20 | `FIDELITY-III-2025#0` / `UBS-NEXTGEN-2026#81` | Theme mode, no firm named: research is one group among seven and gets 3-4 of 20 slots; among the 751 research chunks that match, `UBS#81` ranks 53 and `FIDELITY#0` 59 even with `under 40` synonyms (Cerulli, BofA and UBS `#83` rank first). `FIDELITY#0` is not tagged `younger_investors` (tagger has no "next generation" keyword; a re-tag is a corpus change) | L2c `under 40` synonyms only; expected **not** reached, see "Can't reach" |

Lever 3 of the issue (rank table rows that carry the asked metric) is not needed for Q22 once
L2b is in (probe: `#60` rank 2). It is built only if the full mock run shows Q22 losing `#60`
again; then it is designed and measured in a plan update before any code.

## Levers (chosen)
- **L1 Answer turn with its question turn (selection rule, ADR-017).** Transcript chunks only.
  A kept chunk is a *question turn* when it holds an operator hand-off ("Operator"/"Moderator"
  paragraph, Bloomberg "Q - " label) or its last paragraph ends with "?". Its *answer turn* is the
  next chunk of the same document (`seq + 1`) when that chunk is not itself a question turn.
  `search()` fetches the answer turns of the question turns in the pool with one SQL query that
  carries every hard filter of the main pass (entity/segment, window, date range, keywords,
  doc-type scope) but no word match: an answer turn the filters exclude (a BAC consumer turn in a
  Merrill question, an out-of-window call) never comes in. In `select()` the answer turn is kept
  right after its question turn, in the same firm's turn, subject to MAX_PER_DOC, near-duplicate
  removal and k. Variants measured: `attach` (both kept, the answer takes the next slot) and
  `replace` (the answer takes the question's slot). Default `attach`; `replace` only if `attach`
  costs a PASS. Module-level switch `PAIR_TURNS` like the other slot rules (#198).
- **L2 Vocabulary (`config/entities.yaml` + `expand_synonyms`/`_tsquery_sql`).**
  - L2a: a synonym key matches the question with a hyphen or a space between its words
    ("stock-plan" fires `stock plan`), and a lower-case key's last word also matches with an
    inflection (s, es, ed, ing: `recruit` fires on "recruit", "recruiting", "recruits").
    All-caps keys keep exact case and whole-word match (the "FA" vs "FAs" test stays).
    `_synonym_pattern` also strips the `synonym_only` words (`pay`) from the full-text words in
    `keyword_terms`, so with L2a "pays"/"paying" are stripped too. That is consistent (the
    stemmer folds them to "pay", which is searched only through its synonyms anyway); a unit
    test pins it. Fallback (TL choice): if L2a/L2b brings a payout-grid chunk into gap question
    Q25, `compensation structure` is excluded from inflection matching, so Q25 stays a clean gap.
  - L2b: a multi-word key found in the question is searched as a phrase too (its adjacency counts
    as one probe with its own IDF), next to its values. Keys like `net new assets`,
    `advisor headcount`-type metric names are what a benchmark question asks for.
  - L2c: new entries (key -> values, never back):
    `recruit` -> "hiring", "transition assistance", "forgivable loans", "payout",
    "affiliation options" (the existing `recruiting` key is folded in; Q7 "recruiting" still fires);
    `convert` -> "channel migration"; `workplace` -> "originating from workplace",
    "workplace channel"; `AI` += "AI-powered", "AI-enabled", "AI tools", "AI-driven";
    `under 40` -> "next generation", "younger investors", "younger clients", "millennials",
    "Gen Z". Each entry is a firm/industry wording for the asked concept, commented with the
    question IDs it was found on, as the existing entries are. Entries that cost a PASS in the
    full run are dropped, not tuned per question.

## Can't reach (expected; confirmed or revised by step 5)
- **Q2 `RJF-PR-web-affiliation-options#1`:** the page is in the list through its `#0` (affiliation
  choice and "true autonomy" per model); `#1` is a second chunk of a press document, and
  new-document-first (ADR-016) gives RJF's 3-4 press slots to other documents first. Reaching it
  needs either a second chunk per document ahead of new documents (reverts #199 for Q6/Q11/Q13/Q27)
  or ignoring the page's provenance header in ranking (probed: `#0` still outranks `#1`). Neither
  is a general fix inside this issue; recorded for #121 known gaps and `docs/NEXT.md`.
- **Q20 `FIDELITY-III-2025#0` / `UBS-NEXTGEN-2026#81`:** ranked 59 / 53 of 751 matching research
  chunks; the research part of a theme question gets 3-4 slots. Reaching them needs a different
  research share for theme questions or re-tagging the corpus ("next generation" as a
  younger-investor keyword), a selection-rule change across Q17/Q18/Q20 or a new snapshot; out
  of this issue. Q20 still depends on #204 (behavior: partial evidence -> answer) with the
  UBS `#83` passage it already gets.

## Files to change
- `src/cee/retrieve/fts.py` - L1 (`PAIR_TURNS`, question-turn test, answer-turn fetch in
  `search()`, keep-after in `select()`), L2a/L2b in `_synonym_pattern`/`expand_synonyms`/
  `keyword_terms`. Kept small and in one place each, since #205 edits `fts.py` after this.
- `config/entities.yaml` - L2c entries with question-ID comments; the comment block above
  `synonyms:` (which describes key matching: case, "plurals and verb forms need no entry") updated
  for L2a (hyphen/space, inflected last word) and L2b (a multi-word key is also a phrase).
- `tests/test_fts_synonyms.py` - L2a, L2b, L2c expansions (no DB).
- `tests/test_retrieval_quotas.py` (or new `tests/test_retrieval_turns.py`) - L1 on hand-built
  pools: answer kept after its question; not when it is a question turn itself; not past
  MAX_PER_DOC or k; `replace` variant; a filtered-out answer turn never appears (fake DB as in
  `test_retrieval_themes.py`).
- `specs/retrieval.md` - interface lines for L1 and L2a/L2b; ADR-017 in the header list.
- `docs/DECISIONS.md` - new ADR "Answer turn with its question turn; multi-word synonym keys as
  phrases" (TL-approved, per #121 TL decisions). Written as ADR-017 here; #204 and #205 are
  planned in parallel, so the number is the next free one in `docs/DECISIONS.md` order at merge
  time (renumbered on rebase, with the `specs/retrieval.md` header list and plan text).
- `evals/baselines/corpus-2026-11-17/` - refreshed only if any status moves (issue Deliverable).
- `plans/0203-gate4-retrieval.md` - this plan.
- Not changed: prompt, Answer schema, `evals/questions.yaml`, `evals/expected_chunks.yaml`, corpus.

## Steps
1. **Baselines (mock, 0 calls).** In `wt-203` (PYTHONPATH=`wt-203\src`, PYTHONUTF8=1, venv
   `repo\.venv`), before any edit: `scripts/eval_run.py --as-of 2026-11-17 --baseline
   evals/baselines/corpus-2026-11-17/report.json --out D:\ALLPROJECTS\EDJ\cache\ev203\main-1117`
   and `--as-of 2026-10-29 --out ...\ev203\main-1029`. Expect 28/2 (Q15, Q19), 0 forbidden,
   refusal 5/5 and 19/19, tier-1 doc recall 0.727 at 2026-11-17 (same as `ev121\mock-main`).
2. **L2 (config + matching), tests first.** Unit tests for L2a/L2b/L2c; then the code and config.
   Mock eval at both as-of dates -> `ev203\l2-1117`, `ev203\l2-1029`.
3. **L1 (answer turns), tests first.** Unit tests; then the code. Mock eval `attach` ->
   `ev203\l12-1117`, `ev203\l12-1029`; if `attach` costs a PASS, the same for `replace`.
4. **Named-passage and gap-question check.** A check script (kept in
   `D:\ALLPROJECTS\EDJ\cache\ev203\probes\` with the diagnosis probes) reads each run's
   `report.json` `chunk_ids` and prints:
   - per linked question, which named passages are in the retrieved set;
   - Q4/Q27/Q30: any BAC chunk whose segment is not GWIM/Merrill (must be none);
   - for all 30 questions, the synonym keys that fire on `main` vs the branch
     (`expand_synonyms` on the `keyword_terms` terms), as a per-question diff;
   - Q25 and Q29 (gap): the changed chunk IDs against `ev203\main-1117`, with every retrieved
     chunk whose text contains "payout" listed (ID and the sentence around it).
   All of it goes into the progress log.
5. **Decide and record.** Keep the levers that reach a target without a PASS -> FAIL; drop the
   rest. Update "Can't reach" with measured ranks if a probe was wrong. Per-question diff
   (changed chunk IDs) of the six linked questions and the three traps in the progress log.
6. **Docs.** `specs/retrieval.md` lines, ADR-017, baseline refresh if statuses moved.
7. **Verify.** `pytest -q`; `python -m cee.smoke`; `scripts/verify_cee.py run` (retrieval is
   behind the Ask page, so the `ask-answer` feature run proves the app still answers with
   citations) -> VERIFY PASS. Then `/finish-task` (PR "Closes #203"; review through `/tl-review`
   is run by the TL, not here).

## Acceptance
- [x] Mock eval on `corpus-2026-11-17`, `--as-of 2026-11-17`, app budget (no `--k`): named
      passage in the retrieved set, or explained under "Can't reach" with measured ranks
      (`cache\ev203\final-1117`, `check-final-1117.txt`):
  - [x] Q6: `RJF-TR-2026Q1#46` in (L1, right after `#45`)
  - [x] Q13: `MS-TR-2025Q4#20` in, and `MS-TR-2026Q1#24` (L2)
  - [x] Q17: `MS-TR-2025Q3#8` in (L2)
  - [x] Q22: `EDJ-10Q-2026Q2#60` in (L2c table label; L2b alone was not enough, see log)
  - [x] Q2: `RJF-PR-web-affiliation-options#1` not in; explanation holds (measured: `#0` rank 9,
        `#1` rank 43 at k=80; `#0` and `advisor-select#0` now in the list)
  - [x] Q20: neither in; explanation holds (measured: neither in the top 80 on the branch;
        `UBS-NEXTGEN-2026#83` stays in, plus `CERULLI-GWT-2025#1`, `BOFA-PB-STUDY-2026#15`)
- [x] No PASS -> FAIL against `evals/baselines/corpus-2026-11-17/report.json` (as of 2026-11-17)
      and against `ev203\main-1029` (as of 2026-10-29); 0 forbidden; refusal 5/5 and 19/19;
      tier-1 doc recall not below 0.727 (as of 2026-11-17); doc/passage recall of Q2, Q6, Q13,
      Q17, Q20, Q22 not below `ev203\main-1117`.
- [x] Sentinels Q4, Q27, Q30: no BAC chunk outside GWIM/Merrill in the retrieved set (an answer
      turn of a BAC call is filtered like any chunk), forbidden 0, refusal ok, status unchanged.
- [x] Q25 and Q29 (gap): changed keys and chunk IDs recorded in the progress log; status and
      refusal unchanged; if L2a/L2b brings a payout-grid chunk into Q25, `compensation structure`
      is excluded from inflection matching (TL choice: keep Q25 a clean gap) and the step-4 check
      is re-run to show it gone.
- [x] `pytest -q` PASS (including the `synonym_only` stripping test for inflected "pays"/"paying");
      smoke PASS; `verify_cee.py run` VERIFY PASS.
- [x] 0 real calls (the real check is #121's combined R2).

## Paid calls
None. Mock eval and unit tests only. Q2, Q6, Q13, Q17, Q20, Q22 and Q4, Q27, Q30 are judged for
real once, in #121's R2 (run ledger in `plans/0121-gate4.md`).

## Risks / unsure
- L1 spends a slot on the answer turn; the firm's last pick drops. Most likely to move: RJF and MS
  questions with Q&A turns (Q1, Q2, Q6, Q7, Q11, Q13). The full mock run shows it; `replace` is
  the fallback.
- The question-turn test is textual ("?" at the end, operator hand-off); a management turn ending
  in a rhetorical question would pull in the next turn. Measured by the share of paired chunks
  whose partner is an analyst turn in the step 3 run (spot-check 10).
- L2b adds a phrase probe to every multi-word key in a question (`net new assets`,
  `client assets`, `wealth transfer`, ...): ranking moves on Q1, Q15, Q21, Q22, Q24. Full run.
- L2a makes inflected keys fire on more questions than today, not only the new entries:
  `advisor` -> "adviser" on "advisors" (Q2, Q7, Q20, Q29 and others), and the gap-question case,
  Q25 "advisor compensation structures", where `compensation structure` starts to fire and adds
  "payout grid" and "compensation and benefits" (and, with L2b, the phrase "compensation
  structure"). The config comment on that entry says expansion must not turn a payout-grid story
  into a fact, and a mock PASS cannot show a gap question drifting (the mock always answers).
  Checked in step 4 (fired keys main vs branch for all 30; Q25/Q29 changed chunks and payout
  chunks); fallback above (exclude `compensation structure` from inflection matching).
- New synonyms widen the match (OR query): more chunks enter the pool; the floor and quotas
  still apply. `payout` under `recruit` must not reach gap questions Q25/Q29 (they do not say
  "recruit"; checked in step 4 with the fired-keys diff).
- #205 edits `fts.py` after this; L1 and L2 stay in their own functions so the rebase is small.

## Progress log
- 2026-11-18 00:28 - plan written on `tl/203-gate4-retrieval` (from origin/main a886741);
  DB `cee` = `corpus-2026-11-17` (sync check up to date); diagnosis probes run read-only (above);
  0 real calls.
- 2026-11-18 00:34 - plan review round 1 (PLAN CHANGES REQUESTED, #203 comment 6971073215). Blocking 1 fixed: Risks name L2a firing on more questions, with Q25 (`compensation structure` -> "payout grid") as the gap case; step 4 prints fired synonym keys main vs branch for all 30 and Q25/Q29 changed chunk IDs with payout chunks; acceptance line for Q25/Q29 with the TL fallback (exclude `compensation structure` from inflection matching if a payout-grid chunk enters Q25). Non-blocking 1-4 taken: `synonym_only` stripping of inflected "pay" stated and tested; config comment block updated in the same PR; ADR number = next free in DECISIONS.md at merge; probes copied to `cache\ev203\probes\`.
- 2026-11-18 00:35 - plan review round 2: PLAN APPROVED (#203 comment 6971106248). Non-blocking notes taken: step 4 records which "payout" chunks are judged payout-grid vs harmless; ADR number kept in sync across DECISIONS.md, specs/retrieval.md and this plan. Implementation started.
- 2026-11-18 00:37 - step 1: main mock baselines `cache\ev203\main-1117` 28/2 (Q15, Q19), tier-1 doc
  recall 0.727, passages 0.523; `main-1029` 28/2, 0.742 / 0.550; 0 forbidden, refusal 5/5 and 19/19
  at both dates (same as `ev121\mock-main`).
- 2026-11-18 00:40 - step 2 (L2) run `l2-1117`/`l2-1029`: 28/2 both dates, tier-1 0.788 / 0.800. Q17
  `MS-TR-2025Q3#8` in. Surprises: (a) Q22 `#60` not in: the probe that put it at rank 2 also had the
  table label "net new assets for the period" as a value; L2b alone leaves it at 64 -> the label is
  added to `net new assets` (the issue names it). (b) Q13 `#20` not in: with L2a "stock-plan" now
  fires `stock plan` (+ phrase + "equity compensation"), lifting the CEO's Carta turn `#12` of the
  same call above `#20` -> `convert` += "originating from" (fires only on "convert"). (c) Q25: L2a
  fired `compensation structure`; `RJF-TR-2026Q1#44` entered ("independent payouts are higher ...
  tiered payout systems ... higher up on the payout grid") = a payout-grid chunk -> TL fallback
  applied: config `synonym_exact: ["compensation structure"]`; re-run shows Q25's chunk set equal
  to main (added [], removed []). (d) `affiliation models` now fires `affiliation model` on Q6.
- 2026-11-18 00:44 - step 3 (L1, `attach`). First run paired 3 turns: Q6 `#45 -> #46` (analyst ->
  CEO, right), Q8 `SCHW-TR-2026Q1#49 -> #50` and Q17 `BAC-TR-2026Q2#6 -> #7` (a CEO handing over to
  the CFO with "...?", wrong). Fix: the "?" test does not count under a speaker label with an
  executive title. After it, the bank keeps one question turn and one pair (Q6), analyst -> CEO
  (`cache\ev203\pairs-final-1117.txt`). `attach` cost no PASS, so `replace` was not run (built and
  unit-tested as the fallback).
- 2026-11-18 00:46 - step 4/5, final runs `final-1117` / `final-1029`: 28 PASS / 2 FAIL (Q15, Q19)
  at both dates, PASS -> FAIL none, 0 forbidden, refusal 5/5 and 19/19; tier-1 doc recall 0.727 ->
  0.788 (11-17) and 0.742 -> 0.800 (10-29); passages 0.523 -> 0.607 and 0.550 -> 0.629. Linked doc /
  passage recall (11-17): Q2 0.556 -> 0.667 / 0.556 -> 0.667; Q6 0.667 -> 1.0 / 0.667 -> 1.0;
  Q13 0.833 -> 1.0 / 0.833 -> 1.0; Q17 0.333 -> 0.667 / 0.333 -> 0.667; Q20 0.286 -> 0.429 /
  0.286 -> 0.429; Q22 0.424 -> 0.424 / 0.125 -> 0.375. Other change: Q5 1.0 -> 0.833 (`advisor`
  now fires on "advisors", PASS kept); Q1 up 0.778 -> 0.889. Traps Q4, Q27, Q30: chunk sets equal
  to main, no BAC chunk outside GWIM/Merrill, forbidden 0, refusal ok. Changed chunk IDs per
  linked question: `cache\ev203\diff-final.txt`.
  Fired keys main -> branch: Q2 [] -> [advisor, recruit]; Q5 [technology] -> [advisor, technology];
  Q6 [] -> [affiliation model]; Q7 [.., recruiting] -> [.., recruit]; Q8 [] -> [advisor, independent
  advisor]; Q10 [] -> [mass affluent]; Q13 [] -> [stock plan, convert, workplace]; Q20 [advisor] ->
  [advisor, under 40]; Q29 [pay] -> [advisor, pay]; Q25 unchanged ([advisor]) after `synonym_exact`.
  Q25 / Q29 "payout" chunks, judged: Q25 chunk set equal to main; its one payout chunk
  `RJF-PR-web-affiliation-options#2` (bank & credit union: "competitive compensation package from
  the financial institution") is on main too, not a grid -> harmless. Q29 added
  `MS-TR-2026Q2#23`, `MS-TR-2026Q3#36`, removed `MS-PR-2026-01-15-01#1`, `MS-TR-2025Q4#12`; no
  added chunk mentions payout. Its payout chunks are all on main too: MS "formulaic payout to Wealth
  Management advisors" (`MS-10Q-2026Q2#20`, `MS-10K-2025#170`, `#153`, `#128`, `MS-10Q-2026Q1#19`,
  `MS-10Q-2025Q3#64`, `MS-10Q-2025Q2#20`) = the disclosed adjacent that Q29's R1 PASS labels, not a
  grid -> harmless; `MS-TR-2025Q3#89` (dividend payout) and `MS-TRADE-2026-08-25-RB-01#0` (an
  editor's payout) unrelated -> harmless. Lever 3 (table rows) not built: not needed for Q22.
  Baseline not refreshed: no status moved.
- 2026-11-18 00:50 - step 6: ADR-017 (next free number in `docs/DECISIONS.md`, re-checked against
  origin/main at this time), `specs/retrieval.md` lines, config comment block. Step 7: `pytest -q`
  499 passed; smoke PASS; `verify_cee.py run` VERIFY PASS, all 9 features
  (`.verify-runs\20261118-004733-7f1fa09`, working tree on top of 7f1fa09). 0 real calls.
