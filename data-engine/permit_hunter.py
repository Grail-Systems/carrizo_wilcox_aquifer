import json
import urllib.request
import time

print("[INIT] Initiating live-fire sequence. Connecting to USGS National Water Information System (NWIS)...")
time.sleep(1)

# Real-world USGS Groundwater API for the Carrizo-Wilcox Bounding Box
USGS_API_URL = "https://waterservices.usgs.gov/nwis/gwlevels/?bBox=-98.000000,28.500000,-93.500000,33.500000&format=json"

try:
    print("[UPLINK] Fetching live telemetry from federal database...")
    req = urllib.request.Request(USGS_API_URL, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        raw_data = json.loads(response.read().decode())
except Exception as e:
    print(f"[ERROR] Connection to USGS failed: {e}")
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
            # Scale to fit the 1000-8000 volume slider visually
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

filepath = 'frontend/threat_feed.json'
with open(filepath, 'w') as f:
    json.dump(live_threats, f, indent=4)

print(f"\n--- DEEP SWEEP COMPLETE ---")
print(f"Total Live Targets Acquired: {len(live_threats)}")
print("[READY] Real-world payload compiled. Ready for deployment.")
