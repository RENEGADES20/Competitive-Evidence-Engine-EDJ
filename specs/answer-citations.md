# Spec: Answer and citations

**Owner:** S2
Rules and invariants: [CLAUDE.md](../CLAUDE.md). Decisions: ADR-002, ADR-003 in [DECISIONS.md](../docs/DECISIONS.md).

## Purpose

Turn retrieved chunks into a cited answer with one LLM call, then check it in code: every
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

## Acceptance

- 100% of claims carry at least one `chunk_id` from the retrieved set, or are flagged.
- Q30: answer says Merrill does not report standalone results and the GWIM caveat appears
  (inserted by code; test with the prompt's caveat instruction removed).
- Q12, Q19: behavior `answer_with_boundary`, no sentence recommending action.
- Q28, Q29: adjacent data carries `differs_because`; a named `suggested_source` appears.
- Number check catches a planted wrong figure.
- Every answer includes a coverage note.
- Works with `LLM_PROVIDER=anthropic` and `LLM_PROVIDER=openai`.

## Linked questions

Q12, Q19, Q24, Q25, Q28, Q29, Q30 (primary); every question.

## Open questions

- Trade-press claims: allowed only as `adjacent` / labeled indicative? (Q29 suggests labeled)
- How strict is the number check with rounding and units ("$1.2 trillion" vs "1,200 billion")?
