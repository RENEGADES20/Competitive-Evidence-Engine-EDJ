"""Dollar cost of each model call, from the price table in config/pricing.yaml (#248, ADR-021 rule 7).

Pure code, 0 calls. A call is priced from its saved `usage` and its completion time:
- deepseek: cache-hit input x hit rate + cache-miss input x miss rate + output x output rate
  (reasoning tokens are part of the output); without a hit / miss split all input is a miss.
  Peak or off-peak by completion time in UTC (the rule #243 used).
- anthropic: uncached input x input + cache read x read + cache write x write + output x output; flat.
- a provider / model not in the table: `unpriced` (usd None), never $0. The mock: $0.
- a call without usage (a failed call): `no_usage` (usd None); it still counts as a call.

Time zone: a time with a UTC offset is read in that offset. A naive time (every record written before
#248) needs an explicit zone, `naive_tz` (an IANA name such as "America/Chicago" or a fixed offset such
as "-06:00"); pricing never depends on the zone of the machine that prices.
"""
from __future__ import annotations

import datetime as dt
import re
from functools import lru_cache
from pathlib import Path

import yaml

from cee.config import REPO_ROOT

PRICING_PATH = REPO_ROOT / "config" / "pricing.yaml"
OFFSET = re.compile(r"^(?:UTC)?([+-])(\d{1,2}):?(\d{2})$")


class CostError(ValueError):
    """A price cannot be computed as asked (no zone for a naive time, an unknown zone)."""


@lru_cache(maxsize=4)
def load_prices(path: Path | str | None = None) -> dict:
    return yaml.safe_load(Path(path or PRICING_PATH).read_text(encoding="utf-8")) or {}


def parse_tz(spec: str | None) -> dt.tzinfo | None:
    """A zone from 'UTC', a fixed offset ('-06:00', '+0800', 'UTC-06:00') or an IANA name."""
    if spec is None or str(spec).strip() == "":
        return None
    s = str(spec).strip()
    if s.upper() in ("UTC", "Z", "+00:00", "-00:00"):
        return dt.timezone.utc
    m = OFFSET.match(s)
    if m:
        sign = 1 if m.group(1) == "+" else -1
        return dt.timezone(sign * dt.timedelta(hours=int(m.group(2)), minutes=int(m.group(3))))
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
    try:
        return ZoneInfo(s)
    except (ZoneInfoNotFoundError, ValueError) as e:
        raise CostError(f"time zone {s!r} not found (no tz database on this machine? `pip install tzdata`, "
                        f"or pass a fixed offset such as -06:00)") from e


def is_naive(text: str | None) -> bool:
    """True when a saved ISO time has no UTC offset."""
    if not text:
        return False
    try:
        return dt.datetime.fromisoformat(str(text)).tzinfo is None
    except ValueError:
        return False


def completion_time(at=None, wall_s=None, finished_at=None, naive_tz: str | None = None
                    ) -> tuple[dt.datetime | None, str | None]:
    """(completion time in UTC, how its zone was known): `finished_at`, else `at` + `wall_s`, else `at`.
    A naive time without `naive_tz` raises CostError."""
    text, add = (finished_at, 0.0) if finished_at else (at, float(wall_s or 0))
    if not text:
        return None, None
    t = dt.datetime.fromisoformat(str(text))
    if t.tzinfo is None:
        tz = parse_tz(naive_tz)
        if tz is None:
            raise CostError(f"naive time {text} (no UTC offset): pass the zone it was written in "
                            f"(--naive-tz, e.g. America/Chicago or -06:00)")
        t, how = t.replace(tzinfo=tz), f"--naive-tz {naive_tz}"
    else:
        how = "record offset"
    return (t + dt.timedelta(seconds=add)).astimezone(dt.timezone.utc), how


def _minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def is_peak(t_utc: dt.datetime, entry: dict) -> bool:
    """Peak: a listed weekday (UTC), not a listed holiday, inside a [start, end) UTC window."""
    t = t_utc.astimezone(dt.timezone.utc)
    if t.weekday() not in entry.get("peak_weekdays", [0, 1, 2, 3, 4]):
        return False
    if t.date().isoformat() in {str(d) for d in entry.get("holidays") or []}:
        return False
    now = t.hour * 60 + t.minute
    return any(_minutes(a) <= now < _minutes(b) for a, b in entry.get("peak_utc") or [])


def _n(usage: dict, key: str) -> int:
    v = usage.get(key)
    return int(v) if isinstance(v, (int, float)) else 0


