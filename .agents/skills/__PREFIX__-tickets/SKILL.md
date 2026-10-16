---
name: __PREFIX__-tickets
description: Split one approved docs/changes/<YYMMDD_NN>-<slug>/plan.md into PR-sized tickets with blocking order, appended to plan.md. Use only when one plan must ship as more than one PR — "티켓 나눠", "작업 분해", "split into tickets", "to-tickets".
argument-hint: "[폴더명] — 예 260910_00-<slug>; 생략하면 docs/changes/ 의 최근 plan.md 를 쓴다"
---

Use this only when one plan must ship as several PRs; for a single-PR change the plan's
`## Files that change` / `## Order of work` already is the breakdown — say so and stop.

1. Resolve the change folder: `$0` when given, otherwise the folder with the largest
   `<YYMMDD_NN>` id that has `plan.md`; confirm it with the user. Read that `plan.md`: it is the
   source of the breakdown, not the conversation alone.
2. Read `docs/agents/issue-tracker.md`.
3. Read `.agents/skills/to-tickets/SKILL.md` and follow it, with these overrides:
   - Publish nothing outside the repo and write no `.scratch/` files; skip tracker issues and
     labels.
   - Ticket bodies in __HUMAN_DOC_LANG__; titles in the form `<동사구> — <끝에서 끝까지 동작>`.
   - No `**Status:** ready-for-agent` line and no `## Parent` section.
   - The only output is a `## 티켓` section appended to that `plan.md`: one row per ticket,
     blockers first — `| [ ] | <제목> | <한 줄 범위> | <blocked-by> |`. The implementer ticks a
     row in the same commit that lands the ticket.
4. Once the user approves the breakdown, commit `plan.md`, name the frontier (tickets with no open
   blockers), and invoke `Skill(__PREFIX__-implement)` with args `<YYMMDD_NN>-<slug> <ticket title>`
   for the frontier ticket the user picks.
