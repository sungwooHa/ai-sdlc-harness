# Stage handoffs

Read this contract when capturing intent, producing a spec/plan, or assigning implementation.
The stages preserve decisions through observable results. Use only the reasoning the task needs;
the repository's artifact, plan approval, branch, commit and review requirements still apply.

## Responsibilities and finish

| Stage | Owns | Handoff | Finish |
|---|---|---|---|
| Intent and grilling | Outcome, value, scope, constraints and material unresolved decisions | Decisions with their actual source, constraints, exclusions and blocking/deferred questions | Decisions needed for the next requested work are resolved or explicitly deferred |
| Specification | Observable behavior and external contracts | Acceptance criteria and applicable normal, boundary, interruption, finish and recovery cases; assumptions separated from decisions | Another worker can distinguish success from failure without recovering the entire conversation |
| Planning | Feasible implementation and proof in the current repository | Changed boundaries, dependency order, risks, owners/capabilities and criterion-level checks/environment | The approved work and its verification can actually be executed, with unavailable prerequisites explicit |
| Implementation | Working changes and evidence on the final candidate | Changes, criterion-level observed results, failures and unverified scope | The requested criteria pass at their required boundary; delivery records gaps without calling them complete |

The main agent owns continuity across handoffs. Reuse the active task's documents and decisions.
A missing intent file is an artifact gap, not evidence that the user needs another interview.
Synthesize required records from the authorized request and settled conversation; distinguish
confirmed decisions, new proposals and assumptions. Keep required artifacts even when their
reasoning was already completed in conversation. Record approval only when actually given.

## Questions and stage selection

Resolve repository facts, existing conventions, ordinary controls, internal file order and useful
test details yourself. Ask the human about unresolved changes to outcomes, policy, compatibility,
risk or authorization. Offer grilling when a focused interview would help; start it after the
user requests or accepts it. An ordinary necessary clarification does not require a full interview.
Reuse answered questions. When real alternatives exist, present a recommendation and alternatives;
do not manufacture options or ask the human to choose a slug or a test seam.

A clear bug uses the existing expected behavior plus the original repro as specification input.
A refactor uses the preserved contract and behavior baseline. Read
[task routes](task-routes.md) for their implementation and acceptance evidence. Avoid recreating
feature discovery for these tasks. A document-only, planning-only or review-only request finishes
with that result; continue to implementation only when it was also requested and approved.

## Preserve the contract

Keep a short correspondence in the existing artifacts: source decision -> acceptance criterion
-> planned proof -> actual result. Simple labels such as D1/A1 help when several items exist;
they are not a new schema or document requirement.

- The spec identifies the entry point, user-visible state/result and applicable stop/recovery
  paths. Include external API/data semantics where they define behavior. Put change-file lists,
  internal decomposition and command details in the plan. Resolve material contract decisions
  with their owner; choose ordinary implementation details locally.
- The plan maps every criterion to a change boundary and a meaningful test or observation.
  Establish useful baseline/repro evidence before edits and verify shared dependencies before
  parallel work. Name unavailable prerequisites rather than assuming a future verifier can fix them.
- For web work, prepare [browser acceptance](../qc/web-acceptance.md) in the plan: final build/URL,
  authorized account/data, intended backend/persistence boundary, browser-capable owner, failure
  injection/recovery and runtime cleanup. Static review, fixtures and physical-device input are
  separate coverage. Resolve available setup before delivery.
- Give implementers and reviewers the same decisions, criteria, permitted files and proof surface.
  Include the actual source/build identity; relevant edits invalidate earlier evidence. A reader
  who lacks the conversation must still receive its relevant constraints and actual approval scope.
- Inspect actual tool/delegate results and the resulting artifact. A failed start, denied action
  or missing result cannot establish an independent review or completed check. Preserve failures
  and distinguish executed behavior from a reported claim.

## Return to the cause

| Observed gap | Return to |
|---|---|
| Desired outcome/policy is materially undecided | Intent/grilling, with the focused decision and available evidence |
| Outcome is settled but behavior, state or acceptance is missing/contradictory | Specification |
| Behavior is defined but implementation dependencies or verification setup are infeasible | Planning |
| Contract and approach are sound but the product behaves incorrectly | Implementation, then the failed criterion and affected regressions |

Update the owning artifact and affected downstream work. Reuse unaffected decisions and evidence;
reopen approval only where a material change or the existing approval mechanism requires it.
Do not restart all stages for an ordinary implementation correction.

## Host capabilities

Stage responsibilities are shared across hosts; tool availability and enforcement are not.
Use a host's Skill tool when available, otherwise read the project adapter by path and follow it.
Use a supported question tool or ordinary conversation for human decisions. Use native
EnterPlanMode/ExitPlanMode when available; otherwise present the plan and wait for human approval
before implementation. Carry actual existing approval forward only within its scope.
These equivalents do not create Claude hook coverage on another host.

Use the host's supported subagent facility for implementation/review and accept its actual result.
If a required capability is unavailable, report that gap and continue independent authorized
preparation; do not simulate a subagent, approve a plan yourself, create trust/approval markers
or set a human-only approval variable. Keep browser execution with a browser-capable agent or
the main agent. A file/shell-only review can inspect evidence but cannot claim interaction.
