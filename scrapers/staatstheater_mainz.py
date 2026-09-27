"""Staatstheater Mainz – monthly overview pages (static HTML)."""
import re
from datetime import date
from .base import soup, text, make_event, group_runs, skip

SOURCE = {"id": "staatstheater_mainz", "name": "Staatstheater Mainz",
          "url": "https://www.staatstheater-mainz.com/uebersicht/oktober"}
MONTH_SLUGS = ["januar", "februar", "maerz", "april", "mai", "juni", "juli", "august",
               "september", "oktober", "november", "dezember"]
KEEP = ("oper", "konzert", "ballett", "tanz", "musiktheater", "musical")


def scrape(ctx):
    out = []
    for y, m in ctx.months(3):
        url = f"https://www.staatstheater-mainz.com/uebersicht/{MONTH_SLUGS[m - 1]}"
        sp = soup(url)
        for div in sp.select("div[id^=t20]"):
            mid = re.match(r"t(\d{4})(\d{2})(\d{2})", div["id"])
            d = date(int(mid.group(1)), int(mid.group(2)), int(mid.group(3)))
            if not ctx.in_window(d):
                continue
            raw = div.get_text(" ", strip=True)
            arrow = div.find(string=re.compile("→"))
            genre_a = arrow.find_next("a") if arrow else None
            genre = text(genre_a)
            if not any(k in genre.lower() for k in KEEP):
                continue
            tm = re.search(r"(\d{1,2}:\d{2})(?:\s*[-–]\s*\d{1,2}:\d{2})?\s*→", raw)
            a = div.select_one("a.titel")
            if not a:
                continue
            title = text(a)
            if skip(title) or re.search(r"im gespräch|reingehört|einführung", title, re.I):
                continue
            sub = text(div.find("p"))
            stage = text(div.select_one(".single_location"))
            ticket = div.select_one("a.kk_link")
            out.append(make_event(ctx, title=title, date_=d, time_=tm.group(1).zfill(5) if tm else "",
                                  venue_key="Staatstheater Mainz", room=stage or None,
                                  url=ticket["href"] if ticket else a["href"], source=a["href"],
                                  default_category="classical", text_=f"{genre}. {sub}"))
    return group_runs(out)
