#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Re-sweep every share link and report drift against the committed catalog.

This is the script that backs the "links checked" badge. It is read-only by
default: it prints what changed and exits non-zero if anything went dead, but it
does not rewrite catalog.json unless you pass --write.

    python3 scripts/check_links.py                 # report only
    python3 scripts/check_links.py --write         # also update checked/link_status,
                                                   # and move dead rows to retired.json
    python3 scripts/check_links.py --limit 20      # quick smoke test

Rate limiting is intentional (6 workers, 0.25s pause each). These are other
people's pages; sweep them politely.
"""

import argparse
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = "awesome-grokbot-linkcheck/1.0 (+https://github.com/kydlikebtc/awesome-grokbot)"
WORKERS = 6
PAUSE = 0.25
TIMEOUT = 25
RETRIES = 3

OG_TITLE = r'property=["\']og:title["\'][^>]*content=["\'](.*?)["\']'
OG_DESC = r'property=["\']og:description["\'][^>]*content=["\'](.*?)["\']'


def grab(pattern, text):
    m = re.search(pattern, text, re.S | re.I)
    if not m:
        return None
    return html.unescape(re.sub(r"\s+", " ", m.group(1))).strip() or None


def probe(entry):
    """Fetch one share page. Network errors retry; HTTP errors do not."""
    url = entry["import"]
    out = {
        "slug": entry["slug"],
        "status": None,
        "og_title": None,
        "og_description": None,
        "error": None,
    }
    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                out["status"] = resp.status
                body = resp.read().decode("utf-8", "replace")
            out["og_title"] = grab(OG_TITLE, body)
            out["og_description"] = grab(OG_DESC, body)
            break
        except urllib.error.HTTPError as e:
            out["status"] = e.code
            out["error"] = f"HTTP {e.code}"
            break
        except Exception as e:
            out["error"] = f"{type(e).__name__}: {e}"
            time.sleep(1.5 * (attempt + 1))
    time.sleep(PAUSE)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--write",
        action="store_true",
        help="update catalog.json and retired.json in place",
    )
    ap.add_argument(
        "--limit", type=int, default=0, help="only check the first N entries"
    )
    ap.add_argument(
        "--date", default=None, help="date to stamp as `checked` (YYYY-MM-DD)"
    )
    args = ap.parse_args()

    catalog = json.load(open(os.path.join(ROOT, "catalog.json"), encoding="utf-8"))
    entries = catalog["entries"]
    todo = entries[: args.limit] if args.limit else entries
    print(
        f"sweeping {len(todo)} share links with {WORKERS} workers...", file=sys.stderr
    )

    results = {}
    done = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for r in pool.map(probe, todo):
            results[r["slug"]] = r
            done += 1
            if done % 25 == 0:
                print(f"  {done}/{len(todo)}", file=sys.stderr)

    dead, renamed, ok = [], [], 0
    for e in todo:
        r = results[e["slug"]]
        if r["status"] != 200:
            dead.append((e, r))
            continue
        ok += 1
        title = r["og_title"] or ""
        m = re.match(r"^(.*?)\s+by\s+([^,]+)$", title)
        live_name = (m.group(1) if m else title).strip()
        if live_name and live_name.lower() != e["name"].lower():
            renamed.append((e, live_name))

    print(f"\nOK        {ok}")
    print(f"DEAD      {len(dead)}")
    print(f"RENAMED   {len(renamed)}")

    for e, r in dead:
        print(f"  dead    {e['slug']:38} {r['status'] or r['error']}  {e['import']}")
    for e, live_name in renamed:
        print(f"  renamed {e['slug']:38} catalog={e['name']!r} live={live_name!r}")

    if args.write:
        stamp = args.date or time.strftime("%Y-%m-%d")
        dead_slugs = {e["slug"] for e, _ in dead}
        retired = json.load(open(os.path.join(ROOT, "retired.json"), encoding="utf-8"))
        moved = []
        keep = []
        for e in entries:
            if e["slug"] in dead_slugs:
                r = results[e["slug"]]
                e["link_status"] = r["status"]
                e["checked"] = stamp
                moved.append(e)
            else:
                if e["slug"] in results:
                    e["checked"] = stamp
                    e["link_status"] = 200
                keep.append(e)
        catalog["entries"] = keep
        catalog["checked"] = stamp
        catalog["generated"] = stamp
        counts = {}
        for e in keep:
            counts[e["category"]] = counts.get(e["category"], 0) + 1
        catalog["counts"]["live"] = len(keep)
        catalog["counts"]["by_category"] = {
            k: counts.get(k, 0) for k in catalog["counts"]["by_category"]
        }
        retired["entries"].extend(moved)
        retired["checked"] = stamp
        catalog["counts"]["retired"] = len(retired["entries"])

        json.dump(
            catalog,
            open(os.path.join(ROOT, "catalog.json"), "w", encoding="utf-8"),
            ensure_ascii=False,
            indent=2,
        )
        json.dump(
            retired,
            open(os.path.join(ROOT, "retired.json"), "w", encoding="utf-8"),
            ensure_ascii=False,
            indent=2,
        )
        print(
            f"\nwrote catalog.json ({len(keep)} live) and retired.json ({len(retired['entries'])} retired)"
        )
        print("now run: python3 scripts/build_readme.py")

    return 1 if dead else 0


if __name__ == "__main__":
    sys.exit(main())
