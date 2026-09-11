---
name: __PREFIX__-spec
description: Synthesize the agreed intent into docs/changes/<YYMMDD_NN>-<slug>/spec.md. Use after /__PREFIX__-intent when the user says "스펙 작성", "spec 만들어", "명세 정리", "to-spec", or asks to turn the discussion into a spec. Wraps the vendored to-spec skill with this repo's paths and language.
disable-model-invocation: true
argument-hint: "[폴더명] — 예 260910_00-<slug>; 생략하면 docs/changes/ 의 최근 intent 폴더를 쓴다"
---

Project adapter around the vendored `to-spec` skill. `to-spec` knows how to synthesize a spec; it
does not know this repo's folder layout or language — you supply those and never let it fall back
to its own defaults.

Before calling it:

1. Resolve the change folder. Use `$0` (the folder name `<YYMMDD_NN>-<slug>`) when given; otherwise
   pick the most recent `docs/changes/<YYMMDD_NN>-<slug>/` that has `intent.md` but no `spec.md`,
   and confirm it with the user. Most recent = the folder whose relevant document was added by the
   newest commit (`git log -1 --format=%ct -- <path>`); the folder id sorts chronologically, so
   break a tie with the larger id; if candidates are still ambiguous, ask the user. If no intent
   exists, stop and tell the user to run `/__PREFIX__-intent` first.
2. Read `docs/changes/<YYMMDD_NN>-<slug>/intent.md` and `docs/agents/issue-tracker.md`. There is no
   external tracker and no `ready-for-agent` label — if the vendored skill asks for one, treat the
   repo copy as the single source and skip the step.

Then call the Skill tool with `to-spec` and apply these overrides while following it:

- Seams: check the proposed test seams against `apps/<app>/AGENTS.md` for the touched app before
  asking the user to confirm them.
- Output: draft the spec with the section headings of `docs/changes/_templates/spec.md` (keep the
  headings, fill the body in __HUMAN_DOC_LANG__, no file paths or code snippets) and header status
  `draft`.
- Confirm before commit: once the seams are agreed, show the whole draft in your reply and wait for
  the user's explicit confirmation; apply edits and show it again. Only then write it to
  `docs/changes/<YYMMDD_NN>-<slug>/spec.md` with status `agreed` (keep `draft` if the user says
  they will keep iterating) and commit. Never commit a spec the user has not seen in full.
- No publishing step: the committed file is the only copy.

Finish by telling the user the next step: plan mode for a multi-file change (commit the approved
plan as `docs/changes/<YYMMDD_NN>-<slug>/plan.md`), or `/__PREFIX__-implement` directly for a small one.
