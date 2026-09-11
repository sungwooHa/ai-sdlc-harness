---
name: __PREFIX__-ui-review
description: Review a UI diff for design quality — web-design-guidelines on the changed UI files, plus review-animations when motion files changed — and report findings ranked blocker → major → minor. Use after changing __UI_SOURCE_GLOB__, before declaring a UI change done, or when the user says "UI 리뷰", "화면 리뷰", "디자인 검토", "ui review". Not for logic/spec review (/review-since).
argument-hint: "[base ref, e.g. origin/__INTEGRATION_BRANCH__] — base defaults to the merge-base with __INTEGRATION_BRANCH__"
---

Project adapter that runs the UI quality layer. It wraps the vendored review skills and reports in
this repo's severities.

## 1. Scope the diff

1. Resolve the base (`$0`, else `git merge-base HEAD origin/__INTEGRATION_BRANCH__`) and list the
   changed files matching `__UI_SOURCE_GLOB__`. If none, say so and stop.
2. Split them: **UI files** (anything rendering markup) and **motion files** (animation/transition
   definitions, `@keyframes`, motion tokens). Everything else is out of scope.

## 2. Code pass (in this session, one after another)

- Call `web-design-guidelines` with the UI files. It fetches its rule set at run time; if the fetch
  fails, say so and skip rather than judging from memory.
- If there are motion files, call `review-animations` with them. Otherwise skip and say so.

## 3. Report

- Deduplicate: a defect flagged by more than one pass is one finding; keep one file:line.
- Severities: broken screen, leaked identifiers, console errors → **blocker/major**;
  Recommended / warn → **minor** unless it repeats across screens; Nit / info → one line or drop.
- A finding without a concrete failure scenario is a question — list questions after findings, not
  among them.
- Output in __HUMAN_DOC_LANG__: findings ranked blocker → major → minor with the pass that found
  them, then questions, then 미검증 잔여 (skipped passes, with the reason).

Add a render pass here when the project has one (a screenshot critic subagent under
`.claude/agents/`); until then say the render pass was not run.
