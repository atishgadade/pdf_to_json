"""
PDF to JSON Converter for College Admission Cutoff Data
========================================================
Converts CAP round PDFs (Maharashtra admission cutoffs) to a structured JSON file.
Works with any number of columns — fully flexible for varying PDF layouts.

Usage:
    python pdf_to_json.py <input.pdf> [output.json]

    python pdf_to_json.py cap_round2.pdf
    python pdf_to_json.py cap_round2.pdf output/results.json

Dependencies:
    pip install pdfplumber pandas
"""

import pdfplumber
import pandas as pd
import json
import re
import sys
import os
from pathlib import Path


# ─────────────────────────────────────────────
#  CONFIGURATION  (adjust if your PDF differs)
# ─────────────────────────────────────────────

# Known metadata fields that appear BEFORE the table columns.
# These are extracted from a title row / header area above the table.
META_FIELDS = {
    "year":         r"(?:year|academic year)[:\s]+(\d{4}[-–]\d{2,4})",
    "cap_round":    r"cap\s*round[:\s#]*(\d+)",
    "college_code": r"college\s*code[:\s]+(\d+)",
    "college_name": r"college\s*name[:\s]+(.+?)(?:\n|$)",
    "district":     r"district[:\s]+([A-Za-z\s]+?)(?:\n|$)",
}

# Column name normalisation map — add more as you discover them in your PDFs.
# Keys are raw PDF header text (lowercased), values are the canonical JSON key.
COLUMN_ALIASES = {
    "choice code":       "Choice Code",
    "choicecode":        "Choice Code",
    "branch name":       "Branch Name",
    "branchname":        "Branch Name",
    "branch":            "Branch Name",
    "g open":            "GOPEN",
    "gopen":             "GOPEN",
    "l open":            "LOPEN",
    "lopen":             "LOPEN",
    "g sc":              "GSC",
    "gsc":               "GSC",
    "l sc":              "LSC",
    "lsc":               "LSC",
    "g st":              "GST",
    "gst":               "GST",
    "l st":              "LST",
    "lst":               "LST",
    "g nt a":            "GNTA",
    "gnta":              "GNTA",
    "l nt a":            "LNTA",
    "lnta":              "LNTA",
    "g nt b":            "GNTB",
    "gntb":              "GNTB",
    "l nt b":            "LNTB",
    "lntb":              "LNTB",
    "g nt c":            "GNTC",
    "gntc":              "GNTC",
    "l nt c":            "LNTC",
    "lntc":              "LNTC",
    "g obc":             "GOBC",
    "gobc":              "GOBC",
    "l obc":             "LOBC",
    "lobc":              "LOBC",
    "ews":               "EWS",
    "mi":                "MI",
    "tfws":              "TFWS",
    "pwdopen":           "PWD_OPEN",
    "pwd open":          "PWD_OPEN",
}


# ─────────────────────────────────────────────
#  HELPER FUNCTIONS
# ─────────────────────────────────────────────

def normalise_column(raw: str) -> str:
    """Map raw PDF header text to a canonical column name."""
    key = raw.strip().lower()
    return COLUMN_ALIASES.get(key, raw.strip())   # fall back to stripped original


def clean_cell(value) -> str:
    """Normalise a cell value: strip whitespace, unify empty/null to 'NA'."""
    if value is None:
        return "NA"
    s = str(value).strip()
    if s in ("", "-", "--", "N/A", "n/a", "nil", "Nil"):
        return "NA"
    # collapse internal newlines (pdfplumber sometimes wraps text)
    s = re.sub(r"\s*\n\s*", " ", s)
    return s


def extract_metadata_from_text(text: str) -> dict:
    """
    Pull year, cap_round, college_code, college_name, district
    from raw page text using regex patterns defined in META_FIELDS.
    Returns a dict with only the keys that were found.
    """
    meta = {}
    for field, pattern in META_FIELDS.items():
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            meta[field] = m.group(1).strip()
    return meta


def coerce_types(record: dict) -> dict:
    """
    Attempt light type-casting:
      - Cap Round  → int
      - College Code → int
    Everything else stays as a string.
    """
    for key in ("cap_round", "Cap Round"):
        if key in record:
            try:
                record[key] = int(record[key])
            except (ValueError, TypeError):
                pass
    for key in ("college_code", "College Code"):
        if key in record:
            try:
                record[key] = int(record[key])
            except (ValueError, TypeError):
                pass
    return record


# ─────────────────────────────────────────────
#  CORE EXTRACTION
# ─────────────────────────────────────────────

