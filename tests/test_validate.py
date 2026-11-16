"""Citation check and the empty-retrieval gap/refuse paths. No database, no API."""
from cee.answer.schema import Answer
from cee.answer.validate import check_citations, empty_retrieval_answer
from cee.config import entities_config
from cee.retrieve.fts import Hit, Query, resolve

import pytest

from cee.answer import validate


@pytest.fixture(autouse=True)
def no_registry(monkeypatch):
    """No database in these tests: the registry lookup fails, so gaps use the config fallback.
    Registry tests below install their own fake lookup."""
    def unavailable(entity_id):
        raise ConnectionError("no database in tests")
    monkeypatch.setattr(validate, "registry_lookup", unavailable)


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


# Registry-based suggested sources (#51): expected in source_registry minus ingested doc types.

MS_REGISTRY = [("10-K", "Morgan Stanley Form 10-K annual report (SEC EDGAR)"),
               ("10-Q", "Morgan Stanley Form 10-Q quarterly report (SEC EDGAR)"),
               ("8-K", "Morgan Stanley Form 8-K current report (SEC EDGAR)"),
               ("DEF 14A", "Morgan Stanley Proxy statement (SEC EDGAR)"),
               ("adv", "Morgan Stanley Form ADV (SEC IAPD)"),
               ("deck", "Morgan Stanley Investor-day presentation"),
               ("press", "Morgan Stanley Company press releases"),
               ("supplement", "Morgan Stanley Quarterly financial supplement"),
               ("trade", "Morgan Stanley Trade press (tier 4, indicative)"),
               ("transcript", "Morgan Stanley Earnings-call transcript")]
MS_INGESTED = {"10-K", "10-Q", "press", "supplement", "transcript"}


def fake_registry(monkeypatch, rows=MS_REGISTRY, have=MS_INGESTED):
    monkeypatch.setattr(validate, "registry_lookup", lambda e: (rows if e == "MS" else [], have if e == "MS" else set()))


def test_registry_suggests_only_what_is_not_ingested(monkeypatch):
    fake_registry(monkeypatch)
    text = validate.suggested_sources("MS")
    for name in ("Form 8-K", "Proxy statement", "Form ADV", "Investor-day presentation", "Trade press"):
        assert name in text
    for name in ("Form 10-K", "Form 10-Q", "press releases", "financial supplement", "Earnings-call"):
        assert name not in text


def test_registry_with_every_type_ingested_suggests_nothing(monkeypatch):
    fake_registry(monkeypatch, have={t for t, _ in MS_REGISTRY})
    assert validate.suggested_sources("MS") == ""


def test_unknown_entity_or_database_error_falls_back(monkeypatch):
    fake_registry(monkeypatch)
    assert validate.suggested_sources("VGD").startswith("Vanguard: ")   # not in the registry
    validate.registry_lookup = None                                     # lookup itself broken
    assert "Form ADV" in validate.suggested_sources("VGD")


def test_q29_gap_gets_an_ms_registry_source(monkeypatch):
    # Q29: the model leaves suggested_source empty; code fills it from the registry.
    from cee.ask import answer_for

    fake_registry(monkeypatch)
    q = resolve("What does Morgan Stanley pay its financial advisors?")
    raw = Answer(answerable=False, behavior="gap_with_adjacent",
                 gaps=[{"what": "Payout grids are not public.", "suggested_source": ""}])
    ms_hit = Hit(chunk_id="MS-10K-2025#1", doc_id="MS-10K-2025", entity_id="MS", segment=None,
                 doc_type="10-K", source_tier=2, published_at="2026-02-19", period_end="2025-12-31",
                 section="Item 8", page=None, rank=1.0, text="x")
    out, _ = answer_for(q.question, q, [ms_hit], "mock", raw=raw)
    assert "Morgan Stanley Trade press" in out.gaps[0].suggested_source
    assert "Form 10-K" not in out.gaps[0].suggested_source


def test_model_written_source_is_kept(monkeypatch):
    fake_registry(monkeypatch)
    a = Answer(answerable=False, behavior="gap_with_adjacent",
               gaps=[{"what": "x", "suggested_source": "Morgan Stanley compensation survey"}])
    out = validate.fill_suggested_sources(a, Query(question="q", entities=["MS"]))
    assert out.gaps[0].suggested_source == "Morgan Stanley compensation survey"