def tokens(usage: dict | None) -> dict:
    u = usage or {}
    hit, miss = u.get("cache_hit_tokens"), u.get("cache_miss_tokens")
    if hit is None and miss is None:
        hit = _n(u, "cache_read_input_tokens")
        miss = _n(u, "input_tokens")
    return {"input_tokens": _n(u, "input_tokens") + _n(u, "cache_read_input_tokens")
            + _n(u, "cache_creation_input_tokens"),
            "output_tokens": _n(u, "output_tokens"), "cache_hit_tokens": int(hit or 0),
            "cache_miss_tokens": int(miss or 0), "cache_write_tokens": _n(u, "cache_creation_input_tokens"),
            "reasoning_tokens": _n(u, "reasoning_tokens")}


def price_call(provider: str, model: str | None, usage: dict | None, at=None, wall_s=None, finished_at=None,
               naive_tz: str | None = None, prices: dict | None = None) -> dict:
    """The cost of one call: status priced | unpriced | no_usage; usd (None unless priced); usd_peak
    (the same call at peak); period peak | off_peak | flat; tz (how the zone was known); finished_utc."""
    out = {"provider": provider, "model": model, **tokens(usage), "usd": None, "usd_peak": None,
           "period": None, "tz": None, "finished_utc": None, "status": "priced"}
    if provider == "mock":
        return {**out, "usd": 0.0, "usd_peak": 0.0, "period": "flat"}
    if not usage or (usage.get("input_tokens") is None and usage.get("output_tokens") is None):
        return {**out, "status": "no_usage"}
    table = (prices or load_prices()).get("providers") or {}
    entry = table.get(provider) or {}
    rates = (entry.get("models") or {}).get(model or "")
    if not rates:
        return {**out, "status": "unpriced"}
    tk = out
    if "flat" in rates:
        r = rates["flat"]
        usd = (tk["cache_miss_tokens"] * r.get("input", 0) + tk["cache_hit_tokens"] * r.get("cache_read", 0)
               + tk["cache_write_tokens"] * r.get("cache_write", 0) + tk["output_tokens"] * r.get("output", 0)) / 1e6
        try:   # a flat price needs no time; it is recorded when known (a naive one without a zone is not)
            t, how = completion_time(at, wall_s, finished_at, naive_tz)
        except CostError:
            t, how = None, None
        return {**out, "usd": round(usd, 6), "usd_peak": round(usd, 6), "period": "flat", "tz": how,
                "finished_utc": t.isoformat() if t else None}

    def at_rate(r: dict) -> float:
        return (tk["cache_hit_tokens"] * r["input_cache_hit"] + tk["cache_miss_tokens"] * r["input_cache_miss"]
                + tk["output_tokens"] * r["output"]) / 1e6

    t, how = completion_time(at, wall_s, finished_at, naive_tz)
    peak_usd = at_rate(rates["peak"])
    if t is None:   # no time recorded: priced at peak (the dearer rate), period unknown
        return {**out, "usd": round(peak_usd, 6), "usd_peak": round(peak_usd, 6), "period": "unknown"}
    peak = is_peak(t, entry)
    usd = peak_usd if peak else at_rate(rates["off_peak"])
    return {**out, "usd": round(usd, 6), "usd_peak": round(peak_usd, 6),
            "period": "peak" if peak else "off_peak", "tz": how, "finished_utc": t.isoformat()}


def needs_time(provider: str, prices: dict | None = None) -> bool:
    """True when the provider's price depends on the time of day (a peak window)."""
    return bool(((prices or load_prices()).get("providers") or {}).get(provider, {}).get("peak_utc"))


CALL_TYPES = ("plan", "map", "remap", "reduce", "answer")


def summarize(rows: list[dict]) -> dict:
    """Totals of ledger rows ({type, new, cost: price_call(...)}): calls by type, new / reused, tokens,
    usd (priced calls), usd_new (new calls), usd_peak, peak / off-peak, unpriced and no-usage calls."""
    def total(key, rs):
        return round(sum(r["cost"][key] or 0 for r in rs if r["cost"].get(key) is not None), 6)

    priced = [r for r in rows if r["cost"]["status"] == "priced"]
    out = {"calls": len(rows), "by_type": {t: sum(r["type"] == t for r in rows) for t in CALL_TYPES},
           "new": sum(bool(r.get("new")) for r in rows), "reused": sum(not r.get("new") for r in rows)}
    for k in ("input_tokens", "output_tokens", "cache_hit_tokens", "cache_miss_tokens", "cache_write_tokens",
              "reasoning_tokens"):
        out[k] = sum(r["cost"].get(k) or 0 for r in rows)
    out |= {"usd": total("usd", priced), "usd_new": total("usd", [r for r in priced if r.get("new")]),
            "usd_peak": total("usd_peak", priced),
            "peak_calls": sum(r["cost"]["period"] == "peak" for r in rows),
            "off_peak_calls": sum(r["cost"]["period"] == "off_peak" for r in rows),
            "unpriced_calls": sum(r["cost"]["status"] == "unpriced" for r in rows),
            "no_usage_calls": sum(r["cost"]["status"] == "no_usage" for r in rows)}
    return out
