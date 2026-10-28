---
name: __PREFIX__-spec
description: Turn settled request decisions into observable behavior, acceptance criteria and spec.md, then prepare a plan when implementation was requested. Use for specification or as the approved workflow's specification stage; do not restart an interview merely because intent.md is absent.
argument-hint: "[active change folder]"
---

Read `docs/standards/execution/stage-handoffs.md` for stage responsibilities and host equivalents.

1. Resolve the folder from the argument or active task, not the newest unrelated record.
   Read its intent/decisions, relevant source and `docs/agents/issue-tracker.md`. If a required
   intent is absent, use the `__PREFIX__-intent` adapter to record the existing request and
   decisions. Interview only after the user requested or accepted one.
2. Read `.agents/skills/to-spec/SKILL.md` as a synthesis reference and apply this adapter's
   contract. Ask only about unresolved material behavior, external contracts or policy.
   Resolve repository facts, ordinary implementation details and useful test seams yourself.
3. Write `spec.md` using `docs/changes/_templates/spec.md` in __HUMAN_DOC_LANG__:
   - preserve the source decisions and distinguish approved behavior, assumptions and open items;
   - define observable acceptance criteria, including normal entry/finish, boundary input,
     cancellation, interruption and failure/recovery where applicable;
   - include external API/data semantics when they define the requested behavior. Keep internal
     file lists, sequencing and verification commands for the plan;
   - for visible behavior, read `__PREFIX__-ui-review` for journey/design scope and consult
     `docs/standards/qc/web-acceptance.md` for web criteria. A mock may clarify a decision but
     does not establish that the product works.
4. Show the spec in full. Obtain explicit confirmation for new or changed material decisions;
   reuse actual agreement for unchanged content. Record `draft` or `agreed` honestly and commit it on
   `feature/<work-slug>`. A spec-only request finishes here with unresolved matters explicit.
5. When implementation was also requested, prepare the plan in
   `docs/changes/_templates/plan.md` using native plan mode when available, otherwise present
   it in conversation. Map every acceptance criterion to changed boundaries, dependency order,
   risks and executable proof. Prepare the web backend/account/browser/failure/cleanup context
   before promising E2E; missing prerequisites remain explicit. Resolve routine choices locally.
6. Present the plan through the host's supported approval path and wait for required approval.
   Reuse existing approval only when it actually covers this plan and scope. After approval,
   continue through `__PREFIX__-implement` with the folder, decisions, criteria and proof context.

The reference's tracker publication/labels do not apply. Read adapters by path when the host has
no Skill tool. No tool name or document status manufactures write approval.
