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
- **Source**: the `source_id` in [docs/source_matrix.csv](../docs/source_matrix.csv)
  (tier 3) or the EDGAR form (tier 2) it comes from.
- **Status**: `in corpus` (checked by query on the named snapshot) or `not loaded`.
- `TODO-verify`: not checked yet; nothing marked so is a fact.

Checked against snapshot **corpus-2026-09-30** (1 document: `EDJ-10K-2025`, 335 chunks)
on 2026-10-15.

---

## Q1 - Morgan Stanley: strategy to increase net new assets

Behavior: `answer`. Entity filter: `MS`. Mode: entity.

| # | doc_id | Section that must come back | Source | Status |
|---|---|---|---|---|
| 1 | `MS-TR-<latest 4 quarters>` | Prepared remarks + Q&A where management credits NNA channels | `MS-IR-TRANSCRIPT-WEBCAST` / a transcript row | not loaded |
| 2 | `MS-10K-2025` | Item 7, Wealth Management segment discussion | EDGAR 10-K | not loaded |
| 3 | `MS-DECK-2025Q4-strategic-update` | Wealth Management pages (4Q25 Strategic Update, Jan 15 2026, per source matrix) | `MS-IR-DECK` | not loaded |
| 4 | `MS-SUPP-<latest>` | Wealth Management net new assets line | `MS-IR-SUPPLEMENT` | not loaded |

