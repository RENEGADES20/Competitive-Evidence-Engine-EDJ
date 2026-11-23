"""Facts table (#285, ADR-022): metric figures extracted once at ingest, served by SQL at query time.

Three parts, one module:
- **Extraction** (offline, a planned paid run through scripts/extract_facts.py): one model call per document that
  holds candidate chunks (config/facts.yaml prefilter); every proposed row is code-checked (check_row) and only
  passing rows are written to config/facts.jsonl. Entity and segment always come from the chunk.
- **Load** (`python -m cee.facts load`, run by sync-db and ingest): config/facts.jsonl -> table `facts`.
- **Serve** (query time, no model): a map cell that passes the serving rule (eligible, registry, lookup, periods,
  freshness, SQL re-check; plan TL conditions B1-B6) is built from rows by code; every other cell takes the LLM map.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field, replace
from functools import lru_cache
from pathlib import Path

import yaml

from cee.config import REPO_ROOT, settings

FACTS_CONFIG = REPO_ROOT / "config" / "facts.yaml"
FACTS_FILE = REPO_ROOT / "config" / "facts.jsonl"
UPGRADE_SQL = REPO_ROOT / "db" / "upgrade.sql"
EXTRACT_TOOL = "submit_facts"
PERIOD_TYPES = ("point", "quarter", "year")
DOC_RANK = {"10-Q": 0, "10-K": 0, "supplement": 1, "press": 2, "monthly": 2, "deck": 3}


@lru_cache(maxsize=1)
def facts_config() -> dict:
    return yaml.safe_load(FACTS_CONFIG.read_text(encoding="utf-8")) or {}


def extract_version() -> str:
    return str(facts_config().get("extract_version") or "facts-v1")


def enabled() -> bool:
    return settings().facts == "on"


def squash(text) -> str:
    return " ".join(str(text or "").split())


def _low(text) -> str:
    return squash(text).lower()


def value_in(value, text) -> bool:
    """The value, whitespace squashed, stands in the text as written and not inside a longer number
    ("1" is not in "20,514")."""
    v, t = squash(value), squash(text)
    if not v:
        return False
    return re.search(r"(?<![\d.,])" + re.escape(v) + r"(?!\d|[.,]\d)", t) is not None


# --- extraction ----------------------------------------------------------------------------------

CANDIDATE_SQL = """
SELECT c.chunk_id, c.doc_id, c.seq, c.segment, c.section, c.page, c.prefix, c.text,
       d.entity_id, d.doc_type, d.published_at, d.period_end
FROM chunks c JOIN documents d USING (doc_id)
WHERE d.entity_id = ANY(%(entities)s) AND d.doc_type = ANY(%(doc_types)s) AND ({match})
ORDER BY c.doc_id, c.seq
"""


def candidate_sql() -> tuple[str, dict]:
    """The prefilter as SQL: a chunk of a scoped document that matches a metric pattern next to a number."""
    cfg = facts_config()
    parts, params = [], {"entities": list(cfg["entities"]), "doc_types": list(cfg["doc_types"])}
    for i, (_, m) in enumerate(cfg["metrics"].items()):
        parts.append(f"(c.text ~* %(p{i})s AND c.text ~ %(n{i})s)")
        params[f"p{i}"], params[f"n{i}"] = m["prefilter"], m["number"]
    return CANDIDATE_SQL.format(match=" OR ".join(parts)), params


def candidate_docs(conn) -> list[dict]:
    """[{doc: {...}, chunks: [...]}] in doc_id order: every scoped document with candidate chunks."""
    sql, params = candidate_sql()
    docs: dict[str, dict] = {}
    for r in conn.execute(sql, params).fetchall():
        d = docs.setdefault(r["doc_id"], {"doc": {k: r[k] for k in ("doc_id", "entity_id", "doc_type",
                                                                    "published_at", "period_end")}, "chunks": []})
        d["chunks"].append({k: r[k] for k in ("chunk_id", "seq", "segment", "section", "page", "prefix", "text")})
    return list(docs.values())


SYSTEM_PROMPT = """You extract reported figures from passages of one firm's own document (a filing, supplement,
press release, monthly report or investor deck). List every figure of the metrics below that a passage states for
the document's firm. Copy, do not compute: never add, convert, round or infer a figure, a unit or a date.

