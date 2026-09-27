"""hr-Sinfonieorchester – monthly concert calendar pages (static HTML)."""
from .base import soup, text, parse_time, make_event, group_runs, skip

SOURCE = {"id": "hr_sinfonieorchester", "name": "hr-Sinfonieorchester",
          "url": "https://www.hr-sinfonieorchester.de/konzerte/konzertkalender/index.html"}
VENUES = {"alte oper": "Alte Oper Frankfurt"}


def scrape(ctx):
    out = []
    for y, m in ctx.months(3):
        url = f"https://www.hr-sinfonieorchester.de/konzerte/veranstaltungen-110~_month-{y}-{m:02d}.html"
        sp = soup(url)
        for sec in sp.select("section[id]"):
            d = sec["id"]
            if len(d) != 10 or not d[:4].isdigit() or not ctx.in_window(d):
                continue
            for t in sec.select(".c-eventTeaser"):
                title = text(t.select_one(".c-eventTeaser__headline"))
                sub = text(t.select_one(".c-eventTeaser__subHeadline"))
                city = text(t.select_one(".c-eventTeaser__venue strong"))
                hall = text(t.select_one(".c-eventInstant__address"))
                if skip(title, sub) or ("frankfurt" not in city.lower() and "wiesbaden" not in city.lower()
                                        and "darmstadt" not in city.lower() and "mainz" not in city.lower()):
                    continue
                a = t.select_one("a.c-teaser__headlineLink")
                detail = a["href"] if a else url
                if "alte oper" in hall.lower():
                    kw = {"venue_key": "Alte Oper Frankfurt", "room": hall.replace("Alte Oper", "").strip(" ,–-") or None}
                elif "sendesaal" in hall.lower():
                    kw = {"venue_key": "hr-Sinfonieorchester", "venue": "hr-Sendesaal",
                          "address": "Bertramstr. 8, 60320 Frankfurt am Main"}
                else:
                    kw = {"venue_key": None, "venue": hall or city, "city": city.replace(" am Main", ""), "address": ""}
                out.append(make_event(ctx, title=f"hr-Sinfonieorchester: {title}" if "hr-" not in title else title,
                                      date_=d, time_=parse_time(text(t.select_one(".c-eventTeaser__startTime"))),
                                      url=detail, source=detail, default_category="classical",
                                      text_=f"{sub}. {text(t.select_one('.mediaInfo__label'))}", **kw))
    return group_runs(out)
