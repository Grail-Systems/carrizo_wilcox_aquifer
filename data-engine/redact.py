"""Redaction tool for the records library. Originals stay OUTSIDE the repo; only redacted copies get published.

  python3 data-engine/redact.py scan   ORIGINAL.pdf          find every phone, email and street address
  python3 data-engine/redact.py review ORIGINAL.pdf          list the items you need to decide, numbered
  python3 data-engine/redact.py mark   ORIGINAL.pdf KEEP 3 5 9      (or REDACT 3 5 9, or KEEP rest)
  python3 data-engine/redact.py apply  ORIGINAL.pdf OUTPUT.pdf     black out, strip hidden text and metadata, re-check

Scanned pages (pictures of paper) are read with OCR automatically when tesseract is installed."""
import sys, os, re, csv, glob, pymupdf

GOV = re.compile(r"@([a-z0-9-]+\.)*(gov|us|edu|mil|angelinacounty\.net|cityoflufkin\.com|lufkintexas\.gov|pineywoodsgcd\.org|lufkinedc\.org)$", re.I)
FREEMAIL = re.compile(r"@(gmail|yahoo|ymail|hotmail|outlook|live|msn|aol|icloud|me|mac|att|sbcglobal|suddenlink|comcast|charter|proton|protonmail|windstream|consolidated)\.", re.I)
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE = re.compile(r"(?<!\d)(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}(?!\d)")
ADDR = re.compile(r"\b\d{2,6}\s+(?:[NSEW]\.?\s+)?[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,3}\s+(?:Rd|Road|St|Street|Dr|Drive|Ln|Lane|Ave|Avenue|Blvd|Ct|Court|Cir|Circle|Trl|Trail|Way|Hwy|Highway|Pkwy|Loop)\b\.?")
ALWAYS = ["3345245918"]   # known private numbers, always redacted (digits only)
TESS = (glob.glob("/usr/share/tesseract-ocr/*/tessdata") or [None])[0]
FIELDS = ["n", "decision", "pages", "type", "match", "context"]
digits = lambda s: re.sub(r"\D", "", s)

def is_scanned(page): return len(page.get_text().strip()) < 25 and bool(page.get_images())
def textpage(page):
    if is_scanned(page) and TESS:
        return page.get_textpage_ocr(dpi=200, full=True, tessdata=TESS)
    return page.get_textpage()
def sheet(pdf):
    os.makedirs("redaction_review", exist_ok=True)
    return os.path.join("redaction_review", os.path.splitext(os.path.basename(pdf))[0] + ".review.tsv")
def load(pdf): return list(csv.DictReader(open(sheet(pdf)), delimiter="\t"))
def save(pdf, rows):
    with open(sheet(pdf), "w", newline="") as f:
        w = csv.DictWriter(f, FIELDS, delimiter="\t", lineterminator="\n"); w.writeheader(); w.writerows(rows)

def scan(pdf):
    doc = pymupdf.open(pdf); rows, idx, ocr_pages, blind = [], {}, [], []
    for i, page in enumerate(doc, 1):
        if i % 25 == 0: print(f"  ...page {i} of {len(doc)}", flush=True)
        if is_scanned(page):
            if TESS: ocr_pages.append(i)
            else: blind.append(i); continue
        flat = " ".join(page.get_text(textpage=textpage(page)).split())
        for kind, rx in (("email", EMAIL), ("phone", PHONE), ("address", ADDR)):
            for m in rx.finditer(flat):
                s = m.group(0).strip()
                if kind == "phone" and len(digits(s)) not in (10, 11): continue
                if kind == "email": d = "KEEP" if GOV.search(s) else "REDACT" if FREEMAIL.search(s) else "REVIEW"
                elif kind == "phone": d = "REDACT"
                else: d = "REVIEW"
                if kind == "phone" and digits(s)[-10:] in ALWAYS: d = "REDACT"
                key = (kind, s.lower())
                if key in idx:
                    r = idx[key]
                    if str(i) not in r["pages"].split(","): r["pages"] += f",{i}"
                    continue
                r = {"n": str(len(rows) + 1), "decision": d, "pages": str(i), "type": kind, "match": s,
                     "context": flat[max(0, m.start() - 60):m.end() + 60].replace("\t", " ")}
                idx[key] = r; rows.append(r)
    save(pdf, rows)
    c = lambda k: sum(1 for r in rows if r["decision"] == k)
    print(f"{os.path.basename(pdf)}: {len(doc)} pages ({len(ocr_pages)} read with OCR)")
    print(f"  REDACT {c('REDACT')}   personal emails and all phone numbers")
    print(f"  KEEP   {c('KEEP')}   government emails")
    print(f"  REVIEW {c('REVIEW')}   company emails and street addresses: you decide")
    if blind: print(f"  NOT READ (scanned, tesseract not installed): {len(blind)} pages. Run: sudo apt-get install -y tesseract-ocr")
    print(f"  Next: python3 {sys.argv[0]} review \"{pdf}\"")

