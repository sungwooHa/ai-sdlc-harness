---
name: __PREFIX__-tickets
description: Split one docs/changes/<YYMMDD_NN>-<slug>/plan.md into several PR-sized tickets with blocking order, appended to plan.md. Use ONLY when a single plan must be delivered as more than one PR — otherwise the plan's "변경 파일과 순서" table is already the breakdown. Triggers: "티켓 나눠", "서브태스크 만들어", "작업 분해", "to-tickets". Wraps the vendored to-tickets skill with this repo's paths and language.
disable-model-invocation: true
argument-hint: "[폴더명] — 예 260910_00-<slug>; 생략하면 docs/changes/ 의 최근 plan.md 를 쓴다"
---

Project adapter around the vendored `to-tickets` skill. Use it only when one plan must be split
into several PRs; for a single-PR change the plan's "변경 파일과 순서" table is enough — say so and
stop.

Before calling it:

1. Resolve the change folder (`$0` = the folder name `<YYMMDD_NN>-<slug>`, else the most recent
   `docs/changes/<YYMMDD_NN>-<slug>/` with a `plan.md`, else `spec.md`; confirm with the user). The
   folders are local and uncommitted, so most recent = the newest file mtime (`ls -t`); the folder
   id sorts chronologically, so break a tie with the larger id; if candidates are still ambiguous,
   ask the user. Read that document — it is the source of the breakdown, not the conversation alone.
2. Read `docs/agents/issue-tracker.md`. There is no external tracker and no `ready-for-agent`
   label — skip those steps if the vendored skill asks.

Then call the Skill tool with `to-tickets` and apply these overrides:

- Do not publish anything outside the repo and do not write local `.scratch/` files. If the
  vendored skill wants to create tracker issues, skip that step.
- Ticket bodies in __HUMAN_DOC_LANG__; titles in the form `<동사구> — <끝에서 끝까지 동작>`.
- Do not produce the vendored template's tracker fields: no `**Status:** ready-for-agent` line and
  no `## Parent` section (they name a tracker parent issue; there is no tracker here).
- The only output is a `## 티켓` section appended to the end of
  `docs/changes/<YYMMDD_NN>-<slug>/plan.md`: one row per ticket, blockers first, each row starting
  with a checkbox column — `| [ ] | <제목> | <한 줄 범위> | <blocked-by> |`.
  `/__PREFIX__-implement` records completion in `progress.md`, preserving approved plan bytes. No commit: `plan.md` is
  local-only; the ticket scope reaches the PR value comparison. If a preserved agreement exists,
  first prepare a new revision with `__PREFIX__-agreement` to revoke the grant before editing
  the plan; prepare again and obtain approval of the changed draft before implementation.

Finish by naming the frontier — the tickets with no open blockers — so the user can start
`/__PREFIX__-implement` on one of them.
