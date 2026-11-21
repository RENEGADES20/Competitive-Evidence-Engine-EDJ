"""Architecture page (#270): one source of module text for the page and the README diagram."""
import re
from pathlib import Path

from cee.app import architecture as A
from cee.app.views import architecture_page as page

REPO = Path(__file__).resolve().parents[1]
NODE = re.compile(r'\b([A-Za-z]\w*)\s*(?:\[\(|\(\[|\[|\(|\{)"([^"]*)"')


def mermaid_nodes(md: Path, heading: str) -> dict[str, str]:
    text = md.read_text(encoding="utf-8")
    section = text[text.index(heading):]
    block = section[section.index("```mermaid"):]
    block = block[:block.index("```", 3)]
    groups = set(re.findall(r"subgraph\s+(\w+)", block))
    return {i: t for i, t in NODE.findall(block)
            if i not in groups and not re.fullmatch(r"k\d", i)}   # subgraph titles; k1..k4: the legend


def test_modules_are_complete_and_unique():
    ids = [m.id for m in A.MODULES]
    assert len(ids) == len(set(ids))
    for m in A.MODULES:
        assert m.kind in A.KINDS and m.stage in ("offline", "online")
        assert all(getattr(m, f).strip() for f in ("label", "sub", "does", "who", "rule")), m.id
        assert '"' not in m.node_text   # quoted mermaid labels
    known = set(ids)
    assert all(a in known and b in known for a, b in A.EDGES)
    assert set(page.PLACE) == known   # every module has a place on the page's diagram


def test_readme_diagram_matches_the_module_list():
    assert mermaid_nodes(REPO / "README.md", "## How it works") == {m.id: m.node_text for m in A.MODULES}


def test_architecture_doc_diagram_matches_the_module_list():
    assert mermaid_nodes(REPO / "docs/ARCHITECTURE.md", "## Pipeline") == {m.id: m.node_text for m in A.MODULES}


def test_page_html_holds_every_module_and_no_script_or_network():
    for dark in (False, True):
        html = page.page_html(dark) + page.list_html()
        assert "<script" not in html.lower() and "http" not in html.lower()
        assert html.count('tabindex="0"') == len(A.MODULES)
        for m in A.MODULES:
            assert f'id="node-{m.id}"' in html and f'id="tip-{m.id}"' in html and f'id="item-{m.id}"' in html
            assert m.label in html
            assert page.escape(m.rule) in html and page.escape(m.does) in html
        assert page.escape(A.PRINCIPLE) in html


def test_no_firm_figures_on_the_page():
    html = re.sub(r"<style>.*?</style>", "", page.page_html() + page.list_html(), flags=re.S)
    text = re.sub(r"<[^>]+>", " ", html)   # the visible text only
    assert not re.search(r"\$\s?\d|\d[\d,]*\s?(billion|million|advisors|%)", text, re.I)


def test_nav_has_architecture_and_no_design_page():
    app = (REPO / "src/cee/app/streamlit_app.py").read_text(encoding="utf-8")
    assert 'title="Architecture", url_path="architecture"' in app
    assert "design_page" not in app and 'title="Design"' not in app
    assert not (REPO / "src/cee/app/views/design_page.py").exists()
    for folder in ("src", "tests", "scripts"):
        for f in (REPO / folder).rglob("*.py"):
            if f.name != Path(__file__).name:
                assert "design_page" not in f.read_text(encoding="utf-8"), f
