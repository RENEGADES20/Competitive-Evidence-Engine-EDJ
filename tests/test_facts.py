"""Facts table (#285, ADR-022): extraction checks with a fake client, the file, the serving rule (TL conditions B1-B6)
and the run_map hook. 0 real calls (tests/conftest.py); database tests skip when Postgres is down."""
import datetime as dt
import json
from types import SimpleNamespace

import pytest

from cee import facts
from cee.answer import llm
from tests.test_llm_deepseek import FakeDeepSeek, response, tool_call

DOC = {"doc_id": "EDJ-10Q-2026Q2", "entity_id": "EDJ", "doc_type": "10-Q", "published_at": dt.date(2026, 8, 5),
       "period_end": dt.date(2026, 6, 26)}
CHUNK = {"chunk_id": "EDJ-10Q-2026Q2#60", "seq": 60, "segment": None, "section": "Item 2", "page": 30, "prefix": "",
         "text": "Financial advisors (actual): At period end 20,514 19,674 4% Net new assets ($ billions) 18 17"}


def fact(**kw):
    base = {"chunk_id": CHUNK["chunk_id"], "metric": "advisor_headcount", "firm": "EDJ", "segment": "",
            "label": "Financial advisors (actual)", "scope": "", "value": "20,514", "unit": "advisors",
            "period_type": "point", "period_end": "2026-06-26",
            "quote": "Financial advisors (actual): At period end 20,514 19,674"}
    return {**base, **kw}


# --- extraction: checks ------------------------------------------------------------------------------

def test_check_row_keeps_a_verbatim_row():
    row, why = facts.check_row(fact(), DOC, CHUNK)
    assert why is None
    assert row["entity_id"] == "EDJ" and row["segment"] is None   # from the chunk, never the model
    assert row["period"] == "2026-06-26" and row["value_num"] == 20514
    assert row["basis"] == "advisor_headcount|financial advisors (actual)|"


@pytest.mark.parametrize("change,reason", [
    ({"quote": "Financial advisors (actual): 20,514"}, "quote_not_verbatim"),
    ({"value": "20,515"}, "value_not_in_quote"),
    ({"firm": "MS"}, "firm_mismatch"),
    ({"segment": "GWIM"}, "segment_mismatch"),
    ({"period_end": "June 2026"}, "period_unparsed"),
    ({"period_end": "2026-09-30"}, "period_after_published"),
    ({"period_end": "2026-07-31"}, "period_after_doc_period"),
    ({"unit": "employees"}, "unit_not_in_chunk"),
    ({"unit": "USD millions"}, "unit_not_in_chunk"),
    ({"metric": "revenue"}, "metric_unknown"),
    ({"period_type": "ytd"}, "period_type_unknown"),
    ({"label": " "}, "label_empty"),
])
def test_check_row_drops_a_failing_row(change, reason):
    row, why = facts.check_row(fact(**change), DOC, CHUNK)
    assert row is None and why == reason


def test_check_row_chunk_must_be_in_the_call():
    assert facts.check_row(fact(), DOC, None) == (None, "chunk_not_in_call")


def test_flow_periods_and_currency_units():
    row, why = facts.check_row(fact(metric="net_new_assets", label="Net new assets", value="18",
                                    unit="USD billions", period_type="quarter",
                                    quote="Net new assets ($ billions) 18 17"),
                               DOC, {**CHUNK, "text": CHUNK["text"] + " in billions"})
    assert why is None and row["period"] == "2026Q2" and row["value_num"] == 18e9
    assert facts.period_label("year", dt.date(2025, 9, 30)) == "FY2025"


def test_check_output_counts_rejects_and_dedupes():
    raw = {"facts": [fact(), fact(), fact(value="99,999")]}
    kept, rejected = facts.check_output(raw, DOC, [CHUNK], "deepseek-v4-pro")
    assert len(kept) == 1 and kept[0]["extract_version"] == facts.extract_version()
    assert [r["reject"] for r in rejected] == ["value_not_in_quote"]


# --- extraction: the call with a fake client --------------------------------------------------------

