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


# Coverage note (#40): every behavior names firms, document types and period, built by code.

def test_coverage_note_names_firm_doc_type_and_period():
    from cee.answer.validate import coverage_note

    hits = [hit("EDJ-10K-2025#1"), hit("EDJ-10K-2025#2")]
    note = coverage_note(Query(question="q", entities=["EDJ"]), hits)
    assert note.startswith("Coverage: searched Edward Jones.")
    assert "2 passages from 1 document" in note
    assert "EDJ 10-K (2025-12-31)" in note


def test_coverage_note_shows_period_range_and_segment_for_merrill():
    # Q30: Merrill is answered from BAC GWIM chunks; the note says so.
    from cee.answer.validate import coverage_note

    older = Hit(chunk_id="BAC-10K-2024#9", doc_id="BAC-10K-2024", entity_id="BAC", segment="GWIM",
                doc_type="10-K", source_tier=2, published_at="2025-02-25", period_end="2024-12-31",
                section="Item 7", page=None, rank=1.0, text="x")
    note = coverage_note(resolve("What is Merrill's standalone profitability?"), [gwim_hit(), older])
    assert "searched Merrill." in note
    assert "2 passages from 2 documents" in note
    assert "BAC 10-K, GWIM segment (2024-12-31 to 2025-12-31)" in note
    assert "No passages" not in note   # BAC GWIM counts as coverage for MER (parent)


def test_coverage_note_names_firm_with_no_passages():
    from cee.answer.validate import coverage_note

    note = coverage_note(Query(question="q", entities=["EDJ", "MS"]), [hit()])
    assert "No passages for Morgan Stanley." in note


def test_every_behavior_carries_a_coverage_note():
    # Q24 (gap), Q12/Q19 (boundary), refuse: the note does not depend on the behavior.
    from cee.ask import answer_for

    q = Query(question="q", entities=["EDJ"])
    for behavior in ("answer", "answer_with_boundary", "gap_with_adjacent", "refuse"):
        raw = Answer(answerable=behavior.startswith("answer"), behavior=behavior,
                     claims=[{"text": "t", "chunk_ids": ["EDJ-10K-2025#1"]}])
        out, _ = answer_for("q", q, [hit()], "mock", raw=raw)
        assert out.coverage_note.startswith("Coverage: searched Edward Jones."), behavior
        assert "10-K" in out.coverage_note and "2025-12-31" in out.coverage_note


def test_empty_retrieval_answers_carry_a_coverage_note():
    from cee.ask import answer_for

    gap, _ = answer_for("q", Query(question="q", entities=["MS"]), [], "mock")
    assert gap.behavior == "gap_with_adjacent"
    assert gap.coverage_note == "Coverage: searched Morgan Stanley. No stored passage matched this question."
    refuse, _ = answer_for("q", resolve("Anything on Vanguard's advisor compensation?"), [], "mock")
    assert refuse.behavior == "refuse"
    assert "No documents in the corpus for Vanguard." in refuse.coverage_note


def test_coverage_note_is_not_written_by_the_model():
    from cee.answer.schema import llm_output_schema

    assert "coverage_note" not in llm_output_schema()["properties"]


def test_coverage_note_states_the_time_window_and_names_research_once():
    # Q26: hit dates are periods; the note says the window is on publication date
    import datetime as dt

    from cee.answer.validate import coverage_note

    q = resolve("What's new on Raymond James in the last 90 days?", today=dt.date(2026, 10, 28))
    assert "Published 2026-07-30 to 2026-10-28 only." in coverage_note(q, [])
    research = Hit(chunk_id="MCK-X#1", doc_id="MCK-X", entity_id=None, segment=None, doc_type="research",
                   source_tier=5, published_at="2025-02-10", period_end=None, section="Document", page=1,
                   rank=1.0, text="x")
    note = coverage_note(Query(question="q"), [research])
    assert "research (2025-02-10)" in note and "Research research" not in note
