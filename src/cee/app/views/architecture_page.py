"""Architecture page (#270): the W11 pipeline (ADR-021) as a diagram; each module explains itself on
hover and keyboard focus, and the same text is listed under the diagram (touch, screen readers).

Text: src/cee/app/architecture.py (also the README diagram's labels). Inline HTML and CSS only (st.html drops
inline SVG, so arrows are divs): no script, no network fetch, no firm figures.
"""
from __future__ import annotations

from html import escape

import streamlit as st

from cee.app import components as ui
from cee.app.architecture import EDGES, KINDS, MODULES, PRINCIPLE, Module

# Layout: four columns (corpus, find, read, write), nodes stacked top to bottom.
NODE_W, NODE_H, COL_X, ROW_Y0, ROW_DY = 200, 66, (10, 270, 530, 790), 44, 96
CANVAS_W, CANVAS_H = 1000, 420
PLACE = {"S": (0, 0), "I": (0, 1), "DB": (0, 2),
         "Q": (1, 0), "R": (1, 1), "P": (1, 2), "F": (1, 3),
         "X": (2, 0), "C": (2, 1), "M": (2, 2),
         "W": (3, 0), "K": (3, 1), "U": (3, 2)}
GROUPS = ((0, 3, "Corpus (built ahead of time)"), (1, 4, "1. Find the evidence"),
          (2, 3, "2. Read it, decide in code"), (3, 3, "3. Write and check"))
KIND_TAG = {"data": "DATA", "code": "CODE", "ai": "AI", "ai+code": "AI+CODE"}
KIND_CLASS = {"data": "k-data", "code": "k-code", "ai": "k-ai", "ai+code": "k-aicode"}

LIGHT = {"ink": ui.INK, "paper": ui.PAPER, "surface": ui.SURFACE, "muted": ui.MUTED, "line": ui.LINE,
         "sunken": ui.SUNKEN, "lime": ui.LIME, "on_lime": ui.INK, "tip_bg": ui.INK, "tip_fg": "#F5F5F4",
         "focus": ui.ORANGE}
DARK = {"ink": "#F3F1EA", "paper": "#1C2321", "surface": "#262D2B", "muted": "#C9C5BC", "line": "#57534E",
        "sunken": "#303735", "lime": ui.LIME, "on_lime": ui.INK, "tip_bg": "#F3F1EA", "tip_fg": ui.INK,
        "focus": "#FDBA74"}


def _xy(mid: str) -> tuple[int, int]:
    col, row = PLACE[mid]
    return COL_X[col], ROW_Y0 + row * ROW_DY


def _edge_points(a: str, b: str) -> list[tuple[int, int]]:
    """The corners of the arrow from module a to module b (straight down, or right-up/down-right)."""
    (ax, ay), (bx, by) = _xy(a), _xy(b)
    if PLACE[a][0] == PLACE[b][0]:   # same column: straight down
        x = ax + NODE_W // 2
        return [(x, ay + NODE_H), (x, by)]
    y1, y2 = ay + NODE_H // 2, by + NODE_H // 2
    mid = (ax + NODE_W + bx) // 2
    return [(ax + NODE_W, y1), (mid, y1), (mid, y2), (bx, y2)]


def edge_html(a: str, b: str) -> str:
    """An arrow as plain divs (st.html drops inline SVG): one div per straight segment, then a head."""
    pts = _edge_points(a, b)
    out = []
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        if x1 == x2 and y1 == y2:
            continue
        if y1 == y2:
            out.append(f'<div class="seg" style="left:{min(x1, x2)}px;top:{y1 - 1}px;width:{abs(x2 - x1)}px;height:2px"></div>')
        else:
            out.append(f'<div class="seg" style="left:{x1 - 1}px;top:{min(y1, y2)}px;width:2px;height:{abs(y2 - y1)}px"></div>')
    (px, py), (x, y) = pts[-2], pts[-1]
    if px == x:   # vertical: head points down
        out.append(f'<div class="head down" style="left:{x - 5}px;top:{y - 8}px"></div>')
    else:         # horizontal: head points right
        out.append(f'<div class="head right" style="left:{x - 8}px;top:{y - 5}px"></div>')
    return f'<div class="edge" data-edge="{a}-{b}" aria-hidden="true">{"".join(out)}</div>'


