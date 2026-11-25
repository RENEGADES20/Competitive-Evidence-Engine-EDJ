"""Build the demo-mode fixture (#299): one prepared answer per eval question Q1-Q30, replayed by the Ask page.

One-time and offline. For each question it:
  1. builds up to MAX_CARDS numbered evidence cards from the W12 fts run (docs/results/w12-latency/b-fts/report.json,
     matrix cells -> items -> chunk_ids) and the stored chunks (local database, snapshot corpus-2026-11-19);
  2. maps the W12 stage timings (docs/results/w12-latency/b-fts-latency.json) onto cee.ask.STAGES, scaled to a
     replay of about 3.6 s;
  3. asks the writer model once for a narrative markdown answer with [n] citations to the cards
     (--provider anthropic: Claude Opus, claude-opus-5-5; --provider mock: a code-built answer, no call);
  4. checks every [n] resolves to a card and every number in the answer appears in the cards;
  5. writes src/cee/app/demo/fixture.json.

Every real call's request and response go to .eval-runs/demo-fixture/raw/<qid>-<prompt>.json with tokens and cost
(config/pricing.yaml). A saved response for the same request is reused, never paid for again. --max-calls caps the
number of new real calls (default 0: a real run must say how many it may make).

  python scripts/build_demo_fixture.py                                  # mock answers, 0 calls
  python scripts/build_demo_fixture.py --provider anthropic --max-calls 30
  python scripts/build_demo_fixture.py --provider anthropic --only Q4,Q27 --prompt demo-2 --max-calls 2
  python scripts/build_demo_fixture.py --check                          # checks the committed fixture only
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from cee.app.demo import replay as R  # noqa: E402

W12_REPORT = REPO / "docs/results/w12-latency/b-fts/report.json"
W12_LATENCY = REPO / "docs/results/w12-latency/b-fts-latency.json"
QUESTIONS = REPO / "evals/questions.yaml"
RUN_DIR = REPO / ".eval-runs/demo-fixture"
MODEL = "claude-opus-5-5"
EFFORT = "high"
MAX_TOKENS = 16000
MAX_CARDS = 12
CARD_CAP = {"Q22": 20}   # a by-quarter series for five firms needs more than 12 cards (review, #299)
CONCURRENCY = 6   # parallel writer calls (one per question)
PASSAGE_CHARS = 700
DEMO_QS = [f"Q{i}" for i in range(1, 31)]
FIRMS = {"MS": "Morgan Stanley", "SCHW": "Schwab", "EDJ": "Edward Jones", "MER": "Merrill", "BAC": "Bank of America",
         "RJF": "Raymond James"}

BEHAVIOR_RULES = {
    "answer": "Answer the question directly from the cards.",
    "answer_with_boundary": (
        "Give the evidence half completely, then hand the judgement back: say plainly that what the firm should "
        "do (or how it could replicate anything) is left to the strategy team. Never recommend or suggest an action."),
    "gap_with_adjacent": (
        "The stored documents do not hold the figure or fact the question asks for (or hold it only for some "
        "firms). The first sentence says plainly what is not disclosed. Then give the closest adjacent evidence, "
        "each item labelled as a different quantity and why it differs. Never present an adjacent figure as the "
        "answer, and never estimate the missing one."),
    "refuse": "Say plainly that nothing in the stored documents answers this, and what kind of source would.",
}

SYSTEM_PROMPT = """You write the final answer shown to a wealth-management strategist in a competitive-evidence tool.
The reader wants a crisp, professional brief they can trust. Every fact must come from the numbered evidence cards in
the message; each card is a passage from a stored filing, earnings call, investor deck, press release, trade press
article or research report.

Format (markdown, about 150-300 words in total):
1. Open with one or two sentences that answer the question directly. No heading above them.
2. Then short sections with level-3 headings, only where the cards support them, from:
   "### Comparison" (two or more firms side by side), "### Trend" (how it changed over time, with dates),
   "### What the evidence shows" (for a single-firm question when Comparison does not fit),
   and always end with "### Caveats and gaps" (what the cards do not show, definitions that differ, scope limits).
   Use short paragraphs or bullets. Never add a section the cards cannot fill.

