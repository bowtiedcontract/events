"""Schlachthof Wiesbaden – concert listing (static HTML) + detail pages (Beginn, VVK price, text)."""
import re
from .base import group_runs, soup, text, parse_de_date, parse_time, make_event, skip, clean

SOURCE = {"id": "schlachthof_wiesbaden", "name": "Schlachthof Wiesbaden",
          "url": "https://schlachthof-wiesbaden.de/konzert"}
HOUSE = ("KESSELHAUS", "HALLE", "RÄUCHERKAMMER", "SCHLACHTHOF", "KULTURPARK", "PLATZ")


def scrape(ctx):
    sp = soup(SOURCE["url"])
    out, seen = [], set()
    for a in sp.select('a[href*="/events/"]'):
        href = a["href"]
        divs = a.find_all("div", recursive=False)
        if href in seen or len(divs) < 2:
            continue
        seen.add(href)
        d = parse_de_date(text(divs[0]))
        if not d or not ctx.in_window(d):
            continue
        title = text(divs[1].find("span"))
        lines = [clean(x) for x in divs[1].get_text("\n").split("\n") if clean(x)]
        info = [l for l in lines[1:] if l != title]
        genre = next((l for l in info if re.search(r"\b(im|in der|in|auf dem)\s+[A-ZÄÖÜ]", l)), info[-1] if info else "")
        if "konzert" not in genre.lower() or skip(title, " ".join(info)):
            continue
        place = re.split(r"\b(?:im|in der|in|auf dem|INDER)\s*(?=[A-ZÄÖÜ]{3})", genre)[-1].strip()
        kw = {"venue_key": "Schlachthof Wiesbaden"}
        if place and place.split()[0] not in HOUSE:
            city = "Frankfurt" if "FRANKFURT" in place else "Mainz" if "MAINZ" in place else "Wiesbaden"
            name = place.title().replace(" Frankfurt", " Frankfurt").strip()
            kw = {"venue_key": None, "venue": name, "city": city, "address": ""}
        elif place:
            kw["room"] = place.title()
        # detail page: Beginn + price + description
        t, price, desc = "", "", ""
        try:
            dt = soup(href).get_text("\n", strip=True)
            i = dt.find("Einlass")
            block = dt[i:i + 300] if i >= 0 else ""
            m = re.search(r"Beginn\s*(\d{1,2}:\d{2})", block)
            t = m.group(1) if m else parse_time(block)
            m = re.search(r"VVK\s*€\s*([\d.,]+)", block)
            price = f"€{m.group(1)}" if m else ""
            j = dt.find("Termin im Kalender eintragen")
            desc = dt[j + 28:j + 1000] if j >= 0 else ""
        except Exception:  # noqa: BLE001 - listing data is still useful
            pass
        out.append(make_event(ctx, title=title, date_=d, time_=t, url=href, source=SOURCE["url"],
                              price=price, default_category="music", text_=f"{' '.join(info)}. {desc}", **kw))
    return group_runs(out)