Must not return: chunks from any entity other than MS. Chunks older than the latest
strategy statement may come back but must be dated (passes_if: 2024 strategy is not
today's strategy).

Today: `resolve` -> entities `[MS]`, mode entity -> **0 hits** (nothing loaded). Correct
gap behavior for the current corpus.

---

## Q4 - Merrill: advisor growth strategy, and how it changed (TRAP 1 of 3)

Behavior: `answer`. Entity filter: Merrill = `entity=MER` OR (`entity=BAC` AND
`segment` in GWIM/Merrill). Mode: entity.

| # | doc_id | Section that must come back | Source | Status |
|---|---|---|---|---|
| 1 | `BAC-TR-<latest 4 quarters>` | GWIM / Merrill commentary only (advisor pipeline, headcount, sourcing) | `BAC-IR-TRANSCRIPT-EARNINGS` | not loaded |
| 2 | `BAC-10K-2025` | Global Wealth & Investment Management segment (segment=GWIM) | EDGAR 10-K | not loaded |
| 3 | `MER-PR-<date>-NN` | Merrill press releases on advisor development / recruiting | `MER-BOFANEWS-PRESS`, `MER-PRN-PRESS` | not loaded |
| 4 | `MER-TRADE-<date>` | Trade press on Merrill advisor sourcing | trade press (C2) - TODO-verify source_id | not loaded |

**Must not return (the trap):**
- Any `BAC` chunk whose `segment` is not GWIM or Merrill: Consumer Banking, Global
  Banking, Global Markets, firm-wide hiring, headcount for all of BAC.
- Merrill Edge material: it sits in Consumer Banking, not GWIM (verified by C1 in
  `config/entities.yaml`, quoting BAC-10K-2024).
- Any EDJ, MS, SCHW, RJF chunk.

Scoring: one BAC chunk without a GWIM/Merrill segment in the hit list = **fail**, however
many correct chunks come back (questions.yaml notes).

Today: `resolve` -> entities `[MER]` -> **0 hits**; no EDJ text leaks in. Correct for the
current corpus. Re-check once any BAC filing is loaded: that is when the trap can fail.

---

## Q11 - How each of the five defines and reports advisor headcount

Behavior: `answer`. Entity filter: all five (MS, SCHW, EDJ, BAC/MER-GWIM, RJF). Mode:
entity, with a quota per firm so no firm fills the list (specs/retrieval.md, Q7 rule).

| # | doc_id | Section that must come back | Source | Status |
|---|---|---|---|---|
| 1 | `EDJ-10K-2025` | `#130` Item 7 highlights table: "Financial advisors (actual): At year end 20,425 ... Average 20,331" | EDGAR 10-K | **in corpus** |
| 2 | `EDJ-10K-2025` | `#131` Item 7 overview: "ended the year with 20,425 financial advisors" | EDGAR 10-K | **in corpus** |
| 3 | `EDJ-10K-2025` | `#148` Item 7 segment table: advisors at year end by segment (U.S. / Canada) | EDGAR 10-K | **in corpus** |
| 4 | `EDJ-10K-2025` | `#29` Item 1 Human Capital: onboarding, trainees study for exams (context for who counts) | EDGAR 10-K | **in corpus** |
| 5 | `MS-10K-2025`, `MS-SUPP-<latest>` | Wealth Management advisor headcount + footnote definition | EDGAR 10-K, `MS-IR-SUPPLEMENT` | not loaded |
| 6 | `SCHW-10K-2025` | Advisor / employee headcount definition | EDGAR 10-K | not loaded |
| 7 | `BAC-10K-2025`, `BAC-SUPP-<latest>` | GWIM advisor headcount + definition (segment=GWIM only) | EDGAR 10-K, `BAC-IR-SUPPLEMENT` | not loaded |
| 8 | `RJF-10K-2025`, `RJF-SUPP-<latest>` | PCG advisor count by affiliation model + definition | EDGAR 10-K, `RJF-IR-SUPPLEMENT` | not loaded |

Must not return: BAC chunks outside GWIM (same rule as Q4); headcount of non-advisor
staff (home office associates, CSTPs) presented as advisors.

**Gap found:** EDJ-10K-2025 reports "Financial advisors (actual)" but no chunk says what
the count includes or excludes (e.g. whether trainees in the onboarding phase count).
`TODO-verify` (C1): check the EDJ 10-Qs / other EDJ sources; if none defines it, the
correct Q11 answer says "EDJ does not state its definition".

Today: `resolve` -> entities `[]`, mode theme ("each of the five" is not mapped) ->
8 EDJ hits: `#276, #11, #179, #222, #58, #71, #1, #178`. **Misses #130, #131, #148**,
the chunks that hold the number. Finding for S1 (see below).

---

## Q22 - Net new assets by quarter for each of the five, with each definition

Behavior: `answer`. Entity filter: all five. Mode: entity, quota per firm. A firm that
does not report NNA must come back as "not reporting", never filled with a neighbour
metric (questions.yaml).

| # | doc_id | Section that must come back | Source | Status |
|---|---|---|---|---|
| 1 | `EDJ-10K-2025` | `#130` "Net new assets for the year ($ billions)(2) $74 $74 $97" + footnote (2) definition: "cash and securities inflows and outflows, excluding mutual fund capital gain distributions received by U.S. clients" | EDGAR 10-K | **in corpus** |
| 2 | `EDJ-10K-2025` | `#148` NNA by segment for the period | EDGAR 10-K | **in corpus** |
| 3 | `EDJ-10Q-2026Q1`, `-2026Q2` | Quarterly NNA (the 10-K is annual only) | EDGAR 10-Q | not loaded |
| 4 | `MS-SUPP-<latest 4 quarters>` | Wealth Management net new assets + definition | `MS-IR-SUPPLEMENT` | not loaded |
| 5 | `SCHW-MONTHLY-<months>`, `SCHW-SUPP-<latest>` | Core net new assets + definition | `SCHW-IR-MONTHLY`, `SCHW-IR-SUPPLEMENT` | not loaded |
| 6 | `BAC-SUPP-<latest>` | GWIM client balance flows (segment=GWIM only) | `BAC-IR-SUPPLEMENT` | not loaded |
| 7 | `RJF-SUPP-<latest>` | PCG asset flows + definition | `RJF-IR-SUPPLEMENT` | not loaded |
| 8 | `MS-PR-<date>`, `RJF-PR-<date>` | Earnings releases (backup for supplement figures) | `MS-IR-PRESS-EARNINGS`, `RJF-IR-PRESS-EARNINGS` | not loaded |

Whether BAC and RJF report a metric on an NNA basis at all: `TODO-verify` (C1). If not,
the expected result is the "not reporting" marker, not a substitute metric.

Must not return: a neighbour metric (e.g. total client assets, AUM change) in place of
NNA without a label; BAC chunks outside GWIM.

Today: `resolve` -> entities `[]`, mode theme -> 8 EDJ hits: `#38, #131, #54, #126,
#170, #292, #92, #173`. Gets #131 (the $74B sentence) but **misses #130**, which holds the
definition the question asks for.

---

## Q26 - What's new on Raymond James in the last 90 days

Behavior: `answer`. Entity filter: `RJF`. **Time window in SQL**: `published_at` within
90 days of the day asked (asked 2026-10-15 -> 2026-07-17 to 2026-10-15). Order newest
first.

| # | doc_id | Section | Source | Status |
|---|---|---|---|---|
| 1 | `RJF-MONTHLY-<month>` | Monthly operating data 8-Ks inside the window | `RJF-IR-MONTHLY` (8-K "RJF OPERATING DATA", entities.yaml) | not loaded |
| 2 | `RJF-PR-<date>-NN` | Press / earnings releases inside the window | `RJF-IR-PRESS-EARNINGS`, `RJF-NEWSROOM-PRESS`, `RJF-GNW-PRESS` | not loaded |
| 3 | `RJF-TR-<quarter>` | Earnings call inside the window | `RJF-IR-TRANSCRIPT-WEBCAST` | not loaded |
| 4 | `RJF-10Q-<quarter>` | 10-Q filed inside the window | EDGAR 10-Q | not loaded |

Exact documents depend on what is loaded and their `published_at`: `TODO-verify` once
RJF items are ingested. The rule, not the list, is the test.

**Must not return:** anything with `published_at` before the window start - this is the
spec acceptance item ("Q26 returns nothing older than 90 days"). Any non-RJF chunk.

Today: `resolve` -> entities `[RJF]` -> 0 hits (nothing loaded). **`Query` has no time
window field**: "last 90 days" is not parsed, so the window is not enforced yet.

---

## Findings for retrieval work (not fixed in #8)

1. **"Each of the five" is not resolved** (Q11, Q22): `resolve()` returns no entities and
   falls back to theme mode. Expected: all five, with a per-firm quota.
2. **Q11 misses the number** (`EDJ-10K-2025#130`, `#131`, `#148`): the table chunks that
   hold advisor headcount rank below risk-factor text. Synonyms ("headcount" ->
   "financial advisors") would likely help (#7).
3. **No time window** (Q26, Q27): `Query` has no `window`; spec requires SQL filtering.
4. **Trap Q4/Q27/Q30 cannot fail yet**: no BAC document is loaded. Re-run these the first
   snapshot that has BAC.

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
