# 0055 - Form ADV Part 2A brochures for the five advisory firms (Q18)

Issue: #55    Role: C3 (reassigned from C1 on 2026-11-05)    Spec: specs/filings.md

## Goal
The current Part 2A brochure of each firm's main advisory entity (EDJ, MS, SCHW, MER = MLPF&S, RJF) is
stored as a PDF with page numbers, `published_at` = brochure date, and the CRDs are verified and recorded
in config, so Q18 can cite fee schedules.

## Files to change
- `config/entities.yaml` (C1's file; the issue asks for it) - `crd:` per core firm with source and date.
- `data/manifest.csv` - 5 rows: `doc_type=adv`, `source_tier=2`, `entity_id` = the firm (MER for Merrill).
- `plans/0055-adv-brochures.md` - this plan.
- Raw PDFs in `data/raw/` (gitignored); the user uploads them via the Box upload link.

## Steps
1. Find each firm's CRD on IAPD (api.adviserinfo.sec.gov) and confirm the legal name on the brochure.
2. Choose the main brochure per firm (each firm files one per program). Rule: the firm's primary retail
   advisory program, per its own 10-K where it says so; for MS, compare candidates and keep the one with
   the broadest program and most fee content.
3. Download with the user's approval, record cover dates, load locally, run Q18 and the full mock eval.

## Acceptance
- [x] Five brochures stored; `published_at` = brochure date
- [x] CRD numbers verified and recorded (no TODO-verify for the core five)
- [x] Q18 retrieval returns fee chunks from at least three firms (all five; MS, RJF, MER, SCHW clearly fee text)
- [x] `pytest -q` passes (365 passed, 1 skipped)
- [x] `verify_cee.py run` PASS (open-citation UNREACHABLE: raw MS supplement PDF not local, same on main)

## Progress log
- 2026-11-16 - plan agreed with the user; branch c3/55-adv-brochures from main 8f92cb1. #120 reviewer asked
  the TL for a decision on #55 versus the freeze; none recorded yet, so the PR leaves it to the TL.
- 2026-11-16 - CRDs on IAPD: EDJ 250 (801-3297), MS 149777 (Morgan Stanley Smith Barney LLC, 801-70103),
  SCHW 5393 (801-29938), MER 7691 (MLPF&S, 801-14235), RJF 705 (Raymond James & Associates, 801-10418).
- 2026-11-16 - Brochures (IAPD BRCHR_VRSN_ID): EDJ Advisory Solutions Fund Models 1027427 (cover 2026-03-27;
  the 10-K says advisory fees come "primarily through" Advisory Solutions); SCHW Schwab Wealth Advisory
  1061131 (2026-10-15); MER Investment Advisory Program 1062763 (2026-10-30); RJF firm brochure 1057715
  (2026-09-14); MS Select UMA 1063273 (2026-11-04), chosen over Consulting Group Advisor (33 pp, 9 fee
  mentions) and Portfolio Management (32 pp, 13) for breadth (52 pp, 26). IAPD returns 404 to a user agent
  string with a project suffix; a plain browser string works.
- 2026-11-16 - Loaded: 1,156 chunks, every one with a page number. Q18 PASS with all five `*:adv` patterns.
- 2026-11-16 - Surprise: full mock eval without vs with the brochures: 27/3 -> 26/4, tier-1 recall
  0.626 -> 0.587. ADV chunks enter the retrievals of 29 of 30 questions. Q23 and Q24 PASS -> FAIL (MS
  supplement and RJF press pushed out); Q26 FAIL -> PASS only because RJF brochure chunks fill the 90-day
  window (not news); Q27 loses BAC Q3 call/press chunks to MER brochure chunks. Cause: retrieval searches
  `adv` for every question. Retrieval is S1's; flagged in the PR with a suggested S1 issue, and a
  recommendation to keep the brochures out of the Gate 3 freeze snapshot until it is fixed.
