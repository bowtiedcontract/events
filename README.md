# Rhine-Main Events

A static events dashboard for Wiesbaden, Mainz, Frankfurt, Darmstadt and the wider Rhine-Main area (Rheingau, Offenbach, Bad Homburg, Hanau …). It covers orchestra and classical music, concerts, festivals, tech, business/networking, art and general/social events.

Live site: https://bowtiedcontract.github.io/rhine-main-events/

It's a sibling of [english-yoga-wiesbaden](https://github.com/bowtiedcontract/english-yoga-wiesbaden) and uses the same look. It's plain HTML/CSS/JS with no build step, served by GitHub Pages from the `main` branch root.

## Files

| Path | What |
|---|---|
| `index.html` | The page: filters, rendering, venues section. It loads the JSON below. |
| `data/events.json` | `{"last_updated": "...", "events": [...]}`: all events |
| `data/venues.json` | Venues list (name, city, type, address, programme URL) for the "Venues" section |
| `scripts/refresh.py` | Prunes past events, dedupes, validates, sorts, stamps last-updated |

## Event schema

```json
{
  "title": "Original title",
  "title_en": "English gloss if the title is German (optional, may be empty)",
  "category": "festival | music | classical | tech | business | art | general",
  "date": "YYYY-MM-DD",
  "time": "HH:MM or empty",
  "end_date": "YYYY-MM-DD (optional, multi-day events / exhibitions)",
  "dates": [{"date": "YYYY-MM-DD", "time": "HH:MM", "url": "booking link"}],
  "venue": "Venue name",
  "city": "Wiesbaden | Mainz | Frankfurt | Darmstadt | Offenbach | Rheingau | ...",
  "address": "Street, postcode city",
  "description": "1–2 sentences in English",
  "price": "free text, e.g. €18–55 (optional)",
  "url": "booking / ticket link (direct if possible)",
  "source": "page the event was taken from",
  "english": true,
  "tags": ["optional"]
}
```

`dates` is optional. Use it for the same production with several performances. The page shows each future performance, and the script drops the past ones.

Only add events you have actually seen on a real source page (venue calendar, city portal, Meetup/Eventbrite/Luma, ticket shop). Don't guess dates, prices or links. Set `english: true` only when it's clearly true (English-language event, international crowd, or no language needed).

## Weekly refresh procedure

1. **Collect new events.** Check the programme pages in `data/venues.json` plus the other sources below. Write the new events as a JSON list, e.g. `new.json` (same schema, a list `[...]` or `{"events": [...]}`).
2. **Merge, prune, dedupe, validate, stamp:**
   ```bash
   python3 scripts/refresh.py --merge new.json --stamp
   ```
   - Removes past events. Multi-day events are kept until `end_date`; past entries in `dates` are dropped.
   - Removes duplicates (same normalised title + venue + date). The earlier entry wins.
   - Validates required fields, category, date/time formats and URLs.
   - Sorts by date and sets `last_updated` (Berlin time).
   - `--merge` can be repeated. `--check` validates without writing. `--today YYYY-MM-DD` simulates another day.
3. **Preview locally (optional):** `python3 -m http.server 8000`, then open http://localhost:8000/
4. **Publish:**
   ```bash
   git add data && git commit -m "Weekly refresh $(date +%F)" && git push
   ```
   GitHub Pages redeploys within a minute or two.

Even without new events, run `python3 scripts/refresh.py --stamp` weekly so past events are pruned. The page also hides past events client-side.

## Sources used

- Venue calendars:
  - Wiesbaden: Kurhaus Wiesbaden, Hessisches Staatstheater Wiesbaden, Schlachthof
  - Mainz: Staatstheater Mainz, Frankfurter Hof, KUZ, Mainz Klassik / Rheingoldhalle
  - Frankfurt: Alte Oper, Oper Frankfurt, hr-Sinfonieorchester, Festhalle, Jahrhunderthalle, Batschkapp, English Theatre Frankfurt
  - Darmstadt: Staatstheater Darmstadt, Centralstation
- Museums: Städel, Schirn, Museum Wiesbaden, Kunsthalle Mainz
- City and event portals: visitfrankfurt.travel, tourismus.wiesbaden.de, mainz.de, buchmesse.de, termine.de (Kurhaus listing)
- Community and ticket platforms:
  - Eventbrite (Frankfurt networking / startup / AI / tech / English comedy; Wiesbaden; Mainz)
  - Luma (lu.ma/frankfurt)
  - datamonster.io
  - IHK Frankfurt events
