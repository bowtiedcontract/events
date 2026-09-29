"""LC Olympia Wiesbaden Lauftreff – dated sessions from the club calendar.

The Lauftreff category lists each Wednesday and Sunday meet with a start time.
Meeting point (from the club's own training-times page): Nerobergbahn car park.
"""
import re
from datetime import date

from .base import ScraperError, absurl, clean, make_event, series, soup, text

SOURCE = {"id": "lc_olympia", "name": "LC Olympia Wiesbaden Lauftreff",
          "url": "https://lcolympia.de/index.php/waswannwo/lcokalender/lauftreff"}
HOME = "https://lcolympia.de/"


def scrape(ctx):
    sp = soup(SOURCE["url"])
    groups = {}
    for ev in sp.select(".eb-event"):
        title = clean(text(ev.select_one(".eb-event-title")))
        raw = clean(text(ev.select_one(".eb-event-property-value")))
        m = re.search(r"(\d{2})-(\d{2})-(\d{4})\s+(\d{1,2}:\d{2})", raw)
        if not title or not m:
            continue
        d = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        if not ctx.in_window(d):
            continue
        link = ev.select_one("a.eb-event-title-link")
        url = absurl(HOME, link["href"]) if link and link.get("href") else SOURCE["url"]
        price = "Free" if re.search(r"\bfrei\b", clean(text(ev)), re.I) else ""
        groups.setdefault(title, []).append((d, m.group(4), url, price))
    if not groups:
        raise ScraperError("no Lauftreff rows found (LC Olympia calendar markup changed?)")
    out = []
    for title, rows in groups.items():
        rows.sort()
        e = make_event(ctx, title=f"LC Olympia {title}", date_=rows[0][0], time_=rows[0][1],
                       venue_key="LC Olympia Wiesbaden Lauftreff", url=rows[0][2], source=SOURCE["url"],
                       price=rows[0][3], category="running",
                       text_="Free public run of LC Olympia Wiesbaden, open to anyone who can run 5 km. "
                             "Meet at the Nerobergbahn car park in the Nerotal. Several pace groups, about an hour, "
                             "everyone starts and finishes together.")
        e = series(e, [(d, t) for d, t, _, _ in rows], url=rows[0][2], key=f"lco-{title}")
        if e and e.get("dates"):
            for slot, row in zip(e["dates"], rows):
                slot["url"] = row[2]
        if e:
            out.append(e)
    return out
