#!/usr/bin/env python3
"""Smoke tests for scripts/check-agent-harness.py against the v2 manifest.

A minimal fixture repo must pass; dropping the shared-policy import from the
Claude entrypoint must fail with a non-zero exit code.
"""

from __future__ import annotations

import json
import re
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
            # the declared path exactly, not a substring of another path
            ("husky runs another directory's copy", "python3 apps/web/scripts/guard.py --staged", {}, True),
            ("husky runs a backup copy", 'python3 "$(git rev-parse --show-toplevel)/scripts/guard.py.bak"', {}, True),
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

        # The reverse direction: every root `scripts/…` path a host file runs (Claude/Codex JSON under
        # its event key, a husky file under its own name) must belong to an intent that lists that host
        # file and that event. One script used by two intents is told apart by host_files.
        declared = [
            {"id": "guard_runtime", "event": "Stop|PreToolUse", "required_scripts": ["scripts/guard.py"],
             "host_files": {"claude": ".claude/settings.json"}},
            {"id": "guard_precommit", "event": "pre-commit", "required_scripts": ["scripts/guard.py"],
             "host_files": {"husky": ".husky/pre-commit"}},
            {"id": "shim", "event": "SessionStart", "required_scripts": ["scripts/harness/shim.sh"],
             "host_files": {"claude": ".claude/settings.json"}},
        ]
        claude_hooks = {
            "SessionStart": [{"hooks": [{"type": "command", "command": 'bash "$CLAUDE_PROJECT_DIR"/scripts/harness/shim.sh'}]}],
            "Stop": [{"hooks": [{"type": "command", "command": 'python3 "$CLAUDE_PROJECT_DIR"/scripts/guard.py'}]}],
            "PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "python3 scripts/guard.py"}]}],
        }
        husky = (
            'python3 "$(git rev-parse --show-toplevel)/scripts/guard.py" --staged\n'
            '# "$(git rev-parse --show-toplevel)/scripts/commented-out.sh"\n'
            'sh apps/web/scripts/lint.sh\n'
        )
        codex_line = "bash -lc 'repo=\"$(git rev-parse --show-toplevel)\"; exec python3 \"$repo/scripts/{}\"'"
        for label, intents, hooks, husky_files, codex_script, expect in (
            ("declared", declared, claude_hooks, {"pre-commit": husky}, None, {}),
            # migration-check.sh is wired in husky without a declaration (a real case); guard.py is
            # declared for Claude and husky but also wired in Codex; shim2.sh hides under a subfolder.
            ("undeclared", declared,
             {**claude_hooks, "SessionStart": [{"hooks": [
                 {"type": "command", "command": 'bash "$CLAUDE_PROJECT_DIR"/scripts/harness/shim.sh'},
                 {"type": "command", "command": 'bash "$CLAUDE_PROJECT_DIR"/scripts/harness/shim2.sh'}]}]},
             {"pre-commit": husky + 'sh "$(git rev-parse --show-toplevel)/scripts/migration-check.sh"\n'},
             "guard.py",
             {"undeclared_hook": {(".husky/pre-commit", "scripts/migration-check.sh"),
                                  (".claude/settings.json", "scripts/harness/shim2.sh"),
                                  (".codex/hooks.json", "scripts/guard.py")}}),
            # guard.py declared on Stop|PreToolUse but also wired on PostToolUse; a husky intent that
            # says pre-commit while its host file is .husky/pre-push.
            ("event mismatch",
             declared + [{"id": "push_guard", "event": "pre-commit", "required_scripts": ["scripts/push.sh"],
                          "host_files": {"husky": ".husky/pre-push"}}],
             {**claude_hooks, "PostToolUse": [{"hooks": [{"type": "command", "command": "python3 scripts/guard.py"}]}]},
             {"pre-commit": husky, "pre-push": 'sh "$(git rev-parse --show-toplevel)/scripts/push.sh"\n'},
             None,
             {"hook_event_mismatch": {(".claude/settings.json", "scripts/guard.py"),
                                      (".husky/pre-push", "scripts/push.sh")},
              # and the forward direction per event: push_guard is not run on its declared pre-commit
              "unwired_hook_intent": {(".husky/pre-push", "scripts/push.sh")}}),
        ):
            root = Path(temp_dir) / f"two-way-{label.replace(' ', '-')}"
            root.mkdir()
            build_fixture(root, f"{IMPORT_LINE}\n")
            manifest = dict(MANIFEST, shared_hook_intents=intents)
            (root / ".agents/harness.yaml").write_text(json.dumps(manifest), encoding="utf-8")
            for rel in ("scripts/guard.py", "scripts/harness/shim.sh", "scripts/push.sh"):
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                (root / rel).write_text("echo ok\n", encoding="utf-8")
            (root / ".claude/settings.json").write_text(json.dumps({"hooks": hooks}), encoding="utf-8")
            (root / ".husky").mkdir()
            for name, body in husky_files.items():
                (root / ".husky" / name).write_text(f"#!/usr/bin/env sh\n{body}", encoding="utf-8")
            if codex_script:
                (root / ".codex").mkdir()
                codex = {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": codex_line.format(codex_script)}]}]}}
                (root / ".codex/hooks.json").write_text(json.dumps(codex), encoding="utf-8")
            code, out = run(root)
            payload = json.loads(out)
            wiring_codes = ("undeclared_hook", "hook_event_mismatch", "unwired_hook_intent")
            found = {c: {(e["path"], s) for e in payload["errors"] if e["code"] == c
                         for s in re.findall(r"scripts/[\w./-]*\w", e["message"])[:1]} for c in wiring_codes}
            for c in wiring_codes:
                assert found[c] == expect.get(c, set()), f"{label}: {c} expected {expect.get(c, set())}, errors={payload['errors']}"
            assert (code == 1) == bool(expect), f"{label}: exit={code}, errors={payload['errors']}"

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

        # A personal skill (`local-<name>`) is a real directory under .claude/skills with a relative
        # symlink in .agents/skills. skills.local_prefix makes both checker spots skip it: the mirror
        # check and the content scan (a retired-root reference inside the skill). Without it, both fail.
        # A personal skill that got committed is not personal any more: the skip must not hide it.
        for label, with_prefix, tracked in (("prefix", True, False), ("no-prefix", False, False), ("tracked", True, True)):
            root = Path(temp_dir) / f"local-skill-{label}"
            root.mkdir()
            build_fixture(root, f"{IMPORT_LINE}\n")
            manifest = json.loads(json.dumps(MANIFEST))
            manifest["documentation_layout"] = {"retired_roots": ["docs/retired"]}
            if with_prefix:
                manifest["skills"]["local_prefix"] = "local-"
            (root / ".agents/harness.yaml").write_text(json.dumps(manifest), encoding="utf-8")
            (root / ".claude/skills/local-demo").mkdir()
            (root / ".claude/skills/local-demo/SKILL.md").write_text(
                "# local demo\nNotes live in docs/retired/notes.md\n", encoding="utf-8"
            )
            (root / ".agents/skills/local-demo").symlink_to("../../.claude/skills/local-demo", target_is_directory=True)
            if tracked:
                subprocess.run(["git", "init", "-q"], cwd=root, check=True)
                subprocess.run(["git", "add", ".claude/skills/local-demo/SKILL.md"], cwd=root, check=True)
            code, out = run(root)
            payload = json.loads(out)
            codes = {item["code"] for item in payload["errors"]}
            if tracked:
                assert code == 1 and "tracked_local_skill" in codes, f"{label}: exit={code}, errors={payload['errors']}"
            elif with_prefix:
                assert code == 0 and payload["errors"] == [], f"{label}: exit={code}, errors={payload['errors']}"
            else:
                assert code == 1, f"{label}: exit={code}"
                assert {"claude_skill_not_symlink", "retired_root_reference"} <= codes, f"{label}: errors={payload['errors']}"

        # agreement_gate lists are data the gate trusts: argv prefixes or exact argv without wildcards,
        # named subagents, and a branch pattern that compiles.
        browser = {"artifact_dir": "$TMPDIR/demo-qa", "global_flags": {"--json": "", "--session": "[a-z]+"},
                   "commands": {"snapshot": {"flags": {"-i": ""}}, "set viewport": {}, "pdf": {"args": ["path"]},
                                "screenshot": {"args": ["path?"], "flags": {"-o": "path"}}}}
        gate = {"enabled": True, "allowed_subagents": ["Explore"], "read_only_commands": [["git", "status"]],
                "branch_pattern": "feature/[a-z0-9-]+(/[a-z0-9-]+)*", "agent_browser": browser}
        mismatches = []
        for label, change, expect_error in (
            ("valid", {}, False),
            ("missing", {"read_only_commands": None}, True),
            ("wildcard", {"read_only_commands": [["git", "*"]]}, True),
            ("empty prefix", {"read_only_commands": [[]]}, True),
            ("unnamed subagent", {"allowed_subagents": [""]}, True),
            ("bad pattern", {"branch_pattern": "feature/("}, True),
            # agent_browser: the gate trusts these shapes, so a typo must fail here (B1)
            ("browser missing", {"agent_browser": None}, True),
            ("browser dir in repo", {"agent_browser": {**browser, "artifact_dir": "docs/qa"}}, True),
            ("browser dir not tmp", {"agent_browser": {**browser, "artifact_dir": "/var/tmp/qa"}}, True),
            ("browser bad value regex", {"agent_browser": {**browser, "global_flags": {"--session": "("}}}, True),
            ("browser flag without dash", {"agent_browser": {**browser, "global_flags": {"json": ""}}}, True),
            ("browser bad slot", {"agent_browser": {**browser, "commands": {"pdf": {"args": ["file"]}}}}, True),
            ("browser option as command", {"agent_browser": {**browser, "commands": {"--cdp": {}}}}, True),
            # M2: a one-token entry opens every subcommand and argument of that program; only a reviewed one passes
            ("whole git unreviewed", {"read_only_commands": [["git"]]}, True),
            ("whole interpreter unreviewed", {"read_only_commands": [["python3"]]}, True),
            ("whole program reviewed", {"read_only_commands": [["make"]], "reviewed_whole_programs": ["make"]}, False),
            ("reviewed list malformed", {"reviewed_whole_programs": "make"}, True),
            # N2: an entry naming a script matches its whole argv ({"exact": [...]}), never a prefix
            ("script as prefix", {"read_only_commands": [["python3", "scripts/check.py"]]}, True),
            ("wrapper as prefix", {"read_only_commands": [["./gradlew", "tasks"]]}, True),
            ("script exact", {"read_only_commands": [{"exact": ["python3", "scripts/check.py", "--format", "text"]}]}, False),
            ("exact empty", {"read_only_commands": [{"exact": []}]}, True),
            ("exact extra key", {"read_only_commands": [{"exact": ["git", "status"], "prefix": True}]}, True),
            ("exact wildcard", {"read_only_commands": [{"exact": ["git", "*"]}]}, True),
            # V2: a script runner plus a script alias or module passes later arguments to it, so it is exact too
            ("runner script as prefix", {"read_only_commands": [["pnpm", "check:harness"]]}, True),
            ("npm run as prefix", {"read_only_commands": [["npm", "run", "check"]]}, True),
            ("python module as prefix", {"read_only_commands": [["python3", "-m", "pkg"]]}, True),
            ("runner script exact", {"read_only_commands": [{"exact": ["pnpm", "check:harness"]}]}, False),
            ("bare runner reviewed", {"read_only_commands": [["pnpm"]], "reviewed_whole_programs": ["pnpm"]}, False),
        ):
            root = Path(temp_dir) / f"gate-{label.replace(' ', '-')}"
            root.mkdir()
            build_fixture(root, f"{IMPORT_LINE}\n")
            manifest = json.loads(json.dumps(MANIFEST))
            manifest["agreement_gate"] = {k: v for k, v in {**gate, **change}.items() if v is not None}
            (root / ".agents/harness.yaml").write_text(json.dumps(manifest), encoding="utf-8")
            code, out = run(root)
            payload = json.loads(out)
            errors = [item for item in payload["errors"] if item["code"] == "agreement_gate_lists"]
            if bool(errors) != expect_error or (code == 1) != expect_error:
                mismatches.append((label, expect_error, code, payload["errors"]))
        assert not mismatches, mismatches

    print("PASS: check-agent-harness smoke tests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
