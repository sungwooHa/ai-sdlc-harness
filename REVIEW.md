# Pull request review policy

Applies to human reviewers, the `verifier` subagent, `/review-since <base>` (standards + spec),
`/__PREFIX__-ui-review`, and Claude Code Review when enabled (blocker and major = Important,
minor = Nit). Code review checks the implementation against the agreement; the human PR value
review (`docs/standards/AGREEMENT_REVIEW.md` §4) is a separate, later step.

## Passes, in order

| Pass | Question | Source of truth |
|---|---|---|
| Agreement adherence | Does the diff do what the approved revision says, and change nothing outside its scope? | `docs/changes/<YYMMDD_NN>-<slug>/agreements/<revision>/` (spec.md, plan.md), `scope.json` |
| Correctness | Bugs, unhandled states, race conditions, missing tests for stated edge cases | code + tests |
| Contracts | Shared contracts (`packages/*`, API, schema) changed on both sides with compatibility notes? | the contract's owner docs |
| Security & data | Secrets, auth boundaries, real personal data in code, fixtures or tests | `AGENTS.md` Hard rules |
| Design system *(conditional)* | Only once the project records a design system: hardcoded tokens, bypassed inventory, exemptions without a reason | that decision |
| UI quality *(conditional)* | Only for diffs under `__UI_SOURCE_GLOB__` unless the approved plan says `시각 변경 없음` | `/__PREFIX__-ui-review` |

## Severity

- **blocker**: wrong behaviour, contract break, security or data issue, scope or plan violated
  silently. Cannot merge.
- **major**: missing test for a stated edge case, undocumented contract change, rule violation
  with a workaround. Fix before merge unless the author records why not.
- **minor**: clarity, naming, small duplication. Optional.

Each finding names file:line, the defect in one sentence, and a concrete failure scenario. A
finding without a failure scenario is a question: list it after the findings. Style preferences
are not findings.

## Do not report

- Generated files and lockfiles (`protected_paths`), except that they were hand-edited.
- What a hook or `check:harness` already blocks; report only a way around it.
- Issues that exist before the diff, unless the diff makes them worse.

## Repeat findings

When the same class of finding appears in three PRs, it becomes a rule: a line in the relevant
`apps/<app>/AGENTS.md`, or a hook if it must never happen.
