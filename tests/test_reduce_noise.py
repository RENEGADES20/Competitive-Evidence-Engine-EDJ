"""#247 part 2 (plans/0247-reduce-2.md sections 4-5): duplicate claims, why-lines only for recency /
window items and never restating, the recency-only re-sort, the context line. Fakes only, 0 calls."""
import datetime as dt

from cee.answer import prompt as P
from cee.answer import reduce as R
from cee.answer.matrix import Cell, EvidenceMatrix, Item, finish
from cee.answer.schema import Answer, Claim
from cee.retrieve.fts import Hit, Query
from cee.retrieve.planner import Aspect

NO_SOURCES = lambda entity: ""   # noqa: E731


def H(cid, published="2026-11-12", text="Raymond James will add $18.7 billion in client assets to its FID as an "
      "existing program merges with Synovus. The move makes FID the largest bank program in the country."):
    return Hit(chunk_id=cid, doc_id=cid.split("#")[0], entity_id="RJF", segment=None, doc_type="trade",
               source_tier=4, published_at=published, period_end=None, section=None, page=None, rank=1.0, text=text)


def mat(aspects, cells, hits=()):
    m = EvidenceMatrix("q", rows=["RJF"], aspects=aspects, cells={c.id: c for c in cells})
    m.hits = {h.chunk_id: h for h in hits}
    return finish(m, sources=NO_SOURCES)


def cl(text, ids, part="a1.RJF"):
    return Claim(text=text, chunk_ids=list(ids), part_id=part)


# --- dedupe ---------------------------------------------------------------------------------------

def test_exact_repeats_across_aspects_keep_one():
    a = Answer(answerable=True, behavior="answer", claims=[
        cl("Industry research: 65% of young investors prefer a human advisor.", ["B#15"], "a1.research"),
        cl("Industry research: 87% are comfortable with AI.", ["B#15"], "a1.research"),
        cl("Industry research: 65% of young investors prefer a human advisor.", ["B#15"], "a5.research")])
    removed = R.dedupe_claims(a)
    assert len(a.claims) == 2 and removed[0]["part_id"] == "a5.research" and removed[0]["kept"] == 0


def test_subsumed_claims_keep_the_longer():
    a = Answer(answerable=True, behavior="answer", claims=[
        cl("A trade press report published November 12, 2026 reports that Raymond James will add $18.7 billion in "
           "client assets to its Financial Institutions Division as an existing FID program merges with Synovus "
           "Financial Corp. " + P.WHY_UNSAID, ["T#0"]),
        cl("A trade press report published November 12, 2026 reports that Raymond James will add $18.7 billion and 70 "
           "advisors to its Financial Institutions Division as an existing FID program merges with Synovus "
           "Financial Corp., with advisors expected to transition in May 2027. " + P.WHY_UNSAID, ["T#0"], "a2.RJF")])
    R.dedupe_claims(a)
    assert len(a.claims) == 1 and "70 advisors" in a.claims[0].text


def test_equal_text_different_chunks_both_kept():
    a = Answer(answerable=True, behavior="answer", claims=[cl("X had 5 advisors.", ["A#1"]),
                                                           cl("X had 5 advisors.", ["B#1"])])
    assert R.dedupe_claims(a) == [] and len(a.claims) == 2


def test_comparison_check_reruns_after_the_dedupe():
    a1 = Aspect("a1", "Figures.")
    a2 = Aspect("a2", "Whether the comparison is valid.", kind="comparison")
    m = mat([a1, a2], [Cell("a1.RJF", "RJF", "a1", "named", "fact", items=[Item("t", chunk_ids=["T#0"])]),
                       Cell("a2.RJF", "RJF", "a2", "named", "fact", items=[Item("t", chunk_ids=["T#0"])])],
            [H("T#0")])
    raw = Answer(answerable=True, behavior="answer", claims=[
        cl("Raymond James: the figures are not comparable.", ["T#0"], "a2"),
        cl("Raymond James: the figures are not comparable.", ["T#0"], "a1.RJF")])
    q = Query(question="q", entities=["RJF"])
    from tests.test_reduce import plan_of
    a, info = R.finish_answer(raw, m, q, plan_of(m), [H("T#0")], "q")
    assert len(info["duplicates_removed"]) == 1 and info["comparison_missing"] == []   # the kept one is a2's


# --- why-lines ------------------------------------------------------------------------------------

