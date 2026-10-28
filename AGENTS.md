# __PROJECT_NAME__ — Agent Contract

__APPS_OVERVIEW__
Each app has its own `AGENTS.md`, loaded when you work under that app.

## Commands
- Test: `__PACKAGE_MANAGER__ test` — whole suite, exits non-zero on failure; pre-push runs it too.
- Typecheck: `__PACKAGE_MANAGER__ typecheck` — replace with this repo's typecheck command.
- Harness: `__PACKAGE_MANAGER__ test:harness` after changing AGENTS.md, `.agents/`, `.claude/`, `.husky/`, `scripts/`.

## Verifying your work
- Narrow → wide: one test file, its directory, then the whole suite and typecheck before you report
  done. Paste each command with its output. A failing test means fix the code, not the test.
- For a bug, write the failing test first. For web outcomes, execute `docs/standards/qc/web-acceptance.md`; compare UI with the agreed reference.
  A red test you did not cause: compare with a clean checkout before touching it.

## Workflow — the main session orchestrates
- Route the requested outcome via `docs/standards/AGENT_HARNESS.md#requested-outcomes`; read `docs/standards/execution/stage-handoffs.md` when preparing intent/spec/plan or implementing. Before edits/assignment, read `.agents/skills/__PREFIX__-implement/SKILL.md`.
- Main session: owns dialogue, decisions, planning and acceptance using the host's available tools.
  Subagents execute: implementers (one per plan unit, parallel
  only on disjoint files), `review-since`, `verifier`. They cannot ask the human: blocked → report.
- Flow: select Bug fix/Feature/Refactoring via `__PREFIX__-implement`; reuse decisions in required intent/spec → plan → human approval →
  implementation (commits `plan.md`, runs implementers with the selected route) → `review-since` in a fresh subagent
  (+ `__PREFIX__-ui-review` and agent-browser acceptance for web effects) → `pr.md` from `docs/changes/_templates/pr.md`. Artifacts live in
  `docs/changes/<YYMMDD_NN>-<slug>/`, branch `feature/<slug>`. A typo-sized fix skips intent/spec;
  after approval it still works on `feature/<slug>`, verifies and commits.
- Accept delegates only after actual completion and result inspection; failed startup is an unsuccessful attempt.
  In Claude, wait for background implementers before EnterPlanMode: it clears their approval.

## Enforced by the system
- Plan-first (Claude Code hook): Edit/Write to a repo file outside `docs/changes/**` is refused
  unless this session had a plan approved since it last entered plan mode — that is all it means,
  not that this change's plan was approved.
  Edit files with Edit/Write, never `sed -i`, redirects or scripts. Headless runs use
  `HARNESS_PLAN_APPROVED=1`, set by a human only. This template has no Codex session hook: show the plan, await approval.
- Protected paths (`.agents/harness.json` `protected_paths`), format-on-edit slot (`format_on_edit`),
  pre-commit secret scan of the staged diff, pre-push `__PACKAGE_MANAGER__ test`.

## Guide — humans check it in PR review against `REVIEW.md`
- High-risk = two or more `apps/*`, a shared contract (`packages/**`, `**/openapi.*`, `**/*.proto`,
  `**/migrations/**`) or a security path (`**/auth/**`, `**/permissions/**`, `**/security/**`):
  commit `intent.md`, `spec.md`, `plan.md` to the change folder before any code edit; never skip review.
- When the work departs from the plan, update `plan.md` in the same commit.
- Commits follow `docs/standards/COMMIT_CONVENTION.md`; no `Co-Authored-By`. The human pushes.
- Ask only for material outcome/risk decisions; reuse answers and approval. Formal grilling needs a request or acceptance.
- Agent-facing docs in English, human-facing docs in __HUMAN_DOC_LANG__.
- `pr.md` is the value review: expected value vs. actual result; unverified value stays explicit.
- Branches: `__DEFAULT_BRANCH__` (production), `__INTEGRATION_BRANCH__` (integration), `feature/*`.
  PRs target `__INTEGRATION_BRANCH__`.

## Things agents get wrong
- Calling EnterPlanMode while implementers run.
- Accepting a subagent's report unchecked; asking the human for facts the repo can answer.
- Calling the vendored skills behind `__PREFIX__-*` adapters directly (`grilling`, `to-spec`, ...).
<!-- Add a line when an agent makes the same mistake twice. -->

## Harness
Yardstick: `docs/references/anthropic-ai-native-sdlc-playbook.pdf` via `docs/standards/PLAYBOOK_MAP.md`.
Principles: `docs/standards/HARNESS_PRINCIPLES.md`; decisions: `docs/decisions/0000-harness-decisions.md`.
Change it only through `docs/standards/AGENT_HARNESS.md`; edit skills in `.agents/skills/`.
