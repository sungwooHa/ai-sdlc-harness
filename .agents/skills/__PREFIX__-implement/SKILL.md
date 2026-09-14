---
name: __PREFIX__-implement
description: Implement an approved local change plan (or small-change spec) under docs/changes/<YYMMDD_NN>-<slug>, optionally one plan ticket test-first, using this repo's test ladder, review against the plan, then compare realized value with the preserved agreement in pr.md. Use when the user says "구현해", "플랜대로 만들어", "implement", "이 티켓 해", or hands you a plan/spec to build. Wraps the vendored implement + tdd skills.
disable-model-invocation: true
argument-hint: "[폴더명] [티켓 제목] — 예 260910_00-<slug>; 생략하면 plan 또는 합의된 spec 후보를 확인한다"
---

Project adapter around the vendored `implement` skill.

## Before implementation

1. Resolve the change folder from `$0`. Otherwise consider folders containing a working plan
   or an agreed spec; use the only candidate, and ask which folder when more than one exists.
   Read its spec and plan, or the approved spec for a small change without a plan. For a
   multi-file change, a plan is required. If `$1` is given, implement only that plan ticket's
   agreed scope. Read each affected app's `AGENTS.md`.
2. Read `docs/standards/AGREEMENT_REVIEW.md`. Product implementation starts after the applicable
   HTML drafts and plan/spec were presented and explicitly approved. Reuse approval already
   given for that exact revision; do not ask for it again. If the draft was never presented,
   prepare it for agreement before editing product code.
3. Run `python3 scripts/agreement-gate.py status`. A current hook-owned approved revision is
   required; a manually written approval or snapshot is insufficient. If absent, use the
   `__PREFIX__-agreement` skill to prepare and present the decision. Read the preserved spec/plan
   and HTML as the baseline. Record progress in `progress.md`; never edit approved planning inputs.
   Material changes use the agreement skill to prepare and approve a new revision.

## Implement and verify

Call the Skill tool with `implement` and apply these overrides:

- TDD at the agreed seams (`/tdd`); use the repo's narrow-to-wide test ladder. Run declared checks through `python3 scripts/agreement-gate.py verify` to record source-bound
  evidence. Show actual commands and results. Respect protected paths and the commit convention in `AGENTS.md`.
- Implementation commits carry `Plan-Ref: <YYMMDD_NN>-<slug>`; the first commit supplies the
  trailer checked by CI. Keep the entire change folder local and uncommitted.
- Run `/review-since <branch-base>` in a fresh subagent against the referenced agreement's
  spec/plan. This is code correctness review. Run `/__PREFIX__-ui-review <branch-base>` for UI
  changes unless the approved plan explicitly says `시각 변경 없음`; report the waiver.
- Repair blockers and majors. Record DoD and completed tickets in `progress.md` when a plan exists.
  For spec-only work, record acceptance results against its User Stories in the PR. Deferred or
  failed acceptance criteria remain explicit; changing their scope requires renewed agreement.

## Prepare the PR value review

The HTML already existed for pre-implementation agreement. After verification, update only the
working `deliverables/` using the result-evidence column in `AGREEMENT_REVIEW.md`; preserve all
agreed copies. Recheck the actual changed paths against `required_when`. An unexpected required
view or materially different behavior returns to agreement for the remaining work; never label
a retrospective draft as pre-implementation approval. If no HTML condition applies, document
that applicability decision and use the approved spec/plan as the value baseline.

Fill `_templates/pr.md`: reference the agreement revision, compare agreed expectations with
observed changes and evidence, and separate verified behavior from value still needing usage
measurement. Name deviations and the next observation/owner/timing for unverified value (use
`담당 미정` when no owner was agreed). An honest `미검증` can be a handoff if the agreed DoD does
not require the measurement before delivery. The agent does not approve value for the human.

Keep the existing short PR limits. The agreement Stop/pre-commit gate locates the active PR from
state and requires current verification, approved scope and the baseline. It does not judge value
or prove attachment. Provide baseline + current result with directory structure and manifest for manual packaging.
Show pr.md in full for the developer to publish and attach manually; automated push/PR creation
is outside this adapter. Use scoped remove/move helpers for deletion/rename and supported
Write/Edit/apply_patch tools for edits. Arbitrary shell mutation is blocked.

Before finishing, consider knowledge beyond this change: put durable rules in the relevant
app's `AGENTS.md`, or state `지식 승격 없음`. Report implementation/verification status, the
agreement reference, deviations, unverified value, required attachments and actual test results.
Human value review may remain pending after implementation handoff; label it as pending.
