---
name: __PREFIX__-tickets
description: Split an approved plan into independently verifiable PR-sized tickets with dependency order. Use when one plan must ship as several PRs; a single-PR change keeps its plan's existing work units.
argument-hint: "[active change folder]"
---

Read `docs/standards/execution/stage-handoffs.md` for handoff ownership and host equivalents.
For one PR, retain the plan's work units and their proof instead of manufacturing tickets.

1. Resolve the argument or active task's approved `plan.md`; ask only when the task is ambiguous.
   Read its intent/spec and `docs/agents/issue-tracker.md`. Preserve the plan's outcome, criteria,
   constraints, actual approval and dependency order.
2. Read `.agents/skills/to-tickets/SKILL.md` by path as a vertical-slice reference. Choose
   independently verifiable outcomes and real blockers; shared dependencies must be ready
   before parallel work. Keep criterion/proof ownership visible in each ticket.
3. Append a `## 티켓` table to the same plan:
   `| [ ] | <제목> | <범위·기준·검증> | <blocked-by> |`. Titles describe the delivered end-to-end
   behavior in __HUMAN_DOC_LANG__. Publish nothing outside the repository.
4. Present the breakdown under the existing approval rules; reuse prior approval only when it
   covers these units. Commit the approved plan, identify unblocked units and continue through
   `__PREFIX__-implement` only when execution was requested. Pass the folder, selected unit,
   decisions, criteria, permitted files and proof context. A breakdown-only request ends here.

Tracker issues, labels and the reference's `.scratch/` files do not apply. An implementer ticks
a finished row with its code; missing verification keeps the corresponding criterion unverified.
