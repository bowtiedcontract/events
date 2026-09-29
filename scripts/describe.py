"""English descriptions for events that have none.

Uses any OpenAI-compatible chat-completions API (OpenAI, Gemini's OpenAI endpoint, OpenRouter, Groq,
...) configured by environment variables:
  LLM_API_KEY   required to enable the model (without it a simple template is used)
  LLM_BASE_URL  default https://api.openai.com/v1
  LLM_MODEL     default gpt-4o-mini
  LLM_BATCH_SIZE (default 15 events per request), LLM_MAX_REQUESTS (default 8 per run)

Results are cached in data/descriptions.json keyed by event id, so an event is only ever sent once.
"""
import json, os, re, time
from datetime import date, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "descriptions.json"
LABEL = {"classical": "Classical music", "music": "Concert", "festival": "Festival", "tech": "Tech event",
         "business": "Business event", "art": "Exhibition", "climbing": "Climbing", "running": "Run",
         "general": "Event"}

SYSTEM = (
    "You write short English blurbs for a bilingual events listing in the Rhine-Main region. "
    "Rules: use ONLY facts contained in the provided fields (title, venue, city, category, date, source text). "
    "Never invent performers, works, programme details, prices, times, awards or opinions, and do not add "
    "superlatives. The source text may be German: translate the relevant facts. If there are few facts, write a "
    "plain factual sentence such as 'Concert by <artist> at <venue>.' Write 1-2 sentences, at most 45 words. "
    "Also return title_en: an English translation of the title if it is not already English (keep names, "
    "work titles in their original language if they are proper names), otherwise an empty string. "
    'Reply with JSON only: {"items": [{"id": "...", "description": "...", "title_en": "..."}]}'
)


def template(e):
    label = LABEL.get(e.get("category"), "Event")
    venue = e.get("venue", "")
    if e.get("category") == "art" and e.get("end_date"):
        return f"{label} at {venue}, on until {date.fromisoformat(e['end_date']).strftime('%-d %b %Y')}."
    if e.get("end_date"):
        return f"{label} at {venue}, {e.get('city', '')}, from {e['date']} to {e['end_date']}. See the organiser's page for details."
    return f"{label} at {venue}, {e.get('city', '')}. See the organiser's page for programme and tickets."


def load_cache():
    return json.loads(CACHE.read_text("utf-8")) if CACHE.exists() else {}


def save_cache(cache, live_ids, today):
    # keep entries for current events, and others for 120 days after they were last seen
    keep = {}
    for k, v in cache.items():
        if k in live_ids:
            v["last_seen"] = today.isoformat()
        if k in live_ids or v.get("last_seen", "9999") >= (today - timedelta(days=120)).isoformat():
            keep[k] = v
    CACHE.write_text(json.dumps(dict(sorted(keep.items())), ensure_ascii=False, indent=1) + "\n", "utf-8")


def _call(cfg, batch):
    items = [{"id": e["id"], "title": e["title"], "venue": e["venue"], "city": e["city"],
              "category": e["category"], "date": e["date"], "source_text": (e.get("_text") or "")[:600]}
             for e in batch]
    body = {"model": cfg["model"], "temperature": 0.2,
            "max_tokens": min(110 * len(batch) + 150, 2500),
            "messages": [{"role": "system", "content": SYSTEM},
                         {"role": "user", "content": json.dumps({"events": items}, ensure_ascii=False)}],
            "response_format": {"type": "json_object"}}
    headers = {"Authorization": f"Bearer {cfg['key']}", "Content-Type": "application/json"}
    url = cfg["base"].rstrip("/") + "/chat/completions"
    for attempt in range(3):
        r = requests.post(url, headers=headers, json=body, timeout=90)
        if r.status_code == 400 and "response_format" in body:
            body.pop("response_format")  # provider doesn't support JSON mode; rely on the prompt
            continue
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(5 * (attempt + 1))
            continue
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
        content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip())
        data = json.loads(content)
        return {str(i.get("id")): i for i in data.get("items", []) if isinstance(i, dict)}
    raise RuntimeError(f"LLM request failed: HTTP {r.status_code} {r.text[:200]}")


def fill(events, today, log=print):
    """Set description (and title_en where empty) on events lacking a description. Returns stats."""
    cfg = {"key": os.environ.get("LLM_API_KEY", "").strip(),
           "base": os.environ.get("LLM_BASE_URL", "").strip() or "https://api.openai.com/v1",
           "model": os.environ.get("LLM_MODEL", "").strip() or "gpt-4o-mini"}
    batch_size = int(os.environ.get("LLM_BATCH_SIZE") or 15)
    max_requests = int(os.environ.get("LLM_MAX_REQUESTS") or 8)
    cache = load_cache()
    stats = {"cached": 0, "llm": 0, "template": 0, "requests": 0, "llm_errors": 0,
             "model": cfg["model"] if cfg["key"] else None}
    todo = []
    for e in events:
        c = cache.get(e.get("id", ""))
        if cfg["key"] and c and c.get("source") == "template" and e.get("description") == c["description"]:
            e["description"] = ""  # a key is set now: upgrade last week's template text
        if e.get("description"):
            continue
        c = cache.get(e["id"])
        if c and (c.get("source") != "template" or not cfg["key"]):
            e["description"] = c["description"]
            if c.get("title_en") and not e.get("title_en"):
                e["title_en"] = c["title_en"]
            stats["cached"] += 1
        else:
            todo.append(e)
    if cfg["key"] and todo:
        for i in range(0, len(todo), batch_size):
            if stats["requests"] >= max_requests:
                log(f"  LLM request cap ({max_requests}) reached; {len(todo) - i} events get the template this week")
                break
            batch = todo[i:i + batch_size]
            stats["requests"] += 1
            try:
                res = _call(cfg, batch)
            except Exception as ex:  # noqa: BLE001
                stats["llm_errors"] += 1
                log(f"  LLM error: {ex}")
                continue
            for e in batch:
                r = res.get(e["id"]) or {}
                desc = re.sub(r"\s+", " ", str(r.get("description") or "")).strip()
                if 10 <= len(desc) <= 400:
                    e["description"] = desc
                    t_en = re.sub(r"\s+", " ", str(r.get("title_en") or "")).strip()
                    if t_en and t_en.lower() != e["title"].lower() and not e.get("title_en"):
                        e["title_en"] = t_en[:200]
                    cache[e["id"]] = {"description": desc, "title_en": e.get("title_en", ""),
                                      "source": f"llm:{cfg['model']}", "created": today.isoformat()}
                    stats["llm"] += 1
    for e in todo:
        if not e.get("description"):
            e["description"] = template(e)
            cache[e["id"]] = {"description": e["description"], "title_en": "", "source": "template",
                              "created": today.isoformat()}
            stats["template"] += 1
    save_cache(cache, {e["id"] for e in events if e.get("id")}, today)
    return stats
