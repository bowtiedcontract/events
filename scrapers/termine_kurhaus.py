"""Kurhaus Wiesbaden guest events via termine.de (promoter concerts that the Kurhaus's own calendar
doesn't list, e.g. touring orchestras, film/anime concerts, piano recitals). Static HTML list."""
import re
from .base import CONCERT, soup, text, parse_de_date, make_event, group_runs, skip

SOURCE = {"id": "termine_kurhaus", "name": "Kurhaus Wiesbaden (termine.de listing)",
          "url": "https://termine.de/calendar/Kurhaus-Wiesbaden/jrgdHS4"}


def scrape(ctx):
    sp = soup(SOURCE["url"])
    out = []
    for li in sp.find_all("li"):
        a = li.find("a", href=True)
        if not a or "/calendar/Kurhaus-Wiesbaden/" not in a["href"] or a["href"].rstrip("/") == SOURCE["url"]:
            continue
        raw = li.get_text(" ", strip=True)
        m = re.search(r":\s*(\d{1,2}\.\d{1,2}\.\d{4}),\s*(\d{1,2}:\d{2})", raw)
        if not m:
            continue
        d = parse_de_date(m.group(1))
        if not d or not ctx.in_window(d):
            continue
        title = text(a)
        if skip(title):
            continue
        blurb = " ".join(text(x) for x in li.find_all(["h2", "p"]))
        out.append(make_event(ctx, title=title, date_=d, time_=m.group(2).zfill(5), venue_key="Kurhaus Wiesbaden",
                              url=a["href"], source=SOURCE["url"], default_category=None, fallback="music",
                              allowed=CONCERT, text_=blurb))
    return group_runs(out)
