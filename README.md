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
| `data/descriptions.json` | Cache of generated English descriptions, keyed by event id (so nothing is generated twice) |
| `data/scrape-report.json` | Result of the last automated run: per source status, events found, error |
| `scrapers/` | One scraper module per source (see table below); `scrapers/base.py` has the shared helpers |
| `scripts/weekly.py` | The automated weekly run: all scrapers → merge → prune → dedupe → descriptions → write |
| `scripts/describe.py` | English descriptions via an OpenAI-compatible API (or a template without a key) |
| `scripts/health_issue.py` | Opens/updates/closes the "Scraper health" issue |
| `scripts/refresh.py` | Prunes past events, dedupes, validates, sorts, stamps last-updated (also used by weekly.py) |
| `.github/workflows/weekly-refresh.yml` | GitHub Actions workflow: Mondays 05:00 UTC + manual runs |

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
  "tags": ["optional"],
  "id": "set automatically (hash of title + venue)",
  "origin": "scraper:<source id> for scraped events; absent for hand-added events"
}
```

`dates` is optional. Use it for the same production with several performances. The page shows each future performance, and the script drops the past ones.

Only add events you have actually seen on a real source page (venue calendar, city portal, Meetup/Eventbrite/Luma, ticket shop). Don't guess dates, prices or links. Set `english: true` only when it's clearly true (English-language event, international crowd, or no language needed).

## How the automation works

Every **Monday at 05:00 UTC** (and whenever you start it by hand) the workflow `.github/workflows/weekly-refresh.yml` runs on GitHub Actions. No agent or person is needed:

1. Sets up Python 3.12, installs `requirements.txt` and a headless Chromium (Playwright, only needed by the Kurhaus, Festhalle and IHK scrapers).
2. Runs `python scripts/weekly.py`:
   - Every scraper in `scrapers/` runs on its own, with a 5-minute timeout. If one crashes or times out, the others carry on.
   - **Merge rules:**
     - A source that worked replaces the events it produced last week with its fresh results.
     - A source that failed, or suddenly returned nothing, keeps its previous events. They stay until their date passes.
     - Events **without an `origin` field** were added by hand. They are never touched until their date has passed.
   - Past events are dropped. Validation uses the same rules as `refresh.py`.
   - Duplicates are removed with the exact `refresh.py` key plus a fuzzy match: same city, overlapping date, similar title (e.g. "Zaide" = "Zaide (Mozart)"). A hand-curated record always beats a scraped one.
   - Events without a description get an English one (see below).
   - Writes `data/events.json` (with a new "last updated" stamp), `data/descriptions.json` and `data/scrape-report.json`.
3. Commits the changed `data/` files to `main` as `github-actions[bot]` with a message like `Weekly refresh 2026-10-05: 470 events, 35 new`, then asks GitHub Pages to rebuild. The site updates a minute or two later.
4. **Health check:** a source counts as broken if it failed, or if it returned 0 events after returning some last time. Seasonal sources (Christmas markets, Buchmesse, Mainz Klassik, English Theatre) are allowed to return 0. If anything is broken, the workflow opens or updates **one** issue titled **"Scraper health"** listing the broken sources and their errors. The issue is closed automatically once every source is healthy again. The run's summary page also shows a per-source table.

Scrapers collect events for the next 9 weeks (`WINDOW_DAYS` in `scrapers/base.py`). Seasonal events like Christmas markets and the Buchmesse are collected up to 4 months ahead.

### English descriptions (AI)

New events without a description are sent to a cheap chat model that writes 1–2 English sentences. The model is prompted to use **only** the facts it is given: title, venue, city, category, date and the scraped source text, which is often German. It must not invent performers, programme, prices or praise. It also returns an English title (`title_en`) for German titles.

- Works with any **OpenAI-compatible** chat-completions endpoint: OpenAI, Google Gemini (OpenAI-compatible endpoint), OpenRouter, Groq, Mistral, etc.
- **Only new events** are sent. Results are cached by event id in `data/descriptions.json`, so nothing is generated twice.
- **Cost limits:** batches of 15 events per request, at most 8 requests per run, and `max_tokens` is capped. A typical week costs a fraction of a cent with gpt-4o-mini.
- **Without a key** (or if the API fails), a simple template is used instead, e.g. "Concert at Batschkapp, Frankfurt. See the organiser's page for programme and tickets." The run carries on normally. Once you add a key, template descriptions are replaced by AI ones on the next run (still within the request cap).

#### Adding the API key

1. Open the repo on GitHub, then **Settings → Secrets and variables → Actions**. Direct link: https://github.com/bowtiedcontract/rhine-main-events/settings/secrets/actions
2. On the **Secrets** tab, click **New repository secret**:
   - Name: `LLM_API_KEY`
   - Value: your API key
3. Optional: on the **Variables** tab, click **New repository variable** to change the provider or model:

| Variable | Default | Examples |
|---|---|---|
| `LLM_BASE_URL` | `https://api.openai.com/v1` | Gemini: `https://generativelanguage.googleapis.com/v1beta/openai` · OpenRouter: `https://openrouter.ai/api/v1` · Groq: `https://api.groq.com/openai/v1` |
| `LLM_MODEL` | `gpt-4o-mini` | `gemini-2.5-flash` · `openai/gpt-4o-mini` (OpenRouter) · `llama-3.1-8b-instant` (Groq); check your provider’s current model list |

