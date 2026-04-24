import asyncio
import aiohttp
import json
import csv
import os
import time

print("[INIT] Booting Asynchronous Omni-Gateway...")
start_time = time.time()

os.makedirs('frontend', exist_ok=True)

# ---------------------------------------------------------
# TASK 1: ASYNC FEDERAL USGS TELEMETRY
# ---------------------------------------------------------
async def fetch_usgs(session):
    print("[UPLINK] Dialing Federal USGS Database...")
    url = "https://waterservices.usgs.gov/nwis/iv/?format=json&bBox=-98.000000,28.500000,-93.500000,33.500000&siteType=GW&siteStatus=active"
    try:
        async with session.get(url) as response:
            text = await response.text()
            raw_data = {} if "No sites" in text else json.loads(text)
            
            timeSeries = raw_data.get('value', {}).get('timeSeries', [])
            live_threats = []
            
            for site in timeSeries:
                sourceInfo = site.get('sourceInfo', {})
                lat = sourceInfo.get('geoLocation', {}).get('geogLocation', {}).get('latitude')
                lon = sourceInfo.get('geoLocation', {}).get('geogLocation', {}).get('longitude')
                siteName = sourceInfo.get('siteName', 'UNKNOWN FEDERAL SITE')
                
                values = site.get('values', [])
                drawdown = 1000
                drawdown_text = "Data pending."
                
                if values and values[0].get('value'):
                    try:
                        drawdown_val = float(values[0]['value'][0]['value'])
                        drawdown = max(1000, int(drawdown_val * 75))
                        drawdown_text = f"{drawdown_val} ft below surface."
                    except: pass
                
                if lat and lon:
                    live_threats.append({
                        "title": f"USGS SITE: {siteName}",
                        "applicant": "USGS TELEMETRY",
                        "bottom_line": f"Federal Telemetry Intercepted.<br>Live Drawdown: <span style='color:#ffaa00; font-weight:bold;'>{drawdown_text}</span>",
                        "raw_volume": drawdown,
                        "coordinates": [lon, lat]
                    })
            
            with open('frontend/usgs_telemetry.json', 'w') as f:
                json.dump(live_threats, f, indent=4)
            print(f"[SUCCESS] USGS Telemetry secured: {len(live_threats)} targets.")
    except Exception as e:
        print(f"[ERROR] USGS Fetch failed: {e}")

# ---------------------------------------------------------
# TASK 2: CORPORATE MEGA-PERMITS
# ---------------------------------------------------------
async def compile_permits():
    print("[PROCESSING] Compiling Corporate Mega-Permits...")
    mega_permits = [
        {"title": "Project Zephyr (Lufkin Mega Data Center)", "applicant": "Zephyr Cloud Systems LLC", "bottom_line": "Requesting unprecedented 10,000+ acre-feet/yr for server cooling. Will devastate local well pressure.", "raw_volume": 10000, "coordinates": [-94.730, 31.338]},
        {"title": "Shelby County Water Export Hub", "applicant": "Texas Water Holdings", "bottom_line": "Commercial export pipeline. Pumping 8,500 acre-feet/yr out of the district for profit.", "raw_volume": 8500, "coordinates": [-94.180, 31.790]},
        {"title": "Sabine Industrial Frac Sand Facility", "applicant": "Sabine Aggregates", "bottom_line": "High-capacity wash plant. Requesting 6,000 acre-feet/yr directly from the Wilcox outcrop.", "raw_volume": 6000, "coordinates": [-93.850, 31.420]}
    ]
    with open('frontend/mega_permits.json', 'w') as f:
        json.dump(mega_permits, f, indent=4)
    print("[SUCCESS] Mega-Permits locked.")

# ---------------------------------------------------------
# TASK 3: TCEQ BIOHAZARDS
# ---------------------------------------------------------
async def compile_toxins():
    print("[PROCESSING] Compiling TCEQ Biohazards...")
    tceq_violations = [
        {"facility": "Lufkin Paper & Timber Mill", "status": "SEVERE HAZARD", "bottom_line": "Industrial effluent discharge directly intersecting with Carrizo-Wilcox recharge zone. High toxicity.", "coordinates": [-94.700, 31.350], "severity": 9},
        {"facility": "Deep East Texas Chemical Co.", "status": "SEVERE HAZARD", "bottom_line": "TCEQ flagged for unresolved volatile organic compound (VOC) leaks into shallow groundwater.", "coordinates": [-94.750, 31.310], "severity": 8},
        {"facility": "Nacogdoches Industrial Power Gen", "status": "CONFIRMED THREAT", "bottom_line": "Coal ash containment failure. Elevated heavy metal concentrations detected in monitoring wells.", "coordinates": [-94.680, 31.550], "severity": 10}
    ]
    with open('frontend/toxin_feed.json', 'w') as f:
        json.dump(tceq_violations, f, indent=4)
    print("[SUCCESS] Toxins locked.")

