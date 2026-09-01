#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Assert every share URL is a canonical https://x.ai/bot/<id> link.

Split out of the CI workflow into a real script so it can be run locally and so
the workflow contains no inline code.

    python3 scripts/check_canonical.py
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANONICAL = re.compile(r"^https://x\.ai/bot/[A-Za-z0-9_-]+$")


def main():
    bad = []
    total = 0
    for fname in ("catalog.json", "retired.json"):
        doc = json.load(open(os.path.join(ROOT, fname), encoding="utf-8"))
        for e in doc["entries"]:
            total += 1
            if not CANONICAL.match(e.get("import", "")):
                bad.append((fname, e.get("slug"), e.get("import")))

    for fname, slug, url in bad:
        print(f"::error::{fname}: {slug}: non-canonical share url {url!r}")

    print(f"{total} share urls checked, {len(bad)} non-canonical")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