def css(t: dict) -> str:
    return f"""<style>
.arch-wrap{{overflow-x:auto;padding-bottom:.5rem}}
.arch{{position:relative;width:{CANVAS_W}px;height:{CANVAS_H}px;font-family:Inter,sans-serif;color:{t['ink']}}}
.arch .grp{{position:absolute;box-sizing:border-box;border:1.5px dashed {t['line']};border-radius:10px}}
.arch .grp-t{{position:absolute;left:8px;top:5px;white-space:nowrap;font:600 10.5px 'JetBrains Mono',monospace;letter-spacing:.02em;color:{t['muted']}}}
.arch .seg{{position:absolute;background:{t['ink']}}}
.arch .head{{position:absolute;width:0;height:0}}
.arch .head.down{{border-left:5px solid transparent;border-right:5px solid transparent;border-top:8px solid {t['ink']}}}
.arch .head.right{{border-top:5px solid transparent;border-bottom:5px solid transparent;border-left:8px solid {t['ink']}}}
.arch-node{{position:absolute;box-sizing:border-box;width:{NODE_W}px;height:{NODE_H}px;padding:6px 10px;
 border-radius:8px;cursor:help;outline:none;line-height:1.2}}
.arch-node b{{display:block;font:700 14px 'Space Grotesk',sans-serif;padding-right:34px}}
.arch-node.k-aicode b{{padding-right:40px}}
.arch-node .sub{{display:block;font-size:11.5px;color:inherit;opacity:.85}}
.arch-node .tag{{position:absolute;right:6px;top:5px;font:700 9px 'JetBrains Mono',monospace;letter-spacing:.06em}}
.arch-node.k-data{{background:{t['sunken']};border:1.5px solid {t['muted']};border-radius:18px}}
.arch-node.k-code{{background:{t['surface']};border:2px solid {t['ink']}}}
.arch-node.k-ai{{background:{t['lime']};color:{t['on_lime']};border:1.5px solid {t['on_lime']}}}
.arch-node.k-aicode{{background:{t['lime']};color:{t['on_lime']};border:2px dashed {t['on_lime']}}}
.arch-node:hover,.arch-node:focus{{z-index:5;box-shadow:0 0 0 3px {t['focus']}}}
.arch-tip{{visibility:hidden;opacity:0;position:absolute;left:calc(100% + 10px);top:-2px;width:300px;z-index:6;
 background:{t['tip_bg']};color:{t['tip_fg']};border-radius:8px;padding:10px 12px;font-size:12.5px;line-height:1.4;
 box-shadow:0 6px 18px rgba(0,0,0,.25);transition:opacity .12s;pointer-events:none}}
.arch-tip.up{{top:auto;bottom:-2px}}
.arch-tip.left{{left:auto;right:calc(100% + 10px)}}
.arch-tip p{{margin:.35em 0 0;font-size:12.5px;line-height:1.4}}
.arch-tip .k{{font:700 10px 'JetBrains Mono',monospace;letter-spacing:.06em;opacity:.8}}
.arch-node:hover .arch-tip,.arch-node:focus .arch-tip,.arch-node:focus-within .arch-tip{{visibility:visible;opacity:1}}
.arch-legend{{display:flex;flex-wrap:wrap;gap:.6rem 1.2rem;margin:.6rem 0 .2rem;font-size:13px;color:{t['ink']}}}
.arch-legend span{{display:inline-flex;align-items:center;gap:.4rem}}
.arch-legend i{{display:inline-block;width:26px;height:16px;border-radius:4px}}
.arch-legend i.k-data{{background:{t['sunken']};border:1.5px solid {t['muted']};border-radius:8px}}
.arch-legend i.k-code{{background:{t['surface']};border:2px solid {t['ink']}}}
.arch-legend i.k-ai{{background:{t['lime']};border:1.5px solid {t['on_lime']}}}
.arch-legend i.k-aicode{{background:{t['lime']};border:2px dashed {t['on_lime']}}}
.arch-principle{{font:600 15px 'Space Grotesk',sans-serif;margin:.4rem 0 .8rem;color:{t['ink']}}}
.arch-list{{padding-left:1.4rem;color:{t['ink']};font-size:14px}}
.arch-list li{{margin:.15rem 0 .7rem}}
.arch-list .k{{font:700 11px 'JetBrains Mono',monospace;letter-spacing:.06em;color:{t['muted']}}}
.arch-list p{{margin:.1rem 0;font-size:14px}}
</style>"""


