"""#247 part 4 (plans/0247-reduce-4.md): the code note "latest count found in the <doc type>: <date>
(<chunk>); no count found in the <doc type> read since (<docs>)" (item 9) and the series-only registry pins
(`series_pins`, item 10). Fakes and the registry; the pin checks use the database and skip without one.
0 paid calls."""
import datetime as dt
import re

import psycopg
import pytest
import yaml

from cee.answer import matrix as mx
from cee.answer.matrix import Cell, EvidenceMatrix, Item
from cee.config import MANIFEST_PATH, REPO_ROOT, settings
from cee.retrieve import planner
from cee.retrieve.fts import Hit
from cee.retrieve.planner import Aspect

AS_OF = dt.date(2026, 11, 17)
Q11 = "How does each of the five define and report advisor headcount -- and what does each definition include or exclude?"
Q23 = "Advisor headcount over the last eight quarters across the five."
Q24 = "Client assets per advisor across the five -- and is that comparison even valid?"
SERIES = Aspect("a1", "Advisor headcount over the last eight quarters.", metric="advisor_headcount", kind="series")
BANNED = re.compile(r"discontinu|stopped|no longer|ceased|current|last reported", re.I)
MS_LATER = ["MS-SUPP-2025Q4", "MS-SUPP-2026Q1", "MS-SUPP-2026Q2", "MS-SUPP-2026Q3"]
MS_NOTE = ("Morgan Stanley - Advisor headcount: latest count found in the quarterly financial supplements: 2020-12-31 "
           "(MS-SUPP-2020Q4#1); no count found in the quarterly financial supplements read since (MS-SUPP-2025Q4, "
           "MS-SUPP-2026Q1, MS-SUPP-2026Q2, MS-SUPP-2026Q3).")


def hit(cid, doc_type, date, part, entity=None):
    doc = cid.split("#")[0]
    return Hit(cid, doc, entity or doc.split("-")[0], None, doc_type, 2, date, date, None, None, 1.0, "text",
               part_id=part)


def item(value, period, chunk, unit="advisors"):
    return Item(text="t", quote="q", chunk_ids=[chunk], value=value, period=period, unit=unit)


def matrix(question, aspects, cells, hits, rows):
    m = EvidenceMatrix(question, rows=rows, aspects=aspects, cells={c.id: c for c in cells})
    m.hits = {h.chunk_id: h for h in hits}
    return m


def notes(m):
    out = mx.last_reported(m, AS_OF)
    for n in out:
        assert not BANNED.search(n), n
    return out


def ms_series(label="fact", later=MS_LATER, extra_items=(), extra_hits=()):
    items = [item("15,468", "2019-12-31", "MS-SUPP-2020Q4#1", "Wealth Management representatives"),
             item("15,950", "2020-12-31", "MS-SUPP-2020Q4#1", "Wealth Management representatives"), *extra_items]
    hits = [hit("MS-SUPP-2020Q4#1", "supplement", "2020-12-31", "a1.MS")]
    hits += [hit(f"{d}#7", "supplement", f"{d[8:12]}-{ {'Q1': '03-31', 'Q2': '06-30', 'Q3': '09-30', 'Q4': '12-31'}[d[12:]] }", "a1.MS")
             for d in later]
    return [Cell("a1.MS", "MS", "a1", "named", label, items=items)], hits + list(extra_hits)


# --- item 9 ------------------------------------------------------------------------------------------------

def test_q23_ms_shape_exact_template():
    cells, hits = ms_series()
    assert notes(matrix(Q23, [SERIES], cells, hits, ["MS"])) == [MS_NOTE]


def test_merrill_different_quantity_names_the_parent_and_ignores_the_undated_deck():
    items = [item("19,273", "2022-12-31", "BAC-SUPP-2023Q4#2", "total wealth advisors"),
             item("18,916", "2023-12-31", "BAC-SUPP-2023Q4#2", "total wealth advisors"),
             item(">15K", "", "BAC-DECK-2025-investor-day#9", "wealth advisors")]
    hits = [hit("BAC-SUPP-2023Q4#2", "supplement", "2023-12-31", "a1.MER", "BAC"),
            hit("BAC-DECK-2025-investor-day#9", "deck", "2025-11-05", "a1.MER", "BAC"),
            hit("BAC-SUPP-2025Q4#58", "supplement", "2025-12-31", "a1.MER", "BAC"),
            hit("BAC-SUPP-2026Q3#12", "supplement", "2026-09-30", "a1.MER", "BAC")]
    out = notes(matrix(Q23, [SERIES], [Cell("a1.MER", "MER", "a1", "named", "different_quantity", items=items)],
                       hits, ["MER"]))
    assert out == ["Merrill (Bank of America Corporation) - Advisor headcount: latest count found in the quarterly "
                   "financial supplements: 2023-12-31 (BAC-SUPP-2023Q4#2); no count found in the quarterly financial "
                   "supplements read since (BAC-SUPP-2025Q4, BAC-SUPP-2026Q3)."]


