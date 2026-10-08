# Pre-implementation agreement and PR value review

Use this procedure when drafting spec/plan, starting implementation, changing accepted scope, or
preparing the PR. `artifact_chain.deliverables.required_when` in `.agents/harness.yaml` still
selects the required HTML files; keep the four perspectives and existing applicability conditions.
Small changes may skip intent, plan and inapplicable HTML; enabled runtime gates still require
a spec, exact scope, approval and verification. Agents cannot exempt themselves by calling work trivial.

## 1. Make the proposed outcome reviewable

During spec, draft the applicable files in `<change-folder>/deliverables/`. During plan, refine
the same drafts and complete the architecture view before asking for implementation approval.
Use the planned affected paths and user scenarios to determine applicability before a diff exists;
check the actual diff again at delivery. Drafts may be written before agreement; label them draft.

| File | Decision it supports before implementation | Evidence added after implementation |
|---|---|---|
| `설명서(eli7).html` | Why this matters, who benefits, what changes, unresolved decisions | Actual change, deviations, remaining value uncertainty |
| `mockup.html` | Proposed screens, states and interactions | Actual screenshots or observed behavior, separately labelled |
| `flow.html` | User steps, failure paths and recovery | Verified paths and known gaps |
| `architecture.html` | Planned boundaries, dependencies and affected contracts | Implemented boundaries and differences from the plan |

The explainer is the entrypoint, with relative links to the other required standalone HTML files.
Use a shared value/story identifier (for example V1/US1) across the views, spec and plan. Show only
what helps the decision. Reuse a view whose meaning is unchanged and label the unchanged scope.
Use inline styles/diagrams and embedded images; no external hosting or remote assets are needed.
A proposed mockup is not execution evidence. If the app cannot run, label actual verification as
unavailable and record the missing environment instead of implying that the mockup was tested.

## 2. Agree, then preserve the baseline

Present the applicable HTML drafts with the spec and plan. Ask about unresolved decisions;
existing explicit approval of the same presented revision remains valid. Approval of intent alone
is not approval of an unseen implementation draft. Product implementation starts after agreement.

For durable architecture, contract or harness decisions, read `docs/decisions/README.md`.
Put the proposed decision in spec/plan and include its future ADR path in scope; write the tracked
ADR after agreement. Reference an existing ADR when the decision is unchanged.

Create `scope.json` from the template: exact file paths and verification commands as argv arrays.
Use the `__PREFIX__-agreement` skill. Run `python3 scripts/agreement-gate.py prepare <change-id>
--revision 001`, then present the drafts, scope, checks and generated approval command. Claude uses
`/__PREFIX__-agreement approve <challenge>`; Codex uses `$__PREFIX__-agreement approve <challenge>`.
The user's exact command is handled by UserPromptSubmit. A Skill call or document saying
“approved” grants nothing. Existing approval of the same prepared revision is reused.

The hook checks the presented hashes, preserves `agreements/001/`, and records the grant in this
worktree's Git directory. Put `Agreement-Ref: agreements/001` in the plan before preparation and
in the PR afterward. Approved intent/spec/plan/scope stay frozen; record ticket/DoD results in
`progress.md`. Result HTML may evolve separately. For amendments, prepare the next revision to
revoke the old grant, edit the drafts, prepare again, and present the new challenge. A pending
draft may end a turn to await the user even with existing edits; implementation and commit stay
blocked. Prior revisions remain unchanged.

For a nontrivial change with no required HTML, preserve the approved plan/spec without HTML.
An implementation already in progress has no retroactive pre-implementation agreement: report
that gap, present the current state, and agree the remaining work explicitly.

## 3. Implement and verify the agreement

The implement adapter reads the referenced snapshot and implements only the approved file scope.
Use Write/Edit or Codex apply_patch for edits. For deletion/rename use the scoped helper commands
`python3 scripts/agreement-gate.py remove <path>` or `move <source> <target>`. Arbitrary mutation
shell commands and unsupported tools are refused. A simple `git switch -c <branch>` whose name
fully matches `agreement_gate.branch_pattern` (default `feature/<slug>(/<part>)*`) is allowed
after approval. Prepare isolated checkouts outside this flow; use one change per worktree.
Run `python3 scripts/agreement-gate.py verify` to execute the declared checks and record their
exit codes against current source hashes. Editing source invalidates that evidence. Run fresh
read-only code review and repair findings, then verify again if source changed. Code review assesses correctness against the
agreement. User value review remains a separate human decision.

After verification, update working `deliverables/` with actual behavior, evidence and deviations.
Keep the approved versions in `agreements/<revision>/deliverables/` unchanged. If actual changes
require a perspective not covered by the approved draft, return to agreement for the remaining
work; do not manufacture an earlier approval. A changed file alone does not prove a value claim.

## 4. Present the PR as a value review

