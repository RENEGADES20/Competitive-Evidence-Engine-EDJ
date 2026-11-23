"""#284 (plans/0284-reduce-short.md): reduce prompt v6, item refs rendered by code. Schema and message, rendering,
ref / part rules (TL B2), matrix provenance (TL B3), render fidelity with a mutation test (TL B4), streamed claims and
the Ask page (TL B5), the mock. Fake clients only: 0 real calls."""
import json

import pytest

from cee import ask as pipeline
from cee.answer import prompt as P
from cee.answer import reduce as R
from cee.answer.matrix import row_name
from cee.answer.validate import _retrieved, source_label
from cee.retrieve.fts import Query
from cee.retrieve.planner import Aspect
from tests.test_llm_deepseek import _strict_problems
from tests.test_reduce import H, _one_population, cell, item, matrix, plan_of, q24_shaped  # noqa: F401
from tests.test_stream_idle import Client


@pytest.fixture(autouse=True)
def _v6(monkeypatch):
    monkeypatch.setenv("REDUCE_PROMPT", "v6")


# --- render fidelity (TL B4): an independent re-check of one rendered item ------------------------------

def fidelity(x: dict, r: dict, m) -> list[str]:
    """Problems of rendered item `r` against its v6 item `x`: every valid ref's item text verbatim, its firm prefix
    (the ref cell's row name, multi-firm or research), its scope, source label (without tier) and publication date of
    the item's first chunk id; a derived ref's formula text and input ids; the why-line once, after P.WHY_LINE; chunk
    ids = union of the refs' ids and `chunk_ids`. [] = faithful."""
    refs, out = R.item_refs(m), []
    firms = [f for f in m.rows if f not in ("research", "all")]
    want_ids: list[str] = []
    text = r["text"]
    for ref in x.get("items") or []:
        got = refs.get(ref)
        if got is None or not (got[0].id == x["part_id"] or got[0].aspect_id == x["part_id"]):
            continue
        c, i = got
        if len(firms) > 1 or c.role == "research":
            if f"{row_name(c)}: " not in text:
                out.append(f"{ref}: firm prefix {row_name(c)!r} missing")
        if i is None:
            d = c.derivation or {}
            if str(d.get("formula_text")) not in text:
                out.append(f"{ref}: formula missing")
            want_ids += list(d.get("input_chunk_ids") or [])
            continue
        body = R._q(i.text).rstrip().rstrip(".")
        if body not in text:
            out.append(f"{ref}: item text missing")
        if i.scope and R._q(i.scope).lower() not in text.lower():
            out.append(f"{ref}: scope missing")
        h = m.hits.get(i.chunk_ids[0])
        if h is not None:   # the item's first chunk id gives the source; label, then date, then the item text
            label = source_label(h).rsplit(" [", 1)[0]
            at = text.find(f"Per the {label}")
            end = text.find(f": {body}", at + len(f"Per the {label}")) + 2 if at >= 0 else -1
            end = end if end >= 2 else -1
            if end < 0:
                out.append(f"{ref}: source label missing")
            elif not _retrieved(h) and h.published_at and not text[at:end].endswith(
                    f", published {R._date_words(h.published_at)}: "):
                out.append(f"{ref}: date missing")
        want_ids += list(i.chunk_ids)
    want_ids += list(x.get("chunk_ids") or [])
    if set(r["chunk_ids"]) != set(want_ids):
        out.append(f"chunk ids {r['chunk_ids']} != {sorted(set(want_ids))}")
    why = " ".join(str(x.get("why") or "").split())
    if why.startswith(P.WHY_LINE.strip()):
        why = why[len(P.WHY_LINE.strip()):].strip()
    if why:
        if text.count(P.WHY_LINE) != 1 or text.split(P.WHY_LINE, 1)[1].strip() != why:
            out.append("why-line not once after WHY_LINE")
    elif P.WHY_LINE in text and P.WHY_LINE not in str(x.get("text") or ""):
        out.append("why-line without why")
    return out


