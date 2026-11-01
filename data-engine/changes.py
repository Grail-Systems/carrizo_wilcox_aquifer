"""What changed since last night: new projects, status changes, new ERCOT grid requests, new records,
new hearing dates and new Comptroller tax-break records. Writes frontend/changes.json for the county
pages, the /updates page, and (once the sign-up form exists) county alerts. First run only records a baseline."""
import json, re, os, datetime, urllib.request
W = "https://raw.githubusercontent.com/Grail-Systems/Grail-Systems.github.io/main/data/"
SNAP, OUT = "frontend/watch_snapshot.json", "frontend/changes.json"
ST = {"announced": "announced or reported", "filed": "filed with a government", "approved": "approved by a government",
      "construction": "under construction", "operating": "operating", "stopped": "withdrawn or stopped"}
get = lambda u: json.load(urllib.request.urlopen(u, timeout=60))
cty = lambda c: re.sub(r"\s*\(.*\)\s*", "", c).strip()
slug = lambda n: re.sub(r"^-|-$", "", re.sub(r"[^a-z0-9]+", "-", n.lower()))
plain = lambda h: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h or "")).strip()
P, D, E = get(W + "projects.json"), get(W + "details.json"), get(W + "events.json")
pc = {p["name"]: cty(p["county"]) for p in P}
now = {}
for p in P:
    now["p:" + p["name"]] = {"kind": "project", "name": p["name"], "county": [pc[p["name"]]], "status": p["status"],
                             "comp": bool(D.get(p["name"], {}).get("comp"))}
for e in E:
    cs = sorted({pc[n] for n in e.get("projects", []) if n in pc})
    now["e:" + e["date"] + " " + e["what"]] = {"kind": "event", "name": e["what"], "date": e["date"], "county": cs, "where": e.get("where", "")}
for g in json.load(open("frontend/mega_permits.json")):
    if not g["title"].startswith("ERCOT"): continue
    m = re.search(r"in ([A-Z][A-Za-z .]+?) County", plain(g["bottom_line"]))
    now["g:" + g["title"] + "|" + g.get("applicant", "")] = {"kind": "grid", "name": g["title"].replace("ERCOT grid request: ", ""),
        "county": [m.group(1)] if m else [], "detail": plain(g["bottom_line"]).split(". Location")[0], "link": g.get("source_url", "")}
for d in json.load(open("frontend/library.json"))["documents"]:
    county = ["Angelina"] if (d.get("request") or "").startswith(("CRR", "ANGELINA", "PINEYWOODS")) else []
    now["d:" + d["sha256"]] = {"kind": "doc", "name": d["title"], "county": county, "link": d["url"]}
today = datetime.date.today().isoformat()
log = json.load(open(OUT)) if os.path.exists(OUT) else {"since": today, "changes": []}
if not os.path.exists(SNAP):
    json.dump(now, open(SNAP, "w"), ensure_ascii=False); json.dump(log, open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"Baseline recorded: {len(now)} items. Changes will be logged from the next run."); raise SystemExit
old, new = json.load(open(SNAP)), []
for k, v in now.items():
    o, n = old.get(k), v["name"]
    if v["kind"] == "project":
        link = "/texas#" + slug(n)
        if not o: new.append({"county": v["county"], "text": f"Added to the map: {n} ({v['county'][0]} County), {ST.get(v['status'], v['status'])}.", "link": link})
        else:
            if o["status"] != v["status"]: new.append({"county": v["county"], "text": f"{n}: status changed from {ST.get(o['status'], o['status'])} to {ST.get(v['status'], v['status'])}.", "link": link})
            if v["comp"] and not o.get("comp"): new.append({"county": v["county"], "text": f"{n} now has a Texas Comptroller tax-break record.", "link": link})
    elif not o:
        if v["kind"] == "event": new.append({"county": v["county"], "text": f"New date: {n}, {v['date']}{', ' + v['where'] if v['where'] else ''}.", "link": "/texas"})
        if v["kind"] == "grid": new.append({"county": v["county"], "text": f"New ERCOT grid request: {n}. {v['detail']}.", "link": v["link"]})
        if v["kind"] == "doc": new.append({"county": v["county"], "text": f"New in the records library: {n}.", "link": v["link"]})
for c in new: c["date"] = today
log["changes"] = (new + log["changes"])[:300]; log["updated"] = today
json.dump(log, open(OUT, "w"), ensure_ascii=False, indent=1); json.dump(now, open(SNAP, "w"), ensure_ascii=False)
print(f"{len(new)} changes logged tonight; {len(log['changes'])} in the log.")
for c in new: print("  -", ", ".join(c["county"]) or "Statewide", "|", c["text"][:110])
