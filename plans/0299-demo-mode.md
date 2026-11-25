# 0299 - Demo mode: replay prepared answers for the 30 questions

Issue: #299    Role: TL    Spec: specs/ui.md, docs/DESIGN.md    Design: none (fixture format in the issue)

## Goal
A muted "Demo" toggle (bottom of the Ask sidebar; also `?demo=1` / `CEE_DEMO=1`) switches the Ask page to replay
prepared results for Q1-Q30: progress bar -> plan -> evidence cards one by one -> a narrative markdown answer (direct
answer, comparison, trend, caveats) with clickable `[n]` citations, in <= 5 s, with zero model calls. Live mode unchanged.

## Files to change
- `scripts/build_demo_fixture.py` (+ `.ps1`, `.sh`) - offline builder: W12 evidence + chunk text -> cards; one Claude
  Opus call per question -> `answer_md`; raw logs to `.eval-runs/demo-fixture/`; writes the fixture.
- `src/cee/app/demo/__init__.py`, `src/cee/app/demo/replay.py` - `load_fixture()` (cached), `match()`, `replay()`.
- `src/cee/app/demo/fixture.json` - generated, committed (30 entries).
- `src/cee/app/views/ask_page.py` - demo branch: dropdown fills the box, Ask -> `replay`, result in
  `st.session_state["last_answer_demo"]`, filters ignored; muted toggle at the bottom of `filters_sidebar`.
- `config/pricing.yaml` - add a `claude-opus-5-5` row (read from the claude-api pricing reference) so calls are costed.
- `scripts/run_demo.ps1`, `scripts/run_demo.sh` - `CEE_DEMO=1`, `LLM_PROVIDER=mock`, start the app.
- `specs/ui.md` - "Demo mode" section. `.claude/skills/verify-cee/features/ask-demo.md`, `scripts/verify_cee.py` step.
- `tests/test_demo_mode.py` - new.

## Steps
1. **Cards.** Per question read `docs/results/w12-latency/b-fts/report.json` `matrix.cells[*].items` (+ `chunk_ids`).
   Pick at most 12 cards: one per distinct chunk, round-robin over entity x aspect, facts before context. Card =
   `{n, chunk_id, doc_id, entity, doc_type, tier, date, label, item_text, passage}`. Passage text by a plain by-id
   SELECT on `chunks JOIN documents` (same columns as `source_page.render`); `fts.fetch_pinned` needs a Query and
   applies filters, so it is not reused. Missing chunk -> build fails loudly (snapshot `corpus-2026-11-19`).
2. **Stages.** Map W12 per-question timings (`b-fts-latency.json`: plan_s, map_max_s, reduce_s, search_s) onto
   `cee.ask.STAGES` (resolve/decompose <- plan; search <- search; extract/research <- map, cards revealed here;
   synthesize <- reduce; check/caveats/log fixed small), scaled to a 3-4 s total, hard cap 5 s.
3. **Answer call.** Prompt (version `demo-1`, stored with each output): question, `expected_behavior`, trap note,
   W12 plan text, numbered cards. Ask for: 1-2 sentence direct answer, then Comparison / Trend sections as the
   question needs, then Caveats / gaps; inline `[n]` only; no fact outside the cards; nothing normative; decline or
   partial exactly as `expected_behavior` says (traps Q4, Q27, Q30; gap_with_adjacent Q24, Q25, Q28, Q29, Q30).
   Code checks every `[n]` resolves and appends the `config/entities.yaml` caveats (code-inserted, not prompted).
   Mock dry run of the whole builder first (fake client), then the one real run of all 30.
4. **Review.** Sonnet spot-check: each answer's claims vs its cards. I read Q4, Q27, Q30 and >= 6 others. Fix by
   re-running only those questions (prompt tweak recorded as `demo-2`).
5. **Replay + UI.** `replay.py` draws into the live slots (`trace_lines`, `evidence_cards`/`_draw_cards`,
   `answer_body`) with `time.sleep` per stage; `[n]` link to the card anchors / source page. Fuzzy match:
   id or exact text, else `difflib.get_close_matches(cutoff~0.6)`, else "prepared question set only" message.
6. **Launchers, spec, recipe, tests**, then verify-cee.

## Acceptance
- [ ] `fixture.json` has 30 entries (Q1-Q30), snapshot `corpus-2026-11-19`; every card's chunk_id exists in the DB.
- [ ] `pytest tests/test_demo_mode.py`: every `[n]` in every `answer_md` resolves to a card of that question; demo on
  -> pick question -> Ask shows cards and answer; `cee.ask.ask` monkeypatched to raise, never called; fuzzy match +
  no-match message; replay total <= 5 s for every entry.
- [ ] Q4, Q27, Q30 decline or flag the trap per `expected_behavior`; Q24, Q25, Q28, Q29 give the gap + adjacent.
- [ ] Sonnet spot-check: no claim unsupported by its cards (report saved in `.eval-runs/demo-fixture/review/`).
- [ ] `tests/test_no_paid_calls.py`, existing ask-progress / ask-answer tests pass; `gh pr checks` green.
- [ ] verify-cee `ask-demo` PASS (mock provider, snapshot `corpus-2026-11-19`) with screenshots: muted sidebar toggle;
  bar mid-progress; evidence before answer; final answer with working `[n]` links; Q4 declining; step log <= 5 s
  from Ask to full answer. verify-cee `ask-progress` PASS (live unchanged).

## Paid calls
Claude Opus `claude-opus-5-5` via `LLM_PROVIDER=anthropic` client (`answer.llm.anthropic_client`, `max_retries=0`):
1 call per question for Q1-Q30 = **30 calls**, plus re-runs only for answers fixed after review, **cap 6** (total
<= 36). Plus the Sonnet spot-check (agent, no API key). The mock cannot judge narrative quality or claim-vs-card
fidelity. Raw request + response per call saved under `.eval-runs/demo-fixture/` (reused, never re-rolled); tokens
and cost logged. Pre-approved by the user 2026-11-24. Zero calls at demo time.

## Gaps found (read-only checks, 2026-11-24)
- Key/provider: `ANTHROPIC_API_KEY` set in `.env`; client in `src/cee/answer/llm.py`. `config/pricing.yaml` has no
  Opus row (added above). Default `LLM_MODEL` is Sonnet; the builder names the Opus model itself.
- W12 evidence: all 30 have matrix cells with chunk_ids (7-167 chunks each, 980 distinct) -> cap 12 cards.
  Q29 is `NOT_EVALUATED` in W12 (cells exist, no scored answer); Q24/Q25/Q28 behaved `answer` in W12 though
  expected `gap_with_adjacent` -> the prompt enforces the expected behavior, not W12's.
- No plain chunk-by-id helper in `fts.py` (only filtered `fetch_pinned`); builder uses its own SELECT (step 1).
- W12 timings are plan/map/reduce, not the 9 `STAGES`; mapping in step 2.

## Progress log
- 2026-11-24 19:14 - plan written; branch `tl/299-demo-mode` from main 1329bde; DB up to date (corpus-2026-11-19).
