# MSCET CAP PDF Layout Notes

Structural facts about the source PDFs that are load-bearing for the extractor
and non-obvious from reading `src/extractor.py` alone. Keep this file in sync
with the parser whenever a future round's PDF surfaces a new layout twist.

## Per-block structure

Each institute × course block in the PDF is laid out as:

```
NNNNN - <College Name>                     ← institute (5-digit code)
NNNNNNNNNN - <Course Name>                 ← course    (10-digit code)
Status: <status>  Home University : ...    ← "Status:" label; value on the following line
<Seat-Type Band Label>                     ← e.g. "State Level",
                                              "Home University Seats Allotted to ...",
                                              "Other Than Home University Seats Allotted to ..."
GOPENS  GSCS  ... EWS                      ← category header row (may wrap onto next line)
Stage                                      ← literal word "Stage" on its OWN baseline
I  <n> <n> ... <n>                          ← stage numeral + merit numbers
(<pct>) (<pct>) ... (<pct>)                ← merit percentiles
[II <n> ...]                                ← optional Stage-II row
[(<pct>) ...]
```

## Layout gotchas the parser handles

1. **Roman-numeral baseline offset.** pdfplumber sometimes places `I` / `II`
   on a baseline 1–2 px below the merit-number row. Handled by `_lines()`
   clustering tops within `±2 px`. Safe because the word `Stage` is dropped
   first and true data-row separations are `≥6 px` apart.
   *(Historical: this caused Amravati CSE and COEP branches to be dropped in
   the initial parser; fixed in commit `a13f4d2`.)*

2. **Wrapped category labels.** e.g. `PWDROBCS` renders as `PWDROBC` at `x=X`
   on line N, then `S` at `x≈X` on line N+1. Rejoined by x-clustering in
   `_header_columns()` — words within 18 pt of the previous column's `x0`
   are concatenated.

3. **Wrapped merit / percentile rows.** Wide courses (25+ categories) can
   spill onto a second physical line. Alignment is by x-coordinate, not token
   index — `_nearest(x, cols, tol)` binds each value to its header column
   using `COLUMN_X_TOLERANCE = 30 pt` (columns are ~50 pt apart, header/value
   x-offset is ~8 pt).

4. **Same-suffix category × multiple seat-type bands.** A category like
   `GOBCH` legitimately appears under multiple bands (e.g. `HU→HU`,
   `HU→Other-than-HU`) with different values. **Do not** de-duplicate on
   `(college, branch, stage, category)` — that drops real data. Dedup on the
   full record instead (last year's file contains 1,799 such multi-band rows).

5. **Page furniture to skip.** `"Government of Maharashtra"`,
   `"State Common Entrance"`, `"Cut Off"`, `"Degree Courses"`, `"Legends"`,
   `"Status"` (the label), and bare page numbers (`line.strip().isdigit()`).

## Category vocabulary

From the PDF's own "Legends" footer:

- **Starting character** — `G` = General, `L` = Ladies, `PWD` = Person with
  Disability, `DEF` = Defence. Standalone codes: `TFWS`, `EWS`, `MI`,
  `ORPHAN`, `AI` (All India).
- **Ending character** — `H` = Home University, `O` = Other than Home
  University, `S` = State Level.

**New in 2025** (not present in last year's data; logged informationally each
run, not treated as errors): SEBC family (`GSEBCS`/`H`/`O`, `LSEBCS`/`H`/`O`)
and various `PWD*S` / `DEF*S` variants (`PWDROBCS`, `DEFROBCS`, etc.).

## Verified against

- **`2025ENGG_CAP1_CutOff.pdf`** — 1,566 pages, ~4.2 MB. Extracts cleanly
  into 34,422 records / 368 colleges / 2,140 branches, 0 nulls,
  0 out-of-range percentiles.
- Rounds 2–4 PDFs are expected to follow the same layout — if they don't,
  the classifiers to revisit are at the top of `src/extractor.py`
  (`RE_INST`, `RE_COURSE`, `_is_merit`, `_is_pct`, `_is_header_material`).
