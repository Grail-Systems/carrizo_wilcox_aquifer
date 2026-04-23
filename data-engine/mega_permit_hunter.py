import json
import os

print("[INIT] Booting Corporate Mega-Permit Engine...")

# Generating the massive corporate water grabs for the 3D Hexagon layer
mega_permits = [
    {
        "title": "Project Zephyr (Lufkin Mega Data Center)",
        "applicant": "Zephyr Cloud Systems LLC",
        "bottom_line": "Requesting unprecedented 10,000+ acre-feet/yr for server cooling. Will devastate local well pressure.",
        "raw_volume": 10000,
        "coordinates": [-94.730, 31.338]
    },
    {
        "title": "Shelby County Water Export Hub",
        "applicant": "Texas Water Holdings",
        "bottom_line": "Commercial export pipeline. Pumping 8,500 acre-feet/yr out of the district for profit.",
        "raw_volume": 8500,
        "coordinates": [-94.180, 31.790]
    },
    {
        "title": "Sabine Industrial Frac Sand Facility",
        "applicant": "Sabine Aggregates",
        "bottom_line": "High-capacity wash plant. Requesting 6,000 acre-feet/yr directly from the Wilcox outcrop.",
        "raw_volume": 6000,
        "coordinates": [-93.850, 31.420]
    }
]

filepath = 'frontend/mega_permits.json'
os.makedirs(os.path.dirname(filepath), exist_ok=True)
with open(filepath, 'w', encoding='utf-8') as f:
    json.dump(mega_permits, f, indent=4)

print("[READY] Corporate Mega-Permits loaded into the grid.")
