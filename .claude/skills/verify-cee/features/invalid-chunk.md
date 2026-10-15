# Unknown chunk ID

A link to a chunk that is not stored shows a clear error instead of a blank page or a
crash.

## Sub-features

- `chunk-missing`: message "Chunk <id> is not in the stored corpus."

## How to get to it (user POV)

- An old or mistyped link, e.g. `?chunk=NOT-A-REAL-CHUNK`.

## Driving it

Preconditions: baseline.

- **Open.** Go to `?chunk=NOT-A-REAL-CHUNK`. Page text contains "is not in the stored
  corpus".

## Gotchas

- None known.
