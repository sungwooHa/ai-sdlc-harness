# Agent Development Harness

Contract for the harness that agents (Claude Code, Codex) run inside. The machine-readable source
is `.agents/harness.yaml` (version 2); this document explains it and is the only place the harness
may be changed from.

## Purpose

The four governing principles — rules in the repo / history on the PR, enforce with the system,
minimum cognitive load for humans, facts are the agent's and decisions the user's — live in
`HARNESS_PRINCIPLES.md`; this document is their implementation.

The harness keeps agent behaviour consistent across hosts by splitting guidance into layers:

| Layer | What it is | Where |
|---|---|---|
| Always-on | Repo-wide operating contract, loaded in every session (≤ 120 lines) | `AGENTS.md`, `CLAUDE.md` |
| Per-app | Rules loaded when work happens under that app (≤ 80 lines each) | `apps/<app>/AGENTS.md` |
| On-demand | Skills invoked by name for a specific job | `.agents/skills/**` |
| Subagents | Claude-only reviewer personas (`verifier`) | `.claude/agents/*.md` |
| Deterministic | Hooks and gates that run without the model deciding to | `.claude/settings.json`, `.codex/hooks.json`, `.husky/pre-commit` |
| Artifact chain | Local working record of what a change intends, specifies, and plans (never committed; the PR carries it) | `docs/changes/**` |
| Evals | Behavioural regression cases: does an agent follow the rules above? | `.claude/evals/**`, `scripts/harness/run-evals.py` |

Prose persuades; hooks enforce. Anything that must never happen belongs in the deterministic layer,
not in a document.

## Layout

| Path | Role |
|---|---|
| `AGENTS.md` | Shared policy entrypoint for every host |
| `CLAUDE.md` | Claude entrypoint; must import `@AGENTS.md` and add only Claude-specific lines |
| `apps/<app>/AGENTS.md` | Per-app rules (`CLAUDE.md` in each app is a symlink to it) |
| `.agents/skills/` | Single skill root |
| `.claude/skills` | Symlink mirror of the skill root (one symlink per skill) |
| `.agents/harness.yaml` | Machine-readable harness contract |
| `.claude/settings.json`, `.codex/hooks.json` | Host hook adapters |
| `.codex/config.toml`, `.codex/rules/commit-convention.mdc` | Codex host files |
| `.husky/pre-commit` | Commit-time gates |
| `docs/changes/<YYMMDD_NN>-<slug>/` | Artifact chain per change — local-only working folder, gitignored, never committed |
| `docs/changes/_templates/` | `intent.md`, `spec.md`, `plan.md`, `pr.md` templates (the only tracked files under `docs/changes/` besides its README) |
| `docs/decisions/` | Tracked ADRs: durable decisions, alternatives and consequences; see its README |
| `docs/agents/issue-tracker.md` | Change-folder convention consumed by the intent/spec/tickets/implement adapters and, through them, review-since |

## Artifact chain

`intent.md` → `spec.md` + HTML drafts → `plan.md` + refined drafts → human agreement →
preserved baseline → code + correctness review → `pr.md` value review. Templates live in
`docs/changes/_templates/`; the filled documents live under `docs/changes/<YYMMDD_NN>-<slug>/`, where
`<YYMMDD_NN>` is the start date plus that day's sequence from `00` (`/__PREFIX__-intent` assigns it).
The stage table (which skill runs each stage) is in `AGENTS.md`; do not duplicate it here.

**Rules in the repo, history on the PR** (`artifact_chain.history_policy`). The harness tracks only
systemic constraints and rules: `AGENTS.md`, `harness.yaml`, hooks, skills, standards, promoted
knowledge, ADRs for durable decisions, and the templates. Per-change execution history — intent, spec, plan, deliverables,
`pr.md`, and scratch — is never committed. The change folder is gitignored (`docs/changes/*` minus
README and `_templates/`), and `documentation_layout.local_only_roots` makes the fast guard refuse
any such path that is staged or appears in a PR diff (so `git add -f` and merges from older branches
are caught at pre-commit and in CI). What leaves the machine: the PR description (from
`_templates/pr.md`), PR attachments for the deliverables, the `Plan-Ref: <YYMMDD_NN>-<slug>` commit
trailer, and knowledge promoted through the one door below. A multi-session or multi-machine handoff
mid-change goes through the PR, not through a commit.

