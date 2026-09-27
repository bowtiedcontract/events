"""Alte Oper Frankfurt – public JSON API used by their programme page."""
from datetime import date
from .base import CONCERT, get, make_event, group_runs, iso_to_berlin, skip

import re
NON_EVENT = re.compile(r"behind the scenes|meeting point|apéro|presseball|investment|hauptversammlung|kongress|symposium|verleihung|gala\b", re.I)
SOURCE = {"id": "alte_oper", "name": "Alte Oper Frankfurt", "url": "https://www.alteoper.de/de/api/events/"}


def scrape(ctx):
    out, url, pages = [], SOURCE["url"] + "?page=1", 0
    while url and pages < 40:
        data = get(url).json()
        pages += 1
        stop = False
        for ev in data.get("results", []):
            d, t = iso_to_berlin(ev["start_date"])
            if date.fromisoformat(d) > ctx.until:
                stop = True
                continue
            if not ctx.in_window(d) or "geschlossen" in (ev.get("ticket_text") or "").lower():
                continue
            title = ev.get("title") or ev.get("headline") or ""
            if skip(title, ev.get("subtitle") or "") or NON_EVENT.search(title):
                continue
            detail = f"https://www.alteoper.de/de/programm/{ev['slug']}/{ev['id']}"
            price = f"from €{ev['lowest_price']}".replace(".00", "") if ev.get("lowest_price") else ""
            out.append(make_event(ctx, title=title, date_=d, time_=t, venue_key="Alte Oper Frankfurt",
                                  room=ev.get("room") or None, url=ev.get("ticket_link") or detail,
                                  source=detail, price=price, default_category=None, fallback="music", allowed=CONCERT,
                                  text_=f"{ev.get('subtitle') or ''}. {ev.get('introduction') or ''} Veranstalter: {ev.get('organizer') or ''}"))
        url = None if stop else data.get("next")
    return group_runs(out)
