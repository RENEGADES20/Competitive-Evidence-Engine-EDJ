"""Stored text reaches the page literally: no Markdown or LaTeX inside component HTML (#99)."""
from cee.app import components as ui

PASSAGE = "Net income for GWIM increased $407 million to $4.7 billion.\n\n# Not a heading\n\n*not italic* | a | b |"


def sent(monkeypatch, draw) -> str:
    out = []
    monkeypatch.setattr(ui.st, "markdown", lambda s, **kw: out.append(s))
    draw()
    return "".join(out)


def test_passage_is_one_html_line_with_dollars_as_entities(monkeypatch):
    html = sent(monkeypatch, lambda: ui.passage(PASSAGE))
    assert "\n" not in html          # no blank line can end the HTML block
    assert "$" not in html           # no $...$ math
    assert "&#36;407 million to &#36;4.7 billion" in html
    assert "&#10;&#10;# Not a heading" in html   # line breaks kept for white-space: pre-wrap


def test_claim_caveat_and_gap_are_escaped_the_same_way(monkeypatch):
    for draw in (lambda: ui.claim_card(1, PASSAGE, [("BAC-10K-2025#246", 2)]),
                 lambda: ui.caveat_box("GWIM costs $1 and $2"),
                 lambda: ui.gap_box("No $ data", "10-K at $0")):
        html = sent(monkeypatch, draw)
        assert "$" not in html and "\n" not in html


def test_context_passages_mark_the_cited_chunk_and_escape_text(monkeypatch):
    items = [{"chunk_id": "D#1", "text": "before $5", "page": None, "cited": False},
             {"chunk_id": "D#2", "text": "<b>cited</b>\n\n# text", "page": 8, "cited": True}]
    html = sent(monkeypatch, lambda: ui.context_passages(items))
    assert html.count("CITED PASSAGE") == 1 and html.count("NEIGHBOURING PASSAGE") == 1
    assert "CITED PASSAGE · D#2 · page 8" in html
    assert 'class="cee-ctx cited"' in html and 'class="cee-ctx"' in html
    assert "<b>cited</b>" not in html and "&lt;b&gt;cited" in html   # stored text is escaped
    assert "$" not in html and "\n" not in html
