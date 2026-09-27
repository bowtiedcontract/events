#!/usr/bin/env python3
"""Maintain data/events.json: prune past events, validate, dedupe, merge new events.

Usage (run from the repo root):
  python3 scripts/refresh.py                     # validate + prune + dedupe + sort, rewrite file
  python3 scripts/refresh.py --merge new.json    # also add events from new.json (a JSON list)
  python3 scripts/refresh.py --stamp             # also set last_updated to now (Europe/Berlin)
  python3 scripts/refresh.py --check             # validate only, don't write (exit 1 on errors)
  python3 scripts/refresh.py --today 2026-10-04  # pretend today is this date (for testing)
"""
import argparse, json, re, sys, unicodedata
from datetime import datetime, date
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
    BERLIN = ZoneInfo("Europe/Berlin")
except Exception:  # pragma: no cover
    BERLIN = None

ROOT = Path(__file__).resolve().parent.parent
EVENTS = ROOT / "data" / "events.json"
VENUES = ROOT / "data" / "venues.json"
CATEGORIES = {"festival", "music", "classical", "tech", "business", "art", "general"}
REQUIRED = ["title", "category", "date", "venue", "city", "description", "source"]
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIME_RE = re.compile(r"^(\d{2}:\d{2})?$")
URL_RE = re.compile(r"^https?://\S+$")


def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def occurrences(e):
    if e.get("dates"):
        return e["dates"]
    return [{"date": e.get("date"), "time": e.get("time", ""), "url": e.get("url", ""), "end_date": e.get("end_date")}]


def validate(e, i):
    errs = []
    label = f"#{i} {e.get('title', '?')!r}"
    for k in REQUIRED:
        if not e.get(k):
            errs.append(f"{label}: missing '{k}'")
    if e.get("category") not in CATEGORIES:
        errs.append(f"{label}: bad category {e.get('category')!r} (use one of {sorted(CATEGORIES)})")
    for o in occurrences(e):
        if not DATE_RE.match(o.get("date") or ""):
            errs.append(f"{label}: bad date {o.get('date')!r}")
        if not TIME_RE.match(o.get("time") or ""):
            errs.append(f"{label}: bad time {o.get('time')!r} (HH:MM or empty)")
        if o.get("end_date") and not DATE_RE.match(o["end_date"]):
            errs.append(f"{label}: bad end_date {o['end_date']!r}")
        if o.get("url") and not URL_RE.match(o["url"]):
            errs.append(f"{label}: bad url {o['url']!r}")
    if e.get("end_date") and not DATE_RE.match(e["end_date"]):
        errs.append(f"{label}: bad end_date {e['end_date']!r}")
    for k in ("url", "source"):
        if e.get(k) and not URL_RE.match(e[k]):
            errs.append(f"{label}: bad {k} {e[k]!r}")
    if not isinstance(e.get("english", False), bool):
        errs.append(f"{label}: 'english' must be true/false")
    return errs


def prune(e, today):
    """Drop past occurrences; return None if nothing is left."""
    t = today.isoformat()
    if e.get("dates"):
        keep = [o for o in e["dates"] if (o.get("end_date") or o["date"]) >= t]
        if not keep:
            return None
        e = dict(e, dates=keep)
        e["date"], e["time"] = keep[0]["date"], keep[0].get("time", "")
        if keep[0].get("url"):
            e["url"] = keep[0]["url"]
        if len(keep) == 1 and not keep[0].get("end_date"):
            # collapse to a single-date event
            e.pop("dates")
        return e
    end = e.get("end_date") or e["date"]
    return e if end >= t else None


def key(e):
    return (norm(e["title"]), norm(e["venue"].split(" – ")[0]), e["date"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--merge", action="append", default=[], help="JSON file with a list of events to add")
    ap.add_argument("--stamp", action="store_true", help="set last_updated to now (Berlin time)")
    ap.add_argument("--check", action="store_true", help="validate only")
    ap.add_argument("--today", help="override today's date (YYYY-MM-DD)")
    a = ap.parse_args()

    data = json.loads(EVENTS.read_text(encoding="utf-8"))
    events = data["events"]
    for f in a.merge:
        new = json.loads(Path(f).read_text(encoding="utf-8"))
        if isinstance(new, dict):
            new = new.get("events", [])
        print(f"merge: {len(new)} events from {f}")
        events += new

    errs = [m for i, e in enumerate(events) for m in validate(e, i)]
    if errs:
        print("VALIDATION ERRORS:\n  " + "\n  ".join(errs))
        sys.exit(1)

    venues = json.loads(VENUES.read_text(encoding="utf-8")) if VENUES.exists() else []
    for v in venues:
        if not v.get("name") or not v.get("city") or not URL_RE.match(v.get("url", "")):
            print(f"VENUE WARNING: {v}")

    today = date.fromisoformat(a.today) if a.today else (datetime.now(BERLIN).date() if BERLIN else date.today())
    before = len(events)
    events = [p for p in (prune(dict(e), today) for e in events) if p]
    pruned = before - len(events)

    seen, out, dups = {}, [], []
    for e in events:
        k = key(e)
        if k in seen:
            # keep the richer record (longer description / has price)
            old = seen[k]
            if len(e.get("description", "")) + len(e.get("price", "")) > len(old.get("description", "")) + len(old.get("price", "")):
                out[out.index(old)] = e
                seen[k] = e
            dups.append(e["title"])
            continue
        seen[k] = e
        out.append(e)
    out.sort(key=lambda e: (e["date"], e.get("time") or "99", e["title"]))

    print(f"events: {len(out)} (pruned {pruned} past, removed {len(dups)} duplicates)")
    if dups:
        print("  duplicates dropped: " + "; ".join(dups))
    if a.check:
        return
    data["events"] = out
    if a.stamp:
        now = datetime.now(BERLIN) if BERLIN else datetime.now()
        data["last_updated"] = now.strftime("%a %-d %b %Y, %H:%M") + " (Berlin time)"
    EVENTS.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    cats, cities = {}, {}
    for e in out:
        cats[e["category"]] = cats.get(e["category"], 0) + 1
        cities[e["city"]] = cities.get(e["city"], 0) + 1
    print("by category:", dict(sorted(cats.items(), key=lambda x: -x[1])))
    print("by city:", dict(sorted(cities.items(), key=lambda x: -x[1])))


if __name__ == "__main__":
    main()
