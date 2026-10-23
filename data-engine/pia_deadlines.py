#!/usr/bin/env python3
"""PIA deadline engine for the Records Requests page.
Reads frontend/records.json (requests may carry a "clock" block) and writes
frontend/deadlines.json (shown on records.html) and data-engine/deadline_alerts.md
(turned into a GitHub issue, which emails Fawn).
clock fields: start, start_note, kind ("legal"|"expected"), certified, ag_requested,
ours: [{"what": "...", "from": "YYYY-MM-DD", "rule": "10bd"|"61d", "done": false}]
Usage: pia_deadlines.py [--today YYYY-MM-DD]
"""
import json, sys, datetime as dt
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
REC, OUT, ALERTS = ROOT/"frontend/records.json", ROOT/"frontend/deadlines.json", ROOT/"data-engine/deadline_alerts.md"
# Texas state holidays when offices close. Local agencies set their own, so dates are estimates.
HOLIDAYS = {
 "2026-01-01","2026-01-19","2026-02-16","2026-05-25","2026-09-07","2026-11-11",
 "2026-11-26","2026-11-27","2026-12-24","2026-12-25",
 "2027-01-01","2027-01-18","2027-02-15","2027-05-31","2027-09-06","2027-11-11",
 "2027-11-25","2027-11-26","2027-12-24",
}
D = dt.date.fromisoformat
def is_bd(d): return d.weekday() < 5 and d.isoformat() not in HOLIDAYS
def add_bd(start, n):
    d = start
    while n:
        d += dt.timedelta(days=1)
        if is_bd(d): n -= 1
    return d
def bd_between(a, b):
    if b == a: return 0
    s, e, sign = (a, b, 1) if b > a else (b, a, -1)
    n, d = 0, s
    while d < e:
        d += dt.timedelta(days=1)
        if is_bd(d): n += 1
    return sign * n
MON = ["Jan.","Feb.","March","April","May","June","July","Aug.","Sept.","Oct.","Nov.","Dec."]
DAY = ["Mon.","Tue.","Wed.","Thu.","Fri.","Sat.","Sun."]
def short(d): return f"{MON[d.month-1]} {d.day}"
def label(d): return f"{DAY[d.weekday()]}, {short(d)}"
def main():
    today = dt.date.today()
    if "--today" in sys.argv: today = D(sys.argv[sys.argv.index("--today")+1])
    data = json.loads(REC.read_text())
    out, alerts = [], []
    for r in data["requests"]:
        name = r["agency"] + (f" {r['number']}" if r.get("number") else f" (filed {r['filed']})")
        c = r.get("clock") or {}
        item = {"key": f"{r['agency']}|{r['filed']}|{r.get('number','')}", "agency": r["agency"], "number": r.get("number",""), "filed": r["filed"]}
        if r.get("state") in ("done", "closed") or not c:
            out.append(item); continue
        if c.get("ag_requested"):
            due = add_bd(D(c["ag_requested"]), 45)
            item.update(type="ag", due=due.isoformat(),
                text=f"Attorney General ruling due about {label(due)}, {due.year} (45 business days after the {r['agency']} request of {short(D(c['ag_requested']))}; the AG may extend it 10 business days).")
            if today > due:
                alerts.append(f"- **{name}**: AG ruling estimate ({due}) has passed with no ruling logged. Check the AG's ruling search.")
        elif c.get("certified"):
            due = D(c["certified"])
            item.update(type="certified", due=due.isoformat(), text=f"The agency said the records would be ready by {label(due)}.")
            if today > due:
                item["overdue_bd"] = bd_between(due, today)
                alerts.append(f"- **{name}**: agency's own ready date ({due}) has passed.")
        elif c.get("start"):
            start, kind = D(c["start"]), c.get("kind","legal")
            due = add_bd(start, 10)
            why = c.get("start_note","the request was received")
            item.update(type=kind, due=due.isoformat(), start=c["start"])
            if kind == "legal":
                item["text"] = f"Response due {label(due)}: 10 business days after {why}."
            else:
                item["text"] = f"Expected around {label(due)} (10 business days after {why}; no fixed legal deadline)."
            if today > due:
                n = bd_between(due, today); item["overdue_bd"] = n
                if kind == "legal":
                    item["text"] = f"Response was due {label(due)} (10 business days after {why}). Past due by {n} business day{'s' if n!=1 else ''}."
                    alerts.append(f"- **{name}**: agency deadline {due} has passed. Consider a follow-up asking for a written ready date (Gov't Code 552.221(d)).")
                else:
                    alerts.append(f"- **{name}**: expected reply ({due}) has not been logged. Consider a check-in.")
        for o in c.get("ours", []):
            if o.get("done"): continue
            f = D(o["from"])
            due = f + dt.timedelta(days=61) if o["rule"] == "61d" else add_bd(f, 10)
            left = (due - today).days if o["rule"] == "61d" else bd_between(today, due)
            if left <= (14 if o["rule"] == "61d" else 5):
                alerts.append(f"- **{name}**: ETLC must {o['what']} by {due}.")
        out.append(item)
    OUT.write_text(json.dumps({"computed": today.isoformat(),
        "note": "Deadlines are estimates. They skip weekends and Texas state holidays; local agencies may observe different holidays.",
        "requests": out}, indent=2))
    ALERTS.write_text(("\n".join(alerts) + "\n") if alerts else "")
    print(f"{len(out)} requests checked on {today}; {len(alerts)} alert(s).")
    for a in alerts: print(a)
if __name__ == "__main__": main()
