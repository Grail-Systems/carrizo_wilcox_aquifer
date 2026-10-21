#!/usr/bin/env python3
"""One-time patch: adds a 'Key votes' table to each official on the Wall of Shame.
Votes come from data-engine/votes.json (legiscan_votes.py); which bills appear
is controlled by data-engine/key_votes.json. Safe to run twice."""
from pathlib import Path

P = Path(__file__).resolve().parent / "omni_gateway.py"
src = P.read_text()
if "def key_votes_html" in src:
    print("Already patched. Nothing to do."); raise SystemExit

FUNC = r'''
# ---------------------------------------------------------
# KEY VOTES: LegiScan roll calls for bills listed in key_votes.json
# ---------------------------------------------------------
def _vote_word(v):
    return {'Yea': 'Yes', 'Nay': 'No', 'NV': 'Not voting', 'Absent': 'Absent'}.get(v, v)

def _stage(motion):
    m = (motion or '').lower()
    if 'conference committee' in m: return 'final version'
    if 'concur' in m: return "accepting the other chamber's changes"
    if 'amendment' in m and 'fail' in m: return 'an amendment that failed'
    if '3rd' in m or 'passed' in m: return 'passage'
    if '2nd' in m: return 'second reading'
    return None  # procedural motions are skipped

def key_votes_html(official, e):
    try:
        kv = json.load(open('data-engine/key_votes.json', encoding='utf-8'))
        votes = json.load(open('data-engine/votes.json', encoding='utf-8'))['officials'].get(official, [])
    except (OSError, ValueError):
        return ''
    rows = ''
    for item in kv:
        recs = [r for r in votes if r['bill'] == item['bill'] and r['session'] == item['session']]
        seen, parts = set(), []
        for r in sorted(recs, key=lambda r: r['date'] or ''):
            st = _stage(r['motion'])
            if not st or (r['date'], st) in seen:
                continue
            seen.add((r['date'], st))
            dt = datetime.strptime(r['date'], '%Y-%m-%d')
            mon = ['Jan.', 'Feb.', 'March', 'April', 'May', 'June', 'July', 'Aug.', 'Sept.', 'Oct.', 'Nov.', 'Dec.'][dt.month - 1]
            d = f'{mon} {dt.day}, {dt.year}'
            parts.append(f"<b>{e(_vote_word(r['vote']))}</b> on {e(st)} <span class=\"kv-d\">({e(d)}, {e(r['tally'])})</span>")
        if not parts:
            continue
        ctx = item.get('context', {}).get(official, '')
        rows += (f'<tr><td><a href="{e(item["url"])}" target="_blank" rel="noopener">{e(item["bill"])}</a>'
                 f'<div class="kv-d">{e(str(item["year"]))}</div></td>'
                 f'<td><b>{e(item["title"])}.</b> {e(item["summary"])}'
                 + (f'<div class="kv-ctx">{e(ctx)}</div>' if ctx else '') +
                 f'</td><td>{"<br>".join(parts)}</td></tr>')
    if not rows:
        return ''
    return ('<h4 class="kv-h">Key votes</h4><div class="tbl"><table><thead><tr><th>Bill</th>'
            '<th>What it does</th><th>How they voted</th></tr></thead><tbody>' + rows + '</tbody></table></div>')

'''

CSS = r""".src a{color:var(--amber)}
.kv-h{font-family:system-ui,sans-serif;font-size:.8rem;letter-spacing:.08em;text-transform:uppercase;color:var(--dim);margin:22px 0 4px}
.kv-d{color:var(--dim);font-size:.8rem}.kv-ctx{margin-top:6px;color:var(--amber);font-size:.85rem}
td a{color:var(--amber)}"""

edits = [
    ("async def process_financials():", FUNC + "async def process_financials():"),
    (".src a{color:var(--amber)}", CSS),
    ("        h += '</section>'\n", "        h += key_votes_html(official, e)\n        h += '</section>'\n"),
    ("</p></div></body></html>'",
     " Vote records from <a href=\"https://legiscan.com\" target=\"_blank\" rel=\"noopener\">LegiScan</a> (CC BY 4.0), checked against Texas Legislature Online.</p></div></body></html>'"),
]
for old, new in edits:
    n = src.count(old)
    if n != 1:
        raise SystemExit(f"Stopped, nothing changed: expected 1 match for {old.strip()[:40]!r}, found {n}.")
for old, new in edits:
    src = src.replace(old, new)
if "from datetime import datetime" not in src:
    src = "from datetime import datetime\n" + src
P.write_text(src)
print("Patched omni_gateway.py: Key votes section added.")
