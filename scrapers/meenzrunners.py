"""MeenzRunners – Tuesday social run at the Theodor-Heuss-Brücke, Mainz.

The club publishes the standing meet on its Strava profile and it is restated on
socialrunclubs.de ("Dienstag, 19:00 Uhr, Theodor-Heuss-Brücke"). There is no
per-date calendar, so each Tuesday in the window is emitted. This is a different
group from the English Tuesday Night Run Club at Kelly's.
"""
import re

from .base import ScraperError, clean, make_event, series, soup

SOURCE = {"id": "meenzrunners", "name": "MeenzRunners",
          "url": "https://socialrunclubs.de/mainz/meenzrunners/"}
CLUB = "https://www.strava.com/clubs/MeenzRunners"


def scrape(ctx):
    flat = clean(soup(SOURCE["url"]).get_text(" ", strip=True))
    m = re.search(r"Dienstag,\s*(\d{1,2}):(\d{2})\s*Uhr,\s*(Theodor-Heuss-Brücke)", flat, re.I)
    if not m:
        raise ScraperError("MeenzRunners Tuesday line not found")
    clock = f"{int(m.group(1)):02d}:{m.group(2)}"
    days = ctx.dates_on(1)
    if not days:
        return []
    e = make_event(ctx, title="MeenzRunners social run", date_=days[0], time_=clock,
                   venue_key="Theodor-Heuss-Brücke", url=CLUB, source=SOURCE["url"],
                   price="Free", category="running",
                   text_="Social run with MeenzRunners, one of the larger Mainz run clubs. "
                         f"Tuesdays at {clock} at the Theodor-Heuss-Brücke. No signup; several pace groups, "
                         "about 6–7 km. The last Tuesday of the month is often the Bierstübchen run.")
    return [series(e, [(d, clock) for d in days], url=CLUB, key="meenzrunners-tue")]