- Skip a stage when it adds nothing. Small changes may skip intent/plan and inapplicable HTML; spec, scope and hook-owned approval remain required.
- Never skip review for a diff touching more than one app or any shared contract.
- No external tracker: the local folder `docs/changes/<YYMMDD_NN>-<slug>/` is the working source
  and the PR is the record.
  `docs/agents/issue-tracker.md` says so and tells adapters to skip the publish/label steps of the
  vendored skills.
- Agreement (`artifact_chain.review_gate` / `agreement`): human review happens before product
  implementation. Spec drafts the applicable HTML, plan refines it, and the user approves the
  presented revision. The snapshot helper preserves it under `agreements/<revision>/` with
  an approval reference and file hashes. Implementation and PR reference that baseline.
- Plan gate (`artifact_chain.plan_gate`): multi-app/shared-contract PRs carry a `Plan-Ref` commit
  trailer. The existing script checks its presence (warn; `PLAN_GATE=enforce`), not the contents
  of the approved plan. The PR refers to the attached agreement for the full plan.
- UI review waiver: the approved plan can state `시각 변경 없음` for a change without visual
  effects. This waives the code/UI audit as declared; HTML applicability still uses `required_when`.
- Deliverables retain the existing conditions: explainer for multi-app/shared-contract or UI;
  mockup, flow and architecture for UI. They are decision drafts before implementation and
  result evidence afterward. The approved copies stay unchanged; working `deliverables/` is
  updated with actual results. The explainer links the required perspectives as one entrypoint.
- PR description: one value title, `Plan-Ref`, applicable `Agreement-Ref`, picture/comparison,
  at most three expectation/result/evidence rows, explicit value status/remaining measurement,
  at most three files and one nonempty evidence block (≤10 lines), ≤30 nonempty prose lines.
  `_templates/pr.md` defines the human-facing shape. A successful test does not establish a
  usage/business benefit; unmeasured value stays explicit, with its next observation/owner/time.

Before drafting, agreeing, implementing or handing off, read `AGREEMENT_REVIEW.md` for stage
ownership, approval commands, amendment handling and evidence semantics. The agreement skill
prepares exact scope and draft hashes. UserPromptSubmit grants approval; PreToolUse checks tools
and paths; Stop/pre-commit require current verification and the active local PR. These adapters
require trusted enabled hooks and are not an OS sandbox. Trusted verification commands and host
paths that bypass hooks remain outside the boundary. Value review and PR publishing are human steps.

## Durable decisions (ADR)

Keep decisions that constrain future work in tracked `docs/decisions/`; keep execution history
in local change folders and on the PR. Read `docs/decisions/README.md` when a change establishes
or replaces architecture, shared contracts, security/operational policy, or a harness control.
Use one short ADR per decision: context, decision, alternatives, consequences, revisit trigger,
and references. Routine fixes and implementation details that do not constrain future work need
no ADR. Reuse an existing ADR when the decision is unchanged.

During agreement, put a proposed new/replacement decision in spec/plan, link relevant existing
ADRs and include its future ADR filename in scope.json. After approval, write the ADR through
the same scoped edit path as other tracked files; link it in the local PR. ADR status is not an
approval credential and never replaces the hook-owned agreement. Supersede accepted decisions
with a new ADR; update the old status/link without rewriting its original rationale. Record only
approval actually given; proposals remain proposed. Selecting whether a decision deserves an ADR
and assessing its reasoning are review judgments; current hooks enforce file scope and ADR structure, not semantics.

