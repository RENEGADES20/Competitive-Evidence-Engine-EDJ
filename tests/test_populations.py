"""#247 part 2 (plans/0247-reduce-2.md section 1, TL conditions 1-3): populations of ratio inputs,
approximate figures, pinned population sources, code computability claims. No paid call; the
database tests skip without one."""
import re

import psycopg
import pytest
import yaml

from cee.answer import matrix as mx
from cee.answer import reduce as R
from cee.answer.matrix import Cell, EvidenceMatrix, Item
from cee.answer.schema import Answer
from cee.config import REPO_ROOT, settings
from cee.retrieve import planner
from cee.retrieve.fts import Hit, Query
from cee.retrieve.planner import Aspect, Plan, SubQuestion

NO_SOURCES = lambda entity: ""   # noqa: E731

POPS = (
    {"entity": "RJF", "input": "client_assets", "key": "rjf_aua_incl_rcs", "match": ["client assets under administration"],
     "quote": "their client assets are included in PCG AUA.", "chunk_id": "RJF-10K#228", "valid_from": "2025-09-30"},
    {"entity": "RJF", "input": "advisor_headcount", "key": "rjf_advisors_excl_rcs", "match": ["financial advisors"],
     "quote": "Advisors in our RCS division are not included", "chunk_id": "RJF-10K#228", "valid_from": "2025-09-30"},
    {"entity": "MS", "input": "client_assets", "key": "ms_wm_all_channels", "match": ["total client assets"],
     "quote": "three channels: Advisor-Led, Self-Directed and Workplace.", "chunk_id": "MS-10K#125",
     "valid_from": "2025-12-31"},
    {"entity": "MS", "input": "client_assets", "key": "ms_wm_advisor_led", "match": ["advisor-led client assets"],
     "quote": "Advisor-led client assets represent client assets in accounts that have a Wealth Management "
              "representative assigned.", "chunk_id": "MS-SUPP#38", "valid_from": "2026-09-30"},
    {"entity": "MS", "input": "advisor_headcount", "key": "ms_wm_advisor_led",
     "match": ["wealth management representatives"],
     "quote": "Advisor-led client assets represents client assets in accounts that have a Wealth Management "
              "representative assigned.", "chunk_id": "MS-SUPP20#3", "valid_from": "2020-12-31"},
    {"entity": "EDJ", "input": "client_assets", "key": "edj_firm", "match": ["client assets under care"], "scope": "",
     "quote": "Client assets under care ($ billions): Total: At period end", "chunk_id": "EDJ-10Q#59",
     "valid_from": "2026-06-26"},
    {"entity": "EDJ", "input": "advisor_headcount", "key": "edj_firm", "match": ["financial advisors (actual)"],
     "scope": "", "quote": "Financial advisors (actual): At year end", "chunk_id": "EDJ-10K#130",
     "valid_from": "2025-12-31"},
)
POP_IDS = {p["chunk_id"] for p in POPS}


@pytest.fixture(autouse=True)
def _pops(monkeypatch):
    monkeypatch.setattr(mx, "_populations", lambda: POPS)


A1 = Aspect("a1", "Client assets per financial advisor.")
A2 = Aspect("a2", "Total client assets, the numerator.", proxy=True)
A3 = Aspect("a3", "Number of financial advisors.", metric="advisor_headcount", proxy=True)
A4 = Aspect("a4", "Whether the comparison is valid.", kind="comparison")


@pytest.fixture(autouse=True)
def _reduce_v52(monkeypatch):
    """These tests pin the list-form reduce v5.2 (the default is v5.2 again since #297)."""
    monkeypatch.setenv("REDUCE_PROMPT", "v5.2")


def it(cid, value, quote, period="2025-09-30", scope="", unit=""):
    return Item(text=f"t {value}", quote=quote, chunk_ids=[cid], value=value, unit=unit, period=period, scope=scope)


def ratio_matrix(firm, assets, fas, pools_extra=POP_IDS, hits=()):
    cells = [Cell(f"a1.{firm}", firm, "a1", "named", "not_disclosed", derivation={"operation": "ratio", "inputs": [
                 {"subquestion_id": f"a2.{firm}", "item": 0}, {"subquestion_id": f"a3.{firm}", "item": 0}]}),
             Cell(f"a2.{firm}", firm, "a2", "named", "fact", items=[assets]),
             Cell(f"a3.{firm}", firm, "a3", "named", "fact", items=[fas])]
    m = EvidenceMatrix("Client assets per advisor across the five?", rows=[firm], aspects=[A1, A2, A3, A4],
                       cells={c.id: c for c in cells})
    m.pools = {c.id: set(pools_extra) | {x for i in c.items for x in i.chunk_ids} for c in cells}
    m.hits = {h.chunk_id: h for h in hits}
    return mx.finish(m, sources=NO_SOURCES)


