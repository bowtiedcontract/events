"""Boulderwelt Frankfurt – courses, workshops, camps and training groups.

Boulderwelt Plus (plus.boulderwelt.de) reads a public API at gate.boulderwelt.de.
Birthday parties, personal training, room hire, company events and tariffs are
not public sessions. Dates in the payload are the gym's local wall time.
"""
import html as htmlmod
import re
from datetime import date

from .base import ScraperError, clean, get, make_event, series

SOURCE = {"id": "boulderwelt_frankfurt", "name": "Boulderwelt Frankfurt",
          "url": "https://www.boulderwelt-frankfurt.de/boulderkurse-und-training/"}
API = "https://gate.boulderwelt.de"
SKIP_MODEL = re.compile(
    r"geburtstag|personal|raumreserv|gruppentarif|firmen|kundenbetreuung", re.I)


# Spelled-out ages leave the group code (BK-08, BT-04) as the only digits.
# The weekly job treats two events as the same listing when they share a day and
# their titles share a number, so "7-10, BK-07" and "7-10, BK-08" would collapse.
_AGE = {
    1: "eins", 2: "zwei", 3: "drei", 4: "vier", 5: "fünf", 6: "sechs",
    7: "sieben", 8: "acht", 9: "neun", 10: "zehn", 11: "elf", 12: "zwölf",
    13: "dreizehn", 14: "vierzehn", 15: "fünfzehn", 16: "sechzehn", 17: "siebzehn",
}


def _plain(s):
    return clean(htmlmod.unescape(re.sub(r"<[^>]+>", " ", s or "")))


def _public_title(title):
    title = _plain(title)
    code = re.search(r"\b((?:BK|BT)-\d+)\b", title, re.I)
    if code:
        kind = "Boulderteens" if re.search(r"teens", title, re.I) else "Boulderkids"
        ages = re.search(r"(\d+)\s*[-–]\s*(\d+)\s*Jahre", title, re.I)
        bits = [kind]
        if ages:
            a, b = _AGE.get(int(ages.group(1))), _AGE.get(int(ages.group(2)))
            if a and b:
                bits.append(f"{a} bis {b} Jahre")
        bits.append(code.group(1).upper())
        return ", ".join(bits)
    title = re.sub(
        r"\s+[–—-]\s+(?:Montag|Dienstag|Mittwoch|Donnerstag|Freitag|Samstag|Sonntag)\s*$",
        "", title, flags=re.I)
    # An en dash glues an age range into one number (6–8 vs 8–12), so two camps
    # on the same week stay separate.
    return re.sub(r"(\d+)\s*[-–]\s*(\d+)", lambda m: f"{m.group(1)}–{m.group(2)}", title)


def _json(url):
    return get(url, headers={"Accept": "application/json"}).json()


def scrape(ctx):
    branches = _json(f"{API}/branch")
    if not isinstance(branches, list):
        raise ScraperError("Boulderwelt branch list was not JSON")
    branch = next((b for b in branches
                   if "frankfurt" in f"{b.get('city', '')} {b.get('name', '')}".lower()), None)
    if not branch:
        raise ScraperError("Boulderwelt Frankfurt branch not found")
    models = _json(f"{API}/event/model")
    if not isinstance(models, list):
        raise ScraperError("Boulderwelt event models were not a list")
    out = []
    for model in models:
        if not model.get("is_active", True) or SKIP_MODEL.search(model.get("name") or ""):
            continue
        try:
            events = _json(f"{API}/event/{branch['id']}?event_model_id={model['id']}")
        except ScraperError:
            continue
        if not isinstance(events, list):
            continue
        for ev in events:
            sessions = []
            for slot in ev.get("event_dates") or []:
                m = re.match(r"(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2})", slot.get("date") or "")
                if not m:
                    continue
                d = date.fromisoformat(m.group(1))
                if ctx.in_window(d):
                    sessions.append((d, m.group(2)))
            if not sessions:
                continue
            raw = _plain(ev.get("name") or model.get("name"))
            title = _public_title(raw)
            url = f"https://plus.boulderwelt.de/event/{ev['id']}"
            blurb = _plain(ev.get("description"))
            e = make_event(ctx, title=title, date_=sessions[0][0], time_=sessions[0][1],
                           venue_key="Boulderwelt Frankfurt", url=url, source=SOURCE["url"],
                           category="climbing",
                           text_=f"Bouldering course at Boulderwelt Frankfurt. {raw}. {blurb}")
            e = series(e, sessions, url=url, key=f"boulderwelt-{ev['id']}")
            if e:
                out.append(e)
    return out
