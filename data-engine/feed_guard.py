#!/usr/bin/env python3
"""
FEED GUARD - keeps a broken government source from wiping the live map.

  python3 data-engine/feed_guard.py snapshot   # before the sweep
  python3 data-engine/feed_guard.py check data-engine/   # inputs only, before the gateway
  python3 data-engine/feed_guard.py check '!data-engine/'  # everything else, after the gateway
  python3 data-engine/feed_guard.py verdict    # last step: fails if anything was held

'check' compares every feed to its snapshot. If a feed came back empty or
lost more than half its records (the usual sign a source renamed its
headers or went down), the old file is put back and the feed is marked
HELD in frontend/feed_status.json. The site keeps showing the last good
data instead of a blank map.

'check' always exits 0 so the job keeps going with the last good data.
'verdict' exits 2 if anything was held, so the nightly job shows as failed
and GitHub emails you.
"""
import json, os, re, shutil, sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, '.feed_guard')
STATUS = os.path.join(ROOT, 'frontend', 'feed_status.json')
DROP_LIMIT = 0.5      # held if fewer than half the old records come back
MIN_TO_JUDGE = 4      # tiny feeds (under 4 records) are never judged on drop

FEEDS = {
    'frontend/mega_permits.json':   'Permits and ERCOT grid requests',
    'frontend/toxin_feed.json':     'EPA ECHO violations',
    'frontend/usgs_telemetry.json': 'TWDB well water levels',
    'frontend/threat_feed.json':    'Threat feed',
    'frontend/threat_wells.json':   'Industrial wells',
    'wall_of_shame.html':           'Wall of Shame officials',
    'data-engine/votes.json':       'Legislative votes (LegiScan)',
    'data-engine/tec_pac_data.csv': 'Campaign donations (TEC)',
}


def count(path):
    full = os.path.join(ROOT, path)
    if not os.path.exists(full):
        return None
    try:
        if path.endswith('.html'):
            return open(full, encoding='utf-8').read().count('class="official"')
        if path.endswith('.csv'):
            with open(full, encoding='utf-8') as f:
                return max(sum(1 for _ in f) - 1, 0)
        d = json.load(open(full, encoding='utf-8'))
        if isinstance(d, list):
            return len(d)
        if 'features' in d:
            return len(d['features'])
        if 'officials' in d:
            return sum(len(v) for v in d['officials'].values())
        return len(d)
    except Exception:
        return 0   # unreadable counts as broken


def snapshot():
    os.makedirs(BASE, exist_ok=True)
    if os.path.exists(os.path.join(BASE, 'HELD')):
        os.remove(os.path.join(BASE, 'HELD'))
    counts = {}
    for path in FEEDS:
        counts[path] = count(path)
        if counts[path] is not None:
            dest = os.path.join(BASE, path.replace('/', '__'))
            shutil.copy2(os.path.join(ROOT, path), dest)
    json.dump(counts, open(os.path.join(BASE, 'counts.json'), 'w'), indent=2)
    print('[GUARD] Snapshot taken:', ', '.join(f'{FEEDS[p]}={c}' for p, c in counts.items()))


def check(prefix=''):
    try:
        old = json.load(open(os.path.join(BASE, 'counts.json')))
    except FileNotFoundError:
        sys.exit('[GUARD] No snapshot found. Run "feed_guard.py snapshot" before the sweep.')
    prev = {}
    if os.path.exists(STATUS):
        try:
            prev = {f['file']: f for f in json.load(open(STATUS))['feeds']}
        except Exception:
            prev = {}
    now = datetime.now(timezone.utc).isoformat(timespec='seconds')
    feeds, held = [], []
    for path, label in FEEDS.items():
        skip = path.startswith(prefix[1:]) if prefix.startswith('!') else not path.startswith(prefix)
        if skip:
            if path in prev:
                feeds.append(prev[path])
            continue
        before, after = old.get(path), count(path)
        state, note = 'updated', ''
        if before is None and after is None:
            continue
        if after in (None, 0) and before:
            state, note = 'held', f'came back empty (had {before})'
        elif before and before >= MIN_TO_JUDGE and after < before * DROP_LIMIT:
            state, note = 'held', f'dropped from {before} to {after}'
        elif after == before:
            state = 'unchanged'
        if state == 'held':
            backup = os.path.join(BASE, path.replace('/', '__'))
            if os.path.exists(backup):
                shutil.copy2(backup, os.path.join(ROOT, path))
            held.append(f'{label}: {note}')
            last_good = prev.get(path, {}).get('last_good')
        else:
            last_good = now if state == 'updated' else prev.get(path, {}).get('last_good', now)
        feeds.append({'file': path, 'label': label, 'state': state, 'records': before if state == 'held' else after,
                      'last_good': last_good, 'note': note})
    json.dump({'checked': now, 'feeds': feeds}, open(STATUS, 'w'), indent=2)
    for f in feeds:
        if f['file'].startswith(prefix[1:]) if prefix.startswith('!') else not f['file'].startswith(prefix):
            continue
        print(f"[GUARD] {f['state'].upper():9} {f['label']}: {f['records']} {f['note']}")
    if held:
        with open(os.path.join(BASE, 'HELD'), 'a') as f:
            f.write('\n'.join(held) + '\n')
        print('\n[GUARD] HELD - last good data kept for:\n  ' + '\n  '.join(held))
        print('[GUARD] Likely cause: the source changed its format or was down. Check the run log above.')
    else:
        print('[GUARD] All checked feeds passed.')


def verdict():
    flag = os.path.join(BASE, 'HELD')
    if os.path.exists(flag):
        print('[GUARD] This run held these feeds (site kept last good data):')
        print(open(flag).read())
        sys.exit(2)
    print('[GUARD] Clean run.')


if __name__ == '__main__':
    cmd = (sys.argv[1:] or [''])[0]
    if cmd == 'snapshot':
        snapshot()
    elif cmd == 'check':
        check(sys.argv[2] if len(sys.argv) > 2 else '')
    elif cmd == 'verdict':
        verdict()
    else:
        sys.exit(__doc__)