Use `__PREFIX__-adr` to author or supersede a record. `adr_gate` in the manifest owns the root,
template, statuses and required sections. The ADR Stop and pre-commit hooks validate numbered
records, nonempty sections, dates, statuses and reciprocal replacement links. Pre-commit reads
the index, so an unstaged repair cannot hide a broken staged ADR. The agreement delivery gate
runs the same validation before accepting its handoff. The exact approved scope stays repairable
if another hook rejects the handoff; source edits require fresh verification. Pending drafts and explicit pauses are
not completed deliveries. Run `python3 scripts/adr-gate.py --all` for a read-only full ADR check.

**Proactive ADR suggestions.** Before the agent runs agreement `prepare`, the existing PreToolUse
adapter consults `scripts/harness/adr-advice.py` using planned scope paths. `adr_suggestions` owns
optional topic/glob rules and the maximum candidate count. The hook supplies advisory context
without granting or denying tools. The ADR skill checks the actual decision and existing ADRs,
then proposes a short title, reason and draft summary only when useful. Ordinary edits inside a
matched directory need not produce a user-facing suggestion. Advice is emitted once per change
and matched-path set, tracked separately in the worktree Git directory; it is not approval state.
Missing/broken advisory configuration does not block work. Direct human-terminal prepare and
hosts without the trusted PreToolUse adapter do not receive this automatic reminder. Paths are
heuristics: an unchanged path set can contain a new decision, so the skill also responds to semantic
changes found during normal work. No claim of complete decision detection is made.

## Skills

- One root: `.agents/skills/`. `.claude/skills` mirrors it with one symlink per skill — never a
  copy, and never a second set of files to keep in sync.
- A skill is a directory with `SKILL.md` (YAML frontmatter: `name`, `description`, optionally
  `disable-model-invocation`, `argument-hint`) plus optional `references/`, `assets/`, `scripts/`.
- Write skills in English, in the imperative, addressed to the agent. Keep `SKILL.md` short and push
  detail into `references/` that the skill loads only when needed. The `writing-for-agents` skill is
  the style reference; use it when creating or editing any skill.
- `description` is the routing signal — say when to use the skill (including the phrases a user
  would actually type), not what it is about.
- A skill that reads a repo fact must read it at run time from the file that owns it, not restate it.

**Vendored skills.** `grilling`, `grill-me`, `grill-with-docs`, `domain-modeling`, `to-spec`,
`to-tickets`, `implement`, `tdd`, `code-review` (vendored **as `review-since`** — the upstream name
collides with the Claude Code built-in), `diagnosing-bugs`, `prototype`, `writing-for-agents`, and
`handoff` come from `github.com/mattpocock/skills` (MIT). Do not hand-edit them; refresh with
`python3 scripts/harness/vendor-skills.py --source mattpocock/skills`. A `{name, as}` entry in
`skills.vendored[].skills` renames on import and the check fails if the frontmatter `name` does not
follow. The UI quality layer adds two sources: `web-design-guidelines` from
`github.com/vercel-labs/agent-skills` (MIT) and `review-animations` + `animation-vocabulary` from
`github.com/emilkowalski/skills` (MIT); each has its own `update_command` in `skills.vendored`.

**Adapters.** Vendored workflow skills do not know this repo's change-folder convention, paths, or
language, and their `description` cannot carry local-language triggers without hand edits. Each
chain stage therefore has a project adapter declared in `skills.adapters.map` —
`__PREFIX__-intent` → `grilling`, `__PREFIX__-spec` → `to-spec`, `__PREFIX__-tickets` → `to-tickets`,
`__PREFIX__-implement` → `implement`, `__PREFIX__-ui-review` → `web-design-guidelines` — that reads
`docs/agents/issue-tracker.md`, fixes the `docs/changes/<YYMMDD_NN>-<slug>/` output path, and then
calls the vendored skill with overrides. Because that call goes through the Skill tool, an
adapter-mapped original must not be `disable-model-invocation: true` (the host refuses the call and
the stage is dead); it carries `user-invocable: false` instead, which hides it from the slash menu.
That one frontmatter line is owned by `vendor-skills.py` (rewritten on import) and pinned by the
harness check (`adapter_target_not_invocable`); AGENTS.md and users still route through the adapters
only.

