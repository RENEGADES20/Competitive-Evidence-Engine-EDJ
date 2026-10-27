# 0042 - Citations show source and tier

Issue: #42    Role: U1    Spec: specs/ui.md

## Goal
Each citation on the Ask page says where it comes from (its own source label) and how much to
trust it (tier badge), and opens the stored passage of that chunk. No external URL is composed.

## Files to change
- src/cee/app/components.py - citation chip takes a per-citation source label; claim card accepts it
- src/cee/app/views/ask_page.py - build one chip per citation from the retrieved hits; a chunk ID outside the retrieved set is shown flagged and not linked
- src/cee/app/views/design_page.py, docs/DESIGN.md - sample and component description follow the change
- scripts/verify_cee.py, .claude/skills/verify-cee/features/open-citation.md - check source label and tier on every citation

## Steps
1. Chip with label under it (link text stays exactly the chunk_id).
2. Ask page: label from `source_label(hit)`, tier from the hit.
3. Update driver and recipe; run verify_cee.py run (mock).

## Acceptance
- [x] Linked questions: Q26, Q29, Q30 (links resolve, tier labels, caveat visible; mock pipeline only)
- [x] Every citation shows its source label and tier label; tier 4 reads "indicative only"
- [x] Each citation opens the source page of that chunk (no external URL composed)
- [x] verify_cee.py run all PASS after updating the open-citation recipe and driver

## Progress log
- 2026-10-27 - plan written
- 2026-10-27 - implemented; verify-cee 5/5 PASS (run 20261027-113414-b077220), pytest 106 passed
