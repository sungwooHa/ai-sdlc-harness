#!/usr/bin/env python3
"""Pre-commit secret scan: block a commit whose staged diff adds a line matching a secret pattern.

Usage: secret-scan.py --staged. Only lines the staged diff adds are scanned (removed lines and
unstaged files are not), against `.agents/harness.json` `secrets.patterns` ({id, regex}). Findings
name the file, line and pattern id; the secret itself is never printed.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def main() -> int:
    if sys.argv[1:] != ["--staged"]:
        print("usage: secret-scan.py --staged", file=sys.stderr)
        return 2
    top = Path(git("rev-parse", "--show-toplevel").strip())
    config = json.loads((top / ".agents" / "harness.json").read_text(encoding="utf-8"))
    patterns = [(p["id"], re.compile(p["regex"])) for p in config.get("secrets", {}).get("patterns", [])]
    diff = git("-C", str(top), "diff", "--cached", "--no-color", "--no-ext-diff", "--no-prefix", "-U0", "--diff-filter=ACMR")

    findings: list[str] = []
    path, line_no, in_hunk = "", 0, False
    for line in diff.splitlines():
        if line.startswith("diff --git "):
            in_hunk = False
        elif not in_hunk and line.startswith("+++ "):
            path = line[4:]
        elif line.startswith("@@"):
            in_hunk = True
            line_no = int(re.match(r"@@ -\S+ \+(\d+)", line).group(1))
        elif in_hunk and line.startswith("+"):
            findings += [f"{path}:{line_no}: {pid}" for pid, rx in patterns if rx.search(line[1:])]
            line_no += 1
    if not findings:
        return 0
    print("secret-scan: the staged diff adds what looks like a secret:", file=sys.stderr)
    for finding in findings:
        print(f"  {finding}", file=sys.stderr)
    print(
        "Remove it from the staged change (keep secrets in untracked env files) and commit again. "
        "A false positive means the pattern in .agents/harness.json secrets.patterns needs fixing.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
