import zipfile
import csv
import os
import time

print("[INIT] Booting Tactical Financial Miner (Precision Targeting Engaged)...")
start_time = time.time()

zip_path = 'data-engine/TEC_CF_CSV.zip'
output_path = 'data-engine/tec_pac_data.csv'

if not os.path.exists(zip_path):
    print(f"[ERROR] {zip_path} not found. Ensure the state ZIP is exactly named and in the data-engine folder.")
    exit()

# 1. THE GEOGRAPHY NET
GEO_TAGS = [
    "ANGELINA", "NACOGDOCHES", "SHELBY", "LUFKIN", "DEEP EAST", 
    "ZAVALLA", "DIBOLL", "CENTER", "TIMPSON", "TENAHA",
    "NICHOLS", "ASHBY" 
]

# 2. THE THREAT NET
THREAT_TAGS = [
    "AQUIFER", "WATER", "GROUNDWATER", "CARRIZO", "WILCOX", "GCD",
    "DATA CENTER", "CLOUD", "AI ", "ARTIFICIAL INTELLIGENCE", "SERVER",
    "INFRASTRUCTURE", "ENERGY", "UTILITY", "TIMBER", "AGGREGATE"
]

# 3. THE REJECT NET (Dolphins to throw back)
REJECT_TAGS = [
    "CENTERPOINT", "WILLETT", "ABBOTT", "PAXTON", "CRUZ", "CORNYN"
]

print("[PROCESSING] Ripping through state financial records. Hunting for local infrastructure bribes...")

intercepted_records = []
total_scanned = 0

with zipfile.ZipFile(zip_path, 'r') as z:
    for filename in z.namelist():
        if filename.endswith('.csv'):
            print(f" -> Scanning sector: {filename}...")
            with z.open(filename) as f:
                decoded_file = (line.decode('utf-8', errors='ignore') for line in f)
                reader = csv.reader(decoded_file)
                
                try:
                    headers = next(reader)
                except StopIteration:
                    continue

                for row in reader:
                    total_scanned += 1
                    
                    if len(row) < 20:
                        continue
                        
                    row_string = " ".join(row).upper()
                    
                    hit_geo = any(tag in row_string for tag in GEO_TAGS)
                    hit_threat = any(tag in row_string for tag in THREAT_TAGS)
                    hit_reject = any(tag in row_string for tag in REJECT_TAGS)
                    
                    # THE FIX: Only proceed if it hits the targets AND avoids the reject tags
                    if hit_geo and hit_threat and not hit_reject:
                        try:
                            # Mapped exactly to the state's internal column structure
                            politician_name = row[8].strip() 
                            
                            org_name = row[16].strip()
                            first_name = row[19].strip()
                            last_name = row[17].strip()
                            
                            # Determine if the donor is a Corporation or an Individual
                            donor_name = org_name if org_name else f"{first_name} {last_name}".strip()
                            if not donor_name:
                                donor_name = "Undisclosed Corporate Entity"
                                
                            amount_val = row[11].replace('$', '').replace(',', '')
                            date_val = row[10]
                            
                            if any(char.isdigit() for char in amount_val) and float(amount_val) > 100:
                                record = {
                                    "Filer_Name": donor_name,
                                    "Recipient_Name": politician_name,
                                    "Amount": amount_val,
                                    "Date": date_val,
                                    "PAC_Industry": "Water/Data Infrastructure"
                                }
                                intercepted_records.append(record)
                        except Exception as e:
                            pass

print(f"\n[REPORT] Scanned {total_scanned:,} state financial records.")
print(f"[SUCCESS] Isolated {len(intercepted_records)} verified targets.")

with open(output_path, mode='w', newline='', encoding='utf-8') as out_file:
    writer = csv.DictWriter(out_file, fieldnames=["Filer_Name", "Recipient_Name", "Amount", "Date", "PAC_Industry"])
    writer.writeheader()
    for record in intercepted_records[:100]:
        writer.writerow(record)

end_time = time.time()
print(f"[READY] Dossiers compiled. Run omni_gateway.py to publish the Wall of Shame.")
print(f"Execution Time: {round(end_time - start_time, 2)} seconds")