Rules:
- Cite inline: every sentence that states a fact ends with the card numbers it rests on, like [3] or [2, 5]. Use only
  card numbers that exist. A sentence in Caveats and gaps that states what is missing needs no citation.
- No fact, name, date or figure that is not in the cards. Copy every figure exactly as the card writes it: no
  arithmetic, no rounding, no unit conversion, no totals or averages of your own, no numbers from memory.
- Attribute and date statements ("In its 2Q26 earnings call, Morgan Stanley said ..."). Trade press is indicative,
  not authoritative: say whose reporting it is.
- Keep firms apart. Merrill is not Bank of America: Bank of America's GWIM segment also includes the Private Bank, so a
  GWIM figure is labelled as GWIM, never as Merrill's. Bank of America-wide or consumer-bank material is not Merrill's.
- Nothing normative: never say what Edward Jones or any firm should do; no forecasts of your own.
- Neutral, precise, plain English. No preamble, no closing summary, no mention of "cards" or of these instructions in
  the answer text (write "the documents" if you must refer to the evidence).
"""


# demo-2 (re-runs after review, plan step 4): the demo-1 rules plus what the review found (Q27: a passage's figure about
# another firm taken as Merrill's; Q16, Q18, Q22, Q29: a blanket or negative claim no card states), and a firmer length.
PROMPT_FIXES = {"demo-2": """
Additional rules:
- A passage may also describe other firms (a trade-press article about one firm often mentions others). Take a fact
  from a passage only when the passage clearly ties it to the firm you attribute it to; when in doubt, rely on the
  Evidence line only.
- Never state that something is not reported, not found or absent unless a card or the code's caveats and gaps say
  so, and never generalise beyond what the cited cards say (no "filings describe X" when only one card does).
