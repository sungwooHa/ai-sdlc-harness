#!/usr/bin/env python3
"""Regression tests for scripts/check-agent-harness.py.

A minimal fixture repository passes: ignored files (.husky/_ shims, an ignored script with Hangul),
a personal `local-*` skill and Hangul under scripts/test/ do not count. Each mutation below breaks
exactly one of the six checks and must fail with that check's code and no other.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

CHECK = Path(__file__).resolve().parents[1] / "check-agent-harness.py"
CONFIG = {
    "always_on_max_lines": 3,
    "skills": {
        "root": ".agents/skills", "claude_mirror": ".claude/skills", "local_prefix": "local-",
        "adapters": {"map": {"x-intent": ["grilling"]}},
    },
    "hook_intents": [
        {"id": "guard", "event": "PreToolUse", "matcher": "Edit|Bash", "script": "scripts/guard.py"},
        {"id": "scan", "event": "pre-commit", "script": "scripts/scan.py"},
    ],
}


def command(script: str) -> dict:
    return {"type": "command", "command": f'python3 "$CLAUDE_PROJECT_DIR"/{script} --repo-root "$CLAUDE_PROJECT_DIR"'}


SETTINGS = {"hooks": {"PreToolUse": [
    {"matcher": "Edit", "hooks": [command("scripts/guard.py")]},
    {"matcher": "Bash", "hooks": [command("scripts/guard.py")]},
]}}
PRE_COMMIT = '#!/usr/bin/env sh\n# Secret scan.\npython3 "$(git rev-parse --show-toplevel)/scripts/scan.py" --staged\n'
PLAYBOOK_MAP = (
    "| S3.6 | `scripts/guard.py`, `scripts/scan.py`, `.husky/pre-commit` |\n"
    "| S1.1 | `.agents/skills/x-intent/`, `.agents/skills/grilling/` |\n"
    "| B5 | `docs/standards/PLAYBOOK_MAP.md`, `.claude/agents/verifier.md` |\n"
)
GRILLING = "---\nname: grilling\ndisable-model-invocation: true\n---\n# grilling\n"


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build(root: Path) -> None:
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    write(root, ".agents/harness.json", json.dumps(CONFIG))
    write(root, ".claude/settings.json", json.dumps(SETTINGS))
    write(root, ".husky/pre-commit", PRE_COMMIT)
    write(root, ".husky/_/.gitignore", "*\n")
    write(root, ".husky/_/pre-push", "# husky shim, ignored\n")
    write(root, ".gitignore", "scripts/tmp/\n")
    write(root, "scripts/tmp/notes.py", "# 무시된 파일\n")
    write(root, "scripts/guard.py", "print('guard')\n")
    write(root, "scripts/scan.py", "print('scan')\n")
    write(root, "scripts/test/guard.test.py", "# 테스트 파일은 한글을 써도 된다\n")
    write(root, ".agents/skills/x-intent/SKILL.md", "---\nname: x-intent\n---\n# x-intent\n")
    write(root, ".agents/skills/grilling/SKILL.md", GRILLING)
    for name in ("x-intent", "grilling"):
        (root / ".claude/skills" / name).parent.mkdir(parents=True, exist_ok=True)
        (root / ".claude/skills" / name).symlink_to(f"../../.agents/skills/{name}", target_is_directory=True)
    # personal skill: real directory under the mirror, symlink under .agents/skills
    write(root, ".claude/skills/local-mine/SKILL.md", "---\nname: local-mine\n---\n")
    (root / ".agents/skills/local-mine").symlink_to("../../.claude/skills/local-mine", target_is_directory=True)
    write(root, "AGENTS.md", "# contract\n\nthree lines\n")
    write(root, "docs/standards/PLAYBOOK_MAP.md", PLAYBOOK_MAP)
    write(root, ".claude/agents/verifier.md", "# verifier\n")


def copy_skill(root: Path) -> None:
    (root / ".claude/skills/grilling").unlink()
    write(root, ".claude/skills/grilling/SKILL.md", GRILLING)


def undeclared_git_hook(root: Path) -> None:  # named in the map, so only the declaration is missing
    write(root, ".husky/commit-msg", "exit 0\n")
    write(root, "docs/standards/PLAYBOOK_MAP.md", PLAYBOOK_MAP + "| S5.2 | `.husky/commit-msg` |\n")


# (label, expected code, mutation)
MUTATIONS = [
    ("1 matcher wired for Edit only", "hook_matcher",
     lambda r: write(r, ".claude/settings.json", json.dumps({"hooks": {"PreToolUse": SETTINGS["hooks"]["PreToolUse"][:1]}}))),
    ("1 pre-commit line commented out", "git_hook",
     lambda r: write(r, ".husky/pre-commit", PRE_COMMIT.replace("python3", "# python3"))),
    ("1 undeclared script wired", "hook_undeclared",
     lambda r: write(r, ".claude/settings.json", json.dumps(
         {"hooks": {**SETTINGS["hooks"], "Stop": [{"hooks": [command("scripts/extra.py")]}]}}))),
    ("1 undeclared git hook", "hook_undeclared", undeclared_git_hook),
    ("1 declared script missing", "hook_script", lambda r: (r / "scripts/scan.py").unlink()),
    ("2 mirror entry missing", "skill_mirror", lambda r: (r / ".claude/skills/grilling").unlink()),
    ("2 mirror entry is a copy", "skill_mirror", copy_skill),
    ("3 adapter target model-invocable", "adapter_target",
     lambda r: write(r, ".agents/skills/grilling/SKILL.md", GRILLING.replace("disable-model-invocation: true\n", ""))),
    ("4 AGENTS.md over the limit", "always_on", lambda r: write(r, "AGENTS.md", "1\n2\n3\n4\n")),
    ("5 agent missing from PLAYBOOK_MAP", "playbook_map",
     lambda r: write(r, "docs/standards/PLAYBOOK_MAP.md", PLAYBOOK_MAP.replace(", `.claude/agents/verifier.md`", ""))),
    ("6 Hangul in a non-test script", "hangul", lambda r: write(r, "scripts/guard.py", "print('안녕')\n")),
]


def run(root: Path) -> tuple[int, str, set[str]]:
    done = subprocess.run([sys.executable, str(CHECK), "--repo-root", str(root)], capture_output=True, text=True)
    return done.returncode, done.stdout + done.stderr, set(re.findall(r"^- \[(\w+)\]", done.stdout, re.M))


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir) / "pass"
        build(root)
        code, out, codes = run(root)
        if code != 0 or not out.startswith("PASS"):
            failures.append(f"passing fixture: exit {code}\n{out}")
        for index, (label, expected, mutate) in enumerate(MUTATIONS):
            root = Path(temp_dir) / f"fail{index}"
            build(root)
            mutate(root)
            code, out, codes = run(root)
            if code != 1 or codes != {expected}:
                failures.append(f"{label}: expected exit 1 with only [{expected}], got exit {code}\n{out}")
    for failure in failures:
        print(f"FAIL {failure}")
    print(f"{'FAIL' if failures else 'PASS'}: check-agent-harness tests ({len(MUTATIONS) + 1} fixtures)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
