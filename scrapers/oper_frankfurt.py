"""Oper Frankfurt – monthly Spielplan pages (static HTML)."""
import re
from datetime import date
from .base import soup, text, absurl, make_event, group_runs, skip

SOURCE = {"id": "oper_frankfurt", "name": "Oper Frankfurt", "url": "https://oper-frankfurt.de/de/spielplan/"}
EXCLUDE = re.compile(r"opernkarussell|kinderbetreuung|führung|oper im dialog|sneak|oper für kinder|oper extra|friedman|oper leicht|familienworkshop", re.I)
PLACES = {"Bockenheimer Depot": ("Bockenheimer Depot", "Carlo-Schmid-Platz 1, 60325 Frankfurt am Main")}


def scrape(ctx):
    out = []
    for y, m in ctx.months(3):
        url = f"{SOURCE['url']}?datum={y}-{m:02d}"
        sp = soup(url)
        for el in sp.select(".repertoire-element"):
            day = re.search(r"\d{1,2}", text(el.select_one(".col-date")))
            if not day:
                continue
            d = date(y, m, int(day.group()))
            if not ctx.in_window(d):
                continue
            title = text(el.find("h3"))
            info = text(el.select_one(".col-element > div"))
            if EXCLUDE.search(title) or skip(title, text(el.select_one(".element-labels"))):
                continue
            meta = text(el.select_one(".meta"))
            tm = re.search(r"(\d{1,2})[.:](\d{2})\s*Uhr", meta)
            place = meta.split(",", 1)[1].strip() if "," in meta else "Opernhaus"
            a = el.find("a", href=True)
            detail = absurl(url, a["href"]) if a else url
            ticket = el.select_one("a[href*=eventim]")
            kw = {"venue_key": "Oper Frankfurt", "room": place}
            if "treffpunkt" in place.lower():
                continue
            if "alte oper" in place.lower():
                kw = {"venue_key": "Alte Oper Frankfurt"}
            elif place in PLACES:
                kw["address"] = PLACES[place][1]
            out.append(make_event(ctx, title=title, date_=d, time_=f"{int(tm.group(1)):02d}:{tm.group(2)}" if tm else "",
                                  url=ticket["href"] if ticket else detail, source=detail,
                                  default_category="classical", text_=info, **kw))
    return group_runs(out)
