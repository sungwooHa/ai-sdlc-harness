#!/usr/bin/env python3
"""Regression tests for scripts/protected-paths-guard.py.

Edit/Write on a protected path must block (exit 2); Bash commands that write to
a protected path must block too; read-only Bash and unrelated writes stay open.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

GUARD = Path(__file__).resolve().parents[1] / "protected-paths-guard.py"

MANIFEST = {
    "protected_paths": [
        {"id": "gen", "globs": ["packages/generated/**/*.generated.ts"], "reason": "generated", "instead": "sync"},
        {"id": "lock", "globs": ["pnpm-lock.yaml", "poetry.lock"], "reason": "lockfile", "instead": "pnpm install"},
    ]
}
GEN = "packages/generated/cli/token-registry.generated.ts"


def run(root: Path, tool_name: str, tool_input: dict) -> int:
    payload = {"tool_name": tool_name, "tool_input": tool_input, "cwd": str(root)}
    completed = subprocess.run(
        [sys.executable, str(GUARD), "--repo-root", str(root)],
        input=json.dumps(payload), capture_output=True, text=True, errors="replace",
    )
    return completed.returncode


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        (root / ".agents").mkdir()
        (root / ".agents/harness.yaml").write_text(json.dumps(MANIFEST), encoding="utf-8")

        cases = [
            # (tool, input, expected exit, label)
            ("Edit", {"file_path": str(root / GEN)}, 2, "Edit on generated file blocks"),
            ("Write", {"file_path": str(root / "pnpm-lock.yaml")}, 2, "Write on lockfile blocks"),
            ("Edit", {"file_path": str(root / "src/x.ts")}, 0, "Edit on ordinary file passes"),
            ("Bash", {"command": f"sed -i '' 's/a/b/' {GEN}"}, 2, "Bash sed -i on generated file blocks"),
            ("Bash", {"command": f"echo '// x' >> {GEN}"}, 2, "Bash >> redirection blocks"),
            ("Bash", {"command": f"cat > {root / GEN} <<'EOF'\nx\nEOF"}, 2, "Bash heredoc with absolute path blocks"),
            ("Bash", {"command": 'echo x >> "$CLAUDE_PROJECT_DIR"/pnpm-lock.yaml'}, 2, "Bash with $CLAUDE_PROJECT_DIR blocks"),
            ("Bash", {"command": f"cat {GEN} | head"}, 0, "Bash read-only passes"),
            ("Bash", {"command": f"grep -n foo {GEN}"}, 0, "Bash grep passes"),
            ("Bash", {"command": "pnpm install"}, 0, "Bash pnpm install passes (regenerates lockfile legitimately)"),
            ("Bash", {"command": "echo hi > src/x.ts"}, 0, "Bash write to ordinary file passes"),
            ("Bash", {"command": f"git add {GEN}"}, 0, "Bash git add passes"),
        ]
        failures = []
        for tool, tool_input, expected, label in cases:
            code = run(root, tool, tool_input)
            if code != expected:
                failures.append(f"{label}: expected exit {expected}, got {code}")
        if failures:
            print("FAIL: protected-paths-guard")
            for f in failures:
                print(f"- {f}")
            return 1
    print("PASS: protected-paths-guard tests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
