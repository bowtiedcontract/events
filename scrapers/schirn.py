"""SCHIRN Kunsthalle Frankfurt – exhibition list; titles sit above a date-range line.
Upcoming shows are sometimes only announced as 'Startet am 1. Oktober' (no end date)."""
import re
from .base import exhibitions, soup, clean, parse_de_date, make_event

SOURCE = {"id": "schirn", "name": "SCHIRN Kunsthalle Frankfurt", "url": "https://www.schirn.de/ausstellungen/"}


def scrape(ctx):
    sp = soup(SOURCE["url"])
    out = exhibitions(ctx, SOURCE["url"], SOURCE["name"], title_offset=1, sp=sp)
    have = {e["title"].lower() for e in out}
    lines = [clean(l) for l in sp.get_text("\n").split("\n") if clean(l)]
    for i, line in enumerate(lines[1:], 1):
        m = re.match(r"(?:Startet am|Ab|Eröffnung am)\s+(.+)$", line)
        if not m:
            continue
        d = parse_de_date(m.group(1), ctx.today)
        title = lines[i - 1]
        if d and ctx.in_window(d) and title.lower() not in have and not title.endswith(":"):
            have.add(title.lower())
            out.append(make_event(ctx, title=title, date_=d, venue_key=SOURCE["name"], url=SOURCE["url"],
                                  source=SOURCE["url"], category="art", text_=f"Ausstellung. {line}"))
    return out