Fill `_templates/pr.md`. Compare each agreed expectation with the observed result and its evidence
in `## 세 상자`. In `## 가치 확인`, record status and uncertainty for each material value claim:

- `확인됨`: the stated value has supporting observations; name the evidence and its limits.
- `부분 확인`: some agreed outcomes are observed, others remain unverified.
- `미검증`: implementation works, but the value needs usage/release observation.
- `미달`: observed results fall short of the agreed criterion; record the gap and next action.

A test showing a flow shrank from five steps to two proves that change; it does not prove reduced
abandonment. For unverified value, identify the metric/observation, agreed owner (or `담당 미정`)
and measurement timing/trigger. `미검증` can be an honest implementation handoff, unless the
agreed acceptance criteria require that measurement before completion. The agent never grants
the human's value approval or silently moves failed stories out of scope.

Keep the PR short: link the baseline and actual-result views, retain the existing three-row and
three-file limits, and use one nonempty evidence block. Attach both versions together with their
relative directory structure (a ZIP is suitable) so links work after extraction; attach the hash
manifest as well. This is still local-only history, not committed source. PR attachment and value
judgment are human checks. Delivery is local `pr.md` and the baseline/result directories; the developer
packages the attachment bundle and publishes the PR. Automated push, PR creation and worktree management are outside this adapter.

## Runtime boundary

Claude and Codex adapters wire UserPromptSubmit, PreToolUse and Stop. Stop and pre-commit locate
the active PR from state, even if never touched, and reject missing/stale verification, missing PR,
baseline corruption and scope drift. Pre-commit also rejects staging a different version from the
verified working copy. Stop does not revoke the approved scope: other hooks can still require
repairs. In-scope repairs need fresh verification; pause or a new prepared revision revokes
the current grant. User `pause` permits an incomplete
handoff; `resume` rechecks the baseline. Neither means completion or value approval.

These controls require trusted, enabled host hooks. They are workflow enforcement, not an OS
sandbox: same-user terminal access, disabling hooks, trusted verification scripts, and host tools
that bypass hooks are outside the boundary. Verification commands run with host privileges;
approve their actual content/dependencies, not just their names. A manual human-terminal approval
fallback exists for hosts without UserPromptSubmit and must be described as weaker provenance.
Do not claim that a matching approval command proves the human read or understood the HTML.
Native host behavior and trust settings require a deployment smoke test; payload tests alone do
not establish coverage for every host version. See the official host hook documentation.

## Gate configuration and switching off

`agreement_gate` in `.agents/harness.yaml` holds the lists the gate reads; approval, scope and
verification decisions stay in `scripts/agreement-gate.py`. `check:harness` validates them.
A missing list opens nothing; a malformed one blocks the call.

Every shell command must be one direct command: shell metacharacters (`; & | > < $`, backquote,
backslash, newline) and unquoted `* ? [ ] { } ( )` are refused, because globs, brace expansion and
zsh glob qualifiers add arguments (or run code) the gate never sees. Quote such arguments.
Environment assignments before the command (`HUSKY=0 git commit`) and git options before the
subcommand (`-C`, `-c`, `--git-dir`, `--work-tree`, `--exec-path`, `--config-env`, `-p`,
`--no-pager`, ...) are refused for every command, listed or not.

- `allowed_subagents` (default `Explore`, `Plan`, `verifier`, `general-purpose`): subagent types
  the Agent/Task tool may start. A call without `subagent_type` counts as `general-purpose`, the
  host default that `/review-since` starts. A subagent's own tool calls pass the same PreToolUse
  hook (the payload carries `agent_id`/`agent_type`), so a listed type gains no edit path.
