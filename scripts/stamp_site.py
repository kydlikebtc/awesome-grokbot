#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stamp the live share count into site/index.html's social metadata.

    python3 scripts/stamp_site.py            # rewrite in place
    python3 scripts/stamp_site.py --check    # exit 1 if it would change anything

`<meta name="description">` and `<meta property="og:description">` are what
search results and link unfurls in Slack, X and iMessage show. They are static
HTML, so a count written into them freezes on the day it was typed -- these two
said "361" while the catalog held 2042, a figure five times too small on the one
line most people read before deciding whether to click.

The page itself renders counts from catalog.json at runtime and was always
right; only the pre-JavaScript metadata went stale, which is exactly the part no
one looks at while developing.

Run by the pages workflow before upload, so what ships is always current while
the file in git keeps a real number and stays viewable on its own.

Exits non-zero when a pattern matches nothing. A silent no-op here would put the
count straight back to rotting, which is the failure this script exists to stop.
"""

import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, "site", "index.html")

# Group 2 is the count. `\s+` rather than a literal newline plus indent, because
# the repo runs a formatter over this HTML and any reflow of the <meta> tags
# would otherwise break the match -- which now aborts the build rather than
# passing silently, so a brittle pattern would be a self-inflicted outage.
PATTERNS = [
    (
        "meta description",
        re.compile(
            r'(name="description"\s+content=")(\d[\d,]*)(?= live x\.ai/bot shares)'
        ),
    ),
    (
        "og:description",
        re.compile(
            r'(property="og:description"\s+content=")(\d[\d,]*)(?= live x\.ai/bot shares)'
        ),
    ),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--check",
        action="store_true",
        help="report what would change and exit 1 if anything would, without writing",
    )
    args = ap.parse_args()

    catalog = json.load(open(os.path.join(ROOT, "catalog.json"), encoding="utf-8"))
    live = catalog["counts"]["live"]
    html = open(INDEX, encoding="utf-8").read()

    missing = [label for label, rx in PATTERNS if not rx.search(html)]
    if missing:
        print(
            f"STOP: {', '.join(missing)} did not match site/index.html.\n"
            "The markup or the wording moved, so the count can no longer be stamped.\n"
            "Fix the pattern in this script -- leaving it unmatched puts the social\n"
            "metadata back to advertising whatever number was last typed by hand.",
            file=sys.stderr,
        )
        return 2

    stale = []
    for label, rx in PATTERNS:
        found = rx.search(html).group(2)
        if found.replace(",", "") != str(live):
            stale.append(f"{label}: {found} -> {live}")
        # \g<1> keeps the matched attribute prefix; only the digits change.
        html = rx.sub(rf"\g<1>{live}", html)

    if args.check:
        if stale:
            print("site/index.html social metadata is behind catalog.json:")
            for s in stale:
                print(f"  {s}")
            print("\nrun: python3 scripts/stamp_site.py")
            return 1
        print(f"social metadata already reads {live}")
        return 0

    if not stale:
        print(f"social metadata already reads {live}, nothing to do")
        return 0

    open(INDEX, "w", encoding="utf-8").write(html)
    for s in stale:
        print(f"  {s}")
    print(f"stamped {live} into {len(stale)} place(s) in site/index.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
