"""Batschkapp Frankfurt – event list (server-rendered Next.js HTML)."""
import re
from .base import soup, text, absurl, parse_de_date, make_event, skip

SOURCE = {"id": "batschkapp", "name": "Batschkapp", "url": "https://www.batschkapp.net/batschkapp"}


def scrape(ctx):
    sp = soup(SOURCE["url"])
    out, seen = [], set()
    for a in sp.select('a[href^="/events/"]'):
        if a["href"] in seen or not a.select_one(".eventlistitemheading"):
            continue
        seen.add(a["href"])
        if text(a.select_one(".rubrik")).lower() != "konzert":
            continue
        d = parse_de_date(text(a.select_one(".datum")).replace(" ", ""))
        if not d or not ctx.in_window(d):
            continue
        title = text(a.select_one(".eventlistitemheading"))
        sub = text(a.select_one(".eventlistitemsubheading"))
        badges = text(a.select_one(".eventlistiteminfos"))
        if skip(title, badges):
            continue
        tm = re.search(r"Beginn:\s*(\d{1,2}:\d{2})", text(a.select_one(".beginn")))
        venue = text(a.select_one(".eventitem-venue"))
        url = absurl(SOURCE["url"], a["href"])
        kw = {"venue_key": "Batschkapp"}
        if venue and "batschkapp" not in venue.lower():
            kw = {"venue_key": None, "venue": venue, "city": "Frankfurt",
                  "address": text(a.select_one(".eventitem-address"))}
        out.append(make_event(ctx, title=title.title() if title.isupper() else title, date_=d,
                              time_=tm.group(1).zfill(5) if tm else "", url=url, source=SOURCE["url"],
                              default_category="music", text_=f"{sub}. {badges}. {text(a.select_one('.eventlist-presenter'))}", **kw))
    return out