Metrics:
{metrics}

For each figure give:
- chunk_id: the passage it is in (one of the listed ids);
- metric: one of the metric keys above;
- firm: the firm the figure belongs to, as an id from the list given; OTHER when it is another firm's figure;
- segment: the passage's segment (shown with it) when the figure is that segment's, else an empty string;
- label: the words the passage uses to name the figure, copied exactly (e.g. "Financial advisors (actual)");
- scope: an empty string when the figure covers the whole metric as labelled; else the part it covers, in the
  passage's words (e.g. "Independent contractors", "U.S.", "Private Client Group");
- value: the figure exactly as written in the passage (e.g. "20,425", "$2.5 trillion", "18.7", ">15K");
- unit: what is counted, with the scale the passage states for it (e.g. "advisors", "USD billions", "USD millions");
- period_type: point (a count or balance at a date), quarter (a flow over a quarter) or year (a flow over a year);
- period_end: the date the figure is as of, or the last day of its period, as YYYY-MM-DD, as the passage or its
  table column states it (a fiscal year or quarter ends on the firm's own date);
- quote: the shortest exact span of the passage (at most 300 characters) that contains both the label and the
  value, copied character for character.
Skip a figure whose date or period the passage does not make clear, year-to-date and nine-month flows, forecasts
and targets, and figures for other firms. Return an empty list when there is none. Return the result by calling
the {tool} tool."""


def system_prompt() -> str:
    lines = [f"- {k}: {squash(m['what'])}" for k, m in facts_config()["metrics"].items()]
    return SYSTEM_PROMPT.format(metrics="\n".join(lines), tool=EXTRACT_TOOL)


def extract_schema() -> dict:
    """Strict tool schema (DeepSeek strict mode: every property required, no extra properties)."""
    s = {"type": "string"}
    item = {"type": "object", "additionalProperties": False,
            "properties": {"chunk_id": s, "metric": {"type": "string", "enum": list(facts_config()["metrics"])},
                           "firm": s, "segment": s, "label": s, "scope": s, "value": s, "unit": s,
                           "period_type": {"type": "string", "enum": list(PERIOD_TYPES)}, "period_end": s, "quote": s},
            "required": ["chunk_id", "metric", "firm", "segment", "label", "scope", "value", "unit", "period_type",
                         "period_end", "quote"]}
    return {"type": "object", "additionalProperties": False,
            "properties": {"facts": {"type": "array", "items": item}}, "required": ["facts"]}


def extract_message(doc: dict, chunks: list[dict]) -> str:
    firms = sorted({doc["entity_id"], "OTHER"})
    lines = [f"Document: {doc['doc_id']} ({doc['doc_type']}), firm {doc['entity_id']}, published "
             f"{doc['published_at']}, period end {doc['period_end'] or 'not set'}.",
             f"Firm ids: {', '.join(firms)}.", "", "Passages:"]
    for c in chunks:
        head = f"[{c['chunk_id']}] segment: {c['segment'] or '(none)'}; section: {squash(c['section']) or '(none)'}"
        lines += [head, squash(c["text"]), ""]
    return "\n".join(lines)


def deepseek_request(doc: dict, chunks: list[dict]) -> dict:
    from cee.answer.llm import deepseek_tool_request, stage_max_tokens
    return deepseek_tool_request(EXTRACT_TOOL, "Submit the extracted figures.", extract_schema(), system_prompt(),
                                 extract_message(doc, chunks), stage_max_tokens("map"), stage="map")


def call_extract(client, doc: dict, chunks: list[dict], meta: dict) -> dict:
    """One extraction call (DeepSeek, the map stage's settings). Returns the tool arguments; raises
    llm.ModelOutputError when the output cannot be trusted (saved by the caller, never re-rolled)."""
    from cee.answer import llm
    req = deepseek_request(doc, chunks)
    resp = llm.deepseek_create(client, req)
    call, stop, usage, payload = llm.deepseek_tool_call(resp, EXTRACT_TOOL, req)
    meta["stop_reason"], meta["usage"] = stop, usage
    meta["reasoning_content"] = (payload or {}).get("reasoning_content") if isinstance(payload, dict) else None
    meta["payload"] = payload
    if stop in llm.CUT_REASONS:
        raise llm.ModelOutputError("Facts output cut at max_tokens", payload, "deepseek", stop, usage)
    if stop not in llm.DEEPSEEK_OK or call is None:
        raise llm.ModelOutputError(f"No {EXTRACT_TOOL} call (finish_reason={stop})", payload, "deepseek", stop, usage)
    raw = llm.deepseek_arguments(call, meta.setdefault("parse_flags", []))
    if not isinstance(raw.get("facts"), list):
        raise llm.ModelOutputError("Facts output has no facts list", raw, "deepseek", stop, usage)
    return raw


# --- code checks (ADR-022; plan TL non-blocking 3) ------------------------------------------------

_UNIT_SKIP = {"usd", "us", "of", "the", "in", "and", "dollar", "dollars", "per"}


def unit_ok(unit: str, text: str) -> bool:
    """Every word of the unit (a scale word, a counted noun) is in the chunk text or prefix; a currency unit
    needs a currency mark there. Stems: a trailing s is dropped."""
    low = text.lower()
    toks = re.findall(r"[a-z]+", unit.lower())
    if not toks and "$" not in unit:
        return False
    if "usd" in toks or "$" in unit or "dollar" in unit.lower():
        if "$" not in text and "dollar" not in low and "usd" not in low:
            return False
    for t in toks:
        if t in _UNIT_SKIP or len(t) < 3:
            continue
        if (t[:-1] if t.endswith("s") else t) not in low:
            return False
    return True


def period_label(period_type: str, end: dt.date) -> str:
    if period_type == "point":
        return end.isoformat()
    if period_type == "quarter":
        return f"{end.year}Q{(end.month - 1) // 3 + 1}"
    return f"FY{end.year}"


def _date(v) -> dt.date | None:
    if v is None or v == "":
        return None
    if isinstance(v, dt.date):
        return v
    try:
        return dt.date.fromisoformat(str(v)[:10])
    except ValueError:
        return None


def basis_key(metric: str, label: str, scope: str) -> str:
    return f"{metric}|{_low(label)}|{_low(scope)}"


def fact_id(row: dict) -> str:
    key = "|".join(str(row[k]) for k in ("chunk_id", "metric", "label", "scope", "period", "value"))
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:20]


def check_row(f: dict, doc: dict, chunk: dict | None) -> tuple[dict | None, str | None]:
    """(stored row, None) or (None, the first failed check). Checks: chunk in the call; metric known; firm =
    the document's entity; segment = the chunk's or empty; quote verbatim in the chunk text and value verbatim in
    the quote (whitespace squashed); period type known, period end a date not after publication nor after the
    document's own period end; unit words in the chunk or prefix; value parses as a number."""
    from cee.answer.matrix import _value
    if chunk is None:
        return None, "chunk_not_in_call"
    if f.get("metric") not in facts_config()["metrics"]:
        return None, "metric_unknown"
    if str(f.get("firm") or "").strip().upper() != str(doc["entity_id"]).upper():
        return None, "firm_mismatch"
    seg = squash(f.get("segment"))
    if seg and _low(seg) != _low(chunk.get("segment")):
        return None, "segment_mismatch"
    quote, value = squash(f.get("quote")), squash(f.get("value"))
    if not quote or quote not in squash(chunk["text"]):
        return None, "quote_not_verbatim"
    if not value_in(value, quote):
        return None, "value_not_in_quote"
    if f.get("period_type") not in PERIOD_TYPES:
        return None, "period_type_unknown"
    end = _date(f.get("period_end"))
    if end is None or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(f.get("period_end") or "").strip()):
        return None, "period_unparsed"
    pub, dend = _date(doc.get("published_at")), _date(doc.get("period_end"))
    if pub and end > pub:
        return None, "period_after_published"
    if dend and end > dend:
        return None, "period_after_doc_period"
    unit = squash(f.get("unit"))
    if not unit or not unit_ok(unit, f"{chunk.get('prefix') or ''} {chunk['text']}"):
        return None, "unit_not_in_chunk"
    num = _value(value, unit)
    if num is None:
        return None, "value_unparsed"
    label, scope = squash(f.get("label")), squash(f.get("scope"))
    if not label:
        return None, "label_empty"
    row = {"chunk_id": chunk["chunk_id"], "doc_id": doc["doc_id"], "entity_id": doc["entity_id"],
           "segment": chunk.get("segment"), "metric": f["metric"], "label": label, "scope": scope,
           "period": period_label(f["period_type"], end), "period_end": end.isoformat(),
           "period_type": f["period_type"], "value": value, "value_num": num, "unit": unit,
           "basis": basis_key(f["metric"], label, scope), "quote": quote}
    row["fact_id"] = fact_id(row)
    return row, None


def check_output(raw: dict, doc: dict, chunks: list[dict], model: str) -> tuple[list[dict], list[dict]]:
    """(kept rows, rejected proposals with their reason) of one output; duplicate rows (same fact_id) kept once."""
    by_id = {c["chunk_id"]: c for c in chunks}
    kept, rejected, seen = [], [], set()
    for f in raw.get("facts") or []:
        f = f if isinstance(f, dict) else {}
        row, why = check_row(f, doc, by_id.get(str(f.get("chunk_id") or "")))
        if row is None:
            rejected.append({**f, "reject": why})
            continue
        if row["fact_id"] in seen:
            continue
        seen.add(row["fact_id"])
        kept.append({**row, "extract_version": extract_version(), "model": model})
    return kept, rejected


# --- file and load ---------------------------------------------------------------------------------

def read_rows(path: Path | None = None) -> list[dict]:
    p = Path(path or FACTS_FILE)
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_rows(rows: list[dict], path: Path | None = None) -> None:
    rows = sorted(rows, key=lambda r: (r["entity_id"] or "", r["metric"], r["chunk_id"], r["period_end"], r["fact_id"]))
    Path(path or FACTS_FILE).write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n"
                                                for r in rows), encoding="utf-8", newline="\n")


