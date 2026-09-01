# Contributing

Thanks for helping keep this catalog accurate. There is exactly one file to edit: **`catalog.json`**. The READMEs are generated from it, so please do not edit them by hand — your changes would be overwritten on the next build.

## Adding a bot

1. Find the canonical share link. It must match `https://x.ai/bot/<id>` exactly. Links to a directory site, a tweet, or a redirector are not share links.
2. **Open it and check it loads.** If it does not return 200, it belongs in `retired.json`, not here.
3. Add one object to `entries` in `catalog.json`:

```json
{
  "slug": "inbox-zero",
  "name": "Inbox Zero",
  "author": {
    "name": "LD",
    "handle": "zapnocode",
    "url": "https://x.com/zapnocode"
  },
  "summary": "Archives the noise and drives Gmail to zero every weekday.",
  "summary_zh": "每个工作日把噪音归档，把 Gmail 压到零。",
  "official_summary": "Read straight from the share page's og:description.",
  "import": "https://x.ai/bot/h5i1TCuYEL2mVtMbQtW98",
  "bot_id": "h5i1TCuYEL2mVtMbQtW98",
  "category": "inbox-calendar",
  "tags": ["email", "gmail"],
  "origin": "https://x.com/zapnocode/status/2093...",
  "sources": [
    {
      "catalog": "your-handle/your-repo",
      "url": "https://github.com/your-handle/your-repo"
    }
  ],
  "checked": "2026-09-01",
  "link_status": 200,
  "license": "CC0-1.0"
}
```

4. Update `counts.live` and the relevant number in `counts.by_category`.
5. Run the checks:

```bash
python3 scripts/lint.py
python3 scripts/build_readme.py
```

6. Commit `catalog.json` **and** both regenerated READMEs.

## Field rules

`slug`, `name`, `summary`, `summary_zh`, `import`, `bot_id`, `category`, `sources` and `license` are required. The rest are optional but welcome. The authoritative definition is [`schema/entry.schema.json`](schema/entry.schema.json) — `scripts/lint.py` enforces it.

| Field              | Rule                                                                                                                                 |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------ |
| `name`             | The name on the **live share page** (`og:title`), not a community nickname.                                                          |
| `aka`              | Use this for the old name if the page has been renamed, so the row stays searchable.                                                 |
| `summary`          | One line, written for scanning. Aim for under 100 characters. Say what it _does_, not that it is "powerful" or "AI-powered".         |
| `summary_zh`       | A real Chinese one-liner, not machine translation. If you cannot write one, open an issue instead and someone will.                  |
| `official_summary` | Verbatim `og:description` from the share page. Do not tidy it up — it is stored as received.                                         |
| `category`         | Exactly one, from the eight in the schema. Pick the job the bot is _hired_ for, not everything it can do.                            |
| `tags`             | Up to 4, lowercase.                                                                                                                  |
| `sources`          | At least one. **Every row must be attributable.** If you found it yourself, name your own repo, blog, or the post you found it in.   |
| `origin`           | The post where the bot was first shared publicly, if you can find it.                                                                |
| `license`          | `CC-BY-4.0` if you inherited descriptive text from a CC BY 4.0 catalog (attribution then rides in `sources[]`), otherwise `CC0-1.0`. |

## Reporting a dead link

Run `python3 scripts/check_links.py` to confirm, then either open an issue or send a PR that moves the row from `catalog.json` to `retired.json` with its real `link_status`. Dead rows are kept rather than deleted so people can recognise a stale link elsewhere.

## What does not belong here

This catalog indexes **live `x.ai/bot` shares** and nothing else. Out of scope, with better homes listed in [docs/sources.md](docs/sources.md):

- Copy-paste prompt templates with no share link
- Skills, plugins, and MCP servers
- CLIs, bridges, and self-hosted alternatives
- Directory sites and other awesome-lists — link to them from `docs/sources.md` instead

## Removal requests

If you authored a listed bot and want the row changed or removed, [open an issue](https://github.com/kydlikebtc/awesome-grokbot/issues/new). No justification needed.

## Ground rules

Be accurate over enthusiastic. Do not add a bot you have not opened. Do not paste an API key into anything. Do not add your own bot with a summary that oversells it — a description that turns out to be wrong costs a reader more than a missing entry does.
