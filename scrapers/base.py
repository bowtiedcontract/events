"""Shared helpers for all scrapers: HTTP, parsing (JSON-LD, iCal, German dates),
venue lookup, category rules and event construction."""
import hashlib, json, re, time, unicodedata
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

BERLIN = ZoneInfo("Europe/Berlin")
ROOT = Path(__file__).resolve().parent.parent
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128 Safari/537.36"
HEADERS = {"User-Agent": UA, "Accept-Language": "de,en;q=0.8"}
WINDOW_DAYS = 63
CONCERT = {"classical", "music", "festival", "general"}  # allowed categories for concert venues  # how far ahead scrapers collect (9 weeks)

_session = requests.Session()
_session.headers.update(HEADERS)


class ScraperError(Exception):
    pass


# ---------------------------------------------------------------- HTTP
def get(url, retries=2, timeout=30, **kw):
    last = None
    for attempt in range(retries + 1):
        try:
            r = _session.get(url, timeout=timeout, **kw)
            if r.status_code >= 500 or r.status_code == 429:
                raise requests.HTTPError(f"HTTP {r.status_code}")
            r.raise_for_status()
            if not r.encoding or r.encoding.lower() == "iso-8859-1":
                r.encoding = r.apparent_encoding or "utf-8"
            return r
        except Exception as ex:  # noqa: BLE001
            last = ex
            time.sleep(1.5 * (attempt + 1))
    raise ScraperError(f"GET {url} failed: {last}")


def soup(url, **kw):
    return BeautifulSoup(get(url, **kw).text, "lxml")


def text(el, sep=" "):
    if el is None:
        return ""
    t = el.get_text(sep, strip=True) if hasattr(el, "get_text") else str(el)
    return re.sub(r"\s+", " ", t).strip()


def absurl(base, href):
    from urllib.parse import urljoin
    return urljoin(base, href) if href else ""


# ---------------------------------------------------------------- context
class Context:
    def __init__(self, today=None):
        self.today = today or datetime.now(BERLIN).date()
        self.until = self.today + timedelta(days=WINDOW_DAYS)
        self.venues = {v["name"]: v for v in json.loads((ROOT / "data" / "venues.json").read_text("utf-8"))}

    def in_window(self, d, end=None):
        """True if the event (or multi-day run until `end`) overlaps today..until."""
        if isinstance(d, str):
            d = date.fromisoformat(d)
        if isinstance(end, str):
            end = date.fromisoformat(end)
        return d <= self.until and (end or d) >= self.today

    def months(self, n=3):
        """(year, month) tuples covering the window, starting this month."""
        y, m = self.today.year, self.today.month
        out = []
        for _ in range(n):
            out.append((y, m))
            m += 1
            if m > 12:
                y, m = y + 1, 1
        return out


# ---------------------------------------------------------------- dates
MONTHS = {
    "januar": 1, "jan": 1, "january": 1, "jänner": 1,
    "februar": 2, "feb": 2, "february": 2,
    "märz": 3, "maerz": 3, "mär": 3, "mrz": 3, "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "mai": 5, "may": 5,
    "juni": 6, "jun": 6, "june": 6,
    "juli": 7, "jul": 7, "july": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "oktober": 10, "okt": 10, "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "dezember": 12, "dez": 12, "december": 12, "dec": 12,
}
MONTH_RE = "|".join(sorted(MONTHS, key=len, reverse=True))


def year4(y, ref=None):
    y = int(y)
    return y + 2000 if y < 100 else y


def guess_year(month, day, today):
    """For dates without a year: pick the next occurrence (allowing ~2 months in the past)."""
    y = today.year
    d = date(y, month, day)
    if (today - d).days > 60:
        d = date(y + 1, month, day)
    return d


def parse_de_date(s, today=None):
    """Parse the first date in s: 12.10.2026 / 12.10.26 / 12. Oktober 2026 / 12 Okt 26 / 12.10."""
    s = s or ""
    m = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{4}|\d{2})(?!\d)", s)
    if m:
        return date(year4(m.group(3)), int(m.group(2)), int(m.group(1)))
    m = re.search(rf"(\d{{1,2}})(?:\.|st|nd|rd|th)?\s*({MONTH_RE})\.?,?\s*(\d{{4}}|\d{{2}})?(?![\d])", s, re.I)
    if m:
        mon = MONTHS[m.group(2).lower()]
        if m.group(3):
            return date(year4(m.group(3)), mon, int(m.group(1)))
        if today:
            return guess_year(mon, int(m.group(1)), today)
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None


