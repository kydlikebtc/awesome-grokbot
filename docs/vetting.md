# Before you import

A community share is **untrusted third-party software**. The share page is public, and adding one accepts Grok Bot's third-party bot terms. This page is the checklist to run before and after you press **Add to Grok Bot**.

## The one thing most people get wrong

**Every bot on your account shares one computer.** Files, browser sessions and logins on that cloud machine are visible to all of them. Spinning up a second bot is _not_ a security boundary — if you would not let bot A read something, do not let bot B put it on the shared disk.

## Checklist

1. **Read the public preview first.** Full standing instructions are usually visible on the share page without importing anything. If the description is vague about what it writes to, that is the answer.
2. **Add only from a canonical `https://x.ai/bot/…` link.** Every row in this catalog uses one. A link that goes anywhere else is not an official share.
3. **Compare the imported profile against what the page said.** If they disagree, trust the imported bot and [open an issue](https://github.com/kydlikebtc/awesome-grokbot/issues/new) so the catalog row gets fixed.
4. **Connect exactly one connector.** A share copies first-party plugin _ids_, never credentials — you reconnect everything yourself. Do that one at a time so you can see what each one unlocks.
5. **Inspect the skills it arrived with.** The preview can list skills while the export ships an empty `skills: []`. Check what is actually there rather than what was advertised.
6. **Run one read-only task.** Ask it to summarise, list, or report — nothing that sends, pays, posts, or deletes.
7. **Only then enable routines or writes.** A routine you forgot about is the most common way people burn their allowance.
8. **Never paste an API key into a profile or setup note.** If a bot's instructions ask you to, that is a red flag worth reporting.

## Bots that deserve extra care

Some rows in this catalog touch things that are hard to undo. Read the profile twice before connecting anything for bots that:

- **move money or trade** — anything in [Finance & ops](../README.md#cat-finance-ops) that mentions a brokerage, wallet, or live account. At least one listed bot trades a real book.
- **send on your behalf** — outbound sales, DM automation, and social posting bots in [Customer & sales](../README.md#cat-customer-sales) and [Content & publishing](../README.md#cat-content-publishing).
- **drive a browser while logged in** — anything that reuses your sessions can act as you on any site you are signed into.
- **run other bots** — [Teams & handoffs](../README.md#cat-teams-handoffs) bots create, edit, or delete other bots. Give them the narrowest approval boundary you can live with.

A good default instruction to add to any imported bot: _"Draft and research only. Do not send, post, pay, delete, or change production until I say yes in chat."_

## Account limits worth knowing

- 50 bots plus group chats per account.
- 50 routines per bot.
- One share installs **one** bot. Multi-bot "team" setups are recipes you assemble yourself, not a single import.
- All bots share one computer (see above).

## What a green link in this catalog does and does not prove

| Claim                                                     | True?                           |
| --------------------------------------------------------- | ------------------------------- |
| The share page returned HTTP 200 on the date in the badge | ✅ Yes, measured                |
| The name and description match what the author published  | ✅ Yes, read from the live page |
| The bot is safe                                           | ❌ Not tested                   |
| The bot still works as described                          | ❌ Not tested                   |
| The bot is actively maintained                            | ❌ Not tested                   |

Reachability is the only property this catalog verifies. Everything else is on you before you connect a single thing.

## Reporting a problem

If a listed bot behaves differently from its description, has gone dead, or should not be listed at all, [open an issue](https://github.com/kydlikebtc/awesome-grokbot/issues/new). Security concerns: see [SECURITY.md](../SECURITY.md).
