# Team

Seven people: one tech lead and six analysts, split 3 corpus / 2 search and answer / 1 surface.
Everyone writes code with Claude Code. Rules for how we work: [CLAUDE.md](../CLAUDE.md).

## Roles

| Role | Name | Owns | Spec | Key questions |
|---|---|---|---|---|
| C1 Filings and structured data (also domain owner) | Jingran Fang | EDGAR, Form ADV, quarterly supplements, metric definitions, `source_registry`, segment tagging rules, `config/entities.yaml` | [filings](../specs/filings.md) | Q11, Q22-25, Q28-30 |
| C2 Transcripts and IR | Mingmin Kong | Earnings calls, investor-day PDFs, press releases, trade press, date field quality | [transcripts-ir](../specs/transcripts-ir.md) | Q1-6, Q13, Q26, Q27 |
| C3 Thematic research | Jieyu Hu | Tier 5 sources, topics taxonomy (from W3) | [thematic](../specs/thematic.md) | Q16-21 |
| S1 Retrieval | Yi-chen Wu | FTS, synonyms, three retrieval modes, segment hard filter, quotas, dedupe, time windows | [retrieval](../specs/retrieval.md) | Q4, Q7, Q21, Q26, Q27, Q30 |
| S2 Answer and citations | Jiapeng Liu | Prompt, Answer JSON, citation and number checks, caveat insertion, coverage and gaps, the normative boundary | [answer-citations](../specs/answer-citations.md) | Q12, Q19, Q24, Q25, Q28-30 |
| U1 Interface | Yiqi Zhang | Streamlit, filters, source viewer with page highlight, tier labels, coverage view, feedback button | [ui](../specs/ui.md) | all |

**Tech lead (TL, Yueyang Du):** skeleton, environment, PDF extractors, glue code, weekly corpus
snapshot, PR review and merge, main-branch safety net (see [DASHBOARD.md](DASHBOARD.md)).
Owns no feature area.

**Corpus intake (from W4, re-planned 2026-10-18):** document packages a teammate shares in the
team chat (transcripts from a licensed seat, IR PDFs) go to the TL, who converts, dates,
registers and loads them in one PR per source type (#76, #77, #78;
`scripts/convert_transcript_pdfs.py`). The TL also ran the first 10-K/10-Q fetch (#69). C1 and C2
keep the routes they fetch themselves and own the quality work: segment tags, metric
definitions, backfill to eight quarters, dates. Before starting an ingestion issue, check
`data/manifest.csv` for what is already stored.

**Domain owner = C1:** owns the question bank and entity taxonomy, is the contact with the
project lead, and posts the weekly X/30 number.

**Evaluation rotation:** from W6 every person scores 5 questions per week and records the
snapshot version (see [PROGRESS.md](PROGRESS.md)). Rotate so each question is seen by
different people over the term.

## Week by week

The term runs W2-W12 on the board (W2 starts 2026-09-28). The W1 and W2 rows below are both scheduled in W2.

| Week | C1 | C2 | C3 | S1 | S2 | U1 | TL |
|---|---|---|---|---|---|---|---|
| W1 | Review question bank with project lead; verify core-five facts in entities.yaml | Source feasibility matrix: transcripts, IR, trade press (access, cost, terms) | Feasibility matrix: tier 5 research; library access to Cerulli | Read retrieval spec; draft synonyms list from the 30 questions | Licensing memo draft with TL (ADR-000); read answer spec | Read ui spec; sketch the screens on paper | Build skeleton (plans/0001); repo, board, ADR-000 with C1 |
| W2 | Map expansion eleven; seed source_registry | Finish matrix; pick first 3 transcripts | Draft topics taxonomy v0 | Hand-write expected results for 5 questions | Draft prompt v0 and gap wording | Run skeleton UI; list gaps vs spec | Fix skeleton on all 7 machines; first snapshot. **Gate 1** |
| W3 | Ingest EDGAR 10-K/10-Q for five; segment tagging for BAC GWIM | Ingest earnings calls (as far back as available) | **Start thematic ingestion**; tag topics | FTS + synonyms + entity/segment filter | Answer JSON + citation validator | Coverage view v0 (docs per entity/type/period) | PDF extractors, review |
| W4 | GWIM segment tags (#37) | Earnings releases from EDGAR (#38, done in #75) | Finish tier 5 matrix (#5) | Time windows in SQL; theme mode | Caveat insertion; coverage note | Source viewer with page number | Corpus intake: 10-K/10-Q, transcripts, supplements, decks (#69, #76-#78); snapshot (#44) |
| W5 | Metric definitions, Q11 (#46) | Transcripts back to eight quarters (#47) | **Start thematic ingestion**: institutional research (#81) | Per-entity quotas; dedupe | Gap + suggested_source from registry | Filters (company/date/keyword) | PDF parse cache (#82); verify-cee wait (#83); eval runner (#43) |
| W6 | Remaining supplements + Schwab monthly (#45); expected_sources to real IDs (#56); start weekly X/30 | Investor-day decks + Merrill press (#48); 90 days of trade press (#57) | Thematic depth for Q16-Q21 | Retrieval hit rate vs expected_sources | Honest-miss path hard testing | Tier labels on citations | PDF page spans (#84); **Gate 2** run: 10 questions by hand; sixth-firm cost check (#54) |
| W7 | Form ADV (#55); project lead session 1 notes | Date quality check (#58); fixes from session | Fixes from session | Tune retrieval; watch refusal accuracy | Number check | Feedback button -> query_feedback | Session logistics |
| W8 | X/30 | Corpus fixes | Corpus fixes | entity+theme mode (Q12, Q21) | Boundary behavior (Q12, Q19) | Polish per feedback | **Gate 3**: >= 18/30 |
| W9 | Cold session 1: record failures | Fix corpus gaps | Fix corpus gaps | Fix retrieval failures | Fix answer failures | Plain UI pass | Expansion only if gates 1-3 were clean |
| W10 | Project lead session 2 notes | Fixes | Fixes | Fixes | Fixes | Fixes | Cold session 2 |
| W11 | X/30; new failing questions appended | Fixes | Fixes | Fixes | Fixes | Fixes | **Gate 4**: >= 21/30 + one unsupervised use |
| W12 | Final question review | Harden | Harden | Harden | Harden | Harden | Run page, what-to-build-next list, final demo. No new capability |
