<!-- Thanks for contributing. catalog.json is the only file to edit by hand. -->

## What this changes

<!-- One line. "Adds 3 bots to finance-ops", "Moves 2 dead links to retired.json". -->

## Checklist

- [ ] I opened every share link I added, and it returned 200
- [ ] Each new row has `sources[]` filled in — every row must be attributable
- [ ] `name` is the name on the **live share page**, not a community nickname
- [ ] I updated `counts.live` and `counts.by_category`
- [ ] `python3 scripts/lint.py` passes with 0 errors
- [ ] `python3 scripts/build_readme.py` was run and both READMEs are committed
- [ ] I did not hand-edit `README.md` or `README.zh-CN.md`

## Scope

- [ ] Only live `https://x.ai/bot/<id>` shares — no prompt templates, skills, plugins, CLIs or directory sites

<!--
Adding your own bot? That is welcome. Please write the summary the way you would
want to read it as a stranger: what it does, plainly. A description that turns
out to be wrong costs a reader more than a missing entry does.
-->
