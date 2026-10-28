---
name: __PREFIX__-implement
description: Implement user-requested repository changes through the approved-plan workflow, using implementer subagents, review and the required delivery artifacts. Use for implementation, fix or refactoring requests, or executing an approved plan. Exclude explanation, design-comparison and review-only requests.
argument-hint: "[active change folder and optional ticket]"
---

The main agent owns the user conversation, decisions and acceptance; implementer subagents make
the edits. Read `docs/standards/execution/stage-handoffs.md` for shared responsibilities, handoffs,
failure returns and host capabilities.

**Plan-first:** use native EnterPlanMode/ExitPlanMode when available; otherwise present the plan
and await human approval before implementation. Existing approval may be reused only within its
actual scope. Claude's hook and marker semantics live in `docs/standards/AGENT_HARNESS.md`;
other hosts do not acquire that hook. Never manufacture approval/trust markers or set a
human-only approval variable. Edit through the host's file-edit tools, not shell writes.

## 0. Select the execution route

Read `docs/standards/execution/task-routes.md` and select Bug fix, Feature or Refactoring from
the requested result. Establish its repro/cause, acceptance criteria or preserved-behavior
baseline before implementation. Read-only preparation can inform the approved plan without
granting write approval. Reuse the settled intent/spec instead of repeating discovery.

Apply the risk/artifact policy in `docs/changes/README.md`, including the high-risk definition
in `AGENTS.md`. A typo-sized routine change uses its approved conversation/native plan without
a change folder, intent/spec, committed plan or pr.md. Their absence does not start an interview
or artifact-creation chain. Standard and high-risk changes retain their committed plan/pr.md;
high-risk work also commits intent/spec before code edits as `AGENTS.md` requires.

## 1. Save the approved plan

1. Read the approved plan and affected app instructions. For standard/high-risk work, resolve
   the folder and optional ticket from the argument or active task and read the required
   intent/spec. Synthesize only a required missing record from the actual decisions; unresolved
   material outcomes return to the owning stage. A routine task keeps its approved plan in
   conversation or the host's native plan record.
2. Work on `feature/<work-slug>` for every class of change. For standard/high-risk work, save
   the approved plan from conversation or the host's approved plan file as
   `docs/changes/<YYMMDD_NN>-<slug>/plan.md` and commit it on `feature/<work-slug>` before code
   edits. Preserve the plan's criterion-to-proof mapping and actual approval source.
3. For visible behavior, apply `__PREFIX__-ui-review` before editing to scope the journey and
   agreed design reference. Prepare `docs/standards/qc/web-acceptance.md` for web work.
   Internal-only changes retain their ordinary verification.

## 2. Implement through subagents

- Unless the user turned it off, apply the `__PREFIX__-ponytail` adapter within the approved
  outcomes. Use the host's Skill tool or read the adapter by path.
- Spawn one implementer per plan work unit using the host's supported subagent facility.
  Parallelize only independent files/state after shared dependencies are ready. For a feature,
  verify the first vertical slice before dependent fan-out.
- Give each implementer the folder/unit or approved routine plan, source decisions and constraints,
  selected task route, criteria or repro/baseline, owned files, proof commands/surface and
  authorized environment.
  Tell it to read `.agents/skills/implement/SKILL.md` and `.agents/skills/tdd/SKILL.md` by path
  and apply these project overrides: test-first at useful approved seams; choose routine test
  details locally; skip their commit/review steps; leave the index to the main agent; report a
  blocked material decision rather than asking the user. Preserve all requested criteria.
- Wait for actual completion, inspect each result and diff, then execute its repro, criteria
  or equivalence checks against the resulting files before accepting it. An unsuccessful
  startup or missing result is a failed attempt, not completed independent work. Report missing
  required capabilities rather than simulating a delegate.
- Run checks narrow -> wide and the whole suite once at the end. Stage only accepted unit paths
  and commit per `docs/standards/COMMIT_CONVENTION.md`.
- When reality departs from a committed plan, update it in the same commit as the code; keep a
  routine task's conversation/native plan current without creating a change document. Return material
  outcome/contract gaps to intent/spec; infeasible dependencies/proof to planning; ordinary
  implementation failures to the unit. Reuse unaffected decisions. Tick finished ticket rows.
- Enter plan mode only after all background implementers finish; it clears Claude's approval.

## 3. Review

Run `review-since` through a fresh supported subagent with the base, source decisions,
available spec and approved plan, selected route, original repro/criteria/baseline and `REVIEW.md`.
Provide the actual final source/build identity and proof context. Inspect its real result before
acceptance; failed or absent review remains explicit.

For visible effects, including helper/API/validation changes, apply `__PREFIX__-ui-review` for
code/design scope. Return blockers and majors to their owning stage/unit, fix through
implementers and rerun affected checks. A green build does not close an unmet criterion.

## 4. Browser acceptance for web outcomes

Execute `docs/standards/qc/web-acceptance.md` after code checks/review. Assign its criteria,
final build/URL and authorized backend/account/data/failure context to a browser-capable
verifier; the main agent executes it when delegation lacks browser capability. Reuse evidence
only for the required journeys on this final candidate. A file/shell review cannot establish
browser interaction. Native-only changes use the project device/emulator procedure.

Return browser failures to the responsible stage/unit and rerun affected journeys/environments
after repair. Required unavailable checks stay unverified with their blocker; resolve available
setup and continue independent work. Keep static, browser, backend and input-device coverage
distinct. Internal-only changes skip this branch.

## 5. pr.md and delivery

For a routine task, complete the applicable verification/review and code commit, then give a
brief report of the change, actual checks and remaining gaps; no change folder or pr.md is
required. Standard/high-risk work follows the artifact delivery below.

Write `docs/changes/<YYMMDD_NN>-<slug>/pr.md` from its template. Map every acceptance criterion
to observed final-candidate evidence, failure or unverified scope. Compare the plan's Value to
actual results; keep unverified value with its next observation, owner (`담당 미정` if needed)
and timing. Record commands actually run and results. The human judges value.

Promote a durable rule to its owning standard/AGENTS.md or state `지식 승격 없음`. Commit
`pr.md`, show it in full, and report status, deviations and evidence gaps.

For every task, clean up task-owned runtimes under the project's lifecycle policy. Pushing,
opening a PR, merging and deployment retain their existing authorization rules.
