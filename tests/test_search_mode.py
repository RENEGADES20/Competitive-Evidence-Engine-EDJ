"""Search mode switch (#128): plain labels, default from RETRIEVAL_MODE, no internal words in the UI."""
import re

import pytest

from cee.app.views import ask_page
from cee.app.views.ask_page import MODE_HELP, MODE_LABELS, SMART_OFF, default_mode, mode_label


@pytest.mark.parametrize("env, want", [("fts", "fts"), ("hybrid", "hybrid"), ("hybrid-norerank", "hybrid")])
def test_default_follows_retrieval_mode(env, want, monkeypatch):
    monkeypatch.setattr(ask_page, "settings", lambda: type("S", (), {"retrieval_mode": env})())
    assert default_mode() == want


def test_only_two_modes_offered():
    assert list(MODE_LABELS) == ["fts", "hybrid"]


def test_labels_are_plain():
    assert (mode_label("fts"), mode_label("hybrid"), mode_label("hybrid-norerank")) == (
        "Exact match", "Smart search", "Smart search")


def test_no_internal_words_in_ui_text():
    text = " ".join([*MODE_LABELS.values(), *MODE_HELP.values(), SMART_OFF])
    assert not re.search(r"hybrid|rerank|\bFTS\b|vector", text, re.IGNORECASE)
