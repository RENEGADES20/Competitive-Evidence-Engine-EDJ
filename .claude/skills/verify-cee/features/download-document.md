# Download the stored document

From a source page, a user downloads the original file the passage came from, byte for
byte as stored.

## Sub-features

- `download-ok`: the button downloads the file; its sha256 equals `documents.sha256`.
- `download-missing`: without the raw file, a clear "not found locally" note appears.

## How to get to it (user POV)

- Open a citation, click "Download stored document".

## Driving it

Preconditions: baseline; for `download-ok` the raw file is in `data/raw/` (copied from the
team Box link). Without it the feature is reported `UNREACHABLE`, not PASS.

- **Open.** Go to the source page of the chunk from `open-citation` (or any chunk).
- **Download.** Click button "Download stored document"; hash the saved file; compare
  with `documents.sha256`.
- **Missing file.** If there is no button, page text must contain "not found locally".

## Gotchas

- Most teammates do not have raw files; UNREACHABLE is expected for them.
