# Expected retrieval results (hand-written)

Owner: S1. Issue #8. Spec: [specs/retrieval.md](../specs/retrieval.md).
Questions: [questions.yaml](questions.yaml) (this file never changes it).

What retrieval **should** return for five Tier-1 questions, and what it **must not**
return. Used to score retrieval changes ("hit rate vs expected sources" and "refusal
accuracy", specs/retrieval.md).

How to read it:
- **doc_id**: the expected document, named by the conventions in `specs/filings.md`
  (`<ENTITY>-<FORM>-<PERIOD>`) and `specs/transcripts-ir.md` (`MS-TR-2025Q2`,
  `...-DECK-...`, `...-PR-YYYY-MM-DD-NN`). `<latest>` means the newest one in the corpus
  when scored. Names of documents not yet loaded are proposals until the ingest owner
  assigns the real `doc_id`.
- **chunk_id** (`doc_id#seq`): the chunk that holds the passage, with a short quote so the
  passage can be found again if chunking changes.
- **Source**: the `source_id` in [docs/source_matrix.csv](../docs/source_matrix.csv)
  (tier 3) or the EDGAR form (tier 2) it comes from.
- **Status**:
  - `in corpus`: in snapshot corpus-2026-09-30 (only `EDJ-10K-2025`), checked by query.
  - `in manifest`: listed in `data/manifest.csv` (25 filings: 10-K + four 10-Qs for EDJ,
    MS, SCHW, BAC, RJF). Chunk IDs come from running the repo's own parser and Item
    splitter (`cee.ingest.load.parse_file` + `chunk_sections`, after #70) on the raw files;
    they match what `cee.ingest.load` writes. Not yet in a published snapshot.
  - `not loaded`: no document of this kind in the manifest yet.
- `TODO-verify`: not checked yet; nothing marked so is a fact.

Checked 2026-10-16 against the manifest (25 filings, 12,097 chunks). "Today" lines are
retrieval runs on snapshot corpus-2026-09-30 from 2026-10-15.

---

## Q1 - Morgan Stanley: strategy to increase net new assets

Behavior: `answer`. Entity filter: `MS`. Mode: entity.

| # | doc_id / chunk | Passage that must come back | Source | Status |
|---|---|---|---|---|
| 1 | `MS-10K-2025#125` | Item 7: "Wealth Management supports clients through three channels: Advisor-Led, Self-Directed and Workplace" | EDGAR 10-K | in manifest |
| 2 | `MS-10K-2025#127` | Item 7 overview: "Fee-based asset flows were $160 billion and the business added net new assets of $356 billion" | EDGAR 10-K | in manifest |
| 3 | `MS-10K-2025#164` | Item 7 table: "Net new assets $356.3 $251.7 $282.3" (2025 / 2024 / 2023) | EDGAR 10-K | in manifest |
| 4 | `MS-10K-2025#166` | Item 7 NNA definition + drivers: "our ability to attract and retain financial advisors and clients ... assets in certain client channels" | EDGAR 10-K | in manifest |
| 5 | `MS-10K-2025#167`, `#168` | Item 7 channel metrics: advisor-led client assets ("accounts that have a Wealth Management representative assigned"), self-directed, workplace | EDGAR 10-K | in manifest |
| 6 | `MS-10K-2025#25` | Item 1 competition: "different channels (i.e., advisor led, workplace and digital direct)" | EDGAR 10-K | in manifest |
| 7 | `MS-10Q-2026Q2#18`, `#57`, `#58` | Item 2: "added net new assets of $148 billion"; NNA table; NNA definition | EDGAR 10-Q | in manifest |
| 8 | `MS-10Q-2026Q1#18`, `#48` | Item 2: "added net new assets of $118 billion"; NNA table | EDGAR 10-Q | in manifest |
| 9 | `MS-TR-<latest 4 quarters>` | Prepared remarks + Q&A where management credits NNA channels | `MS-IR-TRANSCRIPT-WEBCAST` / a transcript row | not loaded |
| 10 | `MS-DECK-2025Q4-strategic-update` | Wealth Management pages (4Q25 Strategic Update, Jan 15 2026, per source matrix) | `MS-IR-DECK` | not loaded |
| 11 | `MS-SUPP-<latest>` | Wealth Management net new assets line | `MS-IR-SUPPLEMENT` | not loaded |

Note: the filings give NNA figures, channels and the definition, but management's own
"why" (which channel it credits, with what emphasis) is transcript/deck material. Until
rows 9-10 are loaded, a correct answer reports channels and figures and says the strategy
framing is not in the stored filings.

Must not return: chunks from any entity other than MS. Chunks older than the latest
strategy statement may come back but must be dated (passes_if: 2024 strategy is not
today's strategy).

Today (corpus-2026-09-30): `resolve` -> entities `[MS]`, mode entity -> **0 hits**
(nothing loaded). Correct gap behavior for that corpus.

---

## Q4 - Merrill: advisor growth strategy, and how it changed (TRAP 1 of 3)

Behavior: `answer`. Entity filter: Merrill = `entity=MER` OR (`entity=BAC` AND
`segment` in GWIM/Merrill). Mode: entity.

| # | doc_id / chunk | Passage that must come back | Source | Status |
|---|---|---|---|---|
| 1 | `BAC-10K-2025#245`, `#246` | Item 7 GWIM: "GWIM consists of two primary businesses: Merrill Wealth Management and Bank of America Private Bank"; "a network of financial advisors focused on clients with over $250,000 in total investable assets" | EDGAR 10-K | in manifest |
| 2 | `BAC-10K-2025#247` | Item 7 GWIM: "Merrill Wealth Management revenue of $20.7 billion increased nine percent"; expense up for "investments in the business, including people and technology" | EDGAR 10-K | in manifest |
| 3 | `BAC-10Q-2026Q2#88`-`#91` | Item 2 GWIM: "Merrill Wealth Management revenue of $5.7 billion increased 16 percent"; revenue by business table | EDGAR 10-Q | in manifest |
| 4 | `BAC-TR-<latest 4 quarters>` | GWIM / Merrill commentary only (advisor pipeline, headcount, sourcing) | `BAC-IR-TRANSCRIPT-EARNINGS` | not loaded |
| 5 | `BAC-SUPP-<latest>` | GWIM advisor headcount line (segment=GWIM only) | `BAC-IR-SUPPLEMENT` | not loaded |
| 6 | `MER-PR-<date>-NN` | Merrill press releases on advisor development / recruiting | `MER-BOFANEWS-PRESS`, `MER-PRN-PRESS` | not loaded |
| 7 | `MER-TRADE-<date>` | Trade press on Merrill advisor sourcing | trade press (C2) - TODO-verify source_id | not loaded |

**Gap found:** the BAC 10-K and four 10-Qs never give a Merrill advisor count or describe
the advisor development pipeline; the only advisor mentions are #246 / #1041 ("network of
financial advisors"). Advisor strategy lives in transcripts, supplements and press
(rows 4-7). Until they are loaded the correct answer is GWIM/Merrill context from rows 1-3
plus "the stored filings do not describe Merrill's advisor growth strategy".

**Must not return (the trap):**
- `BAC-10K-2025#18`: "the Corporation hired over 18,000 teammates" / "building a strong
  pipeline of talent" - **BAC-wide hiring, the exact text that makes a wrong answer read
  well**.
- `BAC-10K-2025#16`, `#172`: BAC-wide headcount ("approximately 213,000 employees").
- `BAC-10Q-2026Q2#77`, `#78`: Consumer Banking deposit flows. Any other `BAC` chunk whose
  text is not about GWIM or Merrill (Consumer Banking, Global Banking, Global Markets).
- Merrill Edge material: it sits in Consumer Banking, not GWIM (verified by C1 in
  `config/entities.yaml`, quoting BAC-10K-2024).
- Any EDJ, MS, SCHW, RJF chunk.

Segment note: every BAC chunk currently has `segment = None` (#37, GWIM tagging, not
merged), so the SQL filter cannot yet tell #246 from #18. `BAC-10K-2025#1041` holds the
GWIM description **and** the start of Global Banking in one chunk - a segment tagger
must split or flag it.

Scoring: one BAC chunk without a GWIM/Merrill segment in the hit list = **fail**, however
many correct chunks come back (questions.yaml notes).

Today (corpus-2026-09-30): `resolve` -> entities `[MER]` -> **0 hits**; no EDJ text leaks
in. Re-check the first snapshot with BAC: that is when the trap can fail.

---

## Q11 - How each of the five defines and reports advisor headcount

Behavior: `answer`. Entity filter: all five (MS, SCHW, EDJ, BAC/MER-GWIM, RJF). Mode:
entity, with a quota per firm so no firm fills the list (specs/retrieval.md, Q7 rule).

| # | doc_id / chunk | Passage that must come back | Source | Status |
|---|---|---|---|---|
| 1 | `EDJ-10K-2025#130` | Item 7 highlights table: "Financial advisors (actual): At year end 20,425 ... Average 20,331" | EDGAR 10-K | **in corpus** |
| 2 | `EDJ-10K-2025#131` | Item 7 overview: "ended the year with 20,425 financial advisors" | EDGAR 10-K | **in corpus** |
| 3 | `EDJ-10K-2025#148` | Item 7 segment table: advisors at year end by segment (U.S. / Canada) | EDGAR 10-K | **in corpus** |
| 4 | `EDJ-10K-2025#29` | Item 1 Human Capital: onboarding, trainees study for exams (context for who counts) | EDGAR 10-K | **in corpus** |
| 5 | `EDJ-10Q-2026Q2#60` | Item 2 table: "Financial advisors (actual): At period end 20,514" | EDGAR 10-Q | in manifest |
| 6 | `RJF-10K-2025#227` | Item 7 table: "Employees 3,878 / Independent contractors 5,065 / Total advisors 8,943" | EDGAR 10-K | in manifest |
| 7 | `RJF-10K-2025#228` | Item 7 definition: "Advisors in our RCS division are not included in our financial advisor metric although their client assets are included in PCG AUA" | EDGAR 10-K | in manifest |
| 8 | `RJF-10K-2025#24` | Item 1 Human Capital: "approximately 19,500 associates (including 3,878 employee financial advisors) and 5,065 independent advisors" | EDGAR 10-K | in manifest |
| 9 | `BAC-10K-2025#246` | GWIM: "network of financial advisors" (no count) | EDGAR 10-K | in manifest |
| 10 | `MS-SUPP-<latest>`, `BAC-SUPP-<latest>`, `RJF-SUPP-<latest>` | Advisor headcount lines + footnotes | IR supplements | not loaded |

**Not reported in the stored filings** (correct answer says so, not a substitute):
- **MS**: no advisor count in the 10-K or 10-Qs. `MS-10K-2025#167` defines advisor-led
  assets as accounts "that have a Wealth Management representative assigned", which is
  the nearest the filings get. Count is in the supplement (row 10).
- **BAC/Merrill**: no advisor count in the filings (see Q4 gap).
- **SCHW**: no advisor headcount at all; Schwab names Financial Consultants / Wealth
  Consultants (`SCHW-10K-2025#18`) but gives no count. Its headcount metric is
  full-time equivalent employees (`SCHW-10K-2025#120` definition, `#178` table) - a
  neighbour metric that must not be presented as advisors.
- **EDJ**: gives counts but no include/exclude definition in the 10-K or the 2026Q2 10-Q
  (`#60` footnotes (1)-(3) cover other lines). `TODO-verify` (C1): other EDJ sources.

Must not return as advisor counts: BAC-wide headcount (`BAC-10K-2025#16`, `#172`), SCHW
FTE employees (`SCHW-10K-2025#178`), RJF total associates (`#24` "19,500 associates") on
their own.

Today (corpus-2026-09-30): `resolve` -> entities `[]`, mode theme ("each of the five" is
not mapped) -> 8 EDJ hits: `#276, #11, #179, #222, #58, #71, #1, #178`. **Misses #130,
#131, #148**, the chunks that hold the number. Finding for S1 (see below).

---

## Q22 - Net new assets by quarter for each of the five, with each definition

Behavior: `answer`. Entity filter: all five. Mode: entity, quota per firm. A firm that
does not report NNA must come back as "not reporting", never filled with a neighbour
metric (questions.yaml).

| # | Firm | Quarterly figure (Item 2 of each 10-Q) | Definition | Status |
|---|---|---|---|---|
| 1 | EDJ | `EDJ-10Q-2026Q2#60`, `EDJ-10Q-2026Q1#51`, `EDJ-10Q-2025Q3#67`, `EDJ-10Q-2025Q2#64` ("Net new assets for the period ($ billions)"); segment tables `-2026Q2#79`, `#82` | `EDJ-10Q-2026Q2#60` footnote (3): "cash and securities inflows and outflows, including fees and commissions and excluding mutual fund capital gain distributions received by U.S. clients" | in manifest |
| 2 | EDJ (annual) | `EDJ-10K-2025#130` "Net new assets for the year ($ billions)(2) $74 $74 $97"; `#148` by segment | `#130` footnote (2): "... excluding mutual fund capital gain distributions received by U.S. clients" | **in corpus** |
| 3 | MS | `MS-10Q-2026Q2#57`, `MS-10Q-2026Q1#48`, `MS-10Q-2025Q3#56`, `MS-10Q-2025Q2#56` ("Net new assets $ ...") | `MS-10Q-2026Q2#58` / `MS-10K-2025#166`: "client asset inflows, including interest, dividends and asset acquisitions, less client asset outflows, and excluding the impact of business combinations/divestitures and the impact of fees and commissions" | in manifest |
| 4 | SCHW | `SCHW-10Q-2026Q2#16`, `-2026Q1#16`, `-2025Q3#16`, `-2025Q2#16` ("Net new client assets" and "Core net new client assets"); by segment `-2026Q2#80`, `#82` | `SCHW-10K-2025#122` "Net new client assets: Total inflows of client cash and securities to Schwab less client outflows ... Capital gains distributions are excluded"; `#119` core NNA excludes one-time flows "generally greater than $25 billion" | in manifest |
| 5 | RJF | `RJF-10Q-2026Q2#305`, `-2026Q1#298`, `-2025Q4#236`, `-2025Q2#294` ("Domestic PCG net new assets") | `RJF-10Q-2026Q2#306` "(1) Domestic PCG net new assets represents domestic PCG client inflows, including dividends and interest, less domestic PCG client outflows, including commissions, advisory fees ..." | in manifest |
| 6 | BAC/Merrill | **not reporting** in the filings: no NNA line in the BAC 10-K or 10-Qs | - | in manifest (checked) |
| 7 | MS, SCHW, BAC, RJF | Supplements, Schwab monthly reports, earnings releases (`MS-SUPP`, `SCHW-MONTHLY`, `BAC-SUPP#GWIM`, `RJF-SUPP`, `MS-PR`, `RJF-PR`) | | not loaded |

Note on bases: the four reporting firms use four different bases (EDJ and SCHW exclude
capital-gain distributions; MS excludes fees and acquisitions; RJF is domestic PCG only,
net of fees). The answer must show each definition beside its numbers.

Must not return as NNA: BAC "positive AUM flows" (`BAC-10Q-2026Q2#30`) or GWIM client
balances; SCHW money-fund roll-forward (`SCHW-10Q-2026Q2#56`); any client-asset or AUM
change; BAC chunks outside GWIM.

Today (corpus-2026-09-30): `resolve` -> entities `[]`, mode theme -> 8 EDJ hits: `#38,
#131, #54, #126, #170, #292, #92, #173`. Gets #131 (the $74B sentence) but **misses
#130**, which holds the definition the question asks for.

---

## Q26 - What's new on Raymond James in the last 90 days

Behavior: `answer`. Entity filter: `RJF`. **Time window in SQL**: `published_at` within
90 days of the day asked. Scored as of **2026-10-16** -> window 2026-07-18 to 2026-10-16.
Order newest first.

| # | doc_id | Section | Source | Status |
|---|---|---|---|---|
| 1 | `RJF-10Q-2026Q2` (published 2026-08-05) | Item 2 MD&A, e.g. `#245` "net new assets driven by financial advisor recruiting and retention", `#305` quarterly PCG NNA | EDGAR 10-Q | in manifest |
| 2 | `RJF-MONTHLY-<month>` | Monthly operating data 8-Ks inside the window | `RJF-IR-MONTHLY` (8-K "RJF OPERATING DATA", entities.yaml) | not loaded |
| 3 | `RJF-PR-<date>-NN` | Press / earnings releases inside the window | `RJF-IR-PRESS-EARNINGS`, `RJF-NEWSROOM-PRESS`, `RJF-GNW-PRESS` | not loaded |
| 4 | `RJF-TR-<quarter>` | Earnings call inside the window | `RJF-IR-TRANSCRIPT-WEBCAST` | not loaded |

The rule, not the list, is the test: re-derive the window on the day of scoring.

**Must not return** (published before 2026-07-18):
- `RJF-10Q-2026Q1` (2026-05-06), `RJF-10Q-2025Q4` (2026-02-06), `RJF-10K-2025`
  (2025-11-25), `RJF-10Q-2025Q2` (2025-08-06).
- Any non-RJF chunk.

This is the spec acceptance item ("Q26 returns nothing older than 90 days"). With the
current manifest, a correct run returns chunks from exactly one document.

Today (corpus-2026-09-30): `resolve` -> entities `[RJF]` -> 0 hits (nothing loaded).
**`Query` has no time window field**: "last 90 days" is not parsed, so the window is not
enforced yet.

---

## Findings for retrieval work (not fixed in #8)

1. **"Each of the five" is not resolved** (Q11, Q22): `resolve()` returns no entities and
   falls back to theme mode. Expected: all five, with a per-firm quota.
2. **Q11 misses the number** (`EDJ-10K-2025#130`, `#131`, `#148`): the table chunks that
   hold advisor headcount rank below risk-factor text. Synonyms ("headcount" ->
   "financial advisors") would likely help (#7).
3. **No time window** (Q26, Q27): `Query` has no `window`; spec requires SQL filtering.
4. **Trap Q4/Q27/Q30 cannot fail yet**: no BAC document is in the snapshot. Once BAC
   filings load, every BAC chunk has `segment = None` until #37 lands, so the Merrill
   filter (`BAC` AND segment GWIM/Merrill) will return **zero** BAC chunks, and a looser
   filter would return `BAC-10K-2025#18`. Re-run these the first snapshot that has BAC.
5. **A chunk spans two segments**: `BAC-10K-2025#1041` (Item 8 segment note) holds GWIM
   and Global Banking text together. Relevant to #37 (segment tagging).
6. **Most "strategy" evidence is not in filings**: Q1 and Q4 need transcripts, decks and
   supplements to pass in full; the filings give figures and definitions only.

## Re-run

Retrieval on the loaded database:

```bash
.venv/bin/python - <<'EOF'
import yaml
from cee.retrieve.fts import resolve, search
qs = {q["id"]: q for q in yaml.safe_load(open("evals/questions.yaml"))["questions"]}
for i in ["Q1", "Q4", "Q11", "Q22", "Q26"]:
    q = resolve(qs[i]["text"])
    print(i, q.entities, q.mode, [h.chunk_id for h in search(q)])
EOF
```

Chunk IDs above were found without the database by parsing the raw files (needs
`requirements-ingest.txt` and the raw files from the corpus share):
`parse_file(row, path)` then `chunk_sections(...)` from `cee.ingest.load` /
`cee.ingest.chunk`, for every row of `read_manifest()`.
