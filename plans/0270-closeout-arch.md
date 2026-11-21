# 0270 - W11 close-out: docs, real screenshots, Architecture page

Issue: #270    Role: TL    Spec: specs/ui.md (also docs/ARCHITECTURE.md, docs/DESIGN.md)

## Goal
A reader of the README or of the app sees how the finished W11 pipeline (ADR-021) works, in the
same diagram in both places, with fresh screenshots from the running app as evidence. The app's
Design page (a component gallery) is replaced by an Architecture page whose diagram explains each
module on hover and keyboard focus. Docs only plus one UI page: no pipeline, retrieval or prompt
change; 0 real calls (mock provider only).

## Pipeline facts the diagram uses (checked against `src/cee/` on 0a7510a)
- Offline: public sources -> ingest (`cee.ingest`: parse, chunk within sections, tag entity /
  segment / date) -> Postgres (documents, chunks, manifest; dated snapshots). pgvector holds
  `chunk_embeddings` only when `CEE_VECTORS=on` (optional SQL, `db/optional/vectors.sql`); the
  diagram says "Postgres (+ optional pgvector)".
- Online (`cee/ask.py` STAGES resolve, decompose, search, extract, research, synthesize, check,
  caveats, log):
  1. resolve firms (code: `retrieve/fts.py resolve`, `config/entities.yaml`);
  2. decompose (AI planner `retrieve/planner.py plan_question` names aspects; code expands
     firms x aspects into sub-questions);
  3. search each sub-question with SQL hard filters on entity / segment / time (code:
     `fts.search`; fts on `main`, hybrid on `exp/hybrid`);
  4. extract per firm (AI map, `answer/extract.py run_map`, strict schema: fact / not_disclosed /
     not_found / different_quantity);
  5. corrective re-search for empty cells, one round (code re-search + AI re-extraction);
  6. evidence matrix (code, `answer/matrix.py finish`: behavior, metric definitions from
     `config/metric_definitions.yaml`, what may be computed, caveats, gaps);
  7. synthesize (AI reduce, `answer/reduce.py call_reduce`, written only from the matrix; or the
     answer is built by code when no call is needed);
  8. check (code, `answer/validate.py`: citations only to retrieved chunk_ids (unmatched ones are
     flagged), number and date checks, caveats inserted by code, gaps named with suggested sources);
  9. app (answer, source labels with tier, source viewer, coverage note) and query_log.
- Principle line: "AI reads and writes; code decides and checks."
The implementer re-checks each name before writing it; a name that differs from the code is
fixed in the module list, not in the code.

## Files to change
- `src/cee/app/architecture.py` (new) - the single source of truth: an ordered list of modules,
  each with `id`, `label` (the exact README node label), `kind` (`data` | `code` | `ai` |
  `ai+code`), `stage` (offline | online), `does` (what it does), `rule` (the rule it enforces,
  e.g. "hard filters live in SQL", "citations only to retrieved chunks"), and the edges between
  ids. Plain Python data (no YAML parser, no new dependency); no firm figures.
- `src/cee/app/views/architecture_page.py` (new) - renders the diagram as inline SVG/HTML built
  from `architecture.py`, through `st.html` (no iframe, no network, no CDN mermaid, no JS):
  - nodes laid out in two bands (offline corpus band, online flow), shaped/coloured by kind
    with a legend (data, code step, AI step) using the tokens in `components.py` / docs/DESIGN.md
    (ink, paper, surface, line, lime, orange); every kind also carries a word, never colour alone;
  - each node is focusable (`tabindex="0"`, `role="button"`, `aria-describedby`) and shows a CSS
    tooltip on `:hover` and `:focus` / `:focus-within` with "what it does / who does it (AI or
    code) / rule"; an SVG `<title>` is kept as a fallback;
  - under the diagram, a plain list of every module with the same three lines (touch and screen
    readers; keeps DESIGN.md principle 3, nothing hidden only in a tooltip);
  - the principle line "AI reads and writes; code decides and checks.";
  - light theme is the app's pinned theme (`.streamlit/config.toml base="light"`); the page reads
    `st.context.theme.type` and swaps to a dark token set when it is `dark`, so text stays readable
    if a user changes the theme in settings.
