"""Kletterkiste / DAV Mainz – courses, the open Klettertreff, and Grip & Grow.

Indoor courses are booked through the Yolawo widget on the course page
(api.yolawo.de). The interest-list widget is not a calendar and is ignored.
The Klettertreff page states the cadence (every other Thursday, with the next
dates written out, from about 19:00). Grip & Grow is the first Monday of the
month at 18:00 at Wiesbadener Nordwand, except public holidays.
"""
import re
from datetime import date, timedelta
from html import unescape

from .base import (MONTH_RE, ScraperError, absurl, clean, get, iso_to_berlin, make_event,
                   parse_de_date, series, soup, text)

SOURCE = {"id": "kletterkiste_mainz", "name": "Kletterkiste Mainz",
          "url": "https://www.kletterkiste-mainz.de/kletterkurse"}
HOME = "https://www.kletterkiste-mainz.de/"
TREFF = "https://www.kletterkiste-mainz.de/klettertreff"
GRIP = "https://www.kletterkiste-mainz.de/artikel/Grip--Grow/142350"
API = "https://api.yolawo.de"
# Nationwide holidays. Hesse autumn/winter additions in this window are not Mondays.
HOLIDAYS = {(1, 1), (5, 1), (10, 3), (12, 25), (12, 26)}
SKIP_PAGE = re.compile(r"film|unfall|statistik|routenliste", re.I)


def _euro(cents):
    if cents is None:
        return ""
    value = cents / 100
    return f"€{int(value)}" if value == int(value) else f"€{value:.2f}"


def _price(pricing):
    lo = ((pricing or {}).get("lowestPrice") or {}).get("amount")
    hi = ((pricing or {}).get("highestPrice") or {}).get("amount")
    if lo and hi and lo != hi:
        return f"{_euro(lo)}–{_euro(hi)}"
    return _euro(lo or hi)


def _json(url):
    return get(url, headers={"Accept": "application/json"}).json()


def _yolawo(ctx):
    page = get(SOURCE["url"]).text
    ids = re.findall(r"widgets\.yolawo\.de/w/([0-9a-f]{24})", page)
    if not ids:
        raise ScraperError("Yolawo course widget not found on the Kletterkiste course page")
    out = []
    for wid in dict.fromkeys(ids):
        meta = _json(f"{API}/widgets/{wid}")
        if re.search(r"interessent", meta.get("name") or "", re.I):
            continue
        for oid in (meta.get("offers") or {}).get("ids") or []:
            try:
                offer = _json(f"{API}/widgets/{wid}/offers/{oid}")
                books = _json(f"{API}/widgets/{wid}/offers/{oid}/bookables")
            except ScraperError:
                continue
            if offer.get("canceled") or not isinstance(books, list):
                continue
            sessions = []
            for book in books:
                if book.get("canceled"):
                    continue
                for slot in book.get("dates") or []:
                    if slot.get("canceled") or not slot.get("start"):
                        continue
                    d, t = iso_to_berlin(slot["start"])
                    if ctx.in_window(d):
                        sessions.append((d, t))
            if not sessions:
                continue
            title = clean(re.sub(r"\s*Nr\.\s*\d+", "", unescape(offer.get("title") or "Kletterkurs")))
            price = _price(offer.get("pricing"))
            e = make_event(ctx, title=title, date_=sessions[0][0], time_=sessions[0][1],
                           venue_key="Kletterkiste Mainz", url=SOURCE["url"], source=SOURCE["url"],
                           price=price, category="climbing",
                           text_=f"Indoor climbing course at Kletterkiste, DAV Mainz. {title}.")
            e = series(e, sessions, url=SOURCE["url"], key=f"kletterkiste-{oid}")
            if e:
                out.append(e)
    return out


def _clock(flat, default):
    m = re.search(r"ab\s+(?:ca\.?\s*)?(\d{1,2})(?::(\d{2}))?\s*uhr", flat, re.I)
    if not m:
        m = re.search(r"(\d{1,2}):(\d{2})\s*uhr", flat, re.I)
    if not m:
        return default
    return f"{int(m.group(1)):02d}:{int(m.group(2) or 0):02d}"


