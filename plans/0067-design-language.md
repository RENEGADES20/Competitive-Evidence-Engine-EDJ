# 0067 - Design language and page shell

Issue: #67    Role: U1    Spec: specs/ui.md

## Goal
The app looks designed, not like a default skeleton: one theme, a written design language,
a page shell with every planned page and control in place as disabled placeholders, and a
Design gallery page showing every component with sample data. Mock answers only.

## Files to change
- .streamlit/config.toml - theme (colours, font, corner radius)
- docs/DESIGN.md - principles, colour/type values, every component, WCAG AA contrast pairs
- src/cee/app/components.py - new: citation chip, tier badge, caveat box, gap box, behavior header,
  source header, coverage cell, placeholder, empty state, footer
- src/cee/app/ (pages) - navigation Ask / Coverage / Design; source page still via ?chunk=<id>
- scripts/verify_cee.py, .claude/skills/verify-cee/ - only if an element name must change

## Steps
1. "Before" screenshots: Ask (mock answer) and Source.
2. Collect design preferences; build 3 directions applied to the Ask page; user picks (max 3 rounds).
3. Theme, then components.py, then DESIGN.md, then Design gallery page.
4. Split pages, add placeholders (#63 sidebar filters, #62 feedback, #41 coverage body,
   #53 passage in context) and the snapshot footer.
5. verify_cee.py run; contrast check (a11y MCP on localhost:8501); "after" screenshots.

Tier badges: the five tiers named in the issue (licensed, filing, IR, trade press (indicative only),
research). Tier 6 "signal" in TIER_LABELS is out of scope here.

## Acceptance
- [x] Linked questions: Q29 (tier label on every citation), Q30 (caveat always visible)
- [x] Theme from .streamlit/config.toml; extra CSS small and in one place
- [x] DESIGN.md covers every component with colours; tier badges carry text; tier 4 "indicative only"
- [x] Text/background pairs >= 4.5:1, listed in DESIGN.md
- [x] Design page shows every component, 5 tiers, 3 coverage states, "Sample, not from the corpus"
- [x] Placeholders disabled, name their issue, do nothing on click
- [x] Caveats and gaps never in expander/tab/tooltip
- [x] Footer shows corpus-YYYY-MM-DD from the database on every page
- [x] scripts/verify_cee.py run -> all PASS (LLM_PROVIDER=mock, 0 real calls)

## Progress log
- 2026-10-15 16:35 - plan written; branch u1/67-design-language created
- 2026-10-15 17:14 - directions B, C, B+C night navy and a watermark variant shown; user picked D (editorial tech,
  after a reference site: warm paper, ink, lime/orange, CSS-only ticker). Theme, components, page shell,
  placeholders (#63 #62 #41 #53), footer and DESIGN.md done. Hero copy taken from docs/BRIEF.md.
- 2026-10-15 17:14 - verify_cee.py run all PASS (driver unchanged). axe-core: no contrast violations; two
  Streamlit-internal sidebar findings remain (noted in DESIGN.md). a11y MCP could not start its browser
  (spawn error -88), so axe-core was run through Playwright instead. Q29, Q30: gap_with_adjacent (mock).
