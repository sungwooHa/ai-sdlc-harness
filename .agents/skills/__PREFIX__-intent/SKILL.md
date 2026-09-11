---
name: __PREFIX__-intent
description: Start a change with a grilling interview and write docs/changes/<YYMMDD_NN>-<slug>/intent.md from the template. Use when a request is new, vague, product-facing, or when the user says "의도 정리", "intent", "뭘 만들지 정리".
disable-model-invocation: true
argument-hint: "[slug] — 없으면 인터뷰에서 정한다; 폴더 id(YYMMDD_NN) 는 자동 부여"
---

Call the Skill tool with "grilling" first and run the interview to an empty frontier.

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
   Apply requested edits and show it again. Do not commit before that confirmation — a document
   nobody has read is not an agreed intent. On confirmation set the header to `상태: agreed`.
4. Commit the file following the repo's commit convention (`AGENTS.md` § Git).
5. Tell the user the next step is `/__PREFIX__-spec` in this or a fresh session.