def test_q11_shape_one_note_per_firm():
    aspects = [Aspect(f"a{n}", "How each firm defines advisor headcount.", metric="advisor_headcount") for n in range(1, 5)]
    cells, hits = ms_series()
    cells = [Cell("a2.MS", "MS", "a2", "named", "fact", items=cells[0].items)]
    cells += [Cell(f"a{n}.MS", "MS", f"a{n}", "named", "not_found") for n in (1, 3, 4)]
    hits = [hit(h.chunk_id, h.doc_type, h.published_at, f"a{1 + n % 4}.MS") for n, h in enumerate(hits)]
    assert notes(matrix(Q11, aspects, cells, hits, ["MS"])) == [MS_NOTE]


def test_rjf_annual_10k_with_later_10qs_gets_none():
    items = [item("8,943", "2025-09-30", "RJF-10K-2025#227", "financial advisors")]
    hits = [hit("RJF-10K-2025#227", "10-K", "2025-09-30", "a3.RJF"),
            hit("RJF-10Q-2025Q4#1", "10-Q", "2025-12-31", "a3.RJF"), hit("RJF-10Q-2026Q2#1", "10-Q", "2026-06-30", "a3.RJF")]
    aspect = Aspect("a3", "Number of financial advisors.", metric="advisor_headcount")
    assert notes(matrix(Q24, [aspect], [Cell("a3.RJF", "RJF", "a3", "named", "fact", items=items)], hits, ["RJF"])) == []


def test_recent_count_and_count_inside_the_asked_window_get_none():
    items = [item("20,514", "2026-06-26", "EDJ-10Q-2026Q2#60", "financial advisors")]
    hits = [hit("EDJ-10Q-2026Q2#60", "10-Q", "2026-06-26", "a1.EDJ")]
    assert notes(matrix(Q23, [SERIES], [Cell("a1.EDJ", "EDJ", "a1", "named", "fact", items=items)], hits, ["EDJ"])) == []
    items = [item("8,731", "2025-03-31", "RJF-DECK-2025-investor-day#43", "financial advisors")]
    hits = [hit("RJF-DECK-2025-investor-day#43", "deck", "2025-06-05", "a1.RJF"),
            hit("RJF-DECK-2026Q2#32", "deck", "2026-06-30", "a1.RJF")]
    assert notes(matrix(Q23, [SERIES], [Cell("a1.RJF", "RJF", "a1", "named", "fact", items=items)], hits, ["RJF"])) == []


def test_count_found_in_a_later_document_or_no_later_document_gets_none():
    cells, hits = ms_series(extra_items=[item("15,000", "2026-03-31", "MS-SUPP-2026Q1#7", "advisors")])
    assert notes(matrix(Q23, [SERIES], cells, hits, ["MS"])) == []   # the count moved to 2026Q1 (not old)
    cells, hits = ms_series(extra_items=[item("15,000", "", "MS-SUPP-2026Q1#7", "advisors")])
    assert notes(matrix(Q23, [SERIES], cells, hits, ["MS"])) == []   # an undated count cites a later supplement
    cells, hits = ms_series(later=[])
    assert notes(matrix(Q23, [SERIES], cells, hits, ["MS"])) == []


def test_read_means_the_map_hits_of_the_firms_metric_subquestions():
    # round 2 nb 4: a later supplement only in m.pools, or only under a non-metric sub-question, is not "read"
    cells, hits = ms_series(later=[])
    m = matrix(Q23, [SERIES, Aspect("a2", "Wealth Management client assets.")], cells,
               hits + [hit("MS-SUPP-2026Q2#9", "supplement", "2026-06-30", "a2.MS")], ["MS"])
    m.cells["a2.MS"] = Cell("a2.MS", "MS", "a2", "named", "fact")
    m.pools = {"a1.MS": {"MS-SUPP-2025Q4#7", "MS-SUPP-2020Q4#1"}}
    assert notes(m) == []


def test_unit_filter_for_the_latest_count_and_the_found_since_check():
    # round 2 nb 5: a dated USD or employees item never moves the latest count; a USD item in a later document
    # does not suppress the note
    extra = [item("$538 million", "2026-03-31", "MS-SUPP-2026Q1#7", "USD"),
             item("80,000", "2026-06-30", "MS-SUPP-2026Q2#7", "employees")]
    cells, hits = ms_series(extra_items=extra)
    assert notes(matrix(Q23, [SERIES], cells, hits, ["MS"])) == [MS_NOTE]