- `read_only_commands`: commands that run before and after approval, no wildcards. Each entry is
  an argv prefix (`["git", "log"]`: any later argument opens) or `{"exact": [...]}` (only that
  whole argv). An entry that names a script or a path must be exact (`check:harness` and the gate
  both refuse it as a prefix): a prefix would hand the script any argument, such as
  `--repo-root <another checkout>`. So must an entry that starts with a script runner (`pnpm`,
  `npm`, `npx`, `yarn`, `bun`, `node`, `python`, `python3`, `bash`, `sh`, `uv`, `poetry`) and names
  more than the runner (`pnpm check:harness`, `npm run x`, `python3 -m pkg`). The default list opens
  `python3 scripts/check-agent-harness.py --format text` exactly, and `git merge-base` for
  `__PREFIX__-ui-review`. These stay refused whatever the list says: unsafe flags (`rg --pre`/`--hostname-bin`; git
  `--output`, `--ext-diff`, `--textconv`, `--no-index`, `--open-files-in-pager`, and `-O` in any
  short cluster) and gate-owned commands in any spelling (`git add|commit|switch|push|checkout`;
  an argument naming `agreement-gate` for any program except git and the plain readers `cat`,
  `head`, `tail`, `wc`, `rg`, `grep`, `ls`, which may read the gate's files). A listed command never records
  verification; only `agreement-gate.py verify` does.
- `reviewed_whole_programs`: a one-token `read_only_commands` entry (`["rg"]`) opens every argument
  of that program, so `check:harness` refuses it unless the program is named here too. Add a name
  only after checking that no argument of the program writes files, runs code, or reaches a
  gate-owned command: a bare `git` reaches `git ci -n` through an alias, a bare `python3` runs any
  code. Prefer listing the subcommand (`["git", "log"]`).
- `agent_browser`: screen checks with `agent-browser`, before and after approval. Write the command
  words first and options after them (`agent-browser snapshot -i --json`). `commands` maps the
  allowed command words (one to three, e.g. `set viewport`) to their `flags` and `args`;
  `global_flags` apply to every command. A flag's value shape is `""` (switch), `"path"`, or a regex
  the value must fully match. `args` is `null` for free text (selectors, URLs, typed text) or a
  list of slots `path`, `path?` (optional) and `text`. A `path` value must be absolute and resolve,
  after `..` and symlinks, inside `artifact_dir` (`$TMPDIR/<name>`: mode 0700, owned by you, never a
  symlink, never inside or around the checkout; the gate creates it 0700 and refuses an existing one
  with any group or other permission). Relative and `~` paths are refused: the agent-browser daemon
  resolves a relative path from its own working directory, and quoting decides whether the shell
  expands `~`. The refusal message prints the resolved directory to use. `batch`, `chat`,
  `connect`, `upload` and `--cdp`, `--auto-connect`, `-p`/`--provider`, `--executable-path`,
  `--args`, `--extension`, `--config`, `--init-script` stay refused whatever the lists say, and every
  call is refused while `./agent-browser.json` exists (it can set all of those). `read_only_commands`
  never opens `agent-browser`. agent-browser takes its global options from any position, so an
  option value or text argument that starts with `-` is refused (negative numbers such as
  `mouse wheel -50 0` excepted); otherwise `scroll down -s --profile <dir>` would hide a profile
  directory inside a selector slot. Not opened by design: element screenshots (a lone `screenshot`
  argument may be read as a path). A download a page starts by itself lands in agent-browser's
  default location, which the gate does not see. After approval, Stop and pre-commit refuse
  changed or new non-ignored files in the working tree outside scope (`git diff` plus untracked
  files `git ls-files --others --exclude-standard` lists); they do not see writes under `.git/`,
  ignored paths or outside the checkout, and Stop checks no files while a draft is pending.
- `branch_pattern`: full-match regex for `git switch -c <branch>` after approval.

**Second fence.** A hook that times out or fails to start does not block the tool call.
`.claude/settings.json` `permissions.deny` and `.codex/rules/harness.rules`
(`prefix_rule(decision="forbidden")`) repeat part of the gate without the hook: `git push`;
`git commit` with `--no-verify` (or an abbreviation) or `-n`, `-nm`, `-an...` clusters; git `-c`,
`-C`, `--git-dir`, `--work-tree`, `--exec-path`, `--config-env` before the subcommand. Claude rules
glob over the whole command text, quotes included, so they cannot tell a message from an option:
they match `-n`/`-an` clusters only right after `git commit` or as the last word (a message such as
`-m "fix: rg -n output"` passes), `--no-v...` anywhere (a message containing ` --no-v` is refused
there; reword it), and `VAR=value` or `env` before `git commit`/`git push`. So `git commit -m x -n
-q` passes Claude's fence. Codex rules compare whole tokens from the start, so `git commit -m x
--no-verify`, `git commit -qn`, `git --git-dir=.git commit` and environment prefixes pass Codex's
fence. The gate is the precise layer: it reads every `git commit` option as git does (abbreviated or
unknown options are refused) and refuses all of them.

**`enabled: false` is not off.** The gate treats a disabled or missing `agreement_gate` as broken
wiring and fails closed: every PreToolUse call is refused (exit 2), UserPromptSubmit refuses every
prompt (on Claude the prompt never reaches the model), Stop exits 2 so the host keeps the session
going, and `check-staged` refuses every commit. To switch the gate off, remove wiring and
declaration in one change:

1. `.claude/settings.json` and `.codex/hooks.json`: the `agreement-gate.py` entries under
   `UserPromptSubmit`, `PreToolUse` and `Stop`.
2. `.husky/pre-commit`: the `agreement-gate.py check-staged` line.
3. `.agents/harness.yaml`: the `agreement_runtime` and `agreement_precommit` entries in
   `shared_hook_intents` (left alone, `check:harness` reports them unwired).
4. `package.json` `test:harness`: drop `scripts/test/agreement-gate.test.py`, which asserts the wiring.

Update `AGENTS.md` and the agreement skill in the same change; they describe the gate. The second
fence is independent: keep or remove it deliberately.
