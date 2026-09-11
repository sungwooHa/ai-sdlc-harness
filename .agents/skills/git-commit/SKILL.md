---
name: git-commit
description: 'Execute git commit with conventional commit message analysis, intelligent staging, and message generation. Use when user asks to commit changes, create a git commit, or mentions "/commit". Supports: (1) Auto-detecting type and scope from changes, (2) Generating conventional commit messages from diff, (3) Interactive commit with optional type/scope/description overrides, (4) Intelligent file staging for logical grouping'
---

# Git Commit with Conventional Commits

## Overview

Create standardized, semantic git commits using the Conventional Commits specification. Analyze the actual diff to determine appropriate type, scope, and message.

## Project-Specific Message Policy

When this workspace uses this project's commit convention, prefer the project format below over a generic Conventional Commit summary:

```text
{type}: [모듈명] {변경 내용}
```

Allowed simplified variant:

```text
{type}: {변경 내용}
```

Apply these rules when generating the final commit message:

- Write `{변경 내용}` in Korean
- Keep `type` lowercase
- Use `[모듈명]` only when the change clearly belongs to one domain or feature area
- Keep the summary clear and concise; 50-72 characters is preferred
- Prefer one logical change per commit and split unrelated work into separate commits

Preferred project types:

- `feat`
- `fix`
- `docs`
- `style`
- `refactor`
- `test`
- `chore`

Examples:

```text
feat: [통합훈련] 채팅 훈련 실습 대화 종료 기능 구현
fix: [통합훈련] 채팅 입력창 Enter 중복 전송 버그 수정
refactor: 전역 스타일 정리
chore: 빌드 설정 업데이트
```

## Conventional Commit Format

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

## Commit Types

| Type       | Purpose                        |
| ---------- | ------------------------------ |
| `feat`     | New feature                    |
| `fix`      | Bug fix                        |
| `docs`     | Documentation only             |
| `style`    | Formatting/style (no logic)    |
| `refactor` | Code refactor (no feature/fix) |
| `perf`     | Performance improvement        |
| `test`     | Add/update tests               |
| `build`    | Build system/dependencies      |
| `ci`       | CI/config changes              |
| `chore`    | Maintenance/misc               |
| `revert`   | Revert commit                  |

## Breaking Changes

```
# Exclamation mark after type/scope
feat!: remove deprecated endpoint

# BREAKING CHANGE footer
feat: allow config to extend other configs

BREAKING CHANGE: `extends` key behavior changed
```

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
# Stage specific files
git add path/to/file1 path/to/file2

# Stage by pattern
git add *.test.*
git add src/components/*

# Interactive staging
git add -p
```

**Never commit secrets** (.env, credentials.json, private keys).

### 3. Generate Commit Message

Analyze the diff to determine:

- **Type**: What kind of change is this?
- **Scope**: What area/module is affected?
- **Description**: One-line summary of what changed (present tense, imperative mood, <72 chars)

When the repository expects the project-specific commit format:

- Prefer the project type set (`feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`)
- Convert the final description to concise Korean
- Add `[모듈명]` only when it improves clarity
- Include the issue number when the task is associated with one

### 4. Execute Commit

```bash
# Single line
git commit -m "<type>[scope]: <description>"

# Multi-line with body/footer
git commit -m "$(cat <<'EOF'
<type>[scope]: <description>

<optional body>

<optional footer>
EOF
)"
```

## Best Practices

- One logical change per commit
- Present tense: "add" not "added"
- Imperative mood: "fix bug" not "fixes bug"
- Reference issues: `Closes #123`, `Refs #456`
- Keep description under 72 characters

## Git Safety Protocol

- NEVER update git config
- NEVER run destructive commands (--force, hard reset) without explicit request
- NEVER skip hooks (--no-verify) unless user asks
- NEVER force push to main/master
- If commit fails due to hooks, fix and create NEW commit (don't amend)
