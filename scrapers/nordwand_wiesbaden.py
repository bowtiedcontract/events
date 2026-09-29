"""Wiesbadener Nordwand – courses and regular clubs.

nordwand.store is WooCommerce Bookings. Public slots live at
/wp-json/wc-bookings/v1/products/slots. Hourly taster inventory, birthday
parties, punch cards and yoga are not public sessions and are skipped.
A product with dozens of slots across every day is drop-in inventory, not a class.

Vorstieg and the Toprope Grundkurs publish two sessions a week apart, but the
shop only lists the start date (the next start is a fortnight later). The second
evening is added from that published pattern.
"""
import html as htmlmod
import re
from datetime import datetime, timedelta
from urllib.parse import urlencode

from .base import ScraperError, clean, get, make_event, series

SOURCE = {"id": "nordwand_wiesbaden", "name": "Wiesbadener Nordwand",
          "url": "https://wiesbadener-nordwand.de/"}
SHOP = "https://nordwand.store/wp-json/wc/store/products?per_page=100"
SLOTS = "https://nordwand.store/wp-json/wc-bookings/v1/products/slots"
SKIP = re.compile(r"yoga|geburtstag|gutschein|\bkarte\b|ticket|schulklasse|schnupper|eltern-?\s*kind", re.I)
# Start dates are every 14 days; the course page says the second session is the week after.
FOLLOW_UP = re.compile(r"vorstiegskurs|grundkurs toprope", re.I)
MAX_SLOTS = 60  # above this, the product is bookable inventory rather than a class list


def _plain(s):
    return clean(htmlmod.unescape(re.sub(r"<[^>]+>", " ", s or "")))


def _euro_minor(prices):
    raw = (prices or {}).get("price")
    if raw in (None, ""):
        return ""
    try:
        minor = int((prices or {}).get("currency_minor_unit") or 2)
        value = int(raw) / (10 ** minor)
    except (TypeError, ValueError):
        return ""
    return f"€{int(value)}" if abs(value - round(value)) < 0.001 else f"€{value:.2f}"


def _slots(pid, ctx):
    q = urlencode({"product_ids": str(pid), "min_date": ctx.today.isoformat(),
                   "max_date": ctx.until.isoformat(), "limit": "200"})
    data = get(f"{SLOTS}?{q}", headers={"Accept": "application/json"}).json()
    if not isinstance(data, dict):
        return []
    if (data.get("count") or 0) > MAX_SLOTS:
        return None  # drop-in inventory
    return data.get("records") or []


def scrape(ctx):
    products = get(SHOP, headers={"Accept": "application/json"}).json()
    if not isinstance(products, list) or not products:
        raise ScraperError("Nordwand shop product list was empty or not JSON")
    out = []
    for product in products:
        name = _plain((product.get("name") if isinstance(product.get("name"), str) else "") or "")
        # En dash so "8–11" and "11–16" don't share the digit 11 and collapse in dedupe.
        name = re.sub(r"(\d+)\s*-\s*(\d+)", r"\1–\2", name)
        if not name or SKIP.search(name):
            continue
        try:
            records = _slots(product.get("id"), ctx)
        except ScraperError:
            continue
        if not records:
            continue
        sessions = []
        starts = set()
        for rec in records:
            try:
                dt = datetime.fromisoformat(rec["date"])
            except (TypeError, ValueError):
                continue
            if not ctx.in_window(dt.date()):
                continue
            # Midnight + a 1-unit duration is a date-only camp booking, not a clock time.
            clock = "" if dt.hour == 0 and dt.minute == 0 else dt.strftime("%H:%M")
            sessions.append((dt.date(), clock))
            starts.add(dt.date())
        if FOLLOW_UP.search(name):
            for day, clock in list(sessions):
                nxt = day + timedelta(days=7)
                if nxt not in starts and ctx.in_window(nxt):
                    sessions.append((nxt, clock))
        if not sessions:
            continue
        url = product.get("permalink") or SOURCE["url"]
        e = make_event(ctx, title=name, date_=sessions[0][0], time_=sessions[0][1],
                       venue_key="Wiesbadener Nordwand", url=url, source=SOURCE["url"],
                       price=_euro_minor(product.get("prices")), category="climbing",
                       text_=f"Climbing course or club at Wiesbadener Nordwand. {name}.")
        e = series(e, sessions, url=url, key=f"nordwand-{product.get('id')}")
        if e:
            out.append(e)
    return out
