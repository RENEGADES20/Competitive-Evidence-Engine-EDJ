from cee.app.views import coverage_page as cp


def test_states():
    assert [cp.cell_state(n) for n in (0, 1, 2)] == ["empty", "thin", "covered"]


def test_grid_counts_dates_and_not_tracked():
    docs = [{"entity_id": "EDJ", "doc_type": "10-K", "n": 1, "first": "2026-03-13", "last": "2026-03-13"},
            {"entity_id": "BAC", "doc_type": "10-Q", "n": 4, "first": "2025-07-31", "last": "2026-07-31"},
            {"entity_id": "LPLA", "doc_type": "10-K", "n": 9, "first": "2026-01-01", "last": "2026-01-02"}]
    expected = [{"entity_id": "EDJ", "doc_type": "10-K"}, {"entity_id": "EDJ", "doc_type": "adv"},
                {"entity_id": "BAC", "doc_type": "10-Q"}, {"entity_id": "LPLA", "doc_type": "10-K"}]
    cols, rows = cp.build_grid(docs, expected)
    by = {label: dict(zip(cols, cells)) for label, _, cells in rows}
    assert cols == ["10-K", "10-Q", "adv"]
    assert by["EDJ"]["10-K"] == ("thin", "1 doc\n2026-03-13")
    assert by["EDJ"]["adv"] == ("empty", "0 docs")
    assert by["EDJ"]["10-Q"] is None
    assert by["BAC filings"]["10-Q"] == ("covered", "4 docs\n2025-07-31\nto 2026-07-31")
    assert all("LPLA" not in label for label in by)
