# Pre-implementation agreement and PR value review

Use this procedure when drafting spec/plan, starting implementation, changing accepted scope, or
preparing the PR. `artifact_chain.deliverables.required_when` in `.agents/harness.yaml` still
selects the required HTML files; keep the four perspectives and existing applicability conditions.
Small changes may skip intent, plan and inapplicable HTML; enabled runtime gates still require
a spec, exact scope, approval and verification. Agents cannot exempt themselves by calling work trivial.

## 1. Make the proposed outcome reviewable

During spec, draft the applicable files in `<change-folder>/deliverables/`. During plan, refine
the same drafts and complete the architecture view before asking for implementation approval.
Use the planned affected paths and user scenarios to determine applicability before a diff exists;
check the actual diff again at delivery. Drafts may be written before agreement; label them draft.

| File | Decision it supports before implementation | Evidence added after implementation |
|---|---|---|
| `설명서(eli7).html` | Why this matters, who benefits, what changes, unresolved decisions | Actual change, deviations, remaining value uncertainty |
| `mockup.html` | Proposed screens, states and interactions | Actual screenshots or observed behavior, separately labelled |
| `flow.html` | User steps, failure paths and recovery | Verified paths and known gaps |
| `architecture.html` | Planned boundaries, dependencies and affected contracts | Implemented boundaries and differences from the plan |

The explainer is the entrypoint, with relative links to the other required standalone HTML files.
Use a shared value/story identifier (for example V1/US1) across the views, spec and plan. Show only
what helps the decision. Reuse a view whose meaning is unchanged and label the unchanged scope.
Use inline styles/diagrams and embedded images; no external hosting or remote assets are needed.
A proposed mockup is not execution evidence. If the app cannot run, label actual verification as
unavailable and record the missing environment instead of implying that the mockup was tested.

## 2. Agree, then preserve the baseline

Present the applicable HTML drafts with the spec and plan. Ask about unresolved decisions;
existing explicit approval of the same presented revision remains valid. Approval of intent alone
is not approval of an unseen implementation draft. Product implementation starts after agreement.

For durable architecture, contract or harness decisions, read `docs/decisions/README.md`.
Put the proposed decision in spec/plan and include its future ADR path in scope; write the tracked
ADR after agreement. Reference an existing ADR when the decision is unchanged.

Create `scope.json` from the template: exact file paths and verification commands as argv arrays.
Use the `__PREFIX__-agreement` skill. Run `python3 scripts/agreement-gate.py prepare <change-id>
--revision 001`, then present the drafts, scope, checks and generated approval command. Claude uses
`/__PREFIX__-agreement approve <challenge>`; Codex uses `$__PREFIX__-agreement approve <challenge>`.
The user's exact command is handled by UserPromptSubmit. A Skill call or document saying
“approved” grants nothing. Existing approval of the same prepared revision is reused.

The hook checks the presented hashes, preserves `agreements/001/`, and records the grant in this
worktree's Git directory. Put `Agreement-Ref: agreements/001` in the plan before preparation and
in the PR afterward. Approved intent/spec/plan/scope stay frozen; record ticket/DoD results in
`progress.md`. Result HTML may evolve separately. For amendments, prepare the next revision to
revoke the old grant, edit the drafts, prepare again, and present the new challenge. A pending
draft may end a turn to await the user even with existing edits; implementation and commit stay
blocked. Prior revisions remain unchanged.

For a nontrivial change with no required HTML, preserve the approved plan/spec without HTML.
An implementation already in progress has no retroactive pre-implementation agreement: report
that gap, present the current state, and agree the remaining work explicitly.

## 3. Implement and verify the agreement

The implement adapter reads the referenced snapshot and implements only the approved file scope.
Use Write/Edit or Codex apply_patch for edits. For deletion/rename use the scoped helper commands
`python3 scripts/agreement-gate.py remove <path>` or `move <source> <target>`. Arbitrary mutation
shell commands and unsupported tools are refused. A simple `git switch -c feature/<name>` is
allowed after approval. Prepare isolated checkouts outside this flow; use one change per worktree.
Run `python3 scripts/agreement-gate.py verify` to execute the declared checks and record their
exit codes against current source hashes. Editing source invalidates that evidence. Run fresh
read-only code review and repair findings, then verify again if source changed. Code review assesses correctness against the
agreement. User value review remains a separate human decision.

After verification, update working `deliverables/` with actual behavior, evidence and deviations.
Keep the approved versions in `agreements/<revision>/deliverables/` unchanged. If actual changes
require a perspective not covered by the approved draft, return to agreement for the remaining
work; do not manufacture an earlier approval. A changed file alone does not prove a value claim.

## 4. Present the PR as a value review

Fill `_templates/pr.md`. Compare each agreed expectation with the observed result and its evidence
in `## 세 상자`. In `## 가치 확인`, record status and uncertainty for each material value claim:

- `확인됨`: the stated value has supporting observations; name the evidence and its limits.
- `부분 확인`: some agreed outcomes are observed, others remain unverified.
- `미검증`: implementation works, but the value needs usage/release observation.
- `미달`: observed results fall short of the agreed criterion; record the gap and next action.

A test showing a flow shrank from five steps to two proves that change; it does not prove reduced
abandonment. For unverified value, identify the metric/observation, agreed owner (or `담당 미정`)
and measurement timing/trigger. `미검증` can be an honest implementation handoff, unless the
agreed acceptance criteria require that measurement before completion. The agent never grants
the human's value approval or silently moves failed stories out of scope.

Keep the PR short: link the baseline and actual-result views, retain the existing three-row and
three-file limits, and use one nonempty evidence block. Attach both versions together with their
relative directory structure (a ZIP is suitable) so links work after extraction; attach the hash
manifest as well. This is still local-only history, not committed source. PR attachment and value
judgment are human checks. Delivery is local `pr.md` and the baseline/result directories; the developer
packages the attachment bundle and publishes the PR. Automated push, PR creation and worktree management are outside this adapter.

## Runtime boundary

Claude and Codex adapters wire UserPromptSubmit, PreToolUse and Stop. Stop and pre-commit locate
the active PR from state, even if never touched, and reject missing/stale verification, missing PR,
baseline corruption and scope drift. Pre-commit also rejects staging a different version from the
verified working copy. Stop does not revoke the approved scope: other hooks can still require
repairs. In-scope repairs need fresh verification; pause or a new prepared revision revokes
the current grant. User `pause` permits an incomplete
handoff; `resume` rechecks the baseline. Neither means completion or value approval.

These controls require trusted, enabled host hooks. They are workflow enforcement, not an OS
sandbox: same-user terminal access, disabling hooks, trusted verification scripts, and host tools
that bypass hooks are outside the boundary. Verification commands run with host privileges;
approve their actual content/dependencies, not just their names. A manual human-terminal approval
fallback exists for hosts without UserPromptSubmit and must be described as weaker provenance.
Do not claim that a matching approval command proves the human read or understood the HTML.
Native host behavior and trust settings require a deployment smoke test; payload tests alone do
not establish coverage for every host version. See the official host hook documentation.
