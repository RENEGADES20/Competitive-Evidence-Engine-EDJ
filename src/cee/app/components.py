"""UI components for every page. Look and colours: docs/DESIGN.md.

All extra CSS is the CSS constant below (injected once per page by inject_css). Components
return nothing and draw with Streamlit built-ins or small HTML blocks. No custom JavaScript.
"""
from __future__ import annotations

from html import escape
from urllib.parse import quote

import streamlit as st

from cee.answer.validate import TIER_LABELS

# Palette (contrast pairs in docs/DESIGN.md)
INK, PAPER, SURFACE, MUTED, LINE = "#1C2321", "#F3F1EA", "#FFFFFF", "#57534E", "#D6D3CB"
LIME, ORANGE, SUNKEN = "#D4F53C", "#C2410C", "#ECEAE3"

# tier -> (background, text). The text label is always shown; colour is only a second cue.
TIER_COLORS = {
    1: (INK, LIME),            # licensed
    2: ("#E7E5DE", INK),       # filing
    3: ("#E0E7FF", "#3730A3"),  # IR
    4: ("#FFEDD5", "#9A3412"),  # trade press (indicative only)
    5: ("#F3E8FF", "#6B21A8"),  # research
}

CSS = f"""
<style>
.cee-mono{{font-family:'JetBrains Mono',monospace}}
.cee-ticker{{background:{INK};color:#F5F5F4;overflow:hidden;white-space:nowrap;border-radius:6px;margin-bottom:1.4rem}}
.cee-ticker .track{{display:inline-block;padding:.5rem 0;animation:cee-scroll 45s linear infinite;
  font-family:'JetBrains Mono',monospace;font-size:.78rem;letter-spacing:.08em;font-weight:600}}
.cee-ticker:hover .track{{animation-play-state:paused}}
.cee-ticker span{{margin:0 1.1rem}} .cee-ticker .sep{{color:{LIME}}}
@keyframes cee-scroll{{from{{transform:translateX(0)}}to{{transform:translateX(-50%)}}}}
@media (prefers-reduced-motion:reduce){{.cee-ticker .track{{animation:none}}}}
.cee-eyebrow{{font-family:'JetBrains Mono',monospace;letter-spacing:.16em;font-size:.78rem;color:{MUTED};
  display:flex;align-items:center;gap:.8rem;text-transform:uppercase}}
.cee-eyebrow:before{{content:'';width:40px;height:2px;background:{ORANGE}}}
.cee-hero{{font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:3rem;line-height:1.05;color:{INK};margin:.5rem 0 .6rem}}
.cee-hero em{{font-style:normal;color:{ORANGE}}}
.cee-card{{background:{INK};color:#F5F5F4;border-radius:14px;padding:1.3rem 1.5rem;transform:rotate(2deg);
  box-shadow:0 18px 36px rgba(28,35,33,.18);margin-top:1.2rem}}
.cee-card .k{{font-family:'JetBrains Mono',monospace;font-size:.72rem;letter-spacing:.1em;color:#D6D3D1}}
.cee-card .v{{font-family:'Space Grotesk',sans-serif;font-size:1.45rem;white-space:nowrap;font-weight:700;margin:.9rem 0 1rem;color:{LIME}}}
.cee-card .row{{display:flex;gap:1.6rem;flex-wrap:wrap}}
.cee-card .row b{{display:block;font-family:'Space Grotesk',sans-serif;font-size:1.3rem;color:#F5F5F4}}
.cee-claim{{background:{SURFACE};border:1px solid {LINE};border-radius:12px;padding:.95rem 1.1rem;margin-bottom:.7rem;color:{INK}}}
.cee-claim .n{{font-family:'JetBrains Mono',monospace;font-weight:700;background:{LIME};color:{INK};
  padding:.05rem .4rem;border-radius:4px;margin-right:.55rem}}
.cee-claim .lbl{{font-family:'JetBrains Mono',monospace;font-size:.72rem;letter-spacing:.1em;color:{MUTED}}}
.cee-claim .src{{color:{MUTED};font-size:.85rem;margin-top:.35rem}}
.cee-chip{{display:inline-flex;gap:.45rem;align-items:center;padding:.18rem .3rem .18rem .65rem;border:1px solid {INK};
  border-radius:999px;margin:.5rem .35rem 0 0;background:{SURFACE}}}
.cee-chip a,.cee-chip .id{{font-family:'JetBrains Mono',monospace;font-size:.78rem;color:{INK} !important;text-decoration:none !important}}
.cee-chip:hover{{background:{LIME}}}
.cee-cite{{display:inline-flex;flex-direction:column;vertical-align:top;margin:0 .6rem 0 0}}
.cee-cite .cee-chip{{margin-right:0;align-self:flex-start}}
.cee-cite-src{{font-size:.78rem;color:{MUTED};margin:.25rem 0 0 .4rem;max-width:26rem}}
.cee-tier{{font-family:'JetBrains Mono',monospace;font-size:.7rem;letter-spacing:.04em;text-transform:uppercase;
  padding:.1rem .5rem;border-radius:999px;font-weight:700;white-space:nowrap}}
.cee-flag{{font-family:'JetBrains Mono',monospace;font-size:.72rem;color:#9A3412;background:#FFEDD5;padding:.1rem .45rem;border-radius:4px}}
.cee-box{{border-radius:12px;padding:.85rem 1.1rem;margin:.7rem 0}}
.cee-box b.l{{font-family:'JetBrains Mono',monospace;font-size:.8rem;letter-spacing:.06em}}
.cee-caveat{{background:#FFF7ED;border-left:4px solid {ORANGE};color:#7C2D12}}
.cee-gap{{background:{SURFACE};border:1.5px dashed {INK};color:{INK}}}
.cee-behavior{{display:flex;align-items:baseline;gap:.7rem;margin-top:1.2rem}}
.cee-behavior h2 a{{display:none}} .cee-behavior h2{{width:auto !important;font-family:'Space Grotesk',sans-serif;font-weight:700;color:{INK};padding:0 !important;margin:0}}
.cee-behavior .code{{font-family:'JetBrains Mono',monospace;font-size:.72rem;color:{INK};border:1px solid {INK};padding:.05rem .4rem;border-radius:4px}}
.cee-meta{{font-family:'JetBrains Mono',monospace;font-size:.78rem;color:{MUTED};line-height:1.7}}
.cee-passage{{background:{SURFACE};border:1px solid {LINE};border-left:4px solid {LIME};border-radius:12px;
  padding:1rem 1.2rem;white-space:pre-wrap;color:{INK};font-size:.95rem;line-height:1.6}}
.cee-cell{{font-family:'JetBrains Mono',monospace;font-size:.78rem;border-radius:8px;padding:.5rem .7rem;display:inline-block;min-width:8.5rem;margin:.2rem}}
.cee-cell.covered{{background:{INK};color:{LIME}}}
.cee-cell.thin{{background:#FFEDD5;color:#9A3412;border:1px solid #FDBA74}}
.cee-cell.empty{{background:{SURFACE};color:{MUTED};border:1.5px dashed {MUTED}}}
.cee-grid{{border-collapse:separate;border-spacing:.3rem;width:100%}}
.cee-grid th{{font-family:'JetBrains Mono',monospace;font-size:.72rem;letter-spacing:.06em;color:{MUTED};text-align:left;font-weight:600;padding:.2rem .3rem}}
.cee-grid td{{vertical-align:top;padding:0}}
.cee-grid .cee-cell{{display:block;min-width:0;margin:0;padding:.45rem .5rem;font-size:.68rem;line-height:1.4;white-space:nowrap}}
.cee-gridwrap{{overflow-x:auto}}
.cee-grid .rowlbl{{font-family:'Space Grotesk',sans-serif;font-weight:700;color:{INK};padding:.4rem .3rem;white-space:nowrap}}
.cee-grid .rowlbl small{{display:block;font-family:'JetBrains Mono',monospace;font-weight:400;font-size:.68rem;color:{MUTED};white-space:normal}}
.cee-grid .na{{display:block;color:{MUTED};font-size:.68rem;padding:.5rem .5rem;white-space:nowrap}}
.cee-empty{{border:1.5px dashed {LINE};border-radius:12px;padding:1.4rem;color:{MUTED};text-align:center}}
.cee-footer{{margin-top:3rem;padding-top:.8rem;border-top:1px solid {LINE};display:flex;justify-content:space-between;
  font-family:'JetBrains Mono',monospace;font-size:.75rem;color:{MUTED};letter-spacing:.04em}}
.cee-sample{{background:{LIME};color:{INK};font-family:'JetBrains Mono',monospace;font-weight:700;font-size:.78rem;
  letter-spacing:.08em;padding:.35rem .7rem;border-radius:6px;display:inline-block}}
[class*="st-key-placeholder"]{{background:{SUNKEN};border:1.5px dashed #A8A29E;border-radius:12px;padding:.8rem 1rem;cursor:not-allowed}}
[class*="st-key-placeholder"] *{{pointer-events:none}}
[class*="st-key-placeholder"] input,[class*="st-key-placeholder"] button,[class*="st-key-placeholder"] [data-baseweb="select"] > div{{background:{SUNKEN} !important;color:{MUTED} !important}}
[class*="st-key-placeholder"] label,[class*="st-key-placeholder"] label p{{color:{MUTED} !important;opacity:1 !important}}
[data-testid="stCaptionContainer"],[data-testid="stCaptionContainer"] p,[data-testid="stCaptionContainer"] a{{color:{MUTED} !important;opacity:1 !important}}
.cee-soon{{font-family:'JetBrains Mono',monospace;font-size:.75rem;letter-spacing:.06em;color:{MUTED}}}
.cee-trace{{font-family:'JetBrains Mono',monospace;font-size:.8rem;line-height:1.9;color:{INK}}}
.cee-trace .m{{display:inline-block;width:1.5rem;font-weight:700}}
.cee-trace .running .m{{color:{ORANGE}}} .cee-trace .done .m{{color:#3F6212}}
.cee-trace .skipped{{color:{MUTED}}} .cee-trace .failed{{color:#B91C1C;font-weight:700}}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def _html(s: str, where=None) -> None:
    # One raw-HTML line: a blank line in stored text would end the HTML block and let Markdown
    # parse the rest ("$407 million to $4.7 billion" became LaTeX, #99). Entities keep the text.
    (where or st).markdown(s.replace("$", "&#36;").replace("\n", "&#10;"), unsafe_allow_html=True)


def tier_badge_html(tier: int | None) -> str:
    label = TIER_LABELS.get(tier, "tier unknown") if tier else "tier unknown"
    bg, fg = TIER_COLORS.get(tier, (SUNKEN, INK))
    prefix = f"T{tier} · " if tier else ""
    return f'<span class="cee-tier" style="background:{bg};color:{fg}">{prefix}{escape(label)}</span>'


def citation_chip_html(chunk_id: str, tier: int | None, link: bool = True, label: str = "") -> str:
    """The link text is exactly the chunk_id (scripts/verify_cee.py reads it).

    label is this citation's own source label; it sits under the chip so each citation says
    where it comes from. A citation that is not in the retrieved set gets link=False.
    """
    cid = escape(chunk_id)
    target = (f'<a href="?chunk={quote(chunk_id)}" target="_blank">{cid}</a>' if link
              else f'<span class="id">{cid}</span>')
    chip = f'<span class="cee-chip">{target}{tier_badge_html(tier)}</span>'
    return f'<span class="cee-cite">{chip}<span class="cee-cite-src">{escape(label)}</span></span>' if label else chip


def ticker(items: list[str]) -> None:
    row = "".join(f"<span>{escape(t)}</span><span class='sep'>&middot;</span>" for t in items)
    _html(f'<div class="cee-ticker"><div class="track">{row}<span aria-hidden="true">{row}</span></div></div>')


def eyebrow(text: str) -> None:
    _html(f'<div class="cee-eyebrow">{escape(text)}</div>')


def hero(before: str, accent: str, after: str) -> None:
    _html(f'<div class="cee-hero">{escape(before)} <em>{escape(accent)}</em> {escape(after)}</div>')


def snapshot_card(snapshot: str, stats: list[tuple[str, str]]) -> None:
    row = "".join(f"<div><span class='k'>{escape(k)}</span><b>{escape(v)}</b></div>" for k, v in stats)
    _html(f'<div class="cee-card"><div class="k">CORPUS SNAPSHOT</div><div class="v">{escape(snapshot)}</div>'
          f'<div class="row">{row}</div></div>')


def behavior_header(text: str, code: str) -> None:
    """A real heading: the verify driver finds it by role and name."""
    _html(f'<div class="cee-behavior"><h2>{escape(text)}</h2><span class="code">{escape(code)}</span></div>')


def claim_card(n: int, text: str, chips: list[tuple], source_label: str = "",
               flags: list[str] | None = None, label: str = "", note: str = "", link: bool = True) -> None:
    """chips: (chunk_id, tier) or (chunk_id, tier, source_label, linkable) per citation."""
    chip_html = "".join(citation_chip_html(c[0], c[1], link and (c[3] if len(c) > 3 else True),
                                           c[2] if len(c) > 2 else "") for c in chips)
    flag_html = "".join(f' <span class="cee-flag">{escape(f)}</span>' for f in flags or [])
    top = f'<div class="lbl">{escape(label)}</div>' if label else ""
    src = f'<div class="src">{escape(source_label)}</div>' if source_label else ""
    extra = f'<div class="src"><b>Differs because:</b> {escape(note)}</div>' if note else ""
    _html(f'<div class="cee-claim">{top}<span class="n">{n:02d}</span>{escape(text)}{flag_html}'
          f'<div>{chip_html}</div>{src}{extra}</div>')


def caveat_box(text: str) -> None:
    """Always expanded: never inside an expander, tab or tooltip."""
    _html(f'<div class="cee-box cee-caveat"><b class="l">Caveat:</b> {escape(text)}</div>')


def gap_box(what: str, suggested_source: str = "") -> None:
    """Always expanded. Starts with 'Gap:' (scripts/verify_cee.py reads it)."""
    fill = f"<br><b>Would be filled by:</b> {escape(suggested_source)}" if suggested_source else ""
    _html(f'<div class="cee-box cee-gap"><b class="l">Gap:</b> {escape(what)}{fill}</div>')


def source_header(title: str, tier: int | None, meta: list[str]) -> None:
    _html(f'<div class="cee-eyebrow">Stored source</div>'
          f'<div class="cee-behavior"><h2>{escape(title)}</h2>{tier_badge_html(tier)}</div>'
          f'<div class="cee-meta">{" &nbsp;|&nbsp; ".join(escape(m) for m in meta)}</div>')


def passage(text: str) -> None:
    _html(f'<div class="cee-passage">{escape(text)}</div>')


def coverage_cell_html(state: str, text: str) -> str:
    """state: covered | thin | empty. The state word is always part of the text; \\n in text is a line break."""
    body = escape(text).replace("\n", "<br>")
    return f'<span class="cee-cell {state}">{escape(state.upper())}<br>{body}</span>'


def coverage_cell(state: str, text: str) -> None:
    _html(coverage_cell_html(state, text))


TRACE_MARKS = {"running": "…", "done": "✓", "skipped": "–", "failed": "✗"}


def trace_lines(steps: list[tuple[str, str]], where=None) -> None:
    """One line per pipeline stage: (state, text). The mark is a second cue; the text says it all."""
    rows = "".join(f'<div class="{escape(state)}"><span class="m">{TRACE_MARKS.get(state, "·")}</span>'
                   f'{escape(text)}</div>' for state, text in steps)
    _html(f'<div class="cee-trace">{rows}</div>', where)


def coverage_grid(columns: list[str], rows: list[tuple[str, str, list[tuple[str, str] | None]]]) -> None:
    """rows: (label, note, cells) with one (state, text) per column, or None where the source
    registry does not expect that document type for the row."""
    head = "".join(f"<th>{escape(c)}</th>" for c in columns)
    body = ""
    for label, note, cells in rows:
        sub = f"<small>{escape(note)}</small>" if note else ""
        tds = "".join(f'<td>{coverage_cell_html(*c)}</td>' if c else '<td><span class="na">not tracked</span></td>'
                      for c in cells)
        body += f'<tr><th class="rowlbl" scope="row">{escape(label)}{sub}</th>{tds}</tr>'
    _html(f'<div class="cee-gridwrap"><table class="cee-grid"><thead><tr><th></th>{head}</tr></thead>'
          f'<tbody>{body}</tbody></table></div>')


def empty_state(text: str) -> None:
    _html(f'<div class="cee-empty">{escape(text)}</div>')


def sample_banner() -> None:
    _html('<span class="cee-sample">SAMPLE, NOT FROM THE CORPUS</span>')


def placeholder(key: str, issue: int | str, title: str):
    """A disabled area that a later issue fills. Returns the container; put only disabled widgets in it."""
    box = st.container(key=f"placeholder-{key}")
    box.markdown(f'<div class="cee-soon">{escape(title.upper())} · Coming soon (#{issue})</div>',
                 unsafe_allow_html=True)
    return box


@st.cache_data(ttl=60, show_spinner=False)
def corpus_stats() -> dict:
    from cee.db import connect
    with connect() as c:
        snap = c.execute("SELECT obj_description('public.documents'::regclass) AS s").fetchone()["s"]
        d = c.execute("SELECT count(*) n, count(DISTINCT entity_id) e, max(published_at) latest FROM documents").fetchone()
        k = c.execute("SELECT count(*) n FROM chunks").fetchone()["n"]
    return {"snapshot": snap or "none (built locally)", "docs": d["n"], "firms": d["e"],
            "latest": str(d["latest"] or "none"), "chunks": k}


def footer() -> None:
    s = corpus_stats()
    _html(f'<div class="cee-footer"><span>SNAPSHOT {escape(s["snapshot"])}</span>'
          f'<span>COMPETITIVE EVIDENCE ENGINE · EVIDENCE ONLY</span></div>')
