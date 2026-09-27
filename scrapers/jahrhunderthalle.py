"""Jahrhunderthalle Frankfurt – public events.json from the myticket box office."""
from datetime import datetime
from .base import get, make_event, group_runs, categorize, skip
import re

SOURCE = {"id": "jahrhunderthalle", "name": "Jahrhunderthalle Frankfurt",
          "url": "https://www.myticket-jahrhunderthalle.de/events.json"}
NOT_MUSIC = re.compile(r"comedy|lesung|podcast|kabarett|kinder|familie|messe|markt|börse|vortrag|live-hörspiel|show\b", re.I)


def scrape(ctx):
    out = []
    for ev in get(SOURCE["url"]).json().get("events", []):
        if ev.get("canceled"):
            continue
        d = datetime.strptime(ev["date"], "%d.%m.%y").date()
        if not ctx.in_window(d):
            continue
        title, sub = ev.get("title", ""), ev.get("subline", "")
        if skip(title, sub) or NOT_MUSIC.search(f"{title} {sub}"):
            continue
        cat = categorize(title, sub, None)
        if cat not in ("music", "classical", "festival"):
            continue  # no genre in the feed: only keep what is clearly a concert
        detail = "https://www.jahrhunderthalle.de" + ev["detailLink"] if ev.get("detailLink") else "https://www.jahrhunderthalle.de/programm"
        out.append(make_event(ctx, title=title, date_=d, time_=ev.get("time", ""),
                              venue_key="Jahrhunderthalle Frankfurt",
                              room=None, url=ev.get("bookingLink") or detail, source=detail, category=cat,
                              text_=f"{sub}. {'Verlegt. ' if ev.get('postponed') else ''}{'Ausverkauft.' if ev.get('sold') else ''}"))
    return group_runs(out)
