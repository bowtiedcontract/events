"""RheinRunners / LaufZeit – the social run published on laufzeit-mainz.de/lauftreff.

The organiser page currently says the meet is Thursdays at 19:00 at Sportraum Mainz,
Curiestraße 2, and that this is always the meeting point (they run through Mainz and
Wiesbaden from there). There is no per-date calendar, so each Thursday in the scrape
window is emitted.

A Monday 19:00 meet at LaufZeit Wiesbaden, Luisenstraße 17, is only emitted if that
page itself mentions a Monday and Luisenstraße. It does not at the moment; an older
directory still describes that meet, and the old Wiesbaden URL on the same site 404s.
"""
import re

from .base import ScraperError, clean, make_event, series, soup

SOURCE = {"id": "rheinrunners", "name": "RheinRunners / LaufZeit",
          "url": "https://laufzeit-mainz.de/lauftreff"}


def scrape(ctx):
    flat = clean(soup(SOURCE["url"]).get_text(" ", strip=True))
    out = []
    if re.search(r"donnerstags?\s+19[:.]00", flat, re.I) and re.search(r"curiestra", flat, re.I):
        days = ctx.dates_on(3)
        if days:
            e = make_event(ctx, title="RheinRunners Lauftreff", date_=days[0], time_="19:00",
                       venue_key="Sportraum Mainz", url=SOURCE["url"], source=SOURCE["url"],
                       price="Free", category="running",
                       text_="Free social run with RheinRunners / LaufZeit. Thursdays at 19:00 on the car park "
                             "of Sportraum Mainz, Curiestraße 2 (stop Jägerhaus). About 5–7 km; beginners and "
                             "regulars, nobody is left behind. Shoe-test events are announced on the same page.")
            out.append(series(e, [(d, "19:00") for d in days], url=SOURCE["url"], key="rheinrunners-thu"))
    if re.search(r"\bmontags?\b", flat, re.I) and re.search(r"luisen", flat, re.I):
        m = re.search(r"(\d{1,2})[:.](\d{2})", flat)
        clock = f"{int(m.group(1)):02d}:{m.group(2)}" if m else "19:00"
        days = ctx.dates_on(0)
        if days:
            e = make_event(ctx, title="RheinRunners Wiesbaden", date_=days[0], time_=clock,
                           venue_key=None, venue="LaufZeit Wiesbaden", city="Wiesbaden",
                           address="Luisenstraße 17, 65185 Wiesbaden",
                           url=SOURCE["url"], source=SOURCE["url"], price="Free", category="running",
                           text_=f"Social run from LaufZeit Wiesbaden, Luisenstraße 17, Mondays at {clock}.")
            out.append(series(e, [(d, clock) for d in days], url=SOURCE["url"], key="rheinrunners-mon"))
    out = [e for e in out if e]
    if not out:
        raise ScraperError("no weekly RheinRunners meet found on the LaufZeit page")
    return out
