#!/usr/bin/env python3
"""Regression tests for local runtime artifact handling in the harness check (v2)."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "check-agent-harness.py"
SPEC = importlib.util.spec_from_file_location("check_agent_harness", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
HarnessCheck = MODULE.HarnessCheck

RETIRED = "docs/retired-root"


def test_local_runtime_paths_are_not_active_scan_surface() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        (root / ".codex/worktrees/old/docs").mkdir(parents=True)
        (root / ".claude/skills/.omc").mkdir(parents=True)
        (root / ".codex/config.toml").write_text(f"see {RETIRED}\n", encoding="utf-8")
        (root / ".codex/worktrees/old/docs/retired.md").write_text(f"see {RETIRED}\n", encoding="utf-8")
        (root / ".claude/skills/.omc/state.json").write_text(f"see {RETIRED}\n", encoding="utf-8")

        check = HarnessCheck(root)
        check.manifest = {
            "version": 2,
            "documentation_layout": {"retired_roots": [RETIRED]},
            "local_artifacts": {
                "scan_excluded_paths": [".codex/worktrees/**", ".claude/skills/.omc/**"],
            },
        }
        check._check_repo_wide_terms()

        paths = {finding.path for finding in check.errors}
        assert ".codex/config.toml" in paths, paths
        assert ".codex/worktrees/old/docs/retired.md" not in paths, paths
        assert ".claude/skills/.omc/state.json" not in paths, paths


def test_only_omc_is_symlink_check_exemption() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        (root / ".claude/skills/.omc").mkdir(parents=True)
        (root / ".claude/skills/plain-skill").mkdir(parents=True)
        (root / ".agents/skills/linked-skill").mkdir(parents=True)
        (root / ".agents/skills/linked-skill/SKILL.md").write_text("# linked\n", encoding="utf-8")
        (root / ".claude/skills/linked-skill").symlink_to(
            "../../.agents/skills/linked-skill", target_is_directory=True
        )

        check = HarnessCheck(root)
        check.manifest = {
            "version": 2,
            "skills": {"root": ".agents/skills", "claude_mirror": ".claude/skills"},
            "local_artifacts": {"claude_skill_symlink_exemptions": [".claude/skills/.omc"]},
        }
        check._check_skills()

        findings = {(finding.code, finding.path) for finding in check.errors}
        assert ("claude_skill_not_symlink", ".claude/skills/plain-skill") in findings, findings
        assert not any(path == ".claude/skills/.omc" for _, path in findings), findings
        assert not any(path == ".claude/skills/linked-skill" for _, path in findings), findings


if __name__ == "__main__":
    test_local_runtime_paths_are_not_active_scan_surface()
    test_only_omc_is_symlink_check_exemption()
    print("PASS: harness local artifact regression tests")
