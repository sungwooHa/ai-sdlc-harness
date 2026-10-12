#!/usr/bin/env python3
"""Regression tests for scripts/commit-msg-gate.py and its .husky/commit-msg wiring.

First line: checked against `commit_message.format` unless that is still a template placeholder;
git-written first lines (Merge branch/branches/pull request/remote-tracking branch/tag/commit, Revert ",
Reapply ", fixup!, squash!, amend!) pass; a comment line first is refused. Trailers: checked always; only
`allowed_trailers` pass while `forbid_other_trailers` is on (the default).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
GATE = REPO / "scripts/commit-msg-gate.py"
TYPES = ["feat", "fix", "docs", "style", "refactor", "test", "chore"]
BRACKET = "{type}: [{모듈명}] {변경 내용}"


def config(**commit_message: object) -> dict:
    return {"version": 2, "commit_message": commit_message} if commit_message else {"version": 2}


def gate(root: Path, manifest: dict, message: str) -> subprocess.CompletedProcess[str]:
    (root / ".agents").mkdir(parents=True, exist_ok=True)
    (root / ".agents/harness.yaml").write_text(json.dumps(manifest), encoding="utf-8")
    (root / "MSG").write_text(message, encoding="utf-8")
    return subprocess.run([sys.executable, str(GATE), "--repo-root", str(root), str(root / "MSG")],
                          capture_output=True, text=True, errors="replace")


def expect(root: Path, manifest: dict, message: str, ok: bool, label: str) -> None:
    result = gate(root, manifest, message)
    assert (result.returncode == 0) == ok, f"{label}: exit={result.returncode} stderr={result.stderr!r}"
    if not ok:
        assert "COMMIT_CONVENTION.md" in result.stderr, f"{label}: refusal must point to the convention"


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir) / "unit"
        bracket = config(format=BRACKET, types=TYPES, forbid_other_trailers=True, allowed_trailers=["Plan-Ref"])
        for message, ok in (
            ("feat: [Harness] 커밋 검사 추가\n", True),
            ("fix: 오타 수정\n", True),  # the bracketed field may be left out
            ("feat: [Harness] 검사 추가\n\n왜 필요한지 한 줄.\n\nPlan-Ref: 261008_00-harness-baseline\n", True),
            ("feat: x\n# Please enter the commit message.\n# Co-Authored-By: commented out\n", True),
            # A comment line first: -m/-F keep it (whitespace cleanup) as the stored subject, so it is
            # refused rather than skipped (`git commit -m "# wip" -m "feat: x"`).
            ("# wip\n\nfeat: [x] y\n", False),
            ("\n# Write the message below.\nfeat: x\n", False),
            ("feat: x\n# ------------------------ >8 ------------------------\n\nCo-Authored-By: below scissors\n", True),
            ("Merge branch 'feature/x' into main\n", True),
            ("Merge branches 'a' and 'b'\n", True),
            ("Merge pull request #12 from org/feature-x\n", True),
            ("Merge remote-tracking branch 'origin/main'\n", True),
            ("Merge tag 'v1.0'\n", True),
            ("Merge commit '0123abc'\n", True),
            ('Revert "feat: x"\n\nThis reverts commit 0123abc.\n', True),
            ('Reapply "feat: x"\n\nThis reverts commit 0123abc.\n', True),  # git 2.43+: revert of a revert
            ("fixup! feat: x\n", True),
            ("squash! anything goes here\n", True),
            ("amend! feat: x\n\nfeat: x 고친 제목\n\nPlan-Ref: 261008_00-a\n", True),  # git commit --fixup=amend:<rev>
            ("Mergesort rewrite\n", False),  # only git's own merge subjects skip the format
            ("Merge stuff quickly\n", False),
            ("update stuff\n", False),
            ("feature: [x] y\n", False),
            ("Feat: y\n", False),
            ("feat:y\n", False),
            ("feat: \n", False),
            # The optional slot alone is not a summary: a summary cannot start with the slot's bracket.
            ("feat: [x]\n", False),
            ("feat: [Harness]\n", False),
            ("feat: [x] y\n", True),
            ("feat: y\n", True),
            ("feat: [Harness] x\n\nCo-Authored-By: Claude <noreply@anthropic.com>\n", False),
            ("feat: x\n\nPlan-Ref: 261008_00-a\nSigned-off-by: A <a@example.com>\n", False),
            ("Merge branch 'x'\n\nCo-authored-by: A <a@example.com>\n", False),  # trailers still checked
        ):
            expect(root, bracket, message, ok, f"bracket format: {message!r}")

        conventional = config(format="{type}({scope}): {description}", types=TYPES)
        for message, ok in (("feat(api): add x\n", True), ("feat: add x\n", True), ("feat(api) add x\n", False)):
            expect(root, conventional, message, ok, f"conventional format: {message!r}")

        # The template repository itself: the format is still a placeholder, so only trailers are checked.
        # Split so init-template.sh does not fill this literal along with the real placeholders.
        placeholder = config(format="__" + "COMMIT_FORMAT__", types=TYPES, forbid_other_trailers=True,
                             allowed_trailers=["Plan-Ref"])
        expect(root, placeholder, "update stuff\n", True, "placeholder skips the format")
        expect(root, placeholder, "update stuff\n\nPlan-Ref: x\n", True, "placeholder keeps Plan-Ref")
        expect(root, placeholder, "update stuff\n\nCo-Authored-By: A <a@example.com>\n", False, "placeholder keeps the trailer check")
        # Defaults without a commit_message section: no format, trailers other than Plan-Ref refused.
        expect(root, config(), "anything\n\nCo-Authored-By: A <a@example.com>\n", False, "default forbids trailers")
        expect(root, config(), "anything\n\nPlan-Ref: x\n", True, "default allows Plan-Ref")
        # The human decision slot: allow any trailer.
        expect(root, config(format=BRACKET, types=TYPES, forbid_other_trailers=False),
               "feat: x\n\nCo-Authored-By: A <a@example.com>\n", True, "trailers allowed when not forbidden")

        # End to end: the real .husky/commit-msg behind the shim ensure-husky.sh writes, with messages
        # git itself writes for merge and revert.
        repo = Path(temp_dir) / "e2e"
        (repo / "scripts/harness").mkdir(parents=True)
        (repo / ".husky").mkdir()
        shutil.copy(GATE, repo / "scripts/commit-msg-gate.py")
        shutil.copy(REPO / "scripts/harness/ensure-husky.sh", repo / "scripts/harness/ensure-husky.sh")
        shutil.copy(REPO / ".husky/commit-msg", repo / ".husky/commit-msg")
        (repo / ".husky/pre-commit").write_text("#!/usr/bin/env sh\nexit 0\n", encoding="utf-8")
        (repo / "package.json").write_text('{"scripts":{"prepare":"husky"}}\n', encoding="utf-8")
        (repo / ".agents").mkdir()
        (repo / ".agents/harness.yaml").write_text(json.dumps(bracket), encoding="utf-8")

        def git(*args: str) -> subprocess.CompletedProcess[str]:
            return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
                                  cwd=repo, capture_output=True, text=True, errors="replace")

        assert git("init", "-q", "-b", "main").returncode == 0
        subprocess.run(["bash", "scripts/harness/ensure-husky.sh", "--quiet"], cwd=repo, check=True)
        assert (repo / ".husky/_/commit-msg").is_file(), "ensure-husky.sh must write the commit-msg shim"
        git("add", "-A")
        assert git("commit", "-q", "-m", "update stuff").returncode != 0, "bad first line must be refused"
        assert git("commit", "-q", "-m", "chore: [harness] 시작").returncode == 0
        refused = git("commit", "-q", "--allow-empty", "-m", "feat: x", "-m", "Co-Authored-By: A <a@example.com>")
        assert refused.returncode != 0 and "Co-Authored-By" in refused.stderr, refused.stderr
        assert git("commit", "-q", "--allow-empty", "-m", "feat: x", "-m", "Plan-Ref: 261008_00-x").returncode == 0
        git("switch", "-q", "-c", "side")
        assert git("commit", "-q", "--allow-empty", "-m", "fix: 옆 가지").returncode == 0
        git("switch", "-q", "main")
        merged = git("merge", "--no-ff", "--no-edit", "side")
        assert merged.returncode == 0, f"git-written merge message must pass: {merged.stderr}"
        (repo / "f.txt").write_text("x\n", encoding="utf-8")
        git("add", "f.txt")
        assert git("commit", "-q", "-m", "feat: f 추가").returncode == 0
        reverted = git("revert", "--no-edit", "HEAD")
        assert reverted.returncode == 0, f"git-written revert message must pass: {reverted.stderr}"
        subjects = git("log", "--format=%s").stdout.splitlines()
        assert subjects[0].startswith('Revert "') and subjects[2].startswith("Merge "), subjects

    print("PASS: commit-msg gate (format, git-written first lines, trailers, husky wiring)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
