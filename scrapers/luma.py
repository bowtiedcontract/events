"""Luma (lu.ma) – city page for Frankfurt; events are embedded as JSON in __NEXT_DATA__."""
import json
from .base import soup, walk_dicts, iso_to_berlin, make_event, categorize, skip, ENGLISH_RE

SOURCE = {"id": "luma", "name": "Luma (Frankfurt)", "url": "https://lu.ma/frankfurt"}
CITIES = {"frankfurt": "Frankfurt", "wiesbaden": "Wiesbaden", "mainz": "Mainz", "darmstadt": "Darmstadt",
          "offenbach": "Offenbach", "eschborn": "Frankfurt"}


def scrape(ctx):
    sp = soup(SOURCE["url"])
    nd = sp.find("script", id="__NEXT_DATA__")
    if not nd:
        raise RuntimeError("__NEXT_DATA__ not found (page layout changed)")
    data = json.loads(nd.string)
    out, seen = [], set()
    for ev in walk_dicts(data):
        if not (ev.get("api_id", "").startswith("evt-") and ev.get("name") and ev.get("start_at")):
            continue
        if ev["api_id"] in seen:
            continue
        seen.add(ev["api_id"])
        geo = ev.get("geo_address_info") or {}
        full = geo.get("full_address") or geo.get("address") or ""
        city_raw = f"{geo.get('city', '')} {full}".lower()
        city = next((c for k, c in CITIES.items() if k in city_raw), None)
        if not city or ev.get("location_type") == "online":
            continue
        d, t = iso_to_berlin(ev["start_at"])
        end = iso_to_berlin(ev["end_at"])[0] if ev.get("end_at") else None
        if not ctx.in_window(d) or skip(ev["name"]):
            continue
        venue = geo.get("address") or full.split(",")[0] or "TBA"
        out.append(make_event(ctx, title=ev["name"], date_=d, time_=t, end_date=end if end and end != d else None,
                              venue_key=None, venue=venue, city=city, address=full,
                              url=f"https://lu.ma/{ev.get('url')}", source=SOURCE["url"],
                              category=categorize(ev["name"], "", None, fallback="general"),
                              english=True if ENGLISH_RE.search(ev["name"]) else None,
                              text_=ev["name"]))
    return out