- `src/cee/app/streamlit_app.py` - nav entry Design -> `st.Page(architecture_page.render,
  title="Architecture", url_path="architecture")`; docstring.
- `src/cee/app/views/design_page.py` - deleted (git history keeps it).
- `tests/test_vectors_optional.py` - its import line swaps `design_page` for `architecture_page`
  (the only other importer; grep of `src/ tests/ scripts/ .claude/` on 0a7510a).
- `tests/test_architecture_page.py` (new) - every module has non-empty id/label/kind/does/rule,
  ids unique, edges point at known ids, kinds in the allowed set; the rendered HTML contains every
  module's label and rule, one `tabindex="0"` per node, no `<script>`, no `http` URL; the README
  mermaid block's node labels (parsed from `README.md`, `<br/>` -> space) equal the module labels,
  same set; the nav has no Design page; no file imports `design_page`.
- `.claude/skills/verify-cee/features/architecture-page.md` (new recipe; entry contract of
  features/README.md) and `features/README.md` (index line). `SKILL.md` feature table row.
- `scripts/verify_cee.py` - `feature_architecture_page`: open `/architecture`, check the title
  and that every module label from `architecture.py` is on the page; hover one node (Search) and
  check its tooltip is visible and its text equals the module's `does`/`rule`; move away, then
  focus a second node by keyboard (Tab / `.focus()`) and check the same; check the plain list
  holds every module; check `/design` no longer serves the Design gallery. Added to `FEATURES`
  and `DRIVERS`. Plus a `screenshots` helper command (`python scripts/verify_cee.py shots`, run
  inside a launched instance) that writes `docs/assets/answer.png`, `source.png`, `gap.png`,
  `architecture.png` at 1280 px width from the same mock app (answer = the answerable question,
  source = its first citation, gap = the no-evidence question, architecture = the page with one
  tooltip open). If a separate command is more than the driver needs, the shots are taken in the
  driver steps and copied; decision recorded in the Progress log.
- `docs/assets/answer.png`, `source.png`, `gap.png` (replaced), `architecture.png` (new).
  `demo.gif` kept as is.
- `README.md` - "How it works" mermaid replaced by the W11 flow in the current style (a
  `Corpus` subgraph, then the online flow) with `classDef data / code / ai` and a legend
  subgraph; node labels exactly the module labels; text under it matches the diagram and the
  principle line; screenshot table (answer, source, gap, architecture) with alt text; the mock
  caption kept; Status re-checked against `docs/results/w11-report.md` and the exp/hybrid report
  (18/30 fts, 22/30 hybrid-norerank, adjudicated; DeepSeek cost line added if missing); code map
  lines for `src/cee/answer/` ("the single LLM call" is stale), `src/cee/retrieve/planner.py`,
  the app pages; documentation map adds `docs/results/w11-report.md`.
- `docs/ARCHITECTURE.md` - "Draft for week 1" header updated; Pipeline section: the same
  diagram as the README (copied, with a pointer to `src/cee/app/architecture.py` as the text
  source) and a short W11 stage list (calls follow the decomposition, ADR-021); Retrieval modes
  says fts on `main`, hybrid / hybrid-norerank on `exp/hybrid`.
- `docs/RUN.md` - section 7: the real-model ask steps describe the W11 calls (planner, one
  extraction call per firm, re-extraction, one reduce call; not "about two calls"); a short
  "Run each retrieval mode" block: fts on `main` (default) and hybrid-norerank on `exp/hybrid`
  (`git switch exp/hybrid`, vectors on per section 1, `RETRIEVAL_MODE` / `--mode`; names checked
  on `exp/hybrid` before writing), Windows and macOS blocks for each; links to the W11 reports.
