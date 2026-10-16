#!/usr/bin/env python3
"""Regression tests for scripts/format-on-edit.py.

The first glob in `.agents/harness.json` `format_on_edit` that matches the edited file runs its argv
with the file appended; an empty config, an unmatched file or a file outside the repository is a no-op
(exit 0); a formatter that fails exits 2 and passes its output on.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "format-on-edit.py"


def run(root: Path, config: dict, file_path: str) -> subprocess.CompletedProcess:
    (root / ".agents/harness.json").write_text(json.dumps({"format_on_edit": config}), encoding="utf-8")
    payload = {"session_id": "s1", "cwd": str(root), "tool_name": "Edit", "tool_input": {"file_path": file_path}}
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--repo-root", str(root)],
        input=json.dumps(payload), capture_output=True, text=True,
    )


def main() -> int:
    failures: list[str] = []

    def check(label: str, actual, expected) -> None:
        if actual != expected:
            failures.append(f"{label}: expected {expected!r}, got {actual!r}")

    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir) / "repo"
        (root / ".agents").mkdir(parents=True)
        (root / "src").mkdir()
        target = root / "src/a.py"
        target.write_text("x\n", encoding="utf-8")
        log = root / "formatted.log"
        # A stand-in formatter: appends its last argument to the log.
        append = [sys.executable, "-c", f"import sys; open({str(log)!r}, 'a').write(sys.argv[-1] + '\\n')"]
        fail = [sys.executable, "-c", "import sys; print('bad syntax at line 1'); sys.exit(3)"]

        check("empty config exits 0", run(root, {}, str(target)).returncode, 0)
        check("unmatched file exits 0", run(root, {"*.ts": append}, str(target)).returncode, 0)
        check("unmatched file runs nothing", log.exists(), False)
        check("file outside repo exits 0", run(root, {"*": append}, str(Path(temp_dir) / "x.py")).returncode, 0)
        check("file outside repo runs nothing", log.exists(), False)

        result = run(root, {"src/*.py": append, "*.py": fail}, str(target))
        check("first match runs and exits 0", result.returncode, 0)
        lines = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
        check("formatter got the file path", lines, [str(target.resolve())])

        result = run(root, {"*.py": fail}, str(target))
        check("failing formatter exits 2", result.returncode, 2)
        check("failing formatter output is passed on", "bad syntax at line 1" in result.stderr, True)
        result = run(root, {"*.py": ["no-such-formatter-xyz"]}, str(target))
        check("missing formatter exits 2", result.returncode, 2)

    if failures:
        print("FAIL: format-on-edit")
        for f in failures:
            print(f"- {f}")
        return 1
    print("PASS: format-on-edit tests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
