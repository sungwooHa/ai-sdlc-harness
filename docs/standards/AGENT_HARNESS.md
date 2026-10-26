# Agent Development Harness

How the harness is built and how to change it. Read it before you touch `AGENTS.md`, `CLAUDE.md`,
`.agents/`, `.claude/`, `.codex/`, `.husky/` or `scripts/`. Principles are in
`HARNESS_PRINCIPLES.md`, the playbook mapping in `PLAYBOOK_MAP.md`, the decisions and their
reasons in `docs/decisions/0000-harness-decisions.md`.

## Requested outcomes

Choose the requested result before starting the implementation flow. The routes below are
guidance for selecting work and recognizing its finish, not a new permission or execution gate.
Use the request and existing decisions; do not select a writing route merely because a read-only
question mentions a bug, feature or plan.

| Requested result | Work and finish |
|---|---|
| Investigation or explanation | Answer from the relevant evidence, separating observed facts, inference and missing evidence. Finish with the answer; do not edit the repository. |
| Design or comparison | Compare relevant alternatives and tradeoffs, recommend a direction and identify unresolved outcome decisions. Do not implement unless the user requested implementation. |
| Review | Fix the review scope and baseline, inspect the relevant change and report concrete findings and unverified areas. Do not apply fixes unless requested. |
| Bug fix | Reproduce the reported symptom on an appropriate surface, confirm the cause, make the smallest justified fix and recheck the original symptom and affected regressions. Report an unavailable repro as unverified. |
| Feature implementation | Derive observable acceptance criteria, implement the requested behavior and verify its completion and applicable failure or recovery paths. Account for each criterion. |
| Refactoring | Identify the external behavior and contracts to preserve, change the structure and verify that the affected behavior is preserved. |

Combine routes when the requested result needs them. "Compare and propose" ends with a proposal;
"compare and then implement" includes implementation, subject to the existing writing workflow.
Do not turn every route transition into an interview or a new approval request. Ask for missing
outcome decisions that cannot be established from evidence; reuse decisions already given.

Writing routes still follow the existing plan-first, approval, artifact, branch and review rules.
A requested document edit is writing work too. Selecting a route neither grants permission nor
satisfies, resets or replaces the plan-first approval marker. Use the existing project skills
only for the work they serve; no new skill chain or document is required by this routing guide.

## Web verification branch

User-visible web changes, including helper/API/state effects outside UI file globs, enter
[web acceptance](qc/web-acceptance.md) after implementation and code checks. The implementation
skill assigns an agent with browser tools or the main agent executes the step. It operates the
actual journey through completion, fresh persistence read and applicable recovery in three
viewports. Failures return to implementation and affected paths rerun on the final candidate.
Missing required execution stays unverified in `pr.md` and delivery. Native-only and internal-only
work keep their applicable checks. This is a shared Claude/Codex execution guide, not a new hook
or proof that a browser ran; preserve all existing approval, data and runtime boundaries.

## Changing the harness

1. Name the `PLAYBOOK_MAP.md` row the change moves (row ID, status before → after). An element with
   no matching play gets a `Beyond` row with its reason; a deliberate departure is a `Deviation` row
   with its reason.
2. Apply the binary criterion: *would a violation be irreversible, or invisible in human review?*
   Yes → system: a hook or git hook that fully enforces it. No → guide: a line in `AGENTS.md`, a
   skill or a template, checked by a human at PR through `REVIEW.md`. Nothing is half-enforced; a
   check that only warns, or that a common path walks around, is a guide — write it as one.
3. Edit `.agents/harness.json` first, then the wiring its `hook_intents` entry names
   (`.claude/settings.json`, `.husky/*`).
