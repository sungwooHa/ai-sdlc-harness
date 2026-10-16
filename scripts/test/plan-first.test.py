#!/usr/bin/env python3
"""Regression tests for scripts/plan-first.py.

`gate` blocks (exit 2) an Edit/Write/MultiEdit/NotebookEdit on a file inside the repository when the
payload's session has no approval marker, and passes files under the exempt roots, files outside the
repository (plan files under ~/.claude/plans, temp dirs), sessions with a marker and runs with the
human-set environment variable. `mark` (PostToolUse ExitPlanMode) writes the marker as JSON from
tool_response; `clear` (PostToolUse EnterPlanMode) deletes it. A subagent call carries the parent's
session_id, with agent_type missing or empty, and is judged the same way. Relative paths resolve
against the payload cwd and symlinks resolve to their real location. An unreadable payload blocks.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "plan-first.py"
ENV = "HARNESS_PLAN_APPROVED"
CONFIG = {"plan_first": {"exempt_roots": ["docs/changes/"], "env": ENV}}


def run(root: Path, mode: str, payload, env_on: bool = False) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k != ENV}
    if env_on:
        env[ENV] = "1"
    data = payload if isinstance(payload, str) else json.dumps(payload)
    return subprocess.run(
        [sys.executable, str(SCRIPT), mode, "--repo-root", str(root)],
        input=data, capture_output=True, text=True, env=env,
    )


def edit(root: Path, path: str, sid: str = "s1", tool: str = "Edit", key: str = "file_path", cwd=None, **extra) -> dict:
    return {"session_id": sid, "cwd": str(cwd or root), "tool_name": tool, "tool_input": {key: path}, **extra}


def main() -> int:
    failures: list[str] = []

    def check(label: str, actual, expected) -> None:
        if actual != expected:
            failures.append(f"{label}: expected {expected!r}, got {actual!r}")

    with tempfile.TemporaryDirectory() as temp_dir:
        base = Path(temp_dir)  # unresolved on purpose (macOS /var -> /private/var)
        root = base / "repo"
        (root / ".agents").mkdir(parents=True)
        (root / "src").mkdir()
        (root / ".agents/harness.json").write_text(json.dumps(CONFIG), encoding="utf-8")
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        outside = base / "outside"
        outside.mkdir()
        os.symlink(root, base / "repo-link")
        os.symlink(outside, root / "out-link")
        src = str(root / "src/a.py")

        def gate(payload, **kw) -> int:
            return run(root, "gate", payload, **kw).returncode

        result = run(root, "gate", edit(root, src))
        check("in repo, no marker -> blocks", result.returncode, 2)
        check("block message names EnterPlanMode", "EnterPlanMode" in result.stderr, True)
        check("block message says not to retry via Bash", "Bash" in result.stderr, True)
        check("block message states the marker meaning", "since its last EnterPlanMode" in result.stderr, True)
        check("docs/changes passes", gate(edit(root, str(root / "docs/changes/261015_00-x/plan.md"))), 0)
        check("plan file under ~/.claude/plans passes", gate(edit(root, os.path.expanduser("~/.claude/plans/x.md"))), 0)
        check("temp dir outside repo passes", gate(edit(root, str(outside / "note.md"))), 0)
        check("Write in repo blocks", gate(edit(root, src, tool="Write")), 2)
        check("MultiEdit in repo blocks", gate(edit(root, src, tool="MultiEdit")), 2)
        check("NotebookEdit notebook_path blocks", gate(edit(root, str(root / "n.ipynb"), tool="NotebookEdit", key="notebook_path")), 2)
        check("relative path against payload cwd blocks", gate(edit(root, "src/a.py")), 2)
        check("relative path from subdir blocks", gate(edit(root, "../src/a.py", cwd=root / "src")), 2)
        check("path through symlinked repo blocks", gate(edit(root, str(base / "repo-link/src/a.py"))), 2)
        check("symlink in repo pointing outside passes", gate(edit(root, str(root / "out-link/x.md"))), 0)
        check("env set passes", gate(edit(root, src), env_on=True), 0)
        check("broken payload blocks", gate("{not json"), 2)
        check("payload without target blocks", gate({"session_id": "s1", "tool_input": {}}), 2)

        plan = {"plan": "# Plan\n- step", "filePath": os.path.expanduser("~/.claude/plans/p.md")}
        result = run(root, "mark", {"session_id": "s1", "cwd": str(root), "tool_name": "ExitPlanMode", "tool_response": plan})
        check("mark exits 0", result.returncode, 0)
        marker = root / ".git/harness/plan-approved/s1"
        data = json.loads(marker.read_text(encoding="utf-8")) if marker.is_file() else {}
        check("marker keys", sorted(data), ["approved_at", "plan", "plan_file"])
        check("marker plan", data.get("plan"), plan["plan"])
        check("marker plan_file", data.get("plan_file"), plan["filePath"])
        check("same session after mark passes", gate(edit(root, src)), 0)
        check("other session after mark blocks", gate(edit(root, src, sid="s2")), 2)
        sub = {"agent_id": "a1"}
        check("subagent, agent_type missing, passes", gate(edit(root, src, **sub)), 0)
        check("subagent, agent_type empty, passes", gate(edit(root, src, agent_type="", **sub)), 0)
        check("subagent of other session blocks", gate(edit(root, src, sid="s2", agent_type="", **sub)), 2)
        check("path-like session_id blocks", gate(edit(root, src, sid="../plan-approved/s1")), 2)

        check("clear exits 0", run(root, "clear", {"session_id": "s1", "cwd": str(root), "tool_name": "EnterPlanMode"}).returncode, 0)
        check("marker removed", marker.exists(), False)
        check("after clear blocks", gate(edit(root, src)), 2)
        check("clear without marker exits 0", run(root, "clear", {"session_id": "s9"}).returncode, 0)
        check("mark with broken payload fails", run(root, "mark", "{").returncode, 2)

    if failures:
        print("FAIL: plan-first")
        for f in failures:
            print(f"- {f}")
        return 1
    print("PASS: plan-first tests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
