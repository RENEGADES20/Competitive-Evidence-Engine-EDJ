"""#277: Stop (cancel token) and Retry (run cache) on the Ask page. Fake clients and the mock: 0 real calls."""
import threading
import time
from dataclasses import replace

import pytest

from cee import ask as pipeline
from cee.answer import cancel, extract
from cee.answer import llm
from cee.answer import reduce as R
from cee.answer import runcache as RC
from cee.answer.extract import CallResult, mock_extract
from cee.retrieve.fts import Hit, Query
from tests.test_deepseek_stages import _req, chunk, tc
from tests.test_stream_idle import BlockingStream, Client


def hit(cid: str, entity: str, part: str) -> Hit:
    return Hit(chunk_id=cid, doc_id=cid.split("#")[0], entity_id=entity, segment=None, doc_type="10-K",
               source_tier=2, published_at="2026-02-25", period_end="2025-12-31", section="Item 7", page=None,
               rank=1.0, text=f"{entity} recruited 120 experienced advisors in 2025.", part_id=part)


HITS = [hit("MS-10K-2025#10", "MS", "a1.MS"), hit("RJF-10K-2025#20", "RJF", "a1.RJF")]


@pytest.fixture
def two_firms(monkeypatch):
    """A two-firm question on the mock: rules plan a1.MS, a1.RJF; two map calls; the mock reduce."""
    monkeypatch.setenv("MOCK_DELAY_S", "0")
    monkeypatch.setattr(pipeline, "resolve", lambda q: Query(question=q, entities=["MS", "RJF"]))
    monkeypatch.setattr(pipeline, "search_subquestions", lambda q, plan, **kw: list(HITS))
    calls: list[str] = []
    return calls


def fake_calls(monkeypatch, calls, behave):
    """extract.provider_call replaced: `behave(spec)` returns a CallResult or raises; every call is counted."""
    def provider_call(provider):
        def call(spec, question, window, firms):
            calls.append(spec.id)
            return behave(spec)
        return call
    monkeypatch.setattr(extract, "provider_call", provider_call)


def ok(spec):
    return CallResult(raw=mock_extract(spec, 0))


# --- the cancel token -----------------------------------------------------------------------------

def test_check_and_sleep_follow_the_token():
    cancel.check()   # no token: a no-op
    t = cancel.CancelToken()
    with cancel.use(t):
        cancel.check()
        t.set("stop", "extract")
        with pytest.raises(cancel.Cancelled):
            cancel.check()
        t0 = time.monotonic()
        with pytest.raises(cancel.Cancelled):
            cancel.sleep(30)
        assert time.monotonic() - t0 < 1
    assert t.reason == "stop" and t.stage == "extract" and t.set_at is not None
    assert issubclass(cancel.Cancelled, BaseException) and not issubclass(cancel.Cancelled, Exception)


def test_a_stop_cuts_a_running_sleep_from_another_thread():
    t = cancel.CancelToken()
    threading.Timer(0.2, lambda: t.set("stop")).start()
    t0 = time.monotonic()
    with cancel.use(t), pytest.raises(cancel.Cancelled):
        cancel.sleep(30)
    assert time.monotonic() - t0 < 2


