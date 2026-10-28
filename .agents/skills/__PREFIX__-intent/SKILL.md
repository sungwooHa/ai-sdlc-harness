---
name: __PREFIX__-intent
description: Capture the requested outcome, scope and decisions in intent.md, reusing settled conversation. Use for intent writing or planning a new or unclear change; interview only after a user request or acceptance. Exclude routine fixes with an established contract and explanation-only requests.
argument-hint: "[slug or active change folder]"
---

Read `docs/standards/execution/stage-handoffs.md` for responsibilities, question ownership and host
equivalents. Capture the current request before considering an interview.

1. Read existing decisions, the active change record and relevant source. Resolve repository
   facts yourself. Identify only material outcome/policy decisions that affect the next work.
   Reuse answers and actual approvals already given; separate assumptions and new proposals.
2. If the user requested or accepted grilling, read `.agents/skills/grilling/SKILL.md` as a
   reference and use its decision tree within this contract. Ask in dependency order until the
   relevant decisions are settled or explicitly deferred. Otherwise offer an interview when
   useful or ask a necessary focused clarification. Ordinary controls, slug/file ordering and
   test details remain agent-owned.
3. Resolve the active folder from the argument or task context. Inspect existing folders rather
   than choosing another task merely because it is newest. Choose a short work slug and an unused
   `docs/changes/<YYMMDD_NN>-<slug>/` identifier; ask only when the task itself is ambiguous.
   Read `docs/agents/issue-tracker.md` for the repository convention.
4. Fill `intent.md` from `docs/changes/_templates/intent.md` in __HUMAN_DOC_LANG__. Preserve
   outcome, value, constraints, exclusions, decision sources and blocking/deferred questions.
   Use `draft` for new proposals. Show the record and obtain explicit confirmation for new or
   changed material decisions; existing agreement may establish `agreed` only for the content it
   actually covered. Do not add a confirmation round for the same decisions again.
5. Commit the agreed intent on `feature/<work-slug>` using
   `docs/standards/COMMIT_CONVENTION.md`. If specification/implementation was requested, continue
   through the `__PREFIX__-spec` adapter with this folder and its decisions. An intent-only
   request finishes with its record and any unresolved decisions.

Read internal references by path and apply these overrides. An absent intent file never starts
grilling automatically. This procedure neither grants plan approval nor authorizes publication.
