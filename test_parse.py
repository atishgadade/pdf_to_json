import pdfplumber
import json
import re

pdf_path = 'C:/Users/Atish Gadade/Downloads/DSE_2025_CAP2.pdf'

def test_tables():
    records = []
    
    current_college_code = ""
    current_college_name = ""
    current_choice_code = ""
    current_branch_name = ""
    
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages[:5]:
            tables = page.extract_tables()
            
            for table in tables:
                if not table: continue
                
                # Check if this is a header table
                # Usually row 0 is College, row 1 is Choice code
                if len(table) >= 2:
                    # Let's search the table for "Choice Code"
                    flat_table = [str(cell) for row in table for cell in row if cell]
                    if any("Choice Code" in cell for cell in flat_table):
                        # Extract from this table
                        # Row 0, Cell 0 usually has the college name
                        college_text = str(table[0][0])
                        m = re.match(r'^(\d+)\s+(.+)$', college_text.strip())
                        if m:
                            current_college_code = m.group(1)
                            current_college_name = m.group(2).strip()
                            
                        # Row 1 usually has Choice Code and Course Name
                        # It looks like: ['Choice Code :', '100219110', 'Course Name :', 'Civil Engineering']
                        row1 = table[1]
                        for i, cell in enumerate(row1):
                            if cell and "Choice Code" in cell and i + 1 < len(row1):
                                current_choice_code = str(row1[i+1]).strip()
                            if cell and "Course Name" in cell and i + 1 < len(row1):
                                current_branch_name = str(row1[i+1]).strip()
                                
                        continue
                        
                # If not a header table, check if it's a data table
                # Data tables usually have categories in row 0, and Stage-I in row 1
                if len(table) >= 2:
                    headers = [str(c).strip() if c else "" for c in table[0]]
                    if any(h in ["GOPEN", "LOPEN", "EWS", "GST", "GOBC", "GSC"] for h in headers):
                        # It's a data table!
                        # We merge stages. Priority: we just take the first non-empty value for each category.
                        # Wait, we want to create one record per Choice Code.
                        # If a record with this Choice Code already exists, we update it.
                        # Actually, better to maintain a current_record dict.
                        
                        # Find or create record for current choice code
                        record = next((r for r in records if r["Choice Code"] == current_choice_code), None)
                        if not record:
                            record = {
                                "Year": "2025-2026",
                                "Cap Round": 2,
                                "College Code": current_college_code,
                                "College Name": current_college_name,
                                "Choice Code": current_choice_code,
                                "Branch Name": current_branch_name
                            }
                            records.append(record)
                            
                        # Process rows
                        for row in table[1:]:
                            if not row or not row[0]: continue
                            stage = str(row[0]).strip()
                            
                            for i, cell in enumerate(row):
                                if i == 0 or i >= len(headers): continue
                                header = headers[i]
                                if not header: continue
                                
                                val = str(cell).strip()
                                # Clean up newlines in value
                                val = val.replace('\n', ' ')
                                
                                # Add to record if not already present or if it's NA
                                if header not in record or record[header] == "NA" or record[header] == "":
                                    record[header] = val
                                    
    print(json.dumps(records[:5], indent=2))

if __name__ == "__main__":
    test_tables()
