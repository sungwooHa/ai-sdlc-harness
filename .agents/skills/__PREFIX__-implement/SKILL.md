---
name: __PREFIX__-implement
description: Implement an approved local docs/changes/<YYMMDD_NN>-<slug>/plan.md (or one ticket from its `## 티켓` section) test-first, using this repo's test ladder, review against the plan, then write the PR description (pr.md). Use when the user says "구현해", "플랜대로 만들어", "implement", "이 티켓 해", or hands you a plan/spec to build. Wraps the vendored implement + tdd skills.
disable-model-invocation: true
argument-hint: "[폴더명] [티켓 제목] — 예 260910_00-<slug>; 생략하면 docs/changes/ 의 최근 plan.md 를 쓴다"
---

Project adapter around the vendored `implement` skill.

Before calling it:

1. Resolve the change folder (`$0` = the folder name `<YYMMDD_NN>-<slug>`, `$1` = ticket title;
   without `$0`, the most recent `docs/changes/<YYMMDD_NN>-<slug>/` with a `plan.md`). The folders
   are local and uncommitted, so most recent = the newest file mtime
   (`ls -t docs/changes/*/plan.md`); the folder id sorts chronologically, so break a tie with the
   larger id; confirm the folder with the user whenever more than one candidate exists. Read `plan.md` — its file order,
   test plan, and Definition of Done are the contract — and `spec.md` for the user stories. If a
   ticket title is given, scope to that ticket row's one-line scope (한 줄 범위) in the `## 티켓`
   table only. If there is no plan and the change touches several files, stop and ask for plan mode
   first; do not invent a plan inside this skill.
2. Read `apps/<app>/AGENTS.md` for every app the plan touches.

Then call the Skill tool with `implement` and apply these overrides:

- TDD at the seams the plan names (`/tdd`); do not open new seams without telling the user.
- Test ladder from `AGENTS.md`: one file → sibling directory → whole suite once before commit.
  Paste the commands and results, not a summary.
- Never edit a path listed in `.agents/harness.yaml` `protected_paths` by hand.
- Commits follow the repo's commit convention (`AGENTS.md` § Git); one commit per plan step where
  practical. The first implementation commit carries the trailer `Plan-Ref: <YYMMDD_NN>-<slug>`
  (`git commit --trailer 'Plan-Ref: ...'`) — it is the only link between commits and the plan now
  that plan.md is not committed, and CI's plan gate looks for it (`artifact_chain.plan_gate`).
- Never stage anything under `docs/changes/<YYMMDD_NN>-<slug>/`: the folder is local-only and the
  fast guard refuses it.
- Review: run `/review-since <branch-base>` in a fresh subagent with
  `docs/changes/<YYMMDD_NN>-<slug>/spec.md` as the spec source; if the diff touches
  `__UI_SOURCE_GLOB__`, also run `/__PREFIX__-ui-review <branch-base>` — unless the approved
  `plan.md` states `시각 변경 없음`, in which case skip it and say so in the final report
  (`artifact_chain.ui_review_waiver`). Fix blockers and majors, then tick the Definition of Done in
  `plan.md`.
- When a ticket's implementation is done, tick its checkbox in the `## 티켓` table of `plan.md`.

Deliverables (`artifact_chain.deliverables.required_when`): `설명서(eli5).html` whenever the diff
spans two or more `apps/*` or touches a shared contract (the plan-scale case) or a UI path;
`mockup.html`, `flow.html`, `architecture.html` only for a UI path (`__UI_SOURCE_GLOB__`).
Nothing matches → say "산출물 없음" and skip. The `pr_body_gate` hook blocks Stop while a required
file is missing next to `pr.md`. After review passes and before the final report, generate them
under `docs/changes/<YYMMDD_NN>-<slug>/deliverables/` (local; the developer attaches them to the
PR), in parallel subagents where possible:

- `mockup.html` — part 1 static wireframe, part 2 real-render walkthrough: screenshots in feature
  order, each numbered with 무엇을 했나 / 무엇이 보이나(확인 포인트) / 관련 US, images embedded as
  base64 (relative paths do not render for the reader). Capture conditions go in the footer; keep no
  screenshot folder. If no runnable environment exists, say so in the footer and ship part 1 only.
- `flow.html` — usage flow diagram; `architecture.html` — system structure with the changed parts
  highlighted. Budget a diagram before drawing it (split rather than iterate) and delete any
  temporary render artifacts before committing.
- `설명서(eli5).html` — picture-first standalone HTML (inline SVG analogy, "누가 무엇을 보나" table,
  3-box mechanism, checklist). Not Markdown.

Only those files, no `/Users/...` paths, no external URLs, no external hosting. Tick the
deliverables row in `plan.md` Definition of Done.

PR description (`artifact_chain.pr_body`): fill `docs/changes/_templates/pr.md` into
`docs/changes/<YYMMDD_NN>-<slug>/pr.md`. The reader is a reviewer with two minutes: one-sentence
title (누가 · 무엇을 · 얻나, ≤ 60 chars, no placeholders), `Plan-Ref:`, `## 그림` naming the attached
explainer, `## 세 상자` (≤ 3 rows: 무엇이 바뀌었나 | 그래서 | 확인은 — one cause→effect per row),
`## 볼 곳` (≤ 3 files with one reason each), `## 증거` (one fenced block, ≤ 10 lines: command →
result). Whole body ≤ 30 non-empty lines outside the fence. The `pr_body_gate` hook refuses a Write
that breaks this and blocks Stop until it is fixed — do not pad; move detail into the explainer.
Show the file in full in the reply; the developer pastes it as the PR description. This file is the
change's history — the repo keeps none of it.

Knowledge: the change folder is local and disappears with the checkout; only what the next agent
needs survives, and only through this door. Before finishing, ask one question — did this change produce something the next agent
needs beyond the code (a decision, a non-obvious constraint, an operational fact)? If yes and it is
a rule, add one line to the relevant `apps/<app>/AGENTS.md`; otherwise say "지식 승격 없음"
explicitly.

Finish by listing which plan rows are done, which are deferred (and why), the exact test commands
that passed, whether `/__PREFIX__-ui-review` ran or was waived, the deliverables to attach (or the
waiver), the `Plan-Ref` trailer used, the `pr.md` path, and the knowledge decision above.