def test_call_extract_with_a_fake_client(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    client = FakeDeepSeek(response([tool_call(facts.EXTRACT_TOOL, json.dumps({"facts": [fact()]}))]))
    meta = {}
    raw = facts.call_extract(client, DOC, [CHUNK], meta)
    assert client.calls == 1 and raw["facts"][0]["value"] == "20,514"
    req = client.kwargs
    assert req["tools"][0]["function"]["name"] == facts.EXTRACT_TOOL
    assert req["tools"][0]["function"]["strict"] is True
    assert CHUNK["chunk_id"] in req["messages"][1]["content"]
    assert meta["usage"]["output_tokens"] == 50


def test_call_extract_without_the_tool_is_invalid(monkeypatch):
    client = FakeDeepSeek(response([], finish="stop", content="none"))
    with pytest.raises(llm.ModelOutputError):
        facts.call_extract(client, DOC, [CHUNK], {})


def test_schema_is_strict():
    s = facts.extract_schema()
    item = s["properties"]["facts"]["items"]
    assert item["additionalProperties"] is False and set(item["required"]) == set(item["properties"])


def test_extract_script_saves_and_writes(tmp_path, monkeypatch):
    """The runner with a fake client: one record per document, then --write keeps only checked rows."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("extract_facts", facts.REPO_ROOT / "scripts" / "extract_facts.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    client = FakeDeepSeek(response([tool_call(facts.EXTRACT_TOOL, json.dumps({"facts": [fact(), fact(value="1")]}))]))
    monkeypatch.setattr(llm, "deepseek_client", lambda: client)
    monkeypatch.setattr(mod, "is_peak_now", lambda prices=None: False)
    docs = [{"doc": DOC, "chunks": [CHUNK]}]
    args = SimpleNamespace(out=str(tmp_path / "ev"), max_calls=1, max_usd=3.0, concurrency=1, allow_peak=False,
                           facts_file=str(tmp_path / "facts.jsonl"))
    assert mod.run(args, docs) == 0
    assert mod.run(args, docs) == 0 and client.calls == 1   # a saved record is reused, never re-called
    summary = mod.write(args, docs)
    assert summary["kept"] == 1 and summary["reasons"] == {"value_not_in_quote": 1}
    assert len(facts.read_rows(tmp_path / "facts.jsonl")) == 1


def test_extract_script_refuses_peak_and_over_cap(tmp_path, monkeypatch):
    import importlib.util
    spec = importlib.util.spec_from_file_location("extract_facts", facts.REPO_ROOT / "scripts" / "extract_facts.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    docs = [{"doc": DOC, "chunks": [CHUNK]}]
    args = SimpleNamespace(out=str(tmp_path / "ev"), max_calls=0, max_usd=3.0, concurrency=1, allow_peak=False,
                           facts_file="")
    assert mod.run(args, docs) == 2   # over --max-calls
    monkeypatch.setattr(mod, "is_peak_now", lambda prices=None: True)
    args.max_calls = 1
    assert mod.run(args, docs) == 2   # peak hours


def test_unit_ok():
    assert facts.unit_ok("advisors", "Total advisors 8,943")
    assert facts.unit_ok("USD billions", "($ in billions) 18")
    assert not facts.unit_ok("USD billions", "18 billion advisors")   # no currency mark
    assert not facts.unit_ok("employees", "Total advisors 8,943")


def test_value_in_never_matches_inside_a_longer_number():
    assert facts.value_in("20,514", "At period end 20,514 19,674")
    assert not facts.value_in("1", "At period end 20,514")
    assert not facts.value_in("20,51", "At period end 20,514")
    assert facts.value_in(">15K", ">15K Wealth Advisors")


# --- serving rule (TL conditions B1-B3) ------------------------------------------------------------------

from cee.answer import extract  # noqa: E402
from cee.answer.extract import CallResult  # noqa: E402
from cee.retrieve.fts import Query  # noqa: E402
from cee.retrieve.planner import Aspect, Plan, SubQuestion  # noqa: E402
from tests.test_extract import cell_out, hit  # noqa: E402

Q23 = "Advisor headcount over the last eight quarters across the five."
AS_OF = dt.date(2026, 11, 17)
QUARTERS = ["2024Q4", "2025Q1", "2025Q2", "2025Q3", "2025Q4", "2026Q1", "2026Q2", "2026Q3"]
QEND = {"Q1": "03-31", "Q2": "06-30", "Q3": "09-30", "Q4": "12-31"}


def sq_for(text="Advisor headcount over the last eight quarters", metric="advisor_headcount", kind="series",
           entity="RJF", proxy=False, role="named"):
    a = Aspect("a1", text, metric=metric, kind=kind, proxy=proxy)
    return SubQuestion(f"a1.{entity}", entity, a, role)


def row(period_end, value="8,943", label="Total advisors", scope="", published="2026-10-22", chunk=None,
        entity="RJF", doc_type="press"):
    cid = chunk or f"{entity}-PR-{period_end}#1"
    return {"fact_id": f"f-{cid}-{period_end}", "metric": "advisor_headcount", "label": label, "scope": scope,
            "period": period_end, "f_period_end": period_end, "period_end": period_end, "period_type": "point",
            "value": value, "value_num": float(value.replace(",", "")), "unit": "advisors", "basis": "b",
            "quote": f"{label} {value}", "extract_version": "facts-v1", "chunk_id": cid, "doc_id": cid.split("#")[0],
            "entity_id": entity, "segment": None, "doc_type": doc_type, "source_tier": 2, "published_at": published,
            "section": None, "page": None, "rank": 0.0, "text": f"{label} {value}", "date_basis": "source"}


def quarter_rows(**kw):
    return [row(f"{q[:4]}-{QEND[q[4:]]}", **kw) for q in QUARTERS]


def serve_one(sq, rows, question=Q23, newest=None, bad=None):
    q = Query(question=question, entities=[sq.entity] if sq.entity else [])
    plan = Plan(aspects=[sq.aspect], subquestions=[sq])
    plan.pools = {sq.id: {"POOL#1"}}
    return facts.serve_cell(q, plan, sq, AS_OF, lookup_fn=lambda sub, metric: rows,
                            newest_fn=lambda ids, metric: newest, recheck_fn=lambda sub, items: bad)


def test_facts_default_is_off(monkeypatch):
    monkeypatch.delenv("FACTS", raising=False)
    assert not facts.enabled()


def test_eligible_q23_shape():
    sq = sq_for()
    assert facts.eligible(sq, sq.aspect, Q23) == (True, "")


@pytest.mark.parametrize("text,question,why", [
    ("What drives net new assets", "Net new assets for each firm.", "drive"),
    ("Advisor headcount", "Why did Merrill's advisor headcount fall?", "why"),
    ("Advisor headcount guidance for next year", Q23, "guidance"),
    ("Advisor headcount growth", Q23, "growth"),
    ("How many advisors and how the count is defined", Q23, "non-figure word"),
    ("Advisor headcount", "How has advisor headcount changed since the start of the year?", "how"),
    ("Advisor headcount", "Advisor headcount per firm, and is it comparable?", "per"),
    ("Net new assets attributable to recruiting", Q23, "attribut"),
    ("Advisor headcount", "What is Merrill's advisor growth strategy?", "strateg"),
    ("The advisor headcount figure, by affiliation model", Q23, "by affiliation"),
])
def test_adversarial_asks_go_to_the_map(text, question, why):
    sq = sq_for(text=text)
    ok, reason = facts.eligible(sq, sq.aspect, question)
    assert not ok and why in reason


@pytest.mark.parametrize("kw,why", [
    ({"metric": None}, "metric tag"), ({"metric": "client_assets"}, "metric tag"), ({"kind": "comparison"}, "kind"),
    ({"proxy": True}, "proxy"), ({"entity": None}, "firm row"), ({"role": "research"}, "firm row"),
])
def test_only_registered_firm_figure_cells(kw, why):
    sq = sq_for(**kw)
    ok, reason = facts.eligible(sq, sq.aspect, Q23)
    assert not ok and why in reason


@pytest.mark.parametrize("entity,metric,ok", [
    ("SCHW", "advisor_headcount", False), ("SCHW", "net_new_assets", False), ("BAC", "net_new_assets", False),
    ("MER", "net_new_assets", False), ("MER", "advisor_headcount", True), ("EDJ", "advisor_headcount", True),
    ("RJF", "net_new_assets", True), ("MS", "advisor_headcount", True),
])
def test_registry_status_quoted_only(entity, metric, ok):
    phrases, why = facts.registered_basis(entity, metric)
    assert (phrases is not None) == ok
    if not ok:
        assert "closest_metric" in why


def test_schw_headcount_is_never_served_even_with_rows():
    sq = sq_for(entity="SCHW")
    served, dec = serve_one(sq, quarter_rows(entity="SCHW", label="Financial consultants"))
    assert served is None and "closest_metric" in dec["reason"]


def test_series_served_when_every_asked_period_is_present():
    sq = sq_for()
    served, dec = serve_one(sq, quarter_rows())
    assert served is not None and dec["served"]
    c = served.cell
    assert c.label == "fact" and c.source == "facts" and len(c.items) == 8
    assert [i.period for i in c.items] == [f"{q[:4]}-{QEND[q[4:]]}" for q in QUARTERS]
    assert all(i.scope == "" and i.definition == "" for i in c.items)   # B5
    assert all(h.origin == "facts" and h.part_id == sq.id for h in served.hits)
    assert dec["in_retrieved"] == 0   # B6: the share already in the plan's retrieved set is reported


def test_series_with_a_missing_asked_period_goes_to_the_map():
    served, dec = serve_one(sq_for(), quarter_rows()[1:])
    assert served is None and "2024Q4" in dec["reason"]


def test_part_scope_and_other_labels_are_not_the_registered_basis():
    rows = quarter_rows(scope="Independent contractors") + quarter_rows(label="Employee advisors")
    served, dec = serve_one(sq_for(), rows)
    assert served is None and "registered basis" in dec["reason"]


def test_a_newer_document_in_the_pool_sends_the_cell_to_the_map():
    served, dec = serve_one(sq_for(), quarter_rows(), newest="2026-11-01")
    assert served is None and "newer document" in dec["reason"]
    served, _ = serve_one(sq_for(), quarter_rows(), newest="2026-10-22")
    assert served is not None


def test_a_failed_recheck_sends_the_cell_to_the_map():
    served, dec = serve_one(sq_for(), quarter_rows(), bad="X#1 does not pass the sub-question's filters")
    assert served is None and dec.get("recheck_failed")


def test_fact_kind_serves_the_latest_row_only():
    sq = sq_for(text="Advisor headcount for the firm", kind="fact")
    served, _ = serve_one(sq, quarter_rows(), question="Advisor headcount for each of the five.")
    assert [i.period for i in served.cell.items] == ["2026-09-30"]


def test_one_row_per_period_newest_document_first():
    sq = sq_for(text="Advisor headcount for the firm", kind="fact")
    old = row("2026-09-30", value="8,900", published="2026-10-22", chunk="RJF-PR-A#1")
    new = row("2026-09-30", value="8,943", published="2026-11-05", chunk="RJF-10K-2026#9", doc_type="10-K")
    served, dec = serve_one(sq, [old, new], question="Advisor headcount for each of the five.")
    assert served.cell.items[0].chunk_ids == ["RJF-10K-2026#9"] and dec["conflicts"] == 1


def test_recheck_uses_the_fts_filters_and_the_chunk_text():
    item = facts.item_of(row("2026-09-30"))
    ok = SimpleNamespace(chunk_id=item.chunk_ids[0], text="Total advisors 8,943 at September 30")
    assert facts.recheck(None, [item], fetch=lambda sub, ids: [ok]) is None
    assert "filters" in facts.recheck(None, [item], fetch=lambda sub, ids: [])
    bad = SimpleNamespace(chunk_id=item.chunk_ids[0], text="Total advisors 8,900")
    assert "verbatim" in facts.recheck(None, [item], fetch=lambda sub, ids: [bad])


# --- run_map hook (TL condition B4: uncovered requests byte-identical, round 1 and re-maps) ---------------

HA1 = Aspect("a1", "Advisor headcount as reported", metric="advisor_headcount")
HA2 = Aspect("a2", "Advisor headcount programs", metric=None)
QQ = Query(question="Advisor headcount for EDJ and MS.", entities=["EDJ", "MS"])


def _run(monkeypatch, on: bool):
    monkeypatch.setenv("FACTS", "on" if on else "off")
    plan = Plan(aspects=[HA1, HA2], subquestions=[SubQuestion(f"{a.id}.{f}", f, a, "named")
                                                  for f in ("EDJ", "MS") for a in (HA1, HA2)])
    plan.pools = {"a1.EDJ": {"EDJ-10K-2025#130"}, "a2.EDJ": {"EDJ-10K-2025#130", "EDJ-10K-2025#131"}}
    hits = [hit("EDJ-10K-2025#130", part="a1.EDJ"), hit("EDJ-10K-2025#131", part="a2.EDJ"),
            hit("MS#1", entity="MS", part="a1.MS"), hit("MS#2", entity="MS", part="a2.MS")]
    fact_hit = hit("EDJ-10Q-2026Q2#60", part="a1.EDJ", text="Financial advisors (actual) 20,514")
    fact_hit.origin = "facts"

    def fake_serve(q, plan_, as_of, cell_ids, **kw):
        from cee.answer.matrix import Cell
        r = row("2026-06-26", value="20,514", label="Financial advisors (actual)", entity="EDJ",
                chunk="EDJ-10Q-2026Q2#60")
        cell = Cell("a1.EDJ", "EDJ", "a1", "named", "fact", source="facts", items=[facts.item_of(r)])
        return {"a1.EDJ": facts.Served(cell, [fact_hit])}, [{"id": "a1.EDJ", "served": True}]

    monkeypatch.setattr(facts, "serve", fake_serve)
    seen, searched = {}, []

    def call(spec, question, window, firms):
        seen[spec.id] = extract.extract_message(question, spec, window, firms)
        # the map finds the figure the facts table would serve (a1.EDJ); every other cell is empty, so it is
        # re-searched and re-mapped in both runs
        return CallResult(raw={"cells": [cell_out(c) if c == "a1.EDJ" else cell_out(c, "not_found")
                                         for c in spec.cell_ids]})

    def search_fn(sq_q, tokens=None, exclude=None, research=False, peers=False, text=None):
        searched.append((sq_q.entities[0], sq_q.terms, tuple(sorted(exclude))))
        e = sq_q.entities[0]
        return [hit(f"NEW-{e}-{sq_q.terms}#1", entity=e)]

    m = extract.run_map(QQ, plan, hits, "anthropic", call=call, search_fn=search_fn, sources=lambda e: "")
    return m, seen, searched, plan, hits


def test_uncovered_requests_are_byte_identical_with_facts_on_or_off(monkeypatch):
    off, seen_off, searched_off, _, _ = _run(monkeypatch, False)
    on, seen_on, searched_on, plan_on, hits_on = _run(monkeypatch, True)
    assert set(seen_off) - set(seen_on) == {"map.a1.EDJ"}                  # the served cell's call only
    assert any(k.startswith("remap.") for k in seen_on)                    # round 2 is compared too
    for k, msg in seen_on.items():
        assert msg == seen_off[k], k
    assert searched_on == searched_off                                      # same re-searches, same exclusions
    assert "EDJ-10Q-2026Q2#60" not in {h.chunk_id for h in hits_on}         # never in the map's hits
    assert "EDJ-10Q-2026Q2#60" not in plan_on.pools.get("a1.EDJ", set())    # nor plan.pools
    assert all("EDJ-10Q-2026Q2#60" not in ex for _, _, ex in searched_on)   # nor the re-search's exclusions
    assert "EDJ-10Q-2026Q2#60" in on.hits and "EDJ-10Q-2026Q2#60" in on.pools["a1.EDJ"]
    assert on.cells["a1.EDJ"].source == "facts" and on.counts()["facts_cells"] == 1
    assert on.facts == [{"id": "a1.EDJ", "served": True}] and off.facts == []
    assert "EDJ-10Q-2026Q2#60" in on.chunk_ids()


def test_facts_off_never_calls_serve(monkeypatch):
    monkeypatch.setenv("FACTS", "off")
    monkeypatch.setattr(facts, "serve", lambda *a, **k: (_ for _ in ()).throw(AssertionError("called")))
    plan = Plan(aspects=[HA1], subquestions=[SubQuestion("a1.EDJ", "EDJ", HA1, "named")])
    m = extract.run_map(QQ, plan, [hit("EDJ-10K-2025#130", part="a1.EDJ")], "mock", sources=lambda e: "")
    assert m.counts()["facts_cells"] == 0


# --- database: the lookup's filters (B6 tests; skipped when Postgres is down) ------------------------------

def _db():
    import psycopg
    from cee.config import settings
    try:
        return psycopg.connect(settings().database_url, connect_timeout=3)
    except Exception:
        pytest.skip("database not running")


def _test_row(chunk_id, entity, label="Total wealth advisors"):
    return {"fact_id": f"test285-{chunk_id}", "chunk_id": chunk_id, "doc_id": chunk_id.split("#")[0],
            "entity_id": entity, "segment": None, "metric": "advisor_headcount", "label": label, "scope": "",
            "period": "2023-12-31", "period_end": "2023-12-31", "period_type": "point", "value": "18,916",
            "value_num": 18916.0, "unit": "advisors", "basis": "b", "quote": "x", "extract_version": "test",
            "model": "test"}


PICK_SQL = """
SELECT k, min(chunk_id) AS chunk_id FROM (
  SELECT CASE WHEN d.entity_id = 'BAC' AND c.segment = 'GWIM' THEN 'gwim'
              WHEN d.entity_id = 'BAC' AND c.segment IS NULL THEN 'bac'
              WHEN d.entity_id = 'MS' THEN 'ms' WHEN d.entity_id = 'EDJ' THEN 'edj' END AS k, c.chunk_id
  FROM chunks c JOIN documents d USING (doc_id) WHERE d.doc_type IN ('10-K', '10-Q', 'supplement')) x
WHERE k IS NOT NULL GROUP BY k
"""


def test_lookup_merrill_gets_only_gwim_bac_rows_and_edj_only_its_own():
    conn = _db()
    with conn:
        ids = {r[0]: r[1] for r in conn.execute(PICK_SQL).fetchall()}
        if set(ids) != {"gwim", "bac", "ms", "edj"}:
            pytest.skip("corpus lacks the chunks for this test")
        rows = [_test_row(ids["gwim"], "BAC"), _test_row(ids["bac"], "BAC"),
                _test_row(ids["ms"], "EDJ", label="Financial advisors"),   # the row says EDJ, the chunk is MS's
                _test_row(ids["edj"], "EDJ", label="Financial advisors")]
        conn.execute(facts.facts_ddl())
        try:
            for r in rows:
                conn.execute(f"INSERT INTO facts ({', '.join(facts.COLUMNS)}) "
                             f"VALUES ({', '.join(['%s'] * len(facts.COLUMNS))})", [r[c] for c in facts.COLUMNS])
            conn.commit()
            mer = facts.lookup(Query(question="Advisor headcount.", entities=["MER"]), "advisor_headcount")
            edj = facts.lookup(Query(question="Advisor headcount.", entities=["EDJ"]), "advisor_headcount")
            assert {r["chunk_id"] for r in mer if r["fact_id"].startswith("test285-")} == {ids["gwim"]}
            assert {r["chunk_id"] for r in edj if r["fact_id"].startswith("test285-")} == {ids["edj"]}
        finally:
            conn.execute("DELETE FROM facts WHERE fact_id LIKE 'test285-%'")
            conn.commit()
