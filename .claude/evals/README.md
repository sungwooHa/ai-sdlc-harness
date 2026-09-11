# Harness evals

Regression checks for the agent harness itself: does an agent, given only the repo's instructions,
do the right thing on tasks we have actually seen go wrong? Run when `AGENTS.md`, `apps/*/AGENTS.md`,
`.agents/**`, `.claude/**`, or `scripts/*guard*` change.

- `cases.jsonl`: one case per line — `id`, `prompt` (what a user would type), `expect` (checks the
  runner can evaluate: `output_matches`, `output_not_matches`, `files_unchanged_glob`,
  `files_changed_not_matching`, `command_succeeds`).
- `scripts/harness/run-evals.py`: runs each case with `claude -p` in a throwaway git worktree,
  evaluates `expect`, prints a table, exits non-zero on any failure. Declared in
  `.agents/harness.yaml` `evals`; `__PACKAGE_MANAGER__ evals:harness` is the entry point. It spends model quota,
  so it is not part of `__PACKAGE_MANAGER__ test:harness`. The `claude` CLI uses whatever login it has — with no
  `ANTHROPIC_API_KEY` in the environment a claude.ai subscription login is used, not API billing.

Auth: a Claude Code session exports a session-scoped `ANTHROPIC_API_KEY` that `claude -p` rejects
with 401, so from inside a session run with `--login` (drops the key, uses the claude.ai login). The
runner aborts on the first authentication failure instead of burning every case.

Known limits: `/__PREFIX__-*` skills are `disable-model-invocation`, so a case cannot expect the agent to
*run* one — it can only expect the agent to *point the user to* it (`vague-request-asks-for-intent`).

Add a case whenever a PR review or an incident traces back to an instruction the agent ignored.
Keep prompts realistic and short; the point is the repo's instructions, not the prompt.

```bash
__PACKAGE_MANAGER__ evals:harness                                    # all cases
__PACKAGE_MANAGER__ evals:harness --login                             # from inside a Claude Code session (see below)
python3 scripts/harness/run-evals.py --only protected-path-untouched
```
