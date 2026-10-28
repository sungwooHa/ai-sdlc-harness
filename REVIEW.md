# Pull request review policy

Applies to human reviewers, the `verifier` subagent, `/review-since <base>` (standards + spec),
`/__PREFIX__-ui-review`, and the AI review workflow once activated (`docs/examples/claude-review.yml`;
blocker and major = Important, minor = Nit). Code review checks the diff against the change
folder's spec.md and plan.md; the PR value review of `pr.md` is a separate, later human step.

## Passes, in order

| Pass | Question | Source of truth |
|---|---|---|
| Plan adherence | Does the diff do what spec.md and plan.md say, and change nothing outside plan.md `Files that change`? | `docs/changes/<YYMMDD_NN>-<slug>/` (spec.md, plan.md); for a routine change, the approved plan-mode plan |
| Decision continuity | Are settled decisions preserved as observable criteria, executable proof and final evidence, with assumptions and unresolved decisions distinguished? | `docs/standards/execution/stage-handoffs.md`; actual handoffs and results |
| Correctness | Bugs, unhandled states, race conditions, missing tests for stated edge cases | code + tests |
| Contracts | Shared contracts (`packages/*`, API, schema) changed on both sides with compatibility notes? | the contract's owner docs |
| Security & data | Secrets, auth boundaries, real personal data in code, fixtures or tests | `AGENTS.md` Guide; `.agents/harness.json` `secrets` |
| Compliance | The guide rules below, which no hook enforces | this file |
| Design system *(conditional)* | Only once the project records a design system: hardcoded tokens, bypassed inventory, exemptions without a reason | that decision |
| UI quality *(conditional)* | User-visible effects, including behavior in helpers/API/state outside `__UI_SOURCE_GLOB__` | `/__PREFIX__-ui-review` |
| Web acceptance *(conditional)* | Were affected journeys executed through completion, fresh read and recovery on the final candidate, with required viewports/input paths? | `docs/standards/qc/web-acceptance.md`; actual browser evidence |

**Compliance pass.** Check each item; the PR is the only place it is checked.

- A high-risk change (definition: `AGENTS.md`) has intent.md, spec.md and plan.md committed in its
  change folder and a second approver.
- The diff matches plan.md `Files that change`, or the commit that departs from the plan also
  updates plan.md.
- No user-specific absolute paths (`/Users/<name>/...`, `/home/<name>/...`) in docs, skills or config.
- No `Co-Authored-By` or other attribution trailers; first lines follow
  `docs/standards/COMMIT_CONVENTION.md`.
- A nontrivial change has `pr.md` with expected vs actual vs evidence and unverified value explicit.
- A fix does not pass by weakening a test (deleted assertion, loosened expectation, added skip).

## Severity

- **blocker**: wrong behaviour, contract break, security or data issue, scope or plan violated
  silently, a weakened test, a high-risk change without a committed plan.md. Cannot merge.
- **major**: missing test for a stated edge case, undocumented contract change, any other
  compliance miss. Fix before merge unless the author records why not.
- **minor**: clarity, naming, small duplication. Optional.

Each finding names file:line, the defect in one sentence, and a concrete failure scenario. A
finding without a failure scenario is a question: list it after the findings. Style preferences
are not findings.

## Do not report

- Generated files and lockfiles (`protected_paths`), except that they were hand-edited.
- What a hook or `check:harness` already blocks; report only a way around it.
- Issues that exist before the diff, unless the diff makes them worse.

## Repeat findings

On the second confirmed occurrence of the same agent mistake, trace the shared cause and update
the owning instruction or skill; use a hook only if it meets the binary criterion in
`docs/standards/AGENT_HARNESS.md`. Count distinct occurrences, not duplicate review comments.
Keep the original failure and expected outcome with the change's evidence. A product defect gets
a focused product regression; a missed or conflicting instruction also gets a realistic harness
evaluation when it can distinguish the failure. Verify the affected outcome after the correction.

Keep domain policy in the project. Promote a reusable workflow correction to the common template
with its originating case, applicable boundary and verification; retain project approval and guard
policies. A new rule, a structural check or one successful task does not establish reduced recurrence.
