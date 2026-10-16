#!/usr/bin/env python3
"""Plan-first hook: no repository edit before this session has an approved plan.

Modes (Claude Code hook payload on stdin):
- gate  PreToolUse Edit|Write|MultiEdit|NotebookEdit. Exit 2 when the target (file_path or
        notebook_path, resolved against the payload cwd, symlinks followed) is inside the
        repository, outside `plan_first.exempt_roots`, the session has no marker and the
        `plan_first.env` variable is not "1". Paths outside the repository (plan files under
        ~/.claude/plans, scratchpads, memory) always pass. An unreadable payload blocks.
- mark  PostToolUse ExitPlanMode (fires only on approval). Writes the marker
        <git common dir>/harness/plan-approved/<session_id> as JSON {approved_at, plan_file, plan}.
- clear PostToolUse EnterPlanMode. Deletes that marker: a new plan needs a new approval.

The marker means "this session had a plan approved since its last EnterPlanMode", not "this
change's plan was approved". Subagents send the parent's session_id, so an approved session's
implementers pass; agent_type is never used. Bash writes are not gated (an accepted gap).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

BLOCK = (
    "plan-first: '{rel}' is in the repository and this session has no approved plan since its last "
    "EnterPlanMode. (An approval marks the session, not this specific change.) Call EnterPlanMode, "
    "present the plan and wait for the user's approval. Do not retry the edit via Bash."
)


def repo_dirs(start: Path) -> tuple[Path, Path]:
    out = subprocess.run(
        ["git", "-C", str(start), "rev-parse", "--path-format=absolute", "--show-toplevel", "--git-common-dir"],
        capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    return Path(out[0]).resolve(), Path(out[1]).resolve()


def load_config(top: Path) -> dict:
    try:
        return json.loads((top / ".agents" / "harness.json").read_text(encoding="utf-8")).get("plan_first", {})
    except Exception:
        return {}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["gate", "mark", "clear"])
    parser.add_argument("--repo-root", default=None)
    args = parser.parse_args()
    try:
        payload = json.load(sys.stdin)
        sid = payload.get("session_id") or ""
        top, common = repo_dirs(Path(args.repo_root or os.getcwd()))
    except Exception as exc:
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
        record = {
            "approved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "plan_file": response.get("filePath"),
            "plan": response.get("plan"),
        }
        marker.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 0
    if args.mode == "clear":
        if valid_sid:
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
    if real != top and top not in real.parents:
        return 0
    rel = real.relative_to(top).as_posix()
    if any(rel.startswith(root) for root in config.get("exempt_roots", [])):
        return 0
    if valid_sid and marker.is_file():
        return 0
    print(BLOCK.format(rel=rel), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
