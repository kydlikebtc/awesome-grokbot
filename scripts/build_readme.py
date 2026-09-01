#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render README.md (English) and README.zh-CN.md (Chinese) from catalog.json.

The READMEs are generated, never hand-edited: catalog.json is the single source
of truth, so a PR that adds a bot only touches one file and the counts, tables
and category sections stay consistent.

    python3 scripts/build_readme.py
"""

import json
import os
import re
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_SLUG = "kydlikebtc/awesome-grokbot"
REPO_URL = f"https://github.com/{REPO_SLUG}"

# emoji, English label, Chinese label, English blurb, Chinese blurb
CATEGORIES = [
    (
        "coding-shipping",
        "🛠️",
        "Coding & shipping",
        "编码与交付",
        "Write code, review PRs, babysit coding agents, keep the box healthy.",
        "写代码、审 PR、盯着编码代理干活、把机器照顾好。",
    ),
    (
        "inbox-calendar",
        "📥",
        "Inbox & calendar",
        "收件箱与日历",
        "Triage mail, draft replies, defend the calendar, run the weekday rhythm.",
        "分拣邮件、起草回复、守住日历、把工作日节奏跑起来。",
    ),
    (
        "research-briefings",
        "🔍",
        "Research & briefings",
        "研究与简报",
        "Watch a beat, verify claims, and hand back one short brief.",
        "盯住一个领域、核查说法，最后只给你一份短简报。",
    ),
    (
        "customer-sales",
        "🤝",
        "Customer & sales",
        "客户与销售",
        "Prospecting, outbound drafts, call support, and account follow-through.",
        "找客户、起草外呼、通话后援、客户跟进到底。",
    ),
    (
        "finance-ops",
        "💰",
        "Finance & ops",
        "财务与运营",
        "Receipts, subscriptions, invoices, spend audits, and back-office chores.",
        "票据、订阅、发票、花费审计，以及各种后台杂务。",
    ),
    (
        "content-publishing",
        "✍️",
        "Content & publishing",
        "内容与发布",
        "Drafting, editing, design, video, and the queue that ships it.",
        "起草、编辑、设计、视频，以及把它们发出去的队列。",
    ),
    (
        "personal-admin",
        "🏠",
        "Personal admin",
        "个人事务",
        "Groceries, household logistics, family schedules, health, and shopping.",
        "买菜、家务后勤、家庭日程、健康和购物。",
    ),
    (
        "teams-handoffs",
        "🧭",
        "Teams & handoffs",
        "团队与交接",
        "Bots that run other bots: rosters, delegation, budgets, and handoffs.",
        "管别的 Bot 的 Bot：花名册、委派、预算和交接。",
    ),
]

SOURCE_REPOS = [
    (
        "majiayu000/awesome-grok-bot",
        "https://github.com/majiayu000/awesome-grok-bot",
        "Live-share catalog with a maintained 8-way taxonomy and Chinese summaries.",
        "维护了 8 类分类法和中文摘要的活分享目录。",
    ),
    (
        "ZeroPointRepo/GrokBotDev",
        "https://github.com/ZeroPointRepo/GrokBotDev",
        "Agent-run directory with the richest per-bot metadata (sharer, origin post, tags).",
        "代理维护的目录，单条元数据最全（分享者、原帖、标签）。",
    ),
    (
        "cs68614-hash/awesome-grokbot-templates",
        "https://github.com/cs68614-hash/awesome-grokbot-templates",
        "Community-scraped share IDs, several of which appear nowhere else.",
        "社区抓取的分享 ID，其中有几条别处找不到。",
    ),
    (
        "elie222/botdirectory.ai",
        "https://github.com/elie222/botdirectory.ai",
        "Open directory of agent-bot prompts; contributor and origin-post attribution.",
        "开源的代理 Bot 提示词目录，带贡献者和原帖出处。",
    ),
]


def load():
    return json.load(open(os.path.join(ROOT, "catalog.json"), encoding="utf-8"))


def load_retired():
    return json.load(open(os.path.join(ROOT, "retired.json"), encoding="utf-8"))


def anchor(key):
    """Stable explicit anchor id.

    GitHub's auto-generated anchors for emoji headings are unreliable — a heading
    like "## 🛠️ Coding & shipping" produces an id containing an invisible U+FE0F
    variation selector. So every jump target in these READMEs is an explicit
    <a name="..."> emitted next to the heading, keyed off the category slug.
    """
    return f"cat-{key}"


def esc(s):
    """Escape bare ampersands so the raw-HTML category table stays valid."""
    return s.replace("&", "&amp;")


def shield(text):
    """shields.io treats '-' as a field separator; '--' renders a literal dash."""
    return text.replace("-", "--").replace(" ", "%20")


def author_md(e):
    a = e.get("author") or {}
    name = a.get("name") or ""
    url = a.get("url")
    handle = a.get("handle")
    if url and name:
        who = f"[{name}]({url})"
    elif name:
        who = name
    else:
        return ""
    if handle and handle.lower() != name.lower():
        who += f" (@{handle})"
    return who


def row(e, zh=False):
    """One catalog line: name -> share link, one-line summary, author, origin."""
    summary = e.get("summary_zh") if zh else e["summary"]
    summary = (summary or e["summary"]).rstrip(".。") + ("。" if zh else ".")
    line = f"- [{e['name']}]({e['import']}) — {summary}"
    bits = []
    who = author_md(e)
    if who:
        bits.append(f"by {who}" if not zh else f"作者 {who}")
    if e.get("aka"):
        bits.append(f"aka *{e['aka']}*" if not zh else f"社区旧称 *{e['aka']}*")
    if e.get("origin"):
        bits.append(f"[origin]({e['origin']})" if not zh else f"[出处]({e['origin']})")
    if bits:
        line += f" <sub>{' · '.join(bits)}</sub>"
    return line


def category_table(entries, zh=False):
    counts = Counter(e["category"] for e in entries)
    out = ["<table>"]
    cells = []
    for key, emo, en, cn, blurb_en, blurb_cn in CATEGORIES:
        label = esc(f"{emo} {cn if zh else en}")
        blurb = esc(blurb_cn if zh else blurb_en)
        unit = "个" if zh else "bots"
        cells.append(
            f'    <td width="25%" valign="top">'
            f'<p><strong><a href="#{anchor(key)}">{label}</a></strong><br>'
            f"<sub>{counts[key]} {unit}</sub></p>"
            f"<sub>{blurb}</sub></td>"
        )
    for i in range(0, len(cells), 4):
        out.append("  <tr>")
        out.extend(cells[i : i + 4])
        out.append("  </tr>")
    out.append("</table>")
    return "\n".join(out)


# ------------------------------------------------------------------ English


def build_en(cat, retired):
    e = cat["entries"]
    counts = Counter(x["category"] for x in e)
    n = len(e)
    checked = cat["checked"]
    L = []
    A = L.append

    A(f'<h1 align="center">awesome-grokbot</h1>')
    A("")
    A(
        f'<h3 align="center">{n} live <code>x.ai/bot</code> shares for Grok Bot.<br>'
        "Every link status-checked. Every row attributed to where it came from.</h3>"
    )
    A("")
    A('<p align="center">')
    A(
        '  <a href="https://awesome.re"><img src="https://awesome.re/badge-flat2.svg" alt="Awesome"></a>'
    )
    A(
        f'  <a href="{REPO_URL}"><img src="https://img.shields.io/github/stars/{REPO_SLUG}?style=flat-square&color=rgb(25%2C%20121%2C%20255)" alt="Stars"></a>'
    )
    A(
        f'  <a href="{REPO_URL}/fork"><img src="https://img.shields.io/github/forks/{REPO_SLUG}?style=flat-square&color=green" alt="Forks"></a>'
    )
    A(
        f'  <a href="catalog.json"><img src="https://img.shields.io/badge/live%20shares-{n}-blueviolet?style=flat-square" alt="Live shares"></a>'
    )
    A(
        f'  <a href="#section-method"><img src="https://img.shields.io/badge/links%20checked-{shield(checked)}-success?style=flat-square" alt="Links checked"></a>'
    )
    A(
        f'  <a href="CONTRIBUTING.md"><img src="https://img.shields.io/badge/PRs-welcome-brightgreen?style=flat-square" alt="PRs welcome"></a>'
    )
    A(
        '  <a href="LICENSE-CC0"><img src="https://img.shields.io/badge/catalog-CC0--1.0-lightgrey?style=flat-square" alt="CC0"></a>'
    )
    A("</p>")
    A("")
    A('<p align="center">')
    A('  <strong>English</strong> | <a href="./README.zh-CN.md">简体中文</a>')
    A("</p>")
    A("")
    A(
        "> [Grok Bot](https://docs.x.ai/grok-bot/overview) gives named AI teammates their own always-on cloud "
        "computer. This repo is not Grok Bot, not an installer, and not source code — it is the index of public "
        "bot configurations you can preview on `x.ai` and add to your own account in one click."
    )
    A("")

    # ---- why
    A("## ⚡️ Why this list")
    A("")
    A(
        f"There are already several Grok Bot lists. They disagree with each other, and most of them never "
        f"re-check the links they publish. This one is built differently:"
    )
    A("")
    A(
        f"- **Every share was fetched, not assumed.** All {n} entries answered under HTTP 400 on {checked}. "
        f"{len(retired['entries'])} shares that returned 404 across two sweeps are quarantined in "
        "[`retired.json`](retired.json) instead of being quietly left in the list."
    )
    A(
        "- **A status code is not a verdict.** The checker sorts results into `alive` / `gone` / `blocked` / "
        "`flaky`, and only `gone` (404/410) counts as a dead bot — a bot wall or a 5xx says something about the "
        "network or the host, not about the bot. This is not theoretical: one share answered 500 mid-sweep, was "
        "retired by the old `status != 200` rule, and answered 200 the next time it was asked. A circuit breaker "
        "aborts the run if more than 25% comes back blocked or flaky, so a challenge page in front of CI can "
        f"never be filed as {n} dead bots. See [docs/method.md](docs/method.md#why-a-status-code-is-not-a-verdict)."
    )
    A(
        "- **Names and blurbs come from the live page.** Each row carries `official_summary`, read straight from "
        "the share page's `og:description`. Where the live name differs from what the community catalogs recorded, "
        "theirs is kept as `aka` so the row stays searchable. 32 rows differ; 27 are qualifier-only "
        "(`Cursor Agent (Local)` vs `Cursor Agent`) and 5 are substantive — one share now points at an entirely "
        "different bot than every community catalog still claims."
    )
    A(
        f"- **Every row says where it came from.** `sources[]` names the community catalog(s) the entry was "
        f"merged from, and `origin` links the post that first shared it ({sum(1 for x in e if x.get('origin'))} of {n} rows)."
    )
    A(
        f"- **Bilingual by default.** All {n} rows carry a hand-checked Chinese one-liner, not machine output."
    )
    A(
        "- **Data first, prose second.** [`catalog.json`](catalog.json) is the source of truth; both READMEs are "
        "generated from it by [`scripts/build_readme.py`](scripts/build_readme.py)."
    )
    A("")

    # ---- quick links
    A("## 📖 Quick links")
    A("")
    A("| | |")
    A("| --- | --- |")
    A(f"| 📦 [`catalog.json`](catalog.json) | All {n} live entries, schema-validated |")
    A(
        f"| 🪦 [`retired.json`](retired.json) | {len(retired['entries'])} shares that stopped resolving |"
    )
    A(
        "| 🔐 [Before you import](docs/vetting.md) | Safety checklist. Read this before adding anything |"
    )
    A(
        "| 🧪 [Data & method](docs/method.md) | How the catalog was built and how to reproduce it |"
    )
    A(
        "| 🙏 [Sources & credits](docs/sources.md) | Upstream catalogs this merges, with licences |"
    )
    A("| 🤝 [Contributing](CONTRIBUTING.md) | Add a bot in one JSON object |")
    A("")

    # ---- how to use
    A("## 🚀 How to use")
    A("")
    A(
        "1. [Install Grok Bot](https://docs.x.ai/grok-bot/get-started) on Mac, Windows or iPhone. "
        "There is no official Linux desktop build — the bot's own computer is already Linux, in the cloud."
    )
    A("2. Open any share link below and read the public preview **before** you add it.")
    A(
        "3. Press **Add to Grok Bot**. That copies the name, instructions, skills, routines and first-party plugin ids."
    )
    A(
        "4. It does **not** copy the author's computer, files, logins or API keys. Reconnect connectors yourself, "
        "one at a time."
    )
    A(
        "5. Run one read-only task first. Only then enable routines or anything that writes."
    )
    A("")
    A(
        "> [!WARNING]\n"
        "> A community share is untrusted third-party software. All bots on one account **share a single "
        "computer** — a second bot is not a security boundary. Full checklist: [docs/vetting.md](docs/vetting.md)."
    )
    A("")

    # ---- categories
    A('<a name="section-categories"></a>')
    A("")
    A("## 🗂️ Categories")
    A("")
    A(category_table(e, zh=False))
    A("")
    A("| Category | Bots |")
    A("| --- | ---: |")
    for key, emo, en, cn, _, _ in CATEGORIES:
        A(f"| [{emo} {en}](#{anchor(key)}) | {counts[key]} |")
    A(f"| **Total** | **{n}** |")
    A("")

    # ---- entries
    for key, emo, en, cn, blurb_en, _ in CATEGORIES:
        rows = [x for x in e if x["category"] == key]
        A(f'<a name="{anchor(key)}"></a>')
        A("")
        A(f"## {emo} {en}")
        A("")
        A(f"*{blurb_en}* — {len(rows)} bots")
        A("")
        for r in sorted(rows, key=lambda x: x["name"].lower()):
            A(row(r, zh=False))
        A("")
        A('<sub><a href="#section-categories">↑ back to categories</a></sub>')
        A("")

    # ---- retired
    A("## 🪦 Retired shares")
    A("")
    A(
        f"These {len(retired['entries'])} shares appear in upstream catalogs but no longer resolve as of {checked}. "
        "They are listed so you can recognise a stale link elsewhere, not so you can import them."
    )
    A("")
    A("| Bot | Status | Last seen in |")
    A("| --- | :---: | --- |")
    for r in retired["entries"]:
        srcs = ", ".join(s["catalog"].split("/")[0] for s in r.get("sources", []))
        A(f"| `{r['name']}` | `HTTP {r['link_status']}` | {srcs} |")
    A("")

    # ---- method
    A('<a name="section-method"></a>')
    A("")
    A("## 📊 Data & method")
    A("")
    A(
        f"The catalog is a merge of four community sources plus a first-party verification pass. "
        f"Merge key is the id inside `https://x.ai/bot/<id>`, so duplicate rows across catalogs collapse into one."
    )
    A("")
    A("| Step | Result |")
    A("| --- | --- |")
    A("| Unique share ids found across 4 catalogs | 365 |")
    A(f"| Answered under 400 on {checked} | **{n}** |")
    A(f"| Answered 404 across two sweeps → `retired.json` | {len(retired['entries'])} |")
    A(
        f"| Rows enriched with first-party `og:` metadata | {sum(1 for x in e if x.get('official_summary'))} |"
    )
    A(
        f"| Rows whose live name differs from the community catalogs | {sum(1 for x in e if x.get('aka'))} (5 substantive, 27 qualifier-only) |"
    )
    A(
        f"| Rows attributed to 2+ upstream catalogs | {sum(1 for x in e if len(x.get('sources', [])) > 1)} |"
    )
    A(
        f"| Rows with a Chinese summary | {sum(1 for x in e if x.get('summary_zh'))} / {n} |"
    )
    A("")
    A(
        "Reproduce it yourself with [`scripts/check_links.py`](scripts/check_links.py) (re-sweeps every share) and "
        "[`scripts/lint.py`](scripts/lint.py) (validates against [`schema/entry.schema.json`](schema/entry.schema.json)). "
        "Method notes: [docs/method.md](docs/method.md)."
    )
    A("")

    # ---- credits
    A("## 🙏 Sources & credits")
    A("")
    A(
        "This list stands on work other people did first. Each catalog row names its upstream in `sources[]`; "
        "the four merged catalogs are:"
    )
    A("")
    A("| Upstream catalog | What it contributed |")
    A("| --- | --- |")
    for name, url, blurb, _ in SOURCE_REPOS:
        A(f"| [{name}]({url}) | {blurb} |")
    A("")
    A("Full attribution and licence notes: [docs/sources.md](docs/sources.md).")
    A("")

    # ---- disclaimer
    A("## 📄 Disclaimer")
    A("")
    A(
        "- This repo indexes **publicly shared** Grok Bot configurations. It claims no ownership over any bot, "
        "prompt or profile listed here."
    )
    A(
        "- Bot names and blurbs are the authors' own, read from the public share page. Chinese summaries are this "
        "repo's editorial translations."
    )
    A(
        "- A reachable share page proves the page loads. It does **not** prove the bot is safe, maintained, or does "
        "what its description claims. Vet before you import."
    )
    A(
        "- Adding a community share accepts Grok Bot's third-party bot terms. Some listed bots touch money, "
        "trading, or outbound messaging — read the profile before connecting anything."
    )
    A(
        "- If you authored a bot listed here and want the row changed or removed, "
        f"[open an issue]({REPO_URL}/issues/new) and it will be handled promptly."
    )
    A("")
    A("**If this saved you time, a ⭐ helps other people find it.**")
    A("")

    A("## 📈 Star history")
    A("")
    A(
        f"[![Star History Chart](https://api.star-history.com/svg?repos={REPO_SLUG}&type=Date)]"
        f"(https://star-history.com/#{REPO_SLUG}&Date)"
    )
    A("")

    A("## 📜 Licence")
    A("")
    A(
        "The catalog data (`catalog.json`, `retired.json`) is released under "
        "[CC0-1.0](LICENSE-CC0) — take it, fork it, build on it. The scripts are "
        "[MIT](LICENSE-MIT). Linked bots and their profiles belong to their authors."
    )
    A("")
    return "\n".join(L) + "\n"


# ------------------------------------------------------------------- Chinese


def build_zh(cat, retired):
    e = cat["entries"]
    counts = Counter(x["category"] for x in e)
    n = len(e)
    checked = cat["checked"]
    L = []
    A = L.append

    A(f'<h1 align="center">awesome-grokbot</h1>')
    A("")
    A(
        f'<h3 align="center">{n} 条可一键添加的 Grok Bot 活分享（<code>x.ai/bot</code>）。<br>'
        "每条链接都实测过，每条记录都标注了出处。</h3>"
    )
    A("")
    A('<p align="center">')
    A(
        '  <a href="https://awesome.re"><img src="https://awesome.re/badge-flat2.svg" alt="Awesome"></a>'
    )
    A(
        f'  <a href="{REPO_URL}"><img src="https://img.shields.io/github/stars/{REPO_SLUG}?style=flat-square&color=rgb(25%2C%20121%2C%20255)" alt="Stars"></a>'
    )
    A(
        f'  <a href="{REPO_URL}/fork"><img src="https://img.shields.io/github/forks/{REPO_SLUG}?style=flat-square&color=green" alt="Forks"></a>'
    )
    A(
        f'  <a href="catalog.json"><img src="https://img.shields.io/badge/%E6%B4%BB%E5%88%86%E4%BA%AB-{n}-blueviolet?style=flat-square" alt="活分享"></a>'
    )
    A(
        f'  <a href="#section-method"><img src="https://img.shields.io/badge/%E9%93%BE%E6%8E%A5%E5%AE%9E%E6%B5%8B-{shield(checked)}-success?style=flat-square" alt="链接实测"></a>'
    )
    A(
        f'  <a href="CONTRIBUTING.md"><img src="https://img.shields.io/badge/PRs-welcome-brightgreen?style=flat-square" alt="PRs welcome"></a>'
    )
    A(
        '  <a href="LICENSE-CC0"><img src="https://img.shields.io/badge/catalog-CC0--1.0-lightgrey?style=flat-square" alt="CC0"></a>'
    )
    A("</p>")
    A("")
    A('<p align="center">')
    A('  <a href="./README.md">English</a> | <strong>简体中文</strong>')
    A("</p>")
    A("")
    A(
        "> [Grok Bot](https://docs.x.ai/grok-bot/overview) 让具名的 AI 队友拥有一台常开的云电脑。"
        "这个仓库不是 Grok Bot 本体，不是安装器，也不是源码——它是**公开 Bot 配置的索引**："
        "你可以先在 `x.ai` 上预览，再一键添加到自己的账号。"
    )
    A("")

    A("## ⚡️ 为什么还要再做一个")
    A("")
    A(
        "Grok Bot 的列表已经有好几个了。它们互相对不上，而且大多数发布之后就再也没复查过链接。这一份的做法不一样："
    )
    A("")
    A(
        f"- **每条分享都真的去抓了，不是假设它还活着。**全部 {n} 条在 {checked} 实测返回 HTTP 400 以下。"
        f"另有 {len(retired['entries'])} 条连续两轮都返回 404 的，单独隔离进 [`retired.json`](retired.json)，"
        "而不是继续留在列表里装作没事。"
    )
    A(
        "- **状态码不等于判决。**检查器把结果分成 `alive` / `gone` / `blocked` / `flaky` 四桶，"
        "只有 `gone`（404/410）才算 Bot 真的没了——反爬墙或 5xx 说的是网络和宿主的事，不是 Bot 的事。"
        "这不是假想：有一条分享在扫描途中返回 500，被旧的「非 200 即死」规则判死，再问一次它返回 200。"
        "另有熔断保护：一轮里超过 25% 落进 blocked 或 flaky 就中止，"
        f"这样 CI 前面挡一个验证页，永远不会被记成 {n} 个 Bot 全死。"
        "详见 [docs/method.md](docs/method.md#why-a-status-code-is-not-a-verdict)。"
    )
    A(
        "- **名字和描述取自分享页本身。**每条都带 `official_summary`，直接读自分享页的 `og:description`。"
        "官方页的名字和社区目录记录不一致时，社区名保留在 `aka` 字段里，旧名字依然搜得到。"
        "32 条存在差异：27 条只是限定词不同（`Cursor Agent (Local)` 对 `Cursor Agent`），"
        "5 条是实质性的——其中一条分享现在指向的，已经是和所有社区目录所写完全不同的另一个 Bot。"
    )
    A(
        f"- **每条都说清楚来自哪。**`sources[]` 标明这条是从哪个（些）社区目录合并来的，"
        f"`origin` 指向最早分享它的那条帖子（{n} 条里有 {sum(1 for x in e if x.get('origin'))} 条）。"
    )
    A(f"- **默认双语。**{n} 条全部配有人工核过的中文一句话说明，不是机翻。")
    A(
        "- **先有数据，才有文档。**[`catalog.json`](catalog.json) 是唯一事实来源，"
        "两份 README 都由 [`scripts/build_readme.py`](scripts/build_readme.py) 生成。"
    )
    A("")

    A("## 📖 快速入口")
    A("")
    A("| | |")
    A("| --- | --- |")
    A(f"| 📦 [`catalog.json`](catalog.json) | 全部 {n} 条活条目，通过 schema 校验 |")
    A(
        f"| 🪦 [`retired.json`](retired.json) | {len(retired['entries'])} 条已经打不开的分享 |"
    )
    A("| 🔐 [导入之前先读](docs/vetting.md) | 安全检查清单。添加任何 Bot 之前请先看 |")
    A("| 🧪 [数据与方法](docs/method.md) | 目录怎么建的，以及如何自己复现 |")
    A("| 🙏 [来源与致谢](docs/sources.md) | 合并了哪些上游目录，各自许可 |")
    A("| 🤝 [参与贡献](CONTRIBUTING.md) | 加一个 Bot 只需要写一个 JSON 对象 |")
    A("")

    A("## 🚀 怎么用")
    A("")
    A(
        "1. 先在 Mac、Windows 或 iPhone 上 [安装 Grok Bot](https://docs.x.ai/grok-bot/get-started)。"
        "官方没有 Linux 桌面版——Bot 自己那台电脑本来就是云上的 Linux。"
    )
    A("2. 打开下面任意一条分享链接，**先读公开预览**，再决定要不要加。")
    A("3. 点 **Add to Grok Bot**。这会复制名字、指令、技能、例行任务和官方插件 id。")
    A(
        "4. 它**不会**复制作者的电脑、文件、登录态或 API key。连接器要你自己重新接，一次只接一个。"
    )
    A("5. 先跑一个只读任务。确认没问题，再开例行任务或任何会写入的操作。")
    A("")
    A(
        "> [!WARNING]\n"
        "> 社区分享属于不可信的第三方软件。同一个账号下的所有 Bot **共用一台电脑**——"
        "多开一个 Bot 并不构成安全边界。完整清单见 [docs/vetting.md](docs/vetting.md)。"
    )
    A("")

    A('<a name="section-categories"></a>')
    A("")
    A("## 🗂️ 分类总览")
    A("")
    A(category_table(e, zh=True))
    A("")
    A("| 分类 | 收录 |")
    A("| --- | ---: |")
    for key, emo, en, cn, _, _ in CATEGORIES:
        A(f"| [{emo} {cn}](#{anchor(key)}) | {counts[key]} |")
    A(f"| **合计** | **{n}** |")
    A("")

    for key, emo, en, cn, _, blurb_cn in CATEGORIES:
        rows = [x for x in e if x["category"] == key]
        A(f'<a name="{anchor(key)}"></a>')
        A("")
        A(f"## {emo} {cn}")
        A("")
        A(f"*{blurb_cn}* —— {len(rows)} 个")
        A("")
        for r in sorted(rows, key=lambda x: x["name"].lower()):
            A(row(r, zh=True))
        A("")
        A('<sub><a href="#section-categories">↑ 回到分类总览</a></sub>')
        A("")

    A("## 🪦 已失效的分享")
    A("")
    A(
        f"这 {len(retired['entries'])} 条在上游目录里还挂着，但截至 {checked} 已经打不开了。"
        "列在这里是为了让你在别处遇到时能认出它是死链，不是让你去导入。"
    )
    A("")
    A("| Bot | 状态 | 最后出现在 |")
    A("| --- | :---: | --- |")
    for r in retired["entries"]:
        srcs = "、".join(s["catalog"].split("/")[0] for s in r.get("sources", []))
        A(f"| `{r['name']}` | `HTTP {r['link_status']}` | {srcs} |")
    A("")

    A('<a name="section-method"></a>')
    A("")
    A("## 📊 数据与方法")
    A("")
    A(
        "目录 = 四个社区来源的合并 + 一次第一手核验。合并键是 `https://x.ai/bot/<id>` 里的 id，"
        "所以跨目录的重复条目会自动收敛成一条。"
    )
    A("")
    A("| 步骤 | 结果 |")
    A("| --- | --- |")
    A("| 四个目录里找到的唯一分享 id | 365 |")
    A(f"| {checked} 实测返回 HTTP 400 以下 | **{n}** |")
    A(f"| 连续两轮返回 404 → 进 `retired.json` | {len(retired['entries'])} |")
    A(
        f"| 补齐第一手 `og:` 元数据的条目 | {sum(1 for x in e if x.get('official_summary'))} |"
    )
    A(
        f"| 官方页名称与社区目录不一致的条目 | {sum(1 for x in e if x.get('aka'))}（5 条实质性，27 条仅限定词差异）|"
    )
    A(
        f"| 能追溯到 2 个以上上游目录的条目 | {sum(1 for x in e if len(x.get('sources', [])) > 1)} |"
    )
    A(f"| 带中文摘要的条目 | {sum(1 for x in e if x.get('summary_zh'))} / {n} |")
    A("")
    A(
        "你可以自己复现：[`scripts/check_links.py`](scripts/check_links.py) 重新扫一遍所有分享，"
        "[`scripts/lint.py`](scripts/lint.py) 按 [`schema/entry.schema.json`](schema/entry.schema.json) 校验。"
        "方法说明见 [docs/method.md](docs/method.md)。"
    )
    A("")

    A("## 🙏 来源与致谢")
    A("")
    A(
        "这份列表建立在别人先做的工作之上。每条记录都在 `sources[]` 里写明了上游；合并的四个目录是："
    )
    A("")
    A("| 上游目录 | 贡献了什么 |")
    A("| --- | --- |")
    for name, url, _, blurb_cn in SOURCE_REPOS:
        A(f"| [{name}]({url}) | {blurb_cn} |")
    A("")
    A("完整署名与许可说明见 [docs/sources.md](docs/sources.md)。")
    A("")

    A("## 📄 声明")
    A("")
    A(
        "- 本仓库收录的是**公开分享**的 Grok Bot 配置，不对其中任何 Bot、提示词或档案主张所有权。"
    )
    A("- Bot 名称与描述来自作者本人（读自公开分享页）。中文摘要是本仓库的编辑性翻译。")
    A(
        "- 分享页能打开，只能证明**页面能打开**。它不能证明这个 Bot 安全、仍在维护，或者真的能做到它描述的事。导入前请自行核验。"
    )
    A(
        "- 添加社区分享即接受 Grok Bot 的第三方 Bot 条款。列表里有些 Bot 涉及资金、交易或对外发消息，接任何连接器之前请先读它的档案。"
    )
    A(
        f"- 如果你是列表中某个 Bot 的作者，希望修改或下架该条目，请 [提一个 issue]({REPO_URL}/issues/new)，会尽快处理。"
    )
    A("")
    A("**如果这份列表帮你省了时间，点个 ⭐ 能让更多人找到它。**")
    A("")

    A("## 📈 Star 趋势")
    A("")
    A(
        f"[![Star History Chart](https://api.star-history.com/svg?repos={REPO_SLUG}&type=Date)]"
        f"(https://star-history.com/#{REPO_SLUG}&Date)"
    )
    A("")

    A("## 📜 开源协议")
    A("")
    A(
        "目录数据（`catalog.json`、`retired.json`）以 [CC0-1.0](LICENSE-CC0) 释出——随便拿、随便 fork、随便二次开发。"
        "脚本采用 [MIT](LICENSE-MIT)。被链接的 Bot 及其档案版权归各自作者。"
    )
    A("")
    return "\n".join(L) + "\n"


def main():
    cat = load()
    retired = load_retired()
    en = build_en(cat, retired)
    zh = build_zh(cat, retired)
    open(os.path.join(ROOT, "README.md"), "w", encoding="utf-8").write(en)
    open(os.path.join(ROOT, "README.zh-CN.md"), "w", encoding="utf-8").write(zh)
    print(f"README.md       {len(en):>7,} bytes")
    print(f"README.zh-CN.md {len(zh):>7,} bytes")
    print(f"entries rendered: {len(cat['entries'])}")


if __name__ == "__main__":
    main()