The key is only read by the workflow. It is never written to the repo or the site.

### Eventbrite (skipped on GitHub Actions)

Eventbrite refuses requests from GitHub's cloud servers (HTTP 405, bot protection), both for plain HTTP and for a headless browser. The workflow therefore skips it by default (repository variable `SKIP_SOURCES`, default `eventbrite`). The Eventbrite events from the last successful run stay on the site until their dates pass. To refresh them, run this once a month from your own computer (a home connection works) and push:

```bash
python scripts/weekly.py --only eventbrite && git add data && git commit -m "Eventbrite refresh" && git push
```

If Eventbrite ever works from Actions again, set the repository variable `SKIP_SOURCES` to `none`.

### Running it manually

- **On GitHub:** go to **Actions → Weekly refresh → Run workflow** (branch `main`).
- **From a terminal with the GitHub CLI:**
  ```bash
  gh workflow run weekly-refresh.yml
  gh run watch
  ```
- **Locally:**
  ```bash
  python -m venv .venv && . .venv/bin/activate
  pip install -r requirements.txt && python -m playwright install chromium
  python scripts/weekly.py                              # everything (about 4 minutes)
  python scripts/weekly.py --only alte_oper,batschkapp  # just some sources (others keep their events)
  python scripts/weekly.py --dry-run                    # print what would happen, write nothing
  LLM_API_KEY=sk-... python scripts/weekly.py           # with AI descriptions
  ```
  Then commit and push `data/` yourself.

### Fixing a scraper

When the "Scraper health" issue appears, the usual cause is that a venue redesigned its website.

1. Run the scraper on its own and look at what it finds:
   ```bash
   python -m scrapers alte_oper          # readable list
   python -m scrapers alte_oper --json   # full event records
   ```
