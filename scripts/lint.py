#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate catalog.json against schema/entry.schema.json, plus catalog-wide rules.

Deliberately dependency-free: CI runs on a bare python3 with no pip install, so
this implements the subset of JSON Schema draft-07 the entry schema actually
uses rather than pulling in `jsonschema`. The schema file stays the single place
where field rules are declared.

    python3 scripts/lint.py          # exits non-zero on any error

Checks beyond the schema:
  - slug and bot_id are unique across the catalog
  - bot_id agrees with the id inside the import URL
  - every live row has link_status 200 (dead links belong in retired.json)
  - counts in the catalog header match the actual entries
  - no entry appears in both catalog.json and retired.json
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
errors = []
warnings = []


def err(msg):
    errors.append(msg)


def warn(msg):
    warnings.append(msg)


# ----------------------------------------------------- minimal schema engine


def validate(node, schema, path, root_schema):
    if "$ref" in schema:  # not used by this schema, but fail loudly if added
        err(f"{path}: $ref is not supported by this validator")
        return

    t = schema.get("type")
    if t == "object":
        if not isinstance(node, dict):
            err(f"{path}: expected object, got {type(node).__name__}")
            return
        for req in schema.get("required", []):
            if req not in node:
                err(f"{path}: missing required field '{req}'")
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for k in node:
                if k not in props:
                    err(f"{path}: unknown field '{k}'")
        for k, v in node.items():
            if k in props:
                validate(v, props[k], f"{path}.{k}", root_schema)
        return

    if t == "array":
        if not isinstance(node, list):
            err(f"{path}: expected array, got {type(node).__name__}")
            return
        if "minItems" in schema and len(node) < schema["minItems"]:
            err(f"{path}: needs at least {schema['minItems']} item(s), has {len(node)}")
        if "maxItems" in schema and len(node) > schema["maxItems"]:
            err(f"{path}: allows at most {schema['maxItems']} item(s), has {len(node)}")
        if "items" in schema:
            for i, item in enumerate(node):
                validate(item, schema["items"], f"{path}[{i}]", root_schema)
        return

    if t == "string":
        if not isinstance(node, str):
            err(f"{path}: expected string, got {type(node).__name__}")
            return
        if "minLength" in schema and len(node) < schema["minLength"]:
            err(f"{path}: shorter than minLength {schema['minLength']}")
        if "maxLength" in schema and len(node) > schema["maxLength"]:
            err(f"{path}: length {len(node)} exceeds maxLength {schema['maxLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], node):
            err(f"{path}: {node!r} does not match {schema['pattern']}")
        if "enum" in schema and node not in schema["enum"]:
            err(f"{path}: {node!r} is not one of {schema['enum']}")
        if schema.get("format") == "uri" and not re.match(r"^https?://", node):
            err(f"{path}: {node!r} is not an http(s) URI")
        return

    if t == "integer":
        if not isinstance(node, int) or isinstance(node, bool):
            err(f"{path}: expected integer, got {type(node).__name__}")
        return

    if "enum" in schema and node not in schema["enum"]:
        err(f"{path}: {node!r} is not one of {schema['enum']}")


# ------------------------------------------------- prose that quotes the data

# docs/method.md states figures in prose. Those are hand-written and drift the
# moment the catalog changes — this repo already shipped a stale 347 once. Each
# entry below pairs the row label in that table with how the number is derived.
METHOD_FACTS = [
    ("Answered under 400 (`alive`)", lambda c, e: c["counts"]["live"]),
    ("Answered 404, stable across two sweeps (`gone`)", lambda c, e: c["counts"]["retired"]),
    ("Rows enriched with first-party `og:` metadata", lambda c, e: sum(1 for x in e if x.get("official_summary"))),
    ("Rows whose live name differs from what the community catalogs recorded", lambda c, e: sum(1 for x in e if x.get("aka"))),
    ("Rows attributable to 2+ upstream catalogs", lambda c, e: sum(1 for x in e if len(x.get("sources", [])) > 1)),
    ("Rows carrying an origin post link", lambda c, e: sum(1 for x in e if x.get("origin"))),
]


def check_method_doc(catalog, entries):
    path = os.path.join(ROOT, "docs", "method.md")
    if not os.path.exists(path):
        warn("docs/method.md is missing")
        return
    text = open(path, encoding="utf-8").read()
    for label, derive in METHOD_FACTS:
        expected = derive(catalog, entries)
        row = None
        for line in text.split("\n"):
            if label in line and line.lstrip().startswith("|"):
                row = line
                break
        if row is None:
            warn(f"docs/method.md: no table row for {label!r}")
            continue
        nums = re.findall(r"\d+", row.split("|")[-2])
        if not nums:
            warn(f"docs/method.md: no figure in the row for {label!r}")
            continue
        stated = int(nums[-1])
        if stated != expected:
            err(f"docs/method.md says {stated} for {label!r}, catalog says {expected}")


# --------------------------------------------------------------------- main


def main():
    schema_path = os.path.join(ROOT, "schema", "entry.schema.json")
    schema = json.load(open(schema_path, encoding="utf-8"))
    catalog = json.load(open(os.path.join(ROOT, "catalog.json"), encoding="utf-8"))
    retired = json.load(open(os.path.join(ROOT, "retired.json"), encoding="utf-8"))

    entries = catalog["entries"]
    print(
        f"linting {len(entries)} entries against {os.path.relpath(schema_path, ROOT)}"
    )

    slugs, ids = {}, {}
    for i, e in enumerate(entries):
        label = e.get("slug") or f"entries[{i}]"
        validate(e, schema, label, schema)

        slug = e.get("slug")
        if slug in slugs:
            err(f"{label}: duplicate slug, also used by entry #{slugs[slug]}")
        elif slug:
            slugs[slug] = i

        bid = e.get("bot_id")
        if bid in ids:
            err(f"{label}: duplicate bot_id {bid!r}, also used by {ids[bid]!r}")
        elif bid:
            ids[bid] = slug

        imp = e.get("import", "")
        m = re.match(r"^https://x\.ai/bot/([A-Za-z0-9_-]+)$", imp)
        if m and bid and m.group(1) != bid:
            err(f"{label}: bot_id {bid!r} does not match import url id {m.group(1)!r}")

        if e.get("link_status") != 200:
            err(
                f"{label}: link_status is {e.get('link_status')}; only HTTP 200 belongs in catalog.json"
            )

        if (
            e.get("summary")
            and e["summary"].strip() == (e.get("summary_zh") or "").strip()
        ):
            warn(f"{label}: summary_zh is identical to summary — untranslated?")

    # catalog-level invariants
    declared = catalog.get("counts", {})
    if declared.get("live") != len(entries):
        err(
            f"counts.live is {declared.get('live')} but there are {len(entries)} entries"
        )
    if declared.get("retired") != len(retired.get("entries", [])):
        err(
            f"counts.retired is {declared.get('retired')} but retired.json has {len(retired.get('entries', []))}"
        )

    by_cat = declared.get("by_category", {})
    actual = {}
    for e in entries:
        actual[e["category"]] = actual.get(e["category"], 0) + 1
    for cat, want in by_cat.items():
        if actual.get(cat, 0) != want:
            err(
                f"counts.by_category['{cat}'] is {want} but {actual.get(cat, 0)} entries have it"
            )
    for cat in actual:
        if cat not in by_cat:
            err(
                f"category '{cat}' is used by entries but missing from counts.by_category"
            )

    check_method_doc(catalog, entries)

    retired_ids = {r.get("bot_id") for r in retired.get("entries", [])}
    both = retired_ids & set(ids)
    if both:
        err(f"bot ids appear in BOTH catalog.json and retired.json: {sorted(both)}")

    for w in warnings:
        print(f"  warn  {w}")
    for e_ in errors:
        print(f"  ERROR {e_}")

    print(
        f"\n{len(entries)} entries | {len(errors)} error(s) | {len(warnings)} warning(s)"
    )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
