# Open a citation

A user clicks a citation and reads the exact stored passage it points to, with its
document, section, tier and filing date.

## Sub-features

- `cite-open`: the link opens the source page for that chunk.
- `cite-match`: the passage shown is the stored text of that chunk.
- `cite-meta`: entity, document type, period, tier, section and chunk ID are shown.

## How to get to it (user POV)

- Click any citation link under a claim (opens a new tab).
- Paste `?chunk=<chunk_id>` after the app address.

## Driving it

Preconditions: baseline; the answerable question returns citations.

- **Open.** Ask the answerable question, click the first citation link, take the new tab.
  Page text contains "Stored passage" and `Chunk: <id>`.
- **Read-back.** The first 80 characters of `chunks.text` for that ID appear on the page.

## Gotchas

- Chunk IDs contain `#`; in an address it must be written `%23`.
- The claim text on the answer page is also a passage excerpt, so check the read-back on
  the source page, not the answer page.
