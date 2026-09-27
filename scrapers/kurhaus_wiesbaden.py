"""Kurhaus Wiesbaden – official calendar. The page is JavaScript-rendered (GraphQL search), so we
render it with Playwright, re-issue the page's own search query with a larger page size, then read
exact dates from the public per-event iCal endpoint."""
import copy, json
from urllib.parse import quote

from .base import CONCERT, get, parse_ics, make_event, group_runs, playwright_page, skip, ScraperError

SOURCE = {"id": "kurhaus_wiesbaden", "name": "Kurhaus Wiesbaden",
          "url": "https://kurhaus.wiesbaden.de/veranstaltungen/veranstaltungskalender"}
BASE = "https://kurhaus.wiesbaden.de"


def _search(pg):
    captured = []

    def on_request(req):
        if "graphql" in req.url and req.method == "POST" and '"Search"' in (req.post_data or ""):
            captured.append(req.post_data)

    pg.on("request", on_request)
    pg.goto(SOURCE["url"], wait_until="networkidle")
    if not captured:
        raise ScraperError("no GraphQL search request seen")
    body = json.loads(captured[0])
    results, offset = [], 0
    while offset < 200:
        b = copy.deepcopy(body)
        si = b["variables"]["searchInput"]
        si["offset"], si["limit"] = offset, 50
        r = pg.request.post(BASE + "/api/graphql/", data=json.dumps(b),
                            headers={"content-type": "application/json"})
        data = r.json()["data"]["search"]
        results += data["results"]
        offset += 50
        if offset >= data["total"]:
            break
    return results


def scrape(ctx):
    results = playwright_page(_search)
    out = []
    for res in results:
        t = res.get("teaser") or {}
        if not res.get("id", "").startswith("info-networking-event"):
            continue
        q = json.dumps({"filter": [{"type": "id", "values": [res["id"]]}], "limit": 1})
        ics = parse_ics(get(BASE + "/api/ical/search?query=" + quote(q)).text)
        num = res["id"].rsplit("-", 1)[-1]
        url = f"{BASE}/info-networking-event?id={num}"
        for v in ics:
            if not ctx.in_window(v["date"], v.get("end")) or skip(t.get("headline", "")):
                continue
            title = t.get("headline") or v.get("SUMMARY", "")
            out.append(make_event(ctx, title=title, date_=v["date"], time_=v.get("time", ""),
                                  venue_key="Kurhaus Wiesbaden", url=url, source=SOURCE["url"],
                                  default_category=None, fallback="music", allowed=CONCERT,
                                  text_=f"{t.get('kicker', '')}. {t.get('text', '')} {v.get('DESCRIPTION', '')[:600]}"))
    return group_runs(out)
