import json
import urllib.request
import time

print("[INIT] Bypassing simulation. Connecting to USGS National Water Information System (NWIS)...")
time.sleep(1)

# REAL WORLD API: USGS Groundwater API for the Carrizo-Wilcox Bounding Box
# This pulls actual active monitoring wells and their most recent drawdown data.
USGS_API_URL = "https://waterservices.usgs.gov/nwis/gwlevels/?bBox=-98.000000,28.500000,-93.500000,33.500000&format=json"

try:
    print("[UPLINK] Fetching live telemetry from federal database...")
    with urllib.request.urlopen(USGS_API_URL) as response:
        raw_data = json.loads(response.read().decode())
except Exception as e:
    print(f"[ERROR] Connection to USGS failed: {e}")
    exit()

timeSeries = raw_data.get('value', {}).get('timeSeries', [])
print(f"[SUCCESS] Intercepted {len(timeSeries)} real-world active monitoring sites.")

live_threats = []

print("[PROCESSING] Formatting raw telemetry for DeckGL deployment...")
for site in timeSeries:
    sourceInfo = site.get('sourceInfo', {})
    location = sourceInfo.get('geoLocation', {}).get('geogLocation', {})
    siteName = sourceInfo.get('siteName', 'UNKNOWN SITE')
    
    lat = location.get('latitude')
    lon = location.get('longitude')
    
    # Extract the most recent water level drawdown metric (if available)
    values = site.get('values', [])
    drawdown = 1000 # Default baseline 
    if values and values[0].get('value'):
        try:
            # USGS often reports depth to water. We use it to scale the spike.
            drawdown_val = float(values[0]['value'][0]['value'])
            # Multiply to make the visual scale match our map's elevation settings
            drawdown = max(1000, int(drawdown_val * 100)) 
        except:
            pass

    if lat and lon:
        live_threats.append({
            "title": f"USGS ACTIVE WELL: {siteName}",
            "applicant": "REAL WORLD DATA",
            "bottom_line": f"Federal Telemetry Intercepted.<br>Live Drawdown Metric: {drawdown / 100} ft below surface.",
            "raw_volume": drawdown,
            "coordinates": [lon, lat]
        })

filepath = 'frontend/threat_feed.json'
with open(filepath, 'w') as f:
    json.dump(live_threats, f, indent=4)

print(f"\n--- DEEP SWEEP COMPLETE ---")
print(f"Total Live Targets Acquired: {len(live_threats)}")
print("[READY] Real-world payload compiled. Ready for deployment.")
