"""Centralstation Darmstadt – programme list (static HTML)."""
import re
from .base import soup, text, parse_de_date, parse_time, make_event, skip

SOURCE = {"id": "centralstation_darmstadt", "name": "Centralstation Darmstadt",
          "url": "https://www.centralstation-darmstadt.de/programm"}
KEEP = re.compile(r"konzert|jazz|klassik|musik|live", re.I)


def scrape(ctx):
    sp = soup(SOURCE["url"])
    out = []
    for a in sp.select("a.calendar-item"):
        meta = text(a.select_one(".calendar-date"))
        parts = [p.strip() for p in meta.split("/")]
        genre = parts[-1] if len(parts) >= 3 else ""
        if not KEEP.search(genre):
            continue
        d = parse_de_date(parts[0])
        if not d or not ctx.in_window(d):
            continue
        title = text(a.select_one(".calendar-title"))
        sub = text(a.select_one(".calendar-subtitle"))
        if skip(title, sub):
            continue
        out.append(make_event(ctx, title=title, date_=d, time_=parse_time(parts[1] if len(parts) > 1 else ""),
                              venue_key="Centralstation Darmstadt", url=a["href"], source=SOURCE["url"],
                              default_category="classical" if "klassik" in genre.lower() else "music",
                              text_=f"{genre}. {sub}"))
    return out