def check_all(raw: dict, m) -> list[str]:
    """fidelity over every claim and adjacent item of a v6 output."""
    probs = []
    for f in R.STREAMED:
        for x in raw.get(f) or []:
            probs += [f"{x.get('part_id')}: {p}" for p in fidelity(x, R.render_one(x, m), m)]
    return probs


# --- a multi-firm matrix with scope, period, a derived cell, research and a recency aspect -------------------

def firms_matrix():
    a1 = Aspect("a1", "Advisor headcount.")
    a2 = Aspect("a2", "What changed in recruiting.", kind="recency")
    a3 = Aspect("a3", "Is the comparison valid?", kind="comparison")
    hits = [H("EDJ-10Q#60", period="2026-06-26", published="2026-08-05"),
            H("MS-10K#5", entity="MS", period="2025-12-31", published="2026-02-20",
              text="Morgan Stanley had 15,000 advisors at year end."),
            H("MS-TR#7", entity="MS", period="2026-06-30", published="2026-07-16",
              text="We expanded recruiting of experienced advisors."),
            H("RES-1#1", entity=None, text="Industry advisor counts fell 2% in 2025.")]
    cells = [
        cell("a1.EDJ", "fact", [item("EDJ-10Q#60", "Edward Jones had 20,514 advisors.", value="20,514",
                                     period="2026-06-26", scope="financial advisors")]),
        cell("a1.MS", "fact", [item("MS-10K#5", "Morgan Stanley had 15,000 advisors at year end.", value="15,000",
                                    period="2025-12-31"),
                               item("MS-10K#5", "Morgan Stanley had 99 advisors.", value="99",
                                    flags=["number_not_found"])]),
        cell("a2.EDJ", "not_found"),
        cell("a2.MS", "fact", [item("MS-TR#7", "Morgan Stanley expanded recruiting of experienced advisors.")]),
        cell("a1.research", "fact", [item("RES-1#1", "Industry advisor counts fell 2% in 2025.")]),
        cell("a3.EDJ", "not_found"), cell("a3.MS", "not_found"),
    ]
    return matrix("Advisor headcount at Edward Jones and Morgan Stanley; what changed; is it comparable?",
                  [a1, a2, a3], cells, hits)


def test_refs_are_counting_items_without_number_not_found_numbered_as_in_the_message():
    m = firms_matrix()
    refs = R.item_refs(m)
    assert "a1.MS/1" in refs and "a1.MS/2" not in refs and "a1.EDJ/1" in refs and "a1.research/1" in refs
    msg = R.reduce_message(m.question, m, None)
    assert "item a1.MS/1: Morgan Stanley had 15,000" in msg and "item a1.MS/2 (no ref): Morgan Stanley had 99" in msg
    for ref in refs:   # every ref in the enum is printed in the message
        assert f"item {ref}:" in msg or ref.endswith("/derived")


def test_v6_schema_is_strict_with_ref_enum_and_v52_bytes_are_unchanged(monkeypatch):
    m = firms_matrix()
    schema, fallback = R.reduce_schema(m)
    assert fallback == [] and _strict_problems(schema) == []
    claim = schema["properties"]["claims"]["items"]
    assert claim["required"] == ["part_id", "items", "text", "chunk_ids", "why"]
    assert claim["properties"]["items"]["items"]["enum"] == list(R.item_refs(m))
    assert "differs_because" in schema["properties"]["adjacent"]["items"]["required"]
    monkeypatch.setenv("REDUCE_PROMPT", "v5.2")
    msg52 = R.reduce_message(m.question, m, None)
    assert "/1" not in msg52 and "(no ref)" not in msg52 and "item 1:" in msg52
    assert "items" not in R.reduce_schema(m)[0]["properties"]["claims"]["items"]["properties"]


