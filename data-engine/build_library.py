"""Build frontend/library.json: every PDF in records/ and docs/, with searchable text.
Skips sign-in sheets (private residents' contact info) unless INCLUDE_SIGNIN=1."""
import os, re, json, hashlib, subprocess, datetime
BASE = "https://grailsystems.io/carrizo_wilcox_aquifer/"
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
            title = re.sub(r"[_-]+", " ", stem).strip()
            title = title[:1].upper() + title[1:]
            parts = dirpath.split(os.sep)
            request = parts[1].upper() if root == "records" and len(parts) > 1 else None
            t = re.sub(r"\s+", " ", text_of(path)).strip()
            docs.append({"title": title, "date": date, "request": request, "collection": root,
                         "url": BASE + path.replace(os.sep, "/"), "pages": pages_of(path),
                         "bytes": os.path.getsize(path),
                         "sha256": hashlib.sha256(open(path, "rb").read()).hexdigest(),
                         "searchable": bool(t), "text": t[:30000]})
docs.sort(key=lambda d: (d["date"] or "0000"), reverse=True)
json.dump({"updated": datetime.date.today().isoformat(), "documents": docs}, open("frontend/library.json", "w"), ensure_ascii=False)
print(f"Library: {len(docs)} documents ({sum(d['searchable'] for d in docs)} searchable). Skipped: {len(skipped)}")
for s in skipped: print("  skipped (privacy):", s)
