#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Print catalog counts, for the daily workflow to diff before and after a run.

    python3 scripts/counts.py                  # human readable
    python3 scripts/counts.py --json           # {"live":405,"retired":4,...}
    python3 scripts/counts.py --since a.json   # one-line delta vs an earlier snapshot

Kept as a script rather than inline YAML so the workflow stays free of embedded
code and this stays testable on its own.
"""

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def snapshot():
    cat = json.load(open(os.path.join(ROOT, "catalog.json"), encoding="utf-8"))
    ret = json.load(open(os.path.join(ROOT, "retired.json"), encoding="utf-8"))
    e = cat["entries"]
    return {
        "live": len(e),
        "retired": len(ret.get("entries", [])),
        "zh_machine": sum(1 for x in e if x.get("zh_machine")),
        "zh_human": sum(
            1 for x in e if x.get("summary_zh") and not x.get("zh_machine")
        ),
        "checked": cat.get("checked", ""),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--since", help="path to an earlier --json snapshot")
    args = ap.parse_args()

    now = snapshot()

    if args.since:
        try:
            before = json.load(open(args.since, encoding="utf-8"))
        except Exception:
            before = {}
        added = now["live"] - before.get("live", now["live"])
        retired = now["retired"] - before.get("retired", now["retired"])
        bits = []
        if added > 0:
            bits.append(f"+{added} new")
        elif added < 0:
            bits.append(f"{added} rows")
        if retired > 0:
            bits.append(f"{retired} retired")
        if now["checked"] != before.get("checked"):
            bits.append(f"checked {now['checked']}")
        # empty means the run found nothing to change; the workflow skips the commit
        print(", ".join(bits))
        return 0

    if args.json:
        json.dump(now, sys.stdout)
        print()
        return 0

    for k, v in now.items():
        print(f"{k:12} {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
