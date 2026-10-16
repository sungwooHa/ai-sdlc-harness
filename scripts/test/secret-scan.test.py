#!/usr/bin/env python3
"""Regression tests for scripts/secret-scan.py --staged.

Only lines the staged diff adds are scanned against `.agents/harness.json` `secrets.patterns`: a staged
secret blocks (non-zero exit, file and pattern id named, secret not echoed), an unstaged one and a line
the diff removes do not, and a clean staged diff passes. A non-UTF-8 (Latin-1) file does not crash the
scan and a CR-only file is still scanned. Fake secrets are assembled at run time so this
file never matches the scan itself.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "secret-scan.py"
REAL_CONFIG = Path(__file__).resolve().parents[2] / ".agents" / "harness.json"
AWS = "AKIA" + "Q" * 16
GHP = "ghp" + "_" + "a1B2" * 9
SK = "sk" + "-" + "x" * 24
PEM = "-----BEGIN RSA " + "PRIVATE KEY-----"


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def scan(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), "--staged"], cwd=root, capture_output=True, text=True)


def main() -> int:
    failures: list[str] = []

    def check(label: str, actual, expected) -> None:
        if actual != expected:
            failures.append(f"{label}: expected {expected!r}, got {actual!r}")

    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        git(root, "init", "-q")
        (root / ".agents").mkdir()
        shutil.copy(REAL_CONFIG, root / ".agents/harness.json")
        (root / "old.env").write_text(f"KEY={AWS}\n", encoding="utf-8")
        git(root, "add", "-A")
        git(root, "-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q", "--no-verify", "-m", "init")

        check("nothing staged passes", scan(root).returncode, 0)
        (root / "old.env").write_text("KEY=redacted\n", encoding="utf-8")
        git(root, "add", "old.env")
        check("removed secret line passes", scan(root).returncode, 0)
        (root / "app.py").write_text("print('hello')\n", encoding="utf-8")
        git(root, "add", "app.py")
        check("clean staged diff passes", scan(root).returncode, 0)
        (root / "unstaged.py").write_text(f"T = '{GHP}'\n", encoding="utf-8")
        check("unstaged secret passes", scan(root).returncode, 0)

        for label, secret in [("aws key", AWS), ("github token", GHP), ("sk- key", SK), ("private key block", PEM)]:
            (root / "leak.py").write_text(f"x = 1\nV = '{secret}'\n", encoding="utf-8")
            git(root, "add", "leak.py")
            result = scan(root)
            check(f"staged {label} blocks", result.returncode != 0, True)
            check(f"staged {label} names the file", "leak.py" in result.stderr, True)
            check(f"staged {label} does not echo the secret", secret in result.stderr + result.stdout, False)
        (root / "leak.py").write_text(f"x = 1\nV = 'ta{SK}'\n", encoding="utf-8")
        git(root, "add", "leak.py")
        check("sk- inside a word passes", scan(root).returncode, 0)

        # Non-UTF-8 text (Latin-1, CP949) must not crash the scan; CR-only line ends must not hide a line.
        git(root, "rm", "-q", "--cached", "leak.py")
        (root / "latin1.txt").write_bytes("café crème\n".encode("latin-1"))
        git(root, "add", "latin1.txt")
        result = scan(root)
        check("Latin-1 file without secret passes", (result.returncode, result.stderr), (0, ""))
        (root / "latin1.txt").write_bytes(f"café\nK = '{AWS}'\n".encode("latin-1"))
        git(root, "add", "latin1.txt")
        check("Latin-1 file with secret blocks", "latin1.txt:2: aws-access-key" in scan(root).stderr, True)
        git(root, "rm", "-q", "--cached", "latin1.txt")
        (root / "cr.txt").write_bytes(f"x = 1\rK = '{AWS}'\r".encode("ascii"))
        git(root, "add", "cr.txt")
        result = scan(root)
        check("CR-only file with secret blocks", result.returncode != 0, True)
        check("CR-only file with secret names the file", "cr.txt" in result.stderr, True)

    if failures:
        print("FAIL: secret-scan")
        for f in failures:
            print(f"- {f}")
        return 1
    print("PASS: secret-scan tests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
