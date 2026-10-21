#!/usr/bin/env python3
"""
Pull Texas roll-call votes from LegiScan's weekly datasets and record how
Ashby, Nichols, Clardy and Thigpen voted on water, energy, grid,
pipeline and crypto/data-center bills.

Data: LegiScan, licensed CC BY 4.0 (attribution required on the site).
Uses a handful of API queries per run (one list + one per changed session).
"""
import base64, json, re, sys, zipfile, urllib.request, urllib.parse
from datetime import datetime
from pathlib import Path

HOME = Path.home()
KEY_FILE = HOME / ".legiscan"
CACHE = HOME / "P2A" / "legiscan"          # zips live here, outside the repo
OUT = Path(__file__).resolve().parent / "votes.json"
MIN_YEAR = 2019

TARGETS = {
    "ASHBY": "Trenton E. Ashby",
    "NICHOLS": "Robert Lee Nichols",
    "CLARDY": "Travis P. Clardy",
    "THIGPEN": 'Alan R. "Rocky" Thigpen',
}

KEYWORDS = [
    "WATER", "AQUIFER", "GROUNDWATER", "DATA CENTER", "ELECTRIC",
    "TRANSMISSION", "ERCOT", "GRID", "UTILIT", "CRYPTO", "BITCOIN",
    "BLOCKCHAIN", "VIRTUAL CURRENCY", "PIPELINE", "OIL", "GAS",
    "EMINENT DOMAIN", "LARGE LOAD",
]
KW_RE = re.compile(r"\b(" + "|".join(re.escape(k) for k in KEYWORDS) + ")")


def load_key():
    if not KEY_FILE.exists():
        sys.exit("No key found. Save it first:  echo 'LEGISCAN_KEY=\"yourkey\"' > ~/.legiscan")
    txt = KEY_FILE.read_text().strip()
    if "=" in txt:
        txt = txt.split("=", 1)[1]
    key = txt.strip().strip('"').strip("'")
    if not key or "paste" in key.lower():
        sys.exit("~/.legiscan still has the placeholder. Put your real key in it.")
    return key


def api(key, op, **params):
    q = urllib.parse.urlencode({"key": key, "op": op, **params})
    with urllib.request.urlopen(urllib.request.Request(f"https://api.legiscan.com/?{q}", headers={"User-Agent": "ETLC-AquiferGrid/1.0 (grailsystems.io)"}), timeout=600) as r:
        data = json.load(r)
    if data.get("status") != "OK":
        sys.exit(f"LegiScan error on {op}: {data.get('alert', data)}")
    return data


def get_zip(key, ds):
    """Download a session zip only if LegiScan's hash says it changed."""
    CACHE.mkdir(parents=True, exist_ok=True)
    sid, h = ds["session_id"], ds["dataset_hash"]
    path = CACHE / f"TX_{sid}.zip"
    hfile = CACHE / f"TX_{sid}.hash"
    if path.exists() and hfile.exists() and hfile.read_text() == h:
        print(f"  cached   {ds['session_name']}")
        return path
    print(f"  download {ds['session_name']} ...")
    d = api(key, "getDataset", id=sid, access_key=ds["access_key"])
    path.write_bytes(base64.b64decode(d["dataset"]["zip"]))
    hfile.write_text(h)
    return path


def read_session(path):
    people, bills, rolls = {}, {}, []
    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            if not name.endswith(".json"):
                continue
            j = json.loads(z.read(name))
            if "/people/" in name:
                p = j["person"]; people[p["people_id"]] = p
            elif "/bill/" in name:
                b = j["bill"]; bills[b["bill_id"]] = b
            elif "/vote/" in name:
                rolls.append(j["roll_call"])
    return people, bills, rolls


def main():
    key = load_key()
    print("Checking LegiScan dataset list for Texas...")
    dl = api(key, "getDatasetList", state="TX")["datasetlist"]
    sessions = sorted((d for d in dl if int(d["year_start"]) >= MIN_YEAR),
                      key=lambda d: d["year_start"])

    results = {name: [] for name in TARGETS.values()}
    matched_people = {}

    for ds in sessions:
        path = get_zip(key, ds)
        people, bills, rolls = read_session(path)

        ids = {}
        for pid, p in people.items():
            last = (p.get("last_name") or "").upper()
            if last in TARGETS:
                ids[pid] = TARGETS[last]
                matched_people[f"{p.get('name')} ({p.get('role')}-{p.get('district')})"] = TARGETS[last]

        for rc in rolls:
            bill = bills.get(rc["bill_id"])
            if not bill:
                continue
            text = f"{bill.get('title', '')} {bill.get('description', '')}".upper()
            hit = KW_RE.search(text)
            if not hit:
                continue
            for v in rc.get("votes", []):
                who = ids.get(v["people_id"])
                if not who:
                    continue
                results[who].append({
                    "date": rc.get("date"),
                    "session": ds["session_name"],
                    "chamber": rc.get("chamber"),
                    "bill": bill.get("bill_number"),
                    "title": bill.get("title"),
                    "motion": rc.get("desc"),
                    "vote": v.get("vote_text"),
                    "passed": bool(rc.get("passed")),
                    "tally": f"{rc.get('yea')}-{rc.get('nay')}",
                    "keyword": hit.group(1),
                    "url": bill.get("state_link") or bill.get("url"),
                })

    for recs in results.values():
        recs.sort(key=lambda r: r["date"] or "", reverse=True)

    OUT.write_text(json.dumps({
        "source": "LegiScan (CC BY 4.0) - https://legiscan.com",
        "generated": datetime.now().isoformat(timespec="seconds"),
        "sessions": [d["session_name"] for d in sessions],
        "officials": results,
    }, indent=2))

    print("\nPeople matched (check these are the right lawmakers):")
    for k, v in matched_people.items():
        print(f"  {k}  ->  {v}")
    print("\nVotes on keyword bills:")
    for who, recs in results.items():
        nays = sum(1 for r in recs if r["vote"] == "Nay")
        print(f"  {who}: {len(recs)} votes ({nays} Nay)")
    print(f"\nSaved {OUT}")


if __name__ == "__main__":
    main()
