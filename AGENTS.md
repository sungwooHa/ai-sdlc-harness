# __PROJECT_NAME__ — Agent Operating Contract

__APPS_OVERVIEW__

Each app has its own `AGENTS.md` (loaded when you work under that app). Deep standards live under
`docs/standards/`; open them only when the app file points there or the task needs the background.

## Principles

Four principles govern every harness rule below — full text and rationale in
`docs/standards/HARNESS_PRINCIPLES.md`; nothing is added to the harness that fails all four:
(1) rules in the repo, history on the PR; (2) enforce with the system, not with prose;
(3) minimum cognitive load for humans; (4) facts are the agent's, decisions are the user's — take
only the stages you need.

## Workflow (artifact chain)

Every non-trivial change works in a local, uncommitted folder `docs/changes/<YYMMDD_NN>-<slug>/`
(`<YYMMDD_NN>` = start date + that day's sequence from `00`; `/__PREFIX__-intent` assigns it). The repo
keeps rules only; the change's history goes to the PR (description from `_templates/pr.md`, attachments):

| Stage | When | Do | Artifact |
|---|---|---|---|
| Intent | requirement is unclear or new | `/__PREFIX__-intent` (interviews you, looks up facts itself) | `intent.md` |
| Spec | intent agreed | `/__PREFIX__-spec`; draft the applicable HTML views for human agreement | `spec.md`, draft `deliverables/` |
| Plan / Agree | before nontrivial implementation | refine plan (or small-change spec) + HTML, present for approval, preserve agreed revision (see `AGREEMENT_REVIEW.md`) | `plan.md`, `agreements/<revision>/` |
| Implement | presented plan/drafts approved and baseline preserved | `/__PREFIX__-implement` (TDD at agreed seams), narrow tests while iterating | code + commits |
| Code review | after implementation, before value handoff | `/review-since <base>` in a fresh subagent, checked against the referenced agreement's spec/plan; UI diffs also `/__PREFIX__-ui-review` unless `plan.md` says `시각 변경 없음` | findings fixed |
| PR value review | code review passed | compare agreed value with actual results; update working HTML, preserve the baseline, write short `pr.md` with unverified value and follow-up | result `deliverables/`, `pr.md` (local → PR) |

Questions to the user in Intent, Spec, and plan mode go through `AskUserQuestion` only — at most 4
per round, 3–4 options each with the recommended one first (`(추천)`), header limited to the stage's
categories declared in `harness.yaml` `question_gate`; a hook refuses numbered text question rounds
and non-compliant calls.
The `/__PREFIX__-*` skills are user-invoked: when a request is vague or product-facing and no
`docs/changes/<YYMMDD_NN>-<slug>/intent.md` exists, do not start coding — say what is unclear and
ask the user to run `/__PREFIX__-intent`. Skip stages that add nothing: small changes may skip intent/plan and inapplicable HTML, but still need spec, scope and
hook-owned agreement. Never skip Review for diffs that touch more than one app or any shared contract;
CI warns when such a PR carries no `Plan-Ref` commit trailer.
Before spec/plan agreement and PR delivery, read `docs/standards/AGREEMENT_REVIEW.md`.
HTML is reviewed before implementation; the PR is the human value review.
For artifact-chain changes, implementation handoff requires that `pr.md` passes the `pr_body_gate` hook, the deliverables required by
`harness.yaml` `artifact_chain.deliverables.required_when` exist beside it, and every applicable Definition of
Done criterion in the approved plan has a result in `progress.md` — unverified value stays explicit; it is not human acceptance. Never commit anything under a
change folder (the fast guard refuses it; `local_only_roots`).

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
- Pre-commit (husky) runs the harness fast guard. the agreement gate requires scope, current verification and local PR value review; agent
  `--no-verify` is blocked.

## Harness

Skills live in `.agents/skills/` (single root; `.claude/skills` is a symlink mirror). Vendored
workflow skills (`grilling`, `to-spec`, `to-tickets`, `implement`, `tdd`, `review-since`, ...) are
reached through the project adapters `__PREFIX__-intent` / `__PREFIX__-spec` / `__PREFIX__-tickets` /
`__PREFIX__-agreement` / `__PREFIX__-implement`, which supply the change-folder convention
(`docs/agents/issue-tracker.md`: no external tracker, slug folders), the `docs/changes` paths, and
__HUMAN_DOC_LANG__ output; do not call the vendored originals directly. Hooks are declared in
`.agents/harness.yaml` and mirrored in `.claude/settings.json` / `.codex/hooks.json`. Change the
harness only through `docs/standards/AGENT_HARNESS.md`, then run `__PACKAGE_MANAGER__ test:harness`.

Ponytail is a code-simplification aid: use `__PREFIX__-ponytail` for project overrides. Its modes
never waive agreed scope, required HTML/ADR/PR evidence, security, accessibility or verification.
