import asyncio
import aiohttp
import json
import csv
import os
import time

print("[INIT] Booting Asynchronous Omni-Gateway...")
start_time = time.time()

os.makedirs('frontend', exist_ok=True)

# ---------------------------------------------------------
# AQUIFER OUTLINE CHECK (keeps USGS sites inside the Carrizo-Wilcox)
# ---------------------------------------------------------
def _load_rings():
    try:
        with open('frontend/wilcox_aquifer.json') as f:
            gj = json.load(f)
    except Exception:
        return None
    rings = []
    feats = gj.get('features', [gj]) if isinstance(gj, dict) else []
    for ft in feats:
        g = ft.get('geometry', ft) or {}
        if g.get('type') == 'Polygon':
            rings.append(g['coordinates'][0])
        elif g.get('type') == 'MultiPolygon':
            rings.extend(poly[0] for poly in g['coordinates'])
    return rings or None

AQUIFER_RINGS = _load_rings()

def _in_ring(x, y, ring):
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi:
            inside = not inside
        j = i
    return inside

def in_aquifer(lon, lat):
    if not AQUIFER_RINGS:
        return True  # no outline file: don't filter
    return any(_in_ring(lon, lat, r) for r in AQUIFER_RINGS)

# Approximate county centers, used when a record only gives a county.
COUNTY_CENTERS = {
    'ANGELINA': (-94.611, 31.255), 'NACOGDOCHES': (-94.616, 31.616), 'ANDERSON': (-95.653, 31.813),
    'HENDERSON': (-95.853, 32.212), 'CHEROKEE': (-95.165, 31.837), 'RUSK': (-94.762, 32.108),
    'NAVARRO': (-96.472, 32.047), 'HOUSTON': (-95.422, 31.318), 'SMITH': (-95.269, 32.375),
    'SHELBY': (-94.145, 31.792), 'SAN AUGUSTINE': (-94.168, 31.394), 'TRINITY': (-95.135, 31.089),
    'POLK': (-94.830, 30.793), 'TYLER': (-94.377, 30.771), 'JASPER': (-94.025, 30.744),
    'SABINE': (-93.852, 31.343), 'PANOLA': (-94.306, 32.162), 'GREGG': (-94.817, 32.480),
}
ECHO_COUNTIES = ['ANGELINA', 'NACOGDOCHES', 'SHELBY', 'SAN AUGUSTINE', 'CHEROKEE', 'RUSK',
                 'ANDERSON', 'HOUSTON', 'TRINITY', 'POLK', 'SABINE', 'SMITH', 'HENDERSON', 'PANOLA']

# ---------------------------------------------------------
# TWDB GROUNDWATER LEVELS (Carrizo-Wilcox wells, East Texas)
# Reads the TWDB Groundwater Database zip directly - no unzipping needed.
# ---------------------------------------------------------
import zipfile, io

TWDB_ZIP_PATHS = ['GWDBDownload.zip', os.path.expanduser('~/P2A/GWDBDownload.zip'),
                  os.path.expanduser('~/carrizo_wilcox_aquifer/GWDBDownload.zip')]
TWDB_MIN_YEAR = 2016   # only show wells measured in the last ~10 years

def _twdb_rows(zf, name):
    member = next((n for n in zf.namelist() if n.endswith('/' + name) or n == name), None)
    if not member:
        raise FileNotFoundError(name)
    with zf.open(member) as raw:
        text = io.TextIOWrapper(raw, encoding='utf-8', errors='replace')
        header = text.readline().rstrip('\r\n').split('|')
        for line in text:
            parts = line.rstrip('\r\n').split('|')
            if len(parts) >= len(header) - 2:
                yield dict(zip(header, parts))