def extract_tables_from_pdf(pdf_path: str, silent: bool = False) -> list[dict]:
    """
    Open the PDF with pdfplumber, iterate every page, extract every table,
    and return a flat list of row-dicts.

    Strategy
    --------
    1. Each page may contain a college header block (name, code, district)
       in plain text ABOVE the data table.
    2. The first row of each table is treated as the column header row.
    3. All subsequent rows become data records.
    4. Metadata (year, round, college info) found anywhere on the page is
       merged into every record from that page.
    5. Columns are normalised via COLUMN_ALIASES so the JSON keys are clean
       regardless of how the PDF spells them.
    """
    all_records: list[dict] = []

    # Global metadata that persists across pages (e.g. year, cap round)
    global_meta: dict = {}

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        if not silent:
            print(f"  -> {total_pages} page(s) found in PDF")

        for page_num, page in enumerate(pdf.pages, start=1):
            if not silent:
                print(f"  Processing page {page_num}/{total_pages} ...", end="\r")

            # ── 1. Raw text for metadata extraction ──────────────────────
            raw_text = page.extract_text() or ""
            page_meta = extract_metadata_from_text(raw_text)

            # Promote stable fields to global scope
            if "year" in page_meta:
                global_meta["Year"] = page_meta["year"]
            if "cap_round" in page_meta:
                global_meta["Cap Round"] = page_meta["cap_round"]
            if "college_code" in page_meta:
                global_meta["College Code"] = page_meta["college_code"]
            if "college_name" in page_meta:
                global_meta["College Name"] = page_meta["college_name"]
            if "district" in page_meta:
                global_meta["District"] = page_meta["district"]

            # ── 2. Table extraction ───────────────────────────────────────
            # pdfplumber.extract_tables() returns a list of tables;
            # each table is a list of rows; each row is a list of cell strings.
            tables = page.extract_tables()

            if not tables:
                # No structured table found — try extract_table() with settings
                table = page.extract_table({
                    "vertical_strategy":   "lines",
                    "horizontal_strategy": "lines",
                })
                tables = [table] if table else []

            for table in tables:
                if not table or len(table) < 2:
                    continue  # skip empty or header-only tables

                # First row → column headers
                raw_headers = table[0]
                if any(h is None for h in raw_headers):
                    # Sometimes pdfplumber merges header cells; try to heal
                    raw_headers = [h or f"Col_{i}" for i, h in enumerate(raw_headers)]

                headers = [normalise_column(h) for h in raw_headers]

                # Remaining rows → data
                for row in table[1:]:
                    if not any(row):          # skip blank rows
                        continue
                    if len(row) != len(headers):
                        # Pad or truncate to match header length
                        row = list(row) + [None] * (len(headers) - len(row))
                        row = row[:len(headers)]

                    record: dict = {}

                    # Start with global metadata so it appears first in the JSON
                    record.update(global_meta)

                    # Add table columns
                    for header, cell in zip(headers, row):
                        record[header] = clean_cell(cell)

                    # Light type coercion
                    record = coerce_types(record)

                    all_records.append(record)

    if not silent:
        print()  # newline after progress indicator
    return all_records


def deduplicate(records: list[dict]) -> list[dict]:
    """
    Remove exact-duplicate records (can happen if pdfplumber picks up
    repeated header rows mid-table).
    """
    seen = set()
    unique = []
    for r in records:
        key = json.dumps(r, sort_keys=True)
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique


def remove_header_rows(records: list[dict]) -> list[dict]:
    """
    Drop rows that look like a repeated header (e.g. Choice Code == 'Choice Code').
    """
    choice_col = "Choice Code"
    return [
        r for r in records
        if r.get(choice_col, "").lower() not in ("choice code", "choicecode")
    ]


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

def convert(pdf_path: str, output_path: str | None = None, silent: bool = False) -> str:
    """
    Convert a CAP-round PDF to a JSON file.
    Returns the path of the written JSON file.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    if output_path is None:
        output_path = pdf_path.with_suffix(".json")
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not silent:
        print(f"\n Input  : {pdf_path}")
        print(f" Output : {output_path}")
        print("-" * 50)

    records = extract_tables_from_pdf(str(pdf_path), silent=silent)

    # Post-processing
    records = remove_header_rows(records)
    records = deduplicate(records)

    if not silent:
        print(f"   {len(records)} record(s) extracted")

    # Write JSON
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    if not silent:
        print(f"   Saved -> {output_path}")
    return str(output_path)


# ─────────────────────────────────────────────
#  CLI ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    pdf_file    = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        result = convert(pdf_file, output_file)
        print(f"\n Done! JSON written to: {result}\n")
    except FileNotFoundError as e:
        print(f" Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f" Unexpected error: {e}")
        raise