def test_rjf_aua_incl_rcs_over_advisors_excl_rcs_is_refused_with_both_sources():
    m = ratio_matrix("RJF", it("RJF-SUPP#9", "1,730.6", "Client assets under administration | $ 1,730.6", unit="USD billions"),
                     it("RJF-TR#4", "8,943", "a record number of financial advisors of 8,943"))
    d = m.cells["a1.RJF"].derivation
    assert not d["ok"] and d["why"] == "populations differ"
    assert d["population_chunk_ids"] == ["RJF-10K#228"]
    assert "RJF-10K#228" in m.chunk_ids()   # citable (TL condition 1)


def test_ms_total_client_assets_over_representatives_refused_advisor_led_accepted():
    reps = it("MS-SUPP20#1", "15,950", "Wealth Management representatives 15,950 15,469", period="2020-12-31")
    total = it("MS-SUPP20#1", "3,999", "Total client assets $ 3,999 $ 2,852", period="2020-12-31", unit="USD billions")
    led = it("MS-SUPP20#1", "3,167", "Total client assets $ 3,999 ... Advisor-led client assets $ 3,167",
             period="2020-12-31", unit="USD billions")
    assert not ratio_matrix("MS", total, reps).cells["a1.MS"].derivation["ok"]
    m = ratio_matrix("MS", led, reps)   # nearest phrase before the figure decides: advisor-led
    d = m.cells["a1.MS"].derivation
    assert d["ok"] and m.cells["a1.MS"].label == "derived"
    assert set(d["population_chunk_ids"]) == {"MS-SUPP#38", "MS-SUPP20#3"}


def test_edj_firm_over_firm_accepted_and_over_us_count_refused():
    assets = it("EDJ-10Q#59", "$2,647", "Client assets under care ($ billions): Total: At period end $ 2,647 "
                "increased over the prior year", period="2026-06-26", unit="USD billions")
    firm = it("EDJ-10Q#60", "20,514", "Financial advisors (actual): At period end 20,514", period="2026-06-26")
    us = it("EDJ-10Q#60", "19,647", "Financial advisors (actual): At period end 19,647", period="2026-06-26",
            scope="U.S.")
    ok = ratio_matrix("EDJ", assets, firm).cells["a1.EDJ"].derivation
    assert ok["ok"], ok   # "over the prior year" is not next to the figure: not approximate (note 1)
    bad = ratio_matrix("EDJ", assets, us).cells["a1.EDJ"].derivation
    assert not bad["ok"]   # the U.S. count: scopes differ / no registered population


@pytest.mark.parametrize("value, quote", [
    (">15K", ">15K Wealth Advisors"), ("more than 20,000", "more than 20,000 financial advisors"),
    ("approximately 9,000", "approximately 9,000 financial advisors"),
    ("9,000", "approximately 9,000 financial advisors"), ("8,900", "about 8,900 advisors"),
])
def test_approximate_figures(value, quote):
    assert mx.approximate(Item(text="t", quote=quote, value=value))


def test_not_approximate_when_the_marker_is_elsewhere():
    assert not mx.approximate(Item(text="t", quote="increased over the prior year to 20,514 advisors", value="20,514"))
    assert not mx.approximate(Item(text="t", quote="20,514 advisors, up 1% over 2025", value="20,514"))


def test_approximate_input_refused():
    m = ratio_matrix("EDJ", it("EDJ-10Q#59", "$2,647", "Client assets under care ($ billions): Total: $ 2,647",
                               period="2025-12-31", unit="USD billions"),
                     it("EDJ-10K#130", "more than 20,000", "Financial advisors (actual): more than 20,000",
                        period="2025-12-31"))
    d = m.cells["a1.EDJ"].derivation
    assert not d["ok"] and d["why"].startswith("approximate")


def test_population_source_outside_the_pool_gives_no_key():
    m = ratio_matrix("RJF", it("RJF-SUPP#9", "1,730.6", "Client assets under administration | $ 1,730.6"),
                     it("RJF-TR#4", "8,943", "financial advisors of 8,943"), pools_extra=set())
    assert m.cells["a2.RJF"].items[0].population == ""
    d = m.cells["a1.RJF"].derivation
    assert not d["ok"] and d["why"].startswith("population not stated") and d["population_chunk_ids"] == []


