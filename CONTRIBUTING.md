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

### 1. Round-1 branch count is lower than last year (needs confirmation)

On the 2025 CAP Round-1 PDF the extractor produces:

| Metric   | 2025 (extracted) | Last year (R1) |
|----------|-----------------:|---------------:|
| Records  | 31,656           | 32,156         |
| Colleges | 368              | 367            |
| Branches | 1,994            | 2,100          |

College count matches almost exactly and there are **no null/malformed rows**,
so this is most likely genuine year-over-year course variation (branches with no
Round-1 allotment, NEP-driven consolidation, discontinued programs). It has
**not** been confirmed against an authoritative 2025 branch list.

**To close this:** cross-check the ~106 branch delta against the official DTE /
CET Cell branch master for 2025-26. If any missing branches *do* appear in the
PDF but not in the output, capture the college code + branch code and the raw
PDF page so the parser gap can be reproduced and fixed.

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
