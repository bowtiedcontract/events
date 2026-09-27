"""Mainz Klassik (Meisterkonzerte, mostly Rheingoldhalle) – Squarespace event collection JSON."""
from datetime import datetime
from bs4 import BeautifulSoup
from .base import get, make_event, BERLIN, skip

SEASONAL = True  # zero events is normal outside the season/between runs
SOURCE = {"id": "mainz_klassik", "name": "Mainz Klassik – Meisterkonzerte",
          "url": "https://www.mainz-klassik.de/alle-meisterkonzerte"}


def scrape(ctx):
    data = get(SOURCE["url"] + "?format=json").json()
    out = []
    for it in data.get("upcoming", []):
        dt = datetime.fromtimestamp(int(it["startDate"]) / 1000, BERLIN)
        if not ctx.in_window(dt.date()) or skip(it.get("title", "")):
            continue
        loc = it.get("location") or {}
        place = loc.get("addressTitle") or ""
        url = "https://www.mainz-klassik.de" + it.get("fullUrl", "")
        excerpt = BeautifulSoup(it.get("excerpt") or "", "lxml").get_text(" ", strip=True)
        if "rheingold" in place.lower() or not place:
            kw = {"venue_key": "Rheingoldhalle Mainz"}
        else:
            addr = ", ".join(x for x in (loc.get("addressLine1"), loc.get("addressLine2")) if x)
            kw = {"venue_key": None, "venue": place + (" Mainz" if "mainz" not in place.lower() else ""),
                  "city": "Mainz", "address": addr}
        out.append(make_event(ctx, title=it["title"], date_=dt.date(), time_=dt.strftime("%H:%M"), url=url,
                              source=SOURCE["url"], category="classical", text_=f"Meisterkonzert. {excerpt}", **kw))
    return out