def compile_twdb_levels():
    zpath = next((p for p in TWDB_ZIP_PATHS if os.path.exists(p)), None)
    if not zpath:
        return None
    print(f"[PROCESSING] Reading TWDB groundwater database ({zpath})...")
    counties = set(COUNTY_CENTERS)
    wells = {}
    with zipfile.ZipFile(zpath) as zf:
        for r in _twdb_rows(zf, 'WellMain.txt'):
            if 'CARRIZO' not in (r.get('Aquifer', '') + r.get('AquiferCodeDescription', '')).upper():
                continue
            if r.get('County', '').upper() not in counties:
                continue
            try:
                lat, lon = float(r['LatitudeDD']), float(r['LongitudeDD'])
            except (KeyError, ValueError):
                continue
            wells[r['StateWellNumber']] = {'county': r['County'], 'lat': lat, 'lon': lon,
                                           'use': r.get('WellUse', ''), 'depth': r.get('WellDepth', '')}
        print(f"[TWDB] {len(wells)} Carrizo-Wilcox wells on file in the target counties.")
        series = {}
        for r in _twdb_rows(zf, 'WaterLevelsMajor.txt'):
            w = r.get('StateWellNumber')
            if w not in wells or r.get('Status', '').strip() != 'Publishable':
                continue
            try:
                depth = float(r['DepthFromLSD'])
                year = int(r['MeasurementYear'])
            except (KeyError, ValueError):
                continue
            date = r.get('MeasurementDate') or str(year)
            series.setdefault(w, []).append((date, year, depth))

    out = []
    for w, pts in series.items():
        pts.sort()
        last_date, last_year, last_depth = pts[-1]
        if last_year < TWDB_MIN_YEAR:
            continue
        first_date, first_year, first_depth = pts[0]
        info = wells[w]
        change = last_depth - first_depth   # positive = water is deeper now (dropped)
        if first_year < last_year:
            trend = (f"Water level has dropped {change:.0f} ft since {first_year}." if change > 0.5 else
                     f"Water level has risen {-change:.0f} ft since {first_year}." if change < -0.5 else
                     f"Water level roughly unchanged since {first_year}.")
        else:
            trend = "Only one measurement on record."
        out.append({
            "title": f"TWDB WELL {w} ({info['county']} County)",
            "applicant": "Texas Water Development Board",
            "bottom_line": (f"Carrizo-Wilcox well{', ' + info['use'].lower() if info['use'] else ''}. "
                            f"Latest depth to water: <span style='color:#ffaa00; font-weight:bold;'>{last_depth:.0f} ft</span> "
                            f"(measured {str(last_date)[:10]}). {trend} {len(pts)} measurements on record."),
            "raw_volume": max(1000, int(last_depth * 75)),
            "drop_ft": round(change, 1),
            "coordinates": [info['lon'], info['lat']],
            "source_url": "https://www3.twdb.texas.gov/apps/reports/GWDB/WaterLevelsByWell",
            "state_well_number": w,
        })
    out.sort(key=lambda x: -x['drop_ft'])
    return out

