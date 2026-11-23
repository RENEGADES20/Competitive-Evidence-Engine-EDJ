"""#283: the map's shared prefix per firm (one byte-identical firm block, the cell named last), one tool schema,
strict id checks (TL condition B1) and the leader-first gate (TL condition B2). Fake calls only; 0 real calls."""
import json
import threading
import time
from types import SimpleNamespace

import pytest

from cee.answer import cancel, extract, llm
from cee.answer.extract import CallResult
from cee.retrieve.planner import Aspect, Plan, SubQuestion
from tests.test_extract import Q, cell_out, hit

A = [Aspect(f"a{n}", f"Aspect number {n} of the firm.") for n in (1, 2, 3, 4)]


def plan3(firms=("EDJ", "MS"), aspects=A[:3]):
    return Plan(aspects=list(aspects), subquestions=[SubQuestion(f"{a.id}.{f}", f, a, "named")
                                                     for f in firms for a in aspects])


def hits3(firms=("EDJ", "MS"), aspects=A[:3]):
    return [hit(f"{f}-10K-2025#{n}", entity=f, part=f"{a.id}.{f}") for f in firms for n, a in enumerate(aspects)]


def cell_specs(plan=None, hits=None, prefix_limit=10**9):
    plan, hits = plan or plan3(), hits or hits3()
    firm_specs, _ = extract.map_specs(Q, plan, hits)
    specs, code = extract.fan_out(firm_specs, Q.question, None, None, 60000, prefix_limit)
    return specs, code, firm_specs


