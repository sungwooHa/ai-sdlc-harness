---
name: __PREFIX__-intent
description: Start a change with a grilling interview and write the local (uncommitted) docs/changes/<YYMMDD_NN>-<slug>/intent.md from the template. Use when a request is new, vague, product-facing, or when the user says "의도 정리", "intent", "뭘 만들지 정리".
disable-model-invocation: true
argument-hint: "[slug] — 없으면 인터뷰에서 정한다; 폴더 id(YYMMDD_NN) 는 자동 부여"
---

Call the Skill tool with "grilling" first and run the interview to an empty frontier, with these
overrides (the `question_gate` hook enforces them — a round that breaks them is refused):

- **Ask through `AskUserQuestion`, never as numbered text.** One round = one call, at most 4
  questions, each with 3–4 options: the recommended one first with its label ending in `(추천)`, then
  at least two real alternatives, so the user only has to click where they disagree. If no real
  alternative exists it is a decision, not a question — write it down as the recommendation.
- **Scope the frontier to this stage.** Each question's `header` is one of 문제 · 결과 · 가치 ·
  제약 · 비범위 · 이름 (slug). Anything about *how* — design, data shape, sequencing, tests —
  is not asked here: write it under "열린 질문" with your recommended answer and let
  `/__PREFIX__-spec` ask it.
- **Order by blocking power.** When the frontier is larger than a round, ask the questions whose
  answers unblock the most others first; the rest wait for the next round.

Facts are yours to find (the repo, the docs under `docs/`); decisions are the user's. Do not
propose a design yet; this stage captures the problem, the desired outcome, the value hypothesis,
constraints, and open questions.

When the user confirms shared understanding:

1. Resolve the folder name `<YYMMDD_NN>-<slug>`. Use `$0` as the slug when given; otherwise pick a
   short kebab-case slug with the user. There is no external tracker — the folder is the change
   identifier. Assign the id yourself unless the user passes an explicit one: `<YYMMDD>` is today's
   date (2-digit year, month, day), and `<NN>` is that day's sequence starting at `00`: run
   `ls docs/changes/`, count the folders whose name starts with today's `YYMMDD_` prefix, and
   zero-pad that count to two digits (e.g. `260910_00-<slug>`, then `260910_01-...`).
2. Copy `docs/changes/_templates/intent.md` to `docs/changes/<YYMMDD_NN>-<slug>/intent.md` and fill
   every section in the requester's own words (__HUMAN_DOC_LANG__). Put each unresolved decision
   under "열린 질문" with your recommended answer. Write the header status as `상태: draft`.
3. Show the filled document in full in your reply and wait for the user's explicit confirmation.
   Apply requested edits and show it again. A document nobody has read is not an agreed intent.
   On confirmation set the header to `상태: agreed`.
4. Do not commit it. The change folder is local-only (`.gitignore`; the fast guard refuses staged
   history) — the intent reaches the team through the PR description's 의도 block later.
5. Tell the user the next step is `/__PREFIX__-spec` in this or a fresh session on the same machine.
