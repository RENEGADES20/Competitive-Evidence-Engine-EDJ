"""#272: one map call per firm x aspect cell (TL condition 1 on plan review round 1), batches over the input
ceiling, the batch merge and the per-call callback. Fake calls and the mock; 0 real calls."""
from cee.answer import extract
from cee.answer.extract import CallResult
from cee.answer.matrix import Cell, Item
from cee.answer.llm import KEPT_ELSEWHERE as KEPT_ELSEWHERE_TEXT
from tests.test_extract import Q, cell_out, hit, plan_for


def _firm(plan, hits):
    specs, code = extract.map_specs(Q, plan, hits)
    return next(s for s in specs if s.id == "map.EDJ"), code


def _shared_setup():
    """One firm, two cells sharing a chunk: a1 lists it, a2 has it only in its search pool (KEPT_ELSEWHERE)."""
    plan = plan_for(firms=("EDJ",))
    plan.pools = {"a1.EDJ": {"EDJ-10K-2025#130"}, "a2.EDJ": {"EDJ-10K-2025#130"}}
    hits = [hit("EDJ-10K-2025#130", part="a1.EDJ")]
    return plan, hits


def test_cell_calls_keep_the_firm_calls_citation_sets():
    plan, hits = _shared_setup()
    firm, _ = _firm(plan, hits)
    cells, code = extract.fan_out([firm], Q.question)
    assert code == [] and [s.id for s in cells] == ["map.a1.EDJ", "map.a2.EDJ"]
    for s in cells:
        cid = s.cells[0].id
        assert s.allowed[cid] == firm.allowed[cid]                       # today's rule, per cell
    a2 = cells[1]
    assert a2.groups["a2.EDJ"] == [] and [h.chunk_id for h in a2.shared["a2.EDJ"]] == ["EDJ-10K-2025#130"]
    msg = extract.extract_message(Q.question, a2)
    assert KEPT_ELSEWHERE_TEXT in msg and "Also in this sub-question's search pool" in msg
    assert '<chunk id="EDJ-10K-2025#130"' in msg and "a1.EDJ" not in msg   # no sibling sub-question shown


def test_per_cell_and_per_firm_results_are_the_same():
    """TL condition 1(c): the same model answers parsed against the firm spec and the cell specs give the same
    labels and claim chunk ids."""
    plan, hits = _shared_setup()
    firm, _ = _firm(plan, hits)
    by_id = {h.chunk_id: h for h in hits}
    answers = {"a1.EDJ": cell_out("a1.EDJ"), "a2.EDJ": cell_out("a2.EDJ", "different_quantity")}
    whole = extract.parse_output({"cells": list(answers.values())}, firm, by_id)
    cells, _ = extract.fan_out([firm], Q.question)
    split = [c for s in cells for c in extract.parse_output({"cells": [answers[s.cells[0].id]]}, s, by_id)]

    def shape(cs):
        return [(c.id, c.label, c.effective_label, [i.chunk_ids for i in c.items], [i.rejected_ids for i in c.items])
                for c in cs]
    assert shape(whole) == shape(split)
    assert split[1].items[0].chunk_ids == ["EDJ-10K-2025#130"]           # cited through the pool, as before


def test_a_cell_with_nothing_citable_is_the_no_passage_code_cell():
    plan = plan_for(firms=("EDJ",))
    firm, _ = _firm(plan, [hit("EDJ-10K-2025#130", part="a1.EDJ")])
    cells, code = extract.fan_out([firm], Q.question)
    assert [s.id for s in cells] == ["map.a1.EDJ"]
    assert [(c.id, c.label, c.source, c.reason, c.flags) for c in code] == [
        ("a2.EDJ", "not_found", "code", "no passages retrieved", ["no_passages"])]
    # same reason and flags as a firm with no passage at all (map_specs)
    _, firm_code = extract.map_specs(Q, plan_for(firms=("EDJ", "MS")), [hit("EDJ#1", part="a1.EDJ")])
    ms = [c for c in firm_code if c.id == "a1.MS"][0]
    assert (ms.reason, ms.flags, ms.source) == (code[0].reason, code[0].flags, code[0].source)


def test_research_spec_stays_one_call():
    plan = plan_for(firms=("EDJ",))
    hits = [hit("EDJ#1", part="a1.EDJ"), hit("R#1", entity=None, part="research")]
    specs, _ = extract.map_specs(Q, plan, hits)
    cells, _ = extract.fan_out(specs, Q.question)
    assert [s.id for s in cells] == ["map.a1.EDJ", "map.research"]


