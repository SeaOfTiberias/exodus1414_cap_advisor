"""
merger.py
=========
Turn the tidy records produced by ``extractor.py`` into the final workbook,
mirroring the layout of last year's ``all_colleges_cutoff.xlsx`` and adding the
round-by-round planning pivot the project is named for.

Output workbook: data/output/CAP_Round_Planning.xlsx
    * "Consolidated"    -- every extracted row (long format, all rounds).
    * "Rd 1".."Rd 4"    -- one sheet per round actually present in the data.
    * "Round Planning"  -- pivot of Merit Percentile with one column per round:
                           College / Branch / Category  x  Round 1..4.
                           Rounds with no PDF yet are marked "Pending".

Why a pivot AND long sheets? The long sheets reproduce last year's deliverable
exactly (both merit no. and percentile, per seat-type band). The pivot answers
the planning question -- "how did this college+course+category's percentile move
across CAP rounds?" -- which is what the original brief described.
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from . import config

log = logging.getLogger("merger")

# Percentile is the value used in the planning pivot.
_PCT = "Cutoff Percentile"
_ROUND = "CAP Round"


# --------------------------------------------------------------------------- #
# Optional cross-check against last year's category vocabulary
# --------------------------------------------------------------------------- #
def validate_against_reference(df: pd.DataFrame) -> None:
    ref = config.REFERENCE_XLSX
    if not ref or not Path(ref).exists():
        return
    try:
        ref_df = pd.read_excel(ref, sheet_name=0, usecols=["Category"])
    except Exception as exc:            # noqa: BLE001 - advisory only
        log.warning("Could not read reference workbook for validation: %s", exc)
        return
    known = set(ref_df["Category"].dropna().astype(str))
    seen = set(df["Category"].astype(str))
    new = sorted(seen - known)
    if new:
        log.info("Categories not present in reference (new/rare, review): %s", new)


# --------------------------------------------------------------------------- #
# Pivot
# --------------------------------------------------------------------------- #
def build_planning_pivot(df: pd.DataFrame) -> pd.DataFrame:
    """
    One row per (College, Branch, Category); one column per CAP round holding the
    Merit Percentile. When a (college, branch, category) appears in several
    seat-type bands within a round, the most competitive (max) percentile is
    kept. Rounds with no data are filled with "Pending".
    """
    index_cols = ["College Code", "College Name", "Branch Code",
                  "Branch/Course", "Category"]

    pivot = (
        df.pivot_table(index=index_cols, columns=_ROUND, values=_PCT,
                       aggfunc="max")
        .reset_index()
    )

    # Ensure a column for every configured round, in order, nicely named.
    for round_no in sorted(config.ROUND_PDF_FILES):
        src = f"Round {round_no}"
        dst = f"Round {round_no} Cut-off (Percentile)"
        if src in pivot.columns:
            pivot = pivot.rename(columns={src: dst})
        else:
            pivot[dst] = "Pending"
        pivot[dst] = pivot[dst].where(pivot[dst].notna(), "Pending")

    ordered = index_cols + [f"Round {n} Cut-off (Percentile)"
                            for n in sorted(config.ROUND_PDF_FILES)]
    return pivot[ordered]


# --------------------------------------------------------------------------- #
# Workbook assembly
# --------------------------------------------------------------------------- #
def write_workbook(records: list[dict], out_path: Path | None = None) -> Path:
    out_path = out_path or config.FINAL_OUTPUT
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not records:
        raise ValueError("No records to write.")

    df = pd.DataFrame(records)
    # Guarantee column order / presence.
    for col in config.OUTPUT_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    df = df[config.OUTPUT_COLUMNS]

    validate_against_reference(df)

    with pd.ExcelWriter(out_path, engine="openpyxl") as xl:
        df.to_excel(xl, sheet_name="Consolidated", index=False)

        rounds_present = sorted(df[_ROUND].dropna().unique(),
                                key=lambda r: int(str(r).split()[-1]))
        for r in rounds_present:
            n = str(r).split()[-1]
            df[df[_ROUND] == r].to_excel(xl, sheet_name=f"Rd {n}", index=False)

        build_planning_pivot(df).to_excel(xl, sheet_name="Round Planning", index=False)

    log.info("Wrote %s rows -> %s (sheets: Consolidated, %s, Round Planning)",
             len(df), out_path.name,
             ", ".join(f"Rd {str(r).split()[-1]}" for r in rounds_present))
    return out_path


def run_merge(records: list[dict]) -> Path:
    return write_workbook(records)


if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    recs = json.loads(config.EXTRACTED_JSON.read_text(encoding="utf-8"))
    run_merge(recs)
