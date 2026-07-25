# Contributing

Thanks for helping improve the MSCET CAP cut-off extractor. This is a small,
focused tool — the notes below cover how to run it, how to validate output, and
the open items worth a second pair of eyes.

## Development setup

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows PowerShell
pip install -r requirements.txt
```

Place the source PDFs in `data/input_pdfs/` (names mapped in
[`src/config.py`](src/config.py) → `ROUND_PDF_FILES`), then:

```bash
python main.py --pages 60    # quick sample while iterating
python main.py               # full run
```

The parser's line/row classifiers live at the top of
[`src/extractor.py`](src/extractor.py) (`RE_INST`, `RE_COURSE`, `_is_merit`,
`_is_pct`, `_is_header_material`). If a future round's PDF changes layout, that's
the place to start.

## How to validate a run

After a full run, sanity-check `data/output/extracted_cutoffs.json`:

- **No null / out-of-range percentiles.** Every `Cutoff Percentile` should be a
  float in `[0, 100]`; every `Category`, `College Name`, `Branch Code` non-empty.
- **Coverage vs. last year.** Compare college and branch counts against last
  year's `all_colleges_cutoff.xlsx` (kept locally; git-ignored).
- **Spot-check a block** against the raw PDF — pick a college, confirm the merit
  numbers and bracketed percentiles line up per category and seat-type band.
- **New category codes** are logged each run (e.g. 2025's `SEBC` / `PwD`
  variants). These are informational, not errors — but eyeball them.

## Known items to verify

### 1. Round-1 coverage vs. last year

On the 2025 CAP Round-1 PDF the extractor now produces:

| Metric   | 2025 (extracted) | Last year (R1) |
|----------|-----------------:|---------------:|
| Records  | 34,422           | 32,156         |
| Colleges | 368              | 367            |
| Branches | 2,140            | 2,100          |

Branch count is slightly *above* last year, consistent with the new SEBC / PwD
category variants introduced in 2025. Zero nulls, zero out-of-range percentiles.

Coverage looks good but has **not** been reconciled row-for-row against the
authoritative DTE / CET Cell branch master for 2025-26. Spot-check any specific
(college, course) you care about; if a block that appears in the PDF is missing
from the output, capture the college code + branch code + PDF page number so
the parser gap can be reproduced.

**Historical note:** the initial parser under-counted at 31,656 rows / 1,994
branches because pdfplumber sometimes places the leading stage numeral (`I` /
`II`) on a baseline 1-2 px offset from its merit row, causing `_is_merit()` to
drop the merit line. Concrete misses included Amravati CSE (0 rows) and
Instrumentation (1 row). Fixed in commit `a13f4d2` by clustering line-tops
within ±2 px in `_lines()`. Worth being aware of if a future round's PDF
regresses this behaviour with a different offset.

### 2. Same-suffix category across seat-type bands

A category such as `GOBCH` can legitimately appear under two seat-type bands
("Home-University → Home-University" and "Home-University → Other-than-Home"),
each with its own value. The extractor keeps all of them (de-duplicating only on
the full record). The `Round Planning` pivot collapses these with `max`
(most-competitive) percentile — revisit if a different aggregation is wanted.

## Reporting a problem

Open an issue with:
- the round / PDF file name,
- the college code + branch code involved,
- the raw PDF page number, and
- what you expected vs. what the output showed.

A minimal repro (`python main.py --pages N` around the offending page) is ideal.
