# 0115 - Clean source_registry names shown in gap answers

## Goal
Every `source_name` in `config/source_registry.csv` reads as a plain source; no file paths (#115).

## Files to change
- `config/source_registry.csv` - 5 `trade` rows (data only; `validate.py` out of scope)

## Steps
1. Rename `"<Firm> Trade press (tier 4, docs/BRIEF.md)"` to `<Firm> Trade press coverage (industry publications)`; `note` keeps the BRIEF pointer (not shown to users).
2. Reseed `source_registry`; pytest; `verify_cee.py run gap-path`; print `suggested_sources('MS')`, `('EDJ')`; Q28/Q29 gap text.

## Acceptance
- [x] No `source_name` contains a file path or "docs/"
- [x] Q28 and Q29 gap text (mock, live database) in the PR
- [x] pytest and verify-cee gap-path PASS

## Progress log
- 2026-11-14 09:35 - 5 trade rows renamed; registry reseeded (49 rows). pytest 365 passed, 1 skipped; verify-cee gap-path PASS (.verify-runs/20261114-093248-4236f14). Q28/Q29 gap text clean (mock model, live database).