def test_stop_closes_an_open_stream_mid_way(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_IDLE_S", "60")   # the stall timer never fires here; only Stop ends it
    stream = BlockingStream([chunk(calls=[tc(0, name="submit_answer", args="{\"claims\": [")]),
                             chunk(calls=[tc(0, args="{\"text\": \"a\"")])])
    client = Client(stream)
    t = cancel.CancelToken()
    threading.Timer(0.3, lambda: t.set("stop")).start()
    t0 = time.monotonic()
    with cancel.use(t), pytest.raises(cancel.Cancelled) as e:
        llm.deepseek_create(client, _req("reduce"))
    assert time.monotonic() - t0 < 2 and stream.closed.is_set() and client.calls == 1
    assert "claims" in e.value.partial["tool_calls"][0]["function"]["arguments"]   # the partial output is kept


def test_no_request_is_sent_after_stop():
    client = Client(BlockingStream([]))
    t = cancel.CancelToken()
    t.set("stop")
    with cancel.use(t), pytest.raises(cancel.Cancelled):
        llm.deepseek_create(client, _req("reduce"))
    assert client.calls == 0


def test_no_new_map_call_starts_after_stop_and_queued_calls_are_cancelled():
    """Concurrency 1, three calls: the token is set when the first lands; the other two never start and the
    round returns at once (no wait for queued calls)."""
    specs = [extract.MapSpec(f"map.a{i}.MS", 1, "MS", False, [], {}, {}) for i in range(3)]
    made = []
    t = cancel.CancelToken()

    def call(spec, *a):
        made.append(spec.id)
        return CallResult(raw={"cells": []})

    def landed(i, r):
        t.set("stop")
    with cancel.use(t), pytest.raises(cancel.Cancelled) as e:
        extract.run_round(specs, call, "q", None, [], 1, on_result=landed)
    assert made == ["map.a0.MS"]
    assert sorted(e.value.not_started) == ["map.a1.MS", "map.a2.MS"]
    assert [r.cancelled for r in e.value.results] == [False, True, True]
    assert all(r.error == extract.STOPPED_ERROR for r in e.value.results[1:])   # not the ProviderStop text


def test_each_map_call_gets_its_own_context_copy():
    """Concurrency 2: every worker sees the caller's token (no "already entered" error from a shared context)."""
    specs = [extract.MapSpec(f"map.a{i}.MS", 1, "MS", False, [], {}, {}) for i in range(6)]
    seen = []
    t = cancel.CancelToken()

    def call(spec, *a):
        time.sleep(0.05)
        seen.append(cancel.current())
        return CallResult(raw={"cells": []})
    with cancel.use(t):
        out = extract.run_round(specs, call, "q", None, [], 2)
    assert len(out) == 6 and all(not r.error for r in out) and seen == [t] * 6


def test_a_provider_stop_keeps_its_own_cancelled_text():
    specs = [extract.MapSpec(f"map.a{i}.MS", 1, "MS", False, [], {}, {}) for i in range(3)]

    def call(spec, *a):
        raise llm.ProviderStop("DeepSeek: out of balance")
    with pytest.raises(llm.ProviderStop):
        extract.run_round(specs, call, "q", None, [], 1)


def test_the_planner_never_turns_a_stop_into_the_rule_plan(monkeypatch):
    from cee.retrieve import planner
    from tests.test_planner import q7

    def stopped(*a, **k):
        raise cancel.Cancelled("stopped by the user")
    monkeypatch.setattr(planner, "call_planner", stopped)
    with pytest.raises(cancel.Cancelled):
        planner.plan_question(q7(), "anthropic")


# --- the run cache ------------------------------------------------------------------------------

@pytest.mark.parametrize("status", RC.FAILED_STATUSES)
def test_a_failed_cut_or_cancelled_record_is_never_reused(status):
    c = RC.RunCache("q")
    c.new_attempt()
    c.record("map", "map.a1.MS", "k", status, output={"raw": "x"})
    assert c.get("k") is None
    c.record("map", "map.a1.MS", "k", RC.OK, output={"raw": "y"})
    assert c.get("k") == {"raw": "y"}


def test_ok_output_is_a_copy():
    c = RC.RunCache("q")
    c.record("map", "m", "k", RC.OK, output={"raw": {"cells": []}})
    c.get("k")["raw"]["cells"].append(1)
    assert c.get("k") == {"raw": {"cells": []}}


def test_retry_after_stop_reuses_finished_calls_and_runs_only_the_missing_ones(two_firms, monkeypatch):
    calls = two_firms
    attempt = {"n": 1}
    started = threading.Event()

    def behave(spec):
        if attempt["n"] == 1 and spec.id == "map.a1.RJF":
            started.set()
            cancel.sleep(30)   # a slow call, cut by Stop
        if attempt["n"] == 1:
            started.wait(5)    # MS lands once RJF is running
        return ok(spec)
    fake_calls(monkeypatch, calls, behave)
    cache, events = RC.RunCache("q"), []
    t = cancel.CancelToken()

    def on_event(kind, data):
        if kind == "evidence":
            t.set("stop")   # Stop as soon as the first evidence card is on the page
    t0 = time.monotonic()
    with pytest.raises(cancel.Cancelled):
        pipeline.ask("q", provider="mock", log=False, on_event=on_event, token=t, cache=cache,
                     progress=lambda *e: events.append(e))
    assert time.monotonic() - t0 < 5
    assert sorted(calls) == ["map.a1.MS", "map.a1.RJF"]
    assert not any(state == "failed" for _, state, _ in events)          # a stop is not a failure
    assert events[-1][:2] == ("extract", "stopped")
    first = cache.summary(1)
    assert first["status"] == {"ok": 1, "cancelled": 1} and first["made"] == {"map": 2}
    attempt["n"] = 2
    r = pipeline.ask("q", provider="mock", log=False, token=cancel.CancelToken(), cache=cache)
    assert sorted(calls) == ["map.a1.MS", "map.a1.RJF", "map.a1.RJF"]   # MS reused, RJF made again
    assert r.answer.behavior == "answer" and r.answer.claims
    assert r.run["attempt"] == 2 and r.run["status"] == "done"
    assert r.run["reused"] == {"map": 1} and r.run["made"] == {"map": 1, "reduce": 1}
    assert pipeline.log_filters(r)["run"]["reused"] == {"map": 1}
    assert pipeline.log_filters(r)["llm_calls"]["map"] == 0   # mock: no paid call either way


def test_a_valid_result_that_lands_after_stop_is_kept_and_reused(two_firms, monkeypatch):
    calls = two_firms
    t = cancel.CancelToken()
    started = threading.Event()

    def behave(spec):
        if spec.id == "map.a1.RJF":
            started.set()
            t.wait(5)   # an uncut call: it ends after the click with a valid output
        else:
            started.wait(5)
        return ok(spec)
    fake_calls(monkeypatch, calls, behave)
    cache = RC.RunCache("q")
    with pytest.raises(cancel.Cancelled):
        pipeline.ask("q", provider="mock", log=False, token=t, cache=cache,
                     on_event=lambda k, d: t.set("stop") if k == "evidence" else None)
    assert cache.summary(1)["status"] == {"ok": 2}
    r = pipeline.ask("q", provider="mock", log=False, token=cancel.CancelToken(), cache=cache)
    assert len(calls) == 2 and r.run["reused"] == {"map": 2}   # never paid twice


def test_retry_after_an_injected_reduce_failure(two_firms, monkeypatch, tmp_path):
    calls = two_firms
    fake_calls(monkeypatch, calls, ok)
    flag = tmp_path / "fail.txt"
    flag.write_text("reduce", encoding="utf-8")
    monkeypatch.setenv("MOCK_FAIL_FILE", str(flag))
    cache = RC.RunCache("q")
    with pytest.raises(RuntimeError, match="injected reduce failure"):
        pipeline.ask("q", provider="mock", log=False, token=cancel.CancelToken(), cache=cache)
    assert cache.summary(1)["status"] == {"ok": 2, "failed": 1}
    flag.unlink()
    r = pipeline.ask("q", provider="mock", log=False, token=cancel.CancelToken(), cache=cache)
    assert len(calls) == 2 and r.run["reused"] == {"map": 2} and r.run["made"] == {"reduce": 1}
    assert r.answer.claims


def test_an_injected_map_failure_is_retried_once(two_firms, monkeypatch, tmp_path):
    monkeypatch.setenv("MOCK_DELAY_S", "0")
    flag = tmp_path / "fail.txt"
    flag.write_text("map", encoding="utf-8")
    monkeypatch.setenv("MOCK_FAIL_FILE", str(flag))
    cache = RC.RunCache("q")
    r = pipeline.ask("q", provider="mock", log=False, token=cancel.CancelToken(), cache=cache)
    assert r.answer.behavior is None or r.answer.incomplete_note   # both cells failed: incomplete, not refuse
    from cee.app.views.ask_page import has_failed_calls
    assert has_failed_calls(r)
    assert cache.summary(1)["status"]["failed"] == 2
    flag.unlink()
    r2 = pipeline.ask("q", provider="mock", log=False, token=cancel.CancelToken(), cache=cache)
    assert r2.run["made"]["map"] == 2 and "map" not in r2.run["reused"]   # failed cells run again
    assert r2.answer.behavior == "answer" and not has_failed_calls(r2)


def test_a_reduce_output_the_checks_cannot_finish_is_not_reused(two_firms, monkeypatch):
    calls = two_firms
    fake_calls(monkeypatch, calls, ok)
    real = R.finish_answer

    def broken(*a, **k):
        raise ValueError("check failed")
    monkeypatch.setattr(R, "finish_answer", broken)
    cache = RC.RunCache("q")
    with pytest.raises(ValueError):
        pipeline.ask("q", provider="mock", log=False, token=cancel.CancelToken(), cache=cache)
    assert [r.status for r in cache.records if r.stage == "reduce"] == ["invalid"]
    monkeypatch.setattr(R, "finish_answer", real)
    r = pipeline.ask("q", provider="mock", log=False, token=cancel.CancelToken(), cache=cache)
    assert r.run["made"] == {"reduce": 1}


def test_ask_without_a_cache_is_unchanged(two_firms, monkeypatch):
    calls = two_firms
    fake_calls(monkeypatch, calls, ok)
    r = pipeline.ask("q", provider="mock", log=False)
    assert r.run is None and "run" not in pipeline.log_filters(r)


# --- the run log --------------------------------------------------------------------------------

class FakeConn:
    def __init__(self, rows):
        self.rows, self.sql = rows, []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, params=None):
        self.sql.append((sql, params))
        row = self.rows.pop(0)
        return type("Cur", (), {"fetchone": lambda self: row})()


