#!/usr/bin/env python3
"""PostToolUse hook: run the configured formatter on the file an Edit/Write/MultiEdit just changed.

`.agents/harness.json` `format_on_edit` maps a repo-relative glob to an argv list; the first glob
that matches runs with the file path appended. An empty map (the template default), an unmatched
file, a file outside the repository or an unreadable payload is a no-op. A formatter that fails or
cannot start exits 2, so its output reaches the agent.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=None)
    args = parser.parse_args()
    repo = Path(args.repo_root or os.getcwd()).resolve()
    try:
        config = json.loads((repo / ".agents" / "harness.json").read_text(encoding="utf-8")).get("format_on_edit") or {}
        payload = json.load(sys.stdin)
        target = (payload.get("tool_input") or {}).get("file_path")
        path = Path(os.path.realpath(Path(payload.get("cwd") or repo) / target))
        rel = path.relative_to(repo).as_posix()
    except Exception:
        return 0
    argv = next((argv for glob, argv in config.items() if fnmatch.fnmatch(rel, glob)), None)
    if not argv:
        return 0
    try:
        result = subprocess.run([*argv, str(path)], cwd=repo, capture_output=True, text=True)
    except OSError as exc:
        print(f"format-on-edit: cannot run {argv[0]}: {exc}", file=sys.stderr)
        return 2
    if result.returncode != 0:
        print(f"format-on-edit: {' '.join(argv)} failed on {rel} (exit {result.returncode}):", file=sys.stderr)
        print((result.stdout + result.stderr).strip(), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
