import zipfile, csv, io, re, os, sys, time, json

# ============================================================
# BULK MINER v2 - finds columns by NAME, not position.
# If the state renames or reorders headers, it adapts.
# If a header is missing entirely, it stops and tells you.
# ============================================================

ZIP_PATH   = 'data-engine/TEC_CF_CSV.zip'
OUT_PATH   = 'data-engine/tec_pac_data.csv'
REPORT     = 'data-engine/miner_report.json'
MIN_YEAR   = 2018      # ignore anything older
MIN_AMOUNT = 100       # ignore tiny donations
MAX_ROWS   = 300       # cap for the web page

# Every name the state has used (or might use) for each field.
# When a new variation shows up, add it to the list. That's it.
FIELDS = {
    'recipient':  ['filerName', 'filer_name', 'recipientName'],
    'date':       ['contributionDt', 'contribution_date', 'contribDt'],
    'amount':     ['contributionAmount', 'contribution_amount', 'contribAmount'],
    'org':        ['contributorNameOrganization', 'contributor_org', 'contributorOrganization'],
    'last':       ['contributorNameLast', 'contributor_last'],
    'first':      ['contributorNameFirst', 'contributor_first'],
    'city':       ['contributorStreetCity', 'contributor_city', 'contributorCity'],
    'employer':   ['contributorEmployer', 'contributor_employer'],
    'occupation': ['contributorOccupation', 'contributor_occupation'],
}
REQUIRED = ['recipient', 'date', 'amount']

# OFFICIALS WE TRACK: any donation TO them is pulled, no matter where the donor lives.
# Add names here as needed (match how TEC lists them: "Last, First").
TARGET_OFFICIALS = ['ASHBY, TRENT', 'NICHOLS, ROBERT', 'THIGPEN, ALAN', 'CLARDY, TRAVIS']  # 'Last, First' as TEC lists them

GEO_CITIES = {'LUFKIN','NACOGDOCHES','DIBOLL','ZAVALLA','HUDSON','HUNTINGTON',
              'CENTER','TIMPSON','TENAHA','JOAQUIN','GARRISON','CUSHING',
              'APPLEBY','CHIRENO','SAN AUGUSTINE','JACKSONVILLE','RUSK','PALESTINE'}

THREAT_WORDS = ['AQUIFER','GCD','INFRASTRUCTURE','OIL','GAS','ELECTRIC','TRANSMISSION','PIPELINE','WATER','GROUNDWATER','CARRIZO','WILCOX','DATA CENTER',
                'CLOUD','ARTIFICIAL INTELLIGENCE','SERVER','ENERGY','POWER',
                'UTILITY','TIMBER','AGGREGATE','PIPELINE','MINING','CRYPTO','BITCOIN']
THREAT_RE = re.compile(r'\b(' + '|'.join(re.escape(w) for w in THREAT_WORDS) + r')\b')

def norm(s):
    return re.sub(r'[^a-z0-9]', '', s.lower())

def map_headers(headers):
    lookup = {norm(h): i for i, h in enumerate(headers)}
    found, missing = {}, []
    for field, aliases in FIELDS.items():
        idx = next((lookup[norm(a)] for a in aliases if norm(a) in lookup), None)
        if idx is None:
            missing.append(field)
        else:
            found[field] = idx
    return found, missing

def parse_date(raw):
    digits = re.sub(r'\D', '', raw or '')
    if len(digits) >= 8:
        return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}", int(digits[:4])
    return None, None

def main():
    t0 = time.time()
    if not os.path.exists(ZIP_PATH):
        sys.exit(f"[ERROR] {ZIP_PATH} not found. Download the TEC bulk CSV zip into data-engine/.")

    hits, seen = [], set()
    report = {'files_scanned': [], 'files_skipped': [], 'rows_scanned': 0}

    with zipfile.ZipFile(ZIP_PATH) as z:
        # Only CONTRIBUTION files. The old miner read every file in the
        # zip with the same column numbers - that was the main bug.
        names = [n for n in z.namelist() if n.lower().endswith('.csv') and 'contrib' in n.lower()]
        if not names:
            sys.exit("[ERROR] No contribution files in the zip. The state may have renamed them - check z.namelist().")

        for name in names:
            with z.open(name) as f:
                reader = csv.reader(io.TextIOWrapper(f, encoding='utf-8', errors='ignore'))
                try:
                    headers = next(reader)
                except StopIteration:
                    continue
                cols, missing = map_headers(headers)
                if any(m in REQUIRED for m in missing):
                    print(f"[FLAG] {name}: unknown headers, skipped. Missing: {missing}")
                    report['files_skipped'].append({'file': name, 'missing': missing, 'headers': headers})
                    continue
                report['files_scanned'].append(name)

                def get(row, field):
                    i = cols.get(field)
                    return row[i].strip() if i is not None and i < len(row) else ''

                for row in reader:
                    report['rows_scanned'] += 1
                    city = get(row, 'city').upper()
                    recipient_up = get(row, 'recipient').upper()
                    is_target = any(recipient_up.startswith(o) for o in TARGET_OFFICIALS)
                    profile = ' '.join([get(row,'org'), get(row,'employer'), get(row,'occupation')]).upper()
                    m = THREAT_RE.search(profile)
                    # Keep if: donation to a tracked official from a threat industry (from ANYWHERE),
                    # or a local donor from a threat industry (old behavior).
                    if not m or not (is_target or city in GEO_CITIES):
                        continue
                    if 'ACTBLUE' in recipient_up or 'WINRED' in recipient_up:
                        continue  # pass-throughs double-count
                    date, year = parse_date(get(row, 'date'))
                    if not year or year < MIN_YEAR:
                        continue
                    try:
                        amount = float(get(row, 'amount').replace('$','').replace(',',''))
                    except ValueError:
                        continue
                    if amount < MIN_AMOUNT:
                        continue
                    donor = get(row,'org') or f"{get(row,'first')} {get(row,'last')}".strip() or 'Unnamed contributor'
                    recipient = get(row, 'recipient')
                    key = (donor.upper(), recipient.upper(), date, amount)
                    if key in seen:
                        continue
                    seen.add(key)
                    hits.append({'Filer_Name': donor, 'Recipient_Name': recipient,
                                 'Amount': f"{amount:.2f}", 'Date': date,
                                 'PAC_Industry': m.group(1).title(),
                                 'Donor_City': city.title(), 'Tracked_Official': 'YES' if is_target else '', 'Source_File': name})

    hits.sort(key=lambda r: (r['Tracked_Official']=='YES', float(r['Amount'])), reverse=True)
    with open(OUT_PATH, 'w', newline='', encoding='utf-8') as out:
        w = csv.DictWriter(out, fieldnames=list(hits[0].keys()) if hits else
                           ['Filer_Name','Recipient_Name','Amount','Date','PAC_Industry','Donor_City','Tracked_Official','Source_File'])
        w.writeheader()
        w.writerows(hits[:MAX_ROWS])

    report['matches'] = len(hits)
    with open(REPORT, 'w') as r:
        json.dump(report, r, indent=2)

    print(f"[REPORT] Scanned {report['rows_scanned']:,} rows in {len(report['files_scanned'])} files.")
    print(f"[SUCCESS] {len(hits)} matches since {MIN_YEAR}. Top {min(len(hits),MAX_ROWS)} written to {OUT_PATH}")
    if report['files_skipped']:
        print(f"[ATTENTION] {len(report['files_skipped'])} file(s) had unknown headers. See {REPORT}.")
    print(f"Done in {time.time()-t0:.1f}s. Next: python3 data-engine/omni_gateway.py")

if __name__ == '__main__':
    main()
