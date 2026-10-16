"""Item sections for 10-K/10-Q text (#70): the layouts seen in the EDJ, RJF, BAC, SCHW and MS
filings, shrunk to a few lines each. No network, no DB."""
from __future__ import annotations

from cee.ingest.chunk import split_10k_sections

BODY = "Some text about the business.\n\nMore text in the same section.\n\n"


def names(text):
    return [s for s, _ in split_10k_sections(text)]


def body_of(text, name):
    return next(b for s, b in split_10k_sections(text) if s == name)


def test_mixed_case_headings_skip_the_table_of_contents():
    # BAC/SCHW 10-K: "Item 1." in mixed case; the table of contents lists every Item with a page.
    text = (
        "Cover page\n\n"
        "  Item 1.       Business                                  2\n"
        "  Item 1A.      Risk Factors                              8\n"
        "  Item 7.       Management's Discussion and Analysis     25\n\n"
        "Item 1. Business\n\n" + BODY +
        "Item 1A. Risk Factors\n\n" + BODY +
        "Item 7. Management's Discussion and Analysis\n\n" + BODY)
    assert names(text) == ["Cover", "Item 1", "Item 1A", "Item 7"]
    assert "Risk Factors                              8" in body_of(text, "Cover")
    assert body_of(text, "Item 1").startswith("Item 1. Business")


def test_upper_case_headings_ignore_running_page_headers():
    # EDJ: "ITEM 1. BUSINESS" heads the section; "Item 1. Business, continued" tops each page.
    text = (
        "Cover page\n\n"
        "ITEM 1. BUSINESS\n\n" + BODY +
        "Item 1. Business, continued\n\n" + BODY +
        "ITEM 1A. RISK FACTORS\n\n" + BODY)
    assert names(text) == ["Cover", "Item 1", "Item 1A"]
    assert "Business, continued" in body_of(text, "Item 1")


def test_table_entry_without_page_number_is_still_table_of_contents():
    # BAC 10-Q: "Item 2. ..." has no page number but heads a list of sub-entries that do.
    text = (
        "INDEX\n\n"
        "  Item 1. Financial Statements                               Page\n"
        "  Consolidated Balance Sheet                                   48\n\n"
        "  Item 2. Management's Discussion and Analysis\n"
        "  Executive Summary                                             3\n"
        "  Item 3. Quantitative and Qualitative Disclosures             46\n\n"
        "Item 2. Management's Discussion and Analysis\n\n" + BODY +
        "Item 3. Quantitative and Qualitative Disclosures\n\n" + BODY +
        "Item 1. Financial Statements\n\n" + BODY)
    assert names(text) == ["Cover", "Item 2", "Item 3", "Item 1"]
    assert "Executive Summary" in body_of(text, "Cover")


def test_ten_q_keeps_part_one_and_part_two_items_in_order():
    # 10-Q: Part I and Part II both have an Item 1; both are real sections.
    text = (
        "PART I\n\nItem 1. Financial Statements\n\n" + BODY +
        "Item 2. Management's Discussion and Analysis\n\n" + BODY +
        "PART II\n\nItem 1. Legal Proceedings\n\n" + BODY +
        "Item 1A. Risk Factors\n\n" + BODY)
    assert names(text) == ["Cover", "Item 1", "Item 2", "Item 1", "Item 1A"]
    assert split_10k_sections(text)[3][1].startswith("Item 1. Legal Proceedings")


def test_prose_starting_with_item_is_not_a_heading():
    text = "Item 1. Business\n\n" + BODY + "Item 1A " + "of our annual report describes risks. " * 10 + "\n"
    assert names(text) == ["Cover", "Item 1"]


def test_cross_reference_table_of_contents():
    # MS: no "Item" text in the body; the table of contents maps titles to Part/Item/Page, and
    # the body heading can drop the "(Unaudited)" note, so the next row's title is used.
    text = (
        "  Table of Contents                                Part   Item Page\n"
        "  Management's Discussion and Analysis              I      2   4\n"
        "  Wealth Management                                            10\n"
        "  Quantitative and Qualitative Disclosures about Risk  I   3  29\n"
        "  Consolidated Financial Statements and Notes       I      1  39\n"
        "  Consolidated Income Statement (Unaudited)                    39\n"
        "  Legal Proceedings                                 II     1  79\n"
        "  Risk Factors                                      II    1A  79\n\n"
        "Management's Discussion and Analysis\n\n" + BODY +
        "Wealth Management\n\n" + BODY +
        "Quantitative and Qualitative Disclosures about Risk\n\n" + BODY +
        "  Consolidated Income Statement\n\n" + BODY +
        "Legal Proceedings\n\n" + BODY +
        "Risk Factors\n\n" + BODY)
    assert names(text) == ["Cover", "Item 2", "Item 3", "Item 1", "Item 1", "Item 1A"]
    assert "Wealth Management" in body_of(text, "Item 2")
    assert "Table of Contents" in body_of(text, "Cover")


def test_no_headings_is_one_document_section():
    assert split_10k_sections("Just a press release.\n\nNo items here.") == [
        ("Document", "Just a press release.\n\nNo items here.")]