def test_why_line_removed_outside_recency_and_restating_one_replaced():
    rec = Aspect("a1", "Recent changes.", kind="recency")
    plain = Aspect("a2", "Headcount.", metric="advisor_headcount", kind="series")
    m = mat([rec, plain], [Cell("a1.RJF", "RJF", "a1", "named", "fact", items=[Item("t", chunk_ids=["T#0"])]),
                           Cell("a2.RJF", "RJF", "a2", "named", "fact", items=[Item("t", chunk_ids=["T#0"])])])
    a = Answer(answerable=True, behavior="answer", claims=[
        cl("Raymond James will add $18.7 billion in client assets. Why it might matter: the source reports the "
           "addition totals $18.7 billion in client assets.", ["T#0"]),
        cl("Raymond James will add $18.7 billion. Why it might matter: the source says it makes FID the largest "
           "bank program in the country.", ["T#0"]),
        cl("Raymond James had 8,943 advisors. Why it might matter: the same table also shows 8,787.", ["T#0"],
           "a2.RJF")])
    log = R.clean_why_lines(a, m, None)
    assert a.claims[0].text.endswith(P.WHY_UNSAID) and "why_line_restated" in a.claims[0].flags
    assert "largest bank program" in a.claims[1].text and not a.claims[1].flags
    assert P.WHY_LINE not in a.claims[2].text and "why_line_removed" in a.claims[2].flags
    assert log["restated"][0]["why"].startswith("the source reports") and log["removed"][0]["part_id"] == "a2.RJF"


def test_restates_rule():
    assert R.restates("X will add $18.7 billion in client assets.", "the addition totals $18.7 billion in client assets.")
    assert not R.restates("X will add $18.7 billion.", "it is the largest bank program in the country.")
    assert not R.restates("X will add $18.7 billion.", "assets rose 20% from $15.5 billion a year earlier.")
    assert not R.restates("X.", P.WHY_UNSAID[len(P.WHY_LINE):])


def test_context_line_only_for_recency_or_window_items_and_cut():
    long = "word " * 400
    rec = Aspect("a1", "Recent changes.", kind="recency")
    plain = Aspect("a2", "Headcount.")
    m = mat([rec, plain], [Cell("a1.RJF", "RJF", "a1", "named", "fact", items=[Item("t1", chunk_ids=["T#0"])]),
                           Cell("a2.RJF", "RJF", "a2", "named", "fact", items=[Item("t2", chunk_ids=["T#1"])])],
            [H("T#0", text="Start. " + long), H("T#1")])
    msg = R.reduce_message("q", m)
    ctx = [line for line in msg.splitlines() if line.strip().startswith("context:")]
    assert len(ctx) == 1 and len(ctx[0]) < R.CONTEXT_CHARS + 40


def test_repeated_item_marked_also_under():
    a1, a2 = Aspect("a1", "Preferences."), Aspect("a5", "Advice preferences.")
    m = mat([a1, a2], [Cell("a1.research", None, "a1", "research", "fact", items=[Item("65% prefer", chunk_ids=["B#1"])]),
                       Cell("a5.research", None, "a5", "research", "fact", items=[Item("65% prefer", chunk_ids=["B#1"])])])
    assert "[also under a1: write it once]" in R.reduce_message("q", m)


# --- re-sort ----------------------------------------------------------------------------------------

def _resort(window):
    rec = Aspect("a12", "Recent changes.", kind="recency")
    other = Aspect("a1", "Preferences.")
    m = mat([other, rec], [Cell("a1.RJF", "RJF", "a1", "named", "fact", items=[Item("t", chunk_ids=["O#1"])]),
                           Cell("a12.RJF", "RJF", "a12", "named", "fact", items=[Item("t", chunk_ids=["N#1"])])])
    by_id = {h.chunk_id: h for h in [H("O#1", "2026-01-01"), H("N#1", "2026-06-01"), H("N#2", "2026-09-01")]}
    a = Answer(answerable=True, behavior="answer", claims=[
        cl("old other", ["O#1"], "a1.RJF"), cl("rec june", ["N#1"], "a12.RJF"), cl("rec sep", ["N#2"], "a12.RJF")])
    q = Query(question="q", window=(dt.date(2026, 1, 1), dt.date(2026, 12, 31)) if window else None)
    R.order_newest_first(a, m, q, by_id)
    return [x.text for x in a.claims]


def test_without_window_only_recency_items_move_in_their_slots():
    assert _resort(False) == ["old other", "rec sep", "rec june"]


def test_with_window_the_whole_answer_is_sorted():
    assert _resort(True) == ["rec sep", "rec june", "old other"]


# --- gap scope in the answer (Q19) ------------------------------------------------------------------