COLUMNS = ("fact_id", "chunk_id", "doc_id", "entity_id", "segment", "metric", "label", "scope", "period", "period_end",
           "period_type", "value", "value_num", "unit", "basis", "quote", "extract_version", "model")


def facts_ddl() -> str:
    """The facts part of db/upgrade.sql (idempotent), so the loader works on a snapshot made before #285."""
    text = UPGRADE_SQL.read_text(encoding="utf-8")
    return text[text.index("CREATE TABLE IF NOT EXISTS facts"):]


def load(path: Path | None = None, conn=None) -> dict:
    """Replace the table's rows with the file's. Rows whose chunk is not in the database are skipped and counted."""
    from cee.db import connect
    rows = read_rows(path)
    own = conn is None
    conn = conn or connect()
    try:
        conn.execute(facts_ddl())
        conn.execute("DELETE FROM facts")
        have = {r["chunk_id"] for r in conn.execute("SELECT chunk_id FROM chunks WHERE chunk_id = ANY(%s)",
                                                    ([r["chunk_id"] for r in rows],)).fetchall()}
        keep = [r for r in rows if r["chunk_id"] in have]
        if keep:
            with conn.cursor() as cur:
                cur.executemany(f"INSERT INTO facts ({', '.join(COLUMNS)}) VALUES "
                                f"({', '.join('%(' + c + ')s' for c in COLUMNS)})", keep)
        conn.commit()
    finally:
        if own:
            conn.close()
    return {"file_rows": len(rows), "loaded": len(keep), "missing_chunk": len(rows) - len(keep)}


