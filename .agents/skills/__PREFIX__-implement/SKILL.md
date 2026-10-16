---
name: __PREFIX__-implement
description: Implement an approved plan under docs/changes/<YYMMDD_NN>-<slug>/ by orchestrating implementer subagents per work unit, then review and write pr.md. Use right after the user approves a plan, or when the user says "구현해", "플랜대로 만들어", "이 티켓 해", "implement".
argument-hint: "[폴더명] [티켓 제목] — 예 260910_00-<slug>; 생략하면 방금 승인된 plan 의 폴더를 쓴다"
---

You are the orchestrator: you keep the conversation with the user, the decisions and the
acceptance of results; implementer subagents make the edits.

**Plan-first**: repo edits outside `docs/changes/` are refused until a plan is approved in this
session. The marker means "this session had a plan approved since it last entered plan mode" (an
`EnterPlanMode` call, or a prompt sent while in plan mode), not "this change's plan is approved",
and subagents share it. Edit files with Edit/Write, never
through Bash. With no approved plan yet, call `EnterPlanMode`.

## 1. Save the plan (first step after approval)

1. Resolve the change folder: `$0`, else the folder the approved plan names; ask when unclear.
   `$1` limits the work to that `## 티켓` row.
2. Save the approved plan — from the conversation, or the `ExitPlanMode` plan file under
   `~/.claude/plans/` — as `docs/changes/<YYMMDD_NN>-<slug>/plan.md` and commit it on
   `feature/<work-slug>` before any code edit.
3. Read `spec.md`, `plan.md` and each affected app's `AGENTS.md`.

## 2. Implement through subagents

- Unless the user turned it off, invoke `Skill(__PREFIX__-ponytail)` to look for a simpler design
  within the plan.
- Spawn one implementer subagent per plan work unit (or the `$1` ticket); run units in parallel
  only when their file lists are disjoint. Each prompt names the folder, the unit, its files and
  its Proof commands, and tells the subagent to:
  - read `.agents/skills/implement/SKILL.md` and `.agents/skills/tdd/SKILL.md` and follow them,
    test-first at the plan's seams, skipping their review and commit steps (you run those);
  - climb the test ladder: one test file → its directory → the whole suite once at the end;
  - leave the git index to you, and stop and report when blocked: subagents cannot ask the user.
- Agent calls run in the background: wait for each completion notification. Verify each output
  before accepting it — read the diff against the unit's files, re-run its tests — then stage that
  unit's paths and commit per `docs/standards/COMMIT_CONVENTION.md`.
- When reality departs from the plan, fix `plan.md` in the same commit as the code (and tick the
  finished `## 티켓` row there). Decisions the plan does not cover go to the user.
- Call `EnterPlanMode` only after every background implementer has finished: it clears the
  approval marker and blocks their edits.

## 3. Review

Run `/review-since <branch-base>` in a fresh subagent against `spec.md` and `plan.md`, with
`REVIEW.md` as the standards source. For UI changes also invoke `Skill(__PREFIX__-ui-review)`
unless `plan.md` says `시각 변경 없음`. Fix blockers and majors as `REVIEW.md` defines them through
implementer subagents, then re-verify.

## 4. pr.md

Write `docs/changes/<YYMMDD_NN>-<slug>/pr.md` from `docs/changes/_templates/pr.md`: compare the
plan's `## Value` with observed results, paste the commands you ran and their output, and keep
unverified value explicit with its next observation, owner (`담당 미정` if none) and timing. The
human judges the value. Put a durable rule learned here in the relevant `AGENTS.md`, or state
`지식 승격 없음`. Commit `pr.md`, show it in full, and report status, deviations and test results;
pushing and opening the PR are the developer's.
