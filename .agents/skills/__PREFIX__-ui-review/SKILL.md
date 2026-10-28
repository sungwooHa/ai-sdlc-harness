---
name: __PREFIX__-ui-review
description: Review user-visible changes for design, behavior and browser acceptance, including helper/API/validation effects outside __UI_SOURCE_GLOB__. Use before UI implementation for scope, before delivery, or for UI review requests. Internal-only work uses ordinary code review.
argument-hint: "[base ref, e.g. origin/__INTEGRATION_BRANCH__] — base defaults to the merge-base with __INTEGRATION_BRANCH__"
---

Project adapter that runs the UI quality layer. It reads the vendored review skills by path and
reports in the severities `REVIEW.md` defines.

## 1. Scope the diff

1. Before implementation and again before delivery, read
   [user journey review](references/user-journey-review.md). Select the affected finish, input and
   recovery cases from the existing product contract. For web, prepare
   `docs/standards/qc/web-acceptance.md`. A new screen has no fabricated before image.
2. Prefer the task-owned diff/baseline when concurrent changes exist; otherwise resolve the base
   (`$0`, else `git merge-base HEAD origin/__INTEGRATION_BRANCH__`). Start at `__UI_SOURCE_GLOB__`
   and follow helpers/API/state changes with visible effects. Stop only when the scope has no
   visible effect; a missing UI-path diff or `시각 변경 없음` alone is insufficient.
3. Review rendering/behavior against the existing project contract and the selected journey cases.
   Include markup, styles and relevant state/validation; apply motion criteria only to changed
   motion. Internal-only work uses ordinary code review; it does not need journey cases.

## 2. Code pass (in this session, one after another)

- Read `.agents/skills/web-design-guidelines/SKILL.md` and follow it on the UI files. It fetches its
  rule set at run time; if the fetch fails, say so and skip rather than judging from memory.
- If there are motion files, read `.agents/skills/review-animations/SKILL.md` and the files it
  references, and follow it on them. Otherwise skip and say so.

## 3. Browser acceptance

For web outcomes, execute `docs/standards/qc/web-acceptance.md`. When called from `__PREFIX__-implement`,
its browser step owns assignment and execution; reuse current-candidate evidence rather than
running the same step twice. For standalone verification, own that execution here. A request
limited to static review stays within that scope and labels browser outcomes unverified.
Native-only changes use the project's device/emulator procedure and report unavailable coverage.

## 4. Report

- Deduplicate: a defect flagged by more than one pass is one finding; keep one file:line.
- Rank each finding with the `REVIEW.md` severities and apply its rules (failure scenario or
  question, what not to report). The vendored skills' own labels are inputs, not severities.
- Output in __HUMAN_DOC_LANG__: findings ranked blocker → major → minor with the pass that found
  them, then questions, then 미검증 잔여 (skipped passes, with the reason).

Report failures to finish, preserve values or recover before visual findings, and missing execution as unverified. Keep code,
rendered interaction, connected E2E and input-device coverage separate; screenshots alone do
not complete the journey. Apply any project visual-review procedure alongside this contract.