# --- serving rule (plan TL conditions B1-B6) ---------------------------------------------------------

@lru_cache(maxsize=1)
def _word_patterns() -> tuple[re.Pattern, ...]:
    words = facts_config()["serve"]["non_figure_words"]
    return tuple(re.compile(r"(?<![a-z])" + re.escape(w.strip().lower()).replace(r"\ ", r"\s+"), re.I)
                 for w in words if w.strip())


def non_figure_word(*texts: str) -> str | None:
    for t in texts:
        for p in _word_patterns():
            m = p.search(t or "")
            if m:
                return m.group(0).strip().lower()
    return None


def eligible(sq, aspect, question: str) -> tuple[bool, str]:
    """B3: the positive rule. (True, "") or (False, why)."""
    serve = facts_config()["serve"]
    if not sq.entity or sq.role not in ("named", "competitor"):
        return False, "not a firm row"
    if aspect.metric not in serve["metrics"]:
        return False, f"metric tag {aspect.metric or '(none)'} not served"
    if aspect.kind not in serve["kinds"]:
        return False, f"kind {aspect.kind}"
    if getattr(aspect, "proxy", False):
        return False, "proxy aspect"
    w = non_figure_word(aspect.text, sq.text, question)
    if w:
        return False, f"non-figure word '{w}'"
    return True, ""