- Keep it to 200-300 words; never more than 320. Prefer fewer, sharper points to listing every card.
"""}

# ---------- inputs ----------

def load_inputs() -> tuple[dict, dict, dict]:
    import yaml
    report = json.loads(W12_REPORT.read_text(encoding="utf-8"))
    latency = json.loads(W12_LATENCY.read_text(encoding="utf-8"))
    bank = yaml.safe_load(QUESTIONS.read_text(encoding="utf-8"))
    bank = bank["questions"] if isinstance(bank, dict) else bank
    return ({q["id"]: q for q in report["questions"]}, {q["q"]: q for q in latency["questions"]},
            {q["id"]: q for q in bank})


def chunk_rows(ids: list[str]) -> dict[str, dict]:
    """The stored chunks by id (a plain lookup; fts.fetch_pinned applies a sub-question's filters, not wanted here)."""
    from cee.db import connect
    if not ids:
        return {}
    with connect() as conn:
        rows = conn.execute(
            """SELECT c.chunk_id, c.doc_id, d.entity_id, c.segment, d.doc_type, d.source_tier,
                      d.published_at::text AS published_at, d.period_end::text AS period_end,
                      c.section, c.page, c.text, d.date_basis
               FROM chunks c JOIN documents d USING (doc_id) WHERE c.chunk_id = ANY(%s)""", (list(ids),)).fetchall()
    return {r["chunk_id"]: dict(r) for r in rows}


def _cells(q: dict) -> list[dict]:
    cells = q["matrix"]["cells"]
    return list(cells.values()) if isinstance(cells, dict) else list(cells)


def _aspects(q: dict) -> dict[str, str]:
    return {a["id"]: a["text"] for a in q["matrix"].get("aspects") or q["plan"].get("aspects") or []}


def select_items(q: dict, max_cards: int = MAX_CARDS) -> list[tuple[dict, dict]]:
    """(cell, item) pairs for the cards: cells that hold evidence (fact before different_quantity), round-robin over
    firms, then over each firm's cells, one item per cell per pass; an item whose chunks are all on an earlier card is
    skipped. Order is deterministic (matrix order)."""
    held = [c for c in _cells(q) if c.get("label") != "not_found" and c.get("items")]
    held.sort(key=lambda c: 0 if c.get("label") == "fact" else 1)
    by_firm: dict[str, list[dict]] = {}
    for c in held:
        by_firm.setdefault(c.get("entity") or "research", []).append(c)
    order: list[dict] = []   # cells interleaved over firms
    queues = [list(v) for v in by_firm.values()]
    while any(queues):
        for qu in queues:
            if qu:
                order.append(qu.pop(0))
    out, used = [], set()
    depth = max((len(c["items"]) for c in order), default=0)
    for p in range(depth):
        for c in order:
            if len(out) >= max_cards:
                return out
            if p < len(c["items"]):
                it = c["items"][p]
                ids = [i for i in it.get("chunk_ids") or [] if i not in used]
                if not ids:
                    continue
                used.update(it.get("chunk_ids") or [])
                out.append((c, it))
    return out


def card_label(cell: dict, aspects: dict[str, str]) -> str:
    firm = FIRMS.get(cell.get("entity") or "", cell.get("entity") or "Research")
    aspect = aspects.get(cell.get("aspect_id") or "", cell.get("aspect_id") or "")
    aspect = aspect if len(aspect) <= 70 else aspect[:70].rsplit(" ", 1)[0] + " ..."
    head = "ADJACENT EVIDENCE" if cell.get("label") == "different_quantity" else "EVIDENCE"
    return f"{head} - {firm} - {aspect}"


def build_cards(q: dict, rows: dict[str, dict], max_cards: int = MAX_CARDS) -> list[dict]:
    from cee.answer.validate import source_label
    from cee.retrieve.fts import Hit
    aspects = _aspects(q)
    cards = []
    for cell, it in select_items(q, max_cards):
        ids = [i for i in it.get("chunk_ids") or [] if i in rows]
        missing = [i for i in it.get("chunk_ids") or [] if i not in rows]
        if missing:
            raise SystemExit(f"{q['id']}: chunk(s) {missing} not in the local database; sync to corpus-2026-11-19")
        hits = []
        for i in ids:
            r = rows[i]
            hits.append({k: r[k] for k in ("chunk_id", "doc_id", "entity_id", "segment", "doc_type", "source_tier",
                                           "published_at", "period_end", "section", "page", "date_basis")})
        first = rows[ids[0]]
        passage = " ".join(str(first["text"]).split())
        passage = passage if len(passage) <= PASSAGE_CHARS else passage[:PASSAGE_CHARS].rsplit(" ", 1)[0] + " ..."
        label = source_label(Hit(**{**first, "rank": 0.0}))
        cards.append({"n": len(cards) + 1, "label": card_label(cell, aspects), "cell": cell["id"],
                      "kind": cell.get("label"), "differs_because": cell.get("differs_because") or "",
                      "text": it["text"], "quote": it.get("quote") or "", "period": it.get("period") or "",
                      "chunk_id": ids[0], "source_label": label, "passage": passage, "hits": hits})
    return cards


def plan_text(q: dict) -> str:
    plan = q["plan"]
    aspects = plan.get("aspects") or []
    subs = plan.get("subquestions") or []
    firms = sorted({s.get("entity") for s in subs if s.get("entity")})
    head = (f"Decomposing the question ({plan.get('provider') or 'rules'}, one call): {len(aspects)} aspect"
            f"{'' if len(aspects) == 1 else 's'} x {len(firms)} firm{'' if len(firms) == 1 else 's'} = "
            f"{len(subs)} sub-question{'' if len(subs) == 1 else 's'}")
    return head + ": " + "; ".join(f"{a['id']} {a['text']}" for a in aspects)


def stages(q: dict, lat: dict | None, n_cards: int, n_caveats: int, n_gaps: int) -> list[dict]:
    """The nine STAGES with replay seconds in the W12 run's proportions, scaled to R.STAGE_BUDGET_S (each at least
    0.12 s, so every line is seen), plus the trace line each shows."""
    from cee.ask import STAGES
    lat = lat or {}
    cells = _cells(q)
    firms = sorted({c.get("entity") for c in cells if c.get("entity")})
    subs = q["plan"].get("subquestions") or []
    labels: dict[str, int] = {}
    for c in cells:
        labels[c.get("label") or "?"] = labels.get(c.get("label") or "?", 0) + 1
    research = lat.get("remap_calls") or 0
    raw = {"resolve": 0.4, "decompose": lat.get("plan_s") or 4.0, "search": q.get("search_s") or 5.0,
           "extract": lat.get("map_max_s") or 30.0, "research": lat.get("remap_max_s") or 1.0,
           "synthesize": lat.get("reduce_s") or 20.0, "check": 0.6, "caveats": 0.6, "log": 0.3}
    texts = {
        "resolve": f"Reading the question: firms {', '.join(firms) or 'none'}",
        "decompose": plan_text(q),
        "search": f"Searching {len(subs)} sub-question{'' if len(subs) == 1 else 's'}: {q.get('passages', 0)} passages",
        "extract": (f"Extracting from {len(firms)} firm{'' if len(firms) == 1 else 's'}: {len(cells)} cells: "
                    + ", ".join(f"{v} {k.replace('_', ' ')}" for k, v in labels.items())
                    + f"; {n_cards} evidence cards"),
        "research": (f"Re-search: {research} cell{'' if research == 1 else 's'} re-searched" if research
                     else "Re-search: every sub-question has evidence; nothing re-searched"),
        "synthesize": "Writing the answer from the evidence cards (prepared answer, no model call now)",
        "check": "Checking citations: every [n] points to an evidence card",
        "caveats": f"Adding caveats and gaps: {n_caveats} caveat{'' if n_caveats == 1 else 's'}, "
                   f"{n_gaps} gap{'' if n_gaps == 1 else 's'}",
        "log": "Demo mode: nothing is saved",
    }
    # Budget: the five short stages 0.15 s each; plan + search 0.6 s and extract + synthesize the rest, each pair split
    # in the W12 proportion (clamped to 30-70 %), so the cards (extract) always get time to land one by one.
    short = {s: 0.15 for s in ("resolve", "research", "check", "caveats", "log")}
    rest = R.STAGE_BUDGET_S - sum(short.values()) - 0.6

    def split(a: str, b: str, total: float) -> dict:
        share = min(0.7, max(0.3, float(raw[a]) / max(float(raw[a]) + float(raw[b]), 0.1)))
        return {a: total * share, b: total * (1 - share)}
    secs = {**short, **split("decompose", "search", 0.6), **split("extract", "synthesize", rest)}
    return [{"stage": s, "seconds": round(secs[s], 3), "text": texts[s]} for s in STAGES]


# ---------- the writer call ----------

def user_message(entry: dict, bank_q: dict) -> str:
    behavior = entry["behavior"]
    lines = [f"Question ({entry['id']}): {entry['text']}", "",
             f"Expected behavior: {behavior}. {BEHAVIOR_RULES.get(behavior, '')}"]
    if bank_q.get("passes_if"):
        lines.append("What a good answer does (guidance on behavior and scope only; it is not evidence, and any fact "
                     f"in it may be used only if a card states it): {' '.join(str(bank_q['passes_if']).split())}")
    if bank_q.get("trap"):
        lines.append("This is a trap question: keep strictly to the firm named, as described above.")
    lines += ["", f"How the question was broken down: {entry['plan_text']}", "", "Evidence cards:"]
    for c in entry["cards"]:
        lines += [f"[{c['n']}] {c['label']} | {c['source_label']} | {c['chunk_id']}",
                  f"Evidence: {c['text']}"]
        if c.get("differs_because"):
            lines.append(f"Differs from what was asked because: {c['differs_because']}")
        if c.get("quote"):
            lines.append(f"Quote: {c['quote']}")
        lines += [f"Passage: {c['passage']}", ""]
    if entry.get("caveats") or entry.get("gaps"):
        lines.append("Shown by code under your answer (reflect them in Caveats and gaps; do not cite them):")
        lines += [f"- Caveat: {c}" for c in entry.get("caveats") or []]
        lines += [f"- Gap: {g['what']}" for g in entry.get("gaps") or []]
    lines += ["", "Write the answer now."]
    return "\n".join(lines)


def request(entry: dict, bank_q: dict, prompt: str = "demo-1") -> dict:
    return {"model": MODEL, "max_tokens": MAX_TOKENS, "system": SYSTEM_PROMPT + PROMPT_FIXES.get(prompt, ""),
            "thinking": {"type": "adaptive"}, "output_config": {"effort": EFFORT},
            "messages": [{"role": "user", "content": user_message(entry, bank_q)}]}


def request_hash(req: dict) -> str:
    return hashlib.sha256(json.dumps(req, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def mock_answer(entry: dict) -> str:
    """A code-built answer with the fixture's shape (pipeline proof only; no model)."""
    cards = entry["cards"]
    if not cards:
        return "The stored documents hold no passage on this question.\n\n### Caveats and gaps\nNothing is stored."
    first = cards[0]
    out = [f"{first['text']} [1]", "", "### What the evidence shows"]
    out += [f"- {c['text']} [{c['n']}]" for c in cards[1:4]]
    out += ["", "### Caveats and gaps", "This is a mock answer built by code from the evidence cards."]
    return "\n".join(out)


def call_writer(req: dict) -> tuple[str, dict, dict]:
    """One Claude call: (answer text, usage, raw response dict). The repo's client (max_retries=0)."""
    from cee.answer.llm import anthropic_client
    client = anthropic_client()
    t0 = time.perf_counter()
    resp = client.messages.create(**req)
    wall = time.perf_counter() - t0
    raw = resp.to_dict() if hasattr(resp, "to_dict") else json.loads(resp.model_dump_json())
    if resp.stop_reason not in ("end_turn",):
        raise RuntimeError(f"stop_reason {resp.stop_reason}: {getattr(resp, 'stop_details', None)}")
    text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()
    u = resp.usage
    usage = {k: getattr(u, k, None) for k in ("input_tokens", "output_tokens", "cache_read_input_tokens",
                                                "cache_creation_input_tokens")}
    usage = {k: v for k, v in usage.items() if isinstance(v, int)}
    return text, {**usage, "wall_s": round(wall, 2)}, raw


# ---------- build ----------

def build(provider: str, only: list[str] | None, prompt: str, max_calls: int, out: Path) -> int:
    from cee.answer.cost import price_call
    report, latency, bank = load_inputs()
    ids = sorted({i for qid in DEMO_QS for c in _cells(report[qid]) for it in c["items"] for i in it["chunk_ids"]})
    rows = chunk_rows(ids)
    old = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {"questions": []}
    old_by_id = {e["id"]: e for e in old.get("questions", [])}
    raw_dir = RUN_DIR / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    entries, todo, problems = [], [], []
    for qid in DEMO_QS:
        q, bq = report[qid], bank[qid]
        m = q["matrix"]
        entry = {"id": qid, "text": bq["text"], "expected_behavior": bq["expected_behavior"],
                 "behavior": bq["expected_behavior"], "trap": bool(bq.get("trap")), "plan_text": plan_text(q),
                 "caveats": list(m.get("caveats") or []),
                 "gaps": [{"what": g.get("what", ""), "suggested_source": g.get("suggested_source", "")}
                          for g in m.get("gaps") or []]}
        entry["cards"] = build_cards(q, rows, CARD_CAP.get(qid, MAX_CARDS))
        entry["stages"] = stages(q, latency.get(qid), len(entry["cards"]), len(entry["caveats"]), len(entry["gaps"]))
        # --only names the questions written with --prompt; the others keep the prompt version they were written
        # with (from the fixture), so their saved output is reused when the request is unchanged.
        mine = prompt if (only is None and qid not in old_by_id) or (only is not None and qid in only) else             ((old_by_id.get(qid) or {}).get("writer") or {}).get("prompt") or prompt
        mine = prompt if only is None and provider == "mock" else mine
        req = request(entry, bq, mine)
        h = request_hash(req)
        entries.append(entry)
        if provider == "mock":
            entry.update(answer_md=mock_answer(entry), writer={"provider": "mock", "prompt": prompt})
        else:
            path = raw_dir / f"{qid}-{mine}.json"
            saved = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
            entry["writer"] = {"provider": "anthropic", "model": MODEL, "prompt": mine, "effort": EFFORT,
                               "request_hash": h}
            if saved and saved.get("request_hash") == h and saved.get("answer_md"):
                print(f"{qid}: reusing {path.name}")
                entry["answer_md"] = saved["answer_md"]
            else:
                todo.append((entry, req, h, path))
    if len(todo) > max_calls:   # checked before the first call: nothing is paid when the cap is too low
        raise SystemExit(f"{len(todo)} real calls needed ({', '.join(e['id'] for e, *_ in todo)}), "
                         f"over --max-calls {max_calls}; nothing was called")

    def one(job) -> tuple[float, str | None]:
        entry, req, h, path = job
        at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        print(f"{entry['id']}: calling {MODEL}", flush=True)
        try:
            text, usage, raw = call_writer(req)
        except Exception as e:   # a failed call is a finding: saved, reported, never retried here
            path.write_text(json.dumps({"qid": entry["id"], "prompt": entry["writer"]["prompt"], "model": MODEL,
                                        "at": at, "request_hash": h, "request": req,
                                        "error": f"{type(e).__name__}: {e}"}, indent=2), encoding="utf-8")
            return 0.0, f"{entry['id']}: call failed ({type(e).__name__}: {e})"
        price = price_call("anthropic", MODEL, usage, at=at, wall_s=usage.get("wall_s"))
        path.write_text(json.dumps({"qid": entry["id"], "prompt": entry["writer"]["prompt"], "model": MODEL,
                                    "at": at, "request_hash": h, "request": req, "response": raw, "usage": usage,
                                    "cost": price, "answer_md": text}, indent=2, default=str), encoding="utf-8")
        entry["answer_md"] = text
        print(f"{entry['id']}: done in {usage.get('wall_s')} s, ${price.get('usd') or 0:.4f}", flush=True)
        return price.get("usd") or 0.0, None

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
        results = list(pool.map(one, todo))
    calls, cost = len(todo), sum(r[0] for r in results)
    failed = [r[1] for r in results if r[1]]
    if failed:
        for f in failed:
            print("FAILED " + f)
        raise SystemExit("Some calls failed; their requests are saved; the fixture was not written")
    for entry in entries:
        bad, nums = R.bad_citations(entry), R.unmatched_numbers(entry)
        entry["checks"] = {"bad_citations": bad, "unmatched_numbers": nums,
                           "words": len(re.sub(r"\[[\d,\s;]+\]", "", entry["answer_md"]).split())}
        if bad or nums:
            problems.append(f"{entry['id']}: bad citations {bad}, numbers not in the cards {nums}")
    fixture = {"version": 1, "snapshot": "corpus-2026-11-19",
               "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "source_run": "docs/results/w12-latency/b-fts (W12 fts, DeepSeek map-reduce)",
               "model": MODEL if provider == "anthropic" else "mock", "questions": entries}
    out.write_text(json.dumps(fixture, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    log = RUN_DIR / "calls.jsonl"
    with log.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"at": fixture["built_at"], "provider": provider, "prompt": prompt, "only": only,
                            "new_calls": calls, "usd": round(cost, 4), "problems": problems}) + "\n")
    print(f"Wrote {out} ({len(entries)} questions); new real calls: {calls}; cost ${cost:.4f}")
    for p in problems:
        print("FLAG " + p)
    return 1 if problems else 0


def check(path: Path) -> int:
    fx = json.loads(path.read_text(encoding="utf-8"))
    problems = []
    for e in fx["questions"]:
        bad, nums = R.bad_citations(e), R.unmatched_numbers(e)
        total = sum(s["seconds"] for s in e["stages"])
        if bad or nums or total > R.MAX_REPLAY_S:
            problems.append(f"{e['id']}: bad citations {bad}, numbers not in the cards {nums}, stages {total:.2f} s")
    print(f"{len(fx['questions'])} questions; {len(problems)} flagged")
    for p in problems:
        print("FLAG " + p)
    return 1 if problems else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--provider", choices=["mock", "anthropic"], default="mock")
    ap.add_argument("--only", help="comma-separated ids to (re)write; the others keep their saved answer")
    ap.add_argument("--prompt", default="demo-1", help="prompt version, part of the raw file name")
    ap.add_argument("--max-calls", type=int, default=0, help="cap on new real calls (default 0)")
    ap.add_argument("--out", default=str(R.FIXTURE_PATH))
    ap.add_argument("--check", action="store_true", help="only check the fixture at --out")
    a = ap.parse_args()
    if a.check:
        return check(Path(a.out))
    only = [s.strip() for s in a.only.split(",")] if a.only else None
    return build(a.provider, only, a.prompt, a.max_calls, Path(a.out))


if __name__ == "__main__":
    sys.exit(main())