def parse_time(s):
    m = re.search(r"(?<!\d)(\d{1,2})[:.](\d{2})\s*(Uhr|h\b|AM|PM|am|pm)?", s or "")
    if not m:
        return ""
    h, mi = int(m.group(1)), int(m.group(2))
    ap = (m.group(3) or "").lower()
    if ap == "pm" and h < 12:
        h += 12
    if ap == "am" and h == 12:
        h = 0
    if h > 23 or mi > 59:
        return ""
    return f"{h:02d}:{mi:02d}"


def parse_range(s, today):
    """Find a date range like '23.11. – 22.12.2026', '17.9.2026–17.1.2027',
    '24. November bis 23. Dezember 2026', '22 Mai 26 — 17 Jan 27', '21/08/26—10/01/27'.
    Returns (start, end) dates or (None, None)."""
    s = re.sub(r"\s+", " ", s or "")
    dash = r"\s*(?:–|-|—|bis|to|until)\s*"
    # 17.9.2026 – 17.1.2027 / 23.11. – 22.12.2026 / 21/08/26—10/01/27
    m = re.search(rf"(\d{{1,2}})[./](\d{{1,2}})[./]?(\d{{4}}|\d{{2}})?{dash}(\d{{1,2}})[./](\d{{1,2}})[./](\d{{4}}|\d{{2}})", s)
    if m:
        y2 = year4(m.group(6))
        e = date(y2, int(m.group(5)), int(m.group(4)))
        y1 = year4(m.group(3)) if m.group(3) else (y2 if int(m.group(2)) <= e.month else y2 - 1)
        return date(y1, int(m.group(2)), int(m.group(1))), e
    # 24. November bis 23. Dezember 2026 / 22 Mai 26 — 17 Jan 27 / 19th September 2026 – 7th November 2026
    mo = rf"(\d{{1,2}})\s*(?:\.|st|nd|rd|th)?\s*({MONTH_RE})\.?\s*(\d{{4}}|\d{{2}})?"
    m = re.search(rf"{mo}{dash}{mo}", s, re.I)
    if m:
        y2 = year4(m.group(6)) if m.group(6) else today.year
        e = date(y2, MONTHS[m.group(5).lower()], int(m.group(4)))
        m1 = MONTHS[m.group(2).lower()]
        y1 = year4(m.group(3)) if m.group(3) else (y2 if m1 <= e.month else y2 - 1)
        return date(y1, m1, int(m.group(1))), e
    # 7 – 11 October 2026 / 07-08 October 2026
    m = re.search(rf"(\d{{1,2}})\.?{dash}(\d{{1,2}})\.?\s*({MONTH_RE})\.?\s*(\d{{4}})", s, re.I)
    if m:
        mon, y = MONTHS[m.group(3).lower()], int(m.group(4))
        return date(y, mon, int(m.group(1))), date(y, mon, int(m.group(2)))
    return None, None


def iso_to_berlin(s):
    """ISO datetime string (with Z/offset or naive=Berlin) -> (date iso, HH:MM)."""
    s = s.strip().replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    if dt.tzinfo:
        dt = dt.astimezone(BERLIN)
    return dt.date().isoformat(), dt.strftime("%H:%M")


