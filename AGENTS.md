# __PROJECT_NAME__ — Agent Operating Contract

__APPS_OVERVIEW__

Each app has its own `AGENTS.md` (loaded when you work under that app). Deep standards live under
`docs/standards/`; open them only when the app file points there or the task needs the background.

## Workflow (artifact chain)

Every non-trivial change leaves committed artifacts under `docs/changes/<YYMMDD_NN>-<slug>/`
(`<YYMMDD_NN>` = start date + that day's sequence from `00`; `/__PREFIX__-intent` assigns it):

| Stage | When | Do | Artifact |
|---|---|---|---|
| Intent | requirement is unclear or new | `/__PREFIX__-intent` (interviews you, looks up facts itself) | `intent.md` |
| Spec | intent agreed | `/__PREFIX__-spec` (synthesizes from intent + conversation) | `spec.md` |
| Plan | change touches several files | plan mode, then commit the approved plan | `plan.md` |
| Implement | plan approved | `/__PREFIX__-implement` (TDD at agreed seams), narrow tests while iterating | code + commits |
| Review | before declaring done | `/review-since <base>` in a fresh subagent, checked against `plan.md` + `spec.md`; UI diffs also `/__PREFIX__-ui-review` unless `plan.md` says `시각 변경 없음` | findings fixed |
| Deliver | review passed, before the completion report | `/__PREFIX__-implement` generates the four PR deliverables (mockup, flow, architecture, 설명서(eli5)) | `deliverables/` |

The `/__PREFIX__-*` skills are user-invoked: when a request is vague or product-facing and no
`docs/changes/<YYMMDD_NN>-<slug>/intent.md` exists, do not start coding — say what is unclear and
ask the user to run `/__PREFIX__-intent`. Skip stages that add nothing: a one-sentence diff needs no
intent/spec/plan. Never skip Review for diffs that touch more than one app or any shared contract;
CI warns when such a PR carries no `plan.md`.
A change is not done until `docs/changes/<YYMMDD_NN>-<slug>/deliverables/` holds the four PR
deliverables (Deliver row) and every Definition of Done box in `plan.md` is ticked — the completion
report lists them.

Show evidence, not confidence: paste the test/typecheck command you ran and its result.

## Commands

```bash
__PACKAGE_MANAGER__ typecheck                  # replace with this repo's typecheck command
__PACKAGE_MANAGER__ test                       # whole suite
__PACKAGE_MANAGER__ test <one test file>       # narrow run while iterating
__PACKAGE_MANAGER__ test:harness               # only when you changed AGENTS.md, .agents/, .claude/, .codex/, scripts/
```

Scope test runs to the change and widen by directory only when you know what is in it:
one file → sibling directory → whole suite once before commit. A red test is not automatically
yours: compare against a clean checkout before claiming or fixing it.

## Hard rules

<!-- project hard rules here — one line each, only rules an agent would otherwise break -->

- No user-specific absolute paths (`/Users/<name>/...`) in docs, skills, or config; use `<repo-root>`.
- Write agent-facing docs (skills, AGENTS.md, contracts) in English; human-facing docs in __HUMAN_DOC_LANG__.

## Git

- Branches: `__DEFAULT_BRANCH__` (production), `__INTEGRATION_BRANCH__` (integration), `feature/*`.
  PRs target `__INTEGRATION_BRANCH__`.
- Commit: `__COMMIT_FORMAT__` with type in
  feat | fix | docs | style | refactor | test | chore. Details: `.codex/rules/commit-convention.mdc`.
- Pre-commit (husky) runs the harness fast guard. `git commit --no-verify` is for emergencies only;
  say so in the PR.

## Harness

Skills live in `.agents/skills/` (single root; `.claude/skills` is a symlink mirror). Vendored
workflow skills (`grilling`, `to-spec`, `to-tickets`, `implement`, `tdd`, `review-since`, ...) are
reached through the project adapters `__PREFIX__-intent` / `__PREFIX__-spec` / `__PREFIX__-tickets` /
`__PREFIX__-implement`, which supply the change-folder convention
(`docs/agents/issue-tracker.md`: no external tracker, slug folders), the `docs/changes` paths, and
__HUMAN_DOC_LANG__ output; do not call the vendored originals directly. Hooks are declared in
`.agents/harness.yaml` and mirrored in `.claude/settings.json` / `.codex/hooks.json`. Change the
harness only through `docs/standards/AGENT_HARNESS.md`, then run `__PACKAGE_MANAGER__ test:harness`.