def test_ref_enum_falls_back_to_a_string_over_the_limits(monkeypatch):
    m = firms_matrix()
    monkeypatch.setattr(R, "ENUM_TOTAL_MAX", 10)
    schema, fallback = R.reduce_schema(m)
    assert fallback[:2] == ["chunk_ids", "items"]
    assert "enum" not in schema["properties"]["claims"]["items"]["properties"]["items"]["items"]


def test_render_fact_with_firm_scope_period_source_and_date():
    m = firms_matrix()
    x = {"part_id": "a1.EDJ", "items": ["a1.EDJ/1"], "text": "", "chunk_ids": [], "why": ""}
    r = R.render_one(x, m)
    assert r["text"] == ("Edward Jones: Per the EDJ 10-Q 2026-06-26, published August 5, 2026: Edward Jones had 20,514 "
                         "advisors (scope: financial advisors; period 2026-06-26).")
    assert r["chunk_ids"] == ["EDJ-10Q#60"] and r["flags"] == [] and fidelity(x, r, m) == []


def test_render_value_and_period_only_when_the_text_lacks_them():
    m = firms_matrix()
    i = m.cells["a1.MS"].items[0]
    r = R.render_item(m, m.cells["a1.MS"], i)
    assert "(period 2025-12-31)" in r and "value" not in r     # 15,000 is in the text
    i.text = "Morgan Stanley reported its advisor count."
    assert "value 15,000" in R.render_item(m, m.cells["a1.MS"], i)
    i.text, i.period = "In 2025-12-31 Morgan Stanley had 15,000 advisors.", "2025-12-31"
    assert "period" not in R.render_item(m, m.cells["a1.MS"], i)


def test_render_multi_ref_aspect_claim_prefixes_each_ref_with_its_own_cell():
    m = firms_matrix()
    x = {"part_id": "a1", "items": ["a1.EDJ/1", "a1.MS/1"], "text": "Headcounts", "chunk_ids": [], "why": ""}
    r = R.render_one(x, m)
    assert r["text"].startswith("Headcounts: Edward Jones: Per the EDJ 10-Q")
    assert "Morgan Stanley: Per the MS 10-Q 2025-12-31, published February 20, 2026: Morgan Stanley had 15,000" in r["text"]
    assert r["chunk_ids"] == ["EDJ-10Q#60", "MS-10K#5"] and fidelity(x, r, m) == []


def test_render_research_row_and_why_line_once_with_background_id():
    m = firms_matrix()
    x = {"part_id": "a2.MS", "items": ["a2.MS/1"], "text": "", "chunk_ids": ["MS-10K#5"],
         "why": "Why it might matter: it follows a year-end headcount of 15,000."}
    r = R.render_one(x, m)
    assert r["text"].count(P.WHY_LINE) == 1 and r["text"].endswith("it follows a year-end headcount of 15,000.")
    assert r["chunk_ids"] == ["MS-TR#7", "MS-10K#5"] and fidelity(x, r, m) == []
    xr = {"part_id": "a1.research", "items": ["a1.research/1"], "text": "", "chunk_ids": [], "why": ""}
    assert R.render_one(xr, m)["text"].startswith("Industry research: Per the Research 10-Q")


def test_render_derived_ref_gives_the_formula_and_both_input_ids():
    m = q24_shaped()
    assert "a1.EDJ/derived" in R.item_refs(m)
    x = {"part_id": "a1.EDJ", "items": ["a1.EDJ/derived"], "text": "", "chunk_ids": [], "why": ""}
    r = R.render_one(x, m)
    d = m.cells["a1.EDJ"].derivation
    assert d["formula_text"] in r["text"] and set(r["chunk_ids"]) == set(d["input_chunk_ids"])
    assert fidelity(x, r, m) == [] and "ref a1.EDJ/derived" in R.reduce_message(m.question, m, None)