def test_two_keys_at_the_same_distance_give_no_key():
    e = [{"key": "a", "match": ["client assets"], "chunk_id": "X"}, {"key": "b", "match": ["client assets"],
                                                                      "chunk_id": "Y"}]
    assert mx._match_entry(Item(text="t", quote="client assets 5", value="5"), e) is None


# --- which aspects pin population sources (TL condition 2) ---------------------------------------

def test_population_inputs_rule():
    assert mx.population_inputs(A2) == ["client_assets"]
    assert mx.population_inputs(A3) == ["advisor_headcount"]
    assert mx.population_inputs(A1) == [] and mx.population_inputs(A4) == []
    assert mx.population_inputs(Aspect("a9", "The closest disclosed figure.", proxy=True)) == list(mx.POPULATION_INPUTS)
    nna = Aspect("a1", "Net new assets by quarter.", metric="net_new_assets", kind="series")
    assert mx.population_inputs(nna) == []
    assert mx.population_inputs(Aspect("a2", "NNA as a stand-in.", metric="net_new_assets", proxy=True)) == []


def test_q22_shaped_nna_aspect_gets_no_population_pins(monkeypatch):
    monkeypatch.setattr(mx, "_populations", lambda: tuple(config_pops()))
    nna = Aspect("a1", "Net new assets by quarter.", metric="net_new_assets", kind="series")
    for firm in ("EDJ", "MS", "SCHW", "MER", "RJF"):
        assert mx.population_entries(firm, nna) == []
        d = mx.metric_definition(firm, "net_new_assets")
        ids, _ = planner.pinned_ids(firm, nna)
        assert ids == list(dict.fromkeys([d["chunk_id"], *d.get("see_also", [])]))[:planner.PIN_MAX]


def test_pin_order_populations_first_then_definition_then_see_also_and_cut_logged(monkeypatch):
    monkeypatch.setattr(planner, "PIN_MAX", 3)
    ids, cut = planner.pinned_ids("EDJ", A3)
    d = mx.metric_definition("EDJ", "advisor_headcount")
    order = ["EDJ-10K#130", d["chunk_id"], *d["see_also"]]
    assert ids == order[:3] and cut == [x for x in order[3:] if x not in ids]   # cut returned (logged)


# --- the code computability claim (TL D5, condition 1) ---------------------------------------------

def H(cid, entity, text, period="2025-09-30", published="2025-11-25"):
    return Hit(chunk_id=cid, doc_id=cid.split("#")[0], entity_id=entity, segment=None, doc_type="10-K",
               source_tier=2, published_at=published, period_end=period, section="Item 7", page=None, rank=1.0,
               text=text, origin="search")


RJF_HITS = [H("RJF-SUPP#9", "RJF", "Client assets under administration | $ 1,730.6"),
            H("RJF-TR#4", "RJF", "a record number of financial advisors of 8,943"),
            H("RJF-10K#228", "RJF", "Advisors in our RCS division are not included in our financial advisor metric "
                                   "although their client assets are included in PCG AUA.", published="2025-11-25")]


def _plan(m):
    return Plan(aspects=list(m.aspects), subquestions=[SubQuestion(c.id, c.entity, m.aspect(c.aspect_id))
                                                       for c in m.cells.values()])


def test_code_adds_not_computed_claim_citing_inputs_and_quoted_source():
    m = ratio_matrix("RJF", it("RJF-SUPP#9", "1,730.6", "Client assets under administration | $ 1,730.6"),
                     it("RJF-TR#4", "8,943", "a record number of financial advisors of 8,943"), hits=RJF_HITS)
    q = Query(question=m.question, entities=["RJF"])
    raw = {"answerable": True, "behavior": m.behavior, "adjacent": [], "gaps": [], "claims": [
        {"text": "Raymond James: client assets were $1,730.6 billion.", "chunk_ids": ["RJF-SUPP#9"],
         "part_id": "a2.RJF"}]}
    a, info = R.finish_answer(Answer(**raw), m, q, _plan(m), RJF_HITS, m.question)
    code = [x for x in a.claims if "code_computability" in x.flags]
    assert len(code) == 1 and info["code_computability"] == ["a1.RJF"]
    c = code[0]
    assert set(c.chunk_ids) == {"RJF-SUPP#9", "RJF-TR#4", "RJF-10K#228"}
    assert "not computed: the two figures cover different populations" in c.text
    assert '"their client assets are included in PCG AUA."' in c.text or "PCG AUA" in c.text
    assert "dated" not in c.text   # both inputs in the statement's quarter (2025Q3)
    for bad in ("outside_matrix", "unmatched_citation", "number_not_found", "no_citation"):
        assert bad not in c.flags, bad


