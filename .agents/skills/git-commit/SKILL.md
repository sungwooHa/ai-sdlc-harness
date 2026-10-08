---
name: git-commit
description: 'Execute git commit with conventional commit message analysis, intelligent staging, and message generation. Use when user asks to commit changes, create a git commit, or mentions "/commit". Supports: (1) Auto-detecting type and scope from changes, (2) Generating conventional commit messages from diff, (3) Interactive commit with optional type/scope/description overrides, (4) Intelligent file staging for logical grouping'
---

# Git Commit

## Overview

Create git commits that follow this repository's commit convention. Analyze the actual diff to determine the type, the optional module or scope, and the message.

## Project Commit Convention

Read `docs/standards/COMMIT_CONVENTION.md` before writing the message. It is the only source for the first-line format, the types, the body and the trailers, and it wins over any generic Conventional Commits habit. The commit-msg hook (`scripts/commit-msg-gate.py`) refuses a first line outside that format and any trailer other than `Plan-Ref`.

## Workflow

### 0. Review and Simplify Pending Code

Before analyzing the commit, review pending code changes (working tree +
staged) for unnecessary duplication, avoidable complexity, inefficient work,
and mismatched abstraction levels. Apply only safe, scope-preserving cleanup so
the commit captures maintainable code without changing the user's intent.

- If the current runtime provides a `simplify` skill or equivalent capability,
  use it for this review
- If no such capability is available, perform the review directly with the
  available diff, search, edit, and validation tools; continue the commit
  workflow without treating the missing optional capability as an error or
  mentioning it to the user
- Do not assume slash commands, Claude Code's `Skill` tool, or any specific
  agent runtime is available
- Skip this step when the change set contains no executable code (for example,
  docs-only changes) or when the user explicitly asks to commit as-is
- Do not introduce behavior changes, broad refactors, or unrelated cleanup as
  part of this step; surface material concerns separately
- If cleanup modifies files, re-check `git status`, staged diff, and unstaged
  diff so the resulting state is what gets staged and analyzed

### 1. Analyze Diff

```bash
# If files are staged, use staged diff
git diff --staged

# If nothing staged, use working tree diff
git diff

# Also check status
git status --porcelain
```

### 2. Stage Files (if needed)

If nothing is staged or you want to group changes differently:

```bash
git add path/to/file1 path/to/file2
```

Name each file exactly. The agreement gate refuses globs (`*.test.*`), directories, files outside the
approved scope and options such as `-p` or `-A`.

**Never commit secrets** (.env, credentials.json, private keys).

### 3. Generate Commit Message

Analyze the diff to determine:

- **Type**: What kind of change is this? Use only the convention's types.
- **Module or scope**: Which one area is affected? Leave it out when the change spans several.
- **Summary**: One line saying what changed, in the language and length the convention sets.
- **Body and trailers**: Only what the convention allows.

### 4. Execute Commit

Pass each paragraph as its own `-m`; agent shells refuse newlines and command substitution:

```bash
git commit -m "<first line>"
git commit -m "<first line>" -m "<why>" -m "Plan-Ref: <YYMMDD_NN>-<slug>"
```

## Best Practices

- One logical change per commit
- When the hook refuses a message, fix the message and commit again

## Git Safety Protocol

- NEVER update git config
- NEVER run destructive commands (--force, hard reset) without explicit request
- NEVER skip hooks (--no-verify) unless user asks
- NEVER force push to main/master
- If commit fails due to hooks, fix and create NEW commit (don't amend)
