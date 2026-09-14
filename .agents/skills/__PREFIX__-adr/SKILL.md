---
name: __PREFIX__-adr
description: Draft or supersede a durable architecture, contract, operations or harness decision as an ADR. Use when the user asks "ADR 만들어", "결정 기록해", replaces an existing decision, or the agreement hook supplies ADR suggestion candidates. Reuse an existing record for an unchanged decision; do not create an ADR for every routine fix.
---

Read `adr_gate` in `.agents/harness.yaml`, its template and `docs/decisions/README.md`.
Read related ADRs and the actual code/requirements; use the configured root and human document language.

For hook-triggered advice, inspect the planned decision behind the matched paths. A path match
alone is not a decision. If it is a routine fix, stay quiet. If an existing ADR still applies,
reuse it without proposing a duplicate. Otherwise briefly suggest a title, why this decision
should survive the PR, and the proposed choice. Do not demand a separate permission round merely
to offer advice; drafting follows the user's scope and the existing agreement flow. Never treat
silence, the hook hint, or acceptance of a suggestion as approval of unseen decision content.

1. Resolve the decision and related records. Reuse an existing ADR when its decision still applies.
   Otherwise choose the next unused four-digit ID and a short lowercase slug. Keep one decision
   per file and explain the context, choice, alternatives, costs and revisit trigger.
2. Read agreement status with `python3 scripts/agreement-gate.py status`. If the current grant
   covers the exact ADR paths and decision, continue without asking again. Otherwise put the
   proposed ADR content in the local spec/plan, include all ADR paths in scope.json and use
   `__PREFIX__-agreement`. A request to draft an ADR does not mean its decision is accepted.
   Keep unapproved decision content proposed, and do not write tracked files before the gate permits it.
3. Write the ADR using the configured template after the required scope agreement. Set accepted
   only from real decision approval and cite that record in 근거; never invent approval or PR links.
   Existing accepted content is not a mutable working plan. For a changed decision, create a new
   record. Once the replacement is accepted, mark the old one superseded, set its 대체됨 link to
   the new record and the new record's 대체함 link back to the old. Preserve the old rationale.
   While the replacement is merely proposed, leave both replacement fields 없음 and cite the
   intended predecessor in its context; the accepted decision remains current.
4. Run `python3 scripts/adr-gate.py --all`. Fix structural/reference errors, then use the existing
   agreement verification and PR handoff. Include the ADR validator in the agreed verification
   commands for ADR-only work. Update the index only when needed and include its path in scope.

The hooks check structure and replacement links at delivery, not the quality of a decision or
whether a person understood it. Report the file, status and decision briefly; a pending proposal
is not implementation completion. Do not add recurring ADR obligations or publish a PR implicitly.
