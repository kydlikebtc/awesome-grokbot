# Sources & credits

This catalog is a merge, not an original discovery effort. Other people found these bots first. This page names them, records what each contributed, and states the licence their work carries.

Per-row attribution lives in the catalog itself: every entry in [`catalog.json`](../catalog.json) has a `sources[]` array naming the upstream catalog(s) it came from, and — for 347 of 360 rows — an `origin` link to the post where the bot was first shared publicly.

## Upstream catalogs

| Catalog                                                                                             | Licence                                  | Contributed                                                                                         |
| --------------------------------------------------------------------------------------------------- | ---------------------------------------- | --------------------------------------------------------------------------------------------------- |
| [majiayu000/awesome-grok-bot](https://github.com/majiayu000/awesome-grok-bot)                       | Catalog data: **CC0-1.0** · scripts: MIT | 268 rows. The eight-way category taxonomy used here, and 267 of the Chinese summaries.              |
| [ZeroPointRepo/GrokBotDev](https://github.com/ZeroPointRepo/GrokBotDev)                             | Code: MIT · `content/`: **CC BY 4.0**    | 331 rows, with the richest per-bot metadata: sharer handle, origin post, posted-at timestamp, tags. |
| [cs68614-hash/awesome-grokbot-templates](https://github.com/cs68614-hash/awesome-grokbot-templates) | **CC0-1.0**                              | 205 rows, including several share ids that appear in no other catalog.                              |
| [elie222/botdirectory.ai](https://github.com/elie222/botdirectory.ai)                               | **MIT**                                  | 194 rows with contributor and origin-post attribution.                                              |

334 of the 360 live rows appear in two or more of these catalogs. Where they disagreed, the live share page broke the tie — see [method.md](method.md#field-precedence).

## Licence of this catalog

The catalog is not uniformly licensed, because its inputs are not. Each row declares its own `license`:

| Row licence | Rows | Meaning                                                                                                                                                                                                                     |
| ----------- | ---: | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `CC-BY-4.0` |  329 | Inherited descriptive text from GrokBotDev's `content/`, which is CC BY 4.0. Attribution is required, and is satisfied by the `sources[]` array on the row itself. If you reuse these rows, carry that attribution forward. |
| `CC0-1.0`   |   31 | Derived only from CC0 / MIT sources. No conditions.                                                                                                                                                                         |

Two things are worth separating here. **Facts are not copyrightable** — a bot's name, its share URL, who shared it, and whether the link resolves are facts, and this repo asserts no rights over them. What can be copyrighted is _descriptive prose_, and where a row's one-line summary was inherited from a CC BY 4.0 catalog, the row is marked accordingly.

Contributions original to this repo — the Chinese summaries, the hand-corrected categories, the link-status measurements, the schema and the scripts — are dedicated to the public domain under [CC0-1.0](../LICENSE-CC0) (data) and [MIT](../LICENSE-MIT) (code).

## The bots themselves

Every bot listed here belongs to its author. This repo links to their public share pages and paraphrases what those pages say. It does not host, copy, or redistribute any bot profile, prompt, or configuration.

If you authored a listed bot and want the row corrected or removed, [open an issue](https://github.com/kydlikebtc/awesome-grokbot/issues/new) — no justification needed, it will be handled promptly.

## Other Grok Bot resources worth knowing

Not merged into this catalog, because they are a different shape — but genuinely useful, and the people behind them deserve the traffic:

| Project                                                                                       | What it is                                                                                           |
| --------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| [RongleCat/awesome-grok-bot](https://github.com/RongleCat/awesome-grok-bot)                   | The largest general Grok Bot resource list. Bilingual, broader scope than share links.               |
| [mergisi/awesome-grokbot](https://github.com/mergisi/awesome-grokbot)                         | Copy-paste `PROFILE.md` / `SETUP.md` bot templates organised by function.                            |
| [cobusgreyling/grok-bot-templates](https://github.com/cobusgreyling/grok-bot-templates)       | An engineering kit: template spec, a "Bot Ready" score, teams, skills, and routines.                 |
| [jaskirat1616/grok-skills](https://github.com/jaskirat1616/grok-skills)                       | 195 `SKILL.md` playbooks, browsable at [grokbotskills.vercel.app](https://grokbotskills.vercel.app). |
| [ZeroPointRepo/awesome-grok-bot](https://github.com/ZeroPointRepo/awesome-grok-bot)           | Skills, plugins and MCP servers, plus self-hosted alternatives.                                      |
| [0xNyk/awesome-grok-bot](https://github.com/0xNyk/awesome-grok-bot)                           | Independent directory of skills, plugins, MCP and setup guides, with maturity labels.                |
| [rdmgator12/awesome-grok-bot-plugins](https://github.com/rdmgator12/awesome-grok-bot-plugins) | A snapshot of the in-app plugin marketplace listings.                                                |
| [Anil-matcha/awesome-grok-bot](https://github.com/Anil-matcha/awesome-grok-bot)               | Ready-to-use bot prompts across productivity, sales, marketing and ops.                              |

Official documentation: [docs.x.ai/grok-bot](https://docs.x.ai/grok-bot/overview).
