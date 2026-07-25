# MSCET CAP Cut-off Extractor

Parses Maharashtra State CET Cell **engineering CAP cut-off PDFs** (Rounds 1–4)
into a clean workbook with the same schema as last year's
`all_colleges_cutoff.xlsx`, plus a round-by-round planning pivot.

## What it produces

`data/output/CAP_Round_Planning.xlsx` with these sheets:

| Sheet | Contents |
|---|---|
| **Consolidated** | Every extracted row, long format (all rounds). |
| **Rd 1 … Rd 4** | One sheet per round that has a PDF present. |
| **Round Planning** | Pivot: `College / Branch / Category` × `Round 1..4` Merit Percentile. Rounds with no PDF yet show **`Pending`**. |

Long-format columns (mirror last year exactly):

```
College Code | College Name | Branch Code | Branch/Course | College Status |
CAP Round | Counseling Stage | Category | Cutoff Rank (Merit No) | Cutoff Percentile
```

Also writes `data/output/extracted_cutoffs.json` (raw records, for auditing).

## Project structure

```
Aarchard_CAP/
├── main.py                     # run the pipeline
├── requirements.txt
├── all_colleges_cutoff.xlsx    # last year's data (schema reference + category check)
├── data/
│   ├── input_pdfs/             # <- put the CAP round PDFs here
│   └── output/                 # <- results land here
└── src/
    ├── config.py               # round->PDF map, output columns, tolerances (edit me)
    ├── extractor.py            # PDF -> tidy records
    └── merger.py               # records -> workbook (long sheets + planning pivot)
```

## 1. Install

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 2. Place the PDFs

Drop the round PDFs in `data/input_pdfs/`. The expected names are in
`src/config.py` → `ROUND_PDF_FILES`:

| Round | Expected file name           |
|-------|------------------------------|
| 1     | `2025ENGG_CAP1_CutOff.pdf`   |
| 2     | `2025ENGG_CAP2_CutOff.pdf`   |
| 3     | `2025ENGG_CAP3_CutOff.pdf`   |
| 4     | `2025ENGG_CAP4_CutOff.pdf`   |

Only rounds whose file is present get processed; the rest are skipped and appear
as `Pending` in the planning pivot. (Rename your files, or edit the map — either
works.)

## 3. Run

```bash
python main.py
```

Quick test on a page subset while iterating:

```bash
python main.py --pages 60
```

## How the extractor works

Each course block in the PDF looks like:

```
01002 - Government College of Engineering, Amravati      (institute, 5-digit code)
0100219110 - Civil Engineering                           (course, 10-digit code)
Status: Government Autonomous  Home University : ...
State Level                                              (seat-type band)
GOPENS  GSCS  GSTS ... EWS                               (category header)
Stage
I  37591  58518 ... 90389                                (Stage-I merit numbers)
(88.9550679) (82.3322294) ... (71.4755245)               (merit percentiles)
```

- Rows are aligned **by x-coordinate**, not token order, so wide tables whose
  merit/percentile rows wrap onto a second line still line up correctly.
- Wrapped category labels (e.g. `PWDROBCS` split as `PWDROBC` + `S`) are folded
  back into their column.
- Both the merit number and the percentile are kept.
- A category can legitimately appear once per seat-type band (e.g. `GOBCH` under
  both "Home-University→Home-University" and "Home-University→Other-than-Home"),
  each with its own value — all are kept, matching last year's workbook.

### Verified on the 2025 Round-1 PDF

1,566 pages → **31,656 records / 368 colleges / 1,994 branches** in ~90s, with
0 null or out-of-range percentiles and spot-checks matching the PDF exactly.
(Last year's R1: 32,156 rows / 367 colleges / 2,100 branches — the branch-count
difference is year-over-year course variation, worth an eyeball but not a bug.)

## Tuning (`src/config.py`)

| Setting | Purpose |
|---|---|
| `ROUND_PDF_FILES` | Round → PDF filename map. |
| `OUTPUT_COLUMNS` | Long-format schema (keep in sync with the reference file). |
| `COLUMN_X_TOLERANCE` | Max x-distance (pts) for a value to bind to a header column. |
| `REFERENCE_XLSX` | Last year's workbook; used to flag category codes not seen before. Set `None` to skip. |

## Notes

- On each run the log prints any **category codes not present in last year's
  file** (e.g. new `SEBC`/`PwD` variants for 2025). These are informational —
  review them, but they are valid categories, not errors.
- If a future round's PDF uses a different layout, the classifiers to revisit are
  at the top of `src/extractor.py` (`RE_INST`, `RE_COURSE`, `_is_merit`,
  `_is_pct`, `_is_header_material`).
```