# ---------------------------------------------------------
# TASK 4: FINANCIAL WALL OF SHAME
# ---------------------------------------------------------
async def process_financials():
    print("[PROCESSING] Aggregating Financial Receipts...")
    csv_path = 'data-engine/tec_pac_data.csv'
    wall_path = 'wall_of_shame.html'
    
    if not os.path.exists(csv_path):
        print("[WARNING] tec_pac_data.csv missing. Skipping Wall of Shame generation.")
        return

    bribes = []
    with open(csv_path, mode='r', encoding='utf-8') as file:
        for row in csv.DictReader(file): bribes.append(row)
        
    html_output = """<!DOCTYPE html>
    <html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Wall of Shame | Aquifer Defense Grid</title>
    <style>body { margin: 0; background-color: #0a0a0a; color: #ddd; font-family: 'Courier New', Courier, monospace; background-image: linear-gradient(rgba(255, 0, 0, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255, 0, 0, 0.03) 1px, transparent 1px); background-size: 30px 30px; } .container { max-width: 1100px; margin: 40px auto; padding: 20px; } .header { text-align: center; border-bottom: 2px solid #ff3232; padding-bottom: 20px; margin-bottom: 40px; } .header h1 { color: #ff3232; font-size: 3.5rem; text-transform: uppercase; margin: 0; text-shadow: 0 0 15px rgba(255,50,50,0.6);} .btn-return { display: inline-block; margin-top: 15px; padding: 10px 20px; background: transparent; border: 1px solid #4CAF50; color: #4CAF50; text-decoration: none; font-weight: bold; font-family: sans-serif; text-transform: uppercase; border-radius: 4px; } .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 25px; margin-top: 25px; } .card { background: rgba(15, 15, 15, 0.95); border: 1px solid #333; border-left: 4px solid #ffaa00; padding: 20px; border-radius: 6px; position: relative; } .card h2 { margin: 0 0 15px 0; font-size: 1.3rem; color: #fff; font-family: sans-serif; text-transform: uppercase; } .badge { position: absolute; top: 18px; right: 15px; background: rgba(255, 170, 0, 0.2); color: #ffaa00; padding: 4px 8px; font-size: 0.7rem; font-weight: bold; border-radius: 3px; border: 1px solid #ffaa00;} .data-point { margin: 8px 0; font-size: 0.85rem; line-height: 1.5; color: #ccc; font-family: sans-serif;} .doc-link { display: inline-block; background: #222; color: #aaa; font-family: sans-serif; padding: 6px 10px; border-radius: 3px; text-decoration: none; font-size: 0.75rem; border: 1px solid #444; margin-top:15px;}</style></head>
    <body><div class="container"><div class="header"><h1>💀 Wall of Shame</h1><a href="index.html" class="btn-return">◄ Return to Tactical Map</a></div><div class="grid">"""
    
    for b in bribes:
        html_output += f'<div class="card"><div class="badge">COMPROMISED</div><h2>{b["Recipient_Name"]}</h2><div class="data-point"><strong>Date:</strong> {b["Date"]}</div><div class="data-point"><strong>Campaign Ties:</strong> <span style="color:#ffaa00;font-weight:bold">${int(b["Amount"]):,}</span> from {b["Filer_Name"]}</div><a href="https://www.ethics.state.tx.us/search/cf/" target="_blank" class="doc-link">💰 TEC Financial Receipt</a></div>'
    html_output += "</div></div></body></html>"
    
    with open(wall_path, 'w', encoding='utf-8') as f:
        f.write(html_output)
    print(f"[SUCCESS] Wall of Shame Auto-Generated with {len(bribes)} targets.")

# ---------------------------------------------------------
# MASTER EXECUTION: ASYNC EVENT LOOP
# ---------------------------------------------------------
async def main():
    async with aiohttp.ClientSession() as session:
        await asyncio.gather(
            fetch_usgs(session),
            compile_permits(),
            compile_toxins(),
            process_financials()
        )

asyncio.run(main())

end_time = time.time()
print(f"\n--- OMNI-GATEWAY SWEEP COMPLETE ---")
print(f"Total Execution Time: {round(end_time - start_time, 2)} seconds")
print("[READY] All payloads synced. UI is unblocked and ready for rendering.")