# ---------------------------------------------------------
# TASK 1: ASYNC FEDERAL USGS TELEMETRY (With Pressure Relief Valve)
# ---------------------------------------------------------
async def fetch_usgs(session):
    try:
        twdb = await asyncio.to_thread(compile_twdb_levels)
    except Exception as e:
        print(f"[ERROR] TWDB read failed: {e}")
        twdb = None
    if twdb is not None:
        with open('frontend/usgs_telemetry.json', 'w') as f:
            json.dump(twdb, f, indent=4)
        dropped = sum(1 for t in twdb if t['drop_ft'] > 0.5)
        print(f"[SUCCESS] TWDB water levels: {len(twdb)} wells measured since {TWDB_MIN_YEAR}, "
              f"{dropped} show a drop since their first record.")
        return
    print("[NOTE] No GWDBDownload.zip found - falling back to USGS.")
    print("[UPLINK] Dialing Federal USGS Database...")
    url = "https://waterservices.usgs.gov/nwis/iv/?format=json&bBox=-96.600000,30.600000,-93.500000,33.000000&siteType=GW&siteStatus=active"
    try:
        async with session.get(url) as response:
            text = await response.text()
            raw_data = {} if "No sites" in text else json.loads(text)
            timeSeries = raw_data.get('value', {}).get('timeSeries', [])
        if not timeSeries:
            # East Texas has no live groundwater sensors. Use USGS field measurements
            # (depth to water, parameter 72019) from the modern Water Data API.
            print("[NOTE] No live USGS sensors in East Texas. Using USGS field measurements (last 3 years).")
            since = time.strftime('%Y-%m-%d', time.gmtime(time.time() - 3 * 365 * 86400))
            url2 = ("https://api.waterdata.usgs.gov/ogcapi/v1/collections/field-measurements/items"
                    f"?f=json&bbox=-96.6,30.6,-93.5,33.0&parameter_code=72019&datetime={since}/..&limit=5000")
            latest = {}
            pages = 0
            while url2 and pages < 10:
                async with session.get(url2, timeout=aiohttp.ClientTimeout(total=120)) as response:
                    page = await response.json(content_type=None)
                pages += 1
                for ft in page.get('features', []):
                    pr = ft.get('properties', {}) or {}
                    loc = pr.get('monitoring_location_id')
                    coords = (ft.get('geometry') or {}).get('coordinates')
                    if not loc or not coords:
                        continue
                    if loc not in latest or str(pr.get('time', '')) > str(latest[loc]['time']):
                        latest[loc] = {'time': pr.get('time', ''), 'value': pr.get('value'), 'coords': coords}
                url2 = next((l.get('href') for l in page.get('links', []) if l.get('rel') == 'next'), None)
                if not page.get('features'):
                    url2 = None
            # Repackage into the same shape the parser below expects
            timeSeries = [{
                'sourceInfo': {'siteName': f"{loc} (measured {str(v['time'])[:10]})",
                               'geoLocation': {'geogLocation': {'longitude': v['coords'][0], 'latitude': v['coords'][1]}}},
                'values': [{'value': [{'value': v['value']}]}] if v['value'] not in (None, '') else []
            } for loc, v in latest.items()]
        if True:
            live_threats = []
            
            for site in timeSeries:
                sourceInfo = site.get('sourceInfo', {})
                lat = sourceInfo.get('geoLocation', {}).get('geogLocation', {}).get('latitude')
                lon = sourceInfo.get('geoLocation', {}).get('geogLocation', {}).get('longitude')
                siteName = sourceInfo.get('siteName', 'UNKNOWN FEDERAL SITE')
                
                values = site.get('values', [])
                drawdown = 1000
                drawdown_text = "Data pending."
                
                if values and values[0].get('value'):
                    try:
                        drawdown_val = float(values[0]['value'][-1]['value'])
                        
                        # THE PRESSURE RELIEF VALVE: Ignore broken sensor blowouts
                        if drawdown_val < -10000 or drawdown_val > 5000:
                            continue 
                            
                        drawdown = max(1000, int(drawdown_val * 75))
                        drawdown_text = f"{drawdown_val} ft below surface."
                    except: pass
                
                if lat and lon and in_aquifer(lon, lat):
                    live_threats.append({
                        "title": f"USGS SITE: {siteName}",
                        "applicant": "USGS TELEMETRY",
                        "bottom_line": f"USGS groundwater reading.<br>Latest depth to water: <span style='color:#ffaa00; font-weight:bold;'>{drawdown_text}</span>",
                        "raw_volume": drawdown,
                        "coordinates": [lon, lat]
                    })
            
            with open('frontend/usgs_telemetry.json', 'w') as f:
                json.dump(live_threats, f, indent=4)
            print(f"[SUCCESS] USGS Telemetry secured: {len(live_threats)} targets.")
    except Exception as e:
        print(f"[ERROR] USGS Fetch failed: {e}")

