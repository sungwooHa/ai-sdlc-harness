#!/usr/bin/env python3
"""Smoke tests for scripts/check-agent-harness.py against the v2 manifest.

A minimal fixture repo must pass; dropping the shared-policy import from the
Claude entrypoint must fail with a non-zero exit code.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

CHECK = Path(__file__).resolve().parents[1] / "check-agent-harness.py"
IMPORT_LINE = "@AGENTS.md"

MANIFEST = {
    "version": 2,
    "layers": {"always_on": ["AGENTS.md", "CLAUDE.md"], "per_app": ["apps/frontend/AGENTS.md"]},
    "always_on_max_lines": 20,
    "per_app_max_lines": 20,
    "skills": {"root": ".agents/skills", "claude_mirror": ".claude/skills"},
    "ci": {"required_package_scripts": ["check:harness"]},
}


def build_fixture(root: Path, claude_entrypoint: str) -> None:
    (root / ".agents/skills/demo").mkdir(parents=True)
    (root / ".agents/skills/demo/SKILL.md").write_text("# demo\n", encoding="utf-8")
    (root / ".claude/skills").mkdir(parents=True)
    (root / ".claude/skills/demo").symlink_to("../../.agents/skills/demo", target_is_directory=True)
    (root / ".agents/harness.yaml").write_text(json.dumps(MANIFEST), encoding="utf-8")
    (root / "AGENTS.md").write_text("# policy\n", encoding="utf-8")
    (root / "CLAUDE.md").write_text(claude_entrypoint, encoding="utf-8")
    (root / "package.json").write_text(
        json.dumps({"scripts": {"check:harness": "python3 scripts/check-agent-harness.py --format text"}}),
        encoding="utf-8",
    )


def run(root: Path) -> tuple[int, str]:
    completed = subprocess.run(
        [sys.executable, str(CHECK), "--repo-root", str(root), "--format", "json"],
        capture_output=True,
        text=True,
        errors="replace",
    )
    return completed.returncode, completed.stdout


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir) / "pass"
        root.mkdir()
        build_fixture(root, f"{IMPORT_LINE}\n")
        code, out = run(root)
        payload = json.loads(out)
        assert code == 0, f"minimal fixture must pass, exit={code}, errors={payload['errors']}"
        assert payload["status"] == "passed"
        # per-app policy files are only a warning while apps are being migrated
        assert any(item["code"] == "missing_per_app" for item in payload["warnings"]), payload["warnings"]

        root = Path(temp_dir) / "fail"
        root.mkdir()
        build_fixture(root, "# no shared policy import\n")
        code, out = run(root)
        payload = json.loads(out)
        assert code == 1, f"missing {IMPORT_LINE} import must fail, exit={code}"
        assert any(item["code"] == "claude_entrypoint_import" for item in payload["errors"]), payload["errors"]

        # Hook wiring must be judged on the executable surface, not on a substring:
        # a commented-out husky line or a JSON string outside `command` is unwired.
        for label, husky_line, json_extra, expect_unwired in (
            ("wired", 'python3 "$(git rev-parse --show-toplevel)/scripts/guard.py" --staged', {}, False),
            ("husky commented out", '# python3 "$(git rev-parse --show-toplevel)/scripts/guard.py" --staged', {}, True),
            ("json mentions script outside command", "", {"note": "scripts/guard.py"}, True),
        ):
            root = Path(temp_dir) / f"wiring-{label.replace(' ', '-')}"
            root.mkdir()
            build_fixture(root, f"{IMPORT_LINE}\n")
            manifest = dict(MANIFEST)
            manifest["shared_hook_intents"] = [
                {"id": "guard_precommit", "event": "pre-commit", "required_scripts": ["scripts/guard.py"],
                 "host_files": {"husky": ".husky/pre-commit"}},
                {"id": "guard_stop", "event": "Stop", "required_scripts": ["scripts/guard.py"],
                 "host_files": {"claude": ".claude/settings.json"}},
            ]
            (root / ".agents/harness.yaml").write_text(json.dumps(manifest), encoding="utf-8")
            (root / "scripts").mkdir()
            (root / "scripts/guard.py").write_text("print('ok')\n", encoding="utf-8")
            (root / ".husky").mkdir()
            (root / ".husky/pre-commit").write_text(f"#!/usr/bin/env sh\n{husky_line}\n", encoding="utf-8")
            settings = {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "python3 scripts/guard.py"}]}]}}
            if json_extra:
                settings = {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "echo hi"}]}]}, **json_extra}
            (root / ".claude/settings.json").write_text(json.dumps(settings), encoding="utf-8")
            code, out = run(root)
            payload = json.loads(out)
            unwired = [item for item in payload["errors"] if item["code"] == "unwired_hook_intent"]
            if expect_unwired:
                assert unwired, f"{label}: expected unwired_hook_intent, errors={payload['errors']}"
            else:
                assert not unwired, f"{label}: unexpected unwired_hook_intent, errors={unwired}"

        # A vendored skill behind an adapter must stay callable by the Skill tool:
        # disable-model-invocation is an error; user-invocable: false or no flag at all passes.
        for label, frontmatter, expect_error in (
            ("locked", "disable-model-invocation: true", True),
            ("hidden", "user-invocable: false", False),
            ("bare", "", False),
        ):
            root = Path(temp_dir) / f"adapter-{label}"
            root.mkdir()
            build_fixture(root, f"{IMPORT_LINE}\n")
            manifest = json.loads(json.dumps(MANIFEST))
            manifest["skills"]["vendored"] = [{"source": "github.com/x/y", "skills": ["vend"]}]
            manifest["skills"]["adapters"] = {"map": {"demo-x": "vend"}}
            (root / ".agents/harness.yaml").write_text(json.dumps(manifest), encoding="utf-8")
            (root / ".agents/skills/vend").mkdir()
            (root / ".agents/skills/vend/SKILL.md").write_text(
                f"---\nname: vend\ndescription: d\n{frontmatter}\nmetadata:\n  source: https://x\n---\n# vend\n",
                encoding="utf-8",
            )
            (root / ".claude/skills/vend").symlink_to("../../.agents/skills/vend", target_is_directory=True)
            code, out = run(root)
            payload = json.loads(out)
            errors = [item for item in payload["errors"] if item["code"] == "adapter_target_not_invocable"]
            assert bool(errors) == expect_error, f"{label}: errors={payload['errors']}"
            assert (code == 1) == expect_error, f"{label}: exit={code}"

    print("PASS: check-agent-harness smoke tests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
