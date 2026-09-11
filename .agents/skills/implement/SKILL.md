---
name: implement
description: "Implement a piece of work based on a spec or set of tickets."
user-invocable: false
metadata:
  source: https://github.com/mattpocock/skills/tree/3cca18b368ae/skills/engineering/implement
  commit: 3cca18b368ae95cdbdebbff572ccafa662551015
  vendored_at: 2026-09-07
  update: python3 scripts/harness/vendor-skills.py --source mattpocock/skills
---

Implement the work described by the user in the spec or tickets.

Use /tdd where possible, at pre-agreed seams.

Run typechecking regularly, single test files regularly, and the full test suite once at the end.

Once done, use /code-review to review the work.

Commit your work to the current branch.
