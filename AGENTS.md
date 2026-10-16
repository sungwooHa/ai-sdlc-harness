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
- For a bug, write the failing test first. For UI, compare a screenshot with the agreed mock.
  A red test you did not cause: compare with a clean checkout before touching it.

## Workflow — the main session orchestrates
- Main session: talks to the human, runs the dialogue skills, calls EnterPlanMode/ExitPlanMode,
  decides with the human, synthesizes. Subagents execute: implementers (one per plan unit, parallel
  only on disjoint files), `review-since`, `verifier`. They cannot ask the human: blocked → report.
- Flow: `__PREFIX__-intent` → `__PREFIX__-spec` → EnterPlanMode → human approval →
  `__PREFIX__-implement` (commits `plan.md`, runs implementers) → `review-since` in a fresh subagent
  (+ `__PREFIX__-ui-review` for UI) → `pr.md` from `docs/changes/_templates/pr.md`. Artifacts live in
  `docs/changes/<YYMMDD_NN>-<slug>/`, branch `feature/<slug>`. A typo-sized fix skips intent/spec;
  after approval it still works on `feature/<slug>`, verifies and commits.
- Agent calls run in the background: wait for each completion notification, check the output, then
  accept it. Call EnterPlanMode only after background implementers finish: it clears their approval.

## Enforced by the system
- Plan-first (Claude Code hook): Edit/Write to a repo file outside `docs/changes/**` is refused
  unless this session had a plan approved since it last entered plan mode — that is all it means,
  not that this change's plan was approved.
  Edit files with Edit/Write, never `sed -i`, redirects or scripts. Headless runs use
  `HARNESS_PLAN_APPROVED=1`, set by a human only. Codex has no hook: show the plan, await approval.
- Protected paths (`.agents/harness.json` `protected_paths`), format-on-edit slot (`format_on_edit`),
  pre-commit secret scan of the staged diff, pre-push `__PACKAGE_MANAGER__ test`.

## Guide — humans check it in PR review against `REVIEW.md`
- High-risk = two or more `apps/*`, a shared contract (`packages/**`, `**/openapi.*`, `**/*.proto`,
  `**/migrations/**`) or a security path (`**/auth/**`, `**/permissions/**`, `**/security/**`):
  commit `intent.md`, `spec.md`, `plan.md` to the change folder before any code edit; never skip review.
- When the work departs from the plan, update `plan.md` in the same commit.
- Commits follow `docs/standards/COMMIT_CONVENTION.md`; no `Co-Authored-By`. The human pushes.
- Ask the human only for decisions (AskUserQuestion, ≤4 per round, recommended option first).
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
