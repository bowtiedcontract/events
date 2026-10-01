"""Maaraue parkrun, Wiesbaden-Kastel – free Saturday 5 km.

parkrun's own page says every Saturday at 9:00 at Maaraue 27. There is no
per-date calendar, so each Saturday in the window is emitted. Participation
needs a one-time free parkrun registration and a barcode; no German is required.

GitHub Actions runners often get HTTP 405 from parkrun.com.de; in that case we
fall back to the known standing meet (Saturday 09:00) so the series stays on
the dashboard. Cancellation text on a successful fetch still returns [].
"""
import re

from .base import ScraperError, clean, make_event, series, soup

SOURCE = {"id": "parkrun_maaraue", "name": "Maaraue parkrun",
          "url": "https://www.parkrun.com.de/maaraue/"}
DEFAULT_CLOCK = "09:00"


def scrape(ctx):
    clock = DEFAULT_CLOCK
    try:
        flat = clean(soup(SOURCE["url"]).get_text(" ", strip=True))
    except ScraperError as ex:
        # Bot protection / method not allowed from some egress IPs (e.g. Actions).
        if re.search(r"\b405\b|Not Allowed|403\b|Forbidden", str(ex), re.I):
            flat = ""
        else:
            raise
    if flat:
        if re.search(r"findet nicht statt|abgesagt|cancelled|event is closed", flat, re.I):
            return []
        m = re.search(r"jeden Samstag um\s*(\d{1,2}):(\d{2})", flat, re.I)
        if m:
            clock = f"{int(m.group(1)):02d}:{m.group(2)}"
        elif not re.search(r"parkrun|Maaraue", flat, re.I):
            raise ScraperError("Maaraue parkrun page content unexpected")
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
