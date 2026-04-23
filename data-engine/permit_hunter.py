import os
import json
import re
from datetime import datetime

def analyze_text(text, doc_title):
    text = text.lower()
    
    # 1. The Threat Matrix (Keywords)
    threat_keywords = ['permit', 'amendment', 'hearing', 'drilling', 'export']
    found_threats = [word for word in threat_keywords if word in text]
    
    # 2. The Extraction Engine (Hunting for numbers and names)
    # Looks for numbers followed by gallons, acre-feet, or ac-ft
    volume_match = re.search(r'([\d,.]+)\s*(acre-feet|gallons|ac-ft|gpm)', text)
    volume = volume_match.group(0) if volume_match else "an undisclosed amount"
    
    # Looks for words after "application of" or "received from"
    name_match = re.search(r'(?:application of|received from|by)\s+([a-z0-9\s.,]+?)(?:\sfor|\sto|\n|,)', text)
    applicant = name_match.group(1).strip().title() if name_match else "An unknown corporation or entity"

    # 3. The 6th-Grade Translator
    if found_threats:
        status = "HIGH THREAT"
        bottom_line = f"⚠️ ALERT: {applicant} is asking the government for permission to pump {volume} of water out of the aquifer. The community needs to review this immediately."
        # For the map spikes later, we need a raw number
        raw_volume = float(re.sub(r'[^\d.]', '', volume_match.group(1))) if volume_match else 1000
    else:
        status = "CLEAR"
        bottom_line = "No major pumping requests or threats detected in this document."
        raw_volume = 0
        applicant = "None"

    return {
        "title": doc_title,
        "status": status,
        "applicant": applicant,
        "volume_requested": volume,
        "raw_volume": raw_volume,
        "bottom_line": bottom_line,
        "keywords_found": found_threats,
        "date_scanned": datetime.now().strftime("%Y-%m-%d")
    }

def generate_mock_feed():
    # Since the real government site only updates once a month, 
    # we are injecting a live test-threat so we can build the 3D map spikes.
    print("Compiling Intelligence Feed...")
    
    intel_feed = [
        analyze_text("application of MegaCorp Water Supply LLC for 5,000,000 gallons per year permit amendment hearing", "Upcoming GCD Hearing - Target A"),
        analyze_text("routine meeting minutes no new permits", "Last Month's Minutes"),
        analyze_text("received from Texas Fracking Partners a request to export 25000 acre-feet", "Emergency Export Request - Target B")
    ]
    
    # Save the data to the frontend folder so the map can see it
    os.makedirs('frontend', exist_ok=True)
    with open('frontend/threat_feed.json', 'w') as f:
        json.dump(intel_feed, f, indent=4)
    
    print("[SUCCESS] Threat feed translated to plain English and saved.")

if __name__ == "__main__":
    generate_mock_feed()
