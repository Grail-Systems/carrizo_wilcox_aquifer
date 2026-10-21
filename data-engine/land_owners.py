#!/usr/bin/env python3
"""
Search the Angelina CAD appraisal export (August 2024, PACS fixed-width) for:
  1. parcels tied to the project sites (owner names, roads, legal descriptions)
  2. landowners whose names match donors in data-engine/tec_pac_data.csv

Run from ~/carrizo_wilcox_aquifer. Writes data-engine/land_matches.json.
Ownership is as of Aug 2024; confirm current owners before publishing.
"""
import csv, json, re
from pathlib import Path

INFO = Path.home() / "P2A" / "2024-08-01_001211_APPRAISAL_INFO.TXT"
DONORS = Path("data-engine/tec_pac_data.csv")
OUT = Path("data-engine/land_matches.json")

# PACS export field positions (1-based start, end), checked against the file
FIELDS = {
    "prop_id": (1, 12), "type": (13, 17), "geo_id": (547, 596),
    "owner": (609, 678), "addr1": (694, 753), "addr2": (754, 813),
    "addr3": (814, 873), "city": (874, 923), "state": (924, 973),
    "zip": (979, 983), "situs_num": (1040, 1049), "situs_street": (1050, 1099),
    "situs_suffix": (1100, 1109), "situs_city": (1110, 1139), "legal": (1150, 1404),
}

# What to look for at each site. Add roads or names here as you learn them.
SITES = {
    "Amp Z / former Southland mill (Herty)": {
        "owner": ["SOUTHLAND", "ABITIBI", "RESOLUTE", "AMP Z", "AMPZ"],
        "where": ["HERTY"],
    },
    "HyperDataGrid (Ben Dunn Rd)": {
        "owner": ["HYPERDATA", "HYPER DATA"],
        "where": ["BEN DUNN"],
    },
    "WattBridge (north of Lufkin)": {
        "owner": ["WATTBRIDGE", "WATT BRIDGE"],
        "where": [],
    },
    "Exacore / Oncor easement": {
        "owner": ["EXACORE"],
        "where": [],
    },
}

CORP = {"LLC", "INC", "LP", "LTD", "CO", "CORP", "COMPANY", "TRUST", "THE", "ET", "AL", "UX", "VIR", "ETAL", "ETUX", "JR", "SR"}


def field(line, name):
    a, b = FIELDS[name]
    return line[a - 1:b].strip()


def tokens(name):
    return {t for t in re.sub(r"[^A-Z0-9 ]", " ", name.upper()).split() if len(t) > 1 and t not in CORP}


def load_parcels():
    out = []
    with open(INFO, encoding="latin-1") as f:
        for line in f:
            if len(line) < 1150:
                continue
            p = {k: field(line, k) for k in FIELDS}
            p["prop_id"] = p["prop_id"].lstrip("0")
            p["situs"] = " ".join(x for x in (p.pop("situs_num"), p.pop("situs_street"), p.pop("situs_suffix")) if x)
            p["mailing"] = ", ".join(x for x in (p.pop("addr1"), p.pop("addr2"), p.pop("addr3"), p.pop("city"), p.pop("state"), p.pop("zip")) if x)
            m = re.search(r"ACRES\s*([\d.]+)", p["legal"])
            p["acres"] = float(m.group(1)) if m else None
            out.append(p)
    return out


def load_donors():
    donors = {}
    if not DONORS.exists():
        print(f"(No {DONORS}; skipping donor cross-check.)")
        return donors
    with open(DONORS, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            name = (r.get("Filer_Name") or "").strip()
            if not name:
                continue
            d = donors.setdefault(name, {"total": 0.0, "to": set(), "city": r.get("Donor_City", "")})
            try:
                d["total"] += float(r.get("Amount") or 0)
            except ValueError:
                pass
            d["to"].add(r.get("Recipient_Name", ""))
    return donors


def main():
    parcels = load_parcels()
    print(f"Read {len(parcels):,} parcels from the Aug 2024 Angelina CAD export.\n")

    site_hits = {}
    for site, rule in SITES.items():
        hits = []
        for p in parcels:
            own, where = p["owner"].upper(), f"{p['situs']} {p['legal']}".upper()
            why = [k for k in rule["owner"] if k in own] + [k for k in rule["where"] if k in where]
            if why:
                hits.append({**p, "matched_on": why})
        hits.sort(key=lambda h: -(h["acres"] or 0))
        site_hits[site] = hits
        print(f"== {site}: {len(hits)} parcels")
        for h in hits[:12]:
            ac = f"{h['acres']:.1f} ac" if h["acres"] else "  ?   "
            print(f"   {h['prop_id']:>7}  {ac:>9}  {h['owner'][:34]:34}  {h['situs'][:28]:28}  [{', '.join(h['matched_on'])}]")
        if len(hits) > 12:
            print(f"   ... {len(hits) - 12} more in land_matches.json")
        print()

    donors = load_donors()
    owner_index = {}
    for p in parcels:
        owner_index.setdefault(p["owner"], []).append(p)
    donor_hits = []
    for dname, d in donors.items():
        dt = tokens(dname)
        if len(dt) < 2:
            continue
        for owner, props in owner_index.items():
            if dt <= tokens(owner):
                donor_hits.append({
                    "donor": dname, "gave": round(d["total"], 2),
                    "to": sorted(x for x in d["to"] if x), "donor_city": d["city"],
                    "owner_on_record": owner,
                    "parcels": [{"prop_id": p["prop_id"], "acres": p["acres"], "situs": p["situs"], "legal": p["legal"], "mailing": p["mailing"]} for p in props],
                })
    donor_hits.sort(key=lambda h: -h["gave"])
    print(f"== Donors who may own land in Angelina County: {len(donor_hits)} name matches (verify each)")
    for h in donor_hits[:25]:
        acres = sum(p["acres"] or 0 for p in h["parcels"])
        print(f"   ${h['gave']:>9,.0f}  {h['donor'][:30]:30} -> {h['owner_on_record'][:30]:30} {len(h['parcels'])} parcels, {acres:,.1f} ac")

    OUT.write_text(json.dumps({
        "source": "Angelina County Appraisal District export dated 2024-08-01 (ownership as of that date)",
        "sites": site_hits, "donor_landowners": donor_hits,
    }, indent=2))
    print(f"\nSaved {OUT}")


if __name__ == "__main__":
    main()
