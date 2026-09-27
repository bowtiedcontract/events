"""Eventbrite – search result pages for the region. Each page embeds its results as JSON
(window.__SERVER_DATA__), with start date/time, venue address and online flag."""
import re
from .base import get, find_json_after, walk_dicts, make_event, categorize, skip, ENGLISH_RE

SOURCE = {"id": "eventbrite", "name": "Eventbrite (Rhein-Main searches)",
          "url": "https://www.eventbrite.com/d/germany--frankfurt-am-main/networking/"}
SEARCHES = [
    "https://www.eventbrite.com/d/germany--frankfurt-am-main/networking/",
    "https://www.eventbrite.com/d/germany--frankfurt-am-main/startup/",
    "https://www.eventbrite.com/d/germany--frankfurt-am-main/ai/",
    "https://www.eventbrite.com/d/germany--frankfurt-am-main/science-and-tech--events/",
    "https://www.eventbrite.com/d/germany--frankfurt-am-main/english-comedy/",
    "https://www.eventbrite.com/d/germany--frankfurt-am-main/expat/",
    "https://www.eventbrite.com/d/germany--wiesbaden/events/",
    "https://www.eventbrite.com/d/germany--mainz/events/",
    "https://www.eventbrite.com/d/germany--darmstadt/business--events/",
]
CITIES = {"frankfurt": "Frankfurt", "wiesbaden": "Wiesbaden", "mainz": "Mainz", "darmstadt": "Darmstadt",
          "offenbach": "Offenbach", "eschborn": "Frankfurt", "bad homburg": "Frankfurt"}
# only keep formats that fit the dashboard (business/tech/networking/culture), not e.g. dating or parties
DROP = re.compile(r"speed ?dating|singles|party|clubbing|rave|yoga|meditation|webinar|online|semester ?opening|studance|ersti|night out|bingo|megamarsch|crypto signals|forex|trading course", re.I)


def scrape(ctx):
    out, seen, errors = [], set(), 0
    for url in SEARCHES:
        try:
            html = get(url).text
        except Exception:  # noqa: BLE001 - one failed search shouldn't lose the others
            errors += 1
            continue
        data = find_json_after(html, "window.__SERVER_DATA__ =") or {}
        for ev in walk_dicts(data):
            if "eventbrite_event_id" not in ev or not ev.get("start_date") or not ev.get("name"):
                continue
            eid = ev["eventbrite_event_id"]
            if eid in seen or ev.get("is_online_event") or ev.get("is_cancelled"):
                continue
            seen.add(eid)
            v = ev.get("primary_venue") or {}
            addr = (v.get("address") or {})
            city_raw = (addr.get("city") or "").lower()
            city = next((c for k, c in CITIES.items() if k in city_raw), None)
            if not city or not ctx.in_window(ev["start_date"], ev.get("end_date")):
                continue
            title = ev["name"]
            summary = ev.get("summary") or ""
            tags = " ".join(t.get("display_name", "") for t in ev.get("tags", []) if isinstance(t, dict))
            if DROP.search(f"{title} {summary}") or skip(title):
                continue
            cat = categorize(title, f"{summary} {tags}", None)
            out.append(make_event(ctx, title=title, date_=ev["start_date"], time_=ev.get("start_time", ""),
                                  venue_key=None, venue=v.get("name") or addr.get("address_1") or "TBA",
                                  city=city, address=addr.get("localized_address_display", ""),
                                  url=ev.get("url", ""), source=url, category=cat,
                                  english=bool(ENGLISH_RE.search(f"{title} {summary}")),
                                  text_=f"{summary} Tags: {tags}"))
    if errors == len(SEARCHES):
        raise RuntimeError("all Eventbrite searches failed")
    return out
