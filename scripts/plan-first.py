#!/usr/bin/env python3
"""Plan-first hook: no repository edit before this session has an approved plan.

Modes (Claude Code hook payload on stdin):
- gate   PreToolUse Edit|Write|MultiEdit|NotebookEdit. The target (file_path or notebook_path, resolved
         against the payload cwd, symlinks followed) is placed by git from its nearest existing directory,
         so case-variant spellings and worktrees (.claude/worktrees/) resolve to their own work tree.
         Exit 2 when that is this repository (same git common dir: any worktree, or its git dir), the
         path relative to its work tree is outside `plan_first.exempt_roots`, the session has no marker
         and the `plan_first.env` variable is not "1". Targets in no git repository or another one
         (plan files under ~/.claude/plans, scratchpads, memory) pass. An unreadable payload blocks.
- mark   PostToolUse ExitPlanMode (fires only on approval). Writes the marker
         <git common dir>/harness/plan-approved/<session_id> as JSON {approved_at, plan_file, plan} and
         deletes markers older than 30 days.
- clear  PostToolUse EnterPlanMode. Deletes that marker: a new plan needs a new approval.
- prompt UserPromptSubmit. Deletes it when permission_mode is "plan" (Shift+Tab into plan mode fires no
         EnterPlanMode). Never blocks the prompt and never prints to stdout (that becomes prompt context).

The marker means "this session had a plan approved since it last entered plan mode" (entering = an
EnterPlanMode call, or a prompt sent while in plan mode). Subagents send the parent's session_id, so an
approved session's implementers pass; agent_type is never used. Bash writes are not gated (an accepted gap).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

BLOCK = (
    "plan-first: '{rel}' is in the repository and there is no record that this session had a plan approved "
    "since it last entered plan mode (entering = an EnterPlanMode call, or a prompt sent while in plan mode). "
    "Call EnterPlanMode, present the plan and wait for the user's approval. Do not retry the edit via Bash."
)
MARKER_DAYS = 30


def rev_parse(start: Path, *args: str) -> list[str]:
    return subprocess.run(
        ["git", "rev-parse", "--path-format=absolute", *args], cwd=start, capture_output=True, text=True, check=True,
    ).stdout.splitlines()


def load_config(top: Path) -> dict:
    try:
        return json.loads((top / ".agents" / "harness.json").read_text(encoding="utf-8")).get("plan_first", {})
    except Exception:
        return {}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["gate", "mark", "clear", "prompt"])
    parser.add_argument("--repo-root", default=None)
    args = parser.parse_args()
    try:
        payload = json.load(sys.stdin)
        sid = payload.get("session_id") or ""
        start = Path(args.repo_root or os.getcwd())
        top, common = (Path(p).resolve() for p in rev_parse(start, "--show-toplevel", "--git-common-dir"))
    except Exception as exc:
        if args.mode == "prompt":
            return 0
        print(f"plan-first: cannot read the hook payload or the repository ({exc}); blocking.", file=sys.stderr)
        return 2
    marker = common / "harness" / "plan-approved" / sid
    valid_sid = re.fullmatch(r"[A-Za-z0-9._-]+", sid) is not None and sid not in (".", "..")

    if args.mode == "mark":
        if not valid_sid:
            print("plan-first: payload has no usable session_id; approval not recorded.", file=sys.stderr)
            return 2
        response = payload.get("tool_response")
        response = response if isinstance(response, dict) else {}
        marker.parent.mkdir(parents=True, exist_ok=True)
        for old in marker.parent.iterdir():
            if old.is_file() and old.stat().st_mtime < time.time() - MARKER_DAYS * 86400:
                old.unlink(missing_ok=True)
        record = {
            "approved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "plan_file": response.get("filePath"),
            "plan": response.get("plan"),
        }
        marker.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 0
    if args.mode in ("clear", "prompt"):
        if valid_sid and (args.mode == "clear" or payload.get("permission_mode") == "plan"):
            marker.unlink(missing_ok=True)
        return 0

    config = load_config(top)
    if os.environ.get(config.get("env") or "HARNESS_PLAN_APPROVED") == "1":
        return 0
    tool_input = payload.get("tool_input") or {}
    target = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not isinstance(target, str) or not target:
        print("plan-first: payload has no file_path or notebook_path; blocking.", file=sys.stderr)
        return 2
    cwd = Path(payload.get("cwd") or os.getcwd())
    real = Path(os.path.realpath(cwd / os.path.expanduser(target)))
    base = real
    while not base.is_dir():
        base = base.parent
    try:
        own = rev_parse(base, "--git-common-dir", "--is-inside-git-dir", "--show-prefix") + [""]
    except subprocess.CalledProcessError:
        return 0  # not in a git repository
    if not os.path.samefile(own[0], common):
        return 0  # another repository
    rel = str(real) if own[1] == "true" else (Path(own[2]) / real.relative_to(base)).as_posix()
    if any(rel.startswith(root) for root in config.get("exempt_roots", [])):
        return 0
    if valid_sid and marker.is_file():
        return 0
    print(BLOCK.format(rel=rel), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
