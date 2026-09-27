"""Hessisches Staatstheater Wiesbaden – monthly calendar with schema.org Event microdata."""
from .base import skip, soup, text, absurl, make_event, group_runs, iso_to_berlin

SOURCE = {"id": "staatstheater_wiesbaden", "name": "Hessisches Staatstheater Wiesbaden",
          "url": "https://www.staatstheater-wiesbaden.de/spielplan/kalender/"}
KEEP = ("konzert", "musiktheater", "tanz", "oper", "ballett")


def scrape(ctx):
    out = []
    for y, m in ctx.months(3):
        url = f"{SOURCE['url']}{y}-{m:02d}/"
        sp = soup(url)
        for p in sp.select("div.performance[itemtype*=Event]"):
            cat = text(p.select_one(".performance__category")).rstrip(":").strip()
            if not any(k in cat.lower() for k in KEEP):
                continue
            sd = p.select_one("meta[itemprop=startDate]")
            if not sd:
                continue
            d, t = iso_to_berlin(sd["content"])
            if not ctx.in_window(d):
                continue
            title = text(p.select_one(".performance__title")).rstrip(":").strip()
            if skip(title):
                continue
            stage = text(p.select_one(".performance__stage")).rstrip(":").strip()
            author = text(p.select_one(".performance__authorcomposer"))
            link = p.select_one("a[href*='/spielplan/kalender/']")
            ticket = p.select_one("a.ticketbutton__button")
            price = text(p.select_one(".ticketbutton__info"))
            detail = absurl(url, link["href"]) if link else url
            if "kurhaus" in stage.lower():
                kw = dict(venue_key="Kurhaus Wiesbaden")
            else:
                kw = dict(venue_key="Hessisches Staatstheater Wiesbaden", venue="Hessisches Staatstheater",
                          room=stage or None)
            booking = ticket["href"] if ticket and ticket.get("href", "").startswith("http") else detail
            out.append(make_event(ctx, title=title, date_=d, time_=t, url=booking,
                                  source=detail, price=price if "€" in price else "",
                                  default_category="classical", text_=f"{cat}. {author}", **kw))
    return group_runs(out)
