"""SCHIRN Kunsthalle Frankfurt. The programme page only prints 'Bis 10. Januar' for shows
already open, so date ranges are read from the WordPress exhibition posts. When a post has
no range, the exhibition page's schema.org Event (startDate/endDate) is used."""
import re
from datetime import date

from bs4 import BeautifulSoup

from .base import get, jsonld, is_event, parse_range, parse_de_date, make_event, clean, ScraperError

SOURCE = {"id": "schirn", "name": "SCHIRN Kunsthalle Frankfurt", "url": "https://www.schirn.de/ausstellungen/"}
API = "https://www.schirn.de/wp-json/wp/v2/exhibition"
_ISO = re.compile(r"\d{4}-\d{2}-\d{2}")


def _plain(html):
    sp = BeautifulSoup(html or "", "lxml")
    for tag in sp.find_all(["script", "style"]):
        tag.decompose()
    return clean(sp.get_text(" ", strip=True))


def _jsonld_range(url, title):
    """schema.org Event on the exhibition page. Prefer the one named like the show."""
    fallback = None
    for o in jsonld(get(url).text):
        if not is_event(o):
            continue
        start, end = str(o.get("startDate") or ""), str(o.get("endDate") or "")
        if not (_ISO.match(start) and _ISO.match(end)):
            continue
        span = date.fromisoformat(start[:10]), date.fromisoformat(end[:10])
        name = clean(o.get("name") or "").lower()
        if name and (name in title.lower() or title.lower() in name):
            return span
        fallback = fallback or span
    return fallback or (None, None)


def _posts():
    items, page = [], 1
    while page <= 10:
        r = get(API, params={"per_page": 100, "page": page, "_fields": "link,title,excerpt,content"},
                timeout=60)
        batch = r.json()
        if not isinstance(batch, list):
            raise ScraperError("unexpected exhibition API response")
        items += batch
        if page >= int(r.headers.get("X-WP-TotalPages") or 1):
            break
        page += 1
    if not items:
        raise ScraperError("exhibition API returned nothing")
    return items


def scrape(ctx):
    out, seen = [], set()
    for item in _posts():
        title = _plain((item.get("title") or {}).get("rendered"))
        link = item.get("link") or ""
        if len(title) < 3 or not link:
            continue
        head = _plain((item.get("content") or {}).get("rendered"))[:600]
        start, end = parse_range(head, ctx.today)
        if not start:
            # Running shows drop the opening day and only say "Bis 10. Januar".
            m = re.search(r"\bBis\s+(.+)$", head)
            end_guess = parse_de_date(m.group(1), ctx.today) if m else None
            if not end_guess or end_guess < ctx.today:
                continue
            start, end = _jsonld_range(link, title)
        if not start or not end or end < start or not ctx.in_window(start, end):
            continue
        key = (title.lower(), start.isoformat())
        if key in seen:
            continue
        seen.add(key)
        excerpt = _plain((item.get("excerpt") or {}).get("rendered"))
        out.append(make_event(ctx, title=title, date_=start, end_date=end, venue_key=SOURCE["name"],
                              url=link, source=SOURCE["url"], category="art",
                              text_=f"Ausstellung. {title}. {excerpt}"))
    return out