def test_a_stopped_attempt_writes_a_row_with_no_answer(two_firms, monkeypatch):
    calls = two_firms

    started = threading.Event()

    def behave(spec):
        if spec.id == "map.a1.RJF" and not started.is_set():
            started.set()
            cancel.sleep(30)   # cut by Stop in the first attempt only
        started.wait(5)
        return ok(spec)
    fake_calls(monkeypatch, calls, behave)
    conn = FakeConn([{"s": "snap"}, {"query_id": 41}])
    monkeypatch.setattr(pipeline, "connect", lambda: conn)
    cache = RC.RunCache("q")
    t = cancel.CancelToken()
    with pytest.raises(cancel.Cancelled):
        pipeline.ask("q", provider="mock", log=True, token=t, cache=cache,
                     on_event=lambda k, d: t.set("stop", "extract") if k == "evidence" else None)
    sql, params = conn.sql[-1]
    assert "VALUES (%s, %s, %s, %s, NULL, %s, %s)" in sql   # answer NULL
    run = params[2].obj["run"]
    assert run["status"] == "stopped" and run["stage"] == "extract" and run["reason"] == "stop"
    assert run["attempt"] == 1 and run["retry_of"] is None and 0 <= run["stop_s"] <= 5
    assert {(x["id"], x["status"]) for x in run["records"]} == {("map.a1.MS", "ok"), ("map.a1.RJF", "cancelled")}
    assert params[2].obj["cost"]["calls"] == 0   # mock: no paid call to price
    assert cache.query_ids == [41]
    monkeypatch.setattr(pipeline, "_log", lambda r, p: 42)
    r = pipeline.ask("q", provider="mock", log=True, token=cancel.CancelToken(), cache=cache)
    assert r.run["retry_of"] == 41 and r.run["attempt"] == 2 and cache.query_ids == [41, 42]


