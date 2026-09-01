# Data & method

How `catalog.json` was built, what was measured versus assumed, and how to reproduce it.

## Pipeline

```
4 community catalogs
        │
        ▼
  merge on bot_id          ← the id inside https://x.ai/bot/<id>
        │                    (duplicates across catalogs collapse into one row)
        ▼
  fetch every share page   ← 6 workers, 0.25s pause, 3 retries on network errors
        │
        ├── HTTP 200  →  enrich with og:title / og:description  →  catalog.json
        └── 404 / 500 →  retired.json
        │
        ▼
  human pass               ← category corrections + Chinese summaries
        │
        ▼
  scripts/build_readme.py  →  README.md + README.zh-CN.md
```

## Numbers from the 2026-09-01 sweep

| Step                                                                                |  Result |
| ----------------------------------------------------------------------------------- | ------: |
| Unique share ids found across the 4 catalogs                                        |     365 |
| Returned HTTP 200                                                                   | **360** |
| Returned 404                                                                        |       4 |
| Returned 500                                                                        |       1 |
| Rows enriched with first-party `og:` metadata                                       |     360 |
| Rows whose live name differs from what the community catalogs recorded              |      32 |
| — of those, substantive (a real rename, or a share now pointing at a different bot) |       5 |
| — of those, qualifier-only (`Cursor Agent (Local)` vs `Cursor Agent`)               |      27 |
| Rows attributable to 2+ upstream catalogs                                           |     334 |
| Rows carrying an origin post link                                                   |     347 |
| Rows given a hand-written Chinese summary in this repo                              |      93 |
| Rows whose auto-assigned category was corrected by hand                             |      30 |

Five further strings matched the share-URL pattern in upstream repos but were documentation placeholders (`REPLACE`, `xxxxxxxx`, a fixture id) and were discarded rather than probed.

## Field precedence

When two sources disagree, this is the order the merge applies. The reasoning matters more than the order:

| Field                   | Wins                       | Why                                                                                                                                                                                                                                                                                                                                                                         |
| ----------------------- | -------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `name`                  | Live share page `og:title` | Community catalogs go stale. 32 rows disagree with the live page — mostly dropped qualifiers, but 5 substantively, including one share that now points at an entirely different bot. Using the live name means the row matches what you see when you click. The community name survives in `aka`, and in 27 of the 32 cases it is arguably the more descriptive of the two. |
| `aka`                   | Community name             | Keeping the old name makes the row findable by people who only know the old one.                                                                                                                                                                                                                                                                                            |
| `author.name`           | Live page display name     | What the author chose to show publicly.                                                                                                                                                                                                                                                                                                                                     |
| `author.handle` / `url` | Community catalog          | The live page shows a display name; the handle and profile link come from the catalogs that recorded the original post.                                                                                                                                                                                                                                                     |
| `summary`               | Community one-liner        | Curated for scanning — median 66 characters. Right length for a list.                                                                                                                                                                                                                                                                                                       |
| `official_summary`      | `og:description`, verbatim | Authoritative, but x.ai truncates it at ~155 characters, so it is stored alongside rather than instead of `summary`.                                                                                                                                                                                                                                                        |
| `summary_zh`            | This repo                  | Editorial translation. 267 rows inherited from `majiayu000/awesome-grok-bot`; the remaining 93 were written here.                                                                                                                                                                                                                                                           |
| `category`              | This repo                  | See below.                                                                                                                                                                                                                                                                                                                                                                  |
| `link_status`           | Measured                   | Never inherited from an upstream catalog.                                                                                                                                                                                                                                                                                                                                   |

## Categories

The eight-way taxonomy is deliberately identical to the one used by [`majiayu000/awesome-grok-bot`](https://github.com/majiayu000/awesome-grok-bot), so the two catalogs stay diffable and rows can be cross-referenced.

Upstream categories were mapped mechanically first (for example GrokBotDev's `developer` → `coding-shipping`), then every mechanically-assigned row was reviewed by hand. That review changed 30 of them. The failure mode of the automatic pass was consistent: keyword rules put family-logistics bots in `inbox-calendar` because they mention calendars, and put a houseplant tracker in `research-briefings` because it "monitors" something. Category is the primary navigation axis of this catalog, so it gets human judgement.

## Reproducing it

```bash
python3 scripts/lint.py                    # validate catalog.json against the schema
python3 scripts/check_links.py             # re-sweep every share, report drift, exit 1 if any died
python3 scripts/check_links.py --write     # also update link_status/checked and move dead rows out
python3 scripts/build_readme.py            # regenerate both READMEs from catalog.json
```

All three are dependency-free — plain `python3`, no `pip install`. `check_links.py` is read-only unless you pass `--write`.

## Known limits

- **Reachability is the only verified property.** No bot in this catalog has been imported and behaviour-tested by the maintainer. A green link does not mean a safe or working bot. See [vetting.md](vetting.md).
- **`official_summary` is truncated at the source.** x.ai cuts `og:description` at roughly 155 characters, sometimes mid-word. It is stored as received rather than silently repaired.
- **Chinese summaries are editorial, not literal.** They are written to be scannable in a list, so they compress rather than translate word for word.
- **Categories are one-per-bot.** Plenty of bots straddle two. The category chosen is the one describing the job the bot is _hired_ for, not every task it can do.
- **`first_seen` comes from upstream metadata** and reflects when a community catalog recorded the bot, not when its author first shared it.