def registered_basis(entity: str, metric: str) -> tuple[list[str] | None, str]:
    """B2: (label phrases of the registered basis, "") when the registry status is quoted, else (None, why)."""
    from cee.answer.matrix import _config_entity, metric_definition
    d = metric_definition(entity, metric)
    if not d:
        return None, "not in the registry"
    if d.get("status") != "quoted":
        return None, f"registry status {d.get('status')}"
    phrases = ((facts_config()["serve"].get("bases") or {}).get(_config_entity(entity)) or {}).get(metric)
    if not phrases:
        return None, "no registered basis phrases"
    return [p.lower() for p in phrases], ""


def on_basis(row: dict, phrases: list[str]) -> bool:
    return not squash(row.get("scope")) and any(p in _low(row.get("label")) for p in phrases)


LOOKUP_SQL = """
SELECT f.fact_id, f.metric, f.label, f.scope, f.period, f.period_end::text AS f_period_end, f.period_type, f.value,
       f.value_num, f.unit, f.basis, f.quote, f.extract_version,
       c.chunk_id, c.doc_id, d.entity_id, c.segment, d.doc_type, d.source_tier,
       d.published_at::text AS published_at, d.period_end::text AS period_end,
       c.section, c.page, 0.0::float AS rank, c.text, d.date_basis
FROM facts f JOIN chunks c ON c.chunk_id = f.chunk_id JOIN documents d ON d.doc_id = c.doc_id
WHERE f.metric = %(metric)s
  AND {entity_filter}
  AND {window_filter}
  AND {filters}
ORDER BY d.published_at DESC, f.fact_id
"""


def _sub_filters(sub) -> tuple[str, str, str, dict]:
    """The sub-question's hard filters, built by the fts builders: entity (+ Merrill segment), window, Ask-page
    filters (date range, keywords) and the doc-type scope."""
    from cee.retrieve import fts
    where, params = fts.entity_filter(sub.entities)
    filters, fp = fts.filters_sql(replace(sub, exclude_ids=[], period_range=None))
    params.update(fp)
    scope, sp = fts.doc_type_scope_sql(sub)
    if scope != "TRUE":
        filters = f"{filters} AND {scope}"
        params.update(sp)
    window, wp = fts.window_filter(sub.window)
    params.update(wp)
    return where, window, filters, params


