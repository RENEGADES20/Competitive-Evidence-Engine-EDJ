# Expansion eleven: reporting shape

**Owner:** C1. Status of every firm here: **mapped, not ingested** (issue #2).
Groups follow [BRIEF.md](BRIEF.md). Entries in `config/entities.yaml` (`expansion:`) carry the
aliases and `expected_sources` the system uses for honest "no evidence" answers.

CIKs and filing forms were checked on SEC EDGAR on 2026-10-10 (forms filed since 2024-10-01).
Segment names were confirmed by EDGAR full-text search in filings since 2025-06-01.
Anything not checked is marked TODO-verify. Never guess a CIK.

| id | Firm | Group | CIK | SEC forms filed | Wealth business reported as | Notes |
|---|---|---|---|---|---|---|
| AMP | Ameriprise Financial | Pure-play public | 820027 | 10-K, 10-Q, 8-K, DEF 14A | "Advice & Wealth Management" segment | |
| LPLA | LPL Financial Holdings | Pure-play public | 1397911 | 10-K, 10-Q, 8-K, DEF 14A | TODO-verify | Monthly activity report: TODO-verify where it is published |
| SF | Stifel Financial | Pure-play public | 720672 | 10-K, 10-Q, 8-K, DEF 14A | "Global Wealth Management" segment | |
| HOOD | Robinhood Markets | Pure-play public | 1783879 | 10-K, 10-Q, 8-K, DEF 14A | TODO-verify | Monthly "Operating Data" filed as 8-K |
| JPM | J.P. Morgan Wealth Management | Bank segment | 19617 (JPMorgan Chase & Co) | 10-K, 10-Q, 8-K, DEF 14A | Inside the "Asset & Wealth Management" segment | Same problem as Merrill: segment is not the wealth brand alone |
| WFC | Wells Fargo Advisors | Bank segment | 72971 (Wells Fargo & Company) | 10-K, 10-Q, 8-K, DEF 14A | Inside the "Wealth and Investment Management" segment | Same problem as Merrill |
| GS | Goldman Sachs Asset & Wealth Management | Bank segment | 886982 (Goldman Sachs Group) | 10-K, 10-Q, 8-K, DEF 14A | "Asset & Wealth Management" segment | Segment mixes asset management and wealth |
| UBS | UBS Group | Foreign filer | 1610520 | 20-F, 6-K | "Global Wealth Management" division | Annual report on 20-F; interim reports on 6-K |
| RBC | Royal Bank of Canada | Foreign filer | 1000275 | 40-F, 6-K | "Wealth Management" segment | Canadian filer; fiscal calendar TODO-verify |
| FID | Fidelity Investments | Private | TODO-verify | none (private) | n/a | Form ADV and research only; several Fidelity advisers on EDGAR, firm choice TODO-verify |
| VGD | Vanguard | Private | TODO-verify | none (private) | n/a | Form ADV and research only; two "VANGUARD GROUP INC" CIKs on EDGAR (735286, 102909), TODO-verify |

## What this means for answers

- Bank-segment firms (JPM, WFC, GS) need the same treatment as Merrill: a `parent`, a
  `reported_as` segment, `equivalence: partial` and a caveat, once they are promoted.
- Foreign filers need new doc types (20-F, 40-F, 6-K) and possibly a different fiscal calendar (RBC, TODO-verify).
- Private firms have no financial filings; answers about them must show the thinness.
- Until a firm is promoted and ingested, questions about it get the honest "no evidence"
  answer plus its `expected_sources` (see `src/cee/answer/validate.py`).

## Not done here

- No documents ingested for any of the eleven.
- `expansion:` entries in `config/entities.yaml` keep their current fields; CIKs go in when a
  firm is promoted (BRIEF.md: only after gates 1-3 pass).
