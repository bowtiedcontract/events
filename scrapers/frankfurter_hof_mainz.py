"""Frankfurter Hof Mainz (mainzplus: also Rheingoldhalle, Schloss, Zitadelle) – ztix event table +
detail pages, which carry a genre tag like 'Konzerte: Klassik' and the reservix booking link."""
import re
from datetime import date
from .base import soup, text, absurl, make_event, group_runs, skip, clean

SOURCE = {"id": "frankfurter_hof_mainz", "name": "Frankfurter Hof Mainz / Rheingoldhalle",
          "url": "https://www.frankfurter-hof-mainz.de/programm-tickets/veranstaltungsuebersicht/"}


def scrape(ctx):
    sp = soup(SOURCE["url"])
    out = []
    for tr in sp.select("table.ztixeventlist tr"):
        tm = tr.find("time")
        a = tr.select_one("a[href*='/programm-tickets/details/']")
        if not tm or not a:
            continue
        dd, mm, yy = tm["datetime"].split("-")
        d = date(int(yy), int(mm), int(dd))
        if not ctx.in_window(d):
            continue
        tds = tr.find_all("td")
        t = text(tds[1]) if len(tds) > 1 else ""
        title = a.get("title") or text(a)
        loc = [clean(x).strip(", ") for x in tds[-1].get_text("\n").split("\n")
               if clean(x).strip(", ") and clean(x) != clean(text(a))]
        place = loc[0] if loc else "Frankfurter Hof"
        if skip(title):
            continue
        url = absurl(SOURCE["url"], a["href"])
        dsp = soup(url)
        body = dsp.get_text("\n", strip=True)
        m = re.search(r"\n([A-ZÄÖÜ][\wäöüß &/-]{2,30}):\n([^\n]{2,40})\n", body)
        genre = f"{m.group(1)}: {m.group(2)}" if m else ""
        if not genre.lower().startswith("konzert"):
            continue  # cabaret, comedy, readings, kids' shows etc. are not in scope
        res = dsp.select_one("a[href*='reservix']")
        i = body.find("Programm & Tickets", body.find("Frankfurter Hof Mainz\nProgramm & Tickets"))
        desc = body[i + 18:i + 1000] if i >= 0 else ""
        if "Rheingoldhalle" in place:
            kw = {"venue_key": "Rheingoldhalle Mainz"}
        elif "Frankfurter Hof" in place:
            kw = {"venue_key": "Frankfurter Hof Mainz"}
        else:
            kw = {"venue_key": None, "venue": place, "city": "Mainz", "address": ", ".join(loc[1:])}
        out.append(make_event(ctx, title=title, date_=d, time_=t if re.fullmatch(r"\d{2}:\d{2}", t) else "",
                              url=res["href"] if res else url, source=url,
                              default_category="classical" if "klassik" in genre.lower() else "music",
                              text_=f"{genre}. {desc}", **kw))
    return group_runs(out)
