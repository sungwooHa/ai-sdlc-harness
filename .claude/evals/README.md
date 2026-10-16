# Harness evals

Behavior regression checks for the agent harness: given only this repo's instructions, skills and hooks,
does an agent do the right thing on the five flows that matter most? Run when `AGENTS.md`, `CLAUDE.md`,
`apps/*/AGENTS.md`, `.agents/**`, `.claude/**` or the hook scripts change.

## Cases (`cases.jsonl`)

One JSON object per line:

- `id`, `prompt` (what a user would type; keep it realistic and short).
- `expect`: checks judged from the run's tool-call trace (`claude -p --output-format stream-json --verbose`)
  and the copy's `git status` — never from the answer's wording:
  - `skill`: a Skill tool call names this skill (`__PREFIX__-x` also matches the copy's initialized prefix).
  - `no_edits_outside`: no changed path outside this prefix (Bash writes count, hook refusals do not matter).
  - `runs_command`: a Bash tool call's command matches this regex.
  - `plan_before_code`: a Write/Edit of a path matching this glob comes before the first Write/Edit of a
    repository path outside `docs/changes/` (order from the trace; attempts count).
  - `written_not_matching`: at least one file changed and none contains this regex.
- `env` (optional): variables for this case's child only. `HARNESS_PLAN_APPROVED` reaches the child only
  when a case sets it here: headless `claude -p` has no EnterPlanMode/ExitPlanMode, so a case that measures
  behavior after plan approval sets it to `1`.
- `critical` (optional): N/N is PASS, at least two thirds (2/3) is WARN (flaky, does not fail the run),
  less is FAIL. Other cases need N/N.
- `measures` (optional, use sparingly): the instruction the case measures, `[{"file", "text"}]`, each text
  occurring exactly once in its file as committed (template paths, before init).
- `measures_todo` (optional): what `measures` should anchor once the text exists; shown by `--mutate`.

The five cases: routing a new-feature request to `__PREFIX__-intent`; plan-first on a direct edit request
(nothing outside `docs/changes/` changes); running the test command after approval; writing a `plan.md`
before code on a multi-app request; no user absolute paths in written files.

## Runner (`scripts/harness/run-evals.py`)

Each run gets its own copy: HEAD's tracked files minus `.claude/evals/**`,
`scripts/test/run-evals.test.py`, `docs/changes/2*` and `docs/references/`, initialized with
`scripts/harness/init-template.sh --project-name acme --prefix acme` (an initialized project has no init
script and is used as is; a failing init is an ERROR and spends no quota), committed in a new git
repository with no remote and nothing leading back to this checkout, which the runner never changes. Every
hook and permission stays. Commit what you want measured first. The agent can still write elsewhere by
absolute path; nothing contains that.

The child runs with `--setting-sources project,local`. Whether that keeps the user's own memory file
(`~/.claude/CLAUDE.md`) out is unverified; every result line says so (`user_memory_isolated`).

Output: one line per case with `PASS|WARN|FAIL k/N`. `--runs N` repeats each case; `--jobs N` runs up to
N copies at once (output stays in case order); `--model` takes the CLI alias (default `sonnet`). Exit
code 1 on any FAIL or ERROR, 2 on an authentication failure.

`--mutate` also runs each case that declares `measures` with that text removed and prints baseline and
mutated side by side: `KILLED k/N` when every mutated run fails, `SURVIVED` otherwise, `ERROR` when the
declaration does not match exactly once or a run got no answer (`claude` exited non-zero, e.g. a usage
limit); `-` for a case without `measures`. A SURVIVED case is kept as a behavior regression test; its
measured instruction is marked `removal_candidate` in the results and a human decides in the PR whether
to delete or reword it. SURVIVED does not fail the run.

Results: each case appends one JSON line to `.claude/evals/results.jsonl` (`--results PATH` to change):
date, sha, model alias and observed model ids, CLI version, case, `baseline` (and `mutated`,
`removal_candidate`), setting sources and the isolation note.

## Login

The runner uses the `claude` CLI's subscription login, nothing else. Other credentials or provider
settings in your environment never reach `claude -p` (also when a case's `env` names them), also inside a
Claude Code session. Log in once with `claude` (then `/login`). If `claude` itself is set up to use another
account or credential (a Console login, a key helper, an active credentials profile), evals use that too:
remove the key helper setting, turn the profile off (`ant auth logout`), then `/login` with your
subscription. The runner aborts on the first authentication failure instead of burning every case.

## Maintenance

`scripts/test/run-evals.test.py` (in `test:harness`, no model use) drives the runner with a fake `claude`
that prints stream-json, and checks that every real case uses known checks and that each declared
`measures` text occurs exactly once. Rewording a measured instruction therefore fails `test:harness` until
the case's `measures` follows the new wording.

Add a case when a PR review or an incident traces back to an instruction the agent ignored. Judge a new
or changed case with `--runs 3`.

```bash
__PACKAGE_MANAGER__ evals:harness                                    # all cases
__PACKAGE_MANAGER__ evals:harness --runs 3 --jobs 4                  # each case three times, four copies at once
__PACKAGE_MANAGER__ evals:harness --mutate --runs 3 --jobs 4         # baseline and mutated side by side
python3 scripts/harness/run-evals.py --only plan-first-direct-edit
```
