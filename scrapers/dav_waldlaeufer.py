"""DAV Wiesbaden Waldläufer – weekly trail run.

The group page gives a fixed meet (Tuesday 18:30, Nerobergbahn valley station)
and no per-date calendar, so each Tuesday in the scrape window is emitted.
"""
import re

from .base import ScraperError, clean, make_event, series, soup

SOURCE = {"id": "dav_waldlaeufer", "name": "DAV Wiesbaden Waldläufer",
          "url": "https://www.dav-wiesbaden.de/gruppen/waldlaeufer"}


def scrape(ctx):
    flat = clean(soup(SOURCE["url"]).get_text(" ", strip=True))
    m = re.search(r"Dienstag\s+(\d{1,2})[:.](\d{2})", flat)
    if not m or not re.search(r"neroberg", flat, re.I):
        raise ScraperError("Waldläufer Tuesday meet not found (page wording changed?)")
    clock = f"{int(m.group(1)):02d}:{m.group(2)}"
    days = ctx.dates_on(1)
    if not days:
        return []
    e = make_event(ctx, title="DAV Waldläufer trail run", date_=days[0], time_=clock,
                   venue_key="DAV Wiesbaden Waldläufer", url=SOURCE["url"], source=SOURCE["url"],
                   price="Free", category="running",
                   text_="Weekly trail run with the DAV Wiesbaden Waldläufer in the Wiesbaden city forest. "
                         f"Tuesdays at {clock} at the Nerobergbahn valley station. About 60 minutes on trails; "
                         "a comfortable 6:30 min/km pace is the group's guide. First-timers should contact the "
                         "group via the DAV page (they coordinate on Signal).")
    return [series(e, [(d, clock) for d in days], url=SOURCE["url"], key="waldlaeufer-tue")]
