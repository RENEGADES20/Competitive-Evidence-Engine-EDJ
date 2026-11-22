"""#275: the stream idle timeout (DEEPSEEK_IDLE_S) and the off reduce cap. Fake streams that block on a real
threading.Event, released only by close(), so the watchdog thread really runs. Never a real call."""
import json
import threading
import time
from types import SimpleNamespace as NS

import openai
import pytest

from cee.answer import llm
from tests.test_deepseek_stages import USAGE, _req, chunk, tc


class BlockingStream:
    """Yields `chunks`, then blocks until close() (the watchdog) or `release` is set; `after` = what happens once
    released: 'raise' a read error like a closed socket, or 'end' (the iteration just stops)."""

    def __init__(self, chunks, after="raise", tail=()):
        self.chunks, self.after, self.tail = list(chunks), after, list(tail)
        self.closed, self.release = threading.Event(), threading.Event()

    def close(self):
        self.closed.set()

    def __iter__(self):
        yield from self.chunks
        while not (self.closed.is_set() or self.release.is_set()):
            self.closed.wait(0.02)
        if self.closed.is_set():
            if self.after == "raise":
                raise RuntimeError("stream closed")   # what a read on a closed response looks like
            return
        yield from self.tail


class Client:
    def __init__(self, stream=None, error=None):
        self.stream, self.error, self.calls, self.kwargs = stream, error, 0, None
        self.chat = NS(completions=NS(create=self._create))

    def _create(self, **kwargs):
        self.calls += 1
        self.kwargs = kwargs
        if self.error:
            raise self.error
        return self.stream


@pytest.fixture
def idle(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_IDLE_S", "0.3")
    return 0.3


def test_a_stall_before_any_output_fails_fast_once(idle):
    client = Client(BlockingStream([]))
    t0 = time.monotonic()
    with pytest.raises(llm.StreamIdle) as e:
        llm.deepseek_create(client, _req("reduce"))
    assert time.monotonic() - t0 < 5 and client.stream.closed.is_set()
    assert e.value.output_seen is False and e.value.ttft_s is None and e.value.idle_s == idle
    assert client.calls == 1   # TL ruling: no automatic retry


def test_a_stall_after_output_keeps_the_partial_output(idle):
    args = '{"answerable": true, "claims": [{"text": "a'
    client = Client(BlockingStream([chunk(reasoning="Let me"), chunk(calls=[tc(0, args, name="submit_answer")])],
                                   after="end"))
    with pytest.raises(llm.StreamIdle) as e:
        llm.deepseek_create(client, _req("reduce"))
    assert e.value.output_seen is True and e.value.ttft_s is not None
    assert e.value.partial["reasoning_content"] == "Let me"
    assert e.value.partial["tool_calls"][0]["function"]["arguments"] == args
    assert client.calls == 1


def test_chunks_that_keep_coming_are_not_idle(idle):
    class Slow:
        def __iter__(self):
            for part in ['{"a"', ": 1", "}"]:
                time.sleep(0.12)   # each gap under the idle limit; the whole call is longer than it
                yield chunk(calls=[tc(0, part, name="t")])
            yield chunk(finish="tool_calls")
            yield chunk(usage=USAGE, choices=False)
    seen = []
    resp = llm.deepseek_create(Client(Slow()), _req("map"), on_delta=lambda i, n, d: seen.append(d))
    call, stop, _, _ = llm.deepseek_tool_call(resp, "t")
    assert json.loads(call.function.arguments) == {"a": 1} and stop == "tool_calls" and seen == ['{"a"', ": 1", "}"]


def test_a_read_timeout_is_a_stall_too(idle):
    class TimesOut:
        def __iter__(self):
            yield chunk(reasoning="x")
            raise openai.APITimeoutError(request=None)
    with pytest.raises(llm.StreamIdle) as e:
        llm.deepseek_create(Client(TimesOut()), _req("plan"))
    assert e.value.output_seen is True


def test_any_other_stream_error_propagates(idle):
    class Broken:
        def __iter__(self):
            yield chunk(reasoning="x")
            raise ValueError("bad chunk")
    with pytest.raises(ValueError, match="bad chunk"):
        llm.deepseek_create(Client(Broken()), _req("plan"))


def test_streamed_requests_get_the_idle_read_timeout_others_keep_3600(idle):
    client = Client(BlockingStream([chunk(finish="stop")], after="end"))
    client.stream.release.set()
    llm.deepseek_create(client, _req("reduce"))
    assert isinstance(client.kwargs["timeout"], openai.Timeout)
    assert client.kwargs["timeout"].read == pytest.approx(idle + llm.IDLE_READ_MARGIN_S)
    whole = Client(NS(choices=[NS(message=NS(tool_calls=None), finish_reason="stop")]))
    req = {k: v for k, v in _req("reduce").items() if k not in ("stream", "stream_options")}
    llm.deepseek_create(whole, req)
    assert "timeout" not in whole.kwargs   # the client's own 3600 s read timeout applies


def test_idle_setting_is_checked(monkeypatch):
    from cee import config
    monkeypatch.setenv("DEEPSEEK_IDLE_S", "soon")
    with pytest.raises(ValueError, match="DEEPSEEK_IDLE_S"):
        config.settings()
    monkeypatch.setenv("DEEPSEEK_IDLE_S", "")
    assert config.settings().deepseek_idle_s == 120.0


def test_off_reduce_cap_is_64000_only_when_streamed(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_EFFORT_REDUCE", "off")
    assert llm.stage_max_tokens("reduce") == 64000
    assert llm.request_version("deepseek", "reduce") == "ds-strict-2-reduce-off-c64000-s1"
    monkeypatch.setenv("DEEPSEEK_STREAM", "off")
    assert llm.stage_max_tokens("reduce") == 20000
    monkeypatch.setenv("DEEPSEEK_STREAM", "on")
    monkeypatch.setenv("DEEPSEEK_EFFORT_MAP", "off")
    assert llm.stage_max_tokens("map") == 20000   # only the reduce writes a whole answer