def lookup(sub, metric: str) -> list[dict]:
    """Rows of one metric that pass the sub-question's hard filters, newest document first."""
    from cee.db import connect
    from cee.retrieve import fts
    if not fts.searchable(sub):
        return []
    where, window, filters, params = _sub_filters(sub)
    params["metric"] = metric
    try:
        with connect() as conn:
            return [dict(r) for r in conn.execute(LOOKUP_SQL.format(entity_filter=where, window_filter=window,
                                                                    filters=filters), params).fetchall()]
    except Exception as e:   # no facts table (a snapshot before #285 and no load): every cell takes the map
        if "facts" in str(e):
            return []
        raise


NEWEST_SQL = """
SELECT max(d.published_at)::text AS newest FROM chunks c JOIN documents d USING (doc_id)
WHERE c.chunk_id = ANY(%(ids)s) AND c.text ~* %(pat)s AND c.text ~ %(num)s
"""


def pool_newest(ids, metric: str) -> str | None:
    """B1: the newest publication date among the pool's chunks that mention the metric next to a number."""
    from cee.db import connect
    m = facts_config()["metrics"][metric]
    if not ids:
        return None
    with connect() as conn:
        r = conn.execute(NEWEST_SQL, {"ids": sorted(ids), "pat": m["prefilter"], "num": m["number"]}).fetchone()
    return (r or {}).get("newest")


def recheck(sub, items, fetch=None) -> str | None:
    """B6: every served item again through the fts filters (fts.fetch_pinned, an independent query: chunk exists,
    entity and Merrill segment, window, Ask-page filters, scope) and its value and quote against the chunk text.
    None when all pass, else why."""
    from cee.retrieve import fts
    fetch = fetch or fts.fetch_pinned
    ids = list(dict.fromkeys(c for i in items for c in i.chunk_ids))
    got = {h.chunk_id: h for h in fetch(sub, ids)}
    for i in items:
        for c in i.chunk_ids:
            h = got.get(c)
            if h is None:
                return f"{c} does not pass the sub-question's filters"
            if squash(i.quote) not in squash(h.text) or not value_in(i.value, i.quote):
                return f"{c}: value or quote not verbatim"
    return None


def _pick(rows: list[dict]) -> dict[str, dict]:
    """One row per period: newest document, then document type (filings first), then id."""
    out: dict[str, dict] = {}
    for r in sorted(rows, key=lambda r: (r["period"], _neg(r["published_at"]), DOC_RANK.get(r["doc_type"], 9),
                                         r["chunk_id"], r["fact_id"])):
        out.setdefault(r["period"], r)
    return out


def _neg(date_text: str) -> int:
    d = _date(date_text)
    return -(d.toordinal() if d else 0)


def item_of(r: dict):
    from cee.answer.matrix import Item
    unit = r["unit"] if r["unit"].lower() not in r["value"].lower() else ""
    text = f"{r['label']}: {r['value']}{' ' + unit if unit else ''} ({r['period']})"
    return Item(text=text, quote=r["quote"], chunk_ids=[r["chunk_id"]], value=r["value"], unit=r["unit"],
                period=r["period"], scope="", definition="")


def hit_of(r: dict, sq_id: str):
    from cee.retrieve.fts import Hit
    return Hit(chunk_id=r["chunk_id"], doc_id=r["doc_id"], entity_id=r["entity_id"], segment=r["segment"],
               doc_type=r["doc_type"], source_tier=r["source_tier"], published_at=r["published_at"],
               period_end=r["period_end"], section=r["section"], page=r["page"], rank=0.0, text=r["text"],
               date_basis=r.get("date_basis") or "source", part_id=sq_id, origin="facts")


@dataclass
class Served:
    cell: object            # matrix.Cell
    hits: list = field(default_factory=list)


