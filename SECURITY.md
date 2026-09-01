# Security

## What this repository is

A list of links. It contains no executable bot code, ships no installer, and never asks for a credential. The security surface that matters is not this repo — it is what happens after you click one of these links and add someone else's bot to your account.

## The threat model you should actually hold

A community share is untrusted third-party software written by a stranger. When you add one:

- **All bots on your account share one computer.** Files, browser sessions and logins on that cloud machine are reachable by every bot you run. A second bot is not a sandbox.
- **A share carries standing instructions.** It arrives with a profile telling it what to do, which you should read before it starts doing it.
- **A share does not carry credentials.** It copies first-party plugin _ids_; you reconnect every connector yourself. Anything asking you to paste an API key into a profile or setup note is a red flag — report it.
- **Routines run without you.** A routine you enabled and forgot is the most common way people burn their allowance or let a bot act unsupervised.

Full pre-import checklist: [docs/vetting.md](docs/vetting.md).

## Reporting a problem with a listed bot

If a bot in this catalog behaves maliciously, exfiltrates data, or does something materially different from its published description:

1. [Open an issue](https://github.com/kydlikebtc/awesome-grokbot/issues/new) with the row's `slug` and what you observed. Public reporting is fine and preferred — other readers benefit from the warning.
2. The row will be removed or flagged promptly, ahead of any other queued work.
3. Report the bot to xAI as well. This catalog can delist a row; it cannot take a bot down.

Please do **not** include credentials, tokens, or personal data in the report.

## Reporting a problem with this repository

For issues in the scripts or workflows — a supply-chain concern, a workflow with excessive permissions, a script doing something unexpected — open an issue, or use GitHub's [private vulnerability reporting](https://github.com/kydlikebtc/awesome-grokbot/security/advisories/new) if you would rather not disclose publicly first.

The scripts here are dependency-free by design: `lint.py`, `check_links.py` and `build_readme.py` use only the Python standard library, so there is no third-party package tree to audit. `check_links.py` makes outbound GET requests to `x.ai` share pages and writes nothing unless you pass `--write`.

## What this catalog verifies, and what it does not

| Property                                                 | Verified              |
| -------------------------------------------------------- | --------------------- |
| The share URL returned HTTP 200 on the date in the badge | ✅ Measured           |
| The name and description match the live share page       | ✅ Read from the page |
| The bot is safe                                          | ❌ Never tested       |
| The bot does what it claims                              | ❌ Never tested       |
| The bot is maintained                                    | ❌ Never tested       |

No bot in this catalog has been imported and behaviour-tested. Reachability is the only claim made. Treat every row as a lead to investigate, not a recommendation.