def test_q19_shaped_answer_drops_out_of_scope_model_gaps_and_adds_no_part_gap():
    from cee.retrieve.planner import Plan, SubQuestion
    own = Aspect("a7", "How does Edward Jones management describe younger investors?", asked_firms=["EDJ"])
    pref = Aspect("a1", "What preferences do younger investors state?")
    cells = [Cell("a7.EDJ", "EDJ", "a7", "named", "fact", items=[Item("t", chunk_ids=["E#1"])]),
             Cell("a7.MS", "MS", "a7", "competitor", "not_found"),
             Cell("a1.EDJ", "EDJ", "a1", "named", "not_found"),
             Cell("a1.MS", "MS", "a1", "competitor", "not_found"), Cell("a1.RJF", "RJF", "a1", "competitor", "not_found")]
    m = EvidenceMatrix("How should the preferences of younger investors shape Edward Jones's offerings?",
                       rows=["EDJ", "MS", "RJF"], aspects=[pref, own], cells={c.id: c for c in cells})
    hit = H("E#1")
    m.hits = {"E#1": hit}
    finish(m, sources=NO_SOURCES)
    plan = Plan(aspects=[pref, own], subquestions=[SubQuestion(c.id, c.entity, m.aspect(c.aspect_id), c.role)
                                                   for c in cells])
    raw = Answer(answerable=True, behavior=m.behavior, claims=[cl("Edward Jones: t.", ["E#1"], "a7.EDJ")],
                 gaps=[{"what": "Morgan Stanley - a7: not found.", "part_id": "a7.MS"},
                       {"what": "Morgan Stanley - a1: not found.", "part_id": "a1.MS"}])
    a, info = R.finish_answer(raw, m, Query(question=m.question, entities=["EDJ"]), plan, [hit], m.question)
    assert not any("part_gap" in g.flags for g in a.gaps)
    assert not any(g.part_id == "a7.MS" for g in a.gaps)
    fold = next(g for g in a.gaps if "matrix_competitors_not_found" in g.flags)
    assert "model_also_named" in fold.flags and "a1" == fold.part_id


# --- #247 part 2 revision (R1, R4) ---------------------------------------------------------------------

def test_r1_restating_why_kept_when_it_cites_background_and_related_items_rendered():
    rec = Aspect("a5", "Recent financial results.", kind="recency")
    m = mat([rec], [Cell("a5.RJF", "RJF", "a5", "named", "fact", items=[
        Item("Raymond James reported revenue of $4.74 billion.", chunk_ids=["T#1"]),
        Item("Raymond James reported revenue of $4.20 billion a year earlier.", chunk_ids=["T#2"])])],
        [H("T#1"), H("T#2")])
    a = Answer(answerable=True, behavior="answer", claims=[
        cl("Raymond James reported revenue of $4.74 billion. Why it might matter: revenue was $4.74 billion.",
           ["T#1"], "a5.RJF"),
        cl("Raymond James reported revenue of $4.74 billion. Why it might matter: revenue of $4.74 billion.",
           ["T#1", "T#2"], "a5.RJF"),
        cl("X. " + P.WHY_UNSAID, ["T#1"], "a5.RJF")])
    log = R.clean_why_lines(a, m, None)
    assert "why_line_restated" not in a.claims[1].flags        # cites another passage: kept
    assert len(log["unsaid"]) == 1                             # model-written, counted, left alone
    m2 = mat([rec], [Cell("a5.RJF", "RJF", "a5", "named", "fact", items=[
        Item("Raymond James reported revenue of $4.74 billion.", chunk_ids=["T#1"])])], [H("T#1")])
    a2 = Answer(answerable=True, behavior="answer", claims=[cl(
        "Raymond James reported revenue of $4.74 billion. Why it might matter: revenue was $4.74 billion.",
        ["T#1"], "a5.RJF")])
    R.clean_why_lines(a2, m2, None)
    assert "why_line_restated" in a2.claims[0].flags           # only its own chunk: replaced
    assert "related: cite T#2" in R.reduce_message("q", m)


def test_r4_comparison_gap_added_once_and_normative_comparison_covered_by_handoff():
    from cee.answer.prompt import BOUNDARY_HANDOFF
    comp = Aspect("a13", "How should younger-investor preferences shape Edward Jones's offerings?", kind="comparison")
    plain = Aspect("a2", "Whether the comparison is valid.", kind="comparison")
    m = mat([comp, plain], [Cell("a13.EDJ", "EDJ", "a13", "named", "not_found"),
                            Cell("a2.EDJ", "EDJ", "a2", "named", "not_found")])
    a = Answer(answerable=True, behavior="answer_with_boundary", claims=[Claim(text=BOUNDARY_HANDOFF, chunk_ids=[])])
    assert R.check_comparisons(a, m) == ["a2"] and R.check_comparisons(a, m) == ["a2"]
    assert sum("comparison_missing" in g.flags for g in a.gaps) == 1


def test_r4_model_gap_contradicting_a_found_claim_dropped():
    own = Aspect("a7", "How does Edward Jones management describe younger investors?", asked_firms=["EDJ"])
    m = mat([own], [Cell("a7.EDJ", "EDJ", "a7", "named", "fact", items=[Item("t", chunk_ids=["E#1"])]),
                    Cell("a7.MS", "MS", "a7", "competitor", "not_found")])
    a = Answer(answerable=True, behavior="answer", gaps=[
        {"what": "Morgan Stanley, Merrill - how Edward Jones management describes younger investors: not found.",
         "part_id": "a7"}, {"what": "Edward Jones - a7: not found.", "part_id": "a7.EDJ"}])
    log = []
    R.place_gaps(a, m, log)
    assert len(log) == 2 and not any(g.part_id in ("a7", "a7.EDJ") and not g.flags for g in a.gaps)
