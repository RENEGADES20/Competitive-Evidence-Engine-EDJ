"""#291: the Ask page draws the answer above the evidence, with footnotes [n] into the evidence cards (0 calls)."""
import re
from types import SimpleNamespace as NS

from cee import ask as pipeline
from cee.answer.schema import Answer, Claim
from cee.app import components as ui
from cee.app.views import ask_page as P
from cee.retrieve.fts import Query
from tests.test_ask_progress import HITS, hit

H244, H246, H85 = HITS


def line(entity: str, hits, text="MS recruited advisors.") -> dict:
    return {"cell": f"a1.{entity}", "entity": entity, "aspect": "a1", "text": text, "value": None,
            "chunk_ids": [h.chunk_id for h in hits], "hits": list(hits)}


def test_a_claim_footnote_points_at_the_first_card_that_cites_its_chunk():
    lines = [line("MER", [H244]), line("MER", [H246, H244])]
    cards, items = P.evidence_cards(lines, [Claim(text="a", chunk_ids=["BAC-10K-2025#244", "BAC-10K-2025#246"])],
                                    HITS)
    assert len(cards) == 2 and items[0]["footnotes"] == [1, 2] and items[0]["unlinked"] == []


def test_a_cited_chunk_with_no_card_gets_a_source_card():
    cards, items = P.evidence_cards([line("MER", [H244])],
                                    [Claim(text="a", chunk_ids=["BAC-10Q-2026Q2#85"]),
                                     Claim(text="b", chunk_ids=["BAC-10Q-2026Q2#85", "BAC-10K-2025#244"])], HITS)
    assert [c["label"] for c in cards] == ["EVIDENCE - Merrill - a1", P.SOURCE_LABEL]
    assert cards[1]["hits"] == [H85] and cards[1]["text"] == "Net income for GWIM increased."
    assert items[0]["footnotes"] == [2] and items[1]["footnotes"] == [2, 1]   # one SOURCE card, reused


def test_an_id_outside_the_retrieved_set_gets_no_card_and_stays_an_unlinked_chip():
    cards, items = P.evidence_cards([], [Claim(text="a", chunk_ids=["NOT-RETRIEVED#1", "BAC-10K-2025#244"])], HITS)
    assert [c["hits"] for c in cards] == [[H244]]   # no evidence lines: the cards are the cited chunks
    assert items[0]["footnotes"] == [1] and items[0]["unlinked"] == ["NOT-RETRIEVED#1"]
    html = ui.answer_html(items, as_list=False)
    assert '<span class="id">NOT-RETRIEVED#1</span>' in html and "not in the retrieved set" in html
    assert 'href="#cee-ev-1"' in html and "?chunk=NOT-RETRIEVED" not in html


def test_window_or_recency_answers_are_a_list_others_a_paragraph(monkeypatch):
    monkeypatch.setenv("REDUCE_PROMPT", "v5.2")   # #291 rule under v5.2; v8: tests/test_reduce_synthesis.py
    fact, recency = NS(kind="fact"), NS(kind="recency")
    assert P.list_form(Query(question="q", window=("2026-08-01", "2026-11-01")), [fact])
    assert P.list_form(Query(question="q"), [fact, recency])
    assert not P.list_form(Query(question="q"), [fact]) and not P.list_form(None, [])
    items = [{"text": "Item one. Why it might matter: the source does not say.", "footnotes": [1]},
             {"text": "Item two.", "footnotes": [2]}]
    listed = ui.answer_html(items, as_list=True)
    assert listed.count("<li") == 2 and '<span class="why">Why it might matter: the source does not say.</span>' in listed
    para = ui.answer_html(items, as_list=False, fade_from=1)
    assert "<li" not in para and "<p>" in para and para.count("cee-fade") == 1   # only the newest sentence fades in


def anchors_resolve(html: str) -> bool:
    targets = re.findall(r'href="#(cee-ev-\d+)"', html)
    return bool(targets) and all(f'id="{t}"' in html for t in targets)


def page():
    from cee.app.views.ask_page import ask_with_trace
    ask_with_trace("What is Merrill's standalone profitability?")


def test_the_finished_run_draws_the_answer_above_the_evidence_and_every_footnote_resolves(monkeypatch):
    from streamlit.testing.v1 import AppTest
    monkeypatch.setattr(pipeline, "resolve", lambda q: Query(question=q, entities=["MER"]))
    monkeypatch.setattr(pipeline, "search_subquestions", lambda q, plan, **kw: HITS)
    monkeypatch.setattr(pipeline, "_log", lambda r, p: 1)
    at = AppTest.from_function(page).run()
    assert not at.exception and not at.error
    texts = [m.value for m in at.markdown]
    answer_i = next(i for i, t in enumerate(texts) if "cee-answer" in t)
    card_i = next(i for i, t in enumerate(texts) if "EVIDENCE - Merrill" in t)
    assert answer_i < card_i and texts[card_i - 1] == f"**{P.EVIDENCE_FINAL_HEADING}**"
    assert anchors_resolve(" ".join(texts))
    assert P.EARLY_HEADING not in " ".join(texts)   # the streamed claims were replaced by the final answer


def render_page():
    from cee.app.views import ask_page
    ask_page.render()


def test_a_rerun_keeps_answer_and_evidence_from_session_state(monkeypatch):
    """The Coverage -> Ask round trip or a feedback click: answer, evidence, footer, no new run."""
    from streamlit.testing.v1 import AppTest

    from cee.answer.runcache import RunCache
    monkeypatch.setattr(P.ui, "corpus_stats", lambda: {"snapshot": "s", "firms": 5, "docs": 1, "chunks": 1,
                                                        "latest": "2026-01-01"})
    monkeypatch.setattr(P, "ask", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no run on a rerun")))
    a = Answer(answerable=True, behavior="answer",
               claims=[Claim(text="Merrill's net income rose.", chunk_ids=["BAC-10K-2025#244"]),
                       Claim(text="A 10-Q says so too.", chunk_ids=["BAC-10Q-2026Q2#85"])])
    r = pipeline.Result(Query(question="q", entities=["MER"]), HITS, a, query_id=None)
    run = P.Run("q", {}, RunCache("q"))
    run.status, run.result, run.evidence = "done", r, [line("MER", [H244], "GWIM net income increased.")]
    at = AppTest.from_function(render_page)
    at.session_state["ask_run"] = run
    at.session_state["last_answer"] = (r, {})
    at.run()
    assert not at.exception
    texts = [m.value for m in at.markdown]
    answer_i = next(i for i, t in enumerate(texts) if "cee-answer" in t)
    ev_i = next(i for i, t in enumerate(texts) if "EVIDENCE - Merrill - a1" in t)
    src_i = next(i for i, t in enumerate(texts) if ">SOURCE<" in t)
    meta_i = next(i for i, t in enumerate(texts) if "LLM called:" in t)
    assert answer_i < ev_i < src_i < meta_i
    assert anchors_resolve(" ".join(texts)) and 'href="#cee-ev-2"' in texts[answer_i]
