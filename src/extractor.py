"""
extractor.py
============
Parse Maharashtra State CET Cell engineering CAP cut-off PDFs into tidy,
one-row-per-(college, branch, stage, category) records that mirror last year's
``all_colleges_cutoff.xlsx`` schema.

Layout of the source PDFs (verified against 2025ENGG_CAP1_CutOff.pdf)
--------------------------------------------------------------------
Repeating blocks, one per (institute, course):

    01002 - Government College of Engineering, Amravati            <- institute (5-digit code)
    0100219110 - Civil Engineering                                 <- course    (10-digit code)
    Status: Government Autonomous  Home University : ...            <- status
    State Level                                                    <- SEAT-TYPE band label
    GOPENS  GSCS  GSTS ... EWS                                     <- category header row
    Stage                                                          <- (literal word, its own line)
    I  37591  58518 ... 90389                                      <- merit numbers (Stage-I)
    (88.9550679) (82.3322294) ... (71.4755245)                    <- merit percentiles

Robustness notes
----------------
* The three data rows (header / merit / percentile) are column-aligned by their
  x-coordinate, so we align values to columns **by x-position**, not by token
  order -- this survives the wide tables whose merit and percentile rows spill
  onto a second physical line.
* Category labels sometimes wrap (e.g. "PWDROBCS" -> "PWDROBC" + "S" on the next
  line); wrapped fragments are folded back into their column by x-clustering.
* We keep BOTH the merit number and the percentile (parity with last year).

Each emitted record is a dict:
    {
        "College Code": "01002",
        "College Name": "Government College of Engineering, Amravati",
        "Branch Code": "0100219110",
        "Branch/Course": "Civil Engineering",
        "College Status": "Government Autonomous",
        "CAP Round": "Round 1",
        "Counseling Stage": "Stage-I",
        "Category": "GOPENS",
        "Cutoff Rank (Merit No)": 37591,
        "Cutoff Percentile": 88.9550679,
    }
"""
from __future__ import annotations

import json
import logging
from collections import defaultdict
from pathlib import Path

import pdfplumber
import regex as re

from . import config

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger("extractor")

# --------------------------------------------------------------------------- #
# Patterns / token classifiers
# --------------------------------------------------------------------------- #
ROMAN = {"I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"}

RE_INST = re.compile(r"^(\d{5})\s*-\s*(.+)$")          # institute: 5-digit code
RE_COURSE = re.compile(r"^(\d{10})\s*-\s*(.+)$")        # course:    10-digit code
RE_CAT_TOK = re.compile(r"^[A-Z][A-Z0-9]*$")            # header token, e.g. GNT1S
RE_INT = re.compile(r"^\d+$")
RE_PCT = re.compile(r"^\((\d{1,3}(?:\.\d+)?)\)$")

# Seat-type band labels (used only to reset state; the H/O/S category suffix
# already encodes the seat type in the output).
BAND_KEYS = (
    "Home University Seats",
    "Other Than Home University Seats",
    "State Level",
    "All India",
    "Minority Seats",
)

# Lines that are page furniture and must be ignored.
SKIP_PREFIXES = ("Status", "Legends", "Cut Off", "Degree Courses")
SKIP_CONTAINS = ("Government of Maharashtra", "State Common Entrance")


# --------------------------------------------------------------------------- #
# Line grouping
# --------------------------------------------------------------------------- #
def _lines(page):
    """
    Return [(top, [words])] for a page, one entry per visual line.

    Words are bucketed by their rounded ``top`` coordinate. Two subtleties:

    * The literal word "Stage" sits on its own baseline between the header and
      the merit row -- we drop it so it can never contaminate a line.
    * pdfplumber sometimes places the leading Roman numeral of a merit row
      (``I``, ``II``, ...) on a baseline 1-2px offset from the merit numbers
      themselves. We fuse adjacent tops within ``JITTER_PX`` to reunite them
      -- safe because "Stage" is already removed and true data-row separations
      in these PDFs are >=6px apart.
    """
    JITTER_PX = 2
    rows = defaultdict(list)
    for w in page.extract_words():
        if w["text"] == "Stage":
            continue
        rows[round(w["top"])].append(w)

    merged: list[list] = []      # each entry: [top, [words]]
    for top in sorted(rows):
        if merged and top - merged[-1][0] <= JITTER_PX:
            merged[-1][1].extend(rows[top])
            merged[-1][0] = top
        else:
            merged.append([top, list(rows[top])])

    return [(t, sorted(ws, key=lambda w: w["x0"])) for t, ws in merged]


