"""verify_cee.wait_for_text: a page that never finishes is a clear timeout, not a wrong FAIL (#83)."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "verify_cee.py"
spec = importlib.util.spec_from_file_location("verify_cee", SCRIPT)
vc = importlib.util.module_from_spec(spec)
sys.modules["verify_cee"] = vc
spec.loader.exec_module(vc)


class Page:
    def __init__(self, renders: bool):
        self.renders, self.idle = renders, 0

    def wait_for_function(self, js, arg=None, timeout=None):
        if "innerText" in js and not self.renders:
            raise TimeoutError("Timeout 90000ms exceeded")   # what playwright raises

    def wait_for_load_state(self, state):
        self.idle += 1

    def wait_for_timeout(self, ms):
        pass


def test_timeout_names_what_did_not_render():
    with pytest.raises(vc.RenderTimeout, match=r"the answer did not render within \d+ s \(waited for: LLM called:\)"):
        vc.wait_for_text(Page(renders=False), ["LLM called:"], "the answer")


def test_rendered_page_then_waits_for_idle():
    page = Page(renders=True)
    vc.wait_for_text(page, ["Stored passage"], "the source page")
    assert page.idle == 1
