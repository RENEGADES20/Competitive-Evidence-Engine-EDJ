# 0205 - Firm scope: an unnamed advisor-led model, and competitors on the theme for home-firm questions

Issue: #205    Role: TL    Spec: specs/retrieval.md (also specs/answer-citations.md for the
coverage note and caveats, read only unless step 5 needs it)

## Goal
Retrieval searches the firms a question is about, through SQL filters and explicit config rules,
never a model guess: (1) "an advisor-led model" means the advisor-led firms (MS, EDJ, Merrill,
RJF), so Q15 gets their revenue evidence next to Schwab's; (2) a theme question whose only named
firm is the home firm (Edward Jones) also gets the other covered firms' passages on that theme,
so Q19 can cite competitor moves aimed at younger investors. The home firm's share and the
research share stay as they are.

## Facts (2026-11-18, read only; DB `cee` = `corpus-2026-11-17`, sync check up to date)
- Base: `origin/main` c5fcfb0 (includes #206 / #203, ADR-017). Mock baseline as of 2026-11-17:
  28 PASS / 2 FAIL (Q15, Q19, coverage 1/5 each), tier-1 doc recall 0.788 (0.800 at 2026-10-29).
- `resolve()` on the bank: only Q15 contains "advisor-led"; only Q19 is `entity+theme` with
  entities = [EDJ] alone (Q12 = SCHW+EDJ, Q28 = EDJ+MER, Q10/Q21 = the five). So rule 1 moves
  Q15 only and rule 2 moves Q19 only; every other question resolves exactly as today.
- **Q15 feasibility** (scratch script, config peer set patched in memory, nothing committed):
  entities become the five, k = 30, and the retrieved set holds `MS-10K-2025#166`,
  `EDJ-10K-2025#20/#23`, `RJF-10K-2025#9`, `SCHW-10K-2025#13`, plus BAC GWIM transcript /
  supplement / 10-Q chunks (no BAC 10-K GWIM chunk). Coverage 4/5 -> PASS.
- **Q19: competitor chunks on the theme** (`younger_investors` keywords, config/topics.yaml,
  the same `on_theme_filter` as #117) in MS, SCHW, MER (incl. BAC GWIM), RJF:
  - Schwab: 12 transcript + 7 deck chunks, real cohort evidence (`SCHW-TR-2025Q4#11` "Gen Z
    investors comprise nearly a third of new retail client accounts...", `SCHW-TR-2026Q3#11`,
    `SCHW-DECK-2026Q3#24` "~70% NTF Retail HH are Gen Z & Millennials").
  - MS: none. RJF: one deck chunk ("Next gen advisor strategy", young advisors, not investors).
  - Merrill: `MER-PR-web-becoming-a-merrill-lynch-advisor#3` ("Top Next-Gen Wealth Advisors")
    and four BAC GWIM press chunks ("Top 40 Advisors Under 40"): advisor rankings, not investors.
  - Ranked with Q19's words: Schwab 32.8 down to 2.8; the four BAC rankings 3.3; the MER and RJF
    chunks do not match Q19's words at all. A floor of 0.3 x the 2nd-best competitor chunk
    (29.45 -> 8.8) keeps 12 Schwab chunks and drops every ranking footnote. A per-firm floor
    (#166) would not: BAC's own 2nd best is the same 3.28.
- **Q19 cannot reach mock PASS honestly.** Its `expected_sources` are THEME:research,
  THEME:survey (not in the corpus), MS:press, SCHW:press, RJF:press, MER:press. No MS, SCHW or
  RJF press chunk is on the theme, and the only Merrill press chunks on it are the advisor
  rankings above. With the rule, the best honest result is research + nothing = 1/5 (unchanged);
  counting a ranking footnote gives 2/5 = 0.4, still FAIL. Appending SCHW:transcript and
  SCHW:deck to `expected_sources` gives 3/7 = 0.43, still FAIL, and editing the bank to fit is
  wrong anyway. Proposed acceptance for Q19 below (named passages); **TL decision D-Q19**.
- `scripts/eval_run.py` `forbidden()` flags every hit whose firm is not in `query.entities`, so
  competitor chunks must be declared on the Query (new field) and accepted only when on the theme.

## Design
**D1 Peer phrase (config only).** New `peer_sets` entry in `config/entities.yaml`:
`advisor_led`, members [MS, EDJ, MER, RJF], phrases "an advisor-led model", "advisor-led models",
"advisor-led firms", "an advisor-led firm" (plus the "adviser-led" spellings). `resolve()` already
unions peer members with named firms (Q15 -> MS, SCHW, EDJ, MER, RJF) and `_search_terms()`
already strips peer phrases. Indefinite and plural forms only, so "Edward Jones's advisor-led
model" or "Morgan Stanley's advisor-led channel" names one firm, not the group. Deliberate edge:
"Edward Jones's and Morgan Stanley's advisor-led models" matches the plural phrase and adds MER
and RJF to the two named firms (the plural names the group; covered by a unit test).
Member check against how each firm reports (config `reporting_shape`, Q15 `expected_sources`
MS:10-K, EDJ:10-K, BAC:10-K#GWIM, RJF:10-K): MS Wealth Management reports advisor-led and
self-directed client assets apart (the only firm using the word, 82 chunks, e.g. `MS-10K-2025#125`);
EDJ serves clients only through its financial advisors; Merrill is GWIM's advisor business
(MER entity filter = BAC GWIM/Merrill only); RJF's Private Client Group is its advisors in every
affiliation model. Schwab is left out: it serves self-directed investors and custodies
independent RIAs; Q15 names it as the contrast. Not a filter on MS's self-directed half: that
split is a reporting fact the answer states, not a segment tag.

**D2 Home-firm theme rule.** Config: `home_firm: {id: EDJ, theme_peers: core_five}` in
`config/entities.yaml`. In `resolve()`: when mode is `entity+theme` and the named covered firms
are exactly [home firm], `Query.theme_peers` = members of that peer set minus the home firm
(MS, SCHW, MER, RJF; Merrill once). `apply_filters` with a firm filter clears it (an explicit
firm choice wins, like the research part, #116). In `search()`: one more SQL pass with
`entity_filter(theme_peers) AND on_theme_filter(themes)` plus the same window, date range,
keywords and doc-type scope; the word match stays. That pool is cut at a floor of FLOOR x its
2nd-best rank across all peers (one group, so a firm whose only on-theme text is an advisor
ranking gets nothing), then `select()` gives each peer firm at most `PEER_THEME_PER_FIRM` slots
(firm turns, slot order, `quota_firms` so BAC GWIM counts as Merrill). The home firm and research
parts are computed exactly as today (k = 20: research <= 4, EDJ the rest); `budget()` adds
`PEER_THEME_PER_FIRM x len(theme_peers)` on top as the cap. `theme_gaps()` stays on named firms.
`PEER_THEME_PER_FIRM` (2 or 3) and the floor are chosen in step 4 by measurement.
Floor edge cases: the cross-peer floor is measured from the 2nd-best peer chunk; a peer pool with
one chunk uses that chunk (its lowest, like `select`'s FLOOR_BASE rule), so it keeps its slot; an
empty pool adds nothing. The cross-peer floor is **kept under a time window** (unlike the home
firm's part, where `opts` sets floor 0): inside a window the peers are still only on-theme
evidence, and dropping the floor would let the advisor-ranking footnotes back in.
Explicit k: `search(q, k)` with a given k (eval `--k 80`) adds the peer cap on top of that k, the
same as `budget()` does on top of K, so the home firm and research parts get the same k with and
without peers and the "EDJ and research passages unchanged" check compares like with like.

**Shown to the user (code, not prompt).** `coverage_note`: "Coverage: searched Edward Jones;
on the theme also Morgan Stanley, Schwab, Merrill, Raymond James." and "No passages on the theme
(...) for Morgan Stanley, ..." for peers with none. `insert_caveats` also applies a peer's caveat
(a cited BAC GWIM chunk for Merrill gets "GWIM is not Merrill"). The Ask page trace and `ask.py`
firm line list the peers as "on the theme".

**ADR.** D2 widens ADR-004's firm filter (named firms only) by an explicit rule and changes the
#117 selection; a new ADR "Home-firm theme questions also search competitors on the theme; peer
phrase for the advisor-led model" (TL-approved; number = next free at merge, ADR-018 unless #204
takes it). ADR-004 and ADR-013 get a "see ADR-0NN" line.

## Files to change
- `config/entities.yaml` - `advisor_led` peer set; `home_firm` block (comments say why).
- `src/cee/retrieve/fts.py` - `Query.theme_peers`; `home_firm()` reader; `resolve()` rule;
  `apply_filters()` clears peers; `search()` peer pass, cross-peer floor, peer selection;
  `budget()` cap; module docstring.
- `src/cee/answer/validate.py` - coverage note line for peers and peer theme gaps; caveats for peers.
- `src/cee/app/views/ask_page.py`, `src/cee/ask.py` - firm line shows the peers "on the theme".
- `scripts/eval_run.py` - `forbidden()` checks peer hits independently of `search()`: a hit from
  a firm not named in the question is allowed only when (a) `query.theme_peers` is set and the
  hit's firm is in it, (b) the hit's text matches the theme pattern recomputed from
  `config/topics.yaml` (and `firm_themes`) for `query.themes` with the tagger's own pattern
  (`cee.ingest.topics`), never the `Hit.on_theme` flag, and (c) a BAC hit counts for MER only
  through the existing `_segment_in` GWIM/Merrill check. Everything else stays forbidden as today.
  The report records `theme_peers`.
- `tests/test_retrieval_themes.py` (+ `test_filters.py`, `test_coverage.py`, `test_eval_run.py`
  as needed) - unit tests below.
- `specs/retrieval.md` - interface sketch lines for D1 and D2, acceptance line for Q15/Q19.
- `docs/DECISIONS.md` - the new ADR; pointer lines in ADR-004 / ADR-013.
- `evals/baselines/corpus-2026-11-17/report.{json,md}` - refreshed only if a status moves (Q15).
- `.claude/skills/verify-cee/features/coverage.md` and `scripts/verify_cee.py` - only if the
  coverage feature's checked text changes (it uses THEME_GAP_Q, the five; expected: no change).
- Not changed: `evals/questions.yaml` (no `expected_sources` edit, see D-Q19), `config/topics.yaml`,
  `prompt.py` / `llm.py` (#204).

## Steps
1. Config: `advisor_led` peer set and `home_firm` block. Unit tests: Q15 resolves to the five;
   "Edward Jones's advisor-led model" and "Morgan Stanley's advisor-led channel" do not add the
   group; Q19 gets `theme_peers` [MS, SCHW, MER, RJF]; Q12, Q28, Q10, Q21 and a home-firm
   question with no theme get none; a firm filter clears them.
2. `search()` peer pass, cross-peer floor, per-firm cap, `budget()`. Unit tests on the theme
   test DB: peer chunks only on the theme; a peer's off-theme chunk never comes back; a BAC chunk
   outside GWIM never comes back as Merrill; a low-ranked peer is cut by the floor; the home and
   research parts are the same list as without peers; window / date range / keywords / doc-type
   scope apply to the peer pass; the cross-peer floor still cuts under a time window; a peer pool
   with one chunk keeps it and an empty pool adds nothing; with an explicit k the peer cap is
   added on top. Resolve test: "Edward Jones's and Morgan Stanley's advisor-led models" adds
   MER and RJF (deliberate).
3. `eval_run.forbidden()` (independent check, see Files to change) and the report field;
   coverage note, caveats, firm line. Named unit tests in `tests/test_eval_run.py`:
   - `test_forbidden_peer_hit_off_theme_text_even_if_flagged_on_theme` (a peer hit with
     `on_theme=True` whose text has no theme keyword is forbidden);
   - `test_forbidden_bac_non_gwim_hit_with_mer_peer` (a BAC hit without GWIM/Merrill segment is
     forbidden even with MER in `theme_peers`);
   - `test_forbidden_non_peer_firm_on_theme_hit` (an on-theme hit of a firm neither named nor in
     `theme_peers` is forbidden);
   - `test_forbidden_without_theme_peers_unchanged` (a query without `theme_peers` gives the same
     result as today's rule on the same hits).
4. Measure (mock, 0 calls): Q19 with `PEER_THEME_PER_FIRM` 2 and 3 and the floor on/off; Q15
   retrieved set. Pick the smallest setting that brings `SCHW-TR-2025Q4#11` or another Schwab
   cohort chunk in and no ranking footnote. Record the grid in the progress log.
5. Full mock eval at `--as-of 2026-11-17` against `evals/baselines/corpus-2026-11-17/report.json`
   and at `--as-of 2026-10-29`; refresh the committed baseline if Q15 moves.
6. Spec lines, ADR, docstring; `pytest -q`; `python -m cee.smoke`; then `verify_cee.py run`
   (filters + coverage features) when the TL says the shared app/DB is free (#204 may be
   running it); the run is on the head the reviewer reviews, and its run id goes in the PR.
7. `/finish-task`: PR "Closes #205", Verification with 0 real calls.

## Acceptance
- [ ] **Q15** mock FAIL -> PASS at as-of 2026-11-17: entities = MS, SCHW, EDJ, MER, RJF; the
      retrieved set holds 10-K passages of at least two advisor-led firms (expected: MS, EDJ, RJF)
      and still Schwab's; coverage >= 3/5; 0 forbidden.
- [ ] **Q19** (D-Q19, accepted by the TL on #205): `theme_peers` = MS, SCHW, MER, RJF; the retrieved set holds at
      least one Schwab passage on the younger-investor theme (`SCHW-TR-2025Q4#11` or another of
      the Schwab cohort chunks listed in Facts) and no advisor-ranking chunk
      (`BAC-PR-*` "Under 40", `MER-PR-web-becoming-a-merrill-lynch-advisor#3`,
      `RJF-DECK-2025-investor-day#42`); every peer hit is on the theme; the EDJ and research
      passages are the same as on `main`; 0 forbidden. Mock status stays FAIL at coverage 1/5,
      explained in the PR (no competitor press on the theme in the corpus). If the TL wants
      mock PASS instead, that needs a question-bank decision, not this code.
- [ ] **Q12** keeps entities SCHW, EDJ, no `theme_peers`, same retrieved set as `main`.
- [ ] Sentinels: Q4, Q27, Q30 unchanged (status, retrieved set, recall, refusal); every other
      question's retrieved set unchanged except Q15 and Q19.
- [ ] Mock 30 at as-of 2026-11-17: no PASS -> FAIL; 0 forbidden; refusal 5/5 and 19/19; tier-1
      doc recall 0.788 (not below 0.727; unchanged expected, no tier-1 question moves). Same
      checks at as-of 2026-10-29 (0.800).
- [ ] Firm filter on the Ask page: a home-firm theme question with a firm filter gets no peers.
- [ ] `forbidden()` is independent of `search()`: the four named tests in Step 3 pass
      (off-theme text flagged on_theme -> forbidden; BAC non-GWIM with MER peer -> forbidden;
      non-peer firm on-theme -> forbidden; no `theme_peers` -> unchanged).
- [ ] Floor edge cases and explicit k covered by the Step 2 tests (window keeps the cross-peer
      floor; 0/1-chunk peer pool; peer cap on top of an explicit k); plural-phrase resolve test.
- [ ] `pytest -q` PASS; smoke PASS; `verify_cee.py run` VERIFY PASS (filters, coverage features)
      on the reviewed head, run id recorded in the PR.
- [ ] 0 real calls (Run ledger of #121: Q15 and Q19 are checked once in the combined R2).

## Risks / unsure
- Q19's answer can now cite Schwab only (MS and RJF have no cohort passages; Merrill's are
  rankings). The coverage note names the peers with nothing on the theme, so the answer can
  say so. Whether that is enough for `passes_if` ("competitor moves aimed at it") is R2's call.
- Q15 grows to 30 passages (five firms). The MS chunks mix advisor-led and self-directed;
  telling them apart is the answer's job (#204), not a filter.
- `fts.py` is also touched by any later F-ret work; this branch rebases on `main` before merge.

## Progress log
- 2026-11-18 01:05 - plan written on `tl/205-firm-scope` (from origin/main c5fcfb0); DB `cee` =
  `corpus-2026-11-17`, sync check up to date; feasibility measured read-only (Q15 4/5 with the
  peer set; Q19 competitor on-theme pool: Schwab only, Merrill/RJF matches are advisor
  rankings); 0 real calls.
- 2026-11-18 - D-Q19 accepted by the TL (named-passage check, mock stays FAIL). Plan review
  round 1 (CHANGES REQUESTED, #205 comment 6971644377). Fixed: blocking 1 (`forbidden()` checks
  peer hits independently: peer list, theme pattern recomputed from config, BAC only via
  GWIM/Merrill segment; four named tests). Non-blocking 1-4 taken: cross-peer floor kept under a
  window and 0/1-chunk pool rule; peer cap added on top of an explicit k; verify-cee run id on
  the reviewed head; plural-phrase test.
