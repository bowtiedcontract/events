"""Kurhaus Wiesbaden – official calendar. The page is JavaScript-rendered, so we render it
with Playwright, re-issue the page's own GraphQL SearchEvents query with a larger page size,
and read exact start times from each teaser's schedulings (Europe/Berlin)."""
import copy, json, re
from urllib.parse import urljoin

from .base import CONCERT, make_event, group_runs, playwright_page, skip, ScraperError, iso_to_berlin

SOURCE = {"id": "kurhaus_wiesbaden", "name": "Kurhaus Wiesbaden",
          "url": "https://kurhaus.wiesbaden.de/veranstaltungen/veranstaltungskalender"}
BASE = "https://kurhaus.wiesbaden.de"
_ID = re.compile(r"info-networking-event-(\d+)-(\d+)-\d+$")


def _search(pg):
    captured = []

    def on_request(req):
        raw = req.post_data or ""
        # "SearchEvents" only — "SearchEventsFacets" is the filter query and has no hits.
        if "graphql" in req.url and req.method == "POST" and '"SearchEvents"' in raw:
            try:
                op = json.loads(raw).get("operationName")
            except json.JSONDecodeError:
                return
            if op == "SearchEvents":
                captured.append(raw)

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
        if not r.ok:
            raise ScraperError(f"graphql HTTP {r.status}")
        payload = r.json()
        if payload.get("errors"):
            msg = payload["errors"][0].get("message", "graphql error")
            raise ScraperError(str(msg)[:200])
        data = payload["data"]["searchEvents"]
        results += data["results"]
        offset += 50
        if offset >= data["total"]:
            break
    return results


def _url(res, teaser):
    m = _ID.match(res.get("id") or "")
    if m:
        return f"{BASE}/info-networking-event?id={m.group(1)}&eventId={m.group(2)}"
    link = ((teaser.get("link") or {}).get("url")) or ""
    return urljoin(BASE, link) if link else SOURCE["url"]


def scrape(ctx):
    results = playwright_page(_search)
    if results and not any((r.get("teaser") or {}).get("schedulings") for r in results):
        raise ScraperError("search results have no schedulings")
    out = []
    for res in results:
        t = res.get("teaser") or {}
        if not str(res.get("id", "")).startswith("info-networking-event"):
            continue
        headline = t.get("headline") or ""
        if skip(headline):
            continue
        url = _url(res, t)
        for s in t.get("schedulings") or []:
            start = s.get("start") or ""
            if not start:
                continue
            d, tm = iso_to_berlin(start)
            end_d = None
            if s.get("end"):
                end_d = iso_to_berlin(s["end"])[0]
                if end_d <= d:
                    end_d = None
            if not s.get("hasStartTime"):
                tm = ""
            if not ctx.in_window(d, end_d):
                continue
            out.append(make_event(ctx, title=headline or "", date_=d, end_date=end_d, time_=tm,
                                  venue_key="Kurhaus Wiesbaden", url=url, source=SOURCE["url"],
                                  default_category=None, fallback="music", allowed=CONCERT,
                                  text_=f"{t.get('kicker', '')}. {t.get('text', '')}"))
    return group_runs(out)
