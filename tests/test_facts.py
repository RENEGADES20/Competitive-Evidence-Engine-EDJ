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
