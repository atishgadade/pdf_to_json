import json

# Define the exact required schema (NOW INCLUDES DISTRICT)
STANDARD_COLUMNS = [
    "Year", "Cap Round", "College Code", "College Name", "Choice Code", "Branch Name",
    "GOPEN", "LOPEN", "GSC", "LSC", "GST", "LST", 
    "GNTA", "LNTA", "GNTB", "LNTB", "GNTC", "LNTC", 
    "GOBC", "LOBC", "EWS", "MI", "District"
]

old_file_path = r"C:\Users\Atish Gadade\OneDrive\Desktop\pdf to json\dse_23_24_cap1.json"
new_file_path = r"C:\Users\Atish Gadade\.gemini\antigravity\scratch\pdf_to_json\DSE_2025_CAP2_new.json"
output_path = r"C:\Users\Atish Gadade\.gemini\antigravity\scratch\pdf_to_json\Final_Merged_Data_With_District.json"

def clean_record(record):
    """Enforce exact schema."""
    cleaned = {}
    for col in STANDARD_COLUMNS:
        # Default to NA if entirely missing, but for District, keep what was parsed/mapped
        cleaned[col] = record.get(col, "NA")
    return cleaned

def merge():
    print(f"Loading historic data from {old_file_path}...")
    with open(old_file_path, "r", encoding="utf-8") as f:
        old_data = json.load(f)
        
    print(f"Loaded {len(old_data)} records from historic file.")
    
    # Process old data
    processed_old_data = [clean_record(r) for r in old_data]
            
    print(f"Loading newly extracted data from {new_file_path}...")
    try:
        with open(new_file_path, "r", encoding="utf-8") as f:
            new_data = json.load(f)
            
        print(f"Loaded {len(new_data)} records from new file.")
        
        # Process new data
        processed_new_data = [clean_record(r) for r in new_data]
        
        combined_data = processed_old_data + processed_new_data
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(combined_data, f, ensure_ascii=False, indent=4)
            
        print(f"Successfully wrote {len(combined_data)} combined records to {output_path}")
        
    except FileNotFoundError:
        print("New data file not found.")

if __name__ == "__main__":
    merge()