- `docs/DESIGN.md` - "Live gallery: the Design page" replaced (components live in
  `components.py`; the gallery page was retired in #270); the a11y note keeps its history.
- `specs/ui.md` - page list: `Page "Architecture"` (diagram, hover/focus explanations, plain
  list, no firm figures); acceptance gains "Architecture page: every module explained on hover and
  keyboard focus".
- `docs/NEXT.md` - links only, if a link changes. `docs/PROGRESS.md` is not edited by hand.

## Steps
1. Write `architecture.py` (module list, edges) from the facts above, re-checking names in code.
2. Write the README mermaid from that list by hand; write `tests/test_architecture_page.py`
   (module list sanity + README label match). Run it.
3. Build `architecture_page.py`, swap the nav, delete `design_page.py`, fix the
   `test_vectors_optional.py` import; grep for `design_page` / `"Design"` again. Page tests.
4. Run the app on mock (`LLM_PROVIDER=mock`) and look at the page at 1280 px and at a narrow
   width (the SVG scales; the list stays readable); check hover and Tab focus by hand.
5. Recipe `features/architecture-page.md`, driver, index and SKILL.md rows; run
   `verify_cee.py run architecture-page ask-answer gap-path open-citation coverage` on mock.
6. Take the four screenshots from the verify instance into `docs/assets/`; look at each.
7. Docs: README (diagram, How it works, screenshots, Status, code map), ARCHITECTURE.md,
   RUN.md (Windows + macOS), DESIGN.md, specs/ui.md.
8. Full `pytest -q`; push; PR; `gh pr checks` green; check the mermaid renders on the PR page.

Unsure: whether `st.html` keeps `:focus` styles and `tabindex` on Streamlit 1.64 (it sanitises
some markup). If it strips them, fall back to `st.markdown(..., unsafe_allow_html=True)`; if both
strip them, `st.components.v1.html` (an iframe, still inline, no network) with the same markup.
Recorded in the Progress log.

Review notes (non-blocking, from the plan review on #270):
1. If the `components.v1.html` iframe fallback is used, the driver's hover and focus checks need
   frame handling (`page.frame_locator(...)`); recorded in the Progress log either way.
2. `specs/ui.md` is owned by U1; the PR names U1 as owner (informational, TL takeover).
3. "Mermaid renders on the PR page" is a manual check: the PR Verification gets the link to the
   rendered README on the branch (or a screenshot of it).

## Acceptance
- [x] Linked questions: none (docs and UI only; no retrieval or answer change).
- [x] README mermaid shows the W11 flow (decompose, per-sub-question search with SQL filters,
  per-firm extract, corrective re-search, evidence matrix decided by code, synthesis, checks)
  with a data / code / AI legend; renders on the GitHub PR page.
- [x] README node labels equal `architecture.py` labels -> `pytest tests/test_architecture_page.py`
  passes.
- [x] README screenshots are new, from the running mock app, with alt text; demo.gif kept.
- [x] README Status, ARCHITECTURE.md and RUN.md match the merged W11 reports and code; RUN.md has
  Windows and macOS blocks for fts and hybrid-norerank. Checks (TL ruling on #270):
  - `grep -c "18/30" README.md` and `grep -c "22/30" README.md` -> each >= 1; `grep -c
    "docs/results/w11-report.md" README.md` >= 1; `grep -c
    "hybrid-eval/corpus-2026-11-19/deepseek/report.md" README.md` >= 1.
  - `grep -n -i "One LLM call\|single LLM call" README.md` -> no output.
  - `sed -n '/^## 7\./,$p' docs/RUN.md | grep -n "about two calls"` -> no output.
  - the RUN.md retrieval-mode section holds a ```` ```powershell ```` and a ```` ```bash ```` block for
    fts and for hybrid-norerank (4 blocks; checked by eye and by `grep -c` inside the section).
  - the mode names and flags in RUN.md (`RETRIEVAL_MODE`, `--mode fts|hybrid|hybrid-norerank`) match
    `git show origin/exp/hybrid:scripts/eval_run.py` (`RETRIEVAL_MODES = ("fts", "hybrid",
    "hybrid-norerank")`, `--mode`) and `origin/exp/hybrid:.env.example` (`RETRIEVAL_MODE=fts`); the
    output is logged in the Progress log.
- [x] App nav shows Architecture (url `architecture`), no Design; `design_page.py` gone and
  nothing imports it (`git grep design_page` -> only plans/ and history docs).
- [x] Hover and keyboard focus show each module's explanation; the plain list shows all modules;
  no firm figures, no network fetch, no script tag on the page.
- [x] `verify_cee.py run architecture-page ask-answer gap-path open-citation coverage` -> PASS
  (mock), evidence folder named in the PR.
- [x] `python -m pytest -q` green locally and `gh pr checks` green.
- [x] 0 real calls; `.env` never read or printed.

## Progress log
- 2026-11-21 01:25 - plan written on `tl/270-closeout-arch` from origin/main 0a7510a (worktree
  D:\ALLPROJECTS\EDJ\wt-270).
- 2026-11-21 01:30 - plan approved with conditions (reviewer + TL ruling on #270): Acceptance item 5
  gets concrete grep checks; review notes 1-3 added. exp/hybrid names checked:
  `scripts/eval_run.py` has `RETRIEVAL_MODES = ("fts", "hybrid", "hybrid-norerank")` and
  `--mode` (default `RETRIEVAL_MODE`, else fts); `.env.example` has `RETRIEVAL_MODE=fts` and says
  hybrid needs `CEE_VECTORS=on`.
- 2026-11-21 01:32 - `st.html` (Streamlit 1.64) keeps `tabindex`, `role`, `aria-describedby`, inline
  `style` and `<style>`, `:hover`/`:focus` work (no iframe, so review note 1's frame handling is not
  needed), but it drops inline SVG entirely: the arrows and group frames are drawn as plain divs.
  Tooltips open beside the box, so the diagram's scroll area never clips them.
- 2026-11-21 01:38 - module text in `src/cee/app/architecture.py` (13 modules: 3 offline, 10 online;
  kinds data / code / ai / ai+code). README and ARCHITECTURE.md mermaid in the current style: a
  `Corpus` subgraph plus three online subgraphs (find / read and decide / write and check), boxes
  and arrows, classDefs and a Legend subgraph. `tests/test_architecture_page.py` checks both
  diagrams' node labels against the module list.
- 2026-11-21 01:42 - `verify_cee.py`: driver `architecture-page` (hover Search, Tab to Evidence
  matrix, list, no figures, /design gone) and a `shots` command (README images into the run's
  `shots/` and docs/assets; Streamlit scrolls inside its own container, so the shots use a tall
  viewport and clip to the content). First drive on the plan commit: architecture-page PASS, the
  other features PASS except open-citation / download-document UNREACHABLE (no raw files in the
  worktree without the share path).
- 2026-11-21 01:45 - item 5 checks: README `18/30` x1, `22/30` x1, `docs/results/w11-report.md` x2,
  the exp/hybrid deepseek report x1, no "One LLM call" / "single LLM call"; RUN.md section 7 has no
  "about two calls"; the retrieval-mode block has 2 PowerShell + 2 bash blocks (fts, hybrid-norerank);
  its names `RETRIEVAL_MODE`, `--mode fts | hybrid | hybrid-norerank` equal exp/hybrid's
  `RETRIEVAL_MODES = ("fts", "hybrid", "hybrid-norerank")` and `.env.example` `RETRIEVAL_MODE=fts`.
  Dark token set checked in a standalone render (scratch, the app is pinned light). Full pytest:
  1055 passed. 0 real calls.
- 2026-11-21 01:52 - final verify-cee on 27cc34e, run `20261121-014743-27cc34e` (mock; every meta
  line says `model: mock`): all 10 features PASS, including architecture-page, open-citation and
  download-document (the main checkout's `.env` was copied in for `CORPUS_SHARE_PATH`, never read,
  and removed after). `shots` from the same run wrote docs/assets answer, source, gap,
  architecture (Search hovered); a standalone dark-token render is kept in the run's `shots/`.
