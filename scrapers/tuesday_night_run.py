"""Tuesday Night Run Club Mainz – English-language social run.

The club page says every Tuesday at 7pm outside Kelly's Irish Pub by Mainz
Hauptbahnhof. There is no per-date calendar, so each Tuesday in the window is emitted.
"""
import re

from .base import ScraperError, clean, make_event, series, soup

SOURCE = {"id": "tuesday_night_run", "name": "Tuesday Night Run Mainz",
          "url": "https://www.tuesdaynightrun.club/"}


def scrape(ctx):
    flat = clean(soup(SOURCE["url"]).get_text(" ", strip=True))
    if not re.search(r"every tuesday at 7\s*pm", flat, re.I):
        raise ScraperError("Tuesday 7pm line not found on tuesdaynightrun.club")
    if not re.search(r"kelly", flat, re.I):
        raise ScraperError("Kelly's meeting point not found on tuesdaynightrun.club")
    days = ctx.dates_on(1)
    if not days:
        return []
    e = make_event(ctx, title="Tuesday Night Run", date_=days[0], time_="19:00",
                   venue_key="Kelly's Irish Pub", url=SOURCE["url"], source=SOURCE["url"],
                   price="Free", category="running", english=True,
                   text_="English-language social run in Mainz, 5–7 km, all paces. "
                         "Every Tuesday at 19:00 outside Kelly's Irish Pub by Mainz Hauptbahnhof. "
                         "Sign-up is via the Meetup link on the club page. A drink afterwards.")
    return [series(e, [(d, "19:00") for d in days], url=SOURCE["url"], key="tnrc-tue")]
