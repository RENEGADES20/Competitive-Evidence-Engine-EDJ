"""Citation check and the empty-retrieval gap/refuse paths. No database, no API."""
from cee.answer.schema import Answer
from cee.answer.validate import check_citations, empty_retrieval_answer
from cee.retrieve.fts import Hit, Query, resolve


def hit(chunk_id="EDJ-10K-2025#1"):
    return Hit(chunk_id=chunk_id, doc_id="EDJ-10K-2025", entity_id="EDJ", segment=None,
               doc_type="10-K", source_tier=2, published_at="2026-03-13",
               period_end="2025-12-31", section="Item 1", page=None, rank=1.0, text="x")


def test_forged_chunk_id_is_flagged_not_dropped():
    a = Answer(answerable=True, behavior="answer", claims=[
        {"text": "real", "chunk_ids": ["EDJ-10K-2025#1"]},
        {"text": "forged", "chunk_ids": ["EDJ-10K-2025#999"]},
        {"text": "uncited", "chunk_ids": []},
    ])
    out = check_citations(a, [hit()])
    assert [c.text for c in out.claims] == ["real", "forged", "uncited"]
    assert out.claims[0].flags == []
    assert out.claims[0].source_label == "EDJ 10-K 2025-12-31 [filing]"
    assert "unmatched_citation" in out.claims[1].flags
    assert "no_citation" in out.claims[2].flags


def test_covered_firm_with_no_hits_is_gap_without_llm():
    a = empty_retrieval_answer(Query(question="q", entities=["EDJ"]))
    assert a.behavior == "gap_with_adjacent"
    assert not a.answerable and not a.llm_called
    assert "Form 10-K" in a.gaps[0].suggested_source


def test_unmapped_firm_is_refused_with_suggested_source():
    q = resolve("Anything on Vanguard's advisor compensation?")
    assert q.entities == [] and q.unmapped == ["VGD"]
    a = empty_retrieval_answer(q)
    assert a.behavior == "refuse"
    assert "Form ADV" in a.gaps[0].suggested_source


def test_merrill_resolves_to_mer_not_bac():
    q = resolve("How is Merrill recruiting advisors?")
    assert q.entities == ["MER"]
