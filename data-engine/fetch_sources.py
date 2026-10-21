#!/usr/bin/env python3
"""
FETCH SOURCES - downloads the bulk government files the Grid is built from,
so the nightly job no longer depends on files sitting on the Chromebook.

  TEC   campaign finance bulk CSV  -> data-engine/TEC_CF_CSV.zip
  TWDB  groundwater database       -> GWDBDownload.zip
  ERCOT GIS interconnection report -> P2A/east_texas_interconnections.json

Each source is independent. If one fails, the old file stays in place,
the others still run, and feed_guard.py keeps the last good data on the site.
Run from the repo folder:  python3 data-engine/fetch_sources.py
"""
import io, json, os, sys, time, urllib.request

UA = {'User-Agent': 'ETLC-AquiferGrid/1.0 (grailsystems.io; contact@grailsystems.io)'}
TEC_URL = 'https://prd.tecprd.ethicsefile.com/public/cf/public/TEC_CF_CSV.zip'
TWDB_URL = 'https://www.twdb.texas.gov/groundwater/data/GWDBDownload.zip'
ERCOT_LIST = 'https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId=15933'
ERCOT_DOC = 'https://www.ercot.com/misdownload/servlets/mirDownload?doclookupId={}'
ERCOT_OUT = 'P2A/east_texas_interconnections.json'
ERCOT_COUNTIES = ['angelina', 'nacogdoches', 'anderson', 'henderson',
                  'cherokee', 'rusk', 'navarro', 'houston', 'smith']
failures = []


def download(url, dest, min_bytes):
    """Download to a temp file and only replace dest if the result looks real."""
    tmp = dest + '.part'
    t0 = time.time()
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=1800) as r, open(tmp, 'wb') as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
    size = os.path.getsize(tmp)
    if size < min_bytes:
        os.remove(tmp)
        raise RuntimeError(f'only {size:,} bytes came back (expected at least {min_bytes:,})')
    with open(tmp, 'rb') as f:
        if f.read(2) != b'PK':
            os.remove(tmp)
            raise RuntimeError('file is not a zip (the source may have returned an error page)')
    os.replace(tmp, dest)
    print(f'[FETCH] {dest}: {size / 1e6:,.1f} MB in {time.time() - t0:.0f}s')


def fetch_tec():
    download(TEC_URL, 'data-engine/TEC_CF_CSV.zip', 10_000_000)


def fetch_twdb():
    download(TWDB_URL, 'GWDBDownload.zip', 5_000_000)


def _find_header(raw):
    """Find the header row by its content instead of a fixed row number."""
    for i in range(min(len(raw), 80)):
        cells = [str(c).strip().lower() for c in raw.iloc[i].tolist()]
        if 'county' in cells and any('inr' in c for c in cells):
            return i
    return None


def parse_ercot(xlsx_bytes):
    import pandas as pd
    book = pd.ExcelFile(io.BytesIO(xlsx_bytes))
    sheet = next((s for s in book.sheet_names if 'large gen' in s.lower()), None)
    if not sheet:
        raise RuntimeError(f'no "Large Gen" sheet; sheets are {book.sheet_names}')
    raw = book.parse(sheet, header=None)
    h = _find_header(raw)
    if h is None:
        raise RuntimeError(f'no header row with "County" and "INR" in sheet {sheet!r}')
    df = raw.iloc[h + 1:].copy()
    df.columns = [str(c).strip().lower().replace(' ', '_').replace('\n', '_') for c in raw.iloc[h]]
    df = df[df['county'].fillna('').astype(str).str.strip().str.lower().isin(ERCOT_COUNTIES)]
    df = df.dropna(how='all', axis=1)
    print(f'[ERCOT] sheet {sheet!r}, header found on row {h + 1}, {len(df)} East Texas projects')
    return json.loads(df.to_json(orient='records', date_format='iso'))


def fetch_ercot():
    req = urllib.request.Request(ERCOT_LIST, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r:
        docs = json.load(r)['ListDocsByRptTypeRes']['DocumentList']
    xlsx = [d['Document'] for d in docs
            if str(d['Document'].get('ConstructedName', '')).lower().endswith('.xlsx')]
    if not xlsx:
        raise RuntimeError('ERCOT list has no .xlsx GIS report')
    latest = max(xlsx, key=lambda d: d.get('PublishDate', ''))
    print(f"[ERCOT] latest report: {latest.get('ConstructedName')} ({latest.get('PublishDate', '')[:10]})")
    req = urllib.request.Request(ERCOT_DOC.format(latest['DocID']), headers=UA)
    with urllib.request.urlopen(req, timeout=600) as r:
        data = r.read()
    rows = parse_ercot(data)
    if not rows:
        raise RuntimeError('parsed 0 East Texas projects')
    os.makedirs('P2A', exist_ok=True)
    json.dump(rows, open(ERCOT_OUT, 'w'), indent=2)
    print(f'[FETCH] {ERCOT_OUT}: {len(rows)} projects')


if __name__ == '__main__':
    for name, fn in [('TEC campaign finance', fetch_tec),
                     ('TWDB groundwater', fetch_twdb),
                     ('ERCOT GIS report', fetch_ercot)]:
        try:
            fn()
        except Exception as e:
            failures.append(name)
            print(f'[FETCH FAILED] {name}: {e}. Keeping the previous file.')
    if failures:
        print(f"[FETCH] Done with failures: {', '.join(failures)}")
    else:
        print('[FETCH] All three sources downloaded.')
    sys.exit(0)   # never block the run; feed_guard decides what gets published
