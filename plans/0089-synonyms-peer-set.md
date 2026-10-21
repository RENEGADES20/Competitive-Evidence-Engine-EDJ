# 0089 - Expand synonyms in search; "the five" resolves to the peer set

Issue: #89    Role: S1    Spec: specs/retrieval.md (+ config/entities.yaml, C1's file)

## Goal
Search adds the configured synonyms to the question's search terms, and a question about
"the five" is filtered in SQL to MS, SCHW, EDJ, MER, RJF. Both are driven by
`config/entities.yaml`, not code.

## Files to change
- `config/entities.yaml` - new `peer_sets` entry (`core_five`: members MS, SCHW, EDJ, MER,
  RJF; phrases "the five", "each of the five", "across the five", "all five"). Synonyms
  header: "read by expand_synonyms()" instead of "not read by code yet".
- `src/cee/retrieve/fts.py`
  - `resolve()` reads the peer phrases; a match adds the members (config order), merged
    with any named firm.
  - `expand_synonyms(question)` with the TL's rules: expansion only key -> values; all-caps
    keys (NNA, FA, FAs, AI, GWIM, PCG, RIA, AUM) match exact case, whole word; every value is
    searched as a phrase (`phraseto_tsquery`), OR'ed with the existing word query.
  - Peer phrase stripped from the search terms, like firm names.
  - No match -> SQL identical to today.
- `tests/test_fts_synonyms.py` (new, no database) - resolve and expansion tests.
- `evals/expected_results.md` - Q11 and Q22 "Today" lines re-run.

## Steps
1. Tests first; capture "before" top-20 for Q4, Q11, Q22 and 5 questions with no synonym
   and no peer phrase (picked by a script against the keys).
2. Peer-set config + `resolve` + term stripping.
3. `expand_synonyms` wired into the SQL.
4. Re-run the #87 checks; before/after.
5. `pytest -q`; `verify_cee.py run` (mock).

## Acceptance
- [x] Q11, Q22 and the four phrasings resolve to `[MS, SCHW, EDJ, MER, RJF]`, entity mode (test)
- [x] No BAC chunk without a GWIM/Merrill segment in Q4, Q11, Q22 results (Merrill returns
      nothing until #37, as expected)
- [ ] Q11: `EDJ-10K-2025#130` and `RJF-10K-2025#227` in the top-20 - **open**, not in the
      top-20; top-8 recorded in the PR and `evals/expected_results.md`
- [x] Q22: top-20 holds NNA chunks from at least three of the five (MS, RJF, SCHW)
- [x] Multi-word synonym searched as a phrase; "AI" does not match "said" (tests)
- [x] 5 no-synonym, no-peer questions (Q2, Q5, Q6, Q8, Q12): identical top-20
- [x] `pytest -q` 134 passed; `verify_cee.py run` 4 PASS + download-document UNREACHABLE
      (raw file not in local `data/raw/`); 0 real calls

## Out of scope
Per-entity quotas (#59), time windows (#49; includes Q23 "last eight quarters"),
neighbour-metric labels (#87 finding 7), new synonyms beyond #66.

## Notes
- Keys match the question's own wording ("advisors" does not fire the `advisor` key); the
  Postgres stemmer still folds plurals in the search itself.
- Without quotas one firm can fill the top-20; if Q11/Q22 thresholds are missed, report
  the numbers rather than tune past scope.

## Progress log
- 2026-10-21 14:01 - plan written and approved; branch `s1/89-synonyms-peer-set`
- 2026-10-21 - tests, peer set, expand_synonyms in. Peer phrases resolve (Q10, Q11, Q22-Q25 ->
  the five); no BAC chunk outside GWIM; Q2/Q5/Q6/Q8/Q12 top-20 identical; pytest 134 passed.
  Ranking short: Q11 targets not in top-20 (within-firm rank EDJ#130 ~125/413, RJF#227
  ~354/1211; still out with a synonym-match bonus up to 8x and a trial "total advisors"
  synonym). Q22: NNA from MS, RJF only; with a 2x synonym-match bonus MS, RJF, SCHW.
- 2026-10-21 - user chose the 2x bonus (`SYNONYM_BONUS`, only when a synonym fires; SQL
  unchanged otherwise). Q22 met; Q11 top-20 left open on #89 (needs table-aware ranking).
  expected_results Q11/Q22 Today lines re-run. verify-cee VERIFY PASS
  (.verify-runs/20261021-141707-d5fa079; download-document UNREACHABLE, raw file absent).
