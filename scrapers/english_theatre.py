"""English Theatre Frankfurt – productions linked from the season page ('READ MORE'),
each production page states its run, e.g. '19th September 2026 – 7th November 2026'."""
import re
from .base import soup, text, parse_range, make_event

SEASONAL = True  # zero events is normal outside the season/between runs
SOURCE = {"id": "english_theatre", "name": "English Theatre Frankfurt",
          "url": "https://english-theatre.de/season-2026-2027/"}


def scrape(ctx):
    sp = soup(SOURCE["url"])
    links = []
    for a in sp.find_all("a", href=True):
        if re.search(r"read more", text(a), re.I) and a["href"] not in links:
            links.append(a["href"])
    if not links:
        # season page layout changed: fall back to the "Playing soon" menu item
        links = [a["href"] for a in sp.find_all("a", href=True) if text(a).lower() == "playing soon"][:1]
    out = []
    for url in links:
        p = soup(url)
        body = p.get_text("\n", strip=True)
        start, end = parse_range(p.get_text(" ", strip=True), ctx.today)
        if not start or not ctx.in_window(start, end):
            continue
        title = text(p.find("h1")) or text(p.title).split("|")[0].strip()
        paras = [text(x) for x in p.select(".wpb_wrapper p, .entry-content p")]
        blurb = " ".join(t for t in paras if len(t) > 25)[:900]
        out.append(make_event(ctx, title=title.title() if title.isupper() else title, date_=start, end_date=end,
                              venue_key="English Theatre Frankfurt", url=url, source=SOURCE["url"],
                              category="general", english=True, text_=f"English-language theatre production. {blurb}"))
    return out
