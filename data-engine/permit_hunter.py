import json
import urllib.request
import time

print("[INIT] Initiating live-fire sequence. Connecting to USGS NWIS...")
time.sleep(1)

# Switching to the 'iv' (Instantaneous Values) endpoint for active Groundwater (GW) sites
# This pulls true live telemetry in the exact Carrizo-Wilcox bounding box.
USGS_API_URL = "https://waterservices.usgs.gov/nwis/iv/?format=json&bBox=-98.000000,28.500000,-93.500000,33.500000&siteType=GW&siteStatus=active"

try:
    print("[UPLINK] Fetching live telemetry from federal database...")
    req = urllib.request.Request(USGS_API_URL, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        raw_response = response.read().decode('utf-8')
        
        # Bulletproof check: Did the feds send back text instead of JSON?
        if "No sites" in raw_response or not raw_response.strip():
            print("[WARNING] Federal database returned 0 active sites for this query. Grid blindspot detected.")
            raw_data = {}
        else:
            raw_data = json.loads(raw_response)
            
except Exception as e:
    print(f"[ERROR] Connection failed: {e}")
    exit()

timeSeries = raw_data.get('value', {}).get('timeSeries', [])
print(f"[SUCCESS] Intercepted {len(timeSeries)} real-world active monitoring sites.")

live_threats = []

print("[PROCESSING] Formatting raw federal telemetry for DeckGL deployment...")
for site in timeSeries:
    sourceInfo = site.get('sourceInfo', {})
    location = sourceInfo.get('geoLocation', {}).get('geogLocation', {})
    siteName = sourceInfo.get('siteName', 'UNKNOWN FEDERAL SITE')
    
    lat = location.get('latitude')
    lon = location.get('longitude')
    
    values = site.get('values', [])
    drawdown = 1000 
    drawdown_text = "Data obscured or pending."
    
    if values and values[0].get('value'):
        try:
            drawdown_val = float(values[0]['value'][0]['value'])
            # Scale the raw water level so it renders visibly on our 3D UI
            drawdown = max(1000, int(drawdown_val * 75)) 
            drawdown_text = f"{drawdown_val} ft below surface."
        except:
            pass

    if lat and lon:
        live_threats.append({
            "title": f"USGS SITE: {siteName}",
            "applicant": "USGS LIVE TELEMETRY",
            "bottom_line": f"Federal Telemetry Intercepted.<br>Live Drawdown Metric: <span style='color:#ff3232; font-weight:bold;'>{drawdown_text}</span>",
            "raw_volume": drawdown,
            "coordinates": [lon, lat]
        })

# OVERWRITE THE FAKE JSON WITH REAL DATA
filepath = 'frontend/threat_feed.json'
with open(filepath, 'w') as f:
    json.dump(live_threats, f, indent=4)

print(f"\n--- DEEP SWEEP COMPLETE ---")
print(f"Total Live Targets Acquired: {len(live_threats)}")
print("[READY] Real-world payload compiled. Ready for deployment.")