def test_a_cut_paid_call_is_logged_as_cost_unknown(monkeypatch):
    cache = RC.RunCache("q")
    cache.new_attempt()
    cache.record("reduce", "reduce", "k", "cancelled", provider="deepseek", model="deepseek-v4-pro", usage=None)
    conn = FakeConn([{"s": "snap"}, {"query_id": 5}])
    monkeypatch.setattr(pipeline, "connect", lambda: conn)
    t = cancel.CancelToken()
    t.set("stop", "synthesize")
    pipeline._log_attempt("q", {"query": None, "plan": None}, "deepseek", cache, 1, None, "stopped",
                          "synthesize", t, None)
    cost = conn.sql[-1][1][2].obj["cost"]
    assert cost["no_usage_calls"] == 1 and cost["rows"][0]["status"] == "no_usage"


def test_the_mock_map_calls_land_one_by_one(monkeypatch):
    """verify-cee: call k waits MOCK_DELAY_S x min(k + 1, 3), so evidence cards appear one at a time."""
    monkeypatch.setenv("MOCK_DELAY_S", "0.2")
    waits = []
    monkeypatch.setattr(extract, "mock_extract", lambda spec, wait=None: waits.append(round(wait, 2)) or {"cells": []})
    call = extract.provider_call("mock")
    spec = extract.MapSpec("map.a1.MS", 1, "MS", False, [], {}, {})
    for _ in range(4):
        call(spec, "q", None, [])
    assert waits == [0.2, 0.4, 0.6, 0.6]


# --- the Ask page -------------------------------------------------------------------------------

class Click(BaseException):
    """Stands for Streamlit's rerun exception, raised at a draw when the user clicks during a run."""


def test_a_click_during_the_run_sets_the_token_and_marks_the_run_stopped(monkeypatch):
    """Bare Streamlit (no runtime): the pump's first trace draw raises like a click; the worker is told to stop."""
    import streamlit as st

    from cee.app.views import ask_page as P

    def fake_ask(question, progress=None, filters=None, on_event=None, token=None, cache=None, **k):
        with cancel.use(token):
            progress("extract", "running", "Extracting")
            cancel.sleep(30)
        raise AssertionError("not stopped")
    monkeypatch.setattr(P, "ask", fake_ask)

    def click(*a, **k):
        raise Click()
    monkeypatch.setattr(P.ui, "trace_lines", click)
    with pytest.raises(Click):
        P.ask_with_trace("q", {})
    run = st.session_state["ask_run"]
    assert run.status == "stopped" and run.token.is_set() and run.token.reason == "page" and run.stage == "extract"
    run.thread.join(3)
    assert not run.thread.is_alive()   # the worker saw the token and ended