def test_empty_retrieval_gap_uses_the_registry(monkeypatch):
    fake_registry(monkeypatch)
    a = empty_retrieval_answer(Query(question="q", entities=["MS"]))
    assert "Form ADV" in a.gaps[0].suggested_source and "Form 10-K" not in a.gaps[0].suggested_source


def test_two_firms_share_one_prefix(monkeypatch):
    # Q28 names two firms: one "Not yet in the corpus:" list, both firms' sources in it.
    rows = {"MS": [("adv", "Morgan Stanley Form ADV (SEC IAPD)")], "EDJ": [("adv", "Edward Jones Form ADV (SEC IAPD)")]}
    monkeypatch.setattr(validate, "registry_lookup", lambda e: (rows.get(e, []), set()))
    a = Answer(answerable=False, behavior="gap_with_adjacent", gaps=[{"what": "x", "suggested_source": ""}])
    text = validate.fill_suggested_sources(a, Query(question="q", entities=["EDJ", "MS"])).gaps[0].suggested_source
    assert text == "Not yet in the corpus: Edward Jones Form ADV (SEC IAPD); Morgan Stanley Form ADV (SEC IAPD)"


# Undated pages dated by the stored copy (ADR-007 T-09, #58): the label says so.

def retrieved_hit(chunk_id="RJF-PR-web-advisor-select#0", published="2026-07-12"):
    return Hit(chunk_id=chunk_id, doc_id=chunk_id.split("#")[0], entity_id="RJF", segment=None,
               doc_type="press", source_tier=3, published_at=published, period_end=None,
               section="Document", page=None, rank=1.0, text="x", date_basis="retrieved")


def test_retrieved_page_label_says_page_content_as_of():
    from cee.answer.validate import date_label, source_label

    assert date_label(retrieved_hit()) == "page content as of 2026-07-12"
    assert source_label(retrieved_hit()) == "RJF press page content as of 2026-07-12 [IR]"


def test_source_dated_label_unchanged():
    from cee.answer.validate import date_label, source_label

    assert hit().date_basis == "source"
    assert date_label(hit()) == "2025-12-31"
    assert source_label(hit()) == "EDJ 10-K 2025-12-31 [filing]"


def test_coverage_note_groups_retrieved_pages_apart():
    from cee.answer.validate import coverage_note

    press = Hit(chunk_id="RJF-PR-2025-10-22#0", doc_id="RJF-PR-2025-10-22", entity_id="RJF", segment=None,
                doc_type="press", source_tier=3, published_at="2025-10-22", period_end=None,
                section="Document", page=None, rank=1.0, text="x")
    pages = [retrieved_hit("RJF-PR-web-a#0", "2026-03-11"), retrieved_hit("RJF-PR-web-b#0", "2026-07-12")]
    note = coverage_note(Query(question="q", entities=["RJF"]), [press, *pages])
    assert "RJF press (2025-10-22)" in note
    assert "RJF press (page content as of 2026-03-11 to 2026-07-12)" in note


def test_label_works_on_hits_without_date_basis():
    import types

    from cee.answer.validate import coverage_note, date_label

    h = types.SimpleNamespace(chunk_id="EDJ-10K-2025#1", doc_id="EDJ-10K-2025", entity_id="EDJ", segment=None,
                              doc_type="10-K", published_at="2026-03-13", period_end="2025-12-31")
    assert date_label(h) == "2025-12-31"
    assert "EDJ 10-K (2025-12-31)" in coverage_note(Query(question="q", entities=["EDJ"]), [h])


# Number check (#52): every number in a claim must be found in a chunk it cites.

def chunk(text, chunk_id="MS-SUPP-2026Q3#1"):
    return Hit(chunk_id=chunk_id, doc_id=chunk_id.split("#")[0], entity_id="MS", segment=None,
               doc_type="supplement", source_tier=2, published_at="2026-10-15", period_end="2026-09-30",
               section="p8", page=8, rank=1.0, text=text)


def flags_for(claim_text, chunk_text):
    a = Answer(answerable=True, behavior="answer", claims=[{"text": claim_text, "chunk_ids": ["MS-SUPP-2026Q3#1"]}])
    return check_citations(a, [chunk(chunk_text)]).claims[0].flags