# ---------------------------------------------------------------- iCal
def parse_ics(raw):
    """Minimal iCalendar parser -> list of dicts with SUMMARY, DESCRIPTION, LOCATION, URL,
    date (YYYY-MM-DD), time (HH:MM or ''), end_date."""
    lines = re.sub(r"\r?\n[ \t]", "", raw).splitlines()
    out, cur = [], None
    for ln in lines:
        if ln == "BEGIN:VEVENT":
            cur = {}
        elif ln == "END:VEVENT" and cur is not None:
            out.append(cur)
            cur = None
        elif cur is not None and ":" in ln:
            k, v = ln.split(":", 1)
            name, *params = k.split(";")
            v = v.replace("\\n", "\n").replace("\\,", ",").replace("\\;", ";")
            if name in ("DTSTART", "DTEND"):
                tz = next((p.split("=", 1)[1] for p in params if p.startswith("TZID=")), None)
                if re.fullmatch(r"\d{8}", v):
                    d, t = f"{v[:4]}-{v[4:6]}-{v[6:8]}", ""
                else:
                    dt = datetime.strptime(v.rstrip("Z")[:15], "%Y%m%dT%H%M%S")
                    if v.endswith("Z"):
                        dt = dt.replace(tzinfo=ZoneInfo("UTC")).astimezone(BERLIN)
                    elif tz:
                        try:
                            dt = dt.replace(tzinfo=ZoneInfo(tz)).astimezone(BERLIN)
                        except Exception:  # noqa: BLE001
                            pass
                    d, t = dt.date().isoformat(), dt.strftime("%H:%M")
                if name == "DTSTART":
                    cur["date"], cur["time"] = d, t
                else:
                    cur["end"] = d
            else:
                cur[name] = v
    return out


# ---------------------------------------------------------------- structured data
def jsonld(html_or_soup):
    """All JSON-LD objects in a page, flattened (@graph / ItemList itemListElement included)."""
    sp = html_or_soup if isinstance(html_or_soup, BeautifulSoup) else BeautifulSoup(html_or_soup, "lxml")
    out = []

    def walk(o):
        if isinstance(o, list):
            for x in o:
                walk(x)
        elif isinstance(o, dict):
            out.append(o)
            for k in ("@graph", "itemListElement", "item", "subEvent"):
                if k in o:
                    walk(o[k])

    for s in sp.find_all("script", type="application/ld+json"):
        try:
            walk(json.loads(s.string or s.get_text() or "null"))
        except Exception:  # noqa: BLE001
            continue
    return out


def is_event(o):
    t = o.get("@type")
    t = t if isinstance(t, list) else [t]
    return any(isinstance(x, str) and x.endswith("Event") for x in t)


def find_json_after(html, marker):
    """Decode the JSON value that follows `marker` in html (e.g. 'window.__DATA__ = ')."""
    i = html.find(marker)
    if i < 0:
        return None
    j = i + len(marker)
    while j < len(html) and html[j] in " =\t\n":
        j += 1
    try:
        return json.JSONDecoder().raw_decode(html, j)[0]
    except Exception:  # noqa: BLE001
        return None


def walk_dicts(o):
    if isinstance(o, dict):
        yield o
        for v in o.values():
            yield from walk_dicts(v)
    elif isinstance(o, list):
        for v in o:
            yield from walk_dicts(v)


# ---------------------------------------------------------------- categories
RULES = [
    ("classical", r"sinfonie|symphon|orchester|orchestra|philharmon|kammermusik|kammerkonzert|streichquartett|string quartet|quartett|klavierabend|piano recital|liederabend|\boper\b|opera|operette|ballett|ballet|requiem|oratorium|messias|messiah|kantate|barock|baroque|mozart|beethoven|bach\b|brahms|vivaldi|händel|haydn|schubert|tschaikowsk|mahler|bruckner|dvořák|dvorak|chopin|sopran|violin|cello|meisterkonzert|domkonzert|orkest|staatskapelle|ensemble modern|quartet\b|kantate|gesang|mezzosopran|bariton|klassik|klassische|klavier|piano|pianist|jahreszeiten|streicher|dirigent|conductor|kammerchor|a cappella chor|orgel|organ recital"),
    ("tech", r"\b(ai|ki|genai|llm|ml)\b|künstliche intelligenz|artificial intelligence|machine learning|\bdata\b|daten|developer|coding|software|cloud|cyber|blockchain|crypto|fintech|hackathon|python|javascript|devops|\btech\b|technolog|digital|monstermeeting|web3|robot"),
    ("business", r"networking|netzwerk|business|unternehmer|gründ|startup|start-up|founder|pitch|entrepreneur|investor|finance|finanz|karriere|career|leadership|marketing|sales|expat|after.?work|ihk|mittelstand|export|steuer"),
    ("art", r"ausstellung|exhibition|vernissage|finissage|kunst(?!stoff)|\bart\b|museum|galerie|gallery|fotografie|photography"),
    ("music", r"konzert|concert|\bband\b|tour\b|tour 20|live\b|jazz|rock|\bpop\b|hip.?hop|\brap\b|indie|metal|punk|soul|funk|folk|techno|\bdj\b|singer|songwriter|acoustic|blues|reggae|electro|musical|tribute|party"),
    ("festival", r"weihnachtsmarkt|christmas market|sternschnuppenmarkt|festival|buchmesse|book fair|weinfest|volksfest|kerb\b|dippemess|oktoberfest"),
    ("general", r"comedy|kabarett|lesung|\bliest\b|messe\b|börse|whisky|reading|quiz|pub quiz|stand.?up|improv|markt|market|führung|tour of|workshop|yoga|wein|wine|tasting|food|film|kino"),
]
_RULES = [(c, re.compile(p, re.I)) for c, p in RULES]