def test_model_claim_citing_inputs_and_sources_means_no_code_claim():
    m = ratio_matrix("RJF", it("RJF-SUPP#9", "1,730.6", "Client assets under administration | $ 1,730.6"),
                     it("RJF-TR#4", "8,943", "a record number of financial advisors of 8,943"), hits=RJF_HITS)
    raw = {"answerable": True, "behavior": m.behavior, "adjacent": [], "gaps": [], "claims": [
        {"text": "Raymond James: not computable, the populations differ.", "chunk_ids": [
            "RJF-SUPP#9", "RJF-TR#4", "RJF-10K#228"], "part_id": "a1.RJF"}]}
    a, info = R.finish_answer(Answer(**raw), m, Query(question=m.question, entities=["RJF"]), _plan(m), RJF_HITS,
                              m.question)
    assert info["code_computability"] == [] and not any("code_computability" in x.flags for x in a.claims)


def test_dated_label_both_directions():
    newer = {"populations": [{"chunk_id": "S#1", "quote": "q", "valid_from": "2025-09-30", "period": "2026-06-30"}]}
    older = {"populations": [{"chunk_id": "S#1", "quote": "q", "valid_from": "2025-12-31", "period": "2020-12-31"}]}
    same = {"populations": [{"chunk_id": "S#1", "quote": "q", "valid_from": "2025-09-30", "period": "2025-09-30"}]}
    m = EvidenceMatrix("q", rows=[])
    assert R.population_sources(m, newer)[0]["dated"] and R.population_sources(m, older)[0]["dated"]
    assert not R.population_sources(m, same)[0]["dated"]
    assert "dated September 30, 2025" in R._sources_text(R.population_sources(m, newer))


def test_computed_claim_citing_inputs_plus_population_ids_passes_the_number_check():
    edj_hits = [H("EDJ-10Q#59", "EDJ", "Client assets under care ($ billions): Total: At period end $ 2,647",
                  period="2026-06-26", published="2026-08-07"),
                H("EDJ-10Q#60", "EDJ", "Financial advisors (actual): At period end 20,514", period="2026-06-26",
                  published="2026-08-07"),
                H("EDJ-10K#130", "EDJ", "Financial advisors (actual): At year end 20,425 20,125 19,232",
                  period="2025-12-31", published="2026-03-13")]
    m = ratio_matrix("EDJ", it("EDJ-10Q#59", "$2,647", "Client assets under care ($ billions): Total: At period "
                               "end $ 2,647", period="2026-06-26", unit="USD billions"),
                     it("EDJ-10Q#60", "20,514", "Financial advisors (actual): At period end 20,514",
                        period="2026-06-26"), hits=edj_hits)
    raw = {"answerable": True, "behavior": m.behavior, "adjacent": [], "gaps": [], "claims": []}
    a, info = R.finish_answer(Answer(**raw), m, Query(question=m.question, entities=["EDJ"]), _plan(m), edj_hits,
                              m.question)
    c = next(x for x in a.claims if "code_computability" in x.flags)
    assert "computed by code" in c.text and "129,033,831" in c.text and "dated December 31, 2025" in c.text
    assert "computed" in c.flags and "number_not_found" not in c.flags
    assert set(c.chunk_ids) == {"EDJ-10Q#59", "EDJ-10Q#60", "EDJ-10K#130"}


