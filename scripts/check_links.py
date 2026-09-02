#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Re-sweep every share link and report drift against the committed catalog.

An HTTP status carries one of two very different meanings, and conflating them
is how link checkers earn a reputation for crying wolf:

  * a statement about the resource   — 404/410: the bot really is not there
  * a statement about the requester  — 403/429/503 behind a bot wall: we were
    turned away, which says nothing at all about whether the bot exists

A checker that reports the second as the first will, the first time x.ai puts a
challenge in front of a datacenter IP, declare all 361 shares dead. So results
land in one of four buckets and only one of them counts as a dead link:

  alive       answered under 400
  gone        404/410, or another 4xx with no wall signature. The bot is not
              there. This is the ONLY bucket --write moves out of the catalog
  blocked     a throttle status carrying a wall signature, or a non-HTTP bot
              code. Reported separately, never treated as breakage
  flaky       5xx, a timeout, or no answer after retries. A statement about the
              host, not about the bot

The flaky bucket is not hypothetical: the 2026-09-01 sweep saw one share return
500, and it answered 200 the next time it was asked. Under a status != 200 rule
that bot was wrongly retired.

A circuit breaker guards the whole run. If more than CIRCUIT_BREAKER of the
sweep comes back blocked or flaky, the problem is the network path, not the
catalog, and the script refuses to write.

    python3 scripts/check_links.py                 # report only
    python3 scripts/check_links.py --write         # move `gone` rows to retired.json
    python3 scripts/check_links.py --limit 20      # quick smoke test

Exit codes: 0 clean · 1 dead links found · 2 circuit breaker tripped

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
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = "awesome-grokbot-linkcheck/1.0 (+https://github.com/kydlikebtc/awesome-grokbot)"
WORKERS = 6
PAUSE = 0.25
TIMEOUT = 25
RETRIES = 3

# Fraction of the sweep that may come back blocked/flaky before we conclude the
# network path is the problem rather than the catalog.
CIRCUIT_BREAKER = 0.25

# Statuses that are a throttle or a bot code rather than a claim about the resource.
THROTTLE_STATUS = {403, 429, 503}
# Statuses that genuinely say "not here".
GONE_STATUS = {404, 410}

BODY_MARKERS = (
    re.compile(r"cf-browser-verification|cf_chl_opt|__cf_chl", re.I),
    re.compile(r"Just a moment\.\.\.", re.I),
    re.compile(r"Checking your browser before accessing", re.I),
    re.compile(r"Attention Required!\s*\|\s*Cloudflare", re.I),
    re.compile(r"<title>\s*Access denied", re.I),
    re.compile(r"captcha", re.I),
)

OG_TITLE = r'property=["\']og:title["\'][^>]*content=["\'](.*?)["\']'
OG_DESC = r'property=["\']og:description["\'][^>]*content=["\'](.*?)["\']'


def grab(pattern, text):
    m = re.search(pattern, text, re.S | re.I)
    if not m:
        return None
    return html.unescape(re.sub(r"\s+", " ", m.group(1))).strip() or None


def wall_signature(status, headers, body):
    """Return a reason string if this status is about us, or None if it is about the resource."""
    lower = {k.lower(): v for k, v in headers.items()}

    mitigated = lower.get("cf-mitigated", "")
    if "challenge" in mitigated.lower():
        return "cf-mitigated: challenge"

    if status >= 900:
        return f"non-standard status {status}, a bot code rather than an HTTP status"

    # RFC 9110 is explicit that 429 is a temporary condition.
    if status == 429:
        return "429, rate limited rather than missing"

    if status not in THROTTLE_STATUS:
        return None

    if "retry-after" in lower:
        return f"{status} with a Retry-After header, a temporary refusal"

    if any(rx.search(body) for rx in BODY_MARKERS):
        return f"{status} serving an interstitial challenge page"

    # A throttle status from a CDN edge with no real body: the edge answered and
    # the origin was never asked. Still not a statement about the bot.
    cdn = "cloudflare" in lower.get("server", "").lower() or "cf-ray" in lower
    if cdn and len(body.strip()) < 512:
        return f"{status} from a CDN edge with no page body"

    return None


