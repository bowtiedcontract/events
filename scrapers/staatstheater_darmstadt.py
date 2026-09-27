"""Staatstheater Darmstadt – full-season Spielplan page (static HTML, one <article> per date)."""
import re
from .base import soup, text, absurl, iso_to_berlin, make_event, group_runs, skip

SOURCE = {"id": "staatstheater_darmstadt", "name": "Staatstheater Darmstadt",
          "url": "https://www.staatstheater-darmstadt.de/spielplan/"}
KEEP = re.compile(r"\boper\b|kurzoper|konzert|ballett|choreogra|musical|sinfoni|kammermusik|jazz|operette|liederabend|werke von", re.I)
DROP = re.compile(r"kinder|familie|minikonzert|teddybär|workshop|antanzen|tanzklub|an der bar|\bführung|theaterführung|infotreffen|lauschangriff|jam session", re.I)


def scrape(ctx):
    sp = soup(SOURCE["url"], timeout=60)
    out = []
    for art in sp.select("article.termin"):
        tm = art.find("time", datetime=True)
        if not tm:
            continue
        d, t = iso_to_berlin(tm["datetime"])
        if not ctx.in_window(d):
            continue
        title = text(art.select_one(".termin__title"))
        details = text(art.select_one(".termin__details"))
        if not KEEP.search(f"{title} {details}") or DROP.search(f"{title} {details}") or skip(title, details):
            continue
        spans = art.select(".termin__meta > span")
        stage = text(spans[0]) if spans else ""
        a = art.select_one("a.termin__anchor")
        url = absurl(SOURCE["url"], a["href"]) if a else SOURCE["url"]
        price = re.search(r"\d+,\d{2}\s*€(?:\s*bis\s*\d+,\d{2}\s*€)?", details)
        out.append(make_event(ctx, title=title, date_=d, time_=t, venue_key="Staatstheater Darmstadt",
                              room=stage or None, url=url, source=url, price=price.group() if price else "",
                              default_category="classical", text_=details))
    return group_runs(out)
