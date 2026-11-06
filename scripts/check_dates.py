"""Check every C2 document's published_at against what the stored file prints (#58).

Offline: reads data/manifest.csv and the raw files (cee.config.resolve_path); rows with doc_type
transcript, press or deck. No network, no database. Writes a Markdown report to stdout and --out.

  python scripts/check_dates.py --today 2026-11-03 --out docs/C2_DATES.md
  python scripts/check_dates.py --manifest other.csv --skip-missing

Where the date comes from (the "date source" column):
  page       printed in the document (deck page 1 or "as of" in pages 1-10, press dateline,
             RJF date before FOR IMMEDIATE RELEASE)
  metadata   PDF creationDate 0-1 day before published_at (no printed date)
  header     line our converter wrote (transcript line 1, MER newsroom line 2): weak on its own;
             "header + URL" / "header + page" when the URL date or the S&P footer agrees,
             "header + cross-check" when the same quarter's deck or press release prints it
  cross-check  nothing printed (BAC press, slide images): a same-entity, same-period deck or
             transcript prints the date
  retrieved  undated web page: "Content as of" plus the ADR-007 T-09 date-check line
Fails (exit 1): MISMATCH, IMPLAUSIBLE, UNDATED, BASIS. WARN (> 120 days after period_end) does not
fail. A missing raw file is NO FILE: exit 2 unless --skip-missing. Allowed exceptions go in NOTES,
keyed (doc_id, rule) with rule one of the codes in RULES; a note turns exactly that rule into
"OK (note: ...)".
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import re
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

SCOPE = {"transcript", "press", "deck"}
MIN_DATE = dt.date(2015, 1, 1)
LATE_DAYS = 120
RULES = {  # code -> verdict label
    "MISMATCH": "MISMATCH", "BEFORE_2015": "IMPLAUSIBLE", "AFTER_ADDED": "IMPLAUSIBLE",
    "AFTER_TODAY": "IMPLAUSIBLE", "BEFORE_PERIOD": "IMPLAUSIBLE", "UNDATED": "UNDATED",
    "BASIS": "BASIS", "PRINTED": "BASIS", "LATE": "WARN"}
NOTES: dict[tuple[str, str], str] = {}  # (doc_id, rule code) -> why this is fine; empty today

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
DATE_RE = r"((?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*)\.?\s+(\d{1,2}),\s+(\d{4})"
ISO_RE = r"(\d{4}-\d{2}-\d{2})"
T09 = "Date check (ADR-007 T-09):"
MARKETBEAT_RE = r"marketbeat\.com/earnings/reports/(\d{4})-(\d{1,2})-(\d{1,2})-"
FOOTER_RE = r"Earnings Call, " + DATE_RE  # S&P: "<Company>, Q1 2026 Earnings Call, Apr 15, 2026"


def to_date(month: str, day: str, year: str) -> dt.date | None:
    try:
        return dt.date(int(year), MONTHS[month[:3].lower()], int(day))
    except (KeyError, ValueError):
        return None


def find_dates(text: str, pattern: str = DATE_RE) -> list[tuple[dt.date, str]]:
    """(date, matched text) for every "Month D, YYYY" in text, case-insensitive."""
    out = []
    for m in re.finditer(pattern, text, re.I):
        d = to_date(*m.groups()[-3:])
        if d:
            out.append((d, " ".join(m.group(0).split())))
    return out


def result(date=None, source="", evidence="", weak=False, others=(), conflict=""):
    """One detection: the date, where it came from, other dates that must agree, any other disagreement."""
    return {"date": date, "source": source, "evidence": evidence, "weak": weak, "others": list(others),
            "conflict": conflict}


# ---- detectors (pure: strings in, result out) ----

def detect_deck(pages: list[str], meta_date: dt.date | None, published: dt.date) -> dict:
    """Page 1 date; else "as of <date>" in pages 1-10; else PDF creationDate 0-1 day before."""
    if pages and (hits := find_dates(pages[0])):
        return result(hits[0][0], "page", f"p1 '{hits[0][1]}'")
    first10 = pages[:10]
    for pat in (r"speaks only as of\s+" + DATE_RE, r"as of\s+" + DATE_RE, DATE_RE):
        for i, text in enumerate(first10, 1):
            if hits := find_dates(text, pat):
                return result(hits[0][0], "page", f"p{i} '{hits[0][1]}'")
    if meta_date and 0 <= (published - meta_date).days <= 1:
        return result(published, "metadata", f"none printed p1-10; PDF creationDate {meta_date}")
    return result(evidence=f"none printed p1-10; PDF creationDate {meta_date or 'none'}")


def detect_press_html(text: str) -> dict:
    """Dateline ("NEW YORK, January 15, 2026 -") or RJF date before FOR IMMEDIATE RELEASE."""
    text = " ".join(text.split())
    if m := re.search(r"([A-Z]{2,}(?: [A-Z]{2,})*(?:, [A-Z][A-Za-z.]+)?),\s+(?i:" + DATE_RE + r")\s*[\u2013\u2014-]",
                      text[:5000]):
        return result(to_date(*m.groups()[1:]), "page", f"dateline '{m.group(0)}'")
    i = text.find("FOR IMMEDIATE RELEASE")
    if i >= 0 and (hits := find_dates(text[max(0, i - 200):i])):
        return result(hits[-1][0], "page", f"'{hits[-1][1]}' before FOR IMMEDIATE RELEASE")
    return result(evidence="none printed")


def detect_transcript(text: str, url: str) -> dict:
    """Line 1 "<Company> - <call> - YYYY-MM-DD" (our converter: weak) confirmed by URL or S&P footer."""
    lines = text.splitlines()
    m = re.search(r" - " + ISO_RE + r"\s*$", lines[0]) if lines else None
    header = dt.date.fromisoformat(m.group(1)) if m else None
    url_m = re.search(MARKETBEAT_RE, url or "")
    url_date = dt.date(*map(int, url_m.groups())) if url_m else None
    footer = find_dates(text, FOOTER_RE)
    footer_date = footer[0][0] if footer else None
    others = [d for d in (url_date, footer_date) if d]
    if not header:
        if footer_date:
            return result(footer_date, "page", f"S&P footer '{footer[0][1]}'", others=others)
        return result(url_date, "URL" if url_date else "", "no header date", weak=True, others=others)
    ev = [f"line 1 {header}"]
    if url_date:
        ev.append(f"URL {url_date}")
    if footer_date:
        ev.append(f"S&P footer '{footer[0][1]}'")
    if url_date == header:
        return result(header, "header + URL", "; ".join(ev), others=others)
    if footer_date == header:
        return result(header, "header + page", "; ".join(ev), others=others)
    return result(header, "header", "; ".join(ev), weak=True, others=others)


def detect_newsroom(text: str, url: str) -> dict:
    """MER newsroom .txt: line 2 "<X> press release - YYYY-MM-DD"; the URL /YYYY/MM/ checks the month only."""
    lines = text.splitlines()
    m = re.search(r"press release - " + ISO_RE, lines[1]) if len(lines) > 1 else None
    if not m:
        return result(evidence="no line-2 date")
    d = dt.date.fromisoformat(m.group(1))
    ev = f"line 2 {d}"
    if u := re.search(r"/(\d{4})/(\d{2})/", url or ""):
        agrees = (int(u.group(1)), int(u.group(2))) == (d.year, d.month)
        ev += f"; URL month {u.group(1)}/{u.group(2)} {'agrees' if agrees else 'DISAGREES'} (month only)"
        if not agrees:
            return result(d, "header", ev, weak=True, conflict=f"URL month {u.group(1)}/{u.group(2)}")
    return result(d, "header", ev, weak=True)


def parse_undated(text: str) -> dict | None:
    """The 5-line undated-page header (convert_undated_web.py); None when the file has none."""
    lines = text.splitlines()[:6]
    if not any(l.startswith("Content as of:") or l.startswith(T09) for l in lines):
        return None
    get = lambda pat: next((m.group(1) for l in lines if (m := re.search(pat, l))), None)
    t09 = next((l for l in lines if l.startswith(T09)), None)
    out = {"content_as_of": get(r"^Content as of: " + ISO_RE),
           "line2": get(r"content as of " + ISO_RE + r"\s*$"), "t09": t09, "printed": None}
    if t09:
        p = re.search(r"printed(?: date)? ([^;]+);", t09)
        out["printed"] = None if not p or p.group(1).strip() == "none" else p.group(1).strip()
        out["metadata"] = get(r"metadata ([^;]+);")
        out["last_modified"] = get(r"Last-Modified ([^;]+);")
        out["wayback"] = get(r"earliest Wayback capture " + ISO_RE)
    body = "\n".join(text.splitlines()[6:])
    # A page-level "Last updated: <date>"; "(Published on <date>. ...)" cites someone else's list.
    if not out["printed"] and (hits := find_dates(
            body, r"(?<!\()\b(?:last updated|updated|published|posted)\s*(?:on|:)?\s*" + DATE_RE)):
        out["printed"] = hits[0][1]
    return out


def detect_retrieved(h: dict | None) -> tuple[dict, list[tuple[str, str]]]:
    """Retrieved row: the header date plus problems (code, text): PRINTED for a date printed on the
    page, BASIS for a header that breaks the contract or names an earlier T-09 source."""
    if h is None:
        return result(evidence="no undated-page header"), [("BASIS", "no undated-page header / T-09 line")]
    problems = []
    if not h["t09"]:
        problems.append(("BASIS", "no T-09 line"))
    else:
        for step in ("metadata", "last_modified"):
            if (h.get(step) or "none") != "none":
                problems.append(("BASIS", f"T-09 {step.replace('_', '-')} {h[step]} comes before the retrieved date"))
        if not h.get("wayback"):
            problems.append(("BASIS", "T-09 line names no earliest Wayback capture"))
    if h["printed"]:
        problems.append(("PRINTED", f"printed date found '{h['printed']}'"))
    if not h["line2"]:
        problems.append(("BASIS", "no '... content as of <date>' line 2"))
    elif h["line2"] != h["content_as_of"]:
        problems.append(("BASIS", f"line 2 {h['line2']} != Content as of {h['content_as_of']}"))
    if not h["content_as_of"]:
        problems.append(("BASIS", "no 'Content as of' line"))
    d = dt.date.fromisoformat(h["content_as_of"]) if h["content_as_of"] else None
    ev = f"Content as of {d}"
    if h["t09"]:
        ev += (f"; T-09: printed {h['printed'] or 'none'}, metadata {h['metadata'] or 'none'},"
               f" Last-Modified {h['last_modified'] or 'none'}, Wayback first {h['wayback'] or 'none'}")
    return result(d, "retrieved", ev), problems


def detect(row: dict, texts: list[str], meta_date: dt.date | None) -> tuple[dict, list[tuple[str, str]]]:
    """Pick the detector for a row; texts = PDF pages or [file text]. Returns (result, problems)."""
    sp = row["storage_path"].lower()
    head = parse_undated(texts[0]) if texts and not sp.endswith(".pdf") else None
    if row.get("date_basis") == "retrieved":
        r, problems = detect_retrieved(head)
        if r["date"] and r["date"] != pub(row):
            problems.append(("BASIS", f"header date {r['date']} != published_at"))
        return r, problems
    if head is not None:
        return result(evidence="file has the undated-page header"), [("BASIS", "source-dated row, undated-page header")]
    if sp.endswith(".pdf"):
        return detect_deck(texts, meta_date, pub(row)), []
    if row["doc_type"] == "transcript":
        return detect_transcript(texts[0], row.get("url", "")), []
    if sp.endswith(".txt"):
        return detect_newsroom(texts[0], row.get("url", "")), []
    return detect_press_html(texts[0]), []


def cross_check(row: dict, results: dict[str, dict], rows: list[dict]) -> dict | None:
    """Nothing printed: a same entity + period_end deck/transcript whose own date equals published_at."""
    if not row.get("period_end"):
        return None
    sibs = [s for s in rows if s["doc_id"] != row["doc_id"] and s["entity_id"] == row["entity_id"]
            and s["period_end"] == row["period_end"] and s["doc_type"] in ("deck", "transcript")]
    sibs.sort(key=lambda s: (results.get(s["doc_id"], {}).get("weak", True), s["doc_type"] != "deck"))
    dated = [(s, results[s["doc_id"]]) for s in sibs if results.get(s["doc_id"], {}).get("date")]
    # Prefer a sibling that agrees; otherwise return the best one, so judge() says MISMATCH, not UNDATED.
    for s, r in sorted(dated, key=lambda sr: sr[1]["date"] != pub(row)):
        where = r["evidence"].split(" '")[0] if r["source"] == "page" else r["source"]
        return result(r["date"], "cross-check", f"none printed; {s['doc_id']} {where} {r['date']}",
                      weak=r["weak"])
    return None


def corroborate(row: dict, r: dict, results: dict[str, dict], rows: list[dict]) -> dict:
    """A weak header date that a same entity + period_end deck or press release prints too."""
    for s in rows:
        o = results.get(s["doc_id"])
        if (s["doc_id"] != row["doc_id"] and s["entity_id"] == row["entity_id"] and row.get("period_end")
                and s["period_end"] == row["period_end"] and s["doc_type"] in ("deck", "press")
                and o and o["source"] == "page" and not o["weak"] and o["date"] == r["date"]):
            return {**r, "source": f"{r['source']} + cross-check", "weak": False,
                    "evidence": f"{r['evidence']}; {s['doc_id']} {o['evidence'].split(' ')[0]} {o['date']}"}
    return r


def pub(row: dict) -> dt.date:
    return dt.date.fromisoformat(row["published_at"])


def judge(row: dict, r: dict, problems: list[tuple[str, str]], today: dt.date) -> str:
    """Verdict text for one row (rules -> labels; NOTES downgrade exactly their rule)."""
    p = pub(row)
    hits = []  # (code, detail)
    if problems:  # a basis problem says it all: no second MISMATCH/UNDATED for the same date
        for code in dict.fromkeys(c for c, _ in problems):
            hits.append((code, "; ".join(t for c, t in problems if c == code)))
    elif r["date"] is None:
        hits.append(("UNDATED", "nothing printed"))
    elif r["date"] != p or any(o != p for o in r["others"]):
        found = ", ".join(sorted({str(d) for d in [r["date"], *r["others"]] if d != p}))
        hits.append(("MISMATCH", f"file says {found}"))
    elif r.get("conflict"):
        hits.append(("MISMATCH", r["conflict"]))
    if p < MIN_DATE:
        hits.append(("BEFORE_2015", "before 2015"))
    if row.get("added_at") and p > dt.date.fromisoformat(row["added_at"]):
        hits.append(("AFTER_ADDED", f"after added_at {row['added_at']}"))
    if p > today:
        hits.append(("AFTER_TODAY", f"after today {today}"))
    if row.get("period_end"):
        pe = dt.date.fromisoformat(row["period_end"])
        if p < pe:
            hits.append(("BEFORE_PERIOD", f"before period_end {pe}"))
        elif (p - pe).days > LATE_DAYS:
            hits.append(("LATE", f"{(p - pe).days} days after period_end"))
    noted = [NOTES[(row["doc_id"], c)] for c, _ in hits if (row["doc_id"], c) in NOTES]
    left = [(c, d) for c, d in hits if (row["doc_id"], c) not in NOTES]
    fails = [f"{RULES[c]} ({d})" for c, d in left if c != "LATE"]
    if fails:
        return "; ".join(fails)
    if left:
        return f"WARN ({left[0][1]})"
    if noted:
        return f"OK (note: {'; '.join(noted)})"
    if r["source"] == "cross-check" and not r["weak"]:
        return "OK (cross-check)"
    return "OK (weak)" if r["weak"] else "OK"


def is_fail(verdict: str) -> bool:
    return verdict.split(" ")[0].rstrip(";") in {"MISMATCH", "IMPLAUSIBLE", "UNDATED", "BASIS"}


def check_rows(rows: list[dict], load, today: dt.date) -> list[dict]:
    """load(row) -> (texts, meta_date), or raises FileNotFoundError. Returns report lines."""
    rows = [r for r in rows if r["doc_type"] in SCOPE]
    results, problems, missing = {}, {}, set()
    for row in rows:
        try:
            texts, meta = load(row)
        except FileNotFoundError:
            missing.add(row["doc_id"])
            continue
        results[row["doc_id"]], problems[row["doc_id"]] = detect(row, texts, meta)
    out = []
    for row in sorted(rows, key=lambda r: r["doc_id"]):
        d = row["doc_id"]
        if d in missing:
            out.append({**row, "source": "", "evidence": "raw file not found", "verdict": "NO FILE"})
            continue
        r = results[d]
        if r["date"] is None and not problems[d] and row.get("date_basis") != "retrieved":
            r = cross_check(row, results, rows) or r
        elif r["weak"] and r["date"] == pub(row) and not r.get("conflict"):
            r = corroborate(row, r, results, rows)
        out.append({**row, "source": r["source"], "evidence": r["evidence"],
                    "verdict": judge(row, r, problems[d], today), "weak": r["weak"]})
    return out


# ---- I/O ----

def pdf_date(raw: str | None) -> dt.date | None:
    m = re.match(r"D:(\d{4})(\d{2})(\d{2})", raw or "")
    return dt.date(*map(int, m.groups())) if m else None


def load_file(row: dict) -> tuple[list[str], dt.date | None]:
    """Raw file -> (page texts or [text], PDF creationDate)."""
    from cee.config import FileNotAvailable, resolve_path
    try:
        path = resolve_path(row["storage_path"])
    except FileNotAvailable as e:
        raise FileNotFoundError(str(e)) from e
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        import pymupdf
        with pymupdf.open(path) as doc:
            return [doc[i].get_text() for i in range(min(10, len(doc)))], pdf_date(doc.metadata.get("creationDate"))
    raw = path.read_text(encoding="utf-8", errors="replace")
    if suffix in (".htm", ".html"):
        from bs4 import BeautifulSoup
        raw = BeautifulSoup(raw, "html.parser").get_text(" ")
    return [raw], None


def verdict_label(v: str) -> str:
    """Count key: "OK", "OK (weak)", "OK (cross-check)", "OK (note)", or the first rule label."""
    if v.startswith("OK ("):
        return v.split(":")[0].rstrip(")") + ")"
    return re.split(r" \(|;", v)[0]


def render(lines: list[dict], today: dt.date, manifest: str) -> str:
    cell = lambda s: str(s or "").replace("|", "\\|").replace("\n", " ")
    out = ["# C2 document dates", "",
           f"Generated by scripts/check_dates.py; do not edit by hand. Manifest: `{manifest}`;"
           f" today: {today}; rows: {len(lines)} (doc_type transcript, press, deck).", "",
           "| doc_id | published_at | date_basis | date source | evidence | verdict |",
           "|---|---|---|---|---|---|"]
    for l in lines:
        out.append("| " + " | ".join(cell(l.get(k)) for k in
                                       ("doc_id", "published_at", "date_basis", "source", "evidence", "verdict")) + " |")
    out += ["", "## Counts", "", "By verdict:", ""]
    out += [f"- {k}: {n}" for k, n in sorted(Counter(verdict_label(l["verdict"]) for l in lines).items())]
    out += ["", "By date source:", ""]
    out += [f"- {k or '(none)'}: {n}" for k, n in sorted(Counter(l["source"] for l in lines).items())]
    weak = [l for l in lines if l.get("weak") and l["verdict"] != "NO FILE"]
    out += ["", "## Weak evidence", "",
            "Dated only by a line our own converter wrote; no printed date, URL date or footer confirms it.", ""]
    out += [f"- {l['doc_id']} ({l['published_at']}): {l['evidence']}" for l in weak] or ["- none"]
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None, load=load_file) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--manifest", default="data/manifest.csv")
    ap.add_argument("--out")
    ap.add_argument("--today", type=dt.date.fromisoformat, default=dt.date.today())
    ap.add_argument("--skip-missing", action="store_true", help="report missing raw files, exit 0/1 anyway")
    a = ap.parse_args(argv)
    with open(a.manifest, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    lines = check_rows(rows, load, a.today)
    text = render(lines, a.today, a.manifest)
    print(text, end="")
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
    if any(l["verdict"] == "NO FILE" for l in lines) and not a.skip_missing:
        return 2
    return 1 if any(is_fail(l["verdict"]) for l in lines) else 0


if __name__ == "__main__":
    sys.exit(main())
