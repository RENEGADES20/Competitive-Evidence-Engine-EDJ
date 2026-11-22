# Architecture page

A user opens Architecture from the top navigation and sees how the engine answers a question:
the W11 pipeline (ADR-021) as a diagram of data, code steps and AI steps. Hovering over a box,
or moving to it with the Tab key, opens a box that says what the module does, whether AI or code
does it, and the rule it enforces. The same text is listed under the diagram. It replaced the
Design component gallery (#270). The text comes from `src/cee/app/architecture.py`, which also
gives the README diagram its labels.

## Sub-features

- `arch-nav`: the top navigation shows Ask, Coverage, Architecture; no Design.
- `arch-diagram`: every module of `architecture.py` is drawn as a box (`#node-<id>`), with a
  legend (Data, Code step, AI step, AI + code step) and the line "AI reads and writes; code
  decides and checks."
- `arch-hover`: hovering a box shows its explanation (`#tip-<id>`): the kind, what it does, who
  does it, the rule. No box is open before a hover.
- `arch-focus`: Tab moves focus to the next box (`tabindex="0"`), and the focused box shows the
  same explanation.
- `arch-list`: under the diagram, a numbered list holds every module with the same text.
- `arch-clean`: no firm figures, no script, no network fetch; `/design` no longer serves the
  Design gallery.

## How to get to it (user POV)

- Click "Architecture" in the top navigation, or open `/architecture`.

## Driving it

Preconditions: baseline (the page reads no database; the footer does).

- **Open.** Go to `<app>/architecture`. Wait for "Every module" and `#node-F`. The nav has an
  "Architecture" link and no "Design" link.
- **Diagram.** For each module in `architecture.MODULES`, exactly one `#node-<id>` and its label in
  the page text. No `#tip-*` is visible yet.
- **Hover.** Hover `#node-F` (Search). `#tip-F` is visible and its text holds "CODE STEP", the
  module's `does` and its `rule` ("Hard filters live in SQL: ...").
- **Keyboard.** Move the mouse away, focus `#node-C` (Re-search), press Tab. Focus is on
  `#node-M` (Evidence matrix), `#tip-M` is visible and holds its `rule`.
- **List.** `ol.arch-list` has one item per module, each holding that module's rule.
- **No figures.** The page text has no `$<digit>`, "billion" or "million" figure.
- **Old address.** `<app>/design` does not show "Design language".

README images: `python scripts/verify_cee.py shots` (after `launch`) saves answer, source, gap and
architecture (Search hovered) into the run's `shots/` folder and copies them to `docs/assets/`.

## Gotchas

- `st.html` drops inline SVG, so the arrows and group frames are plain `div`s; a later change that
  draws SVG will render nothing. The explanation boxes are CSS only (`:hover`, `:focus`); there is
  no JavaScript and no iframe, so the driver needs no frame handling.
- The explanation opens beside the box (right of the two left columns, left of the two right
  ones) so it is never clipped by the diagram's scroll area.
- `inner_text` of a hidden explanation is empty: read it only after the hover or focus.
- The app's theme is pinned to light; the page switches to a dark token set only when
  `st.context.theme.type` is `dark`.
