"""Debug a single scraper: python -m scrapers <module> [--json]"""
import json, sys
from . import load, MODULES
from .base import Context

names = [a for a in sys.argv[1:] if not a.startswith("-")] or MODULES
ctx = Context()
for n in names:
    mod = load(n)
    evs = mod.scrape(ctx)
    print(f"== {n}: {len(evs)} events")
    for e in evs:
        if "--json" in sys.argv:
            print(json.dumps(e, ensure_ascii=False))
        else:
            print(f"  {e['date']} {e['time'] or '--:--'} [{e['category']}] {e['title'][:60]} @ {e['venue']}"
                  + (f" (+{len(e['dates'])-1} dates)" if e.get('dates') else "") + (f" -> {e['end_date']}" if e.get('end_date') else ""))
