---
name: __PREFIX__-intent
description: Capture a new or vague request as docs/changes/<YYMMDD_NN>-<slug>/intent.md through an interview, then hand off to spec. Use when the user asks for a new feature or product change and no intent.md exists — "새 기능", "기획", "만들어줘", "의도 정리", "new feature", "build me", "intent".
argument-hint: "[slug] — 없으면 인터뷰에서 정한다; 폴더 id(YYMMDD_NN) 는 자동 부여"
---

Read `.agents/skills/grilling/SKILL.md` and follow it to an empty frontier, with these overrides:

- **Questions**: ask through `AskUserQuestion`. One round = one call, at most 4 questions, each
  with 3–4 options: the recommended one first with its label ending in `(추천)`, then real
  alternatives, so the user only clicks where they disagree. A question with no real alternative
  is a decision: write it down as the recommendation. Numbered text rounds are fine when the user
  runs `/grilling` themselves.
- **Frontier scope**: 문제 · 결과 · 가치 · 제약 · 비범위 · 이름 (slug). *How* questions (design,
  data shape, sequencing, tests) go under "열린 질문" with your recommended answer;
  `__PREFIX__-spec` asks them.
- **Order by blocking power**: when the frontier exceeds a round, ask first what unblocks the most.

Facts are yours to find (the repo, `docs/`); decisions are the user's.

When the user confirms shared understanding:

1. Resolve the folder name `<YYMMDD_NN>-<work-slug>`. Use `$0` as the work slug when given;
   otherwise agree with the user on a short kebab-case slug that tells this change's purpose
   apart. The work slug names the branch `feature/<work-slug>` and the PR. Assign the id yourself
   unless the user passes one: `<YYMMDD>` is today's date, `<NN>` is that day's sequence from
   `00` — count the folders in `ls docs/changes/` that start with today's `YYMMDD_` prefix and
   zero-pad the count (`260910_00-<work-slug>`, then `260910_01-...`).
2. Copy `docs/changes/_templates/intent.md` to `docs/changes/<YYMMDD_NN>-<work-slug>/intent.md`
   and fill every section in the requester's own words (__HUMAN_DOC_LANG__), each unresolved
   decision under "열린 질문" with your recommended answer, header `상태: draft`.
3. Show the filled document in full and wait for the user's explicit confirmation; apply edits and
   show it again. On confirmation set `상태: agreed`.
4. Commit `intent.md` on `feature/<work-slug>` (create it with `git switch -c` when you are not on
   it), message per `docs/standards/COMMIT_CONVENTION.md`.
5. Invoke `Skill(__PREFIX__-spec)` with args `<YYMMDD_NN>-<work-slug>`.
