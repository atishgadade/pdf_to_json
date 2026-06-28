import json
from pathlib import Path

old_file = r"C:\Users\Atish Gadade\OneDrive\Desktop\pdf to json\dse_23_24_cap1.json"
output_file = r"C:\Users\Atish Gadade\.gemini\antigravity\scratch\pdf_to_json\college_districts.json"

def build_mapping():
    with open(old_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    mapping = {}
    for record in data:
        code = str(record.get("College Code", ""))
        dist = record.get("District", "")
        if code and dist and dist != "NA":
            mapping[code] = dist
            
    print(f"Found {len(mapping)} unique college-to-district mappings.")
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=4)
        
if __name__ == "__main__":
    build_mapping()
