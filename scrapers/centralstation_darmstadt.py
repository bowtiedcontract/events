"""Centralstation Darmstadt – programme list via month AJAX (HTML redesign).

The public programme page loads events through admin-ajax.php
(`filter_events_by_month`). We keep the `konzert` category only (jazz /
classical / live music all sit there); comedy, parties and literature are
skipped, matching the previous scraper filter.
"""
import re

import requests
from bs4 import BeautifulSoup

from .base import HEADERS, ScraperError, get, make_event, parse_de_date, parse_time, skip, text

SOURCE = {"id": "centralstation_darmstadt", "name": "Centralstation Darmstadt",
          "url": "https://www.centralstation-darmstadt.de/programm"}
KEEP = {"konzert"}
AJAX = "https://centralstation-darmstadt.de/wp-admin/admin-ajax.php"


def scrape(ctx):
    page = get(SOURCE["url"])
    nonce_m = re.search(r'eventFilterNonce\s*=\s*"([^"]+)"', page.text)
    comp_m = re.search(r"events-container-calendar-block-block_[a-f0-9]+", page.text)
    if not nonce_m or not comp_m:
        raise ScraperError("Centralstation filter nonce/component id missing")
    nonce, component_id = nonce_m.group(1), comp_m.group(0)

    session = requests.Session()
    session.headers.update(HEADERS)
    # href -> accumulated fields from desktop + mobile rows
    by_href = {}
    for year, month in ctx.months(3):
        r = session.post(AJAX, data={
            "action": "filter_events_by_month",
            "month": f"{year}-{month:02d}",
            "category": "konzert",
            "component_id": component_id,
            "nonce": nonce,
        }, timeout=30)
        try:
            payload = r.json()
        except Exception as ex:  # noqa: BLE001
            raise ScraperError(f"Centralstation AJAX JSON failed for {year}-{month:02d}: {ex}") from ex
        if not payload.get("success"):
            raise ScraperError(f"Centralstation AJAX unsuccessful for {year}-{month:02d}")
        frag = (payload.get("data") or {}).get("html") or ""
        sp = BeautifulSoup(frag, "lxml")
        for row in sp.select("div.event-row"):
            cat = (row.get("data-event-category") or "").lower()
            if cat not in KEEP:
                continue
            a = row.select_one("a[href*='/event/']")
            if not a:
                continue
            href = a["href"]
            flat = text(row)
            rec = by_href.setdefault(href, {"url": href, "category": cat})
            mdate = re.search(r"(\d{1,2}\.\d{1,2}\.\d{4})", flat)
            if mdate:
                rec["date"] = parse_de_date(mdate.group(1))
            mtime = re.search(r"(\d{1,2}:\d{2})\s*Uhr", flat)
            if mtime:
                rec["time"] = parse_time(mtime.group(1))
            title_el = a.select_one("div.text-2xl") or a.select_one("div.font-bold")
            title = text(title_el)
            if title:
                rec["title"] = title
            sub_el = a.select_one("div.mt-2") or a.select_one("div.line-clamp-3")
            sub = text(sub_el)
            if sub:
                rec["sub"] = sub

    out = []
    for rec in by_href.values():
        title = rec.get("title") or ""
        d = rec.get("date")
        if not title or not d or not ctx.in_window(d):
            continue
        sub = rec.get("sub", "")
        if skip(title, sub):
            continue
        out.append(make_event(
            ctx, title=title, date_=d, time_=rec.get("time", ""),
            venue_key="Centralstation Darmstadt", url=rec["url"], source=SOURCE["url"],
            default_category="music",
            text_=f"{rec.get('category', 'konzert')}. {sub}".strip(),
        ))
    return out
