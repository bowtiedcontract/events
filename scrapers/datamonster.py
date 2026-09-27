"""datamonster.io – 'Monster-Meeting Rhein-Main' data/AI community meetups."""
import re
from .base import soup, absurl, parse_de_date, parse_time, make_event, clean

SOURCE = {"id": "datamonster", "name": "datamonster Rhein-Main meetups", "url": "https://www.datamonster.io/monstermeeting"}


def scrape(ctx):
    sp = soup(SOURCE["url"])
    links = sorted({absurl(SOURCE["url"], a["href"]) for a in sp.find_all("a", href=True)
                    if "/monstermeeting/" in a["href"] and "rhein-main" in a["href"].lower()})
    out = []
    for url in links:
        p = soup(url)
        flat = clean(p.get_text(" ", strip=True))
        m = re.search(r"Datum/Uhrzeit:\s*([\d.]+)\s*(\d{1,2}:\d{2})?", flat)
        if not m:
            continue
        d = parse_de_date(m.group(1))
        if not d or not ctx.in_window(d):
            continue
        title = clean(p.find("h1").get_text(" ", strip=True)) if p.find("h1") else "Monster-Meeting Rhein-Main"
        loc = re.search(r"findet (?:wieder )?(?:bei|im|in der)\s+(.{3,80}?)\s+statt", flat)
        venue = loc.group(1).replace(" im ", ", ") if loc else "TBA"
        talk = re.search(r"Vortrag:\s*(.{5,160}?)(?:\s+im Anschlu|\s+\d{2}:\d{2}|$)", flat)
        out.append(make_event(ctx, title=title, date_=d, time_=parse_time(m.group(2) or ""), venue_key=None,
                              venue=venue, city="Frankfurt", address="", url=url, source=SOURCE["url"],
                              category="tech", text_=f"Data & AI community meetup. {('Vortrag: ' + talk.group(1)) if talk else ''}"))
    return out
