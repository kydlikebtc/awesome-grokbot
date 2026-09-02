# A Grok Bot routine that scouts for new shares

This catalog is maintained by two things that do not overlap.

|           | [`daily-update.yml`](../.github/workflows/daily-update.yml) | This routine                              |
| --------- | ----------------------------------------------------------- | ----------------------------------------- |
| Runs on   | GitHub Actions, 05:17 UTC                                   | A Grok Bot you own                        |
| Source    | Four **community catalogs**                                 | **X**, first-hand                         |
| Latency   | Whatever the upstreams' own lag is                          | Same day the author posts                 |
| Judgement | Rules only                                                  | A model reads the post and the share page |
| Writes    | Commits to `main`                                           | Opens an issue, nothing else              |

The workflow follows other people's catalogs. Those catalogs are themselves scraped from X, so following them means always arriving second. A Grok Bot has native X access, which is the one thing GitHub Actions cannot replicate — so this routine goes to the source.

If both are running, the routine finds a share on the day it is posted and the workflow would have picked it up whenever an upstream got around to it.

## Before you add it

**Connectors:** GitHub, with permission to open issues on `kydlikebtc/awesome-grokbot`. Nothing else. The routine never needs write access to code, and never needs to post anywhere.

**Reminder from [SECURITY.md](../SECURITY.md):** every bot on your account shares one computer. Give this one the narrowest connector set that lets it file an issue.

**Run it once by hand before scheduling it.** Ask the bot to do a single pass and show you the issue body _without filing it_. Check that the JSON parses and the categories look sane. Only then turn the schedule on.

## Routine configuration

| Field             | Value                                                                              |
| ----------------- | ---------------------------------------------------------------------------------- |
| Name              | `awesome-grokbot scout`                                                            |
| Schedule          | Daily, **09:00 your local time**                                                   |
| Owner             | A bot with the GitHub connector and nothing that sends                             |
| Output            | One GitHub issue, or nothing                                                       |
| Approval boundary | May open an issue. May not commit, push, comment on other repos, or post anywhere. |

Why 09:00 local: the workflow runs at 05:17 UTC, so by mid-morning the catalog on `main` already reflects whatever the upstreams had. The routine then only reports what they genuinely missed.

## The instruction

Paste this as the routine's instruction, verbatim.

````text
Every run, find Grok Bot shares posted on X in the last 24 hours that are not yet
in the awesome-grokbot catalog, and file one GitHub issue with them.

STEP 1 — Load what is already known.
Fetch https://raw.githubusercontent.com/kydlikebtc/awesome-grokbot/main/catalog.json
and https://raw.githubusercontent.com/kydlikebtc/awesome-grokbot/main/retired.json
Collect every "bot_id" from both files. That is the known set. Rows in
retired.json are known-dead: never propose them again.

STEP 2 — Search X for the last 24 hours.
Look for posts containing "x.ai/bot/" links. Try several phrasings, for example:
  x.ai/bot
  "Add to Grok Bot"
  grok bot share
Collect every distinct https://x.ai/bot/<id> URL you find, with the post URL and
the author's handle.

STEP 3 — Drop what is already known.
Discard any id in the known set from step 1. If nothing remains, stop and do not
file an issue. Say "no new shares today" in the run log and end. Do not file an
empty issue.

STEP 4 — Verify each remaining share.
Open its https://x.ai/bot/<id> page.
  - If it does not load, or shows a 404, discard it. Never propose a dead link.
  - If it loads, read the page title and description. The title is usually
    "<Bot name> by <Author>". Record the bot name and the description exactly as
    the page gives them — do not paraphrase these two.

STEP 5 — Write one row per surviving share.
  summary    One line of plain English, under 100 characters, saying what the bot
             DOES. No marketing words: not "powerful", not "AI-powered", not
             "seamlessly". Write it the way you would describe it to a colleague.
  summary_zh One line of natural Simplified Chinese saying the same thing. Write
             it as a Chinese developer would write it, not a literal translation
             of your English line. Keep product and brand names in English.
  category   Exactly one of these eight. Pick the job the bot is HIRED for, not
             everything it can do:
               coding-shipping     writing code, reviewing PRs, running coding
                                   agents, maintaining the machine
               inbox-calendar      email triage, drafting replies, calendar
               research-briefings  watching a topic, verifying claims, briefings
               customer-sales      prospecting, outbound, call support, accounts
               finance-ops         receipts, subscriptions, invoices, spend, admin
               content-publishing  writing, editing, design, video, publishing
               personal-admin      groceries, household, family, health, shopping
               teams-handoffs      bots that run or coordinate other bots
  tags       Up to 4 short lowercase tags.

STEP 6 — File ONE issue on kydlikebtc/awesome-grokbot.
Title:  scout: N new share(s) found on X
Body:   A short sentence saying where these came from and over what window, then
        a ```json fenced block containing an ARRAY of objects shaped exactly like
        this, and nothing else in the block:

[
  {
    "name": "Bot name exactly as the share page shows it",
    "summary": "One line of plain English under 100 characters",
    "summary_zh": "一句话中文说明",
    "import": "https://x.ai/bot/THE_ID",
    "bot_id": "THE_ID",
    "category": "coding-shipping",
    "tags": ["tag1", "tag2"],
    "author": { "name": "Display name from the page", "handle": "x_handle",
                "url": "https://x.com/x_handle" },
    "origin": "https://x.com/handle/status/POST_ID",
    "sources": [ { "catalog": "x.com (scouted by routine)",
                   "url": "https://x.com/handle/status/POST_ID" } ]
  }
]

After the block, list anything you discarded and why, one line each:
"discarded <id> — did not load" or "discarded <id> — already in catalog".

BOUNDARIES — these are absolute.
- Open an issue on kydlikebtc/awesome-grokbot. That is the only write you make.
- Never commit, push, open a pull request, or edit any file.
- Never post on X, reply to anyone, send a DM, or contact any person.
- Never add a share you could not load. An unverified link is worse than a
  missing one.
- Never invent a bot_id, an author, or a post URL. If you cannot find the origin
  post, leave "origin" out rather than guessing.
- If a step fails, say which step and stop. Do not file a partial issue and do
  not retry destructively.
- If you find more than 40 new shares in one run, something is wrong with the
  search. File the first 40 and say so in the issue.
````

## First safe task

Before switching the schedule on, run this once:

```text
Do one pass of your instruction, but do NOT file the issue. Show me the issue
body you would have filed, and tell me how many shares you found, how many you
discarded, and why.
```

Read what comes back. Things worth checking:

- Does the JSON block parse?
- Is every `bot_id` really the id from the URL?
- Are the categories the job the bot is hired for, or did it file everything under `personal-admin`?
- Is the Chinese natural, or is it a word-for-word rendering of the English?

If the categories or the Chinese are weak, tighten those steps in the instruction before scheduling it. A routine that files noisy issues every morning gets muted within a week.

## Merging what it finds

The issue body is already shaped like `catalog.json` rows. To merge:

1. Paste the objects into the `entries` array in [`catalog.json`](../catalog.json).
2. Add `"first_seen"`, `"checked"` (today), `"link_status": 200`, and `"license": "CC0-1.0"` to each — the routine deliberately does not invent these, since only a real sweep can confirm them.
3. Run `python3 scripts/lint.py`, then `python3 scripts/build_readme.py`.
4. Commit both READMEs with the catalog.

Or hand the issue to an agent with repo access and let it do steps 1–4.

`sources` records `x.com (scouted by routine)` rather than a community catalog, which is accurate: for these rows this repo _is_ the first catalog to list them. That is the whole point of running it.
