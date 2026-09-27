#!/usr/bin/env python3
"""Weekly unattended refresh of data/events.json (run by .github/workflows/weekly-refresh.yml).

1. Runs every scraper in scrapers/ independently (a crash or timeout in one doesn't affect the rest).
2. Merges with the existing data: events a source produced last time are replaced by its fresh results;
   if a source fails (or suddenly returns nothing) its previous events are kept. Events without an
   'origin' field were added by hand and are kept until their date passes.
3. Drops past events, validates, removes duplicates (exact key from refresh.py + fuzzy title match).
4. Writes English descriptions for new events (LLM if LLM_API_KEY is set, template otherwise).
5. Writes data/events.json (with last_updated) and data/scrape-report.json.

Usage: python scripts/weekly.py [--only kurhaus_wiesbaden,alte_oper] [--skip festhalle] [--today 2026-10-05] [--dry-run]
"""
import argparse, json, os, re, signal, sys, time, traceback
from datetime import date, datetime
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import refresh  # noqa: E402  (validate / prune / key / norm)
import describe  # noqa: E402
import scrapers  # noqa: E402
from scrapers.base import Context, BERLIN  # noqa: E402

EVENTS = ROOT / "data" / "events.json"
REPORT = ROOT / "data" / "scrape-report.json"
SOURCE_TIMEOUT = int(os.environ.get("SCRAPER_TIMEOUT", "300"))


class Timeout(Exception):
    pass


def _alarm(signum, frame):
    raise Timeout(f"timed out after {SOURCE_TIMEOUT}s")


def run_source(name, ctx):
    t0 = time.time()
    mod = None
    try:
        mod = scrapers.load(name)
        signal.signal(signal.SIGALRM, _alarm)
        signal.alarm(SOURCE_TIMEOUT)
        try:
            evs = mod.scrape(ctx) or []
        finally:
            signal.alarm(0)
        for e in evs:
            e["origin"] = f"scraper:{mod.SOURCE['id']}"
        return mod, evs, None, time.time() - t0
    except BaseException as ex:  # noqa: BLE001 - isolate every failure
        if isinstance(ex, KeyboardInterrupt):
            raise
        tb = traceback.format_exc(limit=3)
        print(tb, file=sys.stderr)
        return mod, [], f"{type(ex).__name__}: {ex}"[:500], time.time() - t0


# ---------------------------------------------------------------- dedupe
STOP = {"the", "and", "und", "der", "die", "das", "mit", "von", "for", "live", "tour", "concert", "konzert", "2026", "2027", "in", "im", "de"}


def tokens(t):
    return {w for w in refresh.norm(t).split() if len(w) > 2 and w not in STOP}


def core(t):
    """Main part of a title: 'hr-Sinfonieorchester: Titan – Große Reihe' -> 'titan'."""
    t = re.sub(r"^(hr-Sinfonieorchester|Wiener Klassik)\s*[:|]\s*", "", t, flags=re.I)
    t = re.split(r"\s[–—-]\s|\s/\s|\s\|\s|\(|:\s|!", t)[0]
    return refresh.norm(t)


