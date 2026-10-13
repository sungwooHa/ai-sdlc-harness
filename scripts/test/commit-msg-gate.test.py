#!/usr/bin/env python3
"""Regression tests for scripts/commit-msg-gate.py and its .husky/commit-msg wiring.

First line: checked against `commit_message.format` unless that is still a template placeholder;
git-written first lines (Merge branch/branches/pull request/remote-tracking branch/tag/commit, Revert ",
Reapply ", fixup!, squash!, amend!) pass; a comment line first is refused. Trailers: checked always; only
`allowed_trailers` pass while `forbid_other_trailers` is on (the default), and then a `Co-Authored-By:` line
is refused anywhere git may store it unless `allowed_trailers` lists it. Only git's exact scissors line ends
the message, and a `---` line does not: the gate reads the trailers `git log` reads.
"""

from __future__ import annotations

import importlib.util
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
SCISSORS = "# ------------------------ >8 ------------------------"
SIGNED = "Signed-off-by: A <a@example.com>"


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
            # -m/-F keep the scissors line and what is below it, so a Co-Authored-By line there is stored.
            ("feat: x\n# ------------------------ >8 ------------------------\n\nCo-Authored-By: below scissors\n", False),
            # A --verbose diff below the scissors line is dropped; its lines start with +, - or a space.
            ("feat: x\n# ------------------------ >8 ------------------------\n# Do not modify or remove the line above.\n"
             "diff --git a/f b/f\n+Co-Authored-By: A <a@example.com>\n Co-Authored-By: B <b@example.com>\n", True),
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
            # Moved out of the trailers it is still stored: above Plan-Ref, or inside a prose paragraph.
            ("feat: x\n\nCo-Authored-By: C <c@example.com>\n\nPlan-Ref: 261008_00-a\n", False),
            ("feat: x\n\nCo-Authored-By: C <c@example.com>\n이 커밋은 함께 썼다.\n", False),
            ("feat: x\n\n본문에서 co-authored-by: 를 언급하는 문장은 막지 않는다.\n\nPlan-Ref: 261008_00-a\n", True),
            ("feat: x\n\nPlan-Ref: 261008_00-a\nSigned-off-by: A <a@example.com>\n", False),
            ("Merge branch 'x'\n\nCo-authored-by: A <a@example.com>\n", False),  # trailers still checked
            # Only git's exact scissors line ends the message (`wt_status_locate_end`: at the start or after LF,
            # ending in LF, comment char `#`). A look-alike is a comment line, and reading goes on below it.
            # CRLF and a trailing blank are refused even where git would have cut them: wrong on the blocking side.
            (f"feat: x\n\n{SCISSORS}\n\n{SIGNED}\n", True),
            (f"feat: x\n\n# - >8 x\n\n{SIGNED}\n", False),
            (f"feat: x\n\n{SCISSORS}\r\n\r\n{SIGNED}\r\n", False),
            (f"feat: x\n\n{SCISSORS} \n\n{SIGNED}\n", False),
            (f"feat: x\n\n{SCISSORS.replace('# -', '# ', 1)}\n\n{SIGNED}\n", False),  # one dash short
            # git log reads trailers below a `---` line; so does the gate (`--no-divider`).
            (f"feat: x\n\n---\n\n{SIGNED}\n", False),
            ("feat: x\n\n---\n\nPlan-Ref: 261008_00-a\n", True),
        ):
            expect(root, bracket, message, ok, f"bracket format: {message!r}")
        # A last paragraph that is only a URL or `Key: value` lines is read as trailers; the refusal says so.
        for body in ("https://github.com/o/r/issues/1", "Why: hooks were skipped", "Follow-up: 다음 묶음에서"):
            result = gate(root, bracket, f"fix: [x] y\n\n{body}\n")
            assert result.returncode == 1 and "read as trailers" in result.stderr, (body, result.stderr)
            assert "add a sentence" in result.stderr and "remove that trailer" not in result.stderr, (body, result.stderr)
        # A real trailer must be removed: the hint to add a sentence would keep it in the message.
        result = gate(root, bracket, "fix: [x] y\n\nCo-Authored-By: C <c@example.com>\n")
        assert result.returncode == 1 and "add a sentence" not in result.stderr, result.stderr
        assert "remove that trailer" in result.stderr, result.stderr
        expect(root, bracket, "fix: [x] y\n\nhttps://github.com/o/r/issues/1\n\nPlan-Ref: 261008_00-a\n", True,
               "a URL paragraph before Plan-Ref is body text")

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
        expect(root, config(format=BRACKET, types=TYPES, allowed_trailers=["Plan-Ref", "Co-authored-by"]),
               "feat: x\n\nCo-Authored-By: A <a@example.com>\n본문.\n", True, "a listed Co-Authored-By passes in the body")

        # Oracle: the trailers `git log` reads from the stored message (--cleanup=verbatim keeps all of it).
        spec = importlib.util.spec_from_file_location("commit_msg_gate", GATE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        scratch = Path(temp_dir) / "scratch"
        scratch.mkdir()

        def scratch_git(*args: str) -> subprocess.CompletedProcess[str]:
            return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
                                  cwd=scratch, capture_output=True, text=True, errors="replace")

        assert scratch_git("init", "-q", "-b", "main").returncode == 0
        for message in (f"feat: x\n\n{SCISSORS}\n\n{SIGNED}\n", f"feat: x\n\n# - >8 x\n\n{SIGNED}\n",
                        f"feat: x\n\n---\n\n{SIGNED}\n"):
            (Path(temp_dir) / "scratch.msg").write_text(message, encoding="utf-8")
            committed = scratch_git("commit", "-q", "--allow-empty", "--cleanup=verbatim", "-F", str(Path(temp_dir) / "scratch.msg"))
            assert committed.returncode == 0, committed.stderr
            stored = scratch_git("log", "-1", "--format=%(trailers:only)").stdout
            git_keys = [line.split(":", 1)[0] for line in stored.splitlines() if ":" in line]
            gate_keys = module.trailer_keys(module.stored_text(message))
            assert gate_keys == git_keys, f"gate reads {gate_keys}, git log reads {git_keys}: {message!r}"

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
        moved = git("commit", "-q", "--allow-empty", "-m", "feat: x", "-m", "Co-Authored-By: A <a@example.com>",
                    "-m", "Plan-Ref: 261008_00-x")
        assert moved.returncode != 0 and "Co-Authored-By" in moved.stderr, moved.stderr
        assert git("commit", "-q", "--allow-empty", "-m", "feat: x", "-m", "Plan-Ref: 261008_00-x").returncode == 0
        fake = git("commit", "-q", "--allow-empty", "-m", "feat: x", "-m", "# - >8 x", "-m", SIGNED)
        assert fake.returncode != 0 and "Signed-off-by" in fake.stderr, f"a look-alike scissors line hides nothing: {fake.stderr}"
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