@pytest.fixture
def ds(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("MAP_PREFIX", "firm")
    monkeypatch.setenv("MAP_PREFIX_WAIT_S", "0")
    monkeypatch.setenv("MAP_PREFIX_GATE", "done")


# --- layout (acceptance: prefix test) -------------------------------------------------------------

def test_cells_of_one_firm_share_the_request_bytes_up_to_the_cell_part(ds):
    specs, _, firm_specs = cell_specs()
    edj = [s for s in specs if s.entity == "EDJ"]
    assert len(edj) == 3 and all(s.prefix is firm_specs[0] for s in edj)
    reqs = [extract.deepseek_extract_request(Q.question, s) for s in edj]
    assert len({json.dumps(r["tools"]) for r in reqs}) == 1                       # identical tool schema
    assert len({r["messages"][0]["content"] for r in reqs}) == 1                   # identical system prompt
    users = [r["messages"][1]["content"] for r in reqs]
    prefix = extract.prefix_message(Q.question, firm_specs[0])
    for s, u in zip(edj, users):
        assert u.startswith(prefix) and u[len(prefix):].startswith("\n\n" + extract.SUFFIX_MARK + s.cells[0].id)
        assert extract.SUFFIX_MARK not in prefix
    assert len(set(users)) == 3
    # the same prefix in a new spec build (byte-stable)
    again = [s for s in cell_specs()[0] if s.entity == "EDJ"]
    assert [extract.extract_message(Q.question, s) for s in again] == users


def test_one_tool_schema_for_every_map_call_of_a_question(ds):
    specs, _, _ = cell_specs()
    tools = {json.dumps(extract.deepseek_extract_request(Q.question, s)["tools"]) for s in specs}
    assert len(tools) == 1
    assert "enum" not in json.dumps(extract.extraction_schema(specs[0], strict=True)["properties"]["cells"]
                                    ["items"]["properties"]["subquestion_id"])


def test_prefix_lists_every_sub_question_of_the_firm_incl_cells_with_nothing_citable(ds):
    plan = plan3(firms=("EDJ",))
    hits = [hit("EDJ-10K-2025#0", part="a1.EDJ"), hit("EDJ-10K-2025#1", part="a2.EDJ")]   # a3 has nothing
    specs, code, firm_specs = cell_specs(plan, hits)
    assert [c.id for c in code] == ["a3.EDJ"] and len(specs) == 2
    prefix = extract.prefix_message(Q.question, firm_specs[0])
    assert all(f"- a{n}.EDJ [" in prefix for n in (1, 2, 3))
    assert all(extract.extract_message(Q.question, s).startswith(prefix) for s in specs)


def test_pool_passages_listed_for_a_sibling_are_named_in_the_cell_part(ds):
    plan = plan3(firms=("EDJ",), aspects=A[:2])
    plan.pools = {"a2.EDJ": {"EDJ-10K-2025#0"}}
    hits = [hit("EDJ-10K-2025#0", part="a1.EDJ"), hit("EDJ-10K-2025#1", part="a2.EDJ")]
    specs, _, _ = cell_specs(plan, hits)
    a2 = [s for s in specs if s.cells[0].id == "a2.EDJ"][0]
    tail = extract.cell_suffix(a2)
    assert "EDJ-10K-2025#0" in tail and a2.allowed["a2.EDJ"] == {"EDJ-10K-2025#0", "EDJ-10K-2025#1"}


def test_a_firm_block_over_the_ceiling_keeps_the_per_cell_layout(ds):
    specs, _, _ = cell_specs(prefix_limit=1)
    assert all(s.prefix is None for s in specs)
    assert all(extract.prefix_text(Q.question, s) is None for s in specs)
    assert "Also in this" not in extract.extract_message(Q.question, specs[0])


def test_mock_output_is_the_same_in_both_layouts(ds):
    shared, _, _ = cell_specs()
    per_cell, _, _ = cell_specs(prefix_limit=1)
    assert [extract.mock_extract(s, 0) for s in shared] == [extract.mock_extract(s, 0) for s in per_cell]


def test_map_request_version_changes_only_in_firm_mode_and_the_plan_version_never(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    for v in ("MAP_PREFIX", "MAP_PREFIX_TOKENS", "DEEPSEEK_EFFORT_MAP", "DEEPSEEK_STREAM"):
        monkeypatch.delenv(v, raising=False)
    assert llm.request_version("deepseek", "map") == "ds-strict-2-map-low-c128000-s1"   # off: the #272 string
    assert extract.extract_version() == extract.EXTRACT_VERSION == "extract-v1.2"
    monkeypatch.setenv("MAP_PREFIX", "firm")
    assert llm.request_version("deepseek", "map").endswith("-pf150000")
    assert llm.request_version("deepseek", "plan") == "ds-strict-2-plan-off-c8000-s1"
    assert not llm.request_version("deepseek", "reduce").endswith("-pf150000")
    monkeypatch.setenv("MAP_PREFIX_TOKENS", "90000")
    assert llm.request_version("deepseek", "map").endswith("-pf90000")
    assert extract.extract_version() == "extract-v1.3"


# --- default off: byte-identical to main (TL ruling after review, PR #286) --------------------------------

# sha256 of the map requests (deepseek, anthropic, openai) and map cache keys (eval, Ask run cache) of a fixed
# two-firm question with a research call, computed on clean main 0b359d3 (docs/results/w13-prefix-cache/golden.py)
MAIN_SHA = "8fb7c4f8da82166f4446847a221da1ecdf4706a93081b0649d0037833b9fd130"


def test_off_is_byte_identical_to_main(monkeypatch):
    import hashlib
    from cee.answer import runcache
    from scripts import eval_run as er
    monkeypatch.setenv("LLM_PROVIDER", "deepseek")
    for v in ("MAP_PREFIX", "MAP_PREFIX_TOKENS", "DEEPSEEK_EFFORT_MAP", "DEEPSEEK_STREAM"):
        monkeypatch.delenv(v, raising=False)
    plan = plan3()
    plan.pools = {"a2.EDJ": {"EDJ-10K-2025#0"}}
    hits = [hit(f"{f}-10K-2025#{n}", entity=f, part=f"{a.id}.{f}") for f in ("EDJ", "MS") for n, a in enumerate(A[:3])]
    hits.append(hit("R-1#1", entity=None, part="research"))
    fs, _ = extract.map_specs(Q, plan, hits)
    specs, _ = extract.fan_out(fs, Q.question, None, None, 60000)
    reqs = [[extract.deepseek_extract_request(Q.question, s), extract.anthropic_extract_request(Q.question, s),
             extract.openai_extract_request(Q.question, s)] for s in specs]
    keys = [[er.map_cache_key({"id": "Q1", "text": Q.question}, "snap", "deepseek", "m", 1,
                              llm.request_version("deepseek", "map"), s),
             runcache.map_key(Q.question, s, "deepseek")] for s in specs]
    blob = json.dumps([reqs, keys], sort_keys=True)
    assert hashlib.sha256(blob.encode()).hexdigest() == MAIN_SHA
    sid = extract.extraction_schema(specs[0], strict=True)["properties"]["cells"]["items"]["properties"]["subquestion_id"]
    assert sid["enum"] == ["a1.EDJ"]                                           # the per-cell enum schema


def test_run_map_off_never_uses_the_shared_prefix(monkeypatch):
    for v in ("MAP_PREFIX", "MAP_PREFIX_TOKENS"):
        monkeypatch.delenv(v, raising=False)
    seen = []

    def call(spec, *a):
        seen.append(spec.prefix)
        return CallResult(raw=extract.mock_extract(spec, 0))
    m = extract.run_map(Q, plan3(), hits3(), "deepseek", call=call, sources=lambda e: "")
    assert seen and all(p is None for p in seen) and {c["prefix_role"] for c in m.calls} == {"cell"}
    assert m.version == "extract-v1.2"


# --- strict ids (TL condition B1) -----------------------------------------------------------------

def _one(spec_id="a1.EDJ"):
    specs, _, _ = cell_specs()
    return next(s for s in specs if s.cells[0].id == spec_id)


def test_a_sibling_cell_in_the_output_is_dropped_and_flagged_foreign_cell():
    s = _one()
    by_id = {h.chunk_id: h for h in hits3()}
    cells = extract.parse_output({"cells": [cell_out("a2.EDJ", chunk_ids=("EDJ-10K-2025#1",))]}, s, by_id)
    assert [(c.id, c.label) for c in cells] == [("a1.EDJ", "not_found")]
    assert "missing_cell" in cells[0].flags and "foreign_cell" in cells[0].flags
    assert "unknown_cell" not in cells[0].flags


def test_an_id_of_no_sub_question_is_dropped_and_flagged_unknown_cell():
    s = _one()
    by_id = {h.chunk_id: h for h in hits3()}
    out = {"cells": [cell_out("a1.EDJ", chunk_ids=("EDJ-10K-2025#0",)), cell_out("zz.EDJ")]}
    cells = extract.parse_output(out, s, by_id)
    assert cells[0].label == "fact" and cells[0].flags == ["unknown_cell"]


def test_a_derivation_over_a_sibling_cell_is_dropped_and_flagged_unknown_ref():
    s = _one()
    by_id = {h.chunk_id: h for h in hits3()}
    c = cell_out("a1.EDJ", "not_disclosed")
    c["derivation"] = {"operation": "ratio", "inputs": [{"subquestion_id": "a2.EDJ", "item": 0},
                                                        {"subquestion_id": "a1.EDJ", "item": 0}]}
    got = extract.parse_output({"cells": [c]}, s, by_id)[0]
    assert got.derivation is None and "unknown_ref" in got.flags
    c["derivation"]["inputs"] = [{"subquestion_id": "a1.EDJ", "item": 0}, {"subquestion_id": "a1.EDJ", "item": 1}]
    kept = extract.parse_output({"cells": [c]}, s, by_id)[0]
    assert kept.derivation["operation"] == "ratio" and kept.flags == []


def test_a_chunk_outside_the_cells_allowed_set_is_still_rejected():
    s = _one()
    by_id = {h.chunk_id: h for h in hits3()}
    got = extract.parse_output({"cells": [cell_out("a1.EDJ", chunk_ids=("EDJ-10K-2025#1",))]}, s, by_id)[0]
    assert got.items[0].chunk_ids == [] and got.items[0].rejected_ids == ["EDJ-10K-2025#1"]
    assert "unmatched_citation" in got.items[0].flags


# --- leader-first gate (TL condition B2) ------------------------------------------------------------

def run(specs, call, concurrency=24, allow=None, provider="deepseek"):
    return extract.run_round(specs, call, Q.question, None, None, concurrency, allow, provider)


def recorder(delay=0.0, cached=(), on=None):
    log, lock = [], threading.Lock()

    def call(spec, *a):
        with lock:
            log.append(("start", spec.id, time.monotonic()))
        if on:
            on(spec)
        time.sleep(delay)
        with lock:
            log.append(("end", spec.id, time.monotonic()))
        return CallResult(raw=extract.mock_extract(spec, 0), cached=spec.id in cached)
    return call, log


def _t(log, kind, sid):
    return next(t for k, i, t in log if k == kind and i == sid)


def test_roles_and_the_leader_runs_before_its_followers(ds):
    specs, _, _ = cell_specs()
    call, log = recorder(0.05)
    res = run(specs, call)
    roles = {s.id: r.prefix_role for s, r in zip(specs, res)}
    assert roles == {"map.a1.EDJ": "leader", "map.a2.EDJ": "follower", "map.a3.EDJ": "follower",
                     "map.a1.MS": "leader", "map.a2.MS": "follower", "map.a3.MS": "follower"}
    assert len({r.prefix_group for r in res}) == 2
    for f in ("EDJ", "MS"):
        for n in (2, 3):
            assert _t(log, "start", f"map.a{n}.{f}") >= _t(log, "end", f"map.a1.{f}")
    assert all(r.gate_wait_s is not None and r.gate_wait_s >= 0 for r in res)


def test_a_group_of_one_is_solo_and_cells_without_prefix_never_wait(ds):
    specs, _, _ = cell_specs(plan3(firms=("EDJ",), aspects=A[:1]), hits3(("EDJ",), A[:1]))
    res = run(specs, recorder()[0])
    assert [r.prefix_role for r in res] == ["solo"]
    per_cell, _, _ = cell_specs(prefix_limit=1)
    assert {r.prefix_role for r in run(per_cell, recorder()[0])} == {"cell"}


def test_gate_off_or_another_provider_keeps_spec_order_and_no_wait(ds, monkeypatch):
    specs, _, _ = cell_specs()
    for provider, gate in (("deepseek", "off"), ("anthropic", "done")):
        monkeypatch.setenv("MAP_PREFIX_GATE", gate)
        call, log = recorder()
        res = run(specs, call, concurrency=1, provider=provider)
        assert [i for k, i, _ in log if k == "start"] == [s.id for s in specs]
        assert all(r.gate_wait_s is None for r in res)


def test_a_cached_leader_opens_the_gate_at_once_and_skips_the_extra_wait(ds, monkeypatch):
    monkeypatch.setenv("MAP_PREFIX_WAIT_S", "3")
    specs, _, _ = cell_specs()
    t0 = time.monotonic()
    res = run(specs, recorder(cached={"map.a1.EDJ", "map.a1.MS"})[0])
    assert time.monotonic() - t0 < 2 and all(r.gate_wait_s < 2 for r in res)


def test_followers_wait_the_extra_seconds_after_a_new_leader(ds, monkeypatch):
    monkeypatch.setenv("MAP_PREFIX_WAIT_S", "0.3")
    specs, _, _ = cell_specs()
    res = run(specs, recorder()[0])
    assert all(r.gate_wait_s >= 0.3 for r in res if r.prefix_role == "follower")
    assert all(r.gate_wait_s == 0 for r in res if r.prefix_role == "leader")


def test_a_skipped_leader_is_never_waited_for(ds):
    specs, _, _ = cell_specs()
    refused = {"map.a1.EDJ"}
    call, log = recorder()
    res = run(specs, call, allow=lambda s: s.id not in refused)
    assert res[0].skipped and res[0].prefix_role is None
    assert {s.id: r.prefix_role for s, r in zip(specs, res)}["map.a2.EDJ"] == "leader"
    assert len([1 for k, _, _ in log if k == "start"]) == 5


@pytest.mark.parametrize("how", ["invalid", "failed", "raises"])
def test_the_gate_opens_however_the_leader_ends(ds, how):
    specs, _, _ = cell_specs()

    def call(spec, *a):
        if spec.id == "map.a1.EDJ":
            if how == "raises":
                raise RuntimeError("boom")   # not a CallResult: the round records the error
            return CallResult(invalid=how == "invalid", failed_call=how == "failed", error="x")
        return CallResult(raw=extract.mock_extract(spec, 0))

    if how == "raises":
        with pytest.raises(RuntimeError):
            run(specs, call)
    else:
        res = run(specs, call)
        assert all(r.raw is not None for r in res[1:])


def test_a_leader_provider_stop_means_no_follower_call(ds):
    specs, _, _ = cell_specs(plan3(firms=("EDJ",)), hits3(("EDJ",)))
    started = []

    def call(spec, *a):
        started.append(spec.id)
        if spec.id == "map.a1.EDJ":
            time.sleep(0.1)
            raise llm.ProviderStop("DeepSeek: rate limit reached (429)")
        return CallResult(raw=extract.mock_extract(spec, 0))

    with pytest.raises(llm.ProviderStop):
        run(specs, call)
    assert started == ["map.a1.EDJ"]


def test_stop_during_a_followers_wait_cuts_it_without_a_call(ds):
    specs, _, _ = cell_specs(plan3(firms=("EDJ",)), hits3(("EDJ",)))
    token = cancel.CancelToken()
    started = []

    def call(spec, *a):
        started.append(spec.id)
        token.set()
        time.sleep(1.0)
        return CallResult(raw=extract.mock_extract(spec, 0))

    with cancel.use(token), pytest.raises(cancel.Cancelled) as e:
        run(specs, call)
    assert started == ["map.a1.EDJ"] and set(e.value.not_started) == {"map.a2.EDJ", "map.a3.EDJ"}


def test_first_chunk_opens_the_gate_before_the_leader_ends(ds, monkeypatch):
    monkeypatch.setenv("MAP_PREFIX_GATE", "first_chunk")
    specs, _, _ = cell_specs(plan3(firms=("EDJ",)), hits3(("EDJ",)))

    def on(spec):
        hook = llm.FIRST_CHUNK.get()
        if spec.id == "map.a1.EDJ":
            assert hook is not None
            hook()
        else:
            assert hook is None
    call, log = recorder(0.3, on=on)
    run(specs, call)
    assert _t(log, "start", "map.a2.EDJ") < _t(log, "end", "map.a1.EDJ")


def test_first_chunk_with_a_non_streamed_leader_opens_when_it_ends(ds, monkeypatch):
    monkeypatch.setenv("MAP_PREFIX_GATE", "first_chunk")
    specs, _, _ = cell_specs(plan3(firms=("EDJ",)), hits3(("EDJ",)))
    call, log = recorder(0.2)   # never calls the hook (no stream)
    run(specs, call)
    assert _t(log, "start", "map.a2.EDJ") >= _t(log, "end", "map.a1.EDJ")


def test_the_stream_assembler_fires_the_first_chunk_hook_once():
    fired = []
    token = llm.FIRST_CHUNK.set(lambda: fired.append(1))
    try:
        asm = llm.StreamAssembler()
        delta = SimpleNamespace(content=None, reasoning_content="r", tool_calls=None)
        for _ in range(3):
            asm.feed(SimpleNamespace(usage=None, choices=[SimpleNamespace(delta=delta, finish_reason=None)]))
    finally:
        llm.FIRST_CHUNK.reset(token)
    assert fired == [1]


@pytest.mark.parametrize("concurrency", [1, 2])
def test_no_deadlock_with_fewer_workers_than_groups(ds, concurrency):
    firms = ("EDJ", "MS", "SCHW", "RJF")
    specs, _, _ = cell_specs(plan3(firms=firms), hits3(firms))
    done = threading.Event()
    out = {}

    def go():
        out["res"] = run(specs, recorder(0.01)[0], concurrency=concurrency)
        done.set()

    threading.Thread(target=go, daemon=True).start()
    assert done.wait(10) and all(r.raw is not None for r in out["res"])


def test_prefix_info_reaches_the_call_function(ds):
    specs, _, _ = cell_specs()
    seen = {}

    def call(spec, *a):
        seen[spec.id] = dict(extract.PREFIX_INFO.get())
        return CallResult(raw=extract.mock_extract(spec, 0))

    run(specs, call)
    info = seen["map.a2.EDJ"]
    assert info["prefix_role"] == "follower" and 0 < info["prefix_chars"] < info["request_chars"]


def test_the_map_cache_key_carries_the_firm_block(ds):
    from scripts import eval_run as er
    shared, _, _ = cell_specs()
    per_cell, _, _ = cell_specs(prefix_limit=1)
    q = {"id": "Q1", "text": Q.question}

    def key(s):
        return er.map_cache_key(q, "snap", "deepseek", "m", 1, "v", s)
    assert key(shared[0]) != key(per_cell[0])
    other = cell_specs(hits=hits3() + [hit("EDJ-10K-2025#9", part="a2.EDJ")])[0][0]   # same cell, new sibling chunk
    assert other.hits == shared[0].hits and key(other) != key(shared[0])