def _text(ws):
    return " ".join(w["text"] for w in ws)


def _is_header_material(ws):
    """All-caps alnum tokens starting with a letter (category labels + wrapped bits)."""
    return len(ws) >= 1 and all(RE_CAT_TOK.match(w["text"]) for w in ws)


def _is_merit(ws):
    return len(ws) >= 2 and ws[0]["text"] in ROMAN and all(RE_INT.match(w["text"]) for w in ws[1:])


def _is_int_run(ws):
    return len(ws) >= 1 and all(RE_INT.match(w["text"]) for w in ws)


def _is_pct(ws):
    return len(ws) >= 1 and all(RE_PCT.match(w["text"]) for w in ws)


# --------------------------------------------------------------------------- #
# Column building / x-alignment
# --------------------------------------------------------------------------- #
def _header_columns(words):
    """Cluster header words into columns by x0; concatenate wrapped fragments."""
    cols = []
    for w in sorted(words, key=lambda w: w["x0"]):
        if cols and abs(w["x0"] - cols[-1]["x"]) < 18:
            cols[-1]["label"] += w["text"]          # wrapped continuation
        else:
            cols.append({"x": w["x0"], "label": w["text"]})
    return cols


def _nearest(x, items, tol):
    """Nearest item to x within tolerance, else None."""
    best, bestd = None, tol + 1
    for it in items:
        d = abs(it["x"] - x)
        if d < bestd:
            best, bestd = it, d
    return best if bestd <= tol else best  # allow nearest even slightly over tol


# --------------------------------------------------------------------------- #
# Per-block state -> records
# --------------------------------------------------------------------------- #
class _BlockAccumulator:
    """Accumulates header + stage groups for one seat-type band and emits rows."""

    def __init__(self, emit, ctx, round_label):
        self._emit = emit
        self.ctx = ctx                # dict with college/course/status
        self.round_label = round_label
        self.header_words = []
        self.groups = []              # [{stage, merits:[{x,v}], pcts:[{x,v}]}]

    def add_header(self, ws):
        self.header_words.extend(ws)

    def start_stage(self, ws):
        self.groups.append({
            "stage": ws[0]["text"],
            "merits": [{"x": w["x0"], "v": int(w["text"])} for w in ws[1:]],
            "pcts": [],
        })

    def add_merit_cont(self, ws):
        if self.groups and not self.groups[-1]["pcts"]:
            self.groups[-1]["merits"].extend({"x": w["x0"], "v": int(w["text"])} for w in ws)

    def add_pct(self, ws):
        if self.groups:
            self.groups[-1]["pcts"].extend(
                {"x": w["x0"], "v": float(RE_PCT.match(w["text"]).group(1))} for w in ws
            )

    def flush(self):
        if not self.header_words or not self.groups:
            return
        cols = _header_columns(self.header_words)
        tol = config.COLUMN_X_TOLERANCE
        for g in self.groups:
            for m in g["merits"]:
                col = _nearest(m["x"], cols, tol)
                if col is None:
                    continue
                pct = _nearest(m["x"], g["pcts"], tol) if g["pcts"] else None
                self._emit({
                    "College Code": self.ctx.get("college_code"),
                    "College Name": self.ctx.get("college_name"),
                    "Branch Code": self.ctx.get("course_code"),
                    "Branch/Course": self.ctx.get("course_name"),
                    "College Status": self.ctx.get("status"),
                    "CAP Round": self.round_label,
                    "Counseling Stage": f"Stage-{g['stage']}",
                    "Category": col["label"],
                    "Cutoff Rank (Merit No)": m["v"],
                    "Cutoff Percentile": pct["v"] if pct else None,
                })