2. Open the source URL (it's at the top of `scrapers/<id>.py`) in a browser and compare. Usually a CSS class, a URL or a date format has changed. Update the selectors or regex in that module.
   - Shared helpers live in `scrapers/base.py`: `soup`, `parse_ics`, `jsonld`, `parse_de_date`, `parse_range`, `categorize`, `make_event`, `exhibitions`, `seasonal`.
   - Prefer a feed if the site offers one: iCal, RSS, JSON-LD / schema.org, or a JSON API.
3. Run `python scripts/weekly.py --only <id>` and check the site locally (`python3 -m http.server 8000`). Then commit and push. The next run closes the issue if everything is healthy.
4. If a source can't be fixed quickly:
   - Remove it from `MODULES` in `scrapers/__init__.py`. Its old events expire naturally.
   - Add its important events by hand (below).

**Adding a new source:**
- Create `scrapers/<id>.py` with `SOURCE = {"id", "name", "url"}` and `scrape(ctx)`, which returns a list built with `make_event(...)`.
- Add the id to `MODULES`.
- If the venue isn't listed yet, add it to `data/venues.json` so the address is filled in.

**Categories** come from the venue's default (e.g. classical for opera houses) plus keyword rules (`RULES` in `scrapers/base.py`). Edit the rules if events land in the wrong category.

## Adding events by hand

Hand-added events are kept until their date passes, and the automation never overwrites them. Use this for one-off highlights that no scraper covers.

1. Write the new events as a JSON list in `new.json`. Use the schema above, **without** an `origin` field.
2. Run `python3 scripts/refresh.py --merge new.json --stamp`:
   - Removes past events. Multi-day events are kept until `end_date`; past entries in `dates` are dropped.
   - Removes exact duplicates (same normalised title + venue + date).
   - Validates required fields, category, date/time formats and URLs.
   - Sorts by date and stamps `last_updated`.
   - `--check` validates only. `--today YYYY-MM-DD` simulates another day.
3. Commit and push `data/`.

## Sources and scrapers

| Scraper (`scrapers/…`) | Source | Method |
|---|---|---|
| `staatstheater_wiesbaden` | Hessisches Staatstheater Wiesbaden (concerts, opera, dance; incl. Sinfoniekonzerte in the Kurhaus) | schema.org Event microdata, monthly calendar |
| `kurhaus_wiesbaden` | Kurhaus Wiesbaden official calendar | Playwright → the page's GraphQL search → public per-event iCal |
| `termine_kurhaus` | Kurhaus Wiesbaden guest/promoter concerts via termine.de | static HTML list |
| `schlachthof_wiesbaden` | Schlachthof Wiesbaden concerts | HTML list + detail pages (start time, VVK price) |
| `staatstheater_mainz` | Staatstheater Mainz (opera, concerts, ballet) | monthly overview HTML |
| `frankfurter_hof_mainz` | Frankfurter Hof / Rheingoldhalle (mainzplus) | ztix table + detail pages (genre "Konzerte: …", reservix link); cabaret/comedy skipped |
| `kuz_mainz` | KUZ Kulturzentrum Mainz | programme HTML (concerts, markets) |
| `mainz_klassik` | Mainz Klassik – Meisterkonzerte | Squarespace JSON (`?format=json`) |
| `alte_oper` | Alte Oper Frankfurt | public JSON API |
| `oper_frankfurt` | Oper Frankfurt | monthly Spielplan HTML (kids' formats and tours skipped) |
| `hr_sinfonieorchester` | hr-Sinfonieorchester | monthly calendar HTML |
| `batschkapp` | Batschkapp | server-rendered list (rubric "Konzert" only) |
| `jahrhunderthalle` | Jahrhunderthalle | box-office `events.json` (music only, by keywords) |
| `festhalle` | Festhalle Frankfurt | Playwright → the page's Messe Frankfurt event API response |
| `staatstheater_darmstadt` | Staatstheater Darmstadt | season Spielplan HTML (opera, concerts, dance, musical) |
| `centralstation_darmstadt` | Centralstation Darmstadt | programme HTML (concerts/jazz/classical) |
| `english_theatre` | English Theatre Frankfurt | season page → production pages (run dates) |
| `staedel`, `schirn`, `museum_wiesbaden`, `kunsthalle_mainz` | Museums | exhibition lists (title + date range) |
| `eventbrite` | Eventbrite searches (Frankfurt networking/startup/AI/tech/English comedy/expat, Wiesbaden, Mainz, Darmstadt business) | JSON embedded in the search pages; online events and parties skipped |
| `luma` | lu.ma/frankfurt | `__NEXT_DATA__` JSON |
| `ihk_frankfurt` | IHK Frankfurt events | Playwright for the list, static event pages; webinars skipped, only events with a stated local venue |
| `datamonster` | datamonster.io Monster-Meetings Rhein-Main | meeting pages |
| `buchmesse`, `xmas_frankfurt`, `xmas_wiesbaden`, `xmas_mainz` | Frankfurter Buchmesse, Christmas markets (Frankfurt, Wiesbaden Sternschnuppenmarkt, Mainz) | date range on the official page |

**Not automated, so check these monthly by hand:**
- One-off conferences such as EU FinTech Week.
- Meetup.com groups: the site blocks scraping.
- Tanzfestival Rhein-Main highlights.
- Wine/city festivals outside the Christmas markets.
- Small venues and bars without a calendar feed, e.g. the Kakadu Bar at Staatstheater Mainz and theatre-bar formats.
