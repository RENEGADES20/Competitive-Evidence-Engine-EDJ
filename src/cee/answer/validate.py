"""Code-side checks on every answer (specs/answer-citations.md).

Skeleton placeholder, owner: S2 (Jiapeng Liu).
Here: citation check (flag, never drop), code-built source labels, caveat insertion,
coverage note, registry-based suggested sources, number check, empty-retrieval gap/refuse,
uncited grid cells moved to gaps and the per-part check (#215).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from cee.answer.prompt import BOUNDARY_HANDOFF
from cee.answer.schema import Answer, Claim, Gap, Withheld
from cee.config import entities_config
from cee.retrieve.fts import Hit, Query, theme_gaps, theme_label

TIER_LABELS = {1: "licensed", 2: "filing", 3: "IR", 4: "trade press (indicative only)",
               5: "research", 6: "signal"}

SOURCE_NAMES = {
    "10-K": "Form 10-K annual report (SEC EDGAR)", "10-Q": "Form 10-Q quarterly report (SEC EDGAR)",
    "8-K": "Form 8-K current report (SEC EDGAR)", "DEF 14A": "Proxy statement (SEC EDGAR)",
    "20-F": "Form 20-F annual report (SEC EDGAR)", "40-F": "Form 40-F annual report (SEC EDGAR)",
    "6-K": "Form 6-K report (SEC EDGAR)", "adv": "Form ADV (SEC IAPD)",
    "transcript": "earnings-call transcripts", "supplement": "quarterly financial supplement",
    "monthly": "monthly activity reports", "deck": "investor-day presentations",
    "press": "company press releases", "trade": "trade press", "research": "industry research",
}


def _retrieved(hit) -> bool:
    """Dated by the stored copy, the page prints no date (ADR-007 T-09). Test hits may lack the field."""
    return getattr(hit, "date_basis", "source") == "retrieved"


def date_label(hit: Hit) -> str:
    return f"page content as of {hit.published_at}" if _retrieved(hit) else (hit.period_end or hit.published_at)


def source_label(hit: Hit) -> str:
    seg = f" - {hit.segment} segment" if hit.segment else ""
    page = f", p.{hit.page}" if hit.page else ""
    tier = TIER_LABELS.get(hit.source_tier, "?")
    return f"{hit.entity_id or 'Research'} {hit.doc_type}{seg} {date_label(hit)}{page} [{tier}]"


# Boundary (#118, ground rule 6). Rule in specs/answer-citations.md, "Boundary".
WITHHELD_NOTICE = ("A sentence was withheld because it recommended an action for Edward Jones "
                   "(ground rule 6). That decision belongs to the strategy team.")


def _alternation(names: list[str]) -> str:
    return "(?:" + "|".join(re.escape(n) for n in sorted(set(names), key=len, reverse=True)) + ")"


def _normative_patterns() -> list[re.Pattern]:
    edj = _entry("EDJ")
    named = [edj["name"].split(" (")[0], *edj.get("aliases", []), "EJ", "EDJ"]
    # Not "we" / "you": in transcripts they are the speaking firm or an analyst ("we should expect").
    addressed = ["the home firm"]
    firm = _alternation(named + addressed)
    act = (r"(?:should|ought to|would benefit from|might want to|may want to|"
           r"could (?:replicate|adopt|copy|emulate|consider|learn from|follow))")
    # Filings say "Edward Jones must maintain net capital": must / needs to only for addressed subjects.
    duty = rf"{_alternation(addressed)}\s+(?:must|needs? to)"
    return [re.compile(rf"\b{firm}\s+{act}\b", re.I),
            re.compile(rf"\b{duty}\b", re.I),
            re.compile(r"\b(?:we|I)\s+(?:would\s+)?(?:recommend|suggest|advise)\b", re.I),
            re.compile(r"\bit (?:would be|is) (?:wise|advisable|prudent|recommended)\b", re.I),
            re.compile(rf"\b(?:recommend(?:s|ed)?|suggest(?:s|ed)?|advise[sd]?)\s+(?:that\s+)?{firm}\b", re.I)]


def is_normative(text: str) -> bool:
    """A sentence that tells the home firm what to do. The hand-off sentence itself is not."""
    if text.strip() == BOUNDARY_HANDOFF:
        return False
    unquoted = _QUOTED.sub(" ", text)     # a firm's or analyst's own words, quoted, are evidence
    return any(p.search(unquoted) for p in _normative_patterns())


_QUOTED = re.compile(r'"[^"]*"|“[^”]*”')


def withhold_normative(answer: Answer) -> Answer:
    """Keep normative claims out of the shown answer (kept in `withheld`), and re-judge the answer
    as answer_with_boundary. Never silent: the app shows WITHHELD_NOTICE in their place."""
    for field in ("claims", "adjacent"):
        kept = []
        for claim in getattr(answer, field):
            if is_normative(claim.text):
                answer.withheld.append(Withheld(text=claim.text, chunk_ids=claim.chunk_ids))
            else:
                kept.append(claim)
        setattr(answer, field, kept)
    if answer.withheld and answer.behavior == "answer":
        answer.behavior = "answer_with_boundary"
    return answer


def ensure_handoff(answer: Answer) -> Answer:
    """A boundary answer always ends with the hand-off sentence; code adds it when missing."""
    if answer.behavior != "answer_with_boundary" or any(c.text.strip() == BOUNDARY_HANDOFF for c in answer.claims):
        return answer
    cited = list(dict.fromkeys(c for claim in answer.claims for c in claim.chunk_ids))
    answer.claims.append(Claim(text=BOUNDARY_HANDOFF, chunk_ids=cited))
    return answer


def check_citations(answer: Answer, hits: list[Hit], derived=None) -> Answer:
    """`derived` (#247): [(value, input chunk ids)] of the matrix's accepted derivations, for the number
    check. The hand-off sentence is standard wording, not evidence: never flagged no_citation (#247 B2,
    an evidence-free boundary answer)."""
    answer = move_uncited_cells(ensure_handoff(withhold_normative(answer)))
    by_id = {h.chunk_id: h for h in hits}
    for claim in [*answer.claims, *answer.adjacent]:
        known = [c for c in claim.chunk_ids if c in by_id]
        if not claim.chunk_ids:
            if claim.text.strip() != BOUNDARY_HANDOFF:
                claim.flags.append("no_citation")
        elif len(known) < len(claim.chunk_ids):
            claim.flags.append("unmatched_citation")
        claim.source_label = "; ".join(dict.fromkeys(source_label(by_id[c]) for c in known))
    return check_dates(check_numbers(answer, hits, derived), hits)


# Parts (#215). Rules in specs/answer-citations.md, "Every part answered or named as a gap".
UNCITED_CELL_GAP = "{firm} - {dimension}: no cited evidence in this answer."
PART_NO_EVIDENCE = "No evidence retrieved for: {part}"
PART_NOT_ANSWERED = "Not answered from the evidence retrieved for: {part}"
_CELL = re.compile(r"^\s*(?P<dim>[^:\n]{1,80}?)\s+[-–—]\s+(?P<firm>[^:\n]{1,80}?)\s*:")


def _firm_names() -> list[str]:
    cfg = entities_config()
    names = []
    for e in cfg["entities"] + (cfg.get("expansion") or []):
        names += [e["name"], e["name"].split(" (")[0], *e.get("aliases", [])]
    return names


def _is_firm(text: str) -> bool:
    t = " ".join(text.split())
    for n in _firm_names():
        if (t == n) if (n.isupper() and len(n) <= 5) else (t.lower() == n.lower()):
            return True
    return False


def _norm(text: str) -> str:
    return " ".join(text.lower().split())


def move_uncited_cells(answer: Answer) -> Answer:
    """A grid cell ("<Dimension> - <Firm>: ...") the model wrote with no chunk_ids is not a claim
    (ground rule 1): it moves to gaps. The gap text is built by code and true by construction (the
    model gave no citation); the model's text is kept in claim_text, never shown. When the model
    already wrote a gap for that cell, that gap keeps its text and gets the flag. A claim with
    citations, even unmatched ones, is never moved (it is flagged in check_citations)."""
    kept = []
    for claim in answer.claims:
        m = _CELL.match(claim.text)
        if claim.chunk_ids or not m or not _is_firm(m["firm"]):
            kept.append(claim)
            continue
        firm, dim = " ".join(m["firm"].split()), " ".join(m["dim"].split())
        head = _norm(f"{firm} - {dim}:")
        same = next((g for g in answer.gaps if _norm(g.what).startswith(head)), None)
        if same is not None:
            if "uncited_cell" not in same.flags:
                same.flags.append("uncited_cell")
            same.claim_text = "\n".join(t for t in (same.claim_text, claim.text) if t)
            same.part_id = same.part_id or claim.part_id
        else:
            answer.gaps.append(Gap(what=UNCITED_CELL_GAP.format(firm=firm, dimension=dim),
                                   part_id=claim.part_id, flags=["uncited_cell"], claim_text=claim.text))
    answer.claims = kept
    return answer


def _part_label(part, question: str) -> str:
    text = " ".join((part.text or question).split())
    firms = ", ".join(_short_name(f) for f in part.firms)
    if firms and question and _norm(text) == _norm(question):
        text = f"{text} ({firms})"
    if is_normative(text):   # ground rule 6: code never prints a "should"
        text = f"part {part.id}" + (f" ({firms})" if firms else "")
    return text


def _part_pools(plan) -> dict[str, int]:
    """Each part's candidate pool before exclusion (planner.search_subquestions), when known. A
    competitor sub-question the floor across competitors emptied (#245) reads as 0: its candidates
    were below the floor, so nothing usable was found for it."""
    return {s["id"]: 0 if s.get("floor_emptied") else s["pool"]
            for s in getattr(plan, "searched", None) or [] if "pool" in s}


def _matrix_state(pid: str, answer: Answer, matrix, known: dict) -> str | None:
    """#247 B3: a comparison sub-question is covered by its aspect's comparison claim (part_id the
    aspect or one of its cells, citing a retrieved chunk) or by the comparison_missing gap; a proxy
    sub-question by any claim / adjacent item on its aspect, or by design when its cell holds nothing
    (the asked aspect carries the gap)."""
    from cee.answer.matrix import holds
    cell = matrix.cells.get(pid) if matrix is not None else None
    if cell is None:
        return None
    a = matrix.aspect(cell.aspect_id)
    own = {a.id} | {c.id for c in matrix.cells.values() if c.aspect_id == a.id}
    if a.kind == "comparison":
        if any(c.part_id in own and any(k in known for k in c.chunk_ids) for c in answer.claims) \
                or any(g.part_id in own and "comparison_missing" in g.flags for g in answer.gaps):
            return "comparison"
    if getattr(a, "proxy", False):
        if any(c.part_id in own and any(k in known for k in c.chunk_ids) for c in [*answer.claims, *answer.adjacent]):
            return "proxy"
        if not holds(cell):
            return "proxy_by_design"
    if not holds(cell):
        # #247 part 2: an empty cell outside its aspect's firm scope gets no gap by design (Q19); an
        # empty competitor cell is covered by its aspect's folded competitors gap
        from cee.answer.matrix import in_gap_scope
        if not in_gap_scope(a, cell):
            return "out_of_scope"
        if any(g.part_id == a.id and "matrix_competitors_not_found" in g.flags for g in answer.gaps) \
                and cell.role == "competitor":
            return "competitors_gap"
    return None


def part_coverage(answer: Answer, plan, hits: list[Hit], matrix=None, synthesis: bool = False) -> dict[str, str]:
    """{part_id: model | citation | handoff | code_gap | comparison | proxy | proxy_by_design | none}
    for the plan's parts (#215; the matrix states #247 B3).
    model: a cited claim / adjacent item or a gap names the part; citation: an item without a valid
    part_id cites a passage found for the part (v3 outputs, the mock); handoff: a normative part in
    a boundary answer, covered by the hand-off sentence; code_gap: check_parts added a gap.
    #292 synthesis (prompt v7): aspect: a cited sentence with the part's aspect id cites one of the cell's counting
    items or derivation inputs (one sentence may cover several cells)."""
    ids = [p.id for p in plan.parts]
    known = {h.chunk_id: h for h in hits}

    def found_for(chunk_id: str, pid: str) -> bool:
        part = getattr(known[chunk_id], "part_id", None)
        if len(ids) == 1:   # one part: every passage but research / peers was found for it
            return part not in ("research", "peers")
        return part == pid

    out = {}
    items = [*answer.claims, *answer.adjacent]
    for p in plan.parts:
        if any(g.part_id == p.id and "part_gap" in g.flags for g in answer.gaps):
            out[p.id] = "code_gap"
        elif any(c.part_id == p.id and any(k in known for k in c.chunk_ids) for c in items) \
                or any(g.part_id == p.id for g in answer.gaps):
            out[p.id] = "model"
        elif any(c.part_id not in ids and c.text.strip() != BOUNDARY_HANDOFF
                 and any(found_for(k, p.id) for k in c.chunk_ids if k in known) for c in items) \
                or (len(ids) == 1 and any(g.part_id not in ids for g in answer.gaps)):
            out[p.id] = "citation"
        elif answer.behavior == "answer_with_boundary" and is_normative(p.text) \
                and any(c.text.strip() == BOUNDARY_HANDOFF for c in answer.claims):
            out[p.id] = "handoff"
        elif synthesis and _aspect_sentence(p.id, items, matrix, known):
            out[p.id] = "aspect"
        else:
            out[p.id] = _matrix_state(p.id, answer, matrix, known) or "none"
    return out


def _aspect_sentence(pid: str, items, matrix, known: dict) -> bool:
    """#292: a claim with the cell's aspect id as part_id cites a retrieved chunk of the cell's own evidence."""
    cell = matrix.cells.get(pid) if matrix is not None else None
    if cell is None:
        return False
    own = {k for i in cell.counting_items for k in i.chunk_ids} | set((cell.derivation or {}).get("input_chunk_ids") or [])
    return any(c.part_id == cell.aspect_id and any(k in own and k in known for k in c.chunk_ids) for c in items)


def check_parts(answer: Answer, plan, hits: list[Hit], question: str = "", matrix=None,
                synthesis: bool = False) -> Answer:
    """Every planned part has a cited claim, a cited adjacent item or a gap; a part with none gets
    a code-built gap flagged part_gap (#215, ground rule 3). The wording comes from the part's
    candidate pool before exclusion: 0 -> "No evidence retrieved for", else (or unknown) "Not
    answered from the evidence retrieved for" (its passages may sit under another part). Behavior,
    claims and the model's gaps are not changed. No plan: nothing to check."""
    if plan is None or not plan.parts:
        return answer
    pools = _part_pools(plan)
    for p in plan.parts:
        if part_coverage(answer, plan, hits, matrix, synthesis)[p.id] != "none":
            continue
        wording = PART_NO_EVIDENCE if pools.get(p.id) == 0 else PART_NOT_ANSWERED
        answer.gaps.append(Gap(what=wording.format(part=_part_label(p, question)),
                               suggested_source=_sources_for(p.firms), part_id=p.id, flags=["part_gap"]))
    return answer


# Number check (#52). Rule in specs/answer-citations.md, "Number check".
SCALES = {"thousand": 1e3, "k": 1e3, "million": 1e6, "mn": 1e6, "billion": 1e9, "bn": 1e9, "trillion": 1e12}
_MONTHS = r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
_NUMBER = re.compile(
    r"(?<![\w.#/-])(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?(?![\w-]|\.\d)"
    r"(?:\s*(%|percent\b|thousand\b|million\b|billion\b|trillion\b|bn\b|mn\b|k\b))?", re.I)
_TABLE_SCALE = re.compile(r"in (thousands|millions|billions)\b", re.I)
_DAY_AFTER_MONTH = re.compile(rf"\b{_MONTHS}\s+\d{{1,2}}\b")
_NUMERIC_DATE = re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b")                 # 12/31/2025
_SECTION_LABEL = re.compile(r"\b(?:Item|Note|Part)\s+\d+[A-Z]?\b", re.I)    # Item 11, Note 4


@dataclass
class Figure:
    shown: Decimal      # as written, before scale ("20.4" in "20.4 thousand")
    scale: float        # 1, 1e3, 1e6, ...
    decimals: int       # digits after the point as written

    @property
    def value(self) -> float:
        return float(self.shown) * self.scale


def figures(text: str) -> list[Figure]:
    """Numbers in the text, skipping years, quarter/form/section labels and dates."""
    text = _DAY_AFTER_MONTH.sub(lambda m: m.group(0).rsplit(" ", 1)[0], text)
    text = _SECTION_LABEL.sub(" ", _NUMERIC_DATE.sub(" ", text))
    out = []
    for m in _NUMBER.finditer(text):
        whole, frac, unit = m.group(1), m.group(2), (m.group(3) or "").lower()
        if not frac and not unit and "," not in whole and 1990 <= int(whole) <= 2099:
            continue                                            # a year
        shown = Decimal(whole.replace(",", "") + (f".{frac}" if frac else ""))
        out.append(Figure(shown, SCALES.get(unit.strip(), 1.0), len(frac or "")))
    return out


def _chunk_values(text: str, unscaled: bool = False) -> list[float]:
    """Every number in a cited chunk; a "(in millions)" table header also offers bare numbers at that
    scale. unscaled: a claim figure written without a unit may match the digits shown ("21" vs "21 million")."""
    values = [f.value for f in figures(text)]
    if unscaled:
        values += [float(f.shown) for f in figures(text) if f.scale != 1.0]
    for word in {m.group(1).lower() for m in _TABLE_SCALE.finditer(text)}:
        scale = SCALES[word[:-1]]
        values += [f.value * scale for f in figures(text) if f.scale == 1.0]
    return values


def number_matches(f: Figure, value: float) -> bool:
    """1) within 0.1% of the chunk number, or 2) shows a decimal and is the chunk number rounded half up."""
    if abs(f.value - value) <= 0.001 * abs(value):
        return True
    if f.decimals >= 1:
        q = Decimal(1).scaleb(-f.decimals)
        return Decimal(repr(value / f.scale)).quantize(q, rounding=ROUND_HALF_UP) == f.shown
    return False


def check_numbers(answer: Answer, hits: list[Hit], derived=None) -> Answer:
    """Flag (never drop) a claim with a number not found in any chunk it cites (rule 4). #247 (ADR-021
    rule 2): a figure equal to an accepted derivation's value (same match rule) whose input chunks the
    claim all cites is allowed, flag `computed`; without both inputs cited it stays number_not_found."""
    by_id = {h.chunk_id: h for h in hits}
    for claim in [*answer.claims, *answer.adjacent]:
        cited = [by_id[c].text for c in claim.chunk_ids if c in by_id]
        if not cited:
            continue                                            # already flagged by the citation check
        computed = [v for v, ids in (derived or []) if ids and ids <= set(claim.chunk_ids)]
        scaled = [v for text in cited for v in _chunk_values(text)]
        bare = [v for text in cited for v in _chunk_values(text, unscaled=True)]
        # Table cells often lose their "(in millions)" header to another chunk: a claim figure with a
        # unit may match a chunk figure written without one ("$1,875 million" vs "$ 1,875").
        unitless = [float(f.shown) for text in cited for f in figures(text) if f.scale == 1.0]

        def found(f: Figure) -> bool:
            values = bare if f.scale == 1.0 else scaled + [v * f.scale for v in unitless]
            return any(number_matches(f, v) for v in values)

        def from_inputs(f: Figure) -> bool:
            return any(number_matches(f, v) for v in computed)

        figs = figures(claim.text)
        if not all(found(f) or from_inputs(f) for f in figs):
            if "number_not_found" not in claim.flags:
                claim.flags.append("number_not_found")
        elif any(not found(f) and from_inputs(f) for f in figs) and "computed" not in claim.flags:
            claim.flags.append("computed")
    return answer


# Date check (#155). Rule in specs/answer-citations.md, "Date check".
_MONTH_NUMBERS = {m: i for i, m in enumerate(_MONTHS[3:-1].split("|"), start=1)}
_MONTH_YEAR = rf"({_MONTHS})(?:\s+\d{{1,2}},?)?\s+(\d{{4}})"
_PERIOD_DATE = re.compile(rf"\b(?:(?:quarter|period|year|months|fiscal year|fiscal quarter)\s+ended|as of)\s+{_MONTH_YEAR}", re.I)
_PUBLISHED_DATE = re.compile(rf"\bpublished\s+(?:in\s+|on\s+)?{_MONTH_YEAR}", re.I)
_ANY_DATE = re.compile(_MONTH_YEAR, re.I)


def _year_month(iso: str | None) -> tuple[int, int] | None:
    return (int(str(iso)[:4]), int(str(iso)[5:7])) if iso else None


def _stated(m: re.Match) -> tuple[int, int]:
    return int(m.group(2)), _MONTH_NUMBERS[m.group(1).capitalize()]


def check_dates(answer: Answer, hits: list[Hit]) -> Answer:
    """Flag (never drop) a claim whose stated period or publication month does not match any
    document it cites. Quarter shorthand (3Q26) is not checked: fiscal and calendar quarters differ."""
    by_id = {h.chunk_id: h for h in hits}
    for claim in [*answer.claims, *answer.adjacent]:
        cited = [by_id[c] for c in claim.chunk_ids if c in by_id]
        if not cited:
            continue
        in_text = {_stated(m) for h in cited for m in _ANY_DATE.finditer(h.text)}
        periods = {_year_month(h.period_end) for h in cited} | {_year_month(h.published_at) for h in cited}
        published = {_year_month(h.published_at) for h in cited}
        wrong = any(_stated(m) not in periods | in_text for m in _PERIOD_DATE.finditer(claim.text)) or \
            any(_stated(m) not in published | in_text for m in _PUBLISHED_DATE.finditer(claim.text))
        if wrong and "date_mismatch" not in claim.flags:
            claim.flags.append("date_mismatch")
    return answer


def insert_caveats(answer: Answer, query: Query, hits: list[Hit]) -> Answer:
    """Code, not prompt (specs/answer-citations.md): when the answer cites a substitute for a
    firm the question names (BAC GWIM chunks for MER, equivalence: partial), append that firm's
    caveat from config/entities.yaml."""
    by_id = {h.chunk_id: h for h in hits}
    cited = [by_id[c] for claim in [*answer.claims, *answer.adjacent] for c in claim.chunk_ids if c in by_id]
    for e in entities_config()["entities"]:
        if e["id"] not in [*query.entities, *getattr(query, "theme_peers", [])]                 or not e.get("caveat") or not e.get("parent"):
            continue
        segments = {e.get("reported_as"), e["name"]}
        if any(h.entity_id == e["parent"] and h.segment in segments for h in cited) \
                and e["caveat"] not in answer.caveats:
            answer.caveats.append(e["caveat"])
    return answer


def _short_name(entity_id: str) -> str:
    return _entry(entity_id)["name"].split(" (")[0]


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" + ("" if n == 1 else "s")


def coverage_note(query: Query, hits: list[Hit]) -> str:
    """What this answer rests on, built by code from the retrieved hits (#40): firms searched,
    then per entity / document type / segment the period covered. Same note for every behavior.
    Describes this question's retrieval only, not the whole corpus."""
    searched = ", ".join(_short_name(e) for e in query.entities) or "all documents (no covered firm named)"
    parts = [f"Coverage: searched {searched}."]
    peers = getattr(query, "theme_peers", [])
    if peers:  # home-firm theme rule (#205)
        parts[0] = (f"Coverage: searched {searched}; on the theme also "
                    + ", ".join(_short_name(e) for e in peers) + ".")
    window = getattr(query, "window", None)  # dates below are periods; the window is on publication date (#49)
    if window:
        parts.append(f"Published {window[0]} to {window[1]} only.")
    if query.unmapped:
        parts.append("No documents in the corpus for "
                     + ", ".join(_short_name(e) for e in query.unmapped) + ".")
    if not hits:
        if query.entities or not query.unmapped:
            parts.append("No stored passage matched this question.")
        return " ".join(parts)
    groups: dict[tuple, dict] = {}
    for h in hits:
        retrieved = _retrieved(h)  # undated pages form their own group (ADR-007 T-09)
        g = groups.setdefault((h.entity_id or "Research", h.doc_type, h.segment, retrieved),
                              {"docs": set(), "dates": set()})
        g["docs"].add(h.doc_id)
        g["dates"].add(h.published_at if retrieved else (h.period_end or h.published_at))
    sources = []
    for (entity, doc_type, segment, retrieved), g in groups.items():
        lo, hi = min(g["dates"]), max(g["dates"])
        seg = f", {segment} segment" if segment else ""
        label = doc_type if entity == "Research" and doc_type == "research" else f"{entity} {doc_type}"
        basis = "page content as of " if retrieved else ""
        sources.append(f"{label}{seg} ({basis}{lo if lo == hi else f'{lo} to {hi}'})")
    docs = len({h.doc_id for h in hits})
    parts.append(f"{_plural(len(hits), 'passage')} from {_plural(docs, 'document')}: " + "; ".join(sources) + ".")
    hit_entities = {h.entity_id for h in hits}
    missing = [e for e in query.entities
               if e not in hit_entities and _entry(e).get("parent") not in hit_entities]
    if missing:
        parts.append("No passages for " + ", ".join(_short_name(e) for e in missing) + ".")
    off_theme = [e for e in theme_gaps(query, hits) if e not in missing]  # entity+theme (#117)
    if off_theme:
        parts.append(f"No passages on the theme ({theme_label(query)}) for "
                     + ", ".join(_short_name(e) for e in off_theme) + ".")
    firms_hit = hit_entities - {None}  # research passages (no firm) cover no peer
    peer_gaps = [e for e in peers if e not in firms_hit and _entry(e).get("parent") not in firms_hit]
    if peer_gaps:
        parts.append(f"No passages on the theme ({theme_label(query)}) for "
                     + ", ".join(_short_name(e) for e in peer_gaps) + " (searched on the theme only).")
    return " ".join(parts)


def _entry(entity_id: str) -> dict:
    cfg = entities_config()
    return next(e for e in cfg["entities"] + cfg.get("expansion", []) if e["id"] == entity_id)


def _registry_lookup(entity_id: str) -> tuple[list[tuple[str, str]], set[str]]:
    """(doc_type, source_name) rows in source_registry, and the doc types already ingested."""
    from cee.db import connect

    with connect() as conn:
        rows = conn.execute("SELECT doc_type, source_name FROM source_registry WHERE entity_id = %s "
                            "ORDER BY doc_type, source_name", (entity_id,)).fetchall()
        have = conn.execute("SELECT DISTINCT doc_type FROM documents WHERE entity_id = %s",
                            (entity_id,)).fetchall()
    return [(r["doc_type"], r["source_name"]) for r in rows], {r["doc_type"] for r in have}


registry_lookup = _registry_lookup   # tests swap in a fake; no database needed


def _config_sources(entity_id: str) -> str:
    e = _entry(entity_id)
    return f"{e['name']}: " + ", ".join(SOURCE_NAMES.get(t, t) for t in e.get("expected_sources", []))


def suggested_sources(entity_id: str) -> str:
    """Registry sources expected for the firm minus doc types already in the corpus (#51).
    Firm not in the registry, or the registry unreadable: the config list, as before."""
    try:
        rows, have = registry_lookup(entity_id)
    except Exception:
        rows, have = [], set()
    if not rows:
        return _config_sources(entity_id)
    missing = [name for doc_type, name in rows if doc_type not in have]
    if missing:
        return "Not yet in the corpus: " + "; ".join(missing)
    # #247 part 3 item 5: a firm reported inside a parent (MER -> BAC) with nothing of its own missing
    # names its parent's missing sources, never another firm's
    parent = _entry(entity_id).get("parent")
    if parent and parent != entity_id:
        text = suggested_sources(parent)
        prefix = "Not yet in the corpus: "
        if text.startswith(prefix):
            return f"Not yet in the corpus (parent {_short_name(parent)}): " + text[len(prefix):]
    return ""


def _gap_firm(part_id: str | None) -> str | None:
    """The configured firm a gap's part id names ("a1.MER" -> "MER"); None for aspect-level or research."""
    tail = (part_id or "").rsplit(".", 1)
    if len(tail) != 2:
        return None
    cfg = entities_config()
    ids = {e["id"] for e in cfg["entities"] + cfg.get("expansion", [])}
    return tail[1] if tail[1] in ids else None


def fill_suggested_sources(answer: Answer, query: Query) -> Answer:
    """Fill only gaps whose suggested_source is empty; text the model wrote is kept (#51). #247 part 3
    item 5: a gap on one firm's cell gets only that firm's sources (empty stays empty)."""
    empty = [g for g in answer.gaps if not g.suggested_source.strip()]
    if empty and query.entities:
        text = None
        for g in empty:
            firm = _gap_firm(getattr(g, "part_id", None))
            if firm:
                try:
                    g.suggested_source = suggested_sources(firm)
                except Exception:
                    g.suggested_source = ""
                continue
            if text is None:
                text = _sources_for(query.entities)
            g.suggested_source = text
    return answer


_PARENT_PREFIX = re.compile(r"^Not yet in the corpus(?: \(parent [^)]*\))?: ")


def _sources_for(entities: list[str]) -> str:
    """The registry sources of several firms in one line (one "Not yet in the corpus:" prefix; a
    parent's list keeps its "(parent ...)" note inside the line)."""
    prefix = "Not yet in the corpus: "
    parts = [t for t in (suggested_sources(e) for e in entities) if t]
    parts = [prefix + f"({m.group(0)[len('Not yet in the corpus ('):-3]}) " + t[m.end():]
             if (m := _PARENT_PREFIX.match(t)) and m.group(0) != prefix else t for t in parts]
    registry = [t[len(prefix):] for t in parts if t.startswith(prefix)]
    return "; ".join(([prefix + "; ".join(registry)] if registry else [])
                     + [t for t in parts if not t.startswith(prefix)])


def empty_retrieval_answer(query: Query) -> Answer:
    """No eligible chunks: answer in code, without calling the LLM."""
    if query.unmapped and not query.entities:
        return Answer(answerable=False, behavior="refuse", gaps=[
            Gap(what=f"The corpus holds no documents for {_entry(e)['name']}.",
                suggested_source=suggested_sources(e)) for e in query.unmapped])
    if query.entities:
        return Answer(answerable=False, behavior="gap_with_adjacent", gaps=[
            Gap(what=f"No stored {_entry(e)['name']} passage matches this question.",
                suggested_source=suggested_sources(e)) for e in query.entities])
    return Answer(answerable=False, behavior="refuse", gaps=[
        Gap(what="No stored document matches this question and no covered firm is named.")])
