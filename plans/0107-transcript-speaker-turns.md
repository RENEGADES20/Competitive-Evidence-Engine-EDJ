# 0107 - Chunk earnings-call transcripts by speaker turn

Issue: #107    Role: C2    Spec: specs/transcripts-ir.md (also touches config/entities.yaml - C1, evals/expected_chunks.yaml - S1)

## Goal
Every transcript chunk starts at a speaker turn and never holds two turns (a short operator
hand-off joins the next turn); long turns split at 1,200 characters with the speaker line repeated,
so the BAC-TR-2026Q2 Merrill answer becomes its own GWIM-tagged chunk and "management said ..."
cites one speaker. Only transcripts change; all other documents chunk exactly as before.

## Files to change
- src/cee/ingest/transcript.py (new, C2) - split a transcript .txt into a preamble (header lines,
  participant list) and turns [(speaker_label, paragraphs)]. Detector, in order: section headings
  (Presentation / Question and Answer / MD&A close a turn); Operator / Moderator; Bloomberg "Q - "/"A - ";
  exact participant-list label; "<label> at <firm>" (MarketBeat); split label (name + title on two
  paragraphs); bare-name label inside the participant list (Bloomberg); label shape fallback (short,
  capitalised, no sentence punctuation, recurring or ending in a title/org word, or Roic file);
  label merged into the first sentence. Drops leftover page headers ("... EARNINGS CALL ... ",
  "..., Q1 2026 Earnings Call, Apr 15, 2026") from labels. Pure functions, no I/O.
- src/cee/ingest/chunk.py - chunk_sections: when doc_type == "transcript", pack each turn
  separately with TRANSCRIPT_MAX_CHARS = 1200 (pack_paragraphs, unchanged), put the speaker line
  verbatim at the top of every chunk of the turn, and call the segment tagger on the turn text
  without the speaker line (analyst firm names like "RBC Capital Markets" must not count as stop
  words). Operator/Moderator turns under 300 chars become the first paragraph of the next turn.
  Section stays "Document"; prefix format and chunk_id f"{doc_id}#{n}" unchanged. Other doc types:
  untouched code path.
  Added during work (user decision): SegmentTagger.continues - a chunk that continues the same
  speaker's turn after a GWIM-tagged chunk keeps GWIM when it names no segment itself and its GWIM
  signal words are at least twice the other businesses' words (needs C1 sign-off in the PR).
- config/entities.yaml - BAC mention_excludes: add "acquisition of Merrill" (needs C1 sign-off in the PR).
- tests/test_transcript_turns.py (new) - fixtures (inline strings, no network) for the 4 layouts:
  question and answer are separate chunks; a long answer splits into several chunks of the same turn,
  each starting with the speaker line; operator hand-off joins the next turn; page-header leftover is
  not a speaker; non-transcript doc types chunk exactly as before; the Merrill answer fixture
  (paragraphs 0-1 GWIM, paragraph 2 commercial) tags GWIM / untagged.
- evals/expected_chunks.yaml, evals/expected_results.md - remap the 23 transcript chunk ids to the new
  ids by text overlap (each checked against its quoted passage); old->new table in the PR.
- plans/0107-transcript-speaker-turns.md - this plan.

