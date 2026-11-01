"""Build frontend/library.json: every PDF in records/ and docs/, with searchable text and topic tags.
Full text for each document goes to frontend/library_full/ so search covers every page.
Skips sign-in sheets (private residents' contact info) unless INCLUDE_SIGNIN=1."""
import os, re, json, hashlib, subprocess, datetime
BASE = "https://grailsystems.io/carrizo_wilcox_aquifer/"
TITLES = {
 "2026-10-28_city-of-lufkin-water-records.pdf": "City of Lufkin water system records (CRR-2026-316 release)",
 "2026-10-02_angelina-county-data-center-records.pdf": "Angelina County data center records (County's open records release)",
 "2026-02-23_pz-minutes.pdf": "Lufkin Planning & Zoning Commission minutes",
 "2026-02-23_pz-agenda-packet.pdf": "Lufkin Planning & Zoning agenda packet",
 "2026-02-18_pz-agenda-email-draft-minutes-bylaws.pdf": "P&Z agenda email, draft minutes and bylaws",
 "2026-02-09_data-center-faq-email-to-pz.pdf": "City's data center FAQ email to P&Z members",
 "2024-08-05_board-meeting-agenda.pdf": "Pineywoods GCD board meeting agenda",
 "2024-08-05_board-meeting-minutes.pdf": "Pineywoods GCD board meeting minutes",
 "2025-02-10_board-meeting-agenda.pdf": "Pineywoods GCD board meeting agenda",
 "2025-02-10_board-meeting-minutes.pdf": "Pineywoods GCD board meeting minutes",
 "etlc_comment_amendment1_2026-09-22.pdf": "ETLC comment on 2027 State Water Plan Amendment No. 1",
 "lufkin_ag_request_2026-10-09.pdf": "City of Lufkin's letter asking the Attorney General to withhold records",
 "lufkin_utility_rate_study_2018.pdf": "City of Lufkin utility rate study (2018)",
 "tceq_2024-0641-mwd-e.pdf": "TCEQ enforcement docket 2024-0641-MWD-E",
}
TAGS = {  # tag: (kind, pattern, minimum count)
 "Amp Z": ("Company", r"\bamp ?z\b", 1), "HyperDataGrid": ("Company", r"hyper ?data ?grid", 1),
 "WattBridge / Longleaf": ("Company", r"wattbridge|longleaf", 1), "EPG Champion": ("Company", r"epg ?(champion|industry)", 1),
 "Verdant Industries": ("Company", r"\bverdant\b", 1), "Abitibi": ("Company", r"abitibi", 1), "1606 Corp": ("Company", r"\b1606 corp", 1),
 "City of Lufkin": ("Agency", r"city of lufkin", 2), "Angelina County": ("Agency", r"angelina county", 2),
 "Pineywoods GCD": ("Agency", r"pineywoods", 2), "TCEQ": ("Agency", r"\btceq\b|commission on environmental quality", 2),
 "Attorney General": ("Agency", r"attorney general", 2), "TWDB": ("Agency", r"\btwdb\b|water development board", 2), "ERCOT": ("Agency", r"\bercot\b", 1),
 "Water": ("Topic", r"\bwater\b", 5), "Wells": ("Topic", r"\bwells\b|water well|well permit", 2),
 "Tax breaks": ("Topic", r"abatement|chapter 312|chapter 38[01]|payment in lieu|\bpilot\b", 1),
 "Roads": ("Topic", r"road[- ]use|road agreement|road repair", 1), "Power": ("Topic", r"megawatt|\bmw\b|power plant|substation|\bercot\b", 3),
 "Wastewater": ("Topic", r"wastewater|\bsewer", 3), "Zoning": ("Topic", r"\bzoning\b|rezon", 2), "Meetings": ("Topic", r"\bminutes\b|\bagenda\b", 3),
}
def tags_for(text, request):
    t = text.lower(); out = []
    for tag, (kind, pat, n) in TAGS.items():
        if len(re.findall(pat, t)) >= n: out.append([kind, tag])
    if request and request.startswith("CRR") and ["Agency", "City of Lufkin"] not in out: out.append(["Agency", "City of Lufkin"])
    if request == "ANGELINA-COUNTY" and ["Agency", "Angelina County"] not in out: out.append(["Agency", "Angelina County"])
    if request == "PINEYWOODS-GCD" and ["Agency", "Pineywoods GCD"] not in out: out.append(["Agency", "Pineywoods GCD"])
    return out
def text_of(path):
    if os.path.exists(path + ".txt"):  # sidecar OCR text for scanned records
        return open(path + ".txt").read()
    try: return subprocess.run(["pdftotext", "-q", path, "-"], capture_output=True, text=True, timeout=120).stdout
    except Exception: return ""
def pages_of(path):
    try:
        out = subprocess.run(["pdfinfo", path], capture_output=True, text=True, timeout=30).stdout
        m = re.search(r"Pages:\s+(\d+)", out); return int(m.group(1)) if m else None
    except Exception: return None
os.makedirs("frontend/library_full", exist_ok=True)
docs, skipped = [], []
for root in ("records", "docs"):
    for dirpath, _, files in os.walk(root):
        for f in sorted(files):
            if not f.lower().endswith(".pdf"): continue
            path = os.path.join(dirpath, f)
            if "sign-in" in f.lower() and os.environ.get("INCLUDE_SIGNIN") != "1":
                skipped.append(path); continue
            m = re.match(r"(\d{4}-\d{2}-\d{2})[_-]?(.*)\.pdf$", f, re.I)
            date, stem = (m.group(1), m.group(2)) if m else (None, f[:-4])
            m2 = re.search(r"(\d{4}-\d{2}-\d{2})", f)
            if not date and m2: date = m2.group(1)
            title = TITLES.get(f) or (lambda x: x[:1].upper() + x[1:])(re.sub(r"[_-]+", " ", stem).strip())
            parts = dirpath.split(os.sep)
            request = parts[1].upper() if root == "records" and len(parts) > 1 else None
            t = re.sub(r"\s+", " ", text_of(path)).strip()
            sha = hashlib.sha256(open(path, "rb").read()).hexdigest()
            full = f"library_full/{sha[:16]}.txt"
            open("frontend/" + full, "w").write(t)
            docs.append({"title": title, "date": date, "request": request, "collection": root,
                         "url": BASE + path.replace(os.sep, "/"), "pages": pages_of(path),
                         "bytes": os.path.getsize(path), "sha256": sha,
                         "searchable": bool(t), "text": t[:30000], "full": full, "tags": tags_for(t, request)})
keep = {os.path.basename(d["full"]) for d in docs}
for f in os.listdir("frontend/library_full"):
    if f not in keep: os.remove("frontend/library_full/" + f)
docs.sort(key=lambda d: (d["date"] or "0000"), reverse=True)
json.dump({"updated": datetime.date.today().isoformat(), "documents": docs}, open("frontend/library.json", "w"), ensure_ascii=False)
print(f"Library: {len(docs)} documents ({sum(d['searchable'] for d in docs)} searchable, {sum(len(d['tags']) for d in docs)} tags). Skipped: {len(skipped)}")
for s in skipped: print("  skipped (privacy):", s)
