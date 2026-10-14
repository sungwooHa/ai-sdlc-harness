# Harness evals

Regression checks for the agent harness itself: does an agent, given only the repo's instructions,
do the right thing on tasks we have actually seen go wrong? Run when `AGENTS.md`, `apps/*/AGENTS.md`,
`.agents/**`, `.claude/**`, or `scripts/*guard*` change.

- `cases.jsonl`: one case per line — `id`, `prompt` (what a user would type), `expect` (checks the
  runner can evaluate: `output_matches`, `output_not_matches`, `files_unchanged_glob`,
  `files_changed_not_matching`, `command_succeeds`), `measures` (the instruction the case measures:
  `[{"file", "text"}]`, each text occurring exactly once in its file).
- `scripts/harness/run-evals.py`: runs each case with `claude -p` (model alias `sonnet` unless
  `--model` says otherwise) in a throwaway copy, evaluates `expect`, prints a table with
  k/N per case, exits non-zero on any failure. `--runs N` repeats each case; PASS needs N/N.
  `--jobs N` runs up to N copies at once (output stays in case order). `--mutate` removes each case's
  `measures` from the copy and expects the case to fail: `KILLED k/N` when every run fails, `SURVIVED`
  with the agent's words otherwise, `ERROR` when the declaration is missing or does not match. Declared in
  `.agents/harness.yaml` `evals`; `__PACKAGE_MANAGER__ evals:harness` is the entry point. It spends model quota,
  so it is not part of `__PACKAGE_MANAGER__ test:harness`.

The copy is HEAD's tracked files in a new git repository: no remote, no history and nothing that leads
back to this checkout, which the runner never changes. Commit what you want measured first. The copy's
`.claude/settings.json` leaves out the agreement gate's hooks, so an edit case measures the instructions,
not the gate (the gate's own unit tests guard it); every other hook and `permissions.deny` stay. The
agent in a copy can still write elsewhere by absolute path; nothing contains that.

Login: the runner uses the `claude` CLI's subscription login, nothing else. Other credentials or
provider settings in your environment never reach `claude -p`, also inside a Claude Code session.
Log in once with `claude` (then `/login`). If `claude` itself is set up to use another account or
credential (a Console login, a key helper, an active credentials profile), evals use that too: remove the
key helper setting, turn the profile off (`ant auth logout`), then `/login` with your subscription. The
runner aborts on the first authentication failure instead of burning every case.

Known limits: `/__PREFIX__-*` skills are `disable-model-invocation`, so a case cannot expect the agent to
*run* one — it can only expect the agent to *point the user to* it (`vague-request-asks-for-intent`).
Answers vary between runs: judge a new or changed case with `--runs 3` (PASS needs 3/3). A case earns
its place only when it measures the agent, not another gate: `--mutate`, which removes the instruction
it declares in `measures`, must make it FAIL (`KILLED`). So answer checks name this repo's own wording (a protected path's `instead`,
`<repo-root>`) rather than what general knowledge would say anyway, and a case that a hook already
decides deterministically (the commit-msg format) is not repeated here.

Add a case whenever a PR review or an incident traces back to an instruction the agent ignored.
Keep prompts realistic and short; the point is the repo's instructions, not the prompt.

```bash
__PACKAGE_MANAGER__ evals:harness                                    # all cases
__PACKAGE_MANAGER__ evals:harness --runs 3 --jobs 6                  # each case three times, six copies at once
__PACKAGE_MANAGER__ evals:harness --mutate --runs 3 --jobs 6         # does each case fail without its instruction?
python3 scripts/harness/run-evals.py --only protected-path-untouched
```