## Steps
0. Setup: restore corpus-2026-10-29 (local DB still has the 5 #48 docs) with scripts/restore.sh;
   copy the 11 PDF-converted transcripts from Box raw/ into data/raw/ and check sha256; baseline:
   eval_run full bank --as-of 2026-10-30 --out .eval-runs/107-before; chunk_dump.py dump --all to
   .eval-runs/107-before/chunks.json; save old transcript chunks (id, segment, text) to CSV.
1. Write transcript.py + tests; run the detector over all 32 files: turns, turns without a speaker (target 0),
   longest turn, chunks per doc before/after.
2. Wire into chunk_sections (transcripts only), cap 1,200, speaker line repeated, tag without speaker line.
3. Re-ingest the 32 transcripts with bash scripts/ingest.sh --doc <id> (a full ingest stops on research files that
   are only in Box). Prove other docs unchanged: chunk_dump compare filtered to non-transcript ids -> IDENTICAL,
   plus SQL: segment and prefix of every non-transcript chunk unchanged.
4. Check the exclusion: grep the whole corpus for "acquisition of Merrill"; list any non-transcript chunk whose
   GWIM tag would change on the next snapshot rebuild; add the exclude; re-ingest BAC transcripts.
5. GWIM spot-check: list every GWIM-tagged transcript chunk (old 9 vs new); read each; 0 wrong. Note that
   today's BAC-TR-2025Q3#24 is already wrongly tagged (starts with digital/Erica) - report whether fixed.
   Confirm the BAC-TR-2026Q2 Merrill answer is its own chunk and GWIM-tagged.
6. Remap the answer key; run eval_run with the OLD key against the new DB once (shows why the remap is
   needed), then with the NEW key.
7. Checks: explicit Q4 / Q27 retrieval (Merrill answer chunk present, no untagged BAC, 0 forbidden);
   full-bank eval vs baseline; pytest -q; verify_cee.py run (all 7 PASS).
8. /finish-task: PR lists new GWIM chunks, old->new id table, chunk counts, asks C1 (exclude) and
   S1 (answer key, chunk count growth vs MAX_PER_DOC) to review; TL rebuilds the snapshot after merge.

## Acceptance
- [x] Fixture tests: a question and its answer are separate chunks; a long answer splits into several
      chunks of the same turn (speaker line on each).
- [x] All 32 transcripts re-ingested; every chunk holds one speaker turn (script check: 0 chunks with two
      detected speakers, except operator hand-offs merged by design).
- [x] BAC-TR-2026Q2 Merrill answer ("the Merrill 5% guide ... keep growing the sales force ... adviser
      attrition is now at near historic lows") is its own chunk and segment GWIM.
- [x] Every GWIM-tagged transcript chunk listed in the PR and read: 0 wrong (BAC-TR-2025Q3#26 opens with
      one consumer sentence; pre-existing as #24, reported).
- [x] Non-transcript chunks byte-identical (chunk_dump compare) with the same segments.
- [x] Q4, Q27 (traps): 0 forbidden hits, no untagged BAC; Q1, Q13: transcript evidence still retrieved.
- [ ] Mock eval for all 30 (new key, --as-of 2026-10-30): 0 forbidden, no PASS->FAIL, refusal unchanged,
      coverage and doc recall same or better per question; any passage-recall change explained.
      NOT MET: 0 forbidden and refusal unchanged, but Q28 PASS -> FAIL (coverage 2/3 -> 1/3, passage recall
      2/4 -> 3/4; S1's per-firm FLOOR) and Q11 doc recall 7/8 -> 6/8. Handed to S1 (user decision).
- [x] pytest -q passes; verify_cee.py run: all 7 features PASS. 0 paid API calls.

## Risks
- Transcript chunks grow from 1,689 to roughly 2,800; with MAX_PER_DOC = 3 less text per transcript reaches an
  answer. Report counts to S1; do not change retrieval here.
- The speaker-line repeat adds words to every chunk; check it does not crowd FTS ranking (Q1 passage recall).
- Short chunks get tagged by a single "Merrill" mention more easily (own >= 2 * stops); the spot-check is the guard.
- BAC-TR-2026Q1#48 (Moynihan, "wealth strategy") has no mention word and stays untagged - flag to C1, not fixed here.

## Progress log
- 2026-11-01 16:15 - plan written after read-only survey of 32 transcripts (4 layouts, 1,890 turns, 0 unnamed).
- 2026-11-01 16:30 - setup: restored corpus-2026-10-29 (111 docs, 1,689 transcript chunks, 9 GWIM-tagged),
  copied the 11 PDF-converted transcripts from Box (sha256 ok). Baseline eval 27/30 PASS (--as-of 2026-10-30).
- 2026-11-01 17:00 - transcript.py: 1,584 turns over 32 files, 0 without a speaker; 2,852 chunks, none over
  1,200 chars; every source paragraph kept (page-header leftovers dropped). Wired into chunk_sections.
- 2026-11-01 17:10 - dry run: the Merrill answer is its own chunk (BAC-TR-2026Q2#63, 901 chars) and GWIM.
  BAC-TR-2025Q1 "slide 22 ... acquisition of Merrill" became a wrong GWIM chunk -> added the exclude (the
  phrase occurs in no other chunk of the corpus). BAC-TR-2025Q3#26 (was #24) stays GWIM: first sentence is
  consumer digital, the rest wealth, one source paragraph - pre-existing, reported, not fixed.
- 2026-11-01 17:30 - surprise: the 1,200 cap split two GWIM sections so their second half lost the tag
  (BAC-TR-2026Q1#26 "adviser productivity ... attract talent", Q4's row 1; BAC-TR-2026Q2#21). User chose
  the in-turn carry-over rule; simulated on all BAC transcripts it tags exactly these 2 chunks. 14 GWIM
  transcript chunks, all read (list in PR).
- 2026-11-01 17:45 - re-ingested 32 transcripts (BAC twice). Non-transcript chunks identical: 15,494 chunks,
  section/page/text (chunk_dump) and segment/prefix (SQL export) unchanged. Every transcript chunk holds one
  speaker (2,776) or is the preamble (32) or a long operator turn (44); 0 with two speakers.
- 2026-11-01 18:00 - answer key remapped: 23 old ids -> 32 new ids (expected_chunks.yaml, expected_results.md).
  must_return: new chunks holding >= 45% of the old chunk's words plus the chunk with the documented quote,
  minus off-passage chunks (BAC-TR-2026Q2#19 consumer, MS-TR-2026Q1#4 capital). must_not_return: only the
  chunk that holds the misleading text. Table in .eval-runs/107-before/remap.tsv.
- 2026-11-01 18:10 - eval (new key) vs baseline: 26/30 PASS (was 27). IMPROVED Q4 (recall), Q22.
  Q28 PASS -> FAIL: coverage 0.667 -> 0.333 although passage recall rose 0.5 -> 0.75. The Merrill attrition
  answer (#63, rank 10.64) lifts BAC's per-firm floor to 3.19 and BAC-10K-2025#246 (2.88) drops out
  (FLOOR = 0.3, S1). Q11 doc recall 0.875 -> 0.75 (SCHW-TR-2026Q1 slot taken by a SCHW deck). User: keep
  the change, report to S1, PR "Part of #107". Q4/Q27 explicit checks clean (0 untagged BAC, 0 other firms).
- 2026-11-01 19:47 - pytest 271 passed, 1 skipped; verify_cee.py run: all 7 features PASS, 0 FAIL steps
  (.verify-runs/20261101-194621-f336093; app shows 18,346 passages = 15,494 + 2,852). 0 paid API calls.
- 2026-11-03 - /finish-task: PR "Part of #107" (open: Q28 / Q11 eval regressions for S1; C1 sign-off on the
  exclude and the carry-over rule).