def categorize(title, text_="", default=None, allowed=None, fallback="general"):
    """Category from keyword rules; the venue default wins unless the title clearly says otherwise.
    Title matches weigh more than text matches."""
    hits = {}
    for c, rx in _RULES:
        if allowed and c not in allowed:
            continue
        score = 3 * len(rx.findall(title or "")) + len(rx.findall(text_ or ""))
        if score:
            hits[c] = score
    if default:
        # Keep the venue's default unless another category matches the *title* strongly
        # and the default itself doesn't match at all.
        if default in hits or not hits:
            return default
        best = max(hits, key=hits.get)
        return best if hits[best] >= 3 else default
    if not hits:
        return fallback
    order = [c for c, _ in RULES]
    return max(hits, key=lambda c: (hits[c], -order.index(c)))


ENGLISH_RE = re.compile(r"\bin english\b|english[- ]speaking|englischsprachig|auf englisch|\(english\)|\bin englischer sprache|english comedy|english stand.?up|expat", re.I)


# ---------------------------------------------------------------- events
def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def event_id(title, venue):
    base = norm(title) + "|" + norm((venue or "").split(" – ")[0])
    return hashlib.sha1(base.encode()).hexdigest()[:12]


def clean(s, limit=None):
    s = re.sub(r"\s+", " ", (s or "").replace("\xa0", " ")).strip()
    if limit and len(s) > limit:
        s = s[: limit - 1].rsplit(" ", 1)[0] + "…"
    return s


SKIP_RE = re.compile(r"\bführung\b|workshop|öffentliche probe|werkstatt|stadtfest|kinderbetreuung|geschlossene veranstaltung|\babgesagt\b|\bcancel+ed\b|entfällt", re.I)


def skip(title, extra=""):
    """Generic filter for non-events (guided tours, workshops, cancelled shows)."""
    return bool(SKIP_RE.search(f"{title} {extra}"))


def make_event(ctx, *, title, date_, venue_key, time_="", room=None, venue=None, city=None, address=None,
               url="", source="", price="", category=None, default_category=None, fallback="general", allowed=None, text_="",
               end_date=None, english=None, title_en="", description=""):
    """Build an event dict in the events.json schema. `venue_key` is a name from venues.json
    (used for address/city/source defaults); `room` is appended as 'Venue – Room'."""
    v = ctx.venues.get(venue_key or "", {})
    vname = venue or v.get("name") or venue_key or ""
    if room:
        vname = f"{vname} – {room}"
    title = clean(title)
    text_ = clean(text_, 1200)
    if isinstance(date_, date):
        date_ = date_.isoformat()
    if isinstance(end_date, date):
        end_date = end_date.isoformat()
    e = {
        "title": title,
        "title_en": title_en,
        "category": category or categorize(title, text_, default_category, allowed=allowed, fallback=fallback),
        "date": date_,
        "time": time_ or "",
        "venue": vname,
        "city": city or v.get("city", ""),
        "address": address if address is not None else v.get("address", ""),
        "description": description,
        "price": clean(price),
        "url": url or source or v.get("url", ""),
        "source": source or v.get("url", "") or url,
        "english": bool(english) if english is not None else bool(ENGLISH_RE.search(title + " " + text_)),
    }
    if end_date and end_date != date_:
        e["end_date"] = end_date
    e["id"] = event_id(title, vname)
    e["_text"] = text_
    return e