4. Update `docs/decisions/0000-harness-decisions.md` in place; git keeps its history.
5. Run `__PACKAGE_MANAGER__ test:harness` (`check:harness` + the harness's own tests) and paste the
   result. For instruction-text changes also see `.claude/evals/README.md`.

## Layout

| Path | Role |
|---|---|
| `AGENTS.md`, `CLAUDE.md` | Always-on contract (≤ `always_on_max_lines`); `CLAUDE.md` imports `@AGENTS.md` and adds only Claude-specific lines |
| `apps/<app>/AGENTS.md` | Per-app rules (`CLAUDE.md` in each app is a symlink to it) |
| `.agents/harness.json` | Config: protected paths, secret patterns, formatters, plan-first, skills, hook intents |
| `.agents/skills/`, `.claude/skills/` | Skill root and its symlink mirror |
| `.claude/agents/` | Subagents (`verifier`) |
| `.claude/settings.json`, `.husky/*` | Hook wiring and `permissions` |
| `.codex/config.toml`, `.codex/rules/harness.rules` | Codex: no hooks; rules forbid push, hook-skipping commits and `git -c`/`-C` |
| `.claude/evals/`, `scripts/harness/run-evals.py` | Behavioural evals (model quota; not in `test:harness`) |
| `docs/changes/` | One committed folder per change; see its README |
| `docs/decisions/` | ADRs; `0000` is the harness record |
| `docs/examples/` | Inactive CI and CODEOWNERS examples |
| `REVIEW.md` | Review passes and severities |

## Hooks

The only system-enforced rules. `hook_intents` in `.agents/harness.json` declares each one;
`check:harness` fails when a declared script is not wired on its event, or the reverse.

| Intent | Event | Matcher | Script | Effect |
|---|---|---|---|---|
| `plan_first` | PreToolUse, PostToolUse | `Edit\|Write\|MultiEdit\|NotebookEdit`, `ExitPlanMode\|EnterPlanMode` | `scripts/plan-first.py` | Refuses an edit inside the repo outside `plan_first.exempt_roots` without a marker |
| `plan_first` | UserPromptSubmit | — | `scripts/plan-first.py` | Deletes the marker when a prompt is sent while the session is in plan mode |
| `protected_paths` | PreToolUse | `Edit\|Write\|MultiEdit\|Bash` | `scripts/protected-paths-guard.py` | Refuses Edit/Write/MultiEdit to `protected_paths` by target path; the Bash check is best-effort |
| `format_on_edit` | PostToolUse | `Edit\|Write\|MultiEdit` | `scripts/format-on-edit.py` | Runs the argv of the first matching `format_on_edit` glob; empty config is a no-op |
| `secret_scan` | pre-commit | — | `scripts/secret-scan.py` | Refuses a commit whose staged added lines match `secrets.patterns` |
| `pre_push_test` | pre-push | — | `.husky/pre-push` | Runs the project `test`; refuses the push on failure |
| `husky_setup` | SessionStart | — | `scripts/harness/ensure-husky.sh` | Not a gate: writes missing `.husky/_` shims so git hooks run in fresh clones and worktrees |

**Plan-first marker.** PostToolUse `ExitPlanMode` (fires only on approval) writes
`<git-common-dir>/harness/plan-approved/<session_id>`; PostToolUse `EnterPlanMode` deletes it, and
so does UserPromptSubmit while the session is in plan mode (entering with Shift+Tab calls no tool).
The marker means "this session had a plan approved since it last entered plan mode" (an
EnterPlanMode call, or a prompt sent while in plan mode), not "this change's plan was approved".
Subagents send the parent's `session_id`, so an approved session's implementers pass. "Inside the
repo" is decided from the target's own git toplevel: every worktree of this repository (same git
common dir, e.g. `.claude/worktrees/`) is gated like the main tree with its own `docs/changes/`
exempt, and case-variant spellings of a repo path are gated too. Paths in no repository or another
one (plan files, scratchpad, memory) are never refused. Headless runs have no plan mode: a human
sets `HARNESS_PLAN_APPROVED=1`. An unreadable payload is refused.

