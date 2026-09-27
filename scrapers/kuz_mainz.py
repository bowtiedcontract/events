"""KUZ Kulturzentrum Mainz – programme page (static HTML, one block per event)."""
import re
from .base import soup, text, absurl, parse_de_date, parse_time, make_event, skip

SOURCE = {"id": "kuz_mainz", "name": "KUZ Kulturzentrum Mainz",
          "url": "https://www.kulturzentrummainz.de/programm/veranstaltungen"}


def scrape(ctx):
    sp = soup(SOURCE["url"])
    out = []
    for div in sp.select("div[data-month][data-types]"):
        types = div["data-types"]
        if not re.search(r"Konzert|Märkte", types):
            continue
        ds = text(div.select_one(".date"))
        d = parse_de_date(ds)
        if not d or not ctx.in_window(d):
            continue
        title = text(div.select_one("h2.title"))
        sub = text(div.select_one(".subtitle"))
        meta = text(div.select_one(".meta"))
        if skip(title, sub):
            continue
        room = meta.split("—")[0].strip()
        price = re.search(r"VVK\s*([\d.,]+\s*€)", meta)
        info = div.select_one("a[href*='/infos/']")
        ticket = div.select_one("a.btn-ticket-new-window")
        url = absurl(SOURCE["url"], info["href"]) if info else SOURCE["url"]
        out.append(make_event(ctx, title=title, date_=d, time_=parse_time(ds.split("—")[-1]),
                              venue_key="KUZ Kulturzentrum Mainz",
                              room=room if room and room.upper() != "KUZ" else None,
                              url=ticket["href"] if ticket and ticket["href"].startswith("http") else url,
                              source=url, price=f"VVK {price.group(1)}" if price else "",
                              default_category="general" if "Märkte" in types else "music",
                              text_=f"{types}. {sub}"))
    return out
