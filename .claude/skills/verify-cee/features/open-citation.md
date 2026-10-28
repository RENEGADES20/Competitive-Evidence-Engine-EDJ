# Open a citation

A user clicks a citation and reads the exact stored passage it points to, with its
document, section, tier and filing date. The passage is shown inside its section (the chunks
next to it), and a PDF citation also shows the cited PDF page.

## Sub-features

- `cite-open`: the link opens the source page for that chunk.
- `cite-match`: the passage shown is the stored text of that chunk.
- `cite-label`: each citation on the answer page shows its own source label and tier badge.
- `cite-meta`: entity, document type, period, tier, section and chunk ID are shown.
- `cite-context`: the cited chunk is marked `CITED PASSAGE`; up to two chunks of the same section
  on each side are shown as `NEIGHBOURING PASSAGE`.
- `cite-page`: a PDF chunk shows its stored PDF page (`Page N of M of the stored PDF`), and that
  page is `chunks.page`. Without the raw file locally the passage, context and metadata still show.

## How to get to it (user POV)

- Click any citation link under a claim (each shows source label and tier) (opens a new tab).
- Paste `?chunk=<chunk_id>` after the app address.

## Driving it

Preconditions: baseline; the answerable question returns citations.

- **Open.** Ask the answerable question, click the first citation link, take the new tab.
  Page text contains "Stored passage" and `Chunk: <id>`.
- **Read-back.** The first 80 characters of `chunks.text` for that ID appear on the page.
- **Context.** Exactly one `CITED PASSAGE · <chunk_id>` tag; the `NEIGHBOURING PASSAGE` count equals
  the chunks of the same document and section within 2 `seq` of the cited one (database query).
- **PDF page.** For 5 deck/supplement chunks (`MS-SUPP-2026Q3#16`, `SCHW-DECK-2026Q2#53`, then 3 picked
  by a fixed hash), open `?chunk=<id>`: the caption is `Page N of M of the stored PDF`, one page image
  is shown, and at least 80% of the chunk's words are in page N of the raw PDF (read with pymupdf).
  Needs the raw PDF (`CORPUS_SHARE_PATH` or `data/raw/`); otherwise the step is UNREACHABLE.

## Gotchas

- Chunk IDs contain `#`; in an address it must be written `%23`.
- Chunks of a PDF are cut per page, so the neighbours of a PDF chunk can sit on other pages; each
  tag carries its own page number.
- The claim text on the answer page is also a passage excerpt, so check the read-back on
  the source page, not the answer page.
