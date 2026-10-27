from cee.app.views import coverage_page as cp

ENTITIES = [{"id": "EDJ", "name": "Edward Jones"},
            {"id": "BAC", "name": "Bank of America Corporation"},
            {"id": "MER", "name": "Merrill", "parent": "BAC", "reported_as": "GWIM"}]


def test_states_follow_the_expected_cadence():
    assert [cp.cell_state(n, "annual") for n in (0, 1, 2)] == ["empty", "covered", "covered"]
    assert [cp.cell_state(n, "quarterly") for n in (0, 3, 4)] == ["empty", "thin", "covered"]
    assert [cp.cell_state(n, "event-driven") for n in (1, 2)] == ["thin", "covered"]


def test_rows_come_from_config():
    rows = cp.rows_from_config(ENTITIES)
    assert [r[0] for r in rows] == ["EDJ", "BAC", "MER"]
    assert "parent of Merrill" in rows[1][2]
    assert "BAC chunks tagged GWIM" in rows[2][2]


def test_grid_counts_dates_and_not_tracked():
    docs = [{"entity_id": "EDJ", "doc_type": "10-K", "n": 1, "first": "2026-03-13", "last": "2026-03-13"},
            {"entity_id": "BAC", "doc_type": "10-Q", "n": 4, "first": "2025-07-31", "last": "2026-07-31"},
            {"entity_id": "BAC", "doc_type": "transcript", "n": 3, "first": "2026-01-14", "last": "2026-07-14"},
            {"entity_id": "LPLA", "doc_type": "10-K", "n": 9, "first": "2026-01-01", "last": "2026-01-02"}]
    expected = [{"entity_id": "EDJ", "doc_type": "10-K", "expected_cadence": "annual"},
                {"entity_id": "EDJ", "doc_type": "adv", "expected_cadence": "annual amendment"},
                {"entity_id": "BAC", "doc_type": "10-Q", "expected_cadence": "quarterly"},
                {"entity_id": "BAC", "doc_type": "transcript", "expected_cadence": "quarterly"},
                {"entity_id": "LPLA", "doc_type": "10-K", "expected_cadence": "annual"}]
    cols, rows = cp.build_grid(docs, expected, cp.rows_from_config(ENTITIES), {"MER": 12})
    by = {label: dict(zip(cols, cells)) for label, _, cells in rows}
    notes = {label: note for label, note, _ in rows}
    assert cols == ["10-K", "10-Q", "transcript", "adv"]
    assert by["EDJ"]["10-K"] == ("covered", "1 doc\n2026-03-13")
    assert by["EDJ"]["adv"] == ("empty", "0 docs")
    assert by["EDJ"]["10-Q"] is None
    assert by["BAC"]["10-Q"] == ("covered", "4 docs\n2025-07-31\nto 2026-07-31")
    assert by["BAC"]["transcript"][0] == "thin"
    assert notes["MER"].endswith(": 12 chunks")
    assert "LPLA" not in by
