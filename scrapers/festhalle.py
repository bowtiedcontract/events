"""Festhalle Frankfurt – the calendar page loads its events from Messe Frankfurt's event API in the
browser. We render the page with Playwright and read that JSON response (no API key in our code)."""
import re
from .base import CONCERT, soup, make_event, playwright_page, iso_to_berlin, skip, ScraperError

SOURCE = {"id": "festhalle", "name": "Festhalle Frankfurt",
          "url": "https://festhalle.messefrankfurt.com/frankfurt/de/veranstaltungen.html"}


def _capture(pg):
    hits = []

    def on_response(r):
        if "event-service" in r.url and "search" in r.url.lower():
            try:
                hits.extend(r.json().get("result", {}).get("hits", []))
            except Exception:  # noqa: BLE001
                pass

    pg.on("response", on_response)
    pg.goto(SOURCE["url"], wait_until="domcontentloaded")
    for _ in range(30):  # wait up to ~30 s for the API call
        if hits:
            break
        pg.wait_for_timeout(1000)
    pg.wait_for_timeout(1500)
    return hits


def scrape(ctx):
    hits = playwright_page(_capture)
    if not hits:
        raise ScraperError("event API response not captured")
    out, seen = [], set()
    for h in hits:
        ev = h.get("event", h)
        if str(ev.get("cancelled")).upper() in ("Y", "TRUE"):
            continue
        name = ev.get("eventname") or ""
        start = ev.get("startdate") or ""
        if not name or not start:
            continue
        d = start[:10]
        if not ctx.in_window(d, (ev.get("enddate") or "")[:10] or None) or skip(name):
            continue
        t = ""
        if "T" in start and not start.endswith("T00:00:00"):
            try:
                t = iso_to_berlin(start)[1]
            except ValueError:
                t = ""
        url = ev.get("interneturl") or SOURCE["url"]
        if url and not url.startswith("http"):
            url = "https://" + url.lstrip("/")
        key = (name, d)
        if key in seen:
            continue
        seen.add(key)
        fmt = ev.get("formatname") or ""
        if re.search(r"sport", fmt, re.I):
            continue
        if not t and url != SOURCE["url"]:
            try:  # the detail page has "Beginn: 20:00 Uhr"
                m = re.search(r"Beginn:\s*(\d{1,2}:\d{2})", soup(url).get_text(" ", strip=True))
                t = m.group(1).zfill(5) if m else ""
            except Exception:  # noqa: BLE001
                pass
        out.append(make_event(ctx, title=name, date_=d, time_=t if t != "00:00" else "", venue_key="Festhalle Frankfurt",
                              url=url, source=SOURCE["url"], default_category=None, fallback="music",
                              allowed=CONCERT, text_=f"{fmt}. {ev.get('subtitle') or ''}"))
    return out
