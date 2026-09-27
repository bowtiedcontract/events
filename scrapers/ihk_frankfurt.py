"""IHK Frankfurt am Main – event teaser list is JavaScript-rendered (Playwright); the linked
event pages (events.frankfurt-main.ihk.de) are static and carry date, time and place."""
import re
from .base import soup, playwright_page, parse_de_date, make_event, skip, clean

SOURCE = {"id": "ihk_frankfurt", "name": "IHK Frankfurt am Main",
          "url": "https://www.frankfurt-main.ihk.de/veranstaltungen"}
ONLINE = re.compile(r"webinar|online|livestream|virtuell|digital-session|videokonferenz|zoom|teams-", re.I)
LOCAL = re.compile(r"frankfurt|offenbach|eschborn|wiesbaden|mainz|darmstadt|hanau|bad homburg|börsenplatz", re.I)


def _links(pg):
    pg.goto(SOURCE["url"], wait_until="domcontentloaded")
    pg.wait_for_selector("a.teaser--link", timeout=30000)
    for _ in range(5):  # click "load more" if present
        more = pg.query_selector("button:has-text('Mehr'), a:has-text('Mehr anzeigen'), button:has-text('weitere')")
        if not more:
            break
        try:
            more.click()
            pg.wait_for_timeout(1500)
        except Exception:  # noqa: BLE001
            break
    return pg.eval_on_selector_all("a.teaser--link", "els => els.map(e => [e.href, e.getAttribute('aria-label') || ''])")


def scrape(ctx):
    links = playwright_page(_links)
    out, seen = [], set()
    for href, label in links:
        if href in seen or ONLINE.search(label) or "ihk" not in href:
            continue
        seen.add(href)
        try:
            page = soup(href)
        except Exception:  # noqa: BLE001
            continue
        body = page.get_text("\n", strip=True)
        head = body[:1500]
        d = parse_de_date(head, ctx.today)
        if not d or not ctx.in_window(d) or ONLINE.search(head[:600]):
            continue
        m = re.search(r"(\d{1,2}[:.]\d{2})\s*(?:Uhr)?\s*(?:-|–|bis|und)", head)
        t = m.group(1).replace(".", ":").zfill(5) if m else ""
        flat = page.get_text(" ", strip=True)
        ort = None
        for m in re.finditer(r"(?:Veranstaltungs)?[Oo]rt\s*:?\s*(.{3,150}?\d{5}\s+[A-ZÄÖÜ][\wäöüß-]+(?:\s+am\s+Main)?)", flat):
            ort = m
            break
        place = clean(ort.group(1)) if ort else ""
        if not place or not LOCAL.search(place):
            continue  # no physical place in the region stated
        title = label or clean(page.title.get_text() if page.title else "")
        if skip(title):
            continue
        venue = place.split(",")[0]
        addr = ", ".join(place.split(",")[1:]).strip()
        if re.search(r"\d", venue):  # "Börsenpl. 4, 60313 Frankfurt" – no venue name given
            addr = place
            venue = "IHK Frankfurt am Main" if "börsenpl" in place.lower() else venue
        city = next((c.title() for c in ("wiesbaden", "mainz", "darmstadt", "offenbach") if c in place.lower()), "Frankfurt")
        out.append(make_event(ctx, title=title, date_=d, time_=t, venue_key=None, venue=venue, city=city,
                              address=re.sub(r"\s+", " ", addr), url=href, source=SOURCE["url"],
                              default_category="business", allowed={"business", "tech"},
                              text_=body[:900]))
    return out
