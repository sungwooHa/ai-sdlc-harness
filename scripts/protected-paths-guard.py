#!/usr/bin/env python3
"""PreToolUse hook: block agent edits to generated or protected files.

Reads the Claude Code hook payload from stdin and exits 2 (block) when the
target matches a protected pattern declared in `.agents/harness.yaml`
`protected_paths`.

Two tool shapes are covered:
- Edit/Write/MultiEdit: the `file_path` (or `path`) field is the target.
- Bash: every path-shaped token of `command` is a candidate target, but the
  call is blocked only when the command also carries a write marker
  (`>`/`>>` redirection, `sed`, `tee`, `mv`, `cp`, `rm`, ...). Read-only
  commands (`cat`, `grep`, `diff`, ...) on protected files stay allowed.
  This is a heuristic side fence, not a parser; the pre-commit drift gate is
  the second fence for anything that slips through.

Fail-open on any parsing problem so a broken hook never blocks normal work.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import shlex
import sys
from pathlib import Path

# Commands/tokens that indicate the shell line writes to a file. `git` is left
# out on purpose: `git add`/`git checkout -- <file>` are not edits.
WRITE_MARKERS = {
    ">", ">>", "sed", "tee", "mv", "cp", "rm", "truncate", "dd", "install", "patch",
    "perl", "python", "python3", "node", "npx", "ruby", "awk",
}


def load_patterns(repo: Path) -> list[dict]:
    manifest = repo / ".agents" / "harness.yaml"
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except Exception:
        return []
    return list(data.get("protected_paths", []))


def to_rel(target: str, repo: Path, cwd: Path) -> str | None:
    try:
        rel = os.path.relpath((cwd / target).resolve(), repo)
    except Exception:
        return None
    if rel.startswith(".."):
        return None
    return rel


def match_rule(rel: str, rules: list[dict]) -> dict | None:
    for rule in rules:
        for pattern in rule.get("globs", []):
            if fnmatch.fnmatch(rel, pattern):
                return rule
    return None


def bash_targets(command: str, repo: Path, cwd: Path) -> list[str]:
    """Path-shaped tokens of a shell command, as repo-relative paths."""
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        tokens = command.split()
    # Split glued redirections like `>>file` and drop the operator itself.
    words: list[str] = []
    for tok in tokens:
        stripped = tok.lstrip(">")
        if stripped != tok and stripped:
            words.append(stripped)
        else:
            words.append(tok)
    has_write = any(t in WRITE_MARKERS or t.startswith(">") for t in tokens)
    if not has_write:
        return []
    rels: list[str] = []
    for tok in words:
        if tok in WRITE_MARKERS or tok.startswith("-") or "/" not in tok and "." not in tok:
            continue
        tok = tok.replace("$CLAUDE_PROJECT_DIR", str(repo)).replace("${CLAUDE_PROJECT_DIR}", str(repo))
        rel = to_rel(tok, repo, cwd)
        if rel:
            rels.append(rel)
    return rels


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=None)
    args = parser.parse_args()
    repo = Path(args.repo_root).resolve() if args.repo_root else Path.cwd().resolve()

    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    tool_name = payload.get("tool_name") or ""
    tool_input = payload.get("tool_input") or {}
    cwd = Path(payload.get("cwd") or repo)

    rules = load_patterns(repo)
    if not rules:
        return 0

    candidates: list[str] = []
    if tool_name == "Bash":
        command = tool_input.get("command") or ""
        if not command:
            return 0
        candidates = bash_targets(command, repo, cwd)
    else:
        target = tool_input.get("file_path") or tool_input.get("path")
        if not target:
            return 0
        rel = to_rel(target, repo, cwd)
        if rel:
            candidates = [rel]

    for rel in candidates:
        rule = match_rule(rel, rules)
        if rule:
            via = " (via Bash)" if tool_name == "Bash" else ""
            print(
                f"protected-paths-guard: '{rel}' is protected ({rule.get('id')}){via}. "
                f"{rule.get('reason', '')} {rule.get('instead', '')}".strip(),
                file=sys.stderr,
            )
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