def test_count_units_exclude_advisory():
    # PR #265 review nb 2: "advisory assets" is not a count of advisors; advisor and representative units are
    for unit in ("financial advisors", "Wealth Management representatives", "wealth advisors", "advisors",
                 "investment adviser representatives", "employee financial advisors", "advisor"):
        assert mx._counts_metric(item("1,000", "2026-03-31", "X#1", unit)), unit
    for unit in ("advisory assets", "advisory accounts", "employees performing investment advisory functions",
                 "employees", "USD", "client assets"):
        assert not mx._counts_metric(item("1,000", "2026-03-31", "X#1", unit)), unit
    extra = [item("$9 billion", "2026-03-31", "MS-SUPP-2026Q1#7", "advisory assets")]
    cells, hits = ms_series(extra_items=extra)
    assert notes(matrix(Q23, [SERIES], cells, hits, ["MS"])) == [MS_NOTE]


def test_no_count_date_or_no_registered_metric_gets_none():
    items = [item("30,690", "2025-12-31", "SCHW-ADV1A-2026#1", "employees")]
    hits = [hit("SCHW-ADV1A-2026#1", "adv", "2025-12-31", "a1.SCHW"), hit("SCHW-SUPP-2026Q1#1", "adv", "2026-03-31", "a1.SCHW")]
    assert notes(matrix(Q23, [SERIES], [Cell("a1.SCHW", "SCHW", "a1", "named", "different_quantity", items=items)],
                        hits, ["SCHW"])) == []
    cells, hits = ms_series()
    other = Aspect("a1", "Advisor headcount over the last eight quarters.", kind="series")   # no metric
    assert notes(matrix(Q23, [other], cells, hits, ["MS"])) == []


def test_finish_places_the_note_after_the_series_span():
    cells, hits = ms_series()
    m = matrix(Q23, [SERIES], cells, hits, ["MS"])
    mx.finish(m, sources=lambda e: "", as_of=AS_OF)
    assert MS_NOTE in m.caveats
    span = next(i for i, c in enumerate(m.caveats) if "the series in the documents searched runs" in c)
    assert m.caveats.index(MS_NOTE) > span


def test_doc_words_for_decks():
    assert mx.DOC_WORDS["deck"] == "investor presentations"


# --- item 10 ------------------------------------------------------------------------------------------------

TARGET = "RJF-DECK-2025-investor-day#43"


def test_series_pin_only_for_series_aspects():
    ids, cut = planner.pinned_ids("RJF", SERIES)
    assert ids[-1] == TARGET and len(ids) <= planner.PIN_MAX and not cut
    fact = Aspect("a3", "Number of financial advisors.", metric="advisor_headcount")
    assert TARGET not in planner.pinned_ids("RJF", fact)[0]
    assert TARGET not in planner.pinned_ids("MS", SERIES)[0]


def _series_pin_entries():
    data = yaml.safe_load((REPO_ROOT / "config" / "metric_definitions.yaml").read_text(encoding="utf-8"))
    return [d for d in data["definitions"] if d.get("series_pins")]


def test_registry_series_pins_shape():
    entries = _series_pin_entries()
    assert [(d["entity"], d["metric"], d["series_pins"]) for d in entries] == [("RJF", "advisor_headcount", [TARGET])]
    manifest = MANIFEST_PATH.read_text(encoding="utf-8")
    for d in entries:
        assert not set(d["series_pins"]) & set(d.get("see_also") or [])
        for cid in d["series_pins"]:
            assert cid.split("#")[0] in manifest


DATE = re.compile(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}\b"
                  r"|\b\d{4}-\d{2}-\d{2}\b|\b[1-4]Q\d{2}\b|\b\d{4}\s?Q[1-4]\b")


def test_date_pattern_accepts_month_abbreviations_with_a_dot():
    for s in ("Mar. 31, 2025", "March 31, 2025", "Sept. 30, 2025", "2025-03-31", "3Q25", "2025Q1"):
        assert DATE.search(s), s
    assert not DATE.search("8,731 PCG advisors")


def test_series_pins_are_undated_documents_stating_a_dated_count():
    ids = [cid for d in _series_pin_entries() for cid in d["series_pins"]]
    try:
        with psycopg.connect(settings().database_url, connect_timeout=3) as conn:
            rows = {r[0]: r[1:] for r in conn.execute(
                "SELECT c.chunk_id, c.text, d.period_end, d.source_tier FROM chunks c JOIN documents d USING (doc_id) "
                "WHERE c.chunk_id = ANY(%s)", (ids,)).fetchall()}
    except psycopg.OperationalError:
        pytest.skip("database not running")
    if not rows:
        pytest.skip("no corpus loaded")
    assert set(ids) == rows.keys()
    for cid, (text, period_end, tier) in rows.items():
        flat = re.sub(r"\s+", " ", text)
        assert period_end is None and 1 <= tier <= 3, cid
        assert DATE.search(flat) and re.search(r"\d[\d,]{2,}", flat), cid
    flat = re.sub(r"\s+", " ", rows[TARGET][0])
    assert "8,731" in flat and "Mar. 31, 2025" in flat
