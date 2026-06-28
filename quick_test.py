from pdf_to_json import extract_tables_from_pdf, DISTRICT_MAP
import pdfplumber

# Let's see if the map is loaded
print(f"Map size: {len(DISTRICT_MAP)}")

# Let's inspect the first 2 pages so it's fast
pdf_path = r"C:\Users\Atish Gadade\Downloads\DSE_2025_CAP2.pdf"

# We'll patch pdfplumber.open to only return the first page so it finishes instantly
import sys

import pdfplumber

def mock_open(path):
    pass

pdf = pdfplumber.open(pdf_path)
page = pdf.pages[0]
raw_text = page.extract_text()
tables = page.extract_tables()

# Let's see if the logic works on the first table
current_college_code = ""
for table in tables:
    if len(table) >= 2:
        college_text = str(table[0][0])
        import re
        m = re.match(r'^(\d+)\s+(.+)$', college_text.strip())
        if m:
            current_college_code = m.group(1)
            
            code_str = str(current_college_code).strip()
            if code_str in DISTRICT_MAP:
                print("FOUND IN MAP:", DISTRICT_MAP[code_str])
            else:
                print(f"NOT FOUND IN MAP. code='{code_str}' type={type(code_str)}")
pdf.close()
