# Harness evals

Regression checks for the agent harness itself: does an agent, given only the repo's instructions,
do the right thing on tasks we have actually seen go wrong? Run when `AGENTS.md`, `apps/*/AGENTS.md`,
`.agents/**`, `.claude/**`, or `scripts/*guard*` change.

- `cases.jsonl`: one case per line — `id`, `prompt` (what a user would type), `expect` (checks the
  runner can evaluate: `output_matches`, `output_not_matches`, `files_unchanged_glob`,
  `files_changed_not_matching`, `command_succeeds`).
- `scripts/harness/run-evals.py`: runs each case with `claude -p` (model alias `sonnet` unless
  `--model` says otherwise) in a throwaway git worktree, evaluates `expect`, prints a table with
  k/N per case, exits non-zero on any failure. `--runs N` repeats each case; PASS needs N/N. Declared in
  `.agents/harness.yaml` `evals`; `__PACKAGE_MANAGER__ evals:harness` is the entry point. It spends model quota,
  so it is not part of `__PACKAGE_MANAGER__ test:harness`.

Login: the runner uses the `claude` CLI's subscription login, nothing else. Other credentials or
provider settings in your environment never reach `claude -p`, also inside a Claude Code session.
Log in once with `claude` (then `/login`). If `claude` itself is set up to use another account or
credential (a Console login, a key helper, an active credentials profile), evals use that too: remove the
key helper setting, turn the profile off (`ant auth logout`), then `/login` with your subscription. The
runner aborts on the first authentication failure instead of burning every case.

Known limits: `/__PREFIX__-*` skills are `disable-model-invocation`, so a case cannot expect the agent to
*run* one — it can only expect the agent to *point the user to* it (`vague-request-asks-for-intent`).
Answers vary between runs: judge a new or changed case with `--runs 3` (PASS needs 3/3). A case earns
its place only when it measures the agent, not another gate: removing the instruction it tests from a
copy must make it FAIL. So answer checks name this repo's own wording (a protected path's `instead`,
`<repo-root>`) rather than what general knowledge would say anyway, and a case that a hook already
decides deterministically (the commit-msg format) is not repeated here.

Add a case whenever a PR review or an incident traces back to an instruction the agent ignored.
Keep prompts realistic and short; the point is the repo's instructions, not the prompt.

```bash
__PACKAGE_MANAGER__ evals:harness                                    # all cases
__PACKAGE_MANAGER__ evals:harness --runs 3                           # each case three times; PASS needs 3/3
python3 scripts/harness/run-evals.py --only protected-path-untouched
```
