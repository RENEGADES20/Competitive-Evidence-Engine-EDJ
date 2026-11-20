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


class LatePage(Page):
    """#248: the source page whose cited passage renders after the header; records what was awaited."""

    def __init__(self, renders: bool):
        super().__init__(renders)
        self.awaited = []

    def wait_for_function(self, js, arg=None, timeout=None):
        self.awaited.append(arg)
        super().wait_for_function(js, arg, timeout)


def test_open_citation_waits_for_the_cited_passage_tag():
    page = LatePage(renders=True)
    vc.wait_for_cited(page, "EDJ-10K-2025#19")
    assert ["CITED PASSAGE · EDJ-10K-2025#19", "is not in the stored corpus"] in page.awaited


def test_a_cited_passage_that_never_renders_is_a_timeout_not_a_fail():
    with pytest.raises(vc.RenderTimeout, match="the cited passage EDJ-10K-2025#19 did not render"):
        vc.wait_for_cited(LatePage(renders=False), "EDJ-10K-2025#19")