**Disabled skills.** A skill kept but not routed is stored as `SKILL.md.disabled` and declared in
`harness.yaml` `skills.disabled` with `reason` and `replacement`, so the next agent learns why
instead of re-enabling it.

## Hooks and gates

`shared_hook_intents` in `harness.yaml` declares intent once; each host file implements it. The
harness check fails when a declared intent is missing from its host file.

| Intent | Event | Script | Host files |
|---|---|---|---|
| `husky_shim_sessionstart` | SessionStart | `scripts/harness/ensure-husky.sh` | `.claude/settings.json` |
| `harness_fast_guard_stop` | Stop | `scripts/agent-harness-fast-guard.py` (also refuses staged/PR-diff paths under `local_only_roots`) | `.claude/settings.json`, `.codex/hooks.json` |
| `protected_paths_pretooluse` | PreToolUse (Edit/Write/MultiEdit **and Bash**) | `scripts/protected-paths-guard.py` | `.claude/settings.json` |
| `question_gate` | UserPromptSubmit / PreToolUse (AskUserQuestion, EnterPlanMode, ExitPlanMode, Skill) / Stop | `scripts/question-gate.py` | `.claude/settings.json` |
| `pr_body_gate` | PreToolUse (Write) / PostToolUse (Edit, Write, MultiEdit) / Stop | `scripts/pr-body-gate.py` | `.claude/settings.json` |
| `harness_fast_guard_precommit` | pre-commit | `scripts/agent-harness-fast-guard.py` | `.husky/pre-commit` |

Add a project gate by writing it as one line in `.husky/pre-commit` (or one hook entry in
`.claude/settings.json`) **and** declaring it as a `shared_hook_intents` entry — the check then
fails if someone removes the wiring but leaves the declaration, or the reverse.

**Protected paths** (`protected_paths`) block agent edits outright. The PreToolUse guard covers
`Edit`/`Write`/`MultiEdit` by target path and `Bash` by scanning the command for a protected path
next to a write marker (`>`, `sed`, `tee`, `mv`, ...). Read-only shell use of those files is
allowed. The Bash check is a heuristic, so back it with a pre-commit gate for anything that must
never be committed. `protected_paths_examples` in the manifest holds an inactive example entry;
move an entry into `protected_paths` to activate it.

**Question gate** (`question_gate`). The interview stages otherwise dump the whole grilling frontier
on the user as one numbered list — ten questions at once, half of them spec-level. The gate turns
that into rounds of choices: `/__PREFIX__-intent`, `/__PREFIX__-spec` (typed or model-invoked via
`Skill`) and `EnterPlanMode` arm a stage for the session; while armed, every `AskUserQuestion` call
must have at most `max_per_round` (4) questions, each `header` from the stage's category list
(intent: 문제 · 결과 · 가치 · 제약 · 비범위 · 이름; spec: 해법 · 스토리 · 구현 · 테스트 · 우려 ·
비범위; plan: 변경 순서 · 테스트 · 리스크 · 완료 증거), at least `min_options` (3) choices, and
exactly one recommended option, first, labelled `(추천)` — a question with no real alternative is a
decision and is written down instead of asked; a violation is refused (exit 2) with the fix in the
message. A Stop whose last assistant text is a numbered question round (`❓ **Q1**`, `Q1:`, or three
`n. …?` lines) is blocked and sent back to be re-asked as choices. `/__PREFIX__-implement` and
`ExitPlanMode` disarm. Questions outside the stage's categories are not asked — they go to the
artifact's deferral slot (intent 열린 질문 → spec; spec Flagged Concerns → plan) with a recommended
answer. Claude Code is the reference host; the gate has no Codex mirror because Codex has no
selectable-question tool. The vendored `grilling` skill still says "ask the whole frontier in one
round"; the adapters override it and the gate enforces the override.