def _tip(m: Module) -> str:
    col, row = PLACE[m.id]
    # Beside the node (never below the canvas edge, which would clip): right of the two left columns,
    # left of the two right ones; top-aligned in rows 0-1, bottom-aligned below.
    cls = "arch-tip" + (" left" if col >= 2 else "") + (" up" if row >= 2 else "")
    return (f'<div class="{cls}" role="tooltip" id="tip-{m.id}">'
            f'<span class="k">{escape(KINDS[m.kind].upper())}</span>'
            f'<p class="does">{escape(m.does)}</p>'
            f'<p class="who"><b>Who:</b> {escape(m.who)}</p>'
            f'<p class="rule"><b>Rule:</b> {escape(m.rule)}</p></div>')


def node_html(m: Module) -> str:
    x, y = _xy(m.id)
    return (f'<div class="arch-node {KIND_CLASS[m.kind]}" id="node-{m.id}" data-module="{m.id}" '
            f'tabindex="0" role="button" aria-describedby="tip-{m.id}" style="left:{x}px;top:{y}px">'
            f'<span class="tag">{KIND_TAG[m.kind]}</span><b>{escape(m.label)}</b>'
            f'<span class="sub">{escape(m.sub)}</span>{_tip(m)}</div>')


def diagram_html() -> str:
    groups = []
    for col, rows, title in GROUPS:
        x, top = COL_X[col] - 6, ROW_Y0 - 30
        h = (rows - 1) * ROW_DY + NODE_H + 38
        groups.append(f'<div class="grp" style="left:{x}px;top:{top}px;width:{NODE_W + 12}px;height:{h}px">'
                      f'<span class="grp-t">{escape(title.upper())}</span></div>')
    edges = "".join(edge_html(a, b) for a, b in EDGES)
    nodes = "".join(node_html(m) for m in MODULES)
    return (f'<div class="arch-wrap"><div class="arch" role="group" aria-label="Pipeline diagram">'
            f'{"".join(groups)}{edges}{nodes}</div></div>')


def legend_html() -> str:
    items = "".join(f'<span><i class="{KIND_CLASS[k]}"></i>{escape(v)}</span>' for k, v in KINDS.items())
    return f'<div class="arch-legend" aria-label="Legend">{items}</div>'


def list_html() -> str:
    rows = []
    for m in MODULES:
        rows.append(f'<li id="item-{m.id}"><b>{escape(m.label)}</b> <span class="k">{escape(KINDS[m.kind].upper())}'
                    f'</span><p>{escape(m.does)}</p><p><b>Who:</b> {escape(m.who)}</p>'
                    f'<p><b>Rule:</b> {escape(m.rule)}</p></li>')
    return f'<ol class="arch-list">{"".join(rows)}</ol>'


def page_html(dark: bool = False) -> str:
    return (css(DARK if dark else LIGHT) + f'<p class="arch-principle">{escape(PRINCIPLE)}</p>' + legend_html() + diagram_html())


def _dark() -> bool:
    try:
        return getattr(st.context.theme, "type", None) == "dark"
    except Exception:   # older runtimes or no context: the app's pinned light theme
        return False


def render() -> None:
    ui.eyebrow("How it works")
    st.title("Architecture")
    st.caption("How the engine answers a question. Hover over a box, or move to it with the Tab key, to "
               "see what it does, whether AI or code does it, and the rule it enforces. The same text is "
               "listed under the diagram.")
    dark = _dark()
    st.html(page_html(dark))
    st.markdown("#### Every module")
    st.html(css(DARK if dark else LIGHT) + list_html())
