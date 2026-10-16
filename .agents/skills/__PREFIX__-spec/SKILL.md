---
name: __PREFIX__-spec
description: Turn an agreed intent into docs/changes/<YYMMDD_NN>-<slug>/spec.md, then enter plan mode. Use right after __PREFIX__-intent, or when the user says "스펙 작성", "명세 정리", "spec", "to-spec".
argument-hint: "[폴더명] — 예 260910_00-<slug>; 생략하면 docs/changes/ 의 최근 intent 폴더를 쓴다"
---

1. Resolve the change folder: `$0` when given, otherwise the folder with the largest
   `<YYMMDD_NN>` id that has `intent.md` but no `spec.md` (`_templates` is not a change folder);
   ask the user when candidates are ambiguous. If no intent exists, invoke
   `Skill(__PREFIX__-intent)` and stop here.
2. Read the folder's `intent.md` and `docs/agents/issue-tracker.md`.
3. Read `.agents/skills/to-spec/SKILL.md` and follow it, with these overrides:
   - **Questions**: ask through `AskUserQuestion` — at most 4 per round, 3–4 options each, the
     recommended one first (label ending in `(추천)`). Start from the intent's "열린 질문"; each
     already carries a recommended answer, so present it as the first option. Plan-level questions
     (file order, rollout) wait for plan mode.
   - **Seams**: check proposed test seams against `apps/<app>/AGENTS.md` for each touched app
     before asking the user to confirm them.
   - **Output**: `docs/changes/<YYMMDD_NN>-<slug>/spec.md` with the headings of
     `docs/changes/_templates/spec.md`, body in __HUMAN_DOC_LANG__, no implementation file paths or
     code snippets, status `draft`. Skip to-spec's publish and label step. For UI work, a mock or
     screenshot beside spec.md is recommended.
   - **Confirm**: show the whole draft and wait for the user's explicit confirmation; apply edits
     and show it again. Then set status `agreed` and commit `spec.md` on `feature/<work-slug>`.
4. Call `EnterPlanMode`. Write the plan in the shape of `docs/changes/_templates/plan.md`
   (`## Files that change` / `## Order of work` / `## Risks` / `## Proof` / `## Value`) and present
   it with `ExitPlanMode`. Repo edits outside `docs/changes/` stay refused until the user approves.
5. After the user approves the plan, invoke `Skill(__PREFIX__-implement)` with args
   `<YYMMDD_NN>-<slug>`.
