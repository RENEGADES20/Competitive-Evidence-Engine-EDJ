"""Segment tagging (#37): a segment starts at a heading line that is only its name and ends at
the next heading of another segment or at the end of the Item. Names come from config, so a new
firm needs only config. Layouts shrunk from BAC-10K-2025 Item 7 and BAC-10Q-2026Q2 Item 2.
No network, no DB."""
from __future__ import annotations

from cee.config import entity_by_id
from cee.ingest.chunk import SegmentTagger, chunk_sections

PARA = "Some text. " * 110  # ~1100 chars: one paragraph per chunk, plus a short heading line


def para(label):
    return f"{label} {PARA}"


def segments_by_label(text, tagger, section="Item 7"):
    """{first word of chunk: segment} for one section, chunked the way load.py does."""
    chunks = chunk_sections("X-10K-2025", "X", "10-K", "2025", [(section, text, None)],
                            segment_for=tagger)
    return [(c.text.split()[0], c.segment) for c in chunks]


# BAC MD&A: the heading sits alone on its line at the end of the previous chunk, with a page
# footer before it; the GWIM tables come right after it and never say "GWIM".
BAC_MDNA = "\n\n".join([
    para("CB1"), para("CB2"), para("CB3"),
    "Bank of America 38",
    "Global Wealth & Investment Management",
    "(Dollars in millions) 2025 2024 % Change " + "1,234 5,678 " * 120,
    para("GW2"), para("GW3"), para("GW4"),
    "Bank of America 40",
    "Global Banking",
    para("GB1"), para("GB2"),
])

BAC_ALIASES = {
    "GWIM": ["Global Wealth & Investment Management", "Global Wealth and Investment Management",
             "GWIM"],
}
BAC_STOPS = ["Consumer Banking", "Global Banking", "Global Markets", "All Other"]


def test_heading_line_starts_segment_and_next_segment_heading_ends_it():
    tags = dict(segments_by_label(BAC_MDNA, SegmentTagger(BAC_ALIASES, BAC_STOPS)))
    assert tags["CB1"] is None
    assert tags["(Dollars"] == "GWIM"          # table chunk with no segment name in it
    assert tags["GW2"] == "GWIM"
    assert tags["GB1"] is None


def test_chunk_ending_with_the_heading_belongs_to_the_previous_segment():
    tags = segments_by_label(BAC_MDNA, SegmentTagger(BAC_ALIASES, BAC_STOPS))
    gwim = [label for label, seg in tags if seg == "GWIM"]
    assert gwim and gwim[0] == "(Dollars"
    assert all(not label.startswith("CB") and not label.startswith("GB") for label in gwim)


def test_mention_inside_prose_is_not_a_heading():
    text = "\n\n".join([
        "Results by segment for Consumer Banking, Global Wealth & Investment Management and "
        "Global Banking are discussed in Business Segment Operations.",
        para("XX1"),
        "GWIM consists of two primary businesses: Merrill Wealth Management and Private Bank.",
    ])
    assert all(seg is None for _, seg in segments_by_label(text, SegmentTagger(BAC_ALIASES, BAC_STOPS)))


def test_segment_does_not_leak_into_the_next_item():
    tagger = SegmentTagger(BAC_ALIASES, BAC_STOPS)
    sections = [
        ("Item 7", "\n\n".join([para("CB1"), "Global Wealth & Investment Management", para("GW1")]), None),
        ("Item 7A", para("MR1"), None),
    ]
    chunks = chunk_sections("X-10K-2025", "X", "10-K", "2025", sections, segment_for=tagger)
    tags = {c.text.split()[0]: c.segment for c in chunks}
    assert tags["GW1"] == "GWIM"
    assert tags["MR1"] is None


def test_heading_match_ignores_case_and_spacing():
    text = "\n\n".join(["  GLOBAL WEALTH  &  INVESTMENT MANAGEMENT  ", para("GW1")])
    assert segments_by_label(text, SegmentTagger(BAC_ALIASES, BAC_STOPS)) == [("GLOBAL", "GWIM")]