**Husky in worktrees and fresh clones.** husky only creates the gitignored `.husky/_` shims during
install; without them git runs no hooks at all. `scripts/harness/ensure-husky.sh` writes minimal
shims (idempotent, gitignored), runs at Claude `SessionStart`, and the fast guard fails (exit 1)
when hooks are still unwired instead of only warning. `core.hooksPath` is repo-level and must stay
the relative `.husky/_` husky writes, so each worktree runs its own hook files; an absolute value
that resolves to this repo's `.husky/_` is normalized back by `ensure-husky.sh`, and both scripts
accept either form when judging wiring.

`--no-verify` is for emergencies and must be declared in the PR.

**Wiring check.** The harness check reads only the executable surface of a host file — `command`
strings in JSON adapters, non-comment lines in shell hooks — so a commented-out invocation counts as
unwired even when the script name survives in a comment.

Local agent runtime state (`.claude/skills/.omc/**`, `.codex/worktrees/**`, `.claude/worktrees/**`,
`.serena/**`) is excluded from harness scanning and is not repository policy.

## Verification

```bash
__PACKAGE_MANAGER__ check:harness        # full harness contract check (read-only)
__PACKAGE_MANAGER__ check:harness:fast   # fast guard: doc roots, absolute paths, husky wiring
__PACKAGE_MANAGER__ check:plan           # artifact-chain gate: multi-app / shared-contract diff needs a Plan-Ref commit trailer
__PACKAGE_MANAGER__ test:harness         # check:harness + the harness's own regression tests
__PACKAGE_MANAGER__ evals:harness        # behavioural evals via `claude -p` (model quota; not in test:harness)
```

Run `__PACKAGE_MANAGER__ test:harness` whenever you change `AGENTS.md`, `.agents/`, `.claude/`,
`.codex/`, or `scripts/`. Run `__PACKAGE_MANAGER__ evals:harness` when you change instruction text
(`AGENTS.md`, `apps/*/AGENTS.md`, skills) — it is the only check that measures whether an agent
*follows* a rule, not whether the rule is present. Cases live in `.claude/evals/cases.jsonl`
(declared in `harness.yaml` `evals`); add one whenever a review or incident traces back to an
ignored instruction.

## CI

Run the read-only harness lane from `__CI_FILE__`: `scripts/check-agent-harness.py --format text`
plus the guard regression tests, on every PR and on the default branch when `AGENTS.md`,
`package.json`, `.agents/**`, `.claude/**`, `.codex/**`, `docs/**`, `scripts/**`, or the pipeline
file changed. Point `harness.yaml` `ci.pipeline_file` at `__CI_FILE__` once the lane exists — the
harness check then warns when the pipeline stops referencing the checker.

Also run `scripts/harness/check-plan-artifact.sh` on every PR: a diff spanning two or more `apps/*`
or touching a shared contract without a `Plan-Ref: <YYMMDD_NN>-<slug>` commit trailer in the PR
range gets a warning in the log. Warn-first; promote with `PLAN_GATE=enforce` once the gate has
earned trust. CI cannot read the PR description without a token, so the gate reads commit trailers,
not the description.

## Changing the harness

1. Edit `.agents/harness.yaml` first — it is the contract, the host files are adapters.
2. Mirror the change into every host file the intent declares (`.claude/settings.json`,
   `.codex/hooks.json`, `.husky/pre-commit`).
3. Run `__PACKAGE_MANAGER__ test:harness` and paste the result.
4. Open a PR describing which layer changed and why the rule could not live one layer lower.

## Ponytail simplification

Use `__PREFIX__-ponytail` for the vendored Ponytail ladder: existing code, standard library,
native platform features, installed dependencies, then minimal new code. This is a code-design
aid, not authorization to shrink agreed requirements, skip HTML/ADR/value-review artifacts or
replace the project's test/review requirements. The upstream skill is pinned by recorded commit
and carries its MIT license. Only the main skill is installed; upstream lifecycle hooks, mode
tracking, metrics and other plugin components are not registered in this harness.
The project adapter preserves the original skill body and states harness-specific overrides.
