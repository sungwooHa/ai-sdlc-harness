---
name: __PREFIX__-adr
description: Draft or supersede a durable architecture, contract, operations or harness decision as an ADR under docs/decisions/. Use when the user asks "ADR 만들어", "결정 기록해", or replaces an existing decision. Reuse an existing record for an unchanged decision; routine fixes get no ADR.
---

ADR contract (the same values as `docs/decisions/README.md`):

- Root `docs/decisions/`; one decision per file `NNNN-<slug>.md` (four-digit number, short
  lowercase kebab-case slug). Numbers are never reused.
- `0000-harness-decisions.md` is the harness's living record: a harness decision updates it in
  place (git keeps the history). Project ADRs number from `0001`, skipping `0000`: the next one
  takes the highest existing number plus one.
- Template `docs/decisions/_template.md`: header 상태 (`proposed` | `accepted` | `superseded`) ·
  날짜 · 대체함 · 대체됨; sections 배경 · 결정 · 검토한 대안 · 결과와 감수한 비용 · 재검토 조건 ·
  근거. Write it in __HUMAN_DOC_LANG__.

1. Read `docs/decisions/README.md`, related ADRs and the actual code/requirements. If an existing
   ADR still covers the decision, reuse it and stop.
2. Copy the template to the next number and fill it, status `proposed`. A request to draft an ADR
   does not accept its decision. ADR files sit outside `docs/changes/`, so writing one needs an
   approved plan in this session: list the ADR path in the plan.
3. Set `accepted` only after the user approves the decision content, and cite that approval in
   근거; never invent approvals or PR links.
4. Superseding: create a new record rather than rewriting accepted content. Once the replacement is
   accepted, mark the old one `superseded`, set its 대체됨 to the new record and the new record's
   대체함 to the old (`- 대체함: [ADR-0001](0001-example.md)`), and keep the old rationale. While
   the replacement is proposed, both fields stay `없음` and its 배경 names the predecessor.
5. Commit the ADR with the change and report the file, status and decision briefly.
