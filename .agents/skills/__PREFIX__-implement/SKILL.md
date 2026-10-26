---
name: __PREFIX__-implement
description: Implement user-requested repository changes through the approved-plan workflow, using implementer subagents, review and pr.md. Use for implementation, fix or refactoring requests, or executing an approved plan. Exclude explanation, design-comparison and review-only requests.
argument-hint: "[폴더명] [티켓 제목] — 예 260910_00-<slug>; 생략하면 방금 승인된 plan 의 폴더를 쓴다"
---

You are the orchestrator: you keep the conversation with the user, the decisions and the
acceptance of results; implementer subagents make the edits.

**Plan-first**: repo edits outside `docs/changes/` are refused until a plan is approved in this
session. The marker means "this session had a plan approved since it last entered plan mode" (an
`EnterPlanMode` call, or a prompt sent while in plan mode), not "this change's plan is approved",
and subagents share it. Edit files with Edit/Write, never
through Bash. With no approved plan yet, call `EnterPlanMode`.

## 0. Select the execution route

Read `docs/standards/execution/task-routes.md` and select Bug fix, Feature or Refactoring from
the requested result. Establish its repro/cause, acceptance criteria or preserved-behavior
baseline before implementation. Read-only preparation can inform the approved plan; it does
not grant write approval. Keep this route and its evidence in subsequent handoffs. This selects
work inside the existing approval workflow, without creating an additional skill/artifact chain.

## 1. Save the plan (first step after approval)

1. Resolve the change folder: `$0`, else the folder the approved plan names; ask when unclear.
   `$1` limits the work to that `## 티켓` row.
2. Save the approved plan — from the conversation, or the `ExitPlanMode` plan file under
   `~/.claude/plans/` — as `docs/changes/<YYMMDD_NN>-<slug>/plan.md` and commit it on
   `feature/<work-slug>` before any code edit.
3. Read `spec.md`, `plan.md` and each affected app's `AGENTS.md`.
   For user-visible changes, read `__PREFIX__-ui-review` section 1 before editing to scope the
   journey and rendered reference; web work also prepares `docs/standards/qc/web-acceptance.md`.

## 2. Implement through subagents

- Unless the user turned it off, invoke `Skill(__PREFIX__-ponytail)` to look for a simpler design
  within the plan.
- Spawn one implementer subagent per plan work unit (or the `$1` ticket); run units in parallel
  only when their files/state are independent and shared dependencies are ready. For a feature,
  verify the first vertical slice before dependent fan-out. Each prompt names the folder, unit,
  files, selected task route, repro/criteria/baseline and Proof commands/surface, and tells it to:
  - read `.agents/skills/implement/SKILL.md` and `.agents/skills/tdd/SKILL.md` and follow them,
    test-first at the plan's seams, skipping their review and commit steps (you run those);
  - apply the selected task route over upstream workflow preferences. Reuse the approved plan's
    boundaries; choose ordinary test details locally rather than requiring a new user confirmation
    for each seam. Stop for a material missing decision or scope change, not a routine test choice;
  - climb the test ladder: one test file → its directory → the whole suite once at the end;
  - leave the git index to you, and stop and report when blocked: subagents cannot ask the user.
- Agent calls run in the background: wait for each completion notification. Verify each output
  before accepting it — read the diff, execute its route's repro/criteria/equivalence evidence and
  appropriate checks against the unit's files — then stage that
  unit's paths and commit per `docs/standards/COMMIT_CONVENTION.md`.
- When reality departs from the plan, fix `plan.md` in the same commit as the code (and tick the
  finished `## 티켓` row there). Decisions the plan does not cover go to the user.
- Call `EnterPlanMode` only after every background implementer has finished: it clears the
  approval marker and blocks their edits.

## 3. Review

Run `/review-since <branch-base>` in a fresh subagent against `spec.md` and `plan.md`, with
`REVIEW.md` as the standards source. For user-visible effects, including helper/API/validation
changes, invoke `Skill(__PREFIX__-ui-review)` for its scope and code/design passes. A declaration
of no visual change does not exclude changed behavior. Fix blockers and majors as `REVIEW.md`
defines them through implementer subagents, then re-verify.
Give the reviewer the selected route and its original repro, feature criteria or preserved baseline.
Return failed evidence to its owning route before proceeding; a green build alone does not close it.

## 4. Browser acceptance for web outcomes

Execute `docs/standards/qc/web-acceptance.md` as a distinct step after code checks/review. Assign
the outcome, acceptance criteria, final build/URL and authorized test context to a browser-capable
verifier. If it cannot operate the browser, you perform the browser step; a file/shell-only code
reviewer cannot replace it. Reuse UI-review evidence only when it executed the required paths on
this final candidate. Native-only work uses the project's device/emulator procedure; internal-only
changes skip this branch.

Return browser failures to implementer subagents, then rerun affected journeys/environments.
Required checks that cannot run stay unverified. Proceed to the report with their exact scope
and blocker, without calling the web outcome complete; resolving available setup remains yours.

## 5. pr.md

Write `docs/changes/<YYMMDD_NN>-<slug>/pr.md` from `docs/changes/_templates/pr.md`: compare the
plan's `## Value` with observed results, paste the commands you ran and their output, and keep
unverified value explicit with its next observation, owner (`담당 미정` if none) and timing. The
human judges the value. Put a durable rule learned here in the relevant `AGENTS.md`, or state
`지식 승격 없음`. Commit `pr.md`, show it in full, and report status, deviations and test results;
pushing and opening the PR are the developer's.