def test_prefix_carries_the_segment():
    text = "\n\n".join(["Global Wealth & Investment Management", para("GW1")])
    [c] = chunk_sections("BAC-10K-2025", "BAC", "10-K", "2025", [("Item 7", text, None)],
                         segment_for=SegmentTagger(BAC_ALIASES, BAC_STOPS))
    assert c.prefix == "[BAC|GWIM|10-K|2025]"


def test_another_firm_needs_only_config():
    # Made-up firm: two tagged segments, one untagged; nothing about it is in the code.
    aliases = {"Retail": ["Retail Brokerage"], "Advice": ["Advice Solutions", "Advice"]}
    stops = ["Corporate and Other"]
    text = "\n\n".join([
        para("PRE"),
        "Retail Brokerage", para("RB1"),
        "ADVICE SOLUTIONS", para("AS1"),
        "Corporate and Other", para("CO1"),
    ])
    # Each heading packs onto the end of the chunk before it, as in the BAC filings.
    assert segments_by_label(text, SegmentTagger(aliases, stops)) == [
        ("PRE", None), ("RB1", "Retail"), ("AS1", "Advice"), ("CO1", None)]


def test_bac_config_drives_the_tagger():
    bac = entity_by_id("BAC")
    tags = dict(segments_by_label(BAC_MDNA, SegmentTagger(bac["segment_aliases"], bac["segment_stops"])))
    assert tags["GW2"] == "GWIM"
    assert tags["CB1"] is None and tags["GB1"] is None


def test_section_titled_with_a_segment_name_is_that_segment():
    # BAC decks and supplements: each slide or table is a section titled by its heading.
    tagger = SegmentTagger(BAC_ALIASES, BAC_STOPS)
    sections = [
        ("Global Wealth & Investment Management Key Indicators", para("GW1"), 3),
        ("Global Banking Key Indicators", para("GB1"), 4),
        ("Global Wealth & Investment Management", para("GW2"), 5),
        ("Balance Sheet Highlights", para("BS1"), 6),
    ]
    chunks = chunk_sections("X-SUPP", "X", "supplement", "2026Q1", sections, segment_for=tagger)
    assert [(c.text.split()[0], c.segment) for c in chunks] == [
        ("GW1", "GWIM"), ("GB1", None), ("GW2", "GWIM"), ("BS1", None)]


def test_page_with_titles_of_two_segments_is_left_untagged():
    # BAC-DECK-2026Q1 p19: one column per segment; the parser put the GWIM column heading over
    # Consumer Banking text. Untagged beats mis-tagged.
    sections = [
        ("Global Wealth & Investment Management", para("GW1"), 14),
        ("Global Wealth & Investment Management", para("CB1"), 19),
        ("Global Markets", para("GM1"), 19),
    ]
    tagger = SegmentTagger(BAC_ALIASES, BAC_STOPS, sections)
    chunks = chunk_sections("X-DECK", "X", "deck", "2026Q1", sections, segment_for=tagger)
    assert [(c.text.split()[0], c.segment) for c in chunks] == [
        ("GW1", "GWIM"), ("CB1", None), ("GM1", None)]


def test_chunk_with_another_segment_heading_and_text_after_it_is_untagged():
    # BAC-10K-2025#1041 (segment note): GWIM paragraph, "Global Banking" heading, Global Banking
    # paragraph, all in one chunk. Untagged beats mis-tagged.
    short = "Some text. " * 30
    text = "\n\n".join([
        "Global Wealth & Investment Management", f"GW1 {short}",
        f"GW2 {short}", "Global Banking", f"GB1 {short}",
        "Global Markets", para("GM1"),
    ])
    tags = segments_by_label(text, SegmentTagger(BAC_ALIASES, BAC_STOPS))
    assert tags[0] == ("Global", None)
    assert all(seg is None for _, seg in tags)
