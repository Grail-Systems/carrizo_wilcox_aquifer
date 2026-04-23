import csv
import os

print("[INIT] Booting Financial Cross-Referencing Engine...")

csv_path = 'data-engine/tec_pac_data.csv'
wall_path = 'wall_of_shame.html'

if not os.path.exists(csv_path) or not os.path.exists(wall_path):
    print("[ERROR] Missing required files. Ensure tec_pac_data.csv and wall_of_shame.html exist.")
    exit()

print("[UPLINK] Scanning Texas Ethics Commission PAC records...")

# Step 1: Extract the Bribes
bribes = []
with open(csv_path, mode='r', encoding='utf-8') as file:
    reader = csv.DictReader(file)
    for row in reader:
        bribes.append({
            "donor": row["Filer_Name"],
            "recipient": row["Recipient_Name"],
            "amount": int(row["Amount"]),
            "industry": row["PAC_Industry"]
        })

print(f"[SUCCESS] Extracted {len(bribes)} high-profile PAC transactions.")
print("[PROCESSING] Weaponizing Wall of Shame with financial receipts...")

# Step 2: Inject the Bribes into the Wall of Shame HTML
with open(wall_path, 'r', encoding='utf-8') as file:
    html_content = file.read()

# Target 1 Injection (The Politician)
pol_bribe = next((b for b in bribes if "Nichols" in b["recipient"] or "Ashby" in b["recipient"]), bribes[0])
html_content = html_content.replace("[Local Official / Board Member]", pol_bribe["recipient"])
html_content = html_content.replace("$12,500+", f"${pol_bribe['amount']:,}")
html_content = html_content.replace("industrial water and energy PACs.", f"the {pol_bribe['donor']} ({pol_bribe['industry']} sector).")

# Target 2 Injection (The Local Board)
board_bribe = next((b for b in bribes if "GCD" in b["recipient"] or "Judge" in b["recipient"]), bribes[1])
html_content = html_content.replace("[Target Corporate Entity]", board_bribe["donor"])
html_content = html_content.replace("Extracting 7,000+ acre-feet/year", f"Financed local authorities with ${board_bribe['amount']:,} to secure extraction rights")

# Step 3: Save the Weaponized HTML
with open(wall_path, 'w', encoding='utf-8') as file:
    file.write(html_content)

print("\n--- DEEP SWEEP COMPLETE ---")
print("[READY] Financial ledgers injected. Wall of Shame updated. Ready to push.")
