#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Discover shares the upstream catalogs have and this one does not, then add them.

The upstream catalogs move fast — on 2026-09-02, one day after this catalog was
built, they already held 48 share ids it was missing. This script closes that gap
daily.

What it will and will not do:

  * Only ids that answer under HTTP 400 are added. A share the upstream lists but
    that does not resolve never enters the catalog.
  * Name, author and `official_summary` come from the live share page, never from
    the upstream row — same precedence rule the original merge used.
  * Chinese comes from the upstream row when it has one — majiayu000 writes them
    by hand, and a human line beats a fresh translation. Only the remainder is
    translated here, and only those rows are marked `zh_machine: true`, so the
    READMEs can report the split honestly instead of claiming the whole catalog
    is hand-written.
  * Without ANTHROPIC_API_KEY the rows that would need translating are skipped
    for that run; rows carrying upstream Chinese still go in. English is never
    written into a `summary_zh`.
  * MAX_NEW per run caps the blast radius if an upstream ever publishes garbage.

    python3 scripts/sync_upstream.py --dry-run     # report only
    python3 scripts/sync_upstream.py --write       # add to catalog.json

Exit codes: 0 nothing to do or written · 1 error · 3 new rows found in --dry-run
"""

import argparse
import html
import io
import json
import os
import re
import sys
import tarfile
import time
import urllib.error
import urllib.request
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = "awesome-grokbot-sync/1.0 (+https://github.com/kydlikebtc/awesome-grokbot)"

MAX_NEW = 150  # per run; an upstream glitch cannot flood the catalog
PROBE_WORKERS = 6
PROBE_PAUSE = 0.25
TIMEOUT = 30

SHARE_RE = re.compile(r"https://x\.ai/bot/([A-Za-z0-9_-]+)")

UPSTREAMS = [
    {
        "name": "majiayu000/awesome-grok-bot",
        "url": "https://github.com/majiayu000/awesome-grok-bot",
        "kind": "raw-json",
        "raw": "https://raw.githubusercontent.com/majiayu000/awesome-grok-bot/main/catalog.json",
    },
    {
        "name": "cs68614-hash/awesome-grokbot-templates",
        "url": "https://github.com/cs68614-hash/awesome-grokbot-templates",
        "kind": "raw-json",
        "raw": "https://raw.githubusercontent.com/cs68614-hash/awesome-grokbot-templates/main/data/templates.json",
    },
    {
        "name": "ZeroPointRepo/GrokBotDev",
        "url": "https://github.com/ZeroPointRepo/GrokBotDev",
        "kind": "tarball",
        "prefix": "content/templates/",
    },
    {
        "name": "elie222/botdirectory.ai",
        "url": "https://github.com/elie222/botdirectory.ai",
        "kind": "tarball",
        "prefix": "bots/",
    },
]

# Coarse upstream categories -> this catalog's taxonomy. Same tables the original
# merge used; the tag rules below still refine the obvious misfits.
CAT_MAP = {
    "developer": "coding-shipping",
    "engineering": "coding-shipping",
    "personal": "personal-admin",
    "life": "personal-admin",
    "shopping": "personal-admin",
    "real-estate": "personal-admin",
    "productivity": "personal-admin",
    "business": "finance-ops",
    "investor": "finance-ops",
    "finance": "finance-ops",
    "money": "finance-ops",
    "ops": "finance-ops",
    "creator": "content-publishing",
    "marketer": "content-publishing",
    "social-media": "content-publishing",
    "creative": "content-publishing",
    "marketing": "content-publishing",
    "sales": "customer-sales",
    "success": "customer-sales",
    "research": "research-briefings",
    "student": "research-briefings",
    "recruiting": "teams-handoffs",
    "assistants": "teams-handoffs",
    "email": "inbox-calendar",
}

TAG_RULES = [
    ({"email", "gmail", "calendar", "inbox", "scheduling"}, "inbox-calendar"),
    ({"agent-team", "meta-bot", "recruiting", "handoff", "hiring"}, "teams-handoffs"),
    ({"engineering", "developer", "code", "shipping", "devops"}, "coding-shipping"),
    (
        {"research", "digest", "monitoring", "briefing", "learning"},
        "research-briefings",
    ),
    ({"sales", "crm", "outbound", "leads", "support"}, "customer-sales"),
    ({"finance", "invoice", "accounting", "back-office", "investing"}, "finance-ops"),
    (
        {"content", "social-media", "creator", "video", "design", "writing"},
        "content-publishing",
    ),
]


def fetch(url, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        data = r.read()
    return data if binary else data.decode("utf-8", "replace")


def slugify(name):
    s = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return s or "unnamed"


def read_frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not m:
        return {}
    data, stack = {}, None
    for line in m.group(1).split("\n"):
        if not line.strip():
            continue
        indented = line.startswith((" ", "\t"))
        km = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", line)
        if not km:
            continue
        key, val = km.group(1), km.group(2).strip()
        if indented and stack is not None:
            data[stack][key] = val.strip("\"'")
            continue
        if val == "":
            data[key] = {}
            stack = key
            continue
        stack = None
        if val.startswith("[") and val.endswith("]"):
            inner = val[1:-1].strip()
            data[key] = [x.strip().strip("\"'") for x in inner.split(",") if x.strip()]
        else:
            data[key] = val.strip("\"'")
    return data


# --------------------------------------------------------------- collection


def collect_upstream():
    """bot_id -> {'name','summary','category','tags','author','origin','sources'}"""
    found = {}

    def note(bid, src, **fields):
        rec = found.setdefault(bid, {"sources": []})
        if not any(s["catalog"] == src["name"] for s in rec["sources"]):
            rec["sources"].append({"catalog": src["name"], "url": src["url"]})
        for k, v in fields.items():
            if v and not rec.get(k):
                rec[k] = v

    for src in UPSTREAMS:
        try:
            if src["kind"] == "raw-json":
                data = json.loads(fetch(src["raw"]))
                rows = (
                    data["entries"]
                    if isinstance(data, dict) and "entries" in data
                    else (data if isinstance(data, list) else list(data.values())[0])
                )
                for r in rows:
                    url = r.get("import") or r.get("share_url") or ""
                    m = SHARE_RE.search(url)
                    if not m:
                        continue
                    author = None
                    a = r.get("author")
                    if isinstance(a, dict) and a.get("name"):
                        author = {"name": a["name"], "url": a.get("url")}
                    elif r.get("twitter"):
                        author = {
                            "name": r["twitter"],
                            "url": f"https://x.com/{r['twitter']}",
                        }
                    note(
                        m.group(1),
                        src,
                        name=r.get("name"),
                        summary=r.get("summary") or r.get("description"),
                        summary_zh=r.get("summary_zh"),
                        category=r.get("category"),
                        tags=r.get("tags"),
                        author=author,
                        origin=r.get("source") or r.get("origin"),
                    )
            else:
                # One tarball beats hundreds of raw requests, and stays inside
                # the unauthenticated rate limit that broke the contents API.
                blob = fetch(
                    f"https://codeload.github.com/{src['name']}/tar.gz/refs/heads/main",
                    binary=True,
                )
                with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tf:
                    for member in tf.getmembers():
                        if not member.isfile() or not member.name.endswith(".md"):
                            continue
                        rel = member.name.split("/", 1)[-1]
                        if not rel.startswith(src["prefix"]):
                            continue
                        fh = tf.extractfile(member)
                        if fh is None:
                            continue
                        fm = read_frontmatter(fh.read().decode("utf-8", "replace"))
                        url = fm.get("share_url") or fm.get("grok_share_url") or ""
                        m = SHARE_RE.search(url if isinstance(url, str) else "")
                        if not m:
                            continue
                        sharer = (
                            fm.get("sharer")
                            if isinstance(fm.get("sharer"), dict)
                            else {}
                        )
                        handle = sharer.get("handle") or fm.get("contributor")
                        author = None
                        if handle:
                            author = {
                                "name": handle,
                                "url": sharer.get("url")
                                or fm.get("contributor_url")
                                or f"https://x.com/{handle}",
                            }
                        source = (
                            fm.get("source")
                            if isinstance(fm.get("source"), dict)
                            else {}
                        )
                        note(
                            m.group(1),
                            src,
                            name=fm.get("name"),
                            summary=fm.get("tagline") or fm.get("description"),
                            category=fm.get("primary_category") or fm.get("category"),
                            tags=fm.get("tags"),
                            author=author,
                            origin=source.get("url") or fm.get("added_via"),
                        )
            print(f"  read {src['name']}", file=sys.stderr)
        except Exception as exc:  # one bad upstream must not sink the run
            print(f"  WARN {src['name']}: {type(exc).__name__}: {exc}", file=sys.stderr)

    return found


# ------------------------------------------------------------------ probing


def probe(bid):
    """Fetch the live share page. Returns None unless it answers under 400."""
    url = f"https://x.ai/bot/{bid}"
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                if r.status >= 400:
                    return None
                body = r.read().decode("utf-8", "replace")
            break
        except urllib.error.HTTPError:
            return None  # an answer, just not a usable one
        except Exception:
            time.sleep(1.5 * (attempt + 1))
    else:
        return None

    def og(prop):
        m = re.search(
            rf'property=["\']og:{prop}["\'][^>]*content=["\'](.*?)["\']',
            body,
            re.S | re.I,
        )
        return html.unescape(re.sub(r"\s+", " ", m.group(1))).strip() if m else None

    title, desc = og("title"), og("description")
    m = re.match(r"^(.*?)\s+by\s+([^,]+)$", title or "")
    return {
        "name": (m.group(1) if m else title or "").strip() or None,
        "author": m.group(2).strip() if m else None,
        "official_summary": desc,
    }


# -------------------------------------------------------------- translation


def translate(texts, api_key):
    """Batch-translate one-line summaries to Chinese with Claude.

    Returns a list the same length as `texts`, with None where translation
    failed — callers skip those rows rather than shipping English in the
    Chinese README.
    """
    if not texts:
        return []
    numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(texts))
    prompt = (
        "Translate each numbered one-line bot description into concise Simplified Chinese "
        "for a catalog listing. Keep it short and plain, the way a Chinese developer would "
        "write it — not a literal word-for-word rendering. Keep product names, brand names "
        "and technical terms in their original form. No trailing period is needed.\n\n"
        "Reply with ONLY a JSON array of strings, same length and order as the input.\n\n"
        f"{numbered}"
    )
    payload = {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 4000,
        "messages": [{"role": "user", "content": prompt}],
    }
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
            "User-Agent": UA,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            body = json.loads(r.read().decode("utf-8"))
        text = "".join(b.get("text", "") for b in body.get("content", []))
        m = re.search(r"\[.*\]", text, re.S)
        out = json.loads(m.group(0)) if m else None
        if not isinstance(out, list) or len(out) != len(texts):
            print(
                f"  WARN translation returned {len(out) if isinstance(out, list) else '?'} "
                f"items for {len(texts)} inputs",
                file=sys.stderr,
            )
            return [None] * len(texts)
        return [(s.strip() if isinstance(s, str) and s.strip() else None) for s in out]
    except Exception as exc:
        print(
            f"  WARN translation failed: {type(exc).__name__}: {exc}", file=sys.stderr
        )
        return [None] * len(texts)


# ----------------------------------------------------------------- category


def pick_category(upstream_cat, tags, name, blurb):
    base = CAT_MAP.get((upstream_cat or "").strip().lower())
    tagset = {str(t).lower() for t in (tags or [])}
    hay = f"{name} {blurb}".lower()
    for keys, target in TAG_RULES:
        if tagset & keys:
            return target
    if base:
        return base
    for keys, target in TAG_RULES:
        if any(re.search(rf"\b{re.escape(k)}\b", hay) for k in keys):
            return target
    return "personal-admin"


# --------------------------------------------------------------------- main


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="add new rows to catalog.json")
    ap.add_argument("--dry-run", action="store_true", help="report only (default)")
    ap.add_argument("--limit", type=int, default=MAX_NEW)
    ap.add_argument("--date", default=None)
    args = ap.parse_args()

    catalog = json.load(open(os.path.join(ROOT, "catalog.json"), encoding="utf-8"))
    retired = json.load(open(os.path.join(ROOT, "retired.json"), encoding="utf-8"))
    entries = catalog["entries"]

    known = {e["bot_id"] for e in entries}
    # A share we already retired should not be re-added just because an upstream
    # still lists it.
    known |= {r.get("bot_id") for r in retired.get("entries", [])}
    known_slugs = {e["slug"] for e in entries}

    print(f"catalog has {len(entries)} rows; scanning upstreams...", file=sys.stderr)
    upstream = collect_upstream()
    new_ids = [b for b in upstream if b not in known]
    print(
        f"\nupstream ids: {len(upstream)} | already known: {len(upstream) - len(new_ids)} "
        f"| new: {len(new_ids)}"
    )

    if not new_ids:
        print("nothing to add")
        return 0

    if len(new_ids) > args.limit:
        print(f"capping at {args.limit} (found {len(new_ids)}); the rest come next run")
        new_ids = new_ids[: args.limit]

    # Most upstream rows already carry a hand-written Chinese line (majiayu000
    # writes them), so a missing key only costs the rows that actually need
    # translating — it is not a reason to abort the whole run.
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()

    # verify each candidate against the live page before it earns a row
    print(f"\nprobing {len(new_ids)} candidate share pages...", file=sys.stderr)
    from concurrent.futures import ThreadPoolExecutor

    def check(bid):
        r = probe(bid)
        time.sleep(PROBE_PAUSE)
        return bid, r

    alive = {}
    with ThreadPoolExecutor(max_workers=PROBE_WORKERS) as pool:
        for i, (bid, res) in enumerate(pool.map(check, new_ids), 1):
            if res and res.get("name"):
                alive[bid] = res
            if i % 25 == 0:
                print(f"  {i}/{len(new_ids)}", file=sys.stderr)

    print(f"alive: {len(alive)} | did not resolve: {len(new_ids) - len(alive)}")
    if not alive:
        print("no live new shares")
        return 0

    stamp = args.date or time.strftime("%Y-%m-%d")
    ordered = sorted(alive)
    blurbs = []
    drafts = []

    for bid in ordered:
        up = upstream[bid]
        live = alive[bid]
        summary = (up.get("summary") or live.get("official_summary") or "").strip()
        summary = re.sub(r"\s+", " ", summary)
        if len(summary) > 300:
            summary = summary[:297].rsplit(" ", 1)[0] + "..."
        if not summary:
            continue

        slug = slugify(up.get("name") or live["name"])
        if slug in known_slugs:
            slug = f"{slug}-{bid[:4].lower()}"
        known_slugs.add(slug)

        author = {}
        if live.get("author"):
            author["name"] = live["author"]
        upa = up.get("author") or {}
        if upa.get("name") and upa["name"].lower() != author.get("name", "").lower():
            author["handle"] = upa["name"]
        if upa.get("url"):
            author["url"] = upa["url"]
        if not author and upa.get("name"):
            author = {"name": upa["name"], "url": upa.get("url")}

        rec = {
            "slug": slug,
            "name": live["name"],
            "summary": summary,
            "import": f"https://x.ai/bot/{bid}",
            "bot_id": bid,
            "category": pick_category(
                up.get("category"), up.get("tags"), live["name"], summary
            ),
            "sources": up["sources"],
            "first_seen": stamp,
            "checked": stamp,
            "link_status": 200,
            "license": "CC-BY-4.0"
            if any(s["catalog"] == "ZeroPointRepo/GrokBotDev" for s in up["sources"])
            else "CC0-1.0",
        }
        if author.get("name"):
            rec["author"] = {k: v for k, v in author.items() if v}
        if up.get("tags"):
            rec["tags"] = [str(t) for t in up["tags"] if t][:4]
        if live.get("official_summary"):
            rec["official_summary"] = live["official_summary"]
        if up.get("origin"):
            rec["origin"] = up["origin"]

        # An upstream Chinese line (majiayu000 writes them) beats a fresh
        # translation, and is not machine output.
        if up.get("summary_zh"):
            rec["summary_zh"] = up["summary_zh"]
        else:
            blurbs.append(summary)
            rec["_needs_zh"] = len(blurbs) - 1
        drafts.append(rec)

    if blurbs and api_key:
        print(f"\ntranslating {len(blurbs)} summaries...", file=sys.stderr)
        zh = []
        for i in range(0, len(blurbs), 40):  # keep each request small
            zh.extend(translate(blurbs[i : i + 40], api_key))
        for rec in drafts:
            idx = rec.pop("_needs_zh", None)
            if idx is not None:
                if zh[idx]:
                    rec["summary_zh"] = zh[idx]
                    rec["zh_machine"] = True
    elif blurbs:
        print(
            f"\nANTHROPIC_API_KEY is not set — {len(blurbs)} row(s) needing a translated\n"
            "summary will be skipped this run rather than shipped with English in the\n"
            "Chinese README. Rows that arrived with an upstream Chinese line are unaffected.",
            file=sys.stderr,
        )
        for rec in drafts:
            rec.pop("_needs_zh", None)
    else:
        for rec in drafts:
            rec.pop("_needs_zh", None)

    ready = [r for r in drafts if r.get("summary_zh")]
    skipped = len(drafts) - len(ready)
    print(
        f"\nready to add: {len(ready)}"
        + (f" | skipped, no Chinese: {skipped}" if skipped else "")
    )
    for r in ready[:15]:
        tag = "zh:machine" if r.get("zh_machine") else "zh:upstream"
        print(f"  + [{r['category']:19}] {r['name'][:40]:42} {tag}")
    if len(ready) > 15:
        print(f"  ... and {len(ready) - 15} more")

    if not args.write:
        return 3 if ready else 0
    if not ready:
        return 0

    ORDER = [
        "slug",
        "name",
        "aka",
        "author",
        "summary",
        "summary_zh",
        "zh_machine",
        "official_summary",
        "import",
        "bot_id",
        "category",
        "tags",
        "integrations",
        "origin",
        "sources",
        "first_seen",
        "checked",
        "link_status",
        "license",
    ]
    entries.extend({k: r[k] for k in ORDER if k in r} for r in ready)
    entries.sort(key=lambda x: (x["category"], x["name"].lower()))

    counts = Counter(e["category"] for e in entries)
    catalog["entries"] = entries
    catalog["counts"]["live"] = len(entries)
    catalog["counts"]["by_category"] = {
        k: counts.get(k, 0) for k in catalog["counts"]["by_category"]
    }
    catalog["generated"] = stamp

    json.dump(
        catalog,
        open(os.path.join(ROOT, "catalog.json"), "w", encoding="utf-8"),
        ensure_ascii=False,
        indent=2,
    )
    print(f"\nwrote catalog.json: {len(entries)} rows (+{len(ready)})")
    print("now run: python3 scripts/build_readme.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
