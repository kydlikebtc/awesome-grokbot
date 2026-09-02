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
        ├── alive    <400          →  enrich with og:title / og:description  →  catalog.json
        ├── gone     404/410       →  retired.json
        ├── blocked  bot wall      →  stays in catalog, reported separately
        └── flaky    5xx / timeout →  stays in catalog, reported separately
        │
        ▼
  human pass               ← category corrections + Chinese summaries
        │
        ▼
  scripts/build_readme.py  →  README.md + README.zh-CN.md
```

## Numbers from the first build, 2026-09-01

| Step                                                                                |  Result |
| ----------------------------------------------------------------------------------- | ------: |
| Unique share ids found across the 4 catalogs                                        |     365 |
| Answered under 400 (`alive`)                                                        | **361** |
| Answered 404, stable across two sweeps (`gone`)                                     |       4 |
| Answered 500 once, then 200 (`flaky` — kept, see below)                             |       1 |
| Rows enriched with first-party `og:` metadata                                       |     361 |
| Rows whose live name differs from what the community catalogs recorded              |      32 |
| — of those, substantive (a real rename, or a share now pointing at a different bot) |       5 |
| — of those, qualifier-only (`Cursor Agent (Local)` vs `Cursor Agent`)               |      27 |
| Rows attributable to 2+ upstream catalogs                                           |     335 |
| Rows carrying an origin post link                                                   |     348 |
| Rows given a hand-written Chinese summary in this repo                              |      93 |
| Rows whose auto-assigned category was corrected by hand                             |      30 |

> These figures are a **snapshot of the first build** and are deliberately not updated. The catalog grows daily via [`scripts/sync_upstream.py`](../scripts/sync_upstream.py); for current counts see the badge in the README, or `counts` in [`catalog.json`](../catalog.json).

Five further strings matched the share-URL pattern in upstream repos but were documentation placeholders (`REPLACE`, `xxxxxxxx`, a fixture id) and were discarded rather than probed.

## Why a status code is not a verdict

The first version of the sweep used `status != 200` to mean "dead". That rule was wrong, and it was wrong in a way the very first run demonstrated: `Receipt Scanner / Expense Tracking` answered 500 during the sweep and was retired. Asked again, it answered 200. It had never stopped existing — the host stumbled for one request and a live bot was dropped from the catalog for it.

The fix is to notice that an HTTP status answers one of two different questions:

- **about the resource** — 404/410: the bot really is not there
- **about the requester** — 403/429/503 behind a bot wall: we were turned away, which says nothing about the bot

[`scripts/check_links.py`](../scripts/check_links.py) now sorts every result into four buckets, and only one of them is treated as breakage:

| Bucket    | Meaning                                                                                                                                                               | Moved out of the catalog by `--write`? |
| --------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :------------------------------------: |
| `alive`   | answered under 400                                                                                                                                                    |                   no                   |
| `gone`    | 404/410, or another 4xx with no wall signature                                                                                                                        |                **yes**                 |
| `blocked` | throttle status with a wall signature, or a non-HTTP bot code (`cf-mitigated: challenge`, `Retry-After`, an interstitial page, a CDN edge with no body, status ≥ 900) |                   no                   |
| `flaky`   | 5xx, timeout, or no answer after retries                                                                                                                              |                   no                   |

A **circuit breaker** guards the run as a whole: if more than 25% of a sweep comes back `blocked` or `flaky`, the network path is the problem rather than the catalog, so the script reports, refuses to write, and exits 2. The weekly workflow files that as an infrastructure issue with different wording, so a Cloudflare challenge in front of the CI runner can never be mistaken for 361 dead bots.

The bucket rules are borrowed, with thanks, from [`ZeroPointRepo/awesome-grok-bot`](https://github.com/ZeroPointRepo/awesome-grok-bot)'s `check-links.mjs`, which makes the argument better than this paragraph does: reporting a 403 as breakage trains a maintainer to ignore the alarm.

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

## Kept current daily

[`.github/workflows/daily-update.yml`](../.github/workflows/daily-update.yml) runs at 05:17 UTC every day and does three things:

1. **Re-checks every share already listed** with the four-bucket sweep above. Only `gone` (404/410) rows move to `retired.json`; a challenge page or a 5xx leaves the row alone.
2. **Pulls in shares the upstream catalogs have gained**, via [`scripts/sync_upstream.py`](../scripts/sync_upstream.py). This matters more than it sounds: one day after the first build, the four upstreams already held 48 ids this catalog was missing.
3. **Regenerates both READMEs, validates, and commits** — but only if `lint.py` passes.

What the sync will not do:

| Guard | Why |
| --- | --- |
| Only ids answering under HTTP 400 are added | An upstream listing a dead share never propagates the dead link here |
| Name, author and `official_summary` read from the live page | Same precedence as the first build — upstream rows go stale |
| An id already in `retired.json` is never re-added | Otherwise a stale upstream would resurrect it every night |
| At most `MAX_NEW` (150) rows per run | Caps the blast radius if an upstream ever publishes garbage |
| Circuit breaker aborts the whole run | A bot wall in front of the CI runner cannot retire the catalog |
| `lint.py` must pass before the commit | A schema-invalid row never reaches `main` |

### Chinese on new rows

Where an upstream row already carries a Chinese one-liner, that is used as-is — `majiayu000/awesome-grok-bot` writes them by hand, and a human line beats a fresh translation. Only the remainder is machine-translated, and those rows are marked `zh_machine: true`.

The READMEs report the split rather than claiming the whole catalog is hand-written: when any generated rows exist, the figure reads *"N rows with a Chinese summary — X written by hand, Y generated by the daily sync"*.

Translation needs an `ANTHROPIC_API_KEY` repository secret. Without it the sync still runs and still adds every row that arrived with upstream Chinese; rows that would need translating are skipped for that day rather than shipped with English in the Chinese README.

## Reproducing it

```bash
python3 scripts/lint.py                    # validate catalog.json against the schema
python3 scripts/check_links.py             # re-sweep every share, report drift, exit 1 if any died
python3 scripts/check_links.py --write     # also update link_status/checked and move dead rows out
python3 scripts/build_readme.py            # regenerate both READMEs from catalog.json
```

The social preview card is data-driven too. [`docs/social-card.html`](social-card.html) reads the same `catalog.json`, so the figures on it cannot drift from the catalog:

```bash
python3 -m http.server 8000                       # from the repo root
# open http://127.0.0.1:8000/docs/social-card.html at a 1280x640 viewport,
# screenshot it to docs/screenshots/social-card.png, then upload that at
# Settings -> General -> Social preview (GitHub exposes no API for this).
```

All three are dependency-free — plain `python3`, no `pip install`. `check_links.py` is read-only unless you pass `--write`.

## Known limits

- **Reachability is the only verified property.** No bot in this catalog has been imported and behaviour-tested by the maintainer. A green link does not mean a safe or working bot. See [vetting.md](vetting.md).
- **`official_summary` is truncated at the source.** x.ai cuts `og:description` at roughly 155 characters, sometimes mid-word. It is stored as received rather than silently repaired.
- **Chinese summaries are editorial, not literal.** They are written to be scannable in a list, so they compress rather than translate word for word.
- **Categories are one-per-bot.** Plenty of bots straddle two. The category chosen is the one describing the job the bot is _hired_ for, not every task it can do.
- **`first_seen` comes from upstream metadata** and reflects when a community catalog recorded the bot, not when its author first shared it.
