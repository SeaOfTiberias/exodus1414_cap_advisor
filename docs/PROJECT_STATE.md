# Project State

Snapshot of pipeline state and pending work. Update this file when a new round
is processed or an open item is closed.

## What this project is

Python pipeline that parses **Maharashtra State CET Cell engineering CAP
cut-off PDFs** (Rounds 1–4) into a tidy Excel workbook matching the schema of
last year's `all_colleges_cutoff.xlsx`, plus a `Round Planning` pivot
(College × Branch × Category → percentile per round). Used for admission
planning based on year-over-year percentile trends.

## Current state

*(As of Round 1 processing, first full extraction pass.)*

- **Round 1** — extracted from `2025ENGG_CAP1_CutOff.pdf` (1,566 pages).
  - 34,422 records
  - 368 colleges
  - 2,140 branches
  - 0 null percentiles, 0 out-of-range values
  - Slightly above last year's 2,100 branches, consistent with the new
    SEBC / PwD category variants introduced in 2025.
- **Rounds 2, 3, 4** — PDFs not yet published. The pipeline handles missing
  rounds gracefully: they appear as `Pending` in the `Round Planning` sheet.
  Filenames the pipeline expects are `2025ENGG_CAP{2,3,4}_CutOff.pdf` (see
  `src/config.py` → `ROUND_PDF_FILES`).

## Pipeline layout

```
main.py                       # entry: `python main.py` (add --pages N for a fast test)
src/config.py                 # ROUND_PDF_FILES, OUTPUT_COLUMNS, tolerances
src/extractor.py              # x-coordinate-aligned pdfplumber parser
src/merger.py                 # writes Consolidated + per-round + Round Planning
data/input_pdfs/              # put round PDFs here (git-ignored)
data/output/                  # generated workbook + JSON (git-ignored)
```

## Pending work

- **Add Rounds 2–4** when the CET Cell publishes them: drop each PDF into
  `data/input_pdfs/` and re-run `python main.py`.
- **Reconcile branch count against DTE 2025-26 master.** 2,140 branches
  extracted; not yet verified against an authoritative branch list. Any
  branch that appears in the PDF but not in the output should be captured
  with college code + branch code + PDF page number so the parser gap can be
  reproduced.
- **Optional add:** 2024 vs. 2025 percentile diff sheet, once at least one
  2025 round is fully processed.

## Design decisions worth knowing

- **Kept both merit no. + percentile** per record, matching last year's file.
  The `Round Planning` pivot uses percentile only.
- **Same-category-across-seat-type-bands rows are preserved**, not collapsed.
  The pivot aggregates these with `max` (most-competitive percentile).
  Revisit if a different aggregation is preferred.
- **Repo is code-only** — source PDFs, generated output, and last year's
  reference workbook are git-ignored. See `README.md` for how to place them
  before running.
- See [PDF_LAYOUT.md](PDF_LAYOUT.md) for the parser-critical PDF structural
  facts and known layout gotchas.