def test_planted_wrong_figure_is_flagged():
    # Spec: the number check catches a planted wrong figure. Flagged, never dropped.
    a = Answer(answerable=True, behavior="answer", claims=[
        {"text": "The firm had 21,000 financial advisors.", "chunk_ids": ["MS-SUPP-2026Q3#1"]}])
    out = check_citations(a, [chunk("Financial advisors: 20,425 at period end.")])
    assert out.claims[0].text == "The firm had 21,000 financial advisors."
    assert out.claims[0].flags == ["number_not_found"]


def test_exact_figure_matches():
    assert flags_for("20,425 advisors", "Financial advisors 20,425") == []


def test_within_one_tenth_of_a_percent_matches():
    assert flags_for("about 30,020 clients", "30,000 clients") == []
    assert flags_for("about 30,040 clients", "30,000 clients") == ["number_not_found"]


def test_rounded_with_a_decimal_matches():
    assert flags_for("20.4 thousand advisors", "Financial advisors 20,425") == []
    assert flags_for("$1.2 billion of revenue", "revenue of $1,234 million") == []
    assert flags_for("a margin of 2.9%", "margin 2.88 %") == []


def test_coarse_figure_without_a_decimal_is_flagged():
    assert flags_for("$1 billion of revenue", "revenue of $1.4 billion") == ["number_not_found"]
    assert flags_for("20,000 advisors", "Financial advisors 20,425") == ["number_not_found"]
    assert flags_for("a margin of 21%", "margin 20.8%") == ["number_not_found"]


def test_table_unit_header_scales_bare_numbers():
    assert flags_for("net revenues of $7.9 billion", "($ in millions) Net revenues 7,912") == []
    assert flags_for("net revenues of $7.9 billion", "Net revenues 7,912") == ["number_not_found"]


def test_years_quarters_forms_and_dates_are_not_checked():
    text = "In the 2025 10-K and on the 3Q26 call (Q3, December 31, 2025), assets were $5.1 trillion."
    assert flags_for(text, "Total client assets of $5.1 trillion") == []


def test_number_found_only_in_an_uncited_chunk_is_flagged():
    a = Answer(answerable=True, behavior="answer", claims=[{"text": "20,425", "chunk_ids": ["MS-SUPP-2026Q3#1"]}])
    out = check_citations(a, [chunk("nothing here"), chunk("20,425", "MS-SUPP-2026Q3#2")])
    assert out.claims[0].flags == ["number_not_found"]


def test_adjacent_items_are_checked_too():
    a = Answer(answerable=False, behavior="gap_with_adjacent", adjacent=[
        {"text": "Compensation expense was $9.9 billion.", "chunk_ids": ["MS-SUPP-2026Q3#1"], "differs_because": "x"}])
    out = check_citations(a, [chunk("Compensation and benefits $8,512 million")])
    assert out.adjacent[0].flags == ["number_not_found"]


def test_misplaced_table_cell_still_matches():
    # TL's case (MS-SUPP-2026Q3 p.8): docling put 2.88% under the wrong column. The check proves the
    # figure is in the cited text, not that it is the right column; the label keeps the page to open.
    assert flags_for("Period average yield was 2.88%.", "Period average 2.88% 0.12%") == []
    assert ", p.8" in validate.source_label(chunk("x"))


def test_flag_is_shown_next_to_the_claim(monkeypatch):
    from cee.app import components

    shown = []
    monkeypatch.setattr(components, "_html", shown.append)
    components.claim_card(1, "The firm had 21,000 advisors.", [], "", ["number_not_found"])
    assert 'class="cee-flag">number_not_found</span>' in shown[0]


def test_figure_without_unit_matches_the_digits_but_a_wrong_unit_is_flagged():
    assert flags_for("serves nearly 21 households", "serves nearly 21 million households") == []
    assert flags_for("serves nearly 21 thousand households", "serves nearly 21 million households") == ["number_not_found"]


def test_mock_never_cuts_a_figure_in_half():
    from cee.answer.llm import _clip

    text = "word " * 58 + "with $11.90 trillion in client assets"
    assert _clip(text).endswith(("$11.90", "with")) and "trilli" not in _clip(text).split()[-1:]


# Found in the #61 real-model run: correct figures that the first rule flagged.