def similar(a, b):
    na, nb = refresh.norm(a), refresh.norm(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    da, db = set(re.findall(r"\d+", na)) - {"2026", "2027"}, set(re.findall(r"\d+", nb)) - {"2026", "2027"}
    if da and db and not (da & db):
        return False  # '2. Sinfoniekonzert' vs '3. Sinfoniekonzert'
    ca, cb = core(a), core(b)
    if len(ca) >= 4 and len(cb) >= 4 and (ca == cb or re.search(r"\b" + re.escape(ca) + r"\b", nb)
                                          or re.search(r"\b" + re.escape(cb) + r"\b", na)):
        return True
    short, long_ = sorted((na, nb), key=len)
    if len(short) >= 6 and re.search(r"\b" + re.escape(short) + r"\b", long_):
        return True
    ta, tb = tokens(a), tokens(b)
    if ta and tb and len(ta & tb) / len(ta | tb) >= 0.6 and len(ta & tb) >= 2:
        return True
    return SequenceMatcher(None, na, nb).ratio() >= 0.85


def occ_dates(e):
    return {o["date"] for o in refresh.occurrences(e)}


def richness(e):
    return (0 if e.get("origin") else 1000) + len(e.get("description", "")) + 20 * bool(e.get("price")) \
        + 20 * bool(e.get("time")) + 5 * len(e.get("dates", []))


def dedupe(events):
    """Exact duplicates (refresh.key) and fuzzy ones: same city, overlapping dates, similar titles.
    The hand-curated record wins over a scraped one; otherwise the richer record wins."""
    out, dropped = [], []
    by_date = {}
    for e in sorted(events, key=richness, reverse=True):
        cands = {id(x): x for d in occ_dates(e) for x in by_date.get((e["city"], d), [])}
        dup = next((x for x in cands.values()
                    if refresh.key(x) == refresh.key(e) or similar(x["title"], e["title"])
                    or (x.get("title_en") and similar(x["title_en"], e["title"]))), None)
        if dup:
            for k in ("time", "price", "address"):
                if not dup.get(k) and e.get(k):
                    dup[k] = e[k]
            dropped.append(f"{e['title']} [{e.get('origin', 'manual')}] = {dup['title']} [{dup.get('origin', 'manual')}]")
            continue
        out.append(e)
        for d in occ_dates(e):
            by_date.setdefault((e["city"], d), []).append(e)
    return out, dropped


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="comma-separated scraper modules to run")
    ap.add_argument("--skip", help="comma-separated scraper modules to skip")
    ap.add_argument("--today")
    ap.add_argument("--dry-run", action="store_true", help="don't write files")
    a = ap.parse_args()

    today = date.fromisoformat(a.today) if a.today else datetime.now(BERLIN).date()
    ctx = Context(today)
    data = json.loads(EVENTS.read_text("utf-8"))
    old = data["events"]
    prev_report = {}
    if REPORT.exists():
        prev_report = {s["id"]: s for s in json.loads(REPORT.read_text("utf-8")).get("sources", [])}

    names = scrapers.MODULES
    if a.only:
        names = [n for n in names if n in a.only.split(",")]
    if a.skip:
        names = [n for n in names if n not in a.skip.split(",")]

    report, fresh, ok_origins = [], [], set()
    for name in names:
        mod, evs, err, secs = run_source(name, ctx)
        sid = mod.SOURCE["id"] if mod else name
        origin = f"scraper:{sid}"
        prev_n = prev_report.get(sid, {}).get("events")
        if prev_n is None:
            prev_n = sum(1 for e in old if e.get("origin") == origin)
        seasonal = bool(getattr(mod, "SEASONAL", False))
        status = "error" if err else ("ok" if evs else "empty")
        broken = status == "error" or (status == "empty" and prev_n > 0 and not seasonal)
        if status == "ok" or (status == "empty" and not broken):
            ok_origins.add(origin)
            fresh += evs
        report.append({"id": sid, "name": mod.SOURCE["name"] if mod else name,
                       "url": mod.SOURCE["url"] if mod else "", "status": status, "events": len(evs),
                       "previous": prev_n, "seconds": round(secs, 1), "error": err or "",
                       "broken": broken})
        print(f"{'BROKEN' if broken else 'ok':6} {sid:26} {status:5} {len(evs):4} events (prev {prev_n}) {secs:5.1f}s {err or ''}")

    # sources not run this time (--only/--skip) keep their previous report line
    ran = {r["id"] for r in report}
    for sid, r in prev_report.items():
        if sid not in ran and sid in {scrapers.load(n).SOURCE["id"] for n in scrapers.MODULES}:
            report.append(dict(r, note="not run this time"))

    # merge: manual events + previous events of sources that didn't deliver + fresh results
    kept_old = [e for e in old if e.get("origin") not in ok_origins]
    combined = [dict(e) for e in kept_old] + fresh
    before = len(combined)
    combined = [p for p in (refresh.prune(e, today) for e in combined) if p]
    pruned = before - len(combined)

    valid, invalid = [], []
    for i, e in enumerate(combined):
        e.setdefault("description", "")
        errs = [m for m in refresh.validate(dict(e, description=e["description"] or "x"), i)]
        if errs and e.get("origin"):
            invalid.append("; ".join(errs))
            continue
        valid.append(e)
    merged, dropped = dedupe(valid)

    for e in merged:
        if not e.get("id"):
            e["id"] = scrapers.base.event_id(e["title"], e["venue"])
    old_ids = {e.get("id") or scrapers.base.event_id(e["title"], e["venue"]) for e in old}
    new_count = sum(1 for e in merged if e["id"] not in old_ids)

    stats = describe.fill(merged, today) if not a.dry_run else {}
    for e in merged:
        e.pop("_text", None)
    merged.sort(key=lambda e: (e["date"], e.get("time") or "99", e["title"]))

    now = datetime.now(BERLIN)
    data["events"] = merged
    data["last_updated"] = now.strftime("%a %-d %b %Y, %H:%M") + " (Berlin time)"
    broken = [r["id"] for r in report if r["broken"]]
    rep = {"generated": now.isoformat(timespec="seconds"), "events_total": len(merged), "new_events": new_count,
           "pruned_past": pruned, "duplicates_removed": len(dropped), "invalid_dropped": len(invalid),
           "descriptions": stats, "broken": broken, "sources": report, "duplicates": dropped[:400]}
    manual = sum(1 for e in merged if not e.get("origin"))
    summary = (f"{len(merged)} events ({new_count} new, {manual} hand-curated kept, {pruned} past dropped, "
               f"{len(dropped)} duplicates removed); {len(report) - len(broken)}/{len(report)} sources healthy")
    print(summary)
    print("descriptions:", stats)
    if invalid:
        print("invalid scraped events dropped:\n  " + "\n  ".join(invalid[:30]))
    if a.dry_run:
        return
    EVENTS.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", "utf-8")
    REPORT.write_text(json.dumps(rep, ensure_ascii=False, indent=1) + "\n", "utf-8")

    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"summary={summary}\ntotal={len(merged)}\nnew={new_count}\nbroken={','.join(broken)}\n")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
            f.write(f"### Weekly refresh\n\n{summary}\n\n| source | status | events | previous | error |\n|---|---|---|---|---|\n")
            for r in report:
                f.write(f"| {r['name']} | {'❌ ' if r['broken'] else ''}{r['status']} | {r['events']} | {r['previous']} | {r['error'][:120]} |\n")


if __name__ == "__main__":
    main()
