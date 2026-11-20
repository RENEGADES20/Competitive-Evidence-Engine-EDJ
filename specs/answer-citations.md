# Spec: Answer and citations

**Owner:** S2
Rules and invariants: [CLAUDE.md](../CLAUDE.md). Decisions: ADR-002, ADR-003 in [DECISIONS.md](../docs/DECISIONS.md).

## Purpose

Turn retrieved chunks into a cited answer with one LLM call (after at most one question-planner call
before search, ADR-020: 2 calls per question at most), then check it in code: every
citation resolves, every number appears in a cited chunk, caveats are inserted, gaps are named
with a source that would fill them, and the answer never crosses into "should".

## Reference projects

- [bt4103-team8-sec-filing-assistant](https://github.com/niclow236/bt4103-team8-sec-filing-assistant): Pydantic answer templates, citation format.
- [Grounded-Rag-Analyst](https://github.com/Monesh76/Grounded-Rag-Analyst): citation validator, insufficient-evidence gate.
- [agentic-sec-rag](https://github.com/mr-j90/agentic-sec-rag): coverage note computed before the LLM call.
- [sec-edgar-rag](https://github.com/ankankisku-lab/sec-edgar-rag): numeric check.

## Interface draft (sketch)

```
answer(question, hits, query) -> Answer      # see Answer JSON in docs/ARCHITECTURE.md
    behavior in {"answer", "answer_with_boundary", "gap_with_adjacent", "refuse"}

validate(answer, hits) -> Answer
    for claim in claims + adjacent:
        unknown = claim.chunk_ids not in hits  -> claim.flag = "unmatched_citation"  # flag, never drop
        numbers in claim.text not found in cited chunk text -> claim.flag = "number_not_found"
    source_label built by code from documents (entity, doc_type, date, segment, tier label)
    date for an undated web page (date_basis = retrieved, ADR-007 T-09): "page content as of <date>" in
    source_label, coverage_note (own group) and the model's chunk source line, never "published"

insert_caveats(answer, hits, entities_config) -> Answer
    if any cited chunk is a substitute (e.g. BAC GWIM for MER, equivalence: partial):
        append entity.caveat to answer.caveats          # code, not prompt

coverage_note(query) -> "Corpus holds for MER: 12 BAC 10-K GWIM chunks (2019-2025), 0 transcripts..."

suggest_sources(query) -> [source]
    = expected sources in source_registry for the entity - sources actually ingested
```

## Behavior values

| Value | Meaning | Questions |
|---|---|---|
| `answer` | Normal answer, every claim cited | most, incl. Q4, Q26, Q27 |
| `answer_with_boundary` | Evidence half, then an explicit hand-off of the normative part to the strategist | Q12, Q19 |
| `gap_with_adjacent` | "Not available / not disclosed" + adjacent data labeled as different + which source would fill it | Q24, Q25, Q28, Q29, Q30 |
| `refuse` | Nothing in the corpus | none yet |

Partial or missing disclosure (prompt v3, #204): if the asked quantity is not disclosed for most
of the firms asked about, the behavior is `gap_with_adjacent` (answerable=false), with what is
disclosed reported as claims and each firm's missing disclosure as a gap. If the evidence covers
part of the asked population, cohort or period (a survey of an overlapping or narrower group,
some of the quarters), the behavior is `answer`: each finding with its source, sample and date as
printed, the group it covers, and the missing parts as gaps. A wider unit that contains the one
asked about (a parent company, a segment such as GWIM) is not partial evidence; it stays adjacent.
Disclosure questions (prompt v4, #215): a question about what firms disclose on a topic is answered
by the disclosures, but the behavior follows the specifics the topic is about (rates, formulas,
grids, amounts): not disclosed for most firms asked about -> `gap_with_adjacent`, the disclosures
as claims, each firm's undisclosed specifics as a gap naming the firm. Code does not derive the
behavior from per-part coverage (plans/0215: a coverage rule would not fire on Q25, would flip with
the planner's split, and would touch Q11 / Q23, NEXT item 5, which stays open).

## Answer shape (prompt v4, #215; v3 #204)

General rules in the prompt; no question ID, no `passes_if` text and no question text (a test
checks 6-word runs, lower case, punctuation stripped, against every `passes_if` and every question
text; the standard wording below is exempt from the `passes_if` check because the bank quotes it).
v4 reworded v3's recency example (it shared a run with a question's text).

The user message (prompt v4) lists the plan's parts (`p1 [firms]: text`, ADR-020) and groups the
evidence under the part it was found for, in hit order; research and peer passages follow under
their own headings. A part with no passages of its own says why, from its candidate pool before
exclusion (`plan.searched[i]["pool"]`): pool 0 "(no passages were found for this part)", else
"(no further passages; the passages found for this part are listed under another part or the
research passages)". No plan: one part p1, the whole question. The model writes `part_id` on
every claim, adjacent item and gap ("" when none applies).

| Rule | When | What the answer does |
|---|---|---|
| Comparison grid | the question names two or more firms, or "each of" / "across" a set | Dimensions fixed from the question and its parts before reading the evidence (each dimension a part names, or each part when the parts are dimensions); an asked dimension is never dropped because the evidence is thin, none added only because the evidence offers it (v4; v3 also took dimensions from the evidence); the same list for every firm, every firm with a claim or a gap under every dimension (no dimension for one firm only); claims dimension by dimension (all firms for one dimension, then the next), each starting "<Dimension> - <Firm>:", each firm in its own terms; an empty cell is a gap "<Firm> - <dimension>: not found in the evidence provided." with a suggested source; never an inference, an adjacent figure or another firm's fact in a cell; an empty cell is only a gap, never a claim (v4). |
| Positions | where something is heading, the future, the range of views | Claims grouped by position (not by firm or source), each starting with the position, then who holds it and when; every claim attributed; two sources that disagree are reported as disagreeing; no forecast or synthesis of its own. |
| Parts | always | Every claim, adjacent item and gap carries the `part_id` of the plan part it answers; every part gets at least one cited claim or a gap naming what is missing for it; a part with no passages is a gap; a chunk listed under one part may be cited for another; within a part, what a question of its type needs (e.g. headwinds or risks the firm itself names) is covered (v4; v3 split the question itself). A question setting the home firm against a peer, or asking how it could act, shows the home firm's figures on the same dimension from its own filings. |

Time windows (prompt v4.1, #230): in a question about recent change or with a time window, claims
and adjacent items run newest first across the whole answer (by the date of what each reports),
not part by part; each keeps its `part_id`; gaps follow. The grouping of the evidence by part is
how it is listed, not the answer's order. When the resolved query has a window or an Ask page date
range (both SQL filters; their overlap when both are set), the user message adds one line after the
question: "Time window: <from> to <to> (only passages dated in it were searched). Order the answer
newest first across all parts."

The Ask page lists gaps under the claims, with code flags as chips. Answers can be longer: the
Anthropic output cap is 20000 tokens for every answer call (`llm.MAX_TOKENS`, ADR-019 amendment
#230; was 8000), under the SDK's non-streaming limit (21,333). Thinking, when the model runs it,
shares the cap.

## Invalid model outputs (code, #187, #230)

A paid output that cannot be trusted as an answer raises `ModelOutputError`; it is never shown,
scored or re-rolled. The eval saves it (`INVALID_OUTPUT`, the provider payload kept); the Ask page
shows "The answer could not be built" with the reason. Checked by `llm.check_output` on the model's
own output, before code adds part gaps or caveats, and again when the eval reuses a saved output:

| Output | Result |
|---|---|
| No `submit_answer` call, or a tool input that is not a valid Answer | invalid (#187) |
| Cut at the output cap (Anthropic `stop_reason` `max_tokens`, OpenAI `finish_reason` `length`), even when the partial input validates | invalid; every content block kept |
| No claims, no adjacent items and no gaps, unless behavior `refuse` with `answerable` false | invalid; the tool input as sent kept (a misnamed key shows) |
| API `stop_reason` `refusal` (Anthropic, #232), even with a tool input that validates | invalid; every content block kept. Not the model's own answer `behavior: refuse` with `answerable` false, which is a valid answer (row above) |
| DeepSeek (#242): `finish_reason` other than `tool_calls` / `stop` (`length` = cut, `content_filter`, `insufficient_system_resource`, `aborted`) | invalid; the whole message kept (content, `reasoning_content`, tool calls) |
| DeepSeek: tool arguments that are not JSON or not a JSON object (the API warns they may not be valid JSON) | invalid; the arguments string kept |

Every real answer records `stop_reason` and `usage` (input and output tokens; Anthropic also the
content block types, e.g. `thinking`, `tool_use`), code-owned fields of the Answer, so they reach
`query_log.answer` and the eval's saved outputs. A tool answer normally stops with `tool_use`. The
real clients are built with `max_retries=0` (TL, #230): a timeout or transport error is reported,
never a second paid request.

Strict tool input (#232): on Anthropic the `submit_answer` tool is sent with `strict: true` (the
planner's `submit_plan` too, ADR-020), so the API itself enforces `llm_output_schema()` on the tool
input (grammar-constrained); the schema already meets strict mode's rules (every object
`additionalProperties: false`, every property required, no array limits), checked offline by a test
and by the SDK's `anthropic.transform_schema`. `tool_choice` stays `auto` (claude-sonnet-5-5 rejects
forced tool choice), so a response without a tool call is still possible and stays invalid (first
row). The OpenAI request was already strict. The eval's cache keys carry the Anthropic request
version `strict-1` (`llm.request_version`); `PROMPT_VERSION` stays v4.1 (prompt text unchanged).
DeepSeek (#242) sends `submit_answer` and `submit_plan` as strict function tools (`strict: true`
on the `https://api.deepseek.com/beta` base URL), with an explicit `max_tokens`: 20000 / 2000 with
thinking off, 64000 / 16000 with thinking on (reasoning shares the cap). Thinking off forces the
named function; thinking on uses `tool_choice` auto (a forced choice is a 400 there). A 401 / 402 /
429 stops the question with a plain message (`ProviderStop`), with no fallback and nothing saved.
Its request version (`ds-strict-1-think-{on|off}-a{cap}-p{cap}`) joins the eval's cache keys.
`usage` also records cache hit / miss and reasoning tokens.

## Every part answered or named as a gap (code, #215)

Ground rules 1, 3 and 6, enforced in `src/cee/answer/validate.py` after the model, never left to
the prompt. Behavior, claims and the model's own gaps are not changed.

- **Uncited grid cells** (`move_uncited_cells`, in `check_citations`): a claim with **no**
  `chunk_ids` whose text starts "<Dimension> - <Firm>:" (Firm = a configured name or alias) leaves
  `claims`. It becomes a gap "<Firm> - <Dimension>: no cited evidence in this answer." (true by
  construction: code knows only that no citation was given), flag `uncited_cell`, the model's text
  kept in `claim_text` (logged, not shown). When the model already wrote a gap starting
  "<Firm> - <Dimension>:", that gap keeps its own text and gets the flag and `claim_text`. A claim
  with citations, even unmatched ones, is never moved (flagged as before); any other uncited claim
  keeps `no_citation`.
- **Every part covered** (`check_parts`, in `ask.answer_for` after the citation check, when a plan
  is given): part P is covered by a claim or adjacent item with `part_id` P and a citation in the
  retrieved set, or by a gap with `part_id` P. Items with no or an unknown `part_id` (v3 outputs,
  the mock) count by citation: they cover the parts whose search found a passage they cite (in a
  one-part plan, every passage but research / peers; every gap). The hand-off sentence code adds
  covers no part by citation; in an `answer_with_boundary` answer it covers a part whose text is
  normative (e.g. "how could Edward Jones replicate ..."). An uncovered part gets a gap flagged
  `part_gap`, with the part's firms' suggested sources:

| Part's candidate pool before exclusion | Gap (`gaps[].what`) |
|---|---|
| 0 (its search found nothing) | "No evidence retrieved for: <part>" |
| > 0 (passages may sit under another part or research), or unknown | "Not answered from the evidence retrieved for: <part>" |

  `<part>` = the part text (+ " (<firms>)" when it repeats the question, as rule-plan parts do);
  a normative part text is printed as "part pN (<firms>)" instead (ground rule 6).
- `part_coverage()` gives each part's state (model / citation / handoff / code_gap) for the eval.
- Mock: its claims carry their passage's plan part, so the check runs on mock answers too: a
  two-firm mock answer whose top 3 passages are all one firm's gets a part gap for the other part,
  with the pool-chosen wording above.

## Standard wording

The prompt lives in `src/cee/answer/prompt.py` (`PROMPT_VERSION`), which holds these sentences
as constants. Keep the two in sync. Caveats remain code-owned; this wording does not replace them.

| Case | Questions | Gap (`gaps[].what`) | Adjacent `differs_because` |
|---|---|---|---|
| Merrill standalone results | Q30 | "Merrill does not report standalone results." | "GWIM includes both Merrill and Bank of America Private Bank; the two have different reporting scopes, so GWIM figures are not Merrill's." |
| Advisor attrition | Q28 | "Neither firm discloses advisor attrition on a comparable basis." | "Net advisor headcount change is not attrition: it nets hires against departures." |
| Advisor pay (decided per firm, prompt v2, #167; v3 #204) | Q25, Q29 | Firm with nothing published: "Payout grids are not public." (multi-firm answers name the firm first). Firm whose cited chunks publish payout ranges (RJF recruiting pages, #151): the ranges are claims dated "page content as of <date>", and the gap is "Headline payout ranges are published (company recruiting page, as of <date>); the full payout grid is not public." (multi-firm answers name the firm first, v3). Never "not public" for a firm whose evidence shows ranges. | "Aggregate compensation expense covers all employees and pay types; it is not the advisor payout grid." Trade press: "Trade-press reporting is indicative, not authoritative." |

Boundary hand-off (`answer_with_boundary`, Q12, Q19): the evidence half first, then this
sentence as the last claim:

> The evidence above only provides objective context for the strategic question asked.
> Whether or how Edward Jones should act is a judgment for the strategy team to make, beyond
> the scope of this evidence engine.

## Acceptance

- 100% of claims carry at least one `chunk_id` from the retrieved set, or are flagged.
- Q30: answer says Merrill does not report standalone results and the GWIM caveat appears
  (inserted by code; test with the prompt's caveat instruction removed).
- Q12, Q19: behavior `answer_with_boundary`, no sentence recommending action.
- Q28, Q29: adjacent data carries `differs_because`; a named `suggested_source` appears.
- Number check catches a planted wrong figure.
- Every answer includes a coverage note.
- Works with `LLM_PROVIDER=anthropic`, `LLM_PROVIDER=openai` and `LLM_PROVIDER=deepseek` (#242).

## Linked questions

Q12, Q19, Q24, Q25, Q28, Q29, Q30 (primary); every question.

## Number check

`check_numbers()` in `src/cee/answer/validate.py` (#52) runs after the citation check. Every
number in a claim or adjacent item is compared with the numbers in the chunks that claim cites
(not other retrieved chunks). No match: the claim gets the flag `number_not_found`; it is never
dropped, and the app shows the flag next to the claim.

A claim figure matches a chunk figure when either:
1. it is within 0.1% of the chunk figure; or
2. it shows at least one decimal place and equals the chunk figure rounded half up to the
   claim's shown precision and scale.

| Claim | Cited chunk | Result | Why |
|---|---|---|---|
| 20,425 | 20,425 | match | equal |
| 30,020 | 30,000 | match | 0.07% apart |
| 20.4 thousand | 20,425 | match | one decimal, rounded |
| $1.2 billion | $1,234 million | match | one decimal, rounded |
| 2.9% | 2.88% | match | one decimal, rounded |
| $7.9 billion | 7,912 under "($ in millions)" | match | table unit header applied |
| nearly 21 | 21 million | match | a figure written without a unit may match the digits shown |
| $1,875 million | "$ 1,875" (table header in another chunk) | match | a figure with a unit may match the same digits written without one |
| $1 billion | $1.4 billion | `number_not_found` | no decimal, 29% apart |
| 20,000 | 20,425 | `number_not_found` | no decimal, 2% apart |
| 21% | 20.8% | `number_not_found` | no decimal, 1% apart |
| 21 thousand | 21 million | `number_not_found` | wrong unit |
| 21,000 (planted) | 20,425 | `number_not_found` | not in the chunk |

Scale words: thousand, k, million, mn, billion, bn, trillion. Not checked: years 1990-2099,
quarter and form labels (Q3, 3Q26, 10-K), section labels (Item 11, Note 4), dates (December 31,
12/31/2025), numbers written as words. Derived figures (sums, ratios, per-advisor values) are not in the chunk and are flagged.

Limits: a small figure with one decimal can pass rule 2 with a large relative error ("$0.1
billion" vs $0.14 billion). The check proves a figure is in the cited text, not that it came from
the right table column (MS-SUPP-2026Q3 p.8: a docling cell shift put 2.88% under the wrong
column); PDF source labels keep the page so the reader can open it.

## Date check

`check_dates()` in `src/cee/answer/validate.py` (#155) runs after the number check. A claim that
dates itself with a month and year is compared with the documents it cites; no match flags the
claim `date_mismatch` (flagged, never dropped, shown next to the claim). Found in the #61 real run:
Q29 called the MS 3Q26 release (`period_end` 2026-09-30) "the quarter ended September 2025".

| Claim says | Compared with | Result |
|---|---|---|
| "quarter / period / year / months / fiscal year ended <Month> [day,] YYYY", "as of <Month> [day,] YYYY" | a cited document's `period_end` or `published_at` (year and month) | no match: `date_mismatch` |
| "published [in/on] <Month> [day,] YYYY" | a cited document's `published_at` (year and month) | no match: `date_mismatch` |
| the same month and year in a cited chunk's text (a comparative column) | chunk text | match |
| several cited documents | any one matching is enough | |

Not checked: quarter shorthand ("3Q26", "fiscal 3Q25"), because fiscal and calendar quarters
differ (Raymond James's fiscal year ends in September); bare years; days of the month.

## Boundary

Ground rule 6 is enforced by code as well as by the prompt (#118). `withhold_normative()` and
`ensure_handoff()` in `src/cee/answer/validate.py` run at the start of `check_citations`.

- A claim or adjacent item that tells the home firm what to do is **withheld**: it is not shown;
  the Ask page shows "Withheld: A sentence was withheld because it recommended an action for
  Edward Jones (ground rule 6). That decision belongs to the strategy team." in its place. The
  claim is kept in `Answer.withheld` (and so in `query_log`) for review, never silently dropped.
  A shown recommendation, even flagged, has already reached the reader; that is why it is
  withheld rather than flagged.
- An answer with a withheld claim and behavior `answer` is re-judged `answer_with_boundary`.
- Every `answer_with_boundary` answer ends with the hand-off sentence; code adds it, citing the
  answer's chunks, when the model left it out.

| Withheld | Not withheld |
|---|---|
| "Edward Jones should build a similar channel" (EJ, EDJ, aliases, "the home firm"; should, ought to, would benefit from, might/may want to, could replicate/adopt/copy/emulate/consider/learn from/follow) | the hand-off sentence itself |
| "The home firm must / needs to ..." | "Edward Jones must maintain minimum net capital" (a filing duty) |
| "We / I (would) recommend / suggest / advise ..." | text in quotation marks: a firm's or analyst's own words |
| "It would be wise / advisable / prudent ..."; "It is recommended ..." | "we should expect" in a transcript ("we" / "you" are the speaker, not the home firm) |
| "recommend(s/ed) / suggest(s/ed) / advise(s/d) (that) Edward Jones ..." | "advisors recommend products suited to each client"; "should market conditions worsen" |

## Open questions

- Trade-press claims: allowed only as `adjacent` / labeled indicative? (Q29 suggests labeled)
- ~~How strict is the number check with rounding and units?~~ Settled in "Number check" (#52).
