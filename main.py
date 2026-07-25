"""
main.py
=======
Entry point for the MSCET CAP cut-off pipeline. Runs sequentially:

    1. Extract percentile + merit records from each round's PDF   (src/extractor.py)
    2. Assemble the consolidated / per-round / planning workbook   (src/merger.py)

Usage
-----
    python main.py                # process every page of every present PDF
    python main.py --pages 60     # quick sample run (first 60 pages) for testing

Prerequisites
-------------
    * pip install -r requirements.txt
    * PDFs in data/input_pdfs/  (names mapped in src/config.ROUND_PDF_FILES)
    * (optional) last year's all_colleges_cutoff.xlsx in the project root, used
      only to flag any category codes not seen last year.
"""
import argparse
import logging
import sys

from src import config
from src.extractor import extract_all
from src.merger import run_merge

log = logging.getLogger("pipeline")


def main() -> int:
    parser = argparse.ArgumentParser(description="MSCET CAP cut-off pipeline")
    parser.add_argument("--pages", type=int, default=None,
                        help="Limit pages per PDF (for quick test runs).")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

    log.info("=" * 60)
    log.info("STEP 1/2  Extracting cut-off data from PDFs")
    log.info("=" * 60)
    records = extract_all(max_pages=args.pages)

    if not records:
        log.error("No records extracted. Confirm PDFs exist in %s and that their "
                  "names match config.ROUND_PDF_FILES.", config.INPUT_PDF_DIR)
        return 1

    log.info("=" * 60)
    log.info("STEP 2/2  Building consolidated workbook")
    log.info("=" * 60)
    out_path = run_merge(records)

    log.info("=" * 60)
    log.info("DONE. Output: %s", out_path)
    log.info("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
