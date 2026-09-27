#!/usr/bin/env python3
"""Open/update/close the single "Scraper health" GitHub issue from data/scrape-report.json.
Needs the gh CLI and GH_TOKEN (the workflow passes github.token). Run from the repo root."""
import json, os, subprocess, sys
from pathlib import Path

TITLE = "Scraper health"
report = json.loads(Path("data/scrape-report.json").read_text("utf-8"))
repo = os.environ.get("GITHUB_REPOSITORY", "")
run_url = f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/{repo}/actions/runs/{os.environ.get('GITHUB_RUN_ID', '')}"


def gh(*args, check=True):
    r = subprocess.run(["gh", *args], capture_output=True, text=True)
    if check and r.returncode:
        print(r.stderr, file=sys.stderr)
        sys.exit(r.returncode)
    return r.stdout.strip()


issues = json.loads(gh("issue", "list", "--state", "open", "--search", f'in:title "{TITLE}"',
                       "--json", "number,title", "--limit", "20") or "[]")
issue = next((i["number"] for i in issues if i["title"] == TITLE), None)
broken = [s for s in report["sources"] if s["broken"]]

if broken:
    lines = [f"The weekly refresh on {report['generated'][:10]} found **{len(broken)} broken source(s)** "
             f"([workflow run]({run_url})). Their previous events were kept on the site.", "",
             "| source | status | events now | events before | error |", "|---|---|---|---|---|"]
    for s in broken:
        err = (s["error"] or "returned 0 events").replace("|", "\\|").replace("\n", " ")[:300]
        lines.append(f"| [{s['name']}]({s['url']}) (`scrapers/{s['id']}.py`) | {s['status']} | {s['events']} | {s['previous']} | {err} |")
    lines += ["", "How to fix: see *Fixing a scraper* in the README. This issue closes automatically "
              "when every source is healthy again."]
    body = "\n".join(lines)
    if issue:
        gh("issue", "edit", str(issue), "--body", body)
        gh("issue", "comment", str(issue), "--body", f"Still broken on {report['generated'][:10]}: "
           + ", ".join(s["id"] for s in broken) + f" ([run]({run_url}))")
        print(f"updated issue #{issue}")
    else:
        print(gh("issue", "create", "--title", TITLE, "--body", body))
elif issue:
    gh("issue", "comment", str(issue), "--body", f"All {len(report['sources'])} sources healthy again "
       f"on {report['generated'][:10]} ([run]({run_url})). Closing.")
    gh("issue", "close", str(issue))
    print(f"closed issue #{issue}")
else:
    print("all sources healthy; no issue open")