# --------------------------------------------------------------------------- #
# Per-PDF driver
# --------------------------------------------------------------------------- #
def extract_pdf(pdf_path: Path, round_no: int, max_pages: int | None = None) -> list[dict]:
    round_label = f"Round {round_no}"
    log.info("Extracting %s from %s", round_label, pdf_path.name)

    # The same (college, branch, stage, category) legitimately appears once per
    # seat-type band (e.g. GOBCH under both "HU->HU" and "HU->Other-than-HU"),
    # each with its own value -- last year's workbook keeps them all. So we
    # de-duplicate only on the FULL record (incl. rank + percentile), which
    # removes accidental re-emissions without collapsing distinct band values.
    records: dict[tuple, dict] = {}
    dupes = 0

    def emit(rec):
        nonlocal dupes
        key = (rec["College Code"], rec["Branch Code"], rec["Counseling Stage"],
               rec["Category"], rec["Cutoff Rank (Merit No)"], rec["Cutoff Percentile"])
        if key in records:
            dupes += 1
            return
        records[key] = rec

    ctx: dict = {}
    block: _BlockAccumulator | None = None
    expect_status = False

    def new_block():
        return _BlockAccumulator(emit, ctx, round_label)

    with pdfplumber.open(str(pdf_path)) as pdf:
        pages = pdf.pages if max_pages is None else pdf.pages[:max_pages]
        for page in pages:
            for _top, ws in _lines(page):
                line = _text(ws)

                # --- status value (line immediately after "Status:") ---------
                if expect_status:
                    expect_status = False
                    ctx["status"] = line.split("Home University")[0].strip(" :")
                    continue
                if line.startswith("Status"):
                    expect_status = True
                    continue

                # --- structural headers --------------------------------------
                mc = RE_COURSE.match(line)
                if mc:
                    if block:
                        block.flush()
                    ctx["course_code"], ctx["course_name"] = mc.group(1), mc.group(2).strip()
                    block = None
                    continue
                mi = RE_INST.match(line)
                if mi:
                    if block:
                        block.flush()
                    ctx["college_code"], ctx["college_name"] = mi.group(1), mi.group(2).strip()
                    block = None
                    continue

                # --- ignore page furniture -----------------------------------
                if any(line.startswith(p) for p in SKIP_PREFIXES) \
                        or any(s in line for s in SKIP_CONTAINS) \
                        or line.strip().isdigit():          # page number
                    continue

                # --- seat-type band label (resets to a fresh header) ---------
                if any(b in line for b in BAND_KEYS) and not _is_header_material(ws):
                    if block:
                        block.flush()
                    block = new_block()
                    continue

                # --- data rows -----------------------------------------------
                if _is_merit(ws):
                    if block is None:
                        block = new_block()
                    block.start_stage(ws)
                    continue
                if _is_pct(ws):
                    if block:
                        block.add_pct(ws)
                    continue
                if _is_header_material(ws):
                    # A header line arriving mid-data starts a new band.
                    if block and block.groups:
                        block.flush()
                        block = new_block()
                    if block is None:
                        block = new_block()
                    block.add_header(ws)
                    continue
                if _is_int_run(ws):        # wrapped continuation of a merit row
                    if block:
                        block.add_merit_cont(ws)
                    continue
                # anything else: ignore

        if block:
            block.flush()

    out = list(records.values())
    log.info("%s: %s records (%s duplicate keys skipped)", round_label, len(out), dupes)
    return out


def extract_all(max_pages: int | None = None) -> list[dict]:
    all_records: list[dict] = []
    for round_no, fname in sorted(config.ROUND_PDF_FILES.items()):
        pdf_path = config.INPUT_PDF_DIR / fname
        if not pdf_path.exists():
            log.warning("Round %s PDF not found: %s (skipping)", round_no, pdf_path.name)
            continue
        all_records.extend(extract_pdf(pdf_path, round_no, max_pages=max_pages))

    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    config.EXTRACTED_JSON.write_text(json.dumps(all_records, indent=2), encoding="utf-8")
    log.info("Wrote %s records -> %s", len(all_records), config.EXTRACTED_JSON.name)
    return all_records


if __name__ == "__main__":
    import sys
    mp = int(sys.argv[1]) if len(sys.argv) > 1 else None
    extract_all(max_pages=mp)
