# Expected retrieval results (hand-written)

Owner: S1. Issue #8. Spec: [specs/retrieval.md](../specs/retrieval.md).
Questions: [questions.yaml](questions.yaml) (this file never changes it).

What retrieval **should** return for five Tier-1 questions, and what it **must not**
return. Used to score retrieval changes ("hit rate vs expected sources" and "refusal
accuracy", specs/retrieval.md).

How to read it:
- **chunk_id** (`doc_id#seq`): the chunk that holds the passage, with a short quote so the
  passage can be found again if chunking changes. `doc_id`s follow `specs/filings.md`
  and `specs/transcripts-ir.md`.
- **Status**:
  - `in corpus`: the document is in `data/manifest.csv` on main (68 documents: 10-K/10-Q,
    transcripts, supplements, decks, earnings releases) and the chunk ID and quote were
    checked against a database loaded from that manifest.
  - `not loaded`: no such document in the manifest yet. Names are proposals until the
    ingest owner assigns the real `doc_id`.
- `TODO-verify`: not checked yet; nothing marked so is a fact.

Checked 2026-10-19 against the local database loaded from main's manifest (68 documents).
"Today" lines are `resolve()` + `search()` runs on that database the same day.

---

## Q1 - Morgan Stanley: strategy to increase net new assets

Behavior: `answer`. Entity filter: `MS`. Mode: entity.

| # | chunk_id | Passage that must come back | Status |
|---|---|---|---|
| 1 | `MS-TR-2026Q2#3` | Management framing: "a record $148 billion in organic net new assets, driven by large IPOs of late-stage private workplace clients. Growth led by workplace relationships reflects a cornerstone of our client acquisition ..."; "adviser-led and E*TRADE channels" | in corpus |
| 2 | `MS-TR-2026Q2#13`, `#15` | "investments in our client acquisition funnel"; "Stock plan IPO flows represented just over half of the overall NNA this quarter" | in corpus |
| 3 | `MS-TR-2026Q3#2`, `#8` | "net new assets of $232 billion"; "In the first 9 months of the year, we have delivered roughly $0.5 trillion of net new assets" | in corpus |
| 4 | `MS-TR-2026Q1#2`, `#7`, `#8` | "Our client acquisition funnel remains unrivaled ... $118 billion of net new assets"; "contributions across channels" | in corpus |
| 5 | `MS-PR-2026-10-14-01#5`, `MS-PR-2026-07-15-01#5` | "Record net new assets were $232 billion, with just over half associated with IPO-related flows"; Q2 same pattern | in corpus |
| 6 | `MS-10K-2025#125` | "Wealth Management supports clients through three channels: Advisor-Led, Self-Directed and Workplace" | in corpus |
| 7 | `MS-10K-2025#127`, `#164`, `#166` | FY2025 NNA $356 billion; NNA table 2025/2024/2023; definition + drivers ("our ability to attract and retain financial advisors and clients") | in corpus |
| 8 | `MS-SUPP-2026Q3#16`, `MS-SUPP-2026Q2#16`, `MS-SUPP-2026Q1#14` | Wealth Management Metrics: "Net new assets $ 232.4 / $ 148.1 / $ 118.4" by quarter | in corpus |
| 9 | `MS-DECK-<latest>` | Strategic update pages on Wealth Management | not loaded |

Dating rule (passes_if): the 2026Q2-Q3 framing (workplace / stock-plan IPO flows) is not
the 2026Q1 framing ("contributions across channels"); an answer must date each.

Must not return: chunks from any entity other than MS; Investment Management or
Institutional Securities chunks presented as Wealth Management NNA.

Today: `resolve` -> `[MS]`, entity -> `MS-PR-2026-01-15-01#18`, `MS-PR-2026-04-15-01#15`,
`MS-SUPP-2026Q1#43`, `MS-10Q-2025Q2#74`, `MS-10Q-2026Q1#18`, `MS-10Q-2026Q1#51`,
`MS-SUPP-2026Q2#37`, `MS-SUPP-2026Q3#38`. All MS (filter holds), but mostly footnotes;
**no transcript chunk** comes back, so management's framing (rows 1-4) is missed.

---

## Q4 - Merrill: advisor growth strategy, and how it changed (TRAP 1 of 3)

Behavior: `answer`. Entity filter: Merrill = `entity=MER` OR (`entity=BAC` AND
`segment` in GWIM/Merrill). Mode: entity.

| # | chunk_id | Passage that must come back | Status |
|---|---|---|---|
| 1 | `BAC-TR-2026Q1#20` | "adviser productivity and long-term client relationships. We're driving productivity higher on both newer and existing members of our financial advisers team, and we continue to attract talent" | in corpus |
| 2 | `BAC-TR-2026Q1#48` | Analyst asks for "recruiting or retention commentary" on the wealth strategy; CEO answer | in corpus |
| 3 | `BAC-TR-2026Q2#13`, `#14` | "both Merrill and the Private Bank continued to attract talented advisers"; "strong adviser productivity ... AI-enabled tools that help advisers" | in corpus |
| 4 | `BAC-TR-2026Q2#38` | "keep growing the sales force. Well, adviser attrition is now at near historic lows" | in corpus |
| 5 | `BAC-TR-2026Q3#13` | Merrill growth: "Merrill added about 4,200 net new households with at least $500,000 in assets" | in corpus |
| 6 | `BAC-10K-2025#245`, `#246`, `#247` | GWIM = Merrill Wealth Management + Private Bank; "a network of financial advisors"; Merrill revenue $20.7 billion | in corpus |
| 7 | `BAC-10Q-2026Q2#88`-`#91` | GWIM: Merrill Wealth Management revenue by quarter | in corpus |
| 8 | `MER-PR-<date>-NN`, `MER-TRADE-<date>` | Merrill press releases and trade press on advisor development / recruiting | not loaded |

**Gap:** no stored document gives a Merrill advisor **count** (the 10-K/10-Q, the three
GWIM supplement pages, decks and earnings releases list balances and flows, and
"Business Leadership" award counts such as ">300 Merrill advisors on Barron's 2026 Top
1,500" - not headcount). The "how has it changed" half rests on transcripts only.

**Must not return (the trap):**
- `BAC-10K-2025#18`: "the Corporation hired over 18,000 teammates" / "building a strong
  pipeline of talent" - **BAC-wide hiring, the text that makes a wrong answer read well**.
- `BAC-10K-2025#16`, `#172`: BAC-wide headcount ("approximately 213,000 employees").
- `BAC-TR-2026Q1#9`, `BAC-TR-2026Q2#32`, `#33`, `#45`: "pipelines" = investment banking
  pipelines, not advisor pipelines.
- `BAC-DECK-2026Q1#55`, `BAC-DECK-2026Q2#36`, `BAC-DECK-2026Q3#45` and the matching
  press-release bullets: award counts, not advisor headcount (may come back only if
  labeled as awards).
- Consumer Banking, Global Banking, Global Markets chunks (e.g. `BAC-10Q-2026Q2#77`,
  `#78` deposit flows); Merrill Edge material (Consumer Banking, per C1 in
  `config/entities.yaml`).
- Any EDJ, MS, SCHW, RJF chunk.

Segment note: all 4,783 BAC chunks have `segment = None` (#37 not merged), so the SQL
filter cannot tell `#246` from `#18`. `BAC-10K-2025#1041` holds GWIM **and** Global
Banking text in one chunk. Transcripts and press releases are one "Document" section, so
GWIM tagging there must work at chunk level.

Scoring: one BAC chunk without a GWIM/Merrill segment in the hit list = **fail**, however
many correct chunks come back (questions.yaml notes).

Today: `resolve` -> `[MER]`, entity -> **0 hits**. The trap does not fire (no BAC chunk
leaks in) but nothing correct comes back either: with no segment tags the Merrill filter
matches no BAC chunk. Correct behavior needs #37.

---

## Q11 - How each of the five defines and reports advisor headcount

Behavior: `answer`. Entity filter: all five (MS, SCHW, EDJ, BAC/MER-GWIM, RJF). Mode:
entity, with a quota per firm so no firm fills the list (specs/retrieval.md, Q7 rule).

| # | Firm | chunk_id | Passage that must come back | Status |
|---|---|---|---|---|
| 1 | EDJ | `EDJ-10K-2025#130` | "Financial advisors (actual): At year end 20,425 ... Average 20,331" | in corpus |
| 2 | EDJ | `EDJ-10K-2025#131`, `#148` | "ended the year with 20,425 financial advisors"; by segment (U.S. / Canada) | in corpus |
| 3 | EDJ | `EDJ-10Q-2026Q2#60` | "Financial advisors (actual): At period end 20,514" | in corpus |
| 4 | EDJ | `EDJ-10K-2025#29` | Human Capital: onboarding, trainees study for exams (context for who counts) | in corpus |
| 5 | RJF | `RJF-10K-2025#227` | "Employees 3,878 / Independent contractors 5,065 / Total advisors 8,943" | in corpus |
| 6 | RJF | `RJF-10K-2025#228` | Definition: "Advisors in our RCS division are not included in our financial advisor metric although their client assets are included in PCG AUA" | in corpus |
| 7 | RJF | `RJF-10K-2025#24` | "approximately 19,500 associates (including 3,878 employee financial advisors) and 5,065 independent advisors" | in corpus |
| 8 | MS | `MS-10K-2025#167`, `MS-SUPP-2026Q3#38` | Nearest definition: advisor-led client assets are accounts "that have a Wealth Management representative assigned" (no count) | in corpus |
| 9 | BAC/MER | `BAC-10K-2025#246` | "a network of financial advisors" (no count) | in corpus |
| 10 | SCHW | `SCHW-10K-2025#18`, `SCHW-TR-2026Q1#3` | Names Financial Consultants / Wealth Consultants; "continuing to hire financial consultants and wealth advisers" (no count) | in corpus |

**Not reported in any stored document** (correct answer says so, not a substitute):
- **MS**: no advisor count in 10-K, 10-Qs, supplements (three quarters), transcripts or
  earnings releases.
- **BAC/Merrill**: no advisor count anywhere stored (see Q4 gap).
- **SCHW**: no advisor headcount; its headcount metric is full-time equivalent employees
  (`SCHW-10K-2025#120` definition, `#178` table) - a neighbour metric.
- **EDJ**: counts but no include/exclude definition (10-K, 2026Q2 10-Q). `TODO-verify` (C1).
- **RJF**: supplements (`RJF-SUPP-2026Q1`, `-2026Q2`) report advisor **compensation**, not
  advisor counts; the count and definition come from the 10-K only.

Must not return as advisor counts: BAC-wide headcount (`BAC-10K-2025#16`, `#172`), SCHW
FTE employees (`SCHW-10K-2025#178`), RJF total associates (`#24` "19,500 associates") on
their own, RJF advisor compensation (`RJF-SUPP-2026Q1#14`), BAC award counts (Q4 list).

Before #89: `resolve` -> `[]`, theme ("each of the five" was not mapped) ->
`BAC-10K-2025#1083` (Item 9A controls), `RJF-10K-2025#726`, `RJF-10K-2025#90`,
`BAC-10K-2025#613`, `BAC-DECK-2026Q3#54`, `MS-10K-2025#871`, `RJF-10K-2025#27`,
`BAC-DECK-2026Q1#66`. 0 of 8 expected; 3 BAC chunks outside GWIM.

Today (2026-10-21, #89): `resolve` -> `[MS, SCHW, EDJ, MER, RJF]`, entity; synonyms
`advisor` -> adviser, `headcount` -> number of financial advisors / advisor count /
financial advisors (actual). Top-8: `RJF-TR-2026Q2#4`, `#19`, `#24`, `EDJ-10K-2025#21`,
`RJF-TR-2026Q1#34`, `#4`, `EDJ-10K-2025#42`, `#41`. **No BAC chunk** (trap holds; Merrill
returns nothing until #37). Top-20 firms: EDJ, RJF, SCHW. **Still 0 of 8 expected**:
`EDJ-10K-2025#130` and `RJF-10K-2025#227` are not in the top-20 (rank ~125 of 413 EDJ
matches and ~354 of 1,211 RJF matches before the synonym bonus). Short table chunks lose
to prose that repeats the question's words; `#227` says "Total advisors", which no
synonym covers. Needs table-aware ranking (open item on #89), not more synonyms.

---

## Q22 - Net new assets by quarter for each of the five, with each definition

Behavior: `answer`. Entity filter: all five. Mode: entity, quota per firm. A firm that
does not report NNA must come back as "not reporting", never filled with a neighbour
metric (questions.yaml).

| # | Firm | Quarterly figures | Definition | Status |
|---|---|---|---|---|
| 1 | EDJ | 10-Q Item 2 "Net new assets for the period": `EDJ-10Q-2026Q2#60`, `-2026Q1#51`, `-2025Q3#67`, `-2025Q2#64`; annual `EDJ-10K-2025#130` ($74B) | `EDJ-10Q-2026Q2#60` (3): "cash and securities inflows and outflows, including fees and commissions and excluding mutual fund capital gain distributions received by U.S. clients" | in corpus |
| 2 | MS | Supplements `MS-SUPP-2026Q3#16` (232.4), `-2026Q2#16` (148.1), `-2026Q1#14` (118.4; prior quarter 122.3); 10-Qs `MS-10Q-2026Q2#57`, `-2026Q1#48`, `-2025Q3#56`, `-2025Q2#56`; releases `MS-PR-2026-01-15-01#2` (4Q25 $122.3B) | `MS-SUPP-2026Q1#42` / `MS-10K-2025#166`: "client asset inflows, including interest, dividends and asset acquisitions, less client asset outflows, and excluding the impact of business combinations/divestitures and the impact of fees and commissions" | in corpus |
| 3 | SCHW | Releases `SCHW-PR-2026-01-21-01#2` (4Q25 core $163.9B), `SCHW-PR-2026-07-21-01#2` (2Q26 $119.8B); decks `SCHW-DECK-2026Q3#7`, `#20`; 10-Qs `SCHW-10Q-2026Q2#16`, `-2026Q1#16`, `-2025Q3#16`, `-2025Q2#16` | `SCHW-10K-2025#122` net new client assets "Total inflows of client cash and securities to Schwab less client outflows ... Capital gains distributions are excluded"; `#119` / `SCHW-DECK-2026Q3#20` core = before significant one-time flows | in corpus |
| 4 | RJF | Releases `RJF-PR-2026-07-22-01#4` ($21.7B fiscal Q3), `RJF-PR-2026-04-22-01#3` ($23.0B), `RJF-PR-2026-01-28-01#3` ($30.8B), `RJF-PR-2025-10-22-01#4` ($17.9B); 10-Qs `RJF-10Q-2026Q2#305`, `-2026Q1#298`, `-2025Q4#236`, `-2025Q2#294` | `RJF-10Q-2026Q2#306`, `RJF-SUPP-2026Q1#43`: domestic PCG "client inflows, including dividends and interest, less ... client outflows, including commissions, advisory fees, and other fees" | in corpus |
| 5 | BAC/Merrill | **not reporting NNA.** BAC reports "net client flows" and "AUM flows" instead (`BAC-TR-2026Q3#13` "net client flows were about $38 billion, including approximately $20 billion of AUM flows"; `BAC-PR-2026-10-14-01#11`) | - | in corpus (checked) |
| 6 | SCHW | Monthly activity reports | | not loaded |

Note on bases: EDJ and SCHW exclude capital-gain distributions; MS excludes fees and
acquisitions; RJF is domestic PCG only, net of fees; BAC has no NNA. Each number needs its
definition beside it, and quarters differ (RJF fiscal year ends 30 September).

Must not return as NNA: BAC net client flows / AUM flows unlabeled; SCHW money-fund
roll-forward (`SCHW-10Q-2026Q2#56`); MS fee-based asset flows (`MS-PR-2026-04-15-01#15`)
as if NNA; any AUM or client-asset change; BAC chunks outside GWIM.

Before #89: `resolve` -> `[]`, theme -> `RJF-PR-2026-04-22-01#4`, `#3`,
`RJF-PR-2026-07-22-01#4`, `#5`, `MS-PR-2026-04-15-01#15`, `MS-10Q-2025Q3#18`,
`RJF-PR-2026-01-28-01#3`, `MS-10Q-2026Q1#18`. NNA from MS and RJF only.

Today (2026-10-21, #89): `resolve` -> `[MS, SCHW, EDJ, MER, RJF]`, entity; synonyms
`net new assets` -> NNA / core net new assets. Top-8: `RJF-PR-2026-04-22-01#4`, `#3`,
`RJF-PR-2026-07-22-01#4`, `#5`, `SCHW-TR-2026Q2#23`, `SCHW-TR-2026Q3#25`,
`MS-PR-2026-04-15-01#15`, `MS-10Q-2026Q2#58`. **Top-20 holds NNA chunks from MS, RJF and
SCHW** (SCHW via transcripts, e.g. "more than 5% NNA growth"; also `SCHW-TR-2026Q1#31`).
No BAC chunk. Still missing: EDJ (`EDJ-10Q-2026Q2#60` etc.), every definition chunk, and
SCHW's 10-Q figures; `MS-PR-2026-04-15-01#15` is still the fee-based-flows footnote, a
neighbour metric (finding 7). Per-firm quotas (#59) should bring EDJ in.

---

## Q26 - What's new on Raymond James in the last 90 days

Behavior: `answer`. Entity filter: `RJF`. **Time window in SQL**: `published_at` within
90 days of the day asked. Scored as of **2026-10-19** -> window 2026-07-21 to 2026-10-19.
Order newest first.

| # | doc_id (published) | Example chunks | Status |
|---|---|---|---|
| 1 | `RJF-10Q-2026Q2` (2026-08-05) | `#245` "net new assets driven by financial advisor recruiting and retention"; `#305` PCG NNA | in corpus |
| 2 | `RJF-PR-2026-07-22-01` (2026-07-22) | `#0`, `#4` fiscal Q3 results, "Domestic Private Client Group net new assets of $21.7 billion" | in corpus |
| 3 | `RJF-TR-2026Q2` (2026-07-22) | fiscal Q3 earnings call | in corpus |
| 4 | `RJF-SUPP-2026Q2` (2026-07-22) | fiscal Q3 supplement | in corpus |
| 5 | `RJF-DECK-2026Q2` (2026-07-22) | `#4` key metrics: "$21.7B \| 5.5% growth rate Domestic PCG net new assets" (value printed before its label; the next figure, $58.8B, is cash sweep balances) | in corpus |
| 6 | `RJF-MONTHLY-<month>`, `RJF-PR-<other>` | monthly operating data 8-Ks, other news | not loaded |

**The window moves.** Rows 2-5 (2026-07-22) leave the window on 2026-10-21; from then
only `RJF-10Q-2026Q2` is inside until the fiscal Q4 release (late October) is loaded.
Re-derive the list on the day of scoring - the rule, not the list, is the test.

**Must not return** (published before 2026-07-21): `RJF-PR-2026-04-22-01`,
`RJF-TR-2026Q1`, `RJF-SUPP-2026Q1`, `RJF-DECK-2026Q1` (all 2026-04-22),
`RJF-10Q-2026Q1` (2026-05-06), `RJF-PR-2026-01-28-01`, `RJF-10Q-2025Q4` (2026-02-06),
`RJF-10K-2025` (2025-11-25), `RJF-PR-2025-10-22-01`, `RJF-10Q-2025Q2` (2025-08-06); any
non-RJF chunk. This is the spec acceptance item ("Q26 returns nothing older than 90 days").

Today: `resolve` -> `[RJF]`, entity -> `RJF-10K-2025#351`, `#352`, `RJF-10Q-2025Q2#414`,
`RJF-10Q-2025Q4#343`, `#344`, `#236`, `RJF-10Q-2026Q1#415`, `RJF-10Q-2026Q2#426`.
**7 of 8 hits are older than the window** (only `RJF-10Q-2026Q2#426`, a mortgage
delinquency table, is inside). Fails the spec item: `Query` has no time window.

---

## Findings for retrieval work (not fixed in #8)

1. **"Each of the five" is not resolved** (Q11, Q22): `resolve()` returns no entities and
   falls back to theme mode, which returns other-firm and off-topic chunks. Expected: all
   five, with a per-firm quota. *Resolved in #89 (peer set); the quota is #59.*
2. **Q11 misses every number** (`EDJ-10K-2025#130`, `RJF-10K-2025#227`): table chunks rank
   below control-and-procedure boilerplate. Synonyms ("headcount" -> "financial
   advisors") would likely help (#7).
3. **No time window** (Q26, Q27): `Query` has no `window`; 7 of 8 Q26 hits are outside the
   90 days. Spec requires SQL filtering.
4. **Merrill filter returns nothing** (Q4, Q27, Q30): every BAC chunk has `segment = None`
   until #37 lands. Once segments exist, check `BAC-10K-2025#18` stays out.
5. **A chunk spans two segments**: `BAC-10K-2025#1041` (GWIM + Global Banking). Relevant
   to #37.
6. **Transcripts do not surface for strategy questions** (Q1): management's framing sits
   in `MS-TR-*` but numeric footnotes outrank it.
7. **Neighbour metrics come back as NNA** (Q22): fee-based flows, BAC AUM flows. A label
   or exclusion is needed before an answer uses them.
8. **Deck values print before their labels** (`RJF-DECK-2026Q2#4`: "$21.7B | 5.5% growth
   rate Domestic PCG net new assets (2) $58.8B Clients' domestic cash sweep ..."). A reader
   or number check that pairs a label with the figure after it gets the wrong number.

## Re-run

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
