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
    "year":         r"(?:year|academic year|AY)[:\s]+(\d{4}[-–]\d{2,4})",
    "cap_round":    r"cap\s*round[:\s#]*(I{1,3}|\d+)",
}

# The standard columns to always include in the output to ensure uniform JSON structure
# Matches the exact structure of dse_23_24_cap1.json
STANDARD_COLUMNS = [
    "GOPEN", "LOPEN", "GSC", "LSC", "GST", "LST", 
    "GNTA", "LNTA", "GNTB", "LNTB", "GNTC", "LNTC", 
    "GOBC", "LOBC", "EWS", "MI", "District"
]

def clean_cell(value) -> str:
    """Normalise a cell value: strip whitespace, unify empty/null to 'NA'."""
    if not value:
        return "NA"
    s = str(value).strip()
    if s in ("", "-", "--", "N/A", "n/a", "nil", "Nil", "None"):
        return "NA"
    # collapse internal newlines
    s = re.sub(r"\s*\n\s*", " ", s)
    return s

def extract_metadata_from_text(text: str) -> dict:
    meta = {}
    for field, pattern in META_FIELDS.items():
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            # Convert roman numerals for rounds
            if val.upper() == "I": val = 1
            elif val.upper() == "II": val = 2
            elif val.upper() == "III": val = 3
            meta[field] = val
    return meta

# Load the district mapping dictionary if available
DISTRICT_MAP = {}
try:
    dist_map_path = Path(__file__).resolve().parent / "college_districts.json"
    if dist_map_path.exists():
        with open(dist_map_path, "r", encoding="utf-8") as f:
            DISTRICT_MAP = json.load(f)
        print(f"DEBUG: Loaded district map with {len(DISTRICT_MAP)} entries.")
    else:
        print(f"DEBUG: District map not found at {dist_map_path}")
except Exception as e:
    print(f"DEBUG: Failed to load district map: {e}")

def extract_tables_from_pdf(pdf_path: str, silent: bool = False) -> list[dict]:
    all_records = []
    
    global_meta = {
        "Year": "2024-2025", # Fallback
        "Cap Round": 1       # Fallback
    }

    current_college_code = ""
    current_college_name = ""
    current_choice_code = ""
    current_branch_name = ""

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        if not silent:
            print(f"  -> {total_pages} page(s) found in PDF")

        for page_num, page in enumerate(pdf.pages, start=1):
            if not silent:
                print(f"  Processing page {page_num}/{total_pages} ...", end="\r")

            raw_text = page.extract_text() or ""
            page_meta = extract_metadata_from_text(raw_text)
            
            if "year" in page_meta:
                global_meta["Year"] = page_meta["year"]
            if "cap_round" in page_meta:
                global_meta["Cap Round"] = page_meta["cap_round"]

            tables = page.extract_tables()
            
            for table in tables:
                if not table: continue
                
                # Check if this is a header table containing College and Branch info
                if len(table) >= 2:
                    flat_table = [str(cell) for row in table for cell in row if cell]
                    if any("Choice Code" in str(cell) for cell in flat_table):
                        # Extract College Name from the first cell of the first row
                        college_text = str(table[0][0])
                        m = re.match(r'^(\d+)\s+(.+)$', college_text.strip())
                        if m:
                            current_college_code = m.group(1)
                            current_college_name = m.group(2).strip()
                            
                        # Extract Choice Code and Course Name from the second row
                        row1 = table[1]
                        for i, cell in enumerate(row1):
                            if cell and "Choice Code" in str(cell) and i + 1 < len(row1):
                                current_choice_code = str(row1[i+1]).strip()
                            if cell and "Course Name" in str(cell) and i + 1 < len(row1):
                                current_branch_name = str(row1[i+1]).strip()
                        continue
                        
                # Check if it's a data table containing cutoff scores
                if len(table) >= 2:
                    headers = [str(c).strip().upper() if c else "" for c in table[0]]
                    if any(h in STANDARD_COLUMNS for h in headers):
                        # Find or create record for current choice code
                        record = next((r for r in all_records if r.get("Choice Code") == current_choice_code), None)
                        if not record:
                            # 1. Lookup District by College Code
                            code_str = str(current_college_code).strip()
                            if code_str in DISTRICT_MAP:
                                district = DISTRICT_MAP[code_str]
                            else:
                                # 2. User-provided strict list of 36 Maharashtra Districts
                                MAHA_DISTRICTS = [
                                    "Ahmednagar", "Ahilyanagar", "Akola", "Amravati", "Beed", "Bhandara", "Buldhana", 
                                    "Chandrapur", "Chhatrapati Sambhajinagar", "Aurangabad", "Dharashiv", "Osmanabad", 
                                    "Dhule", "Gadchiroli", "Gondia", "Hingoli", "Jalgaon", "Jalna", "Kolhapur", "Latur", 
                                    "Mumbai", "Nagpur", "Nanded", "Nandurbar", "Nashik", "Palghar", "Parbhani", "Pune", 
                                    "Raigad", "Ratnagiri", "Sangli", "Satara", "Sindhudurg", "Solapur", "Thane", 
                                    "Wardha", "Washim", "Yavatmal"
                                ]
                                
                                district = "NA"
                                # Search for any valid district name inside the College Name
                                for dist in MAHA_DISTRICTS:
                                    if dist.lower() in current_college_name.lower():
                                        district = dist
                                        break
                                
                                # 3. Final naive comma fallback if everything fails
                                if district == "NA" and "," in current_college_name:
                                    parts = current_college_name.split(",")
                                    dist_part = parts[-1]
                                    if "(" in dist_part:
                                        dist_part = dist_part.split("(")[0]
                                    district = dist_part.strip()

                            record = {
                                "Year": global_meta["Year"],
                                "Cap Round": global_meta["Cap Round"],
                                "College Code": int(current_college_code) if current_college_code.isdigit() else current_college_code,
                                "College Name": current_college_name,
                                "Choice Code": current_choice_code,
                                "Branch Name": current_branch_name,
                                "District": district
                            }
                            # Initialize all standard columns to NA only if not already set
                            for col in STANDARD_COLUMNS:
                                if col not in record:
                                    record[col] = "NA"
                                
                            all_records.append(record)
                            
                        # Process rows (Stage-I, Stage-II, etc.)
                        for row in table[1:]:
                            if not row or not row[0]: continue
                            
                            for i, cell in enumerate(row):
                                if i == 0 or i >= len(headers): continue
                                header = headers[i]
                                if not header: continue
                                
                                val = clean_cell(cell)
                                
                                # Add to record if not already present or if it's currently NA
                                # This inherently merges multiple stages while prioritizing the first seen score (usually Stage-I)
                                if header in record:
                                    if record[header] == "NA" and val != "NA":
                                        record[header] = val
                                # Notice we DO NOT dynamically add any extra columns, enforcing the strict schema.

    if not silent:
        print()
    return all_records

# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

def convert(pdf_path: str, output_path: str | None = None, silent: bool = False) -> str:
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

    if not silent:
        print(f"   {len(records)} record(s) extracted")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    if not silent:
        print(f"   Saved -> {output_path}")
    return str(output_path)


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
