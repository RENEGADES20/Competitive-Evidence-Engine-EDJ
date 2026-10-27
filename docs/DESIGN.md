# Design language

Owner: U1. Theme: `.streamlit/config.toml`. Components: `src/cee/app/components.py` (all extra
CSS is the `CSS` constant there). Live gallery: the **Design** page. Issue #67.

## Principles

1. **Evidence first.** The passage and its citation are the loudest things on the page; decoration
   (ticker, snapshot card) sits around them, never between a claim and its source.
2. **Text, then colour.** Every state carries a word (tier name, `Caveat:`, `Gap:`, `COVERED`).
   Colour is a second cue, never the only one.
3. **Nothing hidden.** Caveats and gaps are always expanded: no expander, tab or tooltip.
4. **Nothing normative.** Copy describes what is stored; it never tells the reader what to do.
5. **Built-ins only.** Streamlit widgets and theme, a little CSS in one place, no custom JS,
   no emoji, no mobile layout.

Look: warm paper background, ink text, editorial headings, monospace for IDs and labels,
lime and orange as the two accents.

## Colour and type

| Token | Value | Use |
|---|---|---|
| ink | `#1C2321` | text, primary button, dark card, ticker |
| paper | `#F3F1EA` | page background |
| surface | `#FFFFFF` | claim cards, passage, gap box |
| sunken | `#ECEAE3` | sidebar, placeholders |
| muted | `#57534E` | captions, meta lines, footer |
| line | `#D6D3CB` | borders (not text) |
| lime | `#D4F53C` | accent: claim numbers, snapshot value, tier 1 |
| orange | `#C2410C` | accent: hero word, eyebrow rule, caveat rule |

Type: Inter (body), Space Grotesk (headings, hero), JetBrains Mono (IDs, labels, badges, footer).
Radius 12px for cards, 8px buttons, pill (999px) for chips and badges.

## Components

| Component | Function | Look |
|---|---|---|
| Citation chip | `citation_chip_html` | pill, ink 1px border, white; link text is exactly the `chunk_id` (opens `?chunk=<id>` in a new tab), followed by the tier badge, with that citation's own source label under it (`label`); lime on hover. A citation outside the retrieved set is not linked |
| Tier badge | `tier_badge_html` | mono uppercase pill `T<n> · <label>`; label from `TIER_LABELS` |
| Caveat box | `caveat_box` | `#FFF7ED`, 4px orange left rule, starts with **Caveat:** |
| Gap box | `gap_box` | white, 1.5px dashed ink border, starts with **Gap:**, then **Would be filled by:** |
| Answer behavior header | `behavior_header` | Space Grotesk `h2` (Answer / Answer (evidence only; the judgement is yours) / Not in the corpus / No evidence) plus a mono code tag |
| Claim card | `claim_card` | white card, lime mono number `01`, chips (each with its source label); adjacent claims add `ADJACENT EVIDENCE` and **Differs because:** |
| Source page header | `source_header` | eyebrow `STORED SOURCE`, `h2` title, tier badge, mono meta line (`Section`, `Page`, `Chunk`, `Filed`) |
| Coverage cell | `coverage_cell` | `COVERED` lime on ink; `THIN` orange on peach; `EMPTY` muted on white, dashed |
| Coverage grid | `coverage_grid` | table, one row per firm and one column per document type the source registry expects; each cell is a coverage cell with count and earliest-to-latest date; types the registry does not expect read `not tracked`; rows are the firms in `config/entities.yaml`; thin = fewer documents than one period of the registry's `expected_cadence` (`COVERED_MIN`) |
| Placeholder | `placeholder` | sunken, dashed `#A8A29E` border, `TITLE · Coming soon (#N)`, only disabled widgets, pointer events off |
| Empty state | `empty_state` | dashed line border, centred muted sentence |
| Footer | `footer` | top rule, mono muted: `SNAPSHOT corpus-YYYY-MM-DD` read from the database |
| Ticker, snapshot card | `ticker`, `snapshot_card` | Ask page only. Ticker: ink band of live corpus counts, scrolls with CSS, pauses on hover, still under `prefers-reduced-motion` |

Tier badges:

| Tier | Label | Text / background |
|---|---|---|
| 1 | `T1 · LICENSED` | `#D4F53C` / `#1C2321` |
| 2 | `T2 · FILING` | `#1C2321` / `#E7E5DE` |
| 3 | `T3 · IR` | `#3730A3` / `#E0E7FF` |
| 4 | `T4 · TRADE PRESS (INDICATIVE ONLY)` | `#9A3412` / `#FFEDD5` |
| 5 | `T5 · RESEARCH` | `#6B21A8` / `#F3E8FF` |

Placeholders now: sidebar filters (#63), feedback under an answer (#62),
passage in context on the source page (#53).

## Contrast (WCAG AA, 4.5:1 minimum)

| Pair | Text | Background | Ratio |
|---|---|---|---|
| Body text | `#1C2321` | `#F3F1EA` | 14.2:1 |
| Body text on surface | `#1C2321` | `#FFFFFF` | 16.0:1 |
| Muted text | `#57534E` | `#F3F1EA` | 6.8:1 |
| Muted text on surface | `#57534E` | `#FFFFFF` | 7.6:1 |
| Muted text on placeholder | `#57534E` | `#ECEAE3` | 6.3:1 |
| Sidebar text | `#1C2321` | `#ECEAE3` | 13.3:1 |
| Hero accent | `#C2410C` | `#F3F1EA` | 4.6:1 |
| Ticker text | `#F5F5F4` | `#1C2321` | 14.7:1 |
| Ticker separator, card value | `#D4F53C` | `#1C2321` | 12.9:1 |
| Card label | `#D6D3D1` | `#1C2321` | 10.7:1 |
| Claim number, sample banner | `#1C2321` | `#D4F53C` | 12.9:1 |
| Primary button | `#FFFFFF` | `#1C2321` | 16.0:1 |
| T1 licensed, coverage covered | `#D4F53C` | `#1C2321` | 12.9:1 |
| T2 filing | `#1C2321` | `#E7E5DE` | 12.7:1 |
| T3 IR | `#3730A3` | `#E0E7FF` | 8.1:1 |
| T4 trade press, coverage thin, flag | `#9A3412` | `#FFEDD5` | 6.4:1 |
| T5 research | `#6B21A8` | `#F3E8FF` | 7.4:1 |
| Caveat | `#7C2D12` | `#FFF7ED` | 8.8:1 |
| Gap | `#1C2321` | `#FFFFFF` | 16.0:1 |
| Coverage empty | `#57534E` | `#FFFFFF` | 7.6:1 |

The orange hero word (4.6:1) is the tightest pair; do not lighten it.

Checked with axe-core 4.10.2 (WCAG 2.0/2.1 A and AA) on Ask (with a mock answer), Source, Coverage
and Design: no colour-contrast violations. Two findings remain inside Streamlit's own sidebar
markup (`aria-allowed-attr` on the sidebar, `scrollable-region-focusable`); they come from the
framework and cannot be fixed without custom JavaScript.
