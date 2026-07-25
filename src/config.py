"""
Central configuration for the MSCET CAP cut-off pipeline.

Edit the values here (round -> PDF filename, output columns, matching options)
without touching the extraction or merging logic.
"""
from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = ROOT / "data"
INPUT_PDF_DIR = DATA_DIR / "input_pdfs"
TEMPLATE_DIR = DATA_DIR / "template"
OUTPUT_DIR = DATA_DIR / "output"

# Intermediate machine-readable dump of everything scraped from the PDFs.
EXTRACTED_JSON = OUTPUT_DIR / "extracted_cutoffs.json"

# Final consolidated workbook (same schema as last year's all_colleges_cutoff.xlsx).
FINAL_OUTPUT = OUTPUT_DIR / "CAP_Round_Planning.xlsx"

# --------------------------------------------------------------------------- #
# Input PDF -> round-number mapping
# --------------------------------------------------------------------------- #
# Map each CAP round to its PDF file in data/input_pdfs/. Only rounds whose
# file is actually present get extracted; the rest are skipped with a warning.
# The MSCET file naming is e.g. "2025ENGG_CAP1_CutOff.pdf".
ROUND_PDF_FILES = {
    1: "2025ENGG_CAP1_CutOff.pdf",
    2: "2025ENGG_CAP2_CutOff.pdf",
    3: "2025ENGG_CAP3_CutOff.pdf",
    4: "2025ENGG_CAP4_CutOff.pdf",
}

# --------------------------------------------------------------------------- #
# Output schema  (mirrors last year's all_colleges_cutoff.xlsx)
# --------------------------------------------------------------------------- #
OUTPUT_COLUMNS = [
    "College Code",
    "College Name",
    "Branch Code",
    "Branch/Course",
    "College Status",
    "CAP Round",
    "Counseling Stage",
    "Category",
    "Cutoff Rank (Merit No)",
    "Cutoff Percentile",
]

# --------------------------------------------------------------------------- #
# Reference workbook from last year (used by merger.py to sanity-check the
# extracted category vocabulary and to build the same per-round sheet layout).
# Set to None to skip the cross-check.
# --------------------------------------------------------------------------- #
REFERENCE_XLSX = ROOT / "all_colleges_cutoff.xlsx"

# --------------------------------------------------------------------------- #
# Extraction tuning
# --------------------------------------------------------------------------- #
# Max horizontal distance (in PDF points) for a value to be considered part of
# a header column. Column spacing in these PDFs is ~50pt, header/value x-offset
# is ~8pt, so 30 is a safe tolerance.
COLUMN_X_TOLERANCE = 30