def serve_cell(q, plan, sq, as_of, lookup_fn=None, newest_fn=None, recheck_fn=None) -> tuple[Served | None, dict]:
    """One cell: (Served, decision) or (None, decision with the reason it goes to the map)."""
    from cee.answer.matrix import Cell, _covers, asked_periods
    from cee.retrieve import planner
    a = sq.aspect
    dec = {"id": sq.id, "metric": a.metric, "kind": a.kind, "served": False, "reason": ""}
    ok, why = eligible(sq, a, q.question)
    if not ok:
        return None, {**dec, "reason": why}
    phrases, why = registered_basis(sq.entity, a.metric)
    if phrases is None:
        return None, {**dec, "reason": why}
    sub = planner.subquestion_query(q, sq)
    rows = [r for r in (lookup_fn or lookup)(sub, a.metric) if on_basis(r, phrases)]
    if not rows:
        return None, {**dec, "reason": "no row on the registered basis passes the filters"}
    by_period = _pick(rows)
    dec["conflicts"] = sum(1 for p, r in by_period.items()
                           if any(x["period"] == p and x["value_num"] != r["value_num"] for x in rows))
    asked = asked_periods(q.question, as_of)
    if a.kind == "series":
        if asked:
            unit, periods = asked
            cover = {}
            for p, r in by_period.items():
                c = _covers(p, unit)
                if c in periods and (c not in cover or r["period_end"] > cover[c]["period_end"]):
                    cover[c] = r
            missing = [p for p in periods if p not in cover]
            if missing:
                return None, {**dec, "reason": "asked periods missing: " + ", ".join(missing)}
            chosen = [cover[p] for p in periods]
        else:
            types: dict[str, list] = {}
            for r in by_period.values():
                types.setdefault(r["period_type"], []).append(r)
            best = max(types.values(), key=len)
            chosen = sorted(best, key=lambda r: r["period_end"])[-int(facts_config()["serve"]["series_last"]):]
            if len(chosen) < 2:
                return None, {**dec, "reason": "fewer than two periods"}
    else:
        chosen = [max(by_period.values(), key=lambda r: (r["period_end"], r["period_type"] == "quarter"))]
    newest_row = max(r["published_at"] for r in chosen)
    pool = set((getattr(plan, "pools", {}) or {}).get(sq.id, set()))
    newest_pool = (newest_fn or pool_newest)(pool, a.metric)
    if newest_pool and newest_pool > newest_row:
        return None, {**dec, "reason": f"newer document in the pool ({newest_pool} > {newest_row})"}
    items = [item_of(r) for r in chosen]
    bad = (recheck_fn or recheck)(sub, items)
    if bad:
        return None, {**dec, "reason": f"recheck failed: {bad}", "recheck_failed": True}
    cell = Cell(sq.id, sq.entity, a.id, sq.role, "fact", source="facts", items=items,
                reason=f"facts table ({extract_version()}): {len(items)} row(s)")
    hits = list({r["chunk_id"]: hit_of(r, sq.id) for r in chosen}.values())
    in_pool = sum(1 for h in hits if h.chunk_id in pool)
    return Served(cell, hits), {**dec, "served": True, "reason": "served", "rows": len(items),
                                "chunk_ids": [h.chunk_id for h in hits], "in_retrieved": in_pool,
                                "periods": [r["period"] for r in chosen]}


def serve(q, plan, as_of, cell_ids, **fns) -> tuple[dict[str, Served], list[dict]]:
    """Every map cell in `cell_ids` (the cells that would get an LLM call): which are served from facts.
    Decisions are logged for every cell whose aspect carries a metric tag (served or why not)."""
    served, decisions = {}, []
    by_id = {sq.id: sq for sq in plan.subquestions}
    for cid in cell_ids:
        sq = by_id.get(cid)
        if sq is None:
            continue
        s, dec = serve_cell(q, plan, sq, as_of, **fns)
        if s is not None:
            served[cid] = s
        if s is not None or sq.aspect.metric:
            decisions.append(dec)
    return served, decisions


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args[:1] == ["load"]:
        path = Path(args[1]) if len(args) > 1 else None
        out = load(path)
        print(f"facts: {out['loaded']} rows loaded from {path or FACTS_FILE} "
              f"({out['missing_chunk']} skipped: chunk not in the database)")
        return 0
    print("usage: python -m cee.facts load [path]")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
