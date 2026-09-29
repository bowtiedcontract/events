"""Maaraue parkrun, Wiesbaden-Kastel – free Saturday 5 km.

parkrun's own page says every Saturday at 9:00 at Maaraue 27. There is no
per-date calendar, so each Saturday in the window is emitted. Participation
needs a one-time free parkrun registration and a barcode; no German is required.
"""
import re

from .base import ScraperError, clean, make_event, series, soup

SOURCE = {"id": "parkrun_maaraue", "name": "Maaraue parkrun",
          "url": "https://www.parkrun.com.de/maaraue/"}


def scrape(ctx):
    flat = clean(soup(SOURCE["url"]).get_text(" ", strip=True))
    if re.search(r"findet nicht statt|abgesagt|cancelled|event is closed", flat, re.I):
        return []
    m = re.search(r"jeden Samstag um\s*(\d{1,2}):(\d{2})", flat, re.I)
    if not m:
        raise ScraperError("Maaraue parkrun Saturday line not found")
    clock = f"{int(m.group(1)):02d}:{m.group(2)}"
    days = ctx.dates_on(5)
    if not days:
        return []
    e = make_event(ctx, title="Maaraue parkrun", date_=days[0], time_=clock,
                   venue_key="Maaraue parkrun", url=SOURCE["url"], source=SOURCE["url"],
                   price="Free", category="running", english=True,
                   text_="Free weekly 5 km at Maaraue parkrun, Wiesbaden-Kastel (Maaraue 27). "
                         f"Every Saturday at {clock}. Walk, jog or run. Register once on parkrun and bring your barcode. "
                         "Coffee afterwards at the grill hut.")
    return [series(e, [(d, clock) for d in days], url=SOURCE["url"], key="parkrun-maaraue")]
