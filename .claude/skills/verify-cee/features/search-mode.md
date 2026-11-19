# Search mode

Branch `exp/hybrid` only (#128). The Ask page sidebar has a **Search mode** switch: Exact
match (keyword search, `fts`) or Smart search (also finds rephrased wording, `hybrid`), each
with one help line. The default follows `RETRIEVAL_MODE`. Every answer says which mode found
it ("Found with: ..." under the heading and "search: ..." in the meta line). The mode is stored
in `query_log.filters->>'retrieval_mode'`; feedback links to it by `query_id`. With
`CEE_VECTORS` off, Smart search is locked and a help line says it is not set up.

## Sub-features

- `mode-switch`: two options only; `hybrid-norerank` is not offered.
- `mode-label`: the answer names its mode; no "hybrid", "rerank" or "FTS" anywhere on the page.
- `mode-log`: `query_log` and the linked feedback row carry the mode.
- `mode-off`: vectors off -> Smart search disabled, help line, no crash.

## How to get to it (user POV)

- Open Ask; the switch is at the top of the sidebar, above Filters.

## Driving it

Preconditions: baseline. Run per mode: `verify_cee.py run --mode fts` and (vectors set up,
docs/RUN.md "Hybrid retrieval") `verify_cee.py run --mode hybrid`. `--mode` goes after the features.

- **Sidebar.** Radios "Exact match" and "Smart search"; vectors off: Smart search disabled and
  "not set up on this computer" shown.
- **Ask.** The answerable EDJ question. Page text has "Found with: <label>" and "search: <label>".
- **Scan.** Open the trace; page text has no `hybrid`, `rerank` or `FTS`.
- **Read-back.** `query_log.filters->>'retrieval_mode'` for the query = the launched mode; send
  feedback, the joined row has the same mode.

## Gotchas

- `RETRIEVAL_MODE=hybrid-norerank` shows as Smart search in the switch default.
- The pipeline trace says "(hybrid)" internally; the page translates it to "(Smart search)".
- Since #240 Smart search plans the question like Exact match (the same parts, the same token
  budget); only how passages are found and ranked differs. The two-firm check in ask-progress
  expects "in 2 parts (Smart search)".
