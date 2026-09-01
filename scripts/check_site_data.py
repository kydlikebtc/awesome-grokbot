#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify the catalog copy the site will ship is intact before it is published.

Runs in the pages workflow after `cp catalog.json site/catalog.json`. Cheap, but
it turns a silently broken deploy — an empty grid, a stale count in the header —
into a red build.

    python3 scripts/check_site_data.py
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site", "catalog.json")
SRC = os.path.join(ROOT, "catalog.json")

REQUIRED_ROW_FIELDS = ("slug", "name", "summary", "summary_zh", "import", "category")


def main():
    if not os.path.exists(SITE):
        print(f"::error::{SITE} is missing — the build step did not copy it")
        return 1

    site = json.load(open(SITE, encoding="utf-8"))
    src = json.load(open(SRC, encoding="utf-8"))

    problems = []

    if site != src:
        problems.append(
            "site/catalog.json differs from catalog.json — the copy is stale"
        )

    entries = site.get("entries", [])
    if not entries:
        problems.append("catalog has no entries")

    declared = site.get("counts", {}).get("live")
    if declared != len(entries):
        problems.append(
            f"counts.live is {declared} but there are {len(entries)} entries"
        )

    for e in entries:
        missing = [f for f in REQUIRED_ROW_FIELDS if not e.get(f)]
        if missing:
            problems.append(f"{e.get('slug', '?')}: missing {', '.join(missing)}")
            if len(problems) > 12:
                problems.append("...")
                break

    for p in problems:
        print(f"::error::{p}")

    if problems:
        return 1

    print(f"site data ok: {len(entries)} entries, checked {site.get('checked')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
