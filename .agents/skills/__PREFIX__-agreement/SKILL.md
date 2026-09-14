---
name: __PREFIX__-agreement
description: Prepare and present a concrete pre-implementation agreement, its exact file scope and verification commands, then expose the host-owned approval control. Use after spec/plan drafts are ready, when scope changes, or when the user invokes agreement approve/pause/resume.
argument-hint: "approve <challenge> | pause | resume"
---

The agreement hook owns permission. Read `docs/standards/AGREEMENT_REVIEW.md` for the artifact
roles and host limits. A Skill invocation or an agent-written `approved` field never grants it.

## Prepare a decision

1. For a durable decision, use `__PREFIX__-adr` to draft its content in spec/plan and identify
   the tracked ADR paths; reuse existing records when unchanged. Finish the applicable HTML and spec/plan. Put exact repository-relative filenames and
   verification argv arrays in `<change-folder>/scope.json`, using `_templates/scope.json`.
   Include expected generated/tracked files. Commands run as trusted code on the host; choose
   the checks already used by the project, and show their purpose in the review.
2. Run `python3 scripts/agreement-gate.py prepare <change-id> --revision 001` (next revision
   when amending). The helper checks required views before any implementation, records hashes
   and prints the approval command. Changes to drafts afterward require preparing again.
3. If prepare's PreToolUse hook supplied ADR candidates, use `__PREFIX__-adr` to assess the
   actual decision and existing records. Briefly propose useful new decisions with the agreement;
   stay quiet for routine edits and do not turn the hint into an ADR requirement.
   Present the HTML entrypoint, expected result, scope and verification plan. Give the user the
   exact generated approval control (`/` on Claude, `$` on Codex). Ask only for the pending
   decision; do not request approval again once status shows this exact revision is approved.

## User control

On Claude and Codex, `UserPromptSubmit` handles the exact approval command before this skill runs and
preserves the baseline. Inspect `python3 scripts/agreement-gate.py status`, then continue the
approved implementation. Never run the manual `approve` CLI on the user's behalf, invent a
hook payload, or edit the state file. The runtime hook refuses those shell calls.

`pause` and `resume` are also user controls. A pause allows an honest incomplete report and
blocks implementation. Stop validates the handoff but keeps the exact approved scope available
for repairs required by other hooks; any code repair needs fresh verification. A new change or
changed scope needs a new prepared revision. On hosts without the user-submit adapter, show the manual approval
command for the human's own terminal and clearly identify the weaker runtime enforcement.

## Verification and handoff

Run `python3 scripts/agreement-gate.py verify` for the declared commands. Only that execution
records source-bound verification; typed success claims do not count. After any source edit,
rerun verification. Record progress in `progress.md`, leaving agreed planning inputs unchanged.
Prepare the active `pr.md` against the approved revision; Stop and pre-commit locate it from
state even if no PR file was previously touched. Human value judgment is separate from this gate.

Delivery here is local pr.md and baseline/result directories; the developer packages attachments and publishes the PR.
Use the scoped remove/move helpers for file deletion/rename. See the standard for supported tools.