# ---------------------------------------------------------
# TASK 2: PERMITS & GRID REQUESTS (sourced records only)
#   1) data-engine/permits_verified.json - records you enter by hand
#      from documents you hold. Entries without a source_url are skipped.
#   2) P2A/east_texas_interconnections.json - ERCOT GIS report output
#      from ercot_sweeper.py (county-level location).
# ---------------------------------------------------------
def _pick(row, *keys):
    norm = {k.lower().replace(' ', '_'): v for k, v in row.items()}
    for k in keys:
        for nk, v in norm.items():
            if k in nk and v not in (None, '', 'NaN'):
                return v
    return None

async def compile_permits():
    print("[PROCESSING] Compiling sourced permits and grid requests...")
    permits, skipped = [], 0

    try:
        with open('data-engine/permits_verified.json') as f:
            for p in json.load(f):
                if p.get('source_url') and p.get('coordinates') and p.get('title'):
                    permits.append(p)
                else:
                    skipped += 1
    except FileNotFoundError:
        with open('data-engine/permits_verified.json', 'w') as f:
            json.dump([], f)
        print("[NOTE] Created empty data-engine/permits_verified.json - add sourced records there.")
    except Exception as e:
        print(f"[ERROR] permits_verified.json unreadable: {e}")

    ercot_n = 0
    try:
        ercot_path = next((x for x in ['P2A/east_texas_interconnections.json',
                                       os.path.expanduser('~/P2A/east_texas_interconnections.json')]
                           if os.path.exists(x)), 'P2A/east_texas_interconnections.json')
        with open(ercot_path) as f:
            ercot = json.load(f)
        per_county = {}
        for row in ercot:
            county = str(_pick(row, 'county') or '').upper().strip()
            if county not in COUNTY_CENTERS:
                continue
            n = per_county.get(county, 0); per_county[county] = n + 1
            lon, lat = COUNTY_CENTERS[county]
            # fan projects out around the county center so they don't stack
            lon += 0.06 * ((n % 5) - 2); lat += 0.06 * ((n // 5) % 5 - 2)
            name = _pick(row, 'project_name', 'name') or 'Unnamed project'
            inr = _pick(row, 'inr')
            fuel = _pick(row, 'fuel', 'technology') or 'unknown fuel'
            mw = _pick(row, 'capacity', 'mw')
            try: mw = float(mw)
            except (TypeError, ValueError): mw = None
            entity = _pick(row, 'interconnecting_entity', 'developer', 'entity') or 'Not listed'
            cod = _pick(row, 'projected_cod', 'cod')
            permits.append({
                "title": f"ERCOT grid request: {name}",
                "applicant": str(entity),
                "bottom_line": (f"{fuel}, {mw:,.0f} MW" if mw else str(fuel))
                               + f" in {county.title()} County" + (f". Projected online: {str(cod)[:10]}" if cod else "")
                               + (f". ERCOT ID {inr}" if inr else "") + ". Location shown at county level.",
                "raw_volume": int(mw * 20) if mw else 1000,
                "coordinates": [round(lon, 4), round(lat, 4)],
                "source_url": "https://www.ercot.com/mp/data-products/data-product-details?id=PG7-200-ER",
            })
            ercot_n += 1
    except FileNotFoundError:
        print("[NOTE] No ERCOT file found in ~/P2A - run ercot_sweeper.py from your home folder first.")
    except Exception as e:
        print(f"[ERROR] ERCOT file unreadable: {e}")

    with open('frontend/mega_permits.json', 'w') as f:
        json.dump(permits, f, indent=4)
    print(f"[SUCCESS] Permits: {len(permits) - ercot_n} hand-verified, {ercot_n} ERCOT grid requests"
          + (f", {skipped} skipped (missing source)" if skipped else "") + ".")

# ---------------------------------------------------------
# TASK 3: EPA ECHO - facilities with recent violations
# Live from EPA's Enforcement and Compliance History Online.
# ---------------------------------------------------------
ECHO_BASE = "https://echodata.epa.gov/echo/echo_rest_services"

ECHO_WANTED = ['FacName', 'FacCity', 'FacCounty', 'RegistryID', 'FacLat', 'FacLong',
               'FacSNCFlg', 'FacQtrsWithNC', 'FacComplianceStatus']
ECHO_QCOLS = None

async def _echo_qcolumns(session):
    """Look up ECHO's column ID numbers so the results include coordinates."""
    global ECHO_QCOLS
    if ECHO_QCOLS is None:
        ECHO_QCOLS = ''
        try:
            async with session.get(f"{ECHO_BASE}.metadata", params={'output': 'JSON'},
                                   timeout=aiohttp.ClientTimeout(total=60)) as r:
                cols = (await r.json(content_type=None)).get('Results', {}).get('ResultColumns', [])
            ids = [str(c.get('ColumnID')) for c in cols if c.get('ObjectName') in ECHO_WANTED]
            if ids:
                ECHO_QCOLS = ','.join(ids)
        except Exception as e:
            print(f"[WARN] ECHO column lookup failed ({e}); locations will be county-level.")
    return ECHO_QCOLS

async def _echo_county(session, county):
    params = {'output': 'JSON', 'p_st': 'TX', 'p_co': county, 'responseset': '1000'}
    qcols = await _echo_qcolumns(session)
    if qcols:
        params['qcolumns'] = qcols
    async with session.get(f"{ECHO_BASE}.get_facilities", params=params, timeout=aiohttp.ClientTimeout(total=60)) as r:
        res = (await r.json(content_type=None)).get('Results', {})
    facs = res.get('Facilities')
    if facs is None and res.get('QueryID'):
        qp = {'output': 'JSON', 'qid': res['QueryID'], 'pageno': '1'}
        if params.get('qcolumns'):
            qp['qcolumns'] = params['qcolumns']
        async with session.get(f"{ECHO_BASE}.get_qid", params=qp,
                               timeout=aiohttp.ClientTimeout(total=60)) as r:
            facs = (await r.json(content_type=None)).get('Results', {}).get('Facilities', [])
    return facs or []

async def compile_toxins(session):
    print("[PROCESSING] Pulling EPA ECHO compliance records...")
    out, errors, seen = [], 0, set()
    for county in ECHO_COUNTIES:
        try:
            facs = await _echo_county(session, county)
        except Exception as e:
            errors += 1
            print(f"[WARN] ECHO {county}: {e}")
            continue
        for f in facs:
            try:
                qtrs = int(f.get('FacQtrsWithNC') or 0)
            except ValueError:
                qtrs = 0
            snc = str(f.get('FacSNCFlg', '')).upper() == 'Y'
            if not (snc or qtrs > 0):
                continue
            approx = False
            try:
                lat, lon = float(f.get('FacLat')), float(f.get('FacLong'))
            except (TypeError, ValueError):
                cl = COUNTY_CENTERS.get(county)
                if not cl:
                    continue
                k = len(seen)
                lon, lat = cl[0] + 0.05 * ((k % 5) - 2), cl[1] + 0.05 * ((k // 5) % 5 - 2)
                approx = True
            rid = f.get('RegistryID') or ''
            if rid in seen:
                continue
            seen.add(rid)
            status = f.get('FacComplianceStatus') or ('Significant violation' if snc else 'Violation')
            severity = min(10, max(1, qtrs + (4 if snc else 0)))
            out.append({
                "facility": f.get('FacName', 'Unnamed facility'),
                "status": status,
                "bottom_line": f"{f.get('FacCity', '')}, {county.title()} County. EPA status: {status}. "
                               f"Quarters out of compliance (last 3 yrs): {qtrs}"
                               + (". Flagged as significant violator" if snc else "")
                               + (". Location shown at county level" if approx else "") + ".",
                "coordinates": [lon, lat],
                "severity": severity,
                "source_url": f"https://echo.epa.gov/detailed-facility-report?fid={rid}" if rid else "https://echo.epa.gov/",
            })
    if errors == len(ECHO_COUNTIES):
        print("[ERROR] EPA ECHO unreachable. Keeping the previous toxin feed unchanged.")
        return
    out.sort(key=lambda t: -t['severity'])
    with open('frontend/toxin_feed.json', 'w') as f:
        json.dump(out, f, indent=4)
    print(f"[SUCCESS] EPA ECHO: {len(out)} facilities with violations across {len(ECHO_COUNTIES) - errors} counties.")

# ---------------------------------------------------------
# TASK 4: FINANCIAL WALL OF SHAME (per-official summaries)
# ---------------------------------------------------------
import re as _re, html as _html
from collections import defaultdict as _dd

# Same company, many spellings. Pattern (checked in order) -> one clean name.
# Add a line here whenever a new spelling shows up.
DONOR_ALIASES = [
    (r'NEXTERA', 'NextEra Energy PAC'),
    (r'CENTER ?POINT', 'CenterPoint Energy PAC'),
    (r'ATMOS', 'Atmos Energy PAC'),
    (r'\bNRG\b', 'NRG Energy PAC'),
    (r'VISTRA|VISTA ENERGY', 'Vistra Energy Leaders PAC'),
    (r'ENERGY TRANSFER', 'Energy Transfer PAC'),
    (r'OIL\W+(&\W+|AND\W+)?GAS\W+ASS|GOOD GOV', 'Texas Oil & Gas Association PAC'),
    (r'RURAL FRIENDS', 'Rural Friends of Electric Cooperatives'),
    (r'AMERICAN ELECTRIC POWER|AMER ELEC POWER', 'AEP Texas PAC'),
    (r'DIRECT ENERGY', 'Direct Energy Employee PAC'),
    (r'EDF RENEWABLE', 'EDF Renewable Energy PAC'),
    (r'EL PASO ELECTRIC', 'El Paso Electric Employee PAC'),
    (r'(TEXAS|TX) BITCOIN', 'Texas Bitcoin PAC'),
    (r'TEXAS WATER INFRASTRUCTURE', 'Texas Water Infrastructure Network PAC'),
    (r'CHARLES (BRIAN )?B\.? ?BEYER|CHARLES BEYER', 'Charles Beyer'),
    (r'SEMPRA', 'Sempra Energy Employees PAC'),
    (r'CHESAPEAKE', 'Chesapeake Energy PAC'),
    (r'ONCOR', 'Oncor PAC'),
    (r'ENCANA', 'Encana Oil & Gas PAC'),
    (r'DEVON ENERGY', 'Devon Energy PAC'),
    (r'MARATHON OIL', 'Marathon Oil Employees PAC'),
    (r'TEXAS ALLIANCE OIL', 'Texas Alliance Oil & Gas PAC'),
    (r'ONE GAS', 'ONE Gas PAC'),
    (r'TEXAS RURAL WATER', 'Texas Rural Water PAC'),
    (r'REES-?JONES', 'Trevor Rees-Jones'),
    (r'SEQUE(IRA|RIA)', 'Simon Sequeira'),
]

def clean_donor(name):
    u = name.upper()
    for pat, canon in DONOR_ALIASES:
        if _re.search(pat, u):
            return canon
    # People: drop middle initials and fix capitalization ("GEORGE MCKINNEY" -> "George Mckinney")
    parts = [p for p in name.replace('.', ' ').split() if len(p) > 1]
    return ' '.join(p if any(c.islower() for c in p) else p.title() for p in parts) or name

def clean_official(name):
    # "Ashby, Trenton E. (The Honorable)" -> "Trenton E. Ashby"
    n = _re.sub(r'\(.*?\)', '', name).strip()
    if ',' in n:
        last, first = [x.strip() for x in n.split(',', 1)]
        n = f'{first} {last}'
    return n

def money(x):
    return f'${x:,.0f}'

async def process_financials():
    print("[PROCESSING] Aggregating Financial Receipts...")
    csv_path = 'data-engine/tec_pac_data.csv'
    wall_path = 'wall_of_shame.html'
    if not os.path.exists(csv_path):
        print("[WARNING] tec_pac_data.csv missing. Skipping Wall of Shame generation.")
        return

    with open(csv_path, mode='r', encoding='utf-8') as file:
        rows = list(csv.DictReader(file))

    tracked = _dd(lambda: {'total': 0.0, 'count': 0, 'donors': _dd(lambda: {'total': 0.0, 'count': 0, 'industry': '', 'last': ''})})
    local = _dd(lambda: {'total': 0.0, 'count': 0, 'industry': '', 'recipients': set(), 'city': ''})

    for r in rows:
        try:
            amt = float(r['Amount'])
        except (ValueError, KeyError):
            continue
        donor = clean_donor(r.get('Filer_Name', ''))
        if r.get('Tracked_Official') == 'YES':
            o = tracked[clean_official(r['Recipient_Name'])]
            o['total'] += amt; o['count'] += 1
            d = o['donors'][donor]
            d['total'] += amt; d['count'] += 1
            d['industry'] = r.get('PAC_Industry', '')
            d['last'] = max(d['last'], r.get('Date', ''))
        else:
            l = local[donor]
            l['total'] += amt; l['count'] += 1
            l['industry'] = r.get('PAC_Industry', '')
            l['city'] = r.get('Donor_City', '')
            l['recipients'].add(clean_official(r['Recipient_Name']))

    dates = sorted(r['Date'] for r in rows if r.get('Date'))
    span = f'{dates[0][:4]}–{dates[-1][:7]}' if dates else ''
    e = _html.escape
    tec = 'https://www.ethics.state.tx.us/search/cf/'

    css = """
:root{--bg:#0e0d0c;--panel:#171513;--line:#2c2824;--text:#e8e2d9;--dim:#9a9187;--amber:#e0a43a;--red:#d9483b}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font-family:Georgia,'Times New Roman',serif;line-height:1.55}
.wrap{max-width:1000px;margin:0 auto;padding:40px 20px 80px}
header{border-bottom:2px solid var(--red);padding-bottom:22px;margin-bottom:30px}
h1{font-size:clamp(2rem,5vw,3.2rem);margin:0;color:var(--red);letter-spacing:-.01em}
.lede{color:var(--dim);max-width:65ch;margin:10px 0 0}
a.back{display:inline-block;margin-top:16px;color:var(--amber);font-family:system-ui,sans-serif;font-size:.9rem}
h2.sec{font-size:1.4rem;margin:44px 0 6px}p.note{color:var(--dim);margin:0 0 20px;max-width:65ch;font-size:.95rem}
.official{background:var(--panel);border:1px solid var(--line);border-left:4px solid var(--amber);border-radius:4px;padding:22px;margin-bottom:22px}
.off-head{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:baseline;gap:8px}
.off-head h3{margin:0;font-size:1.5rem}.total{font-family:system-ui,sans-serif;font-size:1.6rem;font-weight:700;color:var(--amber)}
.sub{color:var(--dim);font-family:system-ui,sans-serif;font-size:.85rem;margin:2px 0 14px}
.tbl{overflow-x:auto}table{width:100%;border-collapse:collapse;font-family:system-ui,sans-serif;font-size:.88rem}
th{text-align:left;color:var(--dim);font-weight:500;border-bottom:1px solid var(--line);padding:6px 8px}
td{padding:7px 8px;border-bottom:1px solid #221f1c}td.n{text-align:right;white-space:nowrap}th.n{text-align:right}
details summary{cursor:pointer;color:var(--amber);font-family:system-ui,sans-serif;font-size:.85rem;margin-top:10px}
details summary:focus-visible,a:focus-visible{outline:2px solid var(--amber);outline-offset:2px}
.src{font-family:system-ui,sans-serif;font-size:.8rem;color:var(--dim);margin-top:40px;border-top:1px solid var(--line);padding-top:16px}
.src a{color:var(--amber)}
"""

    def donor_table(items):
        out = '<div class="tbl"><table><thead><tr><th>Donor</th><th>Industry</th><th class="n">Gifts</th><th>Most recent</th><th class="n">Total</th></tr></thead><tbody>'
        for name, d in items:
            out += f'<tr><td>{e(name)}</td><td>{e(d["industry"])}</td><td class="n">{d["count"]}</td><td>{e(d["last"])}</td><td class="n">{money(d["total"])}</td></tr>'
        return out + '</tbody></table></div>'

    h = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Wall of Shame | Aquifer Defense Grid</title><style>{css}</style></head><body><div class="wrap">
<header><h1>Wall of Shame</h1>
<p class="lede">Campaign donations from energy, utility, oil and gas, timber and water interests to the officials who represent Deep East Texas, {e(span)}. Every figure comes from Texas Ethics Commission filings.</p>
<a class="back" href="index.html">Back to the map</a></header>
<h2 class="sec">Officials we track</h2>
<p class="note">Totals count only donors whose name, employer or occupation matched an industry keyword, so real totals may be higher. A donation is a public, legal record of support, not proof of wrongdoing.</p>"""

    for official, o in sorted(tracked.items(), key=lambda kv: -kv[1]['total']):
        donors = sorted(o['donors'].items(), key=lambda kv: -kv[1]['total'])
        h += f'<section class="official"><div class="off-head"><h3>{e(official)}</h3><span class="total">{money(o["total"])}</span></div>'
        h += f'<div class="sub">{o["count"]} donations from {len(donors)} donors</div>'
        h += donor_table(donors[:8])
        if len(donors) > 8:
            h += f'<details><summary>Show all {len(donors)} donors</summary>{donor_table(donors[8:])}</details>'
        h += '</section>'

    if local:
        h += '<h2 class="sec">Local industry donors</h2><p class="note">Residents of Deep East Texas towns who listed an industry employer or occupation, giving to any candidate or PAC.</p>'
        h += '<div class="tbl"><table><thead><tr><th>Donor</th><th>Town</th><th>Industry</th><th>Gave to</th><th class="n">Total</th></tr></thead><tbody>'
        for name, l in sorted(local.items(), key=lambda kv: -kv[1]['total']):
            h += f'<tr><td>{e(name)}</td><td>{e(l["city"])}</td><td>{e(l["industry"])}</td><td>{e(", ".join(sorted(l["recipients"])))}</td><td class="n">{money(l["total"])}</td></tr>'
        h += '</tbody></table></div>'

    h += f'<p class="src">Source: Texas Ethics Commission campaign finance bulk data. Look up any filing at <a href="{tec}" target="_blank" rel="noopener">ethics.state.tx.us</a>.</p></div></body></html>'

    with open(wall_path, 'w', encoding='utf-8') as f:
        f.write(h)
    print(f"[SUCCESS] Wall of Shame built: {len(tracked)} officials, {sum(o['count'] for o in tracked.values())} donations, {len(local)} local donors.")

# ---------------------------------------------------------
# MASTER EXECUTION: ASYNC EVENT LOOP
# ---------------------------------------------------------
async def main():
    async with aiohttp.ClientSession() as session:
        await asyncio.gather(
            fetch_usgs(session),
            compile_permits(),
            compile_toxins(session),
            process_financials()
        )

asyncio.run(main())

end_time = time.time()
print(f"\n--- OMNI-GATEWAY SWEEP COMPLETE ---")
print(f"Total Execution Time: {round(end_time - start_time, 2)} seconds")
print("[READY] All payloads synced. UI is unblocked and ready for rendering.")