def _treff(ctx):
    flat = clean(soup(TREFF).get_text(" ", strip=True))
    found = []
    for m in re.finditer(rf"(\d{{1,2}})\.?\s*({MONTH_RE})", flat, re.I):
        d = parse_de_date(m.group(0), ctx.today)
        if d and d.weekday() == 3:
            found.append(d)
    found = sorted(set(found))
    days = []
    if len(found) >= 2 and (found[1] - found[0]).days in (7, 14):
        days = ctx.dates_on(3, step_days=(found[1] - found[0]).days, start=found[0])
    elif re.search(r"ungeraden", flat, re.I) and re.search(r"donnerstag", flat, re.I):
        days = [d for d in ctx.dates_on(3) if d.isocalendar().week % 2 == 1]
    if not days:
        return []
    clock = _clock(flat, "19:00")
    e = make_event(ctx, title="Klettertreff", date_=days[0], time_=clock,
                   venue_key="Kletterkiste Mainz", url=TREFF, source=TREFF, category="climbing",
                   text_="Open climbing meet at Kletterkiste Mainz for people who can already belay. "
                         "No extra signup; pay hall entry. A coach is around from about 19:00. "
                         f"Meets {clock} on the published every-other-Thursday cadence.")
    return [series(e, [(d, clock) for d in days], url=TREFF, key="kletterkiste-treff")]


def _first_weekdays(ctx, weekday):
    out, y, m = [], ctx.today.year, ctx.today.month
    for _ in range(4):
        d = date(y, m, 1)
        d += timedelta(days=(weekday - d.weekday()) % 7)
        if ctx.in_window(d) and (d.month, d.day) not in HOLIDAYS:
            out.append(d)
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out


def _grip(ctx):
    try:
        flat = clean(soup(GRIP).get_text(" ", strip=True))
    except ScraperError:
        return []
    if not re.search(r"ersten Montag im Monat", flat, re.I):
        return []
    clock = _clock(flat, "18:00")
    days = _first_weekdays(ctx, 0)
    if not days:
        return []
    e = make_event(ctx, title="Grip & Grow Frauenklettertreff", date_=days[0], time_=clock,
                   venue_key="Wiesbadener Nordwand", url=GRIP, source=GRIP, category="climbing",
                   text_="Women's climbing meet run jointly by DAV Wiesbaden and DAV Mainz, "
                         f"at Wiesbadener Nordwand in Wiesbaden-Biebrich. First Monday of the month at {clock}, "
                         "except public holidays. Confident lead belaying is expected.")
    return [series(e, [(d, clock) for d in days], url=GRIP, key="grip-grow")]


def _event_pages(ctx):
    try:
        home = soup(HOME)
    except ScraperError:
        return []
    links = []
    for a in home.find_all("a", href=True):
        if "/events/veranstaltung/" in a["href"]:
            links.append(absurl(HOME, a["href"]))
    out = []
    for url in dict.fromkeys(links):
        try:
            sp = soup(url)
        except ScraperError:
            continue
        title = clean(text(sp.find("h1")) or "Kletterkiste")
        if SKIP_PAGE.search(title):
            continue
        flat = clean(sp.get_text(" ", strip=True))
        sessions = []
        for m in re.finditer(r"(\d{1,2}\.\d{1,2}\.\d{4})(?:\s*(\d{1,2}:\d{2}))?", flat):
            d = parse_de_date(m.group(1))
            if d and ctx.in_window(d):
                sessions.append((d, m.group(2) or ""))
        # A range like "12.10.2026 - 14.10.2026" has no clock; the timetable below
        # repeats those days with 09:00. Keep the timed row.
        timed_days = {d for d, t in sessions if t}
        sessions = sorted({(d, t) for d, t in sessions if t or d not in timed_days})
        if not sessions:
            continue
        e = make_event(ctx, title=title, date_=sessions[0][0], time_=sessions[0][1],
                       venue_key="Kletterkiste Mainz", url=url, source=HOME, category="climbing",
                       text_=f"Climbing event at Kletterkiste / DAV Mainz. {title}. {flat[:400]}")
        e = series(e, sessions, url=url, key=f"kletterkiste-page-{url}")
        if e:
            out.append(e)
    return out


def scrape(ctx):
    out, errors = [], []
    for fn in (_yolawo, _treff, _grip, _event_pages):
        try:
            out.extend(x for x in fn(ctx) if x)
        except ScraperError as ex:
            errors.append(str(ex))
    if not out and errors:
        raise ScraperError("; ".join(errors))
    return out