def test_batches_split_a_cell_over_the_ceiling_in_input_order():
    plan = plan_for(firms=("EDJ",))
    hits = [hit(f"EDJ#{i}", part="a1.EDJ", text="advisors " * 200) for i in range(6)]
    firm, _ = _firm(plan, hits)
    one = extract.fan_out([firm], Q.question)[0][0]
    whole = extract.input_tokens(Q.question, one)
    limit = whole - 400
    batches = extract.split_cell(one, Q.question, None, None, limit)
    assert len(batches) >= 2 and [b.id for b in batches] == [f"map.a1.EDJ.b{n}" for n in range(1, len(batches) + 1)]
    assert [h.chunk_id for b in batches for h in b.hits] == [h.chunk_id for h in hits]
    assert all(extract.input_tokens(Q.question, b) <= limit for b in batches)
    assert all(b.allowed["a1.EDJ"] == {h.chunk_id for h in b.hits} for b in batches)
    assert all(b.cell_of == "a1.EDJ" for b in batches)
    assert extract.split_cell(one, Q.question, None, None, whole) == [one]


def _cell(label, chunk=None, flags=None):
    items = [Item("t", "q", [chunk], "", "", "", "", "")] if chunk else []
    return Cell("a1.EDJ", "EDJ", "a1", "named", label, source="model", items=items, reason=label,
                flags=list(flags or []))


def test_batch_merge_precedence():
    m = extract.merge_batches
    assert m("a1.EDJ", [_cell("not_found"), _cell("fact", "X#1")]).label == "fact"
    merged = m("a1.EDJ", [_cell("fact", "X#1"), _cell("fact", "X#2"), _cell("fact", "X#1")])
    assert [i.chunk_ids for i in merged.items] == [["X#1"], ["X#2"]]            # duplicate citation dropped
    assert m("a1.EDJ", [_cell("not_found"), _cell("different_quantity", "X#1")]).label == "different_quantity"
    assert m("a1.EDJ", [_cell("not_found"), _cell("not_disclosed")]).label == "not_disclosed"
    assert m("a1.EDJ", [_cell("not_found"), _cell("not_found")]).label == "not_found"
    failed = Cell("a1.EDJ", "EDJ", "a1", "named", "failed", source="code", reason="timeout", error="timeout")
    assert m("a1.EDJ", [failed, _cell("not_found")]).label == "failed"
    kept = m("a1.EDJ", [failed, _cell("fact", "X#1")])
    assert kept.label == "fact" and "batch_failed" in kept.flags


def test_run_map_batches_and_reports_each_call_as_it_lands(monkeypatch):
    monkeypatch.setenv("MAP_CALL_TOKENS", "1500")
    monkeypatch.setenv("MAP_PREFIX_TOKENS", "1")   # #283: the firm block over its ceiling -> per-cell layout
    plan = plan_for(firms=("EDJ",))
    hits = [hit(f"EDJ#{i}", part="a1.EDJ", text="advisors " * 300) for i in range(4)] + \
        [hit("EDJ#9", part="a2.EDJ")]
    seen = []
    m = extract.run_map(Q, plan, hits, "anthropic", call=lambda spec, *a: CallResult(raw=extract.mock_extract(spec)),
                        sources=lambda e: "", on_call=lambda spec, cells: seen.append((spec.id, [c.id for c in cells])))
    ids = [c["id"] for c in m.calls]
    assert any(i.startswith("map.a1.EDJ.b") for i in ids) and "map.a2.EDJ" in ids
    assert sorted(seen) == sorted((i, ["a1.EDJ" if i.startswith("map.a1") else "a2.EDJ"]) for i in ids)
    assert m.cells["a1.EDJ"].label == "fact" and m.cells["a2.EDJ"].label == "fact"


def test_mock_cells_are_the_same_per_cell_and_per_firm():
    """The mock reads only each cell's own passages, so a firm's mock cells do not change with the fan-out."""
    plan, hits = _shared_setup()
    firm, _ = _firm(plan, hits)
    by_id = {h.chunk_id: h for h in hits}
    whole = extract.parse_output(extract.mock_extract(firm), firm, by_id, "mock")
    cells, _ = extract.fan_out([firm], Q.question)
    split = [c for s in cells for c in extract.parse_output(extract.mock_extract(s), s, by_id, "mock")]
    assert [(c.id, c.label, [i.chunk_ids for i in c.items]) for c in whole] == \
        [(c.id, c.label, [i.chunk_ids for i in c.items]) for c in split]
