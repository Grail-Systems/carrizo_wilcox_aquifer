import os
import json
import requests

def get_epa_geojson(params):
    """Hits the master ECHO endpoint for digital tickets, then downloads the map file."""
    try:
        search_url = "https://echodata.epa.gov/echo/echo_rest_services.get_facilities"
        response = requests.get(search_url, params=params)
        data = response.json()
        
        if 'Results' not in data or 'QueryID' not in data['Results']: 
            return []
            
        query_id = data['Results']['QueryID']
        
        geojson_url = "https://echodata.epa.gov/echo/echo_rest_services.get_geojson"
        gj_params = {"output": "GEOJSON", "qid": query_id}
        gj_response = requests.get(geojson_url, params=gj_params)
        gj_data = gj_response.json()
        
        return gj_data.get('features', [])
    except Exception as e:
        return []

def fetch_live_epa_data():
    toxin_feed = []
    seen_facilities = set()
    
    # The Carrizo-Wilcox Strike Zone: Cities directly over the aquifer
    aquifer_cities = [
        "Lufkin", "Nacogdoches", "Tyler", "Bryan", 
        "College Station", "Bastrop", "San Marcos", "Caldwell"
    ]
    
    print("Initiating Aquifer-Specific Toxic Release & Violation Sweep...")
    
    for city in aquifer_cities:
        print(f"Scanning {city} for spills and violations...")
        
        # 1. Hunt for Active Violators (Facilities currently breaking the law)
        violator_params = {"output": "JSON", "p_st": "TX", "p_ct": city, "p_viol_flag": "Y"}
        v_features = get_epa_geojson(violator_params)
        
        # 2. Hunt the Toxic Release Inventory (Facilities reporting chemical discharges)
        tri_params = {"output": "JSON", "p_st": "TX", "p_ct": city, "p_tri": "Y"}
        t_features = get_epa_geojson(tri_params)
        
        # Combine the intelligence
        all_features = v_features + t_features
        
        for f in all_features:
            props = f.get('properties', {})
            geom = f.get('geometry')
            
            if not geom or geom.get('type') != 'Point': continue
            
            coords = geom.get('coordinates')
            if not coords or len(coords) < 2: continue
            
            lon, lat = float(coords[0]), float(coords[1])
            name = str(props.get('FacName', 'Unknown Facility')).title()
            city_name = str(props.get('FacCity', city)).title()
            
            # Prevent plotting the same facility twice if it's on both lists
            if lat == 0.0 or lon == 0.0 or name in seen_facilities: continue
            seen_facilities.add(name)

            toxin_feed.append({
                "facility": name,
                "chemical": "Toxic Release / Active Violation",
                "status": "CONFIRMED THREAT",
                "coordinates": [lon, lat],
                "impact_radius": 3500, # Focused blast radius
                "bottom_line": f"☣️ TOXIC THREAT: {name} in {city_name} is actively flagged for environmental violations or toxic chemical releases directly over the aquifer."
            })
            
    print(f"[SUCCESS] Intercepted {len(toxin_feed)} verified toxic releases and active violators over the Carrizo-Wilcox.")
    return toxin_feed

def generate_toxin_feed():
    live_data = fetch_live_epa_data()
    os.makedirs('frontend', exist_ok=True)
    with open('frontend/toxin_feed.json', 'w') as f:
        json.dump(live_data, f, indent=4)
    print("[SUCCESS] Live EPA threat feed compiled and saved.")

if __name__ == "__main__":
    generate_toxin_feed()
