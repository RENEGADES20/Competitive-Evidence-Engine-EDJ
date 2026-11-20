"""#248: the dollar cost of each call (cee.answer.cost), 0 calls. Fixed zones only: no test depends on
the zone of the machine (or CI) that runs it."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest

from cee.answer import cost as C

REPO = Path(__file__).resolve().parents[1]
U = dt.timezone.utc
DS = {"input_tokens": 1_000_000, "output_tokens": 1_000_000, "cache_hit_tokens": 0, "cache_miss_tokens": 1_000_000}


def ds_entry():
    return C.load_prices()["providers"]["deepseek"]


@pytest.mark.parametrize("hhmm,peak", [("00:59", False), ("01:00", True), ("03:59", True), ("04:00", False),
                                       ("05:59", False), ("06:00", True), ("09:59", True), ("10:00", False)])
def test_peak_window_edges_on_a_weekday(hhmm, peak):
    h, m = map(int, hhmm.split(":"))
    assert C.is_peak(dt.datetime(2026, 11, 20, h, m, tzinfo=U), ds_entry()) is peak   # a Friday


def test_weekend_and_listed_holiday_are_off_peak():
    e = ds_entry()
    assert not C.is_peak(dt.datetime(2026, 11, 21, 2, 0, tzinfo=U), e)          # Saturday
    assert C.is_peak(dt.datetime(2026, 11, 20, 2, 0, tzinfo=U), e)
    assert not C.is_peak(dt.datetime(2026, 11, 20, 2, 0, tzinfo=U), {**e, "holidays": ["2026-11-20"]})


def test_completion_time_decides_across_six_utc():
    # starts 05:59:30 UTC (off-peak), ends 06:00:30 (peak): priced peak, like #243's Q26
    r = C.price_call("deepseek", "deepseek-v4-pro", DS, at="2026-11-20T05:59:30+00:00", wall_s=60)
    assert r["period"] == "peak" and r["usd"] == pytest.approx(1.32 + 3.96)
    r = C.price_call("deepseek", "deepseek-v4-pro", DS, at="2026-11-20T05:58:00+00:00", wall_s=60)
    assert r["period"] == "off_peak" and r["usd"] == pytest.approx(0.66 + 1.98) and r["usd_peak"] == pytest.approx(5.28)


def test_finished_at_form_and_its_offset_wins_over_naive_tz():
    r = C.price_call("deepseek", "deepseek-v4-pro", DS, finished_at="2026-11-19T21:30:00-06:00", naive_tz="+00:00")
    assert r["period"] == "peak" and r["tz"] == "record offset" and r["finished_utc"].startswith("2026-11-20T03:30")


def test_naive_time_needs_an_explicit_zone_and_the_zone_matters():
    with pytest.raises(C.CostError, match="naive-tz"):
        C.price_call("deepseek", "deepseek-v4-pro", DS, at="2026-11-19T21:35:00", wall_s=10)
    chicago = C.price_call("deepseek", "deepseek-v4-pro", DS, at="2026-11-19T21:35:00", wall_s=10, naive_tz="-06:00")
    utc = C.price_call("deepseek", "deepseek-v4-pro", DS, at="2026-11-19T21:35:00", wall_s=10, naive_tz="UTC")
    assert chicago["period"] == "peak" and chicago["tz"] == "--naive-tz -06:00"
    assert utc["period"] == "off_peak"


def test_split_and_no_split_input():
    u = {"input_tokens": 1_000_000, "output_tokens": 0, "cache_hit_tokens": 400_000, "cache_miss_tokens": 600_000}
    r = C.price_call("deepseek", "deepseek-v4-pro", u, at="2026-11-20T02:00:00+00:00")
    assert r["usd"] == pytest.approx(0.4 * 0.044 + 0.6 * 1.32)
    r = C.price_call("deepseek", "deepseek-v4-pro", {"input_tokens": 1_000_000, "output_tokens": 0},
                     at="2026-11-20T02:00:00+00:00")
    assert r["usd"] == pytest.approx(1.32)   # no split: all input is a miss


def test_anthropic_flat_with_cache_read_and_write():
    u = {"input_tokens": 1_000_000, "output_tokens": 100_000, "cache_read_input_tokens": 2_000_000,
         "cache_creation_input_tokens": 400_000}
    r = C.price_call("anthropic", "claude-sonnet-5-5", u, at="2026-11-20T02:00:00")   # naive: no zone needed
    assert r["period"] == "flat" and r["usd"] == pytest.approx(2.0 + 1.0 + 0.2 + 1.0)
    assert r["input_tokens"] == 3_400_000 and r["cache_hit_tokens"] == 2_000_000


def test_unpriced_failed_and_mock():
    assert C.price_call("openai", "gpt-5", DS)["status"] == "unpriced"
    assert C.price_call("openai", "gpt-5", DS)["usd"] is None
    assert C.price_call("deepseek", "deepseek-v4-pro", None)["status"] == "no_usage"
    assert C.price_call("mock", "mock", None)["usd"] == 0.0


def test_unknown_zone_is_a_clear_error():
    with pytest.raises(C.CostError, match="fixed offset"):
        C.parse_tz("Not/AZone")


def test_summarize_counts_new_reused_and_types():
    p = C.price_call("deepseek", "deepseek-v4-pro", DS, at="2026-11-20T02:00:00+00:00")
    o = C.price_call("deepseek", "deepseek-v4-pro", DS, at="2026-11-20T05:00:00+00:00")
    s = C.summarize([{"type": "plan", "new": False, "cost": p}, {"type": "map", "new": True, "cost": o},
                     {"type": "reduce", "new": True, "cost": C.price_call("deepseek", "deepseek-v4-pro", None)}])
    assert s["calls"] == 3 and s["new"] == 2 and s["reused"] == 1 and s["by_type"]["map"] == 1
    assert s["usd"] == pytest.approx(5.28 + 2.64) and s["usd_new"] == pytest.approx(2.64)
    assert s["peak_calls"] == 1 and s["off_peak_calls"] == 1 and s["no_usage_calls"] == 1


def test_the_0242_records_cost_79_cents_all_at_peak():
    # TL comment on #248: $0.79 at full price for #242's 12 check calls ($0.27 off, $0.52 on). The
    # records' naive `at` was written in America/Chicago (UTC-6 in November): every call is peak.
    totals = {}
    for mode in ("off", "on"):
        rows = []
        for f in sorted((REPO / "docs/results/0242-deepseek-raw" / mode).glob("*.json")):
            rec = json.loads(f.read_text(encoding="utf-8"))
            rows.append({"type": "plan", "new": True, "cost": C.price_call(
                rec["provider"], rec["model"], rec["usage"], at=rec["at"], wall_s=rec.get("wall_s"),
                naive_tz="-06:00")})
        totals[mode] = C.summarize(rows)
    assert totals["off"]["calls"] == totals["on"]["calls"] == 6
    assert round(totals["off"]["usd_peak"], 2) == 0.27 and round(totals["on"]["usd_peak"], 2) == 0.52
    assert round(totals["off"]["usd_peak"] + totals["on"]["usd_peak"], 2) == 0.79
    assert totals["off"]["peak_calls"] + totals["on"]["peak_calls"] == 12
    assert round(totals["off"]["usd"] + totals["on"]["usd"], 2) == 0.79


def test_eval_cost_script_needs_the_zone_of_naive_records(tmp_path, capsys):
    import importlib.util
    spec = importlib.util.spec_from_file_location("eval_cost", REPO / "scripts" / "eval_cost.py")
    ec = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ec)
    folder = REPO / "docs/results/0242-deepseek-raw"
    assert ec.main([str(folder)]) == 2 and "naive-tz" in capsys.readouterr().err
    assert ec.main([str(folder), "--naive-tz=-06:00", "--json", str(tmp_path / "c.json")]) == 0
    total = json.loads((tmp_path / "c.json").read_text(encoding="utf-8"))["total"]
    assert total["calls"] == 12 and round(total["usd"], 2) == 0.79 and total["peak_calls"] == 12