**Protected paths.** Edit/Write/MultiEdit are checked by target path; Bash by a path next to a write
marker (`>`, `sed`, `tee`, `mv`, ...), a heuristic. To protect generated files, add an entry such as:

```json
{
  "id": "generated-sources",
  "globs": ["packages/**/*.generated.ts"],
  "reason": "Generated from a source of truth; hand edits are overwritten.",
  "instead": "Edit the source and run the generator."
}
```

**Project gates.** Add one line to `.husky/pre-commit` and one `hook_intents` entry together.

## Known gaps

Not enforced; guides and PR review (`REVIEW.md`) cover them.

- **Bash writes.** `sed -i`, redirection or `python -c` change files without plan-first, and
  protected paths sees Bash only through its best-effort heuristic. Agents edit files with
  Edit/Write.
- **MCP edit tools.** Serena and similar MCP editors bypass the `Edit|Write|MultiEdit|NotebookEdit`
  matchers, so neither plan-first, protected paths nor the formatter sees them.
- **Nested repositories.** plan-first gates only paths whose git common dir is this repository's
  (the checkout and its worktrees); an independent repository or submodule inside it is not gated.
- **Hook skipping.** `--no-verify`/`-n` and `git -c core.hooksPath=` skip git hooks.
  `.claude/settings.json` `permissions.deny` and `.codex/rules/harness.rules` match command text,
  so they stop only the hook-skipping spellings they list; another spelling passes, and a human
  terminal skips anything. Secret scan and pre-push run locally only — no CI runs until a
  `docs/examples/` file is activated.
- **Approval variable.** A child `HARNESS_PLAN_APPROVED=1 claude -p …` skips plan-first;
  `permissions.deny` refuses a command that assigns the variable, by its text only (a script file
  that sets it passes).
- **Codex.** No plan-first, protected paths or formatter: Codex follows `AGENTS.md`, skills and git
  hooks.

## Skills

- One root, `.agents/skills/`; `.claude/skills/<name>` is a symlink to it per skill, never a copy.
- A skill is a directory with `SKILL.md` (frontmatter `name`, `description`, optionally
  `disable-model-invocation`, `argument-hint`) plus optional `references/`, `assets/`, `scripts/`.
  Write it in English, imperative, addressed to the agent; `writing-for-agents` is the style
  reference. `description` is the routing signal: when to use it, with the phrases users type.
- A skill reads a repo fact at run time from the file that owns it; it does not restate it.

**Vendored skills** are listed in `skills.vendored` with source, license and `update_command`. Do
not hand-edit them; refresh with the entry's command. A `{name, as}` entry renames on import.

**Adapters** (`skills.adapters.map`) give vendored skills this repo's paths and language. The chain
adapters (`__PREFIX__-intent`, `-spec`, `-tickets`, `-implement`) are model-invocable. Every map
target carries `disable-model-invocation: true`, stamped by `vendor-skills.py` on import and checked
by `check:harness`, so an adapter reads the target's `SKILL.md` by path instead of calling it.

**Personal skills.** Keep a skill that is yours out of shared files. Prefer user scope (Claude Code
reads `~/.claude/skills/`, Codex `~/.agents/skills/`; keep the real directory in one and symlink
the other); never reuse a team skill's name. A skill that only makes sense in this repo is named
`local-<name>` (`skills.local_prefix`): real directory `.claude/skills/local-<name>/`, relative
symlink `.agents/skills/local-<name>` → `../../.claude/skills/local-<name>`, both hidden per clone
in `.git/info/exclude` (never `.gitignore`), recreated in each worktree:

```
/.claude/skills/local-*
/.agents/skills/local-*
```

## CI examples

`docs/examples/` holds inactive files: `claude-review.yml` (AI PR review with `REVIEW.md`),
`agent-evals.yml` (evals on harness-config changes) and `CODEOWNERS` (second approver for high-risk
paths). Activating one is a harness change: move its `PLAYBOOK_MAP.md` row.
