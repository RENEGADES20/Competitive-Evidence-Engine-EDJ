# 0001 - Verify core-five entity facts

Issue: #1    Role: C1    Spec: specs/filings.md

(Numbered 0001 for issue #1; plans/0001-e2e-skeleton.md is the TL's skeleton plan.)

## Goal
Every TODO-verify for the core five in config/entities.yaml is replaced by a value checked
against SEC EDGAR, Merrill Edge placement is confirmed from BAC's 10-K, and the question-bank
review with the project lead is prepared.

## Files to change
- config/entities.yaml - CIKs for MS, SCHW, BAC, RJF, MER; Merrill Edge note with 10-K quotes
- docs/PROGRESS.md - one status line
- plans/0001-verify-core-five.md - this plan

## Steps
1. CIKs for MS/SCHW/BAC/RJF from sec.gov company_tickers.json, confirmed via data.sec.gov submissions.
2. MER: choose between the two MLPF&S EDGAR entities (728612 vs 914246).
3. Merrill Edge: find BAC 10-K text placing it in Consumer Banking, not GWIM.
4. Segment names: check each name appears in the latest 10-K.
5. Question-bank review with the project lead (meeting held by the user); change requests go
   in as separate append-only PRs, traps untouched.
6. Tests + smoke.

## Acceptance
- [x] No TODO-verify left for the core five in entities.yaml
- [x] Merrill Edge placement cites BAC-10K-2024 (Q4, Q27, Q30: Merrill Edge never counts as Merrill/GWIM)
- [x] Segment names found in latest 10-Ks: MS "Wealth Management", SCHW "Investor Services"/"Advisor Services", RJF "Private Client Group"/"PCG", BAC "Global Wealth & Investment Management"
- [x] `git diff main -- evals/questions.yaml` -> empty
- [ ] Question-bank review with the project lead held; change requests filed as PRs
- [x] `.venv/bin/python -m pytest -q` -> all pass; `.venv/bin/python -m cee.smoke` -> PASS

## Progress log
- 2026-10-08 - plan written; branch c1/1-verify-core-five
- 2026-10-08 - CIKs confirmed on EDGAR: MS 895421, SCHW 316709, BAC 70858, RJF 720005.
- 2026-10-08 - MER: 728612 "MERRILL LYNCH, PIERCE, FENNER & SMITH INC." is active (filings to 2026);
  914246 "... INC /NY" last filed 2016 (40-series only). Chose 728612. Form ADV lookups on IAPD use
  the CRD number, not the CIK -- add a crd field later if the ADV pipeline needs it.
- 2026-10-08 - Surprise: BAC-10K-2025 does not mention "Merrill Edge" at all (Consumer Lending and
  Deposits were combined in Q1 2025). BAC-10K-2024 states it explicitly under Consumer Banking >
  Deposits > Consumer Investments. Quoted both in entities.yaml.
- 2026-10-08 - Alias "Merrill Lynch Wealth Management" has 0 hits in BAC-10K-2025 (current name is
  "Merrill Wealth Management"); kept for older filings and press.
- 2026-10-08 - Ran Q4/Q27/Q30 on corpus-2026-09-30: all resolve to entity MER, 0 hits, behavior
  gap_with_adjacent (corpus has only EDJ-10K so far; no BAC/EDJ text leaks into Merrill answers).
  pytest 11 passed; smoke PASS.