def review(pdf):
    rows = [r for r in load(pdf) if r["decision"] == "REVIEW"]
    if not rows: print("Nothing left to review. Next: apply"); return
    for r in rows: print(f"#{r['n']}  {r['type']}: {r['match']}  (p. {r['pages'][:30]})\n     ...{r['context']}...")
    print(f"\n{len(rows)} to decide. Paste this list to Claude, or mark them yourself with: mark FILE REDACT 3 5, then mark FILE KEEP rest")

def mark(pdf, decision, which):
    rows = load(pdf); decision = decision.upper(); assert decision in ("KEEP", "REDACT")
    for r in rows:
        if (which == ["rest"] and r["decision"] == "REVIEW") or r["n"] in which: r["decision"] = decision
    save(pdf, rows); print(f"Marked {decision}. Still to review: {sum(1 for r in rows if r['decision'] == 'REVIEW')}")

def apply(pdf, out):
    rows = load(pdf); todo = [r for r in rows if r["decision"] == "REDACT"]
    left = [r for r in rows if r["decision"] == "REVIEW"]
    if left: print(f"Stopped: {len(left)} items still marked REVIEW. Run: review {pdf}"); sys.exit(1)
    if os.path.abspath(out) == os.path.abspath(pdf): print("Output must be a new file, not the original."); sys.exit(1)
    doc = pymupdf.open(pdf); hits, missed, tps, pg = 0, [], {}, {}
    for r in todo:
        found = False
        for pno in [int(x) for x in r["pages"].split(",")]:
            page = pg.setdefault(pno, doc[pno - 1])
            if pno not in tps: tps[pno] = textpage(page)
            tp = tps[pno]
            vs = {r["match"], r["match"].replace(" ", "")}
            if r["type"] == "email" and "@" in r["match"]:
                u, d = r["match"].split("@", 1); vs.add(u + "@" + d.split(".")[0])
            for v in vs:
                for q in page.search_for(v, textpage=tp):
                    page.add_redact_annot(q + (-3, -3, 3, 3), fill=(0, 0, 0)); hits += 1; found = True
        if not found: missed.append(f"{r['match']} (p. {r['pages']})")
    for page in pg.values(): page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_PIXELS)
    tps.clear()
    doc.set_metadata({}); doc.del_xml_metadata()
    doc.save(out, garbage=4, deflate=True, clean=True)
    chk = pymupdf.open(out); pages = sorted(pg)
    def read(p):
        pp = chk[p - 1]; return " ".join(pp.get_text(textpage=textpage(pp)).split())
    ptext = {p: read(p).lower() for p in pages}
    for i, p in enumerate(chk, 1): ptext[i] = ptext.get(i, "") + " " + " ".join(p.get_text().split()).lower()
    still = [f"{r['match']} (p. {','.join(str(i) for i, t in ptext.items() if r['match'].lower() in t)})" for r in todo if any(r["match"].lower() in t for t in ptext.values())]
    print(f"Blacked out {hits} spots for {len(todo)} items. Saved {out}")
    if missed: print("  Could not place a box on these (odd spacing or OCR misread). Check those pages by eye:\n   " + "\n   ".join(missed))
    if still: print(f"  WARNING, still readable in the output: {still}"); sys.exit(1)
    print("  Verified: nothing marked REDACT is readable in the output.")

def add(pdf, pages, text):
    rows = load(pdf)
    rows.append({"n": str(len(rows) + 1), "decision": "REDACT", "pages": pages, "type": "manual", "match": text, "context": "added by hand"})
    save(pdf, rows); print(f"Added: {text} on p. {pages}")

if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) == 2 and a[0] == "scan": scan(a[1])
    elif len(a) == 2 and a[0] == "review": review(a[1])
    elif len(a) >= 4 and a[0] == "mark": mark(a[1], a[2], a[3:])
    elif len(a) == 3 and a[0] == "apply": apply(a[1], a[2])
    elif len(a) == 4 and a[0] == "add": add(a[1], a[2], a[3])
    else: print(__doc__)
