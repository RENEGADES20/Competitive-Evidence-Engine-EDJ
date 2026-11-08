"""#84: text from a docling item is stored under the page it is on. An item whose provenance covers
two pages is cut at the charspan where the page changes. Fake items, no docling, no DB."""
from __future__ import annotations

from types import SimpleNamespace as NS

from cee.ingest.pdf import doc_items


def prov(page, start, end):
    return NS(page_no=page, charspan=(start, end))


def text(t, *spans, label="text"):
    return NS(text=t, prov=list(spans), label=label, kind="text")


def table(md, *spans):
    return NS(prov=list(spans), label="table", kind="table", export_to_markdown=lambda doc: md)


class Doc:
    def __init__(self, *items):
        self.items = items

    def iterate_items(self, traverse_pictures=False):
        assert traverse_pictures
        return ((i, 0) for i in self.items)


def items(*its):
    return doc_items(Doc(*its), lambda i: i.kind == "table")


# The issue's item: SCHW-DECK-2026Q1 p4, pages [4,4,4,5], last span on the next slide.
SLIDE = 'Sustaining Momentum Delivering for Clients Accelerating the Pace of Innovation Our "Through Clients\' Eyes" Strategy continues to drive growth across all fronts.'


def test_two_page_item_is_split_at_the_page_break_and_joins_the_next_page():
    item = text(SLIDE, prov(4, 0, 19), prov(4, 20, 42), prov(4, 43, 78), prov(5, 79, 160))
    out, fallbacks = items(text("Key Takeaways", prov(4, 0, 13), label="section_header"), item,
                           text("1Q26 vs. 1Q25", prov(5, 0, 13)))
    assert out == [("Key Takeaways", 4, SLIDE[:78]),
                   ("Key Takeaways", 5, SLIDE[79:] + "\n\n1Q26 vs. 1Q25")]
    assert fallbacks == 0


def test_page_order_4_5_4_gives_three_parts_in_order():
    t = "aaa bbb ccc"
    out, _ = items(text(t, prov(4, 0, 3), prov(5, 4, 7), prov(4, 8, 11)))
    assert out == [("Document", 4, "aaa"), ("Document", 5, "bbb"), ("Document", 4, "ccc")]


def test_several_spans_on_one_page_stay_one_item():
    t = "Schwab Private Issuer Equity Services Schwab Teen Investor"
    out, fallbacks = items(text(t, prov(6, 0, 37), prov(6, 38, 58)))
    assert out == [("Document", 6, t)] and fallbacks == 0


def test_charspans_that_do_not_fit_keep_the_item_on_its_main_page():
    t = "short text"
    out, fallbacks = items(text(t, prov(8, 0, 2), prov(9, 3, 40)))      # last span past the end
    assert out == [("Document", 9, t)] and fallbacks == 1
    out, fallbacks = items(text(t, prov(8, 0, 6), prov(9, 0, 10)))      # page 9 starts before page 8 ends
    assert out == [("Document", 9, t)] and fallbacks == 1                # 10 chars on p9, 6 on p8


def test_table_over_two_pages_stays_on_its_first_page():
    md = "| a | b |\n| --- | --- |\n| 1 | 2 |"
    out, fallbacks = items(table(md, prov(3, 0, 0), prov(4, 0, 0)))
    assert out == [("Document", 3, md)] and fallbacks == 0


def test_item_without_provenance_or_text_is_skipped():
    out, _ = items(text("no page"), text("   ", prov(1, 0, 3)), text("kept", prov(2, 0, 4)))
    assert out == [("Document", 2, "kept")]