def test_table_cell_without_its_unit_header_matches_the_same_digits():
    # Q25: "$1,875 million" from an EDJ 10-Q table whose "(in millions)" header is in another chunk.
    assert flags_for("financial advisor compensation was $1,875 million",
                     "Compensation and benefits: Financial advisor $ 1,875 $ 1,653 13%") == []
    # Q24: "$11,903.0 billion" from a Schwab table cell "$ 11,903.0".
    assert flags_for("total client assets were $11,903.0 billion", "Total client assets 18% 3% $ 11,903.0") == []
    # Still flagged: a different figure, or a unit that contradicts the chunk's own unit.
    assert flags_for("$1,900 million", "Financial advisor $ 1,875") == ["number_not_found"]
    assert flags_for("21 thousand households", "21 million households") == ["number_not_found"]


def test_numeric_dates_and_section_labels_are_not_checked():
    assert flags_for("in the quarter ended 12/31/2025 (Item 11, Note 4)", "nothing numeric here") == []


# Boundary (#118): a claim that tells the home firm what to do is withheld, never shown.

from cee.answer.prompt import BOUNDARY_HANDOFF


def boundary_answer(*texts, behavior="answer"):
    return Answer(answerable=True, behavior=behavior,
                  claims=[{"text": t, "chunk_ids": ["EDJ-10K-2025#1"]} for t in texts])


def test_recommendation_for_the_home_firm_is_withheld_and_rejudged():
    a = boundary_answer("Schwab grew assets by acquiring clients through its RIA platform.",
                        "Edward Jones should build a similar low-cost acquisition channel.")
    out = check_citations(a, [hit()])
    assert [c.text for c in out.claims] == ["Schwab grew assets by acquiring clients through its RIA platform.",
                                            BOUNDARY_HANDOFF]
    assert out.behavior == "answer_with_boundary"
    assert [w.text for w in out.withheld] == ["Edward Jones should build a similar low-cost acquisition channel."]


def test_each_normative_form_is_caught():
    for text in ("EJ could replicate this by cutting account minimums.",
                 "We recommend that the firm expands its digital offering.",
                 "I would suggest Edward Jones targets younger investors.",
                 "It would be advisable to lower fees for small accounts.",
                 "The home firm needs to invest in AI tools.",
                 "Edward Jones would benefit from a self-directed platform.",
                 "It is recommended that Edward Jones lowers account minimums."):
        assert validate.is_normative(text), text


def test_evidence_with_should_or_recommend_is_not_withheld():
    for text in (BOUNDARY_HANDOFF,
                 "Schwab management said clients should be able to move assets easily.",
                 "The 10-K says financial advisors recommend products suited to each client.",
                 "Should market conditions worsen, the Partnership's revenue would decline.",
                 "Cerulli says younger investors prefer to keep more control."):
        assert not validate.is_normative(text), text


def test_boundary_answer_without_handoff_gets_it_once():
    a = boundary_answer("Evidence claim.", behavior="answer_with_boundary")
    out = check_citations(a, [hit()])
    assert out.claims[-1].text == BOUNDARY_HANDOFF and out.claims[-1].chunk_ids == ["EDJ-10K-2025#1"]
    again = check_citations(out, [hit()])
    assert [c.text for c in again.claims].count(BOUNDARY_HANDOFF) == 1


def test_plain_answer_is_untouched():
    out = check_citations(boundary_answer("The 2025 10-K lists 20,425 financial advisors."), [hit()])
    assert out.behavior == "answer" and out.withheld == [] and len(out.claims) == 1


def test_withheld_is_code_owned_and_shown_as_a_notice(monkeypatch):
    from cee.answer.schema import llm_output_schema
    from cee.app import components

    assert "withheld" not in llm_output_schema()["properties"]
    shown = []
    monkeypatch.setattr(components, "_html", shown.append)
    components.withheld_box(validate.WITHHELD_NOTICE)
    assert "withheld" in shown[0] and "should" not in shown[0].lower().replace("should act", "")


def test_filing_duties_of_the_named_firm_are_not_withheld():
    assert not validate.is_normative("The 10-K says Edward Jones must maintain minimum net capital under SEC rules.")
    assert validate.is_normative("The home firm must move faster than Schwab on digital onboarding.")


def test_transcript_speech_and_quotes_are_not_withheld():
    # Q6 (mock copies a transcript): an analyst's "we should expect" is not advice to the home firm.
    assert not validate.is_normative("Just trying to gauge whether we should expect this mix shift headwind to persist")
    assert not validate.is_normative('Schwab management said "we should continue to win share from Edward Jones".')
    assert validate.is_normative('Management said "growth is strong", so Edward Jones should copy the model.')
