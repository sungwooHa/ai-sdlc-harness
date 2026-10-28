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

The five cases: routing a new-feature request to `__PREFIX__-intent`; plan-first on a direct edit request
(nothing outside `docs/changes/` changes); running the test command after approval; writing a `plan.md`
before code on a high-risk request (an app plus a new shared contract under `packages/`, requirements final,
plan-first hook opened by the case's `env` and not mentioned in the prompt, which agents read as "skip the
plan"; so only the high-risk rule asks for the plan); no user absolute paths in written files.

## Runner (`scripts/harness/run-evals.py`)

Each run gets its own copy: HEAD's tracked files minus `.claude/evals/**`, `docs/changes/2*` and
`docs/references/`, with `scripts/test/run-evals.test.py` replaced by a stub that prints a SKIP line and
exits 0 (`test:harness` names it; the fixtures stay out), initialized with
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

The runner distinguishes successful content from native failure channels. Quoted error names in
a successful response or tool result are task content, not authentication failure. A native
terminal error, missing terminal success or nonzero CLI result cannot pass by merely attempting
a matching tool call. Git routing variables are removed from copy preparation, execution and
case-provided environment overlays; integrity tests verify source HEAD, index, config and bytes.
These fake-CLI tests establish runner behavior, not an OS sandbox or real authentication.

## Maintenance

### Reusable real-work trials

`scripts/harness/work-evals.py` prepares and inspects independent workspaces; it does not
launch a model, change host settings, grant approval or start a server. The existing
`run-evals.py` remains the Claude-only instruction smoke runner. The work catalog in
[work/cases.json](work/cases.json) supplies ordinary requests for field repair, batch
completion/recovery and behavior-preserving refactoring. These are synthetic regression
tasks derived from actual failures, not evidence about every product using the template.

Commit the candidate and task assets first. Choose a fresh output directory outside the
source repository; keep the source unchanged through inspection and grading, including
operator edits. Preparation exports the selected commit, never dirty/untracked source files.
It records the original HEAD, index, config and Git-listed working files, initializes an
independent repository with normal Husky hooks, and overlays only the selected app fixture.
The grader, rubric, labels and receipts remain outside the worker. Historical change folders
and `.claude/evals/**` are excluded; the three harness tests that disclose evaluation fixtures
are replaced with explicit SKIP stubs so the worker's harness command remains runnable.
These exclusions are recorded and do not count as executing the skipped regressions.

```sh
python3 scripts/harness/work-evals.py prepare --case field-repair --ref HEAD --output <outside-repo>/trial-a
# Open the returned worker directory in the normal Claude or Codex host.
# Give it prompt.txt, actual authorization and relevant project context, not the private rubric.
# Retain its real raw trace and exit code outside the worker.
python3 scripts/harness/work-evals.py inspect --trial <outside-repo>/trial-a --host codex --trace <raw-trace.jsonl> --exit-code 0
python3 scripts/harness/work-evals.py grade --trial <outside-repo>/trial-a
```

For a control commit that predates these task assets, add `--task-ref <fixed-task-commit>`.
`--ref` selects the harness instructions; `--task-ref` selects the fixture, catalog, rubric and
external grader, defaulting to `--ref`. Use the same task commit for control and candidate.
Both revisions and asset hashes are retained. The grader is verified against that task commit,
never the mutable working copy or the worker's preferred expected answer.

Use a separate prepared directory for each host, variant or retry. Preserve failed runs;
receipts append rather than replace an earlier verdict. `inspect` checks full file content,
including committed worker edits, against allowed app/change-record paths. It records native
completion separately from correctness; absent/malformed traces or a missing exit code are
unverified, and native errors/nonzero exits fail. Trace attribution and actual delegation
still need independent inspection; a supplied trace filename is not proof it belongs to the worker.
Inventory excludes only untracked, Git-ignored dependency trees (`node_modules`) and Python
bytecode (`.pyc`/`.pyo`). Tracked and unignored files, policy files and active Git hook shims
remain checked. Freeze the helper as well as the source during a run. After changing its
inventory rules, use a new `prepare`; never rewrite existing receipts to fit the new rules.

`grade` verifies the frozen external grader against its committed source and executes its
behavioral checks on the final worker. Changed source, harness policy or oracle prevents grading.
The fixed grader executes candidate code under the operator's normal permissions; private
directories and post-run checks are not an OS sandbox. It stops its own process group after
completion or timeout; deliberately detached descendants are outside that cleanup boundary.
The tool never loads an arbitrary grader command from a worker-controlled file.

Exit codes are 0 for preparation, 1 for a failed integrity/native/behavioral check, 2 for an
invalid setup or receipt, and 3 for `NEEDS_REVIEW`. Even a behavioral PASS leaves browser and
independent-review results unverified. For web cases, run the critical journeys through actual
controls in all three viewports, freshly read the SQLite-backed results, and exercise lost
response/retry and partial-entry recovery under [web acceptance](../../docs/standards/qc/web-acceptance.md).
Keep the task-owned database and runtime evidence outside the worker, record the build/data
boundary, and stop the server after verification. A module test or HTTP request cannot substitute
for the UI actions. A reviewer inspects the private rubric, real tool events and final artifacts;
the helper never certifies that review or browser execution from a JSON assertion.

For Claude, use the native interactive approval path when postapproval work is required and
retain that session for continuation. A print-only denial or preapproval stop is separate evidence;
do not create trust/approval markers or set the human-only approval variable. For Codex, retain
parent-session persistence when testing native delegation. Neither host needs a synthetic
model identity, replacement authentication or reduced tool set for this protocol.

### End-to-end stage handoffs

For changes to intent/spec/plan/implementation, use
`docs/standards/execution/stage-handoffs.md` and observe the connected process, not four isolated
documents. Freeze the final instruction hashes, task, authorized settings and external rubric
before native calls. Use one realistic request with meaningful finish/interruption/recovery
criteria; keep grader, expected solution and model/variant labels outside each worker's context.

1. Intent captures the actual decisions and unresolved material choices. Give a later worker
   the resulting record and relevant repository context, not a reconstruction of hidden dialogue.
2. Specification preserves those decisions as observable acceptance criteria. An independent
   reader checks for lost constraints and missing finish/error cases before planning.
3. Planning maps each criterion to a feasible change and proof. Check backend/account/browser,
   delegation and cleanup capabilities before promising those checks.
4. After actual approval, implementation and fresh review consume the same criteria and proof
   context. Independently execute the final artifact. Web work follows browser acceptance.
5. Challenge a missing outcome, a missing behavior case, infeasible proof setup and an observed
   implementation failure. Check that each returns to its owning stage without reopening
   settled decisions. Preserve failed/denied attempts and inspect actual returned tool results.

Judge decision continuity, independently understandable behavior, feasible proof, correct
handoffs/returns and reporting accuracy separately. Use pass/fail/unverified per criterion.
Grading an attempted tool call or a named skill is not evidence of successful execution.
Record preapproval stops separately when native human approval cannot be supplied; do not set
the human-only environment variable or fabricate trust/markers to complete this lane.

This is a native verification protocol, not another automatic runner or enforced gate. The
bundled runner remains Claude-only. Codex and cross-stage execution need their normal host
tools and separately retained evidence. A few tasks are smoke coverage, not a productivity estimate.
An improvement comparison additionally needs the same task/settings/permissions on control and
candidate, sanitized outputs and a judge blind to model/variant. Inspect all artifacts yourself
against that verdict. Natural project test/eval files can disclose context; report that limit
rather than calling an ordinary source-copy trial perfectly blinded.
The design references [pstack's Eval playbook](https://github.com/cursor/plugins/blob/main/pstack/skills/poteto-mode/playbooks/eval.md).

### Task-route and orchestration checks

For changes to the implementation procedure, supplement discovery cases with ordinary native
work under the project's own policy. Use a private source copy, an organic bug/feature/refactor
request and an external rubric/holdout. Keep expected answers, model/variant labels and grading
files outside the worker's workspace. Preserve normal auth/settings/hooks/tools and record any
task-scoped command grants. A runner that removes Agent/browser capabilities cannot establish
orchestration or interactive acceptance.
Preserve any parent-session context needed by native delegation. For example, the observed Codex
CLI's `--ephemeral` lane could not fork its missing parent rollout, while ordinary persistence
returned a child review. Check that capability before an orchestration run and distinguish a
failed spawn from a completed review; do not change the user's global configuration to get green.

Inspect actual tool events: procedure/reference reads, pre-edit repro/criteria/baseline, edits,
verification commands and real delegation. Independently execute the retained artifact and
check scope/policy integrity. Final wording, a terminal success or a passing build is not enough.
Preserve negative/permission-limited runs; after a repair, use fresh copies and record all changed
instructions and protocol settings rather than reporting only green retries.

An unapproved native session may correctly stop at the plan-first boundary. Record that as
preapproval behavior, separately from postapproval implementation. Do not create a trust or
approval marker for a normal native session. Use the repository's existing approved workflow
when available, and report unavailable write/browser execution explicitly. See
`docs/standards/execution/task-routes.md` and `docs/standards/qc/web-acceptance.md` for acceptance.

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