def test_unknown_ref_is_dropped_and_flagged_and_an_uncited_claim_goes_to_the_gap_path():
    m = firms_matrix()
    raw = {"answerable": True, "behavior": "answer", "adjacent": [], "gaps": [],
           "claims": [{"part_id": "a1.EDJ", "items": ["a1.EDJ/9"], "text": "", "chunk_ids": [], "why": ""},
                      {"part_id": "a1.MS", "items": ["a1.MS/1"], "text": "", "chunk_ids": [], "why": ""}]}
    a = R.to_answer(raw, "mock", m=m)
    assert a._render["unknown_ref"] == 1 and a._render["dropped"] == 1 and len(a.claims) == 1
    q = Query(question=m.question, entities=["EDJ", "MS"])
    final, info = R.finish_answer(a, m, q, plan_of(m), list(m.hits.values()), m.question)
    assert info["render"]["unknown_ref"] == 1
    assert all(c.chunk_ids for c in final.claims)               # rule 1: no shown claim without a citation
    assert not any(c.part_id == "a1.EDJ" for c in final.claims)


@pytest.mark.parametrize("part, ref", [("a1.EDJ", "a1.MS/1"), ("a2", "a1.MS/1"), ("", "a1.MS/1")])
def test_ref_outside_the_part_is_dropped_with_ref_part_mismatch(part, ref):
    m = firms_matrix()
    x = {"part_id": part, "items": [ref], "text": "", "chunk_ids": [], "why": ""}
    log: dict = {}
    r = R.render_one(x, m, log=log)
    assert r["flags"] == ["ref_part_mismatch"] and r["chunk_ids"] == [] and "Morgan Stanley" not in r["text"]
    assert len(log["ref_part_mismatch"]) == 1


def test_number_not_found_item_has_no_ref_so_its_figure_cannot_be_rendered():
    m = firms_matrix()
    x = {"part_id": "a1.MS", "items": ["a1.MS/2"], "text": "", "chunk_ids": [], "why": ""}
    r = R.render_one(x, m)
    assert r["flags"] == ["unknown_ref"] and "99" not in r["text"]


def test_provenance_rendered_is_clean_and_model_text_figures_are_listed():
    m = firms_matrix()
    raw = {"answerable": True, "behavior": "answer", "adjacent": [], "gaps": [], "claims": [
        {"part_id": "a1.MS", "items": ["a1.MS/1"], "text": "", "chunk_ids": [], "why": ""},
        {"part_id": "a3", "items": [], "text": "Edward Jones' 20,514 and Morgan Stanley's 16,500 are not comparable.",
         "chunk_ids": ["EDJ-10Q#60", "MS-10K#5"], "why": ""}]}
    _, log = R.render_output(raw, m)
    assert log["rendered_outside"] == 0 and log["text_claims"] == 1
    assert log["model_outside"] == 1 and log["lists"]["model_outside"][0]["figure"] == "16500"
    assert log["rendered_number_not_found"] == 0 and log["model_number_not_found"] == 1


def test_fidelity_check_catches_a_wrong_cell_a_wrong_firm_and_a_dropped_scope():
    m = firms_matrix()
    x = {"part_id": "a1.EDJ", "items": ["a1.EDJ/1"], "text": "", "chunk_ids": [], "why": ""}
    good = R.render_one(x, m)
    assert fidelity(x, good, m) == []
    wrong_cell = {**good, "text": R.render_one({**x, "part_id": "a1.MS", "items": ["a1.MS/1"]}, m)["text"]}
    assert fidelity(x, wrong_cell, m)
    wrong_firm = {**good, "text": good["text"].replace("Edward Jones: ", "Morgan Stanley: ", 1)}
    assert any("firm prefix" in p for p in fidelity(x, wrong_firm, m))
    no_scope = {**good, "text": good["text"].replace("scope: financial advisors; ", "")}
    assert any("scope" in p for p in fidelity(x, no_scope, m))
    other_date = {**good, "text": good["text"].replace("August 5, 2026", "July 5, 2026")}
    assert any("date" in p for p in fidelity(x, other_date, m))


# --- the mock (v6) ---------------------------------------------------------------------------------------