def late_page():
    from cee.app.views import ask_page
    import streamlit as st
    st.session_state["out"] = ask_page.ask_with_trace("q", {})


def test_a_result_that_lands_after_the_stop_is_never_shown(monkeypatch):
    from streamlit.testing.v1 import AppTest

    from cee.app.views import ask_page as P

    def fake_ask(question, token=None, **k):
        token.set("stop", "synthesize")
        return object()   # the worker finished after the click
    monkeypatch.setattr(P, "ask", fake_ask)
    at = AppTest.from_function(late_page).run()
    assert not at.exception and at.session_state["out"] is None
    run = at.session_state["ask_run"]
    assert run.status == "stopped" and run.result is None
    assert "Stopped while" in at.warning[0].value and [b.label for b in at.button] == ["Retry"]


def render_page():
    from cee.app.views import ask_page
    ask_page.render()


@pytest.fixture
def page_env(monkeypatch):
    from cee.app.views import ask_page as P
    monkeypatch.setattr(P.ui, "corpus_stats", lambda: {"snapshot": "s", "firms": 5, "docs": 1, "chunks": 1,
                                                        "latest": "2026-01-01"})
    asked = []

    def fake_ask(question, filters=None, cache=None, **k):
        asked.append((question, filters, cache))
        raise RuntimeError("provider down")
    monkeypatch.setattr(P, "ask", fake_ask)
    return P, asked


def stopped_run(P, alive=False):
    from tests.test_ask_progress import HITS as MER_HITS
    run = P.Run("How do MS and RJF recruit?", {"firms": ["MS"], "date_range": None, "keywords": []},
                RC.RunCache("How do MS and RJF recruit?"))
    run.status, run.stage, run.plan_text = "stopped", "extract", "Decomposing the question (rules): a1.MS"
    run.token.set("stop", "extract")
    run.stop_clicked = True
    run.evidence = [{"text": "MS recruited advisors.", "hits": [MER_HITS[0]], "entity": "MS", "aspect": "a1"}]
    run.steps = {"extract": ("stopped", "Extracting: stopped")}
    if alive:
        run.thread = type("Alive", (), {"is_alive": lambda self: True, "join": lambda self, timeout=None: None})()
    return run


def test_the_stop_rerun_shows_the_stopped_view_and_starts_no_run(page_env):
    from streamlit.testing.v1 import AppTest
    P, asked = page_env
    at = AppTest.from_function(render_page)
    at.session_state["ask_run"] = stopped_run(P)
    at.run()
    assert not at.exception and asked == []   # no run started
    text = " ".join(m.value for m in at.markdown) + " ".join(w.value for w in at.warning)
    assert "Stopped while extracting evidence" in text and "EVIDENCE - Morgan Stanley - a1" in text
    assert "LLM called:" not in text and "CLAIM (CHECKING)" not in text   # rule 1: no answer, no streamed claims
    assert [b.label for b in at.button if b.label != "Ask"] == ["Retry"] and not at.button(key="retry-ask").disabled


def test_the_retry_poll_while_the_old_worker_lives_draws_no_stop_and_starts_no_run(page_env):
    from streamlit.testing.v1 import AppTest
    P, asked = page_env
    at = AppTest.from_function(render_page)
    at.session_state["ask_run"] = stopped_run(P, alive=True)
    at.run()
    assert not at.exception and asked == []
    labels = [b.label for b in at.button]
    assert "Stop" not in labels and labels.count("Retry") == 1
    assert at.button(key="retry-wait").disabled
    assert P.WAITING_TEXT in " ".join(c.value for c in at.caption)
    at.session_state["retry_ask"] = True   # even a stale Retry flag starts nothing while the worker lives
    at.run()
    assert asked == [] and "Stop" not in [b.label for b in at.button]


def test_retry_asks_once_with_the_saved_question_filters_and_cache(page_env):
    from streamlit.testing.v1 import AppTest
    P, asked = page_env
    at = AppTest.from_function(render_page)
    run = stopped_run(P)
    at.session_state["ask_run"] = run
    at.run()
    at.button(key="retry-ask").click().run()
    assert len(asked) == 1   # one click, one attempt (the attempt failed: no automatic loop)
    question, filters, cache = asked[0]
    assert question == "How do MS and RJF recruit?" and filters == run.filters and cache is run.cache
    assert "provider down" in at.error[0].value and [b.label for b in at.button if b.label != "Ask"] == ["Retry"]
    at.run()   # a later rerun shows the failed view again, and still starts nothing
    assert len(asked) == 1 and "provider down" in at.error[0].value
