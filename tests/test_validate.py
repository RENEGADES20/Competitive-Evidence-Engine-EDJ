"""Citation check and the empty-retrieval gap/refuse paths. No database, no API."""
from cee.answer.schema import Answer
from cee.answer.validate import check_citations, empty_retrieval_answer
from cee.config import entities_config
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


def _gap_firms(answer) -> set[str]:
    by_name = {e["name"]: e["id"] for e in entities_config()["entities"] + entities_config()["expansion"]}
    return {fid for name, fid in by_name.items() for g in answer.gaps if name in g.what}


def test_vanguard_footer_and_gap_name_the_same_firm():
    # #50: U1's Vanguard question showed "firms: none" next to a gap box naming Vanguard
    q = resolve("What is Vanguard's advisor headcount?")
    assert q.firms == ["VGD"]
    assert _gap_firms(empty_retrieval_answer(q)) == set(q.firms)


def test_firms_lists_covered_then_unmapped():
    q = resolve("Compare Edward Jones and Vanguard on fees")
    assert q.entities == ["EDJ"] and q.unmapped == ["VGD"]
    assert q.firms == ["EDJ", "VGD"]


def test_footer_text_names_unmapped_firms():
    from cee.app.views.ask_page import footer_firms
    assert footer_firms(resolve("What is Vanguard's advisor headcount?")) == "VGD (no documents)"
    assert footer_firms(resolve("Compare Edward Jones and Vanguard on fees")) == "EDJ, VGD (no documents)"
    assert footer_firms(resolve("How many advisors does Edward Jones have?")) == "EDJ"
    assert footer_firms(resolve("What is the future of advice?")) == "none"


def test_core_firms_resolve_unchanged():
    cases = {"How many advisors does Edward Jones have?": ["EDJ"],
             "What did Morgan Stanley report for net new assets?": ["MS"],
             "How is Schwab growing advisor services?": ["SCHW"],
             "How is Merrill recruiting advisors?": ["MER"],
             "What is Raymond James's advisor count?": ["RJF"]}
    for question, ids in cases.items():
        q = resolve(question)
        assert q.entities == ids and q.unmapped == [] and q.firms == ids, question


def test_merrill_resolves_to_mer_not_bac():
    q = resolve("How is Merrill recruiting advisors?")
    assert q.entities == ["MER"]


def gwim_hit(chunk_id="BAC-10K-2025#244", segment="GWIM"):
    return Hit(chunk_id=chunk_id, doc_id="BAC-10K-2025", entity_id="BAC", segment=segment,
               doc_type="10-K", source_tier=2, published_at="2026-02-25",
               period_end="2025-12-31", section="Item 7", page=None, rank=1.0, text="x")


def test_merrill_answer_citing_gwim_gets_the_caveat_from_config():
    # Q30: the caveat is code-owned, whatever the prompt says.
    from cee.answer.validate import insert_caveats

    a = Answer(answerable=False, behavior="gap_with_adjacent",
               adjacent=[{"text": "GWIM pretax income ...", "chunk_ids": ["BAC-10K-2025#244"],
                          "differs_because": "x"}])
    out = insert_caveats(a, resolve("What is Merrill's standalone profitability?"), [gwim_hit()])
    mer = next(e for e in entities_config()["entities"] if e["id"] == "MER")
    assert out.caveats == [mer["caveat"]]


def test_no_caveat_when_nothing_substitute_is_cited():
    from cee.answer.validate import insert_caveats

    a = Answer(answerable=True, behavior="answer", claims=[{"text": "t", "chunk_ids": ["EDJ-10K-2025#1"]}])
    assert insert_caveats(a, resolve("What is Merrill's standalone profitability?"), [hit()]).caveats == []
    b = Answer(answerable=True, behavior="answer", claims=[{"text": "t", "chunk_ids": ["BAC-10K-2025#244"]}])
    assert insert_caveats(b, resolve("What is Bank of America's net income?"), [gwim_hit()]).caveats == []