@pytest.mark.parametrize("make", [firms_matrix, q24_shaped])
def test_mock_v6_renders_faithfully_with_the_same_chunk_ids_as_v52(make, monkeypatch):
    m = make()
    raw6 = R.mock_reduce_v6(m)
    assert R.is_v6(raw6) and check_all(raw6, m) == []
    a6 = R.to_answer(raw6, "mock", m=m)
    monkeypatch.setenv("REDUCE_PROMPT", "v5.2")
    a52 = R.to_answer(R.mock_reduce(m), "mock")
    assert [(c.part_id, c.chunk_ids) for c in a6.claims] == [(c.part_id, c.chunk_ids) for c in a52.claims]
    assert [(c.part_id, c.chunk_ids) for c in a6.adjacent] == [(c.part_id, c.chunk_ids) for c in a52.adjacent]
    assert a6._render["unknown_ref"] == a6._render["ref_part_mismatch"] == a6._render["uncited"] == 0


def test_v6_output_without_the_matrix_is_invalid():
    from cee.answer import llm
    m = firms_matrix()
    with pytest.raises(llm.ModelOutputError, match="needs the matrix"):
        R.to_answer(R.mock_reduce_v6(m), "mock")


def test_v52_saved_output_still_needs_no_matrix(monkeypatch):
    monkeypatch.setenv("REDUCE_PROMPT", "v5.2")
    m = firms_matrix()
    a = R.to_answer(R.mock_reduce(m), "mock")
    assert a._render is None and a.claims


# --- streamed claims and the Ask page (TL B5) -------------------------------------------------------------

from tests.test_reduce_stream import _stream_of  # noqa: E402


def _v6_raw(m, extra_claims=()):
    raw = R.mock_reduce_v6(m)
    raw["claims"] = list(raw["claims"]) + list(extra_claims)
    return raw


BAD = [{"part_id": "a1.EDJ", "items": ["a1.EDJ/9"], "text": "", "chunk_ids": ["EDJ-10Q#60"], "why": ""},
       {"part_id": "a1.EDJ", "items": ["a1.MS/1"], "text": "", "chunk_ids": ["EDJ-10Q#60"], "why": ""}]


@pytest.mark.parametrize("make", [firms_matrix, q24_shaped])
def test_streamed_v6_claims_are_rendered_shown_and_equal_their_final_text(make):
    m = make()
    raw = _v6_raw(m, BAD if make is firms_matrix else ())
    client = Client(iter(_stream_of(json.dumps(raw))))
    early = R.EarlyClaims(m, None)
    out = R.call_reduce(m.question, m, None, "deepseek", client=client, on_item=early)
    a = R.to_answer(out, "deepseek", {"stop_reason": "tool_calls"}, m)
    q = Query(question=m.question, entities=[r for r in m.rows if r not in ("research", "all")])
    final, info = R.finish_answer(a, m, q, plan_of(m), list(m.hits.values()), m.question)
    st = early.stats(final)
    assert st["shown"] > 0
    assert st["shown_not_final"] == len(info["duplicates_removed"])
    finals = {c.text for c in final.claims}
    for c in early.shown:
        assert c.text in finals or any(d["text"] == c.text for d in info["duplicates_removed"])
        assert "unknown_ref" not in c.flags and "ref_part_mismatch" not in c.flags
    shown_parts = [(c.part_id, tuple(c.chunk_ids)) for c in early.shown]
    assert ("a1.EDJ", ("EDJ-10Q#60",)) not in shown_parts or make is q24_shaped or \
        sum(p == ("a1.EDJ", ("EDJ-10Q#60",)) for p in shown_parts) == 1   # the bad twins are held
    assert early.held >= len(raw["adjacent"]) + (len(BAD) if make is firms_matrix else 0)