def probe(entry):
    """Fetch one share page and put it in exactly one bucket."""
    url = entry["import"]
    out = {
        "slug": entry["slug"],
        "name": entry["name"],
        "url": url,
        "bucket": None,
        "status": None,
        "detail": "",
        "og_title": None,
        "og_description": None,
    }

    status = headers = None
    body = ""
    last_error = None

    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                status, headers = resp.status, dict(resp.headers)
                body = resp.read().decode("utf-8", "replace")
            break
        except urllib.error.HTTPError as e:
            # An HTTP error is an answer; do not retry it.
            status, headers = e.code, dict(e.headers)
            try:
                body = e.read().decode("utf-8", "replace")
            except Exception:
                body = ""
            break
        except Exception as e:
            last_error = f"{type(e).__name__}: {e}"
            time.sleep(1.5 * (attempt + 1))

    time.sleep(PAUSE)

    if status is None:
        out["bucket"] = "flaky"
        out["detail"] = last_error or "no answer after retries"
        return out

    out["status"] = status

    if status < 400:
        out["bucket"] = "alive"
        out["detail"] = str(status)
        out["og_title"] = grab(OG_TITLE, body)
        out["og_description"] = grab(OG_DESC, body)
        return out

    sig = wall_signature(status, headers or {}, body)
    if sig:
        out["bucket"] = "blocked"
        out["detail"] = sig
        return out

    if 500 <= status < 600:
        # The host stumbled. That is not a claim that the bot is gone — the
        # 2026-09-01 sweep proved it, with a 500 that answered 200 next time.
        out["bucket"] = "flaky"
        out["detail"] = f"{status} server error, not a statement about the bot"
        return out

    out["bucket"] = "gone"
    out["detail"] = f"{status}" + (
        " not found" if status in GONE_STATUS else " with no wall signature"
    )
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--write", action="store_true", help="move `gone` rows into retired.json"
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

    buckets = Counter(r["bucket"] for r in results.values())
    gone = [r for r in results.values() if r["bucket"] == "gone"]
    blocked = [r for r in results.values() if r["bucket"] == "blocked"]
    flaky = [r for r in results.values() if r["bucket"] == "flaky"]

    print(f"\nLinks checked: {len(results)}")
    for b in ("alive", "gone", "blocked", "flaky"):
        print(f"  {b:<8} {buckets[b]}")

    for r in gone:
        print(f"  GONE     {r['slug']:38} {r['detail']}  {r['url']}")
    for r in blocked:
        print(f"  blocked  {r['slug']:38} {r['detail']}")
    for r in flaky:
        print(f"  flaky    {r['slug']:38} {r['detail']}")

    # renames, only meaningful for pages that answered
    renamed = []
    for e in todo:
        r = results[e["slug"]]
        if r["bucket"] != "alive" or not r["og_title"]:
            continue
        m = re.match(r"^(.*?)\s+by\s+([^,]+)$", r["og_title"])
        live = (m.group(1) if m else r["og_title"]).strip()
        if live and live.lower() != e["name"].lower():
            renamed.append((e, live))
    if renamed:
        print(f"\nRENAMED  {len(renamed)}")
        for e, live in renamed:
            print(f"  {e['slug']:38} catalog={e['name']!r} live={live!r}")

    # circuit breaker
    suspect = buckets["blocked"] + buckets["flaky"]
    tripped = len(results) > 0 and suspect / len(results) > CIRCUIT_BREAKER
    if tripped:
        pct = suspect / len(results) * 100
        print(
            f"\nCIRCUIT BREAKER: {suspect}/{len(results)} ({pct:.0f}%) came back blocked or flaky, "
            f"over the {CIRCUIT_BREAKER:.0%} threshold.\n"
            "That pattern means the network path is the problem, not the catalog. "
            "Nothing was written. Re-run from a different network before touching the data."
        )
        return 2

    if args.write:
        stamp = args.date or time.strftime("%Y-%m-%d")

        # Sync names and blurbs from the live page. Without this the catalog
        # slowly drifts away from what a reader sees when they click, which is
        # the one thing it promises not to do. Three rows had been renamed in
        # the day after the first build alone.
        applied = 0
        for e in entries:
            r = results.get(e["slug"])
            if not r or r["bucket"] != "alive":
                continue
            if r.get("og_title"):
                m = re.match(r"^(.*?)\s+by\s+([^,]+)$", r["og_title"])
                live = (m.group(1) if m else r["og_title"]).strip()
                if live and live.lower() != e["name"].lower():
                    # aka keeps the *earliest* known name, so a row stays
                    # findable by whatever people first called it.
                    e.setdefault("aka", e["name"])
                    e["name"] = live
                    applied += 1
                # renamed back to what aka records -> the alias is noise now
                if e.get("aka") and e["aka"].lower() == e["name"].lower():
                    e.pop("aka")
            if r.get("og_description") and r["og_description"] != e.get(
                "official_summary"
            ):
                e["official_summary"] = r["og_description"]
        if applied:
            print(f"\napplied {applied} rename(s) from the live pages")

        # Partition once, whether or not anything is gone. An earlier version
        # nested this under `if not gone`, which meant a real dead link was
        # never actually moved — the one case the branch exists for.
        gone_slugs = {r["slug"] for r in gone}
        retired = json.load(open(os.path.join(ROOT, "retired.json"), encoding="utf-8"))
        keep, moved = [], []
        for e in entries:
            r = results.get(e["slug"])
            if e["slug"] in gone_slugs:
                e["link_status"] = r["status"]
                e["checked"] = stamp
                moved.append(e)
                continue
            if r and r["bucket"] == "alive":
                e["checked"] = stamp
                e["link_status"] = 200
            keep.append(e)

        catalog["entries"] = keep
        catalog["checked"] = stamp
        catalog["generated"] = stamp
        counts = Counter(e["category"] for e in keep)
        catalog["counts"]["live"] = len(keep)
        catalog["counts"]["by_category"] = {
            k: counts.get(k, 0) for k in catalog["counts"]["by_category"]
        }

        if moved:
            retired["entries"].extend(moved)
            retired["checked"] = stamp
            catalog["counts"]["retired"] = len(retired["entries"])
            json.dump(
                retired,
                open(os.path.join(ROOT, "retired.json"), "w", encoding="utf-8"),
                ensure_ascii=False,
                indent=2,
            )

        json.dump(
            catalog,
            open(os.path.join(ROOT, "catalog.json"), "w", encoding="utf-8"),
            ensure_ascii=False,
            indent=2,
        )
        if moved:
            print(f"\nmoved {len(moved)} row(s) to retired.json; {len(keep)} live")
        else:
            print(f"wrote catalog.json ({len(keep)} live, checked {stamp})")
        print("now run: python3 scripts/build_readme.py")

        if blocked or flaky:
            print(
                f"left {len(blocked) + len(flaky)} blocked/flaky row(s) in the catalog on purpose — "
                "those statuses are not evidence the bot is gone"
            )

    return 1 if gone else 0


if __name__ == "__main__":
    sys.exit(main())