def group_runs(events):
    """Merge several performances of the same title at the same venue into one event with `dates`."""
    groups = {}
    order = []
    for e in sorted(events, key=lambda e: (e["date"], e.get("time", ""))):
        k = (norm(e["title"]), norm(e["venue"]))
        if k not in groups:
            groups[k] = []
            order.append(k)
        groups[k].append(e)
    out = []
    for k in order:
        g = groups[k]
        first = dict(g[0])
        if len(g) > 1:
            seen = set()
            first["dates"] = []
            for x in g:
                if (x["date"], x.get("time", "")) in seen:
                    continue
                seen.add((x["date"], x.get("time", "")))
                first["dates"].append({"date": x["date"], "time": x.get("time", ""), "url": x.get("url", "")})
            if len(first["dates"]) == 1:
                first.pop("dates")
            if not first.get("price"):
                first["price"] = next((x["price"] for x in g if x.get("price")), "")
            if len(first.get("_text", "")) < max(len(x.get("_text", "")) for x in g):
                first["_text"] = max((x.get("_text", "") for x in g), key=len)
        out.append(first)
    return out


def playwright_page(fn, timeout=45000):
    """Run fn(page) inside a headless Chromium (imported lazily)."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        try:
            pg = b.new_page(user_agent=UA, locale="de-DE")
            pg.set_default_timeout(timeout)
            return fn(pg)
        finally:
            b.close()


LABELS = re.compile(r"^(vorschau|aktuell|ausstellungen?|dauerausstellung|sonderausstellung|neupräsentation|intervention|current|upcoming|weiter)$", re.I)


def exhibitions(ctx, url, venue_key, title_offset=2, max_date_len=70, sp=None):
    """Generic exhibition-list parser: find lines that are date ranges ('17.9.2026–17.1.2027',
    '22 Mai 26 — 17 Jan 27') and take the title (and subtitle) from the lines just above."""
    sp = sp or soup(url)
    lines = [clean(l) for l in sp.get_text("\n").split("\n") if clean(l)]
    out, seen = [], set()
    for i, line in enumerate(lines):
        if len(line) > max_date_len:
            continue
        start, end = parse_range(line, ctx.today)
        if not start or i < title_offset:
            continue
        if parse_range(lines[i - 1], ctx.today)[0]:
            continue  # the same range printed twice
        title = lines[i - title_offset]
        sub = lines[i - 1] if title_offset == 2 else ""
        if sub and (parse_range(title, ctx.today)[0] or LABELS.match(title)):
            title, sub = sub, ""
        if title.lower() in seen or len(title) < 3 or not ctx.in_window(start, end):
            continue
        seen.add(title.lower())
        out.append(make_event(ctx, title=f"{title}: {sub}" if sub and len(sub) < 80 else title,
                              date_=start, end_date=end, venue_key=venue_key, url=url, source=url,
                              category="art", text_=f"Ausstellung. {title}. {sub}"))
    return out


def seasonal(ctx, source, title, venue, city, address, near=None, lookahead_days=120, category="festival"):
    """One recurring event (Christmas market, trade fair) announced on a page as a date range.
    `near`: regex; the range closest after its first match is used. Seasonal events are collected
    further ahead (lookahead_days) than normal events so they show up in good time."""
    flat = soup(source["url"]).get_text(" ", strip=True)
    seg = flat
    if near:
        m = re.search(near, flat, re.I)
        if m:
            seg = flat[m.start():]
    start, end = parse_range(seg, ctx.today)
    if not start:
        raise ScraperError("no date range found on page (wording changed?)")
    if end < ctx.today or start > ctx.today + timedelta(days=lookahead_days):
        return []
    return [make_event(ctx, title=f"{title} {start.year}" if str(start.year) not in title else title,
                       date_=start, end_date=end, venue_key=None, venue=venue, city=city, address=address,
                       url=source["url"], source=source["url"], category=category,
                       text_=f"{title}, {start.strftime('%d.%m.')}–{end.strftime('%d.%m.%Y')}. "
                             + seg[:500])]