def test_check_item_holds_unknown_ref_mismatch_and_adjacent():
    m = firms_matrix()
    for x in BAD:
        assert R.check_item(x, m, None) is None
    early = R.EarlyClaims(m, None)
    early("adjacent", {"part_id": "a1.MS", "items": ["a1.MS/1"], "text": "", "chunk_ids": [], "why": "",
                       "differs_because": "x"})
    assert early.held == 1 and early.shown == []
    ok = R.check_item({"part_id": "a1.MS", "items": ["a1.MS/1"], "text": "", "chunk_ids": [], "why": ""}, m, None)
    assert ok is not None and ok.text.startswith("Morgan Stanley: Per the MS 10-Q")


def _mer(monkeypatch):
    from tests.test_ask_progress import HITS
    monkeypatch.setattr(pipeline, "resolve", lambda q: Query(question=q, entities=["MER"]))
    monkeypatch.setattr(pipeline, "search_subquestions", lambda q, plan, **kw: HITS)


def test_ask_claim_events_carry_rendered_claims_before_the_answer(monkeypatch):
    _mer(monkeypatch)
    seen = []
    r = pipeline.ask("Merrill profitability?", provider="mock", log=False,
                     progress=lambda s, st, t: seen.append(("stage", s, st)),
                     on_event=lambda kind, data: seen.append((kind, data)))
    claims = [e[1] for e in seen if e[0] == "claim"]
    assert claims and all("Per the " in d["claim"].text for d in claims)
    assert all([h.chunk_id for h in d["hits"]] == d["claim"].chunk_ids for d in claims)
    claim_at = next(i for i, e in enumerate(seen) if e[0] == "claim")
    assert claim_at < next(i for i, e in enumerate(seen) if e[:2] == ("stage", "check"))
    assert r.reduce["version"] == "v6" and r.reduce["render"]["refs"] >= 1
    assert r.reduce["stream_items"]["shown"] == len(claims) and r.reduce["stream_items"]["shown_not_final"] == 0
    assert {d["claim"].text for d in claims} <= {c.text for c in r.answer.claims}


def test_ask_retry_reuses_the_saved_output_with_its_render(monkeypatch):
    """ask.py's run-cache reuse (raw = saved): the saved output is the Answer to_answer made (render_output ran
    on it), so a reuse shows the same rendered text and keeps the render log; no new reduce."""
    from cee.answer import runcache as RC
    _mer(monkeypatch)
    cache = RC.RunCache("q")
    r1 = pipeline.ask("Merrill profitability?", provider="mock", log=False, cache=cache)
    r2 = pipeline.ask("Merrill profitability?", provider="mock", log=False, cache=cache)
    assert r2.run["reused"].get("reduce") == 1
    assert [c.text for c in r2.answer.claims] == [c.text for c in r1.answer.claims]
    assert all("Per the " in c.text for c in r2.answer.claims if c.chunk_ids)
    assert r2.reduce["render"] == r1.reduce["render"]


def test_eval_saves_the_raw_v6_output_and_renders_it_again_on_reuse(monkeypatch, tmp_path):
    from scripts import eval_run as er
    from tests.test_eval_run import _reduce_setup
    qd, qry, m, calls = _reduce_setup(monkeypatch, lambda mm: R.mock_reduce_v6(mm))
    r = er.RealRunner("deepseek", 1, "snap", tmp_path / "r1", cache_dir=tmp_path / "cache")
    a1, how, info = r.reduce(qd, qry, plan_of(m), list(m.hits.values()), m)
    rec = json.loads(next((tmp_path / "cache").glob("Q24-reduce-*.json")).read_text(encoding="utf-8"))
    assert how == "called" and R.is_v6(rec["raw"]) and rec["reduce_version"] == "v6"
    assert info["render"]["unknown_ref"] == 0
    again = er.RealRunner("deepseek", 0, "snap", tmp_path / "r2", cache_dir=tmp_path / "cache")
    a2, how2, info2 = again.reduce(qd, qry, plan_of(m), list(m.hits.values()), m)
    assert how2 == "cached" and again.made == 0
    assert [c["text"] for c in a2["claims"]] == [c["text"] for c in a1["claims"]] and info2["render"] == info["render"]
