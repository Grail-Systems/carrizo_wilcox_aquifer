import csv
import os

print("[INIT] Booting Infinite-Scroll Financial Engine...")

csv_path = 'data-engine/tec_pac_data.csv'
wall_path = 'wall_of_shame.html'

if not os.path.exists(csv_path):
    print("[ERROR] tec_pac_data.csv not found. Drop the state database into the data-engine folder.")
    exit()

print("[UPLINK] Parsing State Finance Records...")

# 1. READ THE UNLIMITED CSV DATA
bribes = []
with open(csv_path, mode='r', encoding='utf-8') as file:
    reader = csv.DictReader(file)
    for row in reader:
        bribes.append(row)

print(f"[SUCCESS] Intercepted {len(bribes)} financial transactions.")
print("[PROCESSING] Generating dynamic HTML ledger...")

# 2. THE HTML MASTER TEMPLATE (Header)
html_output = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Wall of Shame | Aquifer Defense Grid</title>
    <style>
        body { margin: 0; padding: 0; background-color: #0a0a0a; color: #ddd; font-family: 'Courier New', Courier, monospace; background-image: linear-gradient(rgba(255, 0, 0, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255, 0, 0, 0.03) 1px, transparent 1px); background-size: 30px 30px; }
        .container { max-width: 1100px; margin: 40px auto; padding: 20px; }
        .header { text-align: center; border-bottom: 2px solid #ff3232; padding-bottom: 20px; margin-bottom: 40px; }
        .header h1 { color: #ff3232; font-size: 3.5rem; text-transform: uppercase; margin: 0; text-shadow: 0 0 15px rgba(255,50,50,0.6); letter-spacing: 2px;}
        .header p { font-family: sans-serif; color: #aaa; font-size: 1.1rem; max-width: 700px; margin: 10px auto; line-height: 1.5;}
        .btn-return { display: inline-block; margin-top: 15px; padding: 10px 20px; background: transparent; border: 1px solid #4CAF50; color: #4CAF50; text-decoration: none; font-weight: bold; font-family: sans-serif; text-transform: uppercase; transition: 0.3s; border-radius: 4px; }
        .btn-return:hover { background: rgba(76, 175, 80, 0.2); box-shadow: 0 0 10px rgba(76, 175, 80, 0.5); }
        .section-title { color: #ffaa00; border-bottom: 1px solid #444; padding-bottom: 5px; margin-top: 50px; text-transform: uppercase; font-family: sans-serif; font-size: 1.5rem; letter-spacing: 1px;}
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 25px; margin-top: 25px; }
        
        .card { background: rgba(15, 15, 15, 0.95); border: 1px solid #333; border-left: 4px solid #ff3232; padding: 20px; border-radius: 6px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); position: relative; display: flex; flex-direction: column; }
        .card.politician { border-left-color: #ffaa00; }
        .card h2 { margin: 0 0 15px 0; font-size: 1.3rem; color: #fff; font-family: sans-serif; text-transform: uppercase; padding-right: 95px; line-height: 1.3;}
        .badge { position: absolute; top: 18px; right: 15px; background: rgba(255, 50, 50, 0.2); color: #ff3232; padding: 4px 8px; font-size: 0.7rem; font-weight: bold; border-radius: 3px; border: 1px solid #ff3232; letter-spacing: 1px; }
        .badge.pol { background: rgba(255, 170, 0, 0.2); color: #ffaa00; border-color: #ffaa00;}
        .data-point { margin: 8px 0; font-size: 0.85rem; line-height: 1.5; color: #ccc; font-family: sans-serif;}
        .highlight-pol { color: #ffaa00; font-weight: bold; }
        
        .evidence-locker { margin-top: auto; padding-top: 15px; border-top: 1px solid #333; }
        .evidence-locker strong { font-size: 0.75rem; color: #888; text-transform: uppercase; display: block; margin-bottom: 8px; font-family: monospace;}
        .doc-link { display: inline-block; background: #222; color: #aaa; font-family: sans-serif; padding: 6px 10px; margin: 0 5px 5px 0; border-radius: 3px; text-decoration: none; font-size: 0.75rem; border: 1px solid #444; transition: 0.2s; font-weight: bold; }
        .doc-link.financial:hover { border-color: #ffaa00; color: #ffaa00; background: rgba(255,170,0,0.1);}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>💀 Wall of Shame</h1>
            <p>Public accountability ledger for the individuals, shell corporations, and compromised officials facilitating the extraction and contamination of the Carrizo-Wilcox aquifer.</p>
            <a href="index.html" class="btn-return">◄ Return to Tactical Map</a>
        </div>
        
        <h2 class="section-title">Compromised Officials & Boards</h2>
        <div class="grid">
"""

# 3. DYNAMICALLY GENERATE INFINITE CARDS
for bribe in bribes:
    card_html = f"""
            <div class="card politician">
                <div class="badge pol">COMPROMISED</div>
                <h2>{bribe['Recipient_Name']}</h2>
                <div class="data-point"><strong>Date Logged:</strong> {bribe['Date']}</div>
                <div class="data-point"><strong>Identified Campaign Ties:</strong> <span class="highlight-pol">${int(bribe['Amount']):,}</span> accepted from the {bribe['Filer_Name']} ({bribe['PAC_Industry']} sector).</div>
                <div class="data-point"><strong>Status:</strong> Aiding in the industrial extraction and depletion of regional groundwater.</div>
                
                <div class="evidence-locker">
                    <strong>[ FINANCIAL RECEIPTS ]</strong>
                    <a href="https://www.ethics.state.tx.us/search/cf/" target="_blank" class="doc-link financial">💰 TEC Database Verification</a>
                </div>
            </div>
    """
    html_output += card_html

# 4. THE HTML FOOTER
html_output += """
        </div>
    </div>
</body>
</html>
"""

# 5. OVERWRITE THE LIVE WEBSITE FILE
with open(wall_path, 'w', encoding='utf-8') as file:
    file.write(html_output)

print("\n--- DEEP SWEEP COMPLETE ---")
print(f"[READY] {len(bribes)} dossiers auto-generated. Wall of Shame rewritten. Ready to push.")