def test_code_claims_cite_only_chunks_in_the_sub_question_pools(monkeypatch):
    """Blocking 2d: through search_subquestions with fake searches and a fake pin fetch, every id a code
    computability claim cites is in plan.pools of its sub-questions and passes check_citations."""
    hits_by = {"a2.RJF": [RJF_HITS[0]], "a3.RJF": [RJF_HITS[1]]}

    def fake_search(q, trace=None, tokens=None, exclude=None, research=True, peers=True, text=None, k=None):
        return []

    plan = Plan(aspects=[A1, A2, A3], subquestions=[SubQuestion(f"{a.id}.RJF", "RJF", a) for a in (A1, A2, A3)])

    def fake_pin(q, ids):
        return [h for h in RJF_HITS if h.chunk_id in ids]
    monkeypatch.setattr(planner.fts, "budget_tokens", lambda q: 40000)
    q = Query(question="Client assets per advisor at Raymond James?", entities=["RJF"])
    got = planner.search_subquestions(q, plan, search_fn=fake_search, research_fn=lambda q, trace=None: [],
                                      pin_fn=fake_pin)
    assert {h.chunk_id for h in got if h.origin == "pinned"} == {"RJF-10K#228"}
    assert all("RJF-10K#228" in plan.pools[s] for s in ("a2.RJF", "a3.RJF"))
    assert "RJF-10K#228" not in plan.pools.get("a1.RJF", set())   # a1: no ratio input, no pin
    # the map's cells, built from these hits and pools
    cells = [Cell("a1.RJF", "RJF", "a1", "named", "not_disclosed", derivation={"operation": "ratio", "inputs": [
                 {"subquestion_id": "a2.RJF", "item": 0}, {"subquestion_id": "a3.RJF", "item": 0}]}),
             Cell("a2.RJF", "RJF", "a2", "named", "fact",
                  items=[it("RJF-SUPP#9", "1,730.6", "Client assets under administration | $ 1,730.6")]),
             Cell("a3.RJF", "RJF", "a3", "named", "fact", items=[it("RJF-TR#4", "8,943", "financial advisors of 8,943")])]
    m = EvidenceMatrix(q.question, rows=["RJF"], aspects=[A1, A2, A3], cells={c.id: c for c in cells})
    m.pools = {k: set(v) | {x for i in m.cells[k].items for x in i.chunk_ids} for k, v in plan.pools.items()}
    all_hits = got + [h for hs in hits_by.values() for h in hs]
    m.hits = {h.chunk_id: h for h in all_hits}
    mx.finish(m, sources=NO_SOURCES)
    a, _ = R.finish_answer(Answer(answerable=True, behavior=m.behavior), m, q, plan, all_hits, q.question)
    c = next(x for x in a.claims if "code_computability" in x.flags)
    union = set().union(*plan.pools.values()) | {x for i in cells for it_ in i.items for x in it_.chunk_ids}
    assert set(c.chunk_ids) <= union
    assert not {"outside_matrix", "unmatched_citation", "no_citation"} & set(c.flags)


# --- config (database checks skip without one) ------------------------------------------------------

def config_pops():
    return yaml.safe_load((REPO_ROOT / "config" / "metric_definitions.yaml").read_text(encoding="utf-8"))["populations"]


@pytest.mark.parametrize("p", config_pops(), ids=lambda p: f"{p['entity']}-{p['input']}-{p['key']}")
def test_population_entries_are_complete(p):
    assert p["input"] in mx.POPULATION_INPUTS and re.fullmatch(r"[a-z0-9_]+", p["key"])
    assert p.get("match") and p.get("quote") and p.get("chunk_id") and p.get("valid_from") and p.get("covers")


def test_population_quotes_verbatim_and_valid_from_is_the_period_end():
    pops = config_pops()
    try:
        with psycopg.connect(settings().database_url, connect_timeout=3) as conn:
            rows = conn.execute("SELECT c.chunk_id, c.text, d.period_end, d.published_at FROM chunks c "
                                "JOIN documents d USING (doc_id) WHERE c.chunk_id = ANY(%s)",
                                ([p["chunk_id"] for p in pops],)).fetchall()
    except psycopg.OperationalError:
        pytest.skip("database not running")
    if not rows:
        pytest.skip("no corpus loaded")
    by = {r[0]: r for r in rows}
    for p in pops:
        cid, text, period_end, published = by[p["chunk_id"]]
        assert " ".join(p["quote"].split()) in " ".join(text.split()), p["chunk_id"]
        assert str(p["valid_from"]) == str(period_end or published), p["chunk_id"]


# --- #247 part 2 revision (R2) ---------------------------------------------------------------------

def test_r2_phrase_after_the_figure_reads_the_whole_quote():
    m = ratio_matrix("RJF", it("RJF-SUPP#9", "1,730.6", "Client assets under administration | $ 1,730.6"),
                     it("RJF-10K#9", "8,943", "We had 8,943 employee and independent contractor financial advisors "
                        "affiliated with us as of September 30, 2025."))
    assert m.cells["a3.RJF"].items[0].population == "rjf_advisors_excl_rcs"
    assert m.cells["a1.RJF"].derivation["why"] == "populations differ"


def test_r2_registered_ratio_is_not_definition_unverified():
    m = ratio_matrix("EDJ", it("EDJ-10Q#59", "$2,647", "Client assets under care ($ billions): Total: At period end "
                               "$ 2,647", period="2026-06-26", unit="USD billions"),
                     it("EDJ-10Q#60", "20,514", "Financial advisors (actual): At period end 20,514", period="2026-06-26"))
    assert m.cells["a1.EDJ"].label == "derived" and "definition_unverified" not in m.cells["a1.EDJ"].flags
    assert m.marks["a1"].status == "none"
