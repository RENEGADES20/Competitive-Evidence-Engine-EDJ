"""#277: the cancel token of one answer run (the Ask page's Stop button).

The Ask page runs the answer flow in a worker thread and holds a CancelToken in the session. Stop sets it;
the flow checks it before every model call and at each stage boundary (`check`), the DeepSeek stream watchdog
closes an open stream when it is set (llm.read_stream), and queued map calls are never started
(extract.run_round). The token travels in a context variable (`use`); extract.run_round copies the context
into each map call, because executor threads do not inherit context variables.

`Cancelled` subclasses BaseException (like KeyboardInterrupt), so no `except Exception` turns a stop into a
failed call, a failed stage or the planner's rule-plan fallback. With no token (the eval, tests, the CLI)
every helper is a no-op and `sleep` is time.sleep.
"""
from __future__ import annotations

import contextvars
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager


class Cancelled(BaseException):
    """The run was stopped by the user (the token is set). Not a failure: never reused, never retried by code."""


class CancelToken:
    def __init__(self) -> None:
        self._event = threading.Event()
        self.reason: str | None = None   # "stop" (the Stop button) or "page" (another click interrupted the run)
        self.stage: str | None = None    # the stage that was running when the token was set
        self.set_at: float | None = None   # time.monotonic() when set

    def set(self, reason: str = "stop", stage: str | None = None) -> None:
        if not self._event.is_set():
            self.reason, self.stage, self.set_at = reason, stage, time.monotonic()
        self._event.set()

    def is_set(self) -> bool:
        return self._event.is_set()

    def wait(self, timeout: float) -> bool:
        return self._event.wait(timeout)


_current: contextvars.ContextVar[CancelToken | None] = contextvars.ContextVar("cee_cancel", default=None)


def current() -> CancelToken | None:
    return _current.get()


@contextmanager
def use(token: CancelToken | None) -> Iterator[CancelToken | None]:
    """Make `token` the active token of this thread's context for the block (None: no token)."""
    reset = _current.set(token)
    try:
        yield token
    finally:
        _current.reset(reset)


def is_set() -> bool:
    t = _current.get()
    return t is not None and t.is_set()


def check() -> None:
    """Raise Cancelled when the active token is set."""
    if is_set():
        raise Cancelled("stopped by the user")


def sleep(seconds: float) -> None:
    """time.sleep that a stop cuts short (raises Cancelled). The mock waits through it (MOCK_DELAY_S)."""
    t = _current.get()
    if t is None:
        if seconds > 0:
            time.sleep(seconds)
        return
    if seconds > 0:   # no wait, no check: a zero delay never cuts a call that already has its output
        t.wait(seconds)
        check()
