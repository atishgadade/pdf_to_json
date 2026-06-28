from pdf_to_json import extract_tables_from_pdf, DISTRICT_MAP
import re

print("Map entries:", len(DISTRICT_MAP))
print("Test 1002:", DISTRICT_MAP.get("1002"))

# test string extraction
current_college_name = "Government College of Engineering, Amravati (Government Autonomous)"
MAHA_DISTRICTS = [
    "Ahmednagar", "Ahilyanagar", "Akola", "Amravati", "Beed", "Bhandara", "Buldhana", 
    "Chandrapur", "Chhatrapati Sambhajinagar", "Aurangabad", "Dharashiv", "Osmanabad", 
    "Dhule", "Gadchiroli", "Gondia", "Hingoli", "Jalgaon", "Jalna", "Kolhapur", "Latur", 
    "Mumbai", "Nagpur", "Nanded", "Nandurbar", "Nashik", "Palghar", "Parbhani", "Pune", 
    "Raigad", "Ratnagiri", "Sangli", "Satara", "Sindhudurg", "Solapur", "Thane", 
    "Wardha", "Washim", "Yavatmal"
]

district = "NA"
for dist in MAHA_DISTRICTS:
    if dist.lower() in current_college_name.lower():
        district = dist
        break
print("String extraction test:", district)
