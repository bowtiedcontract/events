"""Studio Bloc Wiesbaden – courses, workshops and competitions.

The course pages embed a dr-plano booking widget (data-id / data-backend-url).
The widget's course list and month calendars are public JSON. Birthday parties
and the overnight "hotel" product are private bookings, so they are skipped.
"""
import html as htmlmod
import re
from datetime import datetime

from .base import BERLIN, ScraperError, clean, get, make_event, series

SOURCE = {"id": "studiobloc_wiesbaden", "name": "Studio Bloc Wiesbaden",
          "url": "https://wiesbaden.studiobloc.de/angebote/"}
WIDGET_PAGE = "https://wiesbaden.studiobloc.de/angebote/erwachsene/einfuehrungskurs/"
SKIP = re.compile(r"geburtstag|birthday|\bhotel\b|gutschein", re.I)
# First match wins. Family intro is a different page from the adult intro.
PAGES = [
    (re.compile(r"familien", re.I), "https://wiesbaden.studiobloc.de/angebote/kinder/"),
    (re.compile(r"einführ", re.I), "https://wiesbaden.studiobloc.de/angebote/erwachsene/einfuehrungskurs/"),
    (re.compile(r"basics\s*\+|basic\s*plus", re.I), "https://wiesbaden.studiobloc.de/angebote/erwachsene/bloc-basic-plus/"),
    (re.compile(r"bloc basic", re.I), "https://wiesbaden.studiobloc.de/angebote/erwachsene/bloc-basic/"),
]


def _euro(n):
    n = float(n)
    return f"€{int(round(n))}" if abs(n - round(n)) < 0.05 else f"€{n:.2f}"


def _plain(s):
    s = htmlmod.unescape(re.sub(r"<[^>]+>", " ", s or ""))
    return clean(s)


def _widget():
    page = get(WIDGET_PAGE).text
    cid = re.search(r'data-id="(\d+)"', page)
    backend = re.search(r'data-backend-url="([^"]+)"', page)
    if not cid:
        raise ScraperError("dr-plano booking widget id not found on the course page")
    return cid.group(1), (backend.group(1).rstrip("/") if backend else "https://backend.dr-plano.de")


def _months(ctx):
    y, m = ctx.today.year, ctx.today.month
    last = (ctx.until.year, ctx.until.month)
    out = []
    while (y, m) <= last and len(out) < 6:
        ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
        start = int(datetime(y, m, 1, tzinfo=BERLIN).timestamp() * 1000)
        end = int(datetime(ny, nm, 1, tzinfo=BERLIN).timestamp() * 1000)
        out.append((start, end))
        y, m = ny, nm
    return out


def _page_for(title):
    for rx, url in PAGES:
        if rx.search(title or ""):
            return url
    return SOURCE["url"]


def _json(url):
    return get(url, headers={"Accept": "application/json"}).json()


def scrape(ctx):
    cid, backend = _widget()
    courses = (_json(f"{backend}/courses_list?id={cid}").get("courses")) or []
    if not isinstance(courses, list):
        raise ScraperError("dr-plano course list had an unexpected shape")
    out, seen = [], set()
    for course in courses:
        title = _plain(course.get("title"))
        sub = _plain(course.get("subtitle"))
        if not title or SKIP.search(f"{title} {sub}"):
            continue
        runs = []
        for start_ms, end_ms in _months(ctx):
            try:
                chunk = _json(f"{backend}/courses_dates?id={course['id']}&start={start_ms}&end={end_ms}")
            except ScraperError:
                continue
            if not isinstance(chunk, list):
                continue
            for item in chunk:
                sessions = []
                for slot in item.get("dateList") or []:
                    if not slot.get("start"):
                        continue
                    dt = datetime.fromtimestamp(slot["start"] / 1000, BERLIN)
                    if ctx.in_window(dt.date()):
                        sessions.append((dt.date(), dt.strftime("%H:%M")))
                if not sessions:
                    continue
                key = tuple(sorted(set(sessions)))
                if key in seen:
                    continue
                seen.add(key)
                runs.append(key)
        if not runs:
            continue
        try:
            detail = _json(f"{backend}/courses_detail?id={course['id']}")
        except ScraperError:
            detail = {}
        fees = [fee.get("fee") for tariff in (detail.get("tariffs") or []) for fee in (tariff.get("fees") or [])
                if isinstance(fee.get("fee"), (int, float))]
        price = _euro(min(fees)) if fees else ""
        label = title if not sub or sub.lower() in title.lower() else f"{title}: {sub}"
        blurb = _plain(detail.get("description"))
        url = _page_for(title)
        for sessions in runs:
            e = make_event(ctx, title=label, date_=sessions[0][0], time_=sessions[0][1],
                           venue_key="Studio Bloc Wiesbaden", url=url, source=SOURCE["url"],
                           price=price, category="climbing",
                           text_=f"Bouldering course at Studio Bloc Wiesbaden. {label}. {blurb}")
            e = series(e, sessions, url=url,
                       key=f"studiobloc-{course['id']}-{sessions[0][0].isoformat()}-{sessions[0][1]}")
            if e:
                out.append(e)
    return out
