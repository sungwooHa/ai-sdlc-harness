#!/usr/bin/env python3
"""Read-only structural checks for the agent development harness (v2 layout).

The manifest (.agents/harness.yaml) is stored as JSON-compatible YAML so this
script runs in CI with only the Python standard library.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

MANIFEST_REL = ".agents/harness.yaml"
EXCLUDED_DIRS = {".git", "node_modules", ".venv", "dist", "build", "target", ".gradle", "__pycache__"}
TEXT_SUFFIXES = {
    ".md", ".mdc", ".json", ".yaml", ".yml", ".toml", ".py", ".sh", ".ts", ".tsx",
    ".js", ".mjs", ".cjs", ".txt", ".disabled", "",
}
REPO_WIDE_SCAN_TARGETS = (
    "AGENTS.md", "CLAUDE.md", ".agents", ".claude", ".codex", ".husky", "scripts",
    "package.json", "docs",
)
# Paths of scripts and generators this repo has removed; a surviving reference is stale.
# Fill it when you delete a harness script that other files may still name.
REMOVED_SCRIPT_REFS: tuple[str, ...] = ()
USER_PATH_PATTERNS = (
    re.compile(r"/Users/[A-Za-z0-9._-]+/"),
    re.compile(r"/home/[A-Za-z0-9._-]+/"),
    re.compile(r"[A-Za-z]:[\\/]+Users[\\/]+"),
)
# This file names the removed scripts on purpose (see REMOVED_SCRIPT_REFS).
SELF_REL = "scripts/check-agent-harness.py"


@dataclass
class Finding:
    severity: str
    code: str
    path: str
    message: str


class HarnessCheck:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.errors: list[Finding] = []
        self.warnings: list[Finding] = []
        self.manifest: dict[str, Any] = {}

    # ---------------------------------------------------------------- runner
    def run(self) -> None:
        self.manifest = self._load_manifest()
        if not self.manifest:
            return
        if self.manifest.get("version") != 2:
            self._error("manifest_version", MANIFEST_REL, "manifest version must be 2")
            return
        self._check_always_on()
        self._check_per_app()
        self._check_skills()
        self._check_adapter_invocability()
        self._check_host_adapters()
        self._check_protected_paths()
        self._check_documentation_layout()
        self._check_artifact_chain()
        self._check_repo_wide_terms()
        self._check_ci()

    def _load_manifest(self) -> dict[str, Any]:
        path = self.repo_root / MANIFEST_REL
        if not path.is_file():
            self._error("missing_manifest", MANIFEST_REL, "harness manifest is missing")
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            self._error("invalid_manifest", MANIFEST_REL, f"manifest must be JSON-compatible YAML: {exc}")
            return {}
        if not isinstance(data, dict):
            self._error("invalid_manifest", MANIFEST_REL, "manifest root must be an object")
            return {}
        return data

    # ---------------------------------------------------------------- layers
    def _check_always_on(self) -> None:
        layers = self.manifest.get("layers", {})
        max_lines = int(self.manifest.get("always_on_max_lines", 0) or 0)
        for rel in layers.get("always_on", []):
            path = self.repo_root / rel
            if not path.is_file():
                self._error("missing_always_on", rel, "always-on policy file is missing")
                continue
            self._check_line_budget(rel, path, max_lines, "always_on_max_lines")
        entry = self.manifest.get("host_adapters", {}).get("policy", {}).get("claude_entrypoint", "CLAUDE.md")
        must_import = self.manifest.get("host_adapters", {}).get("policy", {}).get(
            "claude_entrypoint_must_import", "@AGENTS.md"
        )
        entry_path = self.repo_root / entry
        if entry_path.is_file() and must_import not in self._read_text(entry_path):
            self._error("claude_entrypoint_import", entry, f"must import the shared policy via `{must_import}`")

    def _check_per_app(self) -> None:
        max_lines = int(self.manifest.get("per_app_max_lines", 0) or 0)
        for rel in self.manifest.get("layers", {}).get("per_app", []):
            path = self.repo_root / rel
            if not path.is_file():
                self._warn("missing_per_app", rel, "per-app AGENTS.md is not written yet")
                continue
            self._check_line_budget(rel, path, max_lines, "per_app_max_lines")
            mirror = path.parent / "CLAUDE.md"
            mirror_rel = self._rel(mirror)
            if not mirror.is_symlink():
                self._warn("missing_per_app_claude_mirror", mirror_rel, "expected a symlink to AGENTS.md")
            elif os.readlink(mirror) != "AGENTS.md":
                self._error("bad_per_app_claude_mirror", mirror_rel, "symlink target must be AGENTS.md")

    def _check_line_budget(self, rel: str, path: Path, max_lines: int, key: str) -> None:
        if not max_lines:
            return
        count = len(self._read_text(path).splitlines())
        if count > max_lines:
            self._error("line_budget", rel, f"{count} lines exceeds {key}={max_lines}")

    # ---------------------------------------------------------------- skills
    def _check_skills(self) -> None:
        skills = self.manifest.get("skills", {})
        root_rel = skills.get("root", ".agents/skills")
        mirror_rel = skills.get("claude_mirror", ".claude/skills")
        root = self.repo_root / root_rel
        if not root.is_dir():
            self._error("missing_skill_root", root_rel, "skill root directory is missing")
            return
        exemptions = set(self.manifest.get("local_artifacts", {}).get("claude_skill_symlink_exemptions", []))

        names = sorted(p.name for p in root.iterdir() if p.is_dir())
        for name in names:
            skill_dir = root / name
            if not ((skill_dir / "SKILL.md").is_file() or (skill_dir / "SKILL.md.disabled").is_file()):
                self._error(
                    "missing_skill_md",
                    f"{root_rel}/{name}",
                    "skill directory needs SKILL.md or SKILL.md.disabled",
                )

        mirror_root = self.repo_root / mirror_rel
        mirrored: set[str] = set()
        if not mirror_root.is_dir():
            self._error("missing_skill_mirror_root", mirror_rel, "claude skill mirror directory is missing")
        else:
            for entry in sorted(mirror_root.iterdir(), key=lambda p: p.name):
                rel = f"{mirror_rel}/{entry.name}"
                if rel in exemptions:
                    continue
                mirrored.add(entry.name)
                expected = f"../../{root_rel}/{entry.name}"
                if not entry.is_symlink():
                    self._error("claude_skill_not_symlink", rel, f"must be a symlink to {expected}")
                elif os.readlink(entry) != expected:
                    self._error("claude_skill_bad_symlink", rel, f"symlink target must be {expected}")
        for name in names:
            if name not in mirrored:
                self._error("missing_claude_skill_symlink", f"{mirror_rel}/{name}", "mirror symlink is missing")

        declared_disabled = {}
        for entry in skills.get("disabled", []):
            path = entry.get("path", "")
            declared_disabled[path] = entry
            if not (self.repo_root / path).is_file():
                self._error("missing_disabled_skill", path, "declared disabled skill file is missing")
            if not entry.get("reason") or not entry.get("replacement"):
                self._error("incomplete_disabled_skill", path or MANIFEST_REL, "needs reason and replacement")
        for name in names:
            rel = f"{root_rel}/{name}/SKILL.md.disabled"
            if (self.repo_root / rel).is_file() and rel not in declared_disabled:
                self._error("undeclared_disabled_skill", rel, "add it to skills.disabled with reason+replacement")

        for upstream, local in self._vendored_local_names().items():
            rel = f"{root_rel}/{local}/SKILL.md"
            path = self.repo_root / rel
            if not path.is_file():
                self._error("missing_vendored_skill", rel, "vendored skill is declared but missing")
                continue
            front = self._frontmatter(path)
            if "metadata:" not in front or "source:" not in front:
                self._warn(
                    "vendored_skill_provenance",
                    rel,
                    "frontmatter should carry metadata.source for vendored skills",
                )
            if local != upstream and f"name: {local}" not in front:
                self._error(
                    "vendored_skill_name_mismatch",
                    rel,
                    f"vendored as `{local}` but frontmatter name is not `{local}` (host would register `{upstream}`)",
                )

    def _vendored_local_names(self) -> dict[str, str]:
        """Upstream skill name -> local directory name for every declared vendored skill.

        Entries are upstream names, or {name, as} when vendored under a local name
        (e.g. upstream `code-review` collides with the Claude Code built-in)."""
        mapping: dict[str, str] = {}
        for bundle in self.manifest.get("skills", {}).get("vendored", []):
            for item in bundle.get("skills", []):
                if isinstance(item, dict):
                    upstream = item.get("name", "")
                    mapping[upstream] = item.get("as") or upstream
                else:
                    mapping[str(item)] = str(item)
        return mapping

    def _check_adapter_invocability(self) -> None:
        """A vendored skill behind a project adapter must stay callable by the Skill tool.

        The adapter (user-invoked) calls the vendored skill through the Skill tool; with
        `disable-model-invocation: true` the host refuses that call and the whole stage is dead.
        `user-invocable: false` hides the original from the slash menu instead; a skill with
        neither flag (e.g. `grilling`) is allowed — direct use is documented as permitted."""
        skills = self.manifest.get("skills", {})
        root_rel = skills.get("root", ".agents/skills")
        vendored_locals = set(self._vendored_local_names().values())
        for adapter, target in skills.get("adapters", {}).get("map", {}).items():
            if target not in vendored_locals:
                continue  # adapter over a project skill: not vendored, nothing to enforce here
            rel = f"{root_rel}/{target}/SKILL.md"
            path = self.repo_root / rel
            if not path.is_file():
                self._error("missing_adapter_target", rel, f"adapter `{adapter}` maps to a skill that has no SKILL.md")
                continue
            keys = [l.strip() for l in self._frontmatter(path).splitlines() if not l.strip().startswith("#")]
            if "disable-model-invocation: true" in keys:
                self._error(
                    "adapter_target_not_invocable",
                    rel,
                    f"reached through adapter `{adapter}` but disable-model-invocation: true refuses the Skill tool call; "
                    "use user-invocable: false (vendor-skills.py rewrites it on import)",
                )

    def _frontmatter(self, path: Path) -> str:
        lines = self._read_text(path).splitlines()
        if not lines or lines[0].strip() != "---":
            return ""
        for index, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                return "\n".join(lines[1:index])
        return ""

    # --------------------------------------------------------- host adapters
    def _check_host_adapters(self) -> None:
        adapters = self.manifest.get("host_adapters", {})
        for host, adapter in adapters.items():
            if host == "policy" or not isinstance(adapter, dict):
                continue
            for rel in adapter.get("required_files", []):
                if not (self.repo_root / rel).is_file():
                    self._error("missing_host_file", rel, f"required {host} adapter file is missing")
            for rel in adapter.get("absolute_path_scan_files", []):
                path = self.repo_root / rel
                if not path.is_file():
                    continue
                hits = sorted({m for p in USER_PATH_PATTERNS for m in p.findall(self._read_text(path))})
                if hits:
                    self._error(
                        "user_absolute_path",
                        rel,
                        f"replace user-specific absolute paths with <repo-root> ({', '.join(hits[:3])})",
                    )

        for rel in (".claude/settings.json", ".codex/hooks.json"):
            path = self.repo_root / rel
            if not path.is_file():
                continue
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                self._error("invalid_host_config", rel, f"must be valid JSON: {exc}")

        for intent in self.manifest.get("shared_hook_intents", []):
            intent_id = intent.get("id", "?")
            scripts = intent.get("required_scripts", [])
            for script in scripts:
                if not (self.repo_root / script).is_file():
                    self._error("missing_hook_script", script, f"required by hook intent {intent_id}")
            for host, host_file in intent.get("host_files", {}).items():
                host_path = self.repo_root / host_file
                if not host_path.is_file():
                    self._error("missing_hook_host_file", host_file, f"hook intent {intent_id} declares this host file")
                    continue
                text = self._hook_surface(host_path)
                for script in scripts:
                    if script not in text:
                        self._error(
                            "unwired_hook_intent",
                            host_file,
                            f"hook intent {intent_id} ({host}) does not reference {script}",
                        )

    def _hook_surface(self, host_path: Path) -> str:
        """The part of a host file that actually runs hooks.

        A plain substring test passed when the invocation was commented out but
        the script name survived in a comment — the "documented, not enforced"
        phantom this repo has already been bitten by. JSON adapters contribute
        only their `command` strings; shell hooks contribute only lines that are
        not comments.
        """
        text = self._read_text(host_path)
        if host_path.suffix == ".json":
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                return text  # reported separately as invalid_host_config
            commands: list[str] = []

            def walk(node: object) -> None:
                if isinstance(node, dict):
                    for key, value in node.items():
                        if key == "command" and isinstance(value, str):
                            commands.append(value)
                        else:
                            walk(value)
                elif isinstance(node, list):
                    for item in node:
                        walk(item)

            walk(data)
            return "\n".join(commands)
        return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))

    # ------------------------------------------------------ protected paths
    def _check_protected_paths(self) -> None:
        for index, entry in enumerate(self.manifest.get("protected_paths", [])):
            label = entry.get("id") or f"protected_paths[{index}]"
            if not entry.get("id"):
                self._error("protected_path_id", MANIFEST_REL, f"{label} needs an id")
            if not entry.get("globs"):
                self._error("protected_path_globs", MANIFEST_REL, f"{label} needs globs")
            if not entry.get("reason"):
                self._error("protected_path_reason", MANIFEST_REL, f"{label} needs a reason")

    # -------------------------------------------------- documentation layout
    def _check_documentation_layout(self) -> None:
        layout = self.manifest.get("documentation_layout", {})
        for rel in layout.get("active_roots", []):
            if not (self.repo_root / rel).is_dir():
                self._error("missing_active_root", rel, "active documentation root is missing")
        for rel in layout.get("retired_roots", []):
            if (self.repo_root / rel).exists():
                self._error("retired_root_present", rel, "retired documentation root must not exist")

        standards_files = set(layout.get("standards_root_files", []))
        standards_root = self.repo_root / "docs/standards"
        if standards_root.is_dir() and standards_files:
            present = {p.name for p in standards_root.iterdir() if p.is_file()}
            for name in sorted(present - standards_files):
                self._error(
                    "unexpected_standards_root_file",
                    f"docs/standards/{name}",
                    "docs/standards root allows only standards_root_files (move it into a subdirectory)",
                )
            for name in sorted(standards_files - present):
                self._error("missing_standards_root_file", f"docs/standards/{name}", "declared standards root file is missing")

        area_dirs = set(layout.get("knowledge_area_dirs", []))
        knowledge_root = self.repo_root / "docs/knowledge"
        if knowledge_root.is_dir() and area_dirs:
            for entry in sorted(knowledge_root.iterdir(), key=lambda p: p.name):
                if entry.is_dir() and entry.name not in area_dirs:
                    self._error(
                        "unexpected_knowledge_area",
                        f"docs/knowledge/{entry.name}",
                        f"knowledge areas are limited to {', '.join(sorted(area_dirs))}",
                    )

        for rel in layout.get("generated_knowledge_indexes", []):
            if not (self.repo_root / rel).is_file():
                self._error("missing_generated_index", rel, "generated knowledge index is missing")

        generator = layout.get("knowledge_index_generator")
        if generator:
            if not (self.repo_root / generator).is_file():
                self._error("missing_knowledge_generator", generator, "knowledge index generator is missing")
            else:
                code, output = self._run(["python3", generator, "--root", ".", "--check"])
                if code != 0:
                    for line in (output.splitlines() or ["failed"])[:5]:
                        self._error("stale_knowledge_index", generator, line)
        validator = layout.get("knowledge_frontmatter_validator")
        if validator and not (self.repo_root / validator).is_file():
            self._error("missing_knowledge_validator", validator, "knowledge frontmatter validator is missing")

    # ------------------------------------------------------- artifact chain
    def _check_artifact_chain(self) -> None:
        chain = self.manifest.get("artifact_chain", {})
        root = chain.get("root")
        if root and not (self.repo_root / root).is_dir():
            self._error("missing_artifact_root", root, "artifact chain root is missing")
        templates = chain.get("templates_dir")
        if not templates:
            return
        if not (self.repo_root / templates).is_dir():
            self._warn("missing_templates_dir", templates, "artifact chain templates directory is missing")
            return
        for document in chain.get("documents", []):
            rel = f"{templates}/{document}"
            if not (self.repo_root / rel).is_file():
                self._warn("missing_artifact_template", rel, "artifact chain template is missing")
        review = chain.get("review_policy")
        if review and not (self.repo_root / review).is_file():
            self._warn("missing_review_policy", review, "review policy document is missing")

        # Harness evals: behavioural regression cases run through `claude -p`. They cost
        # model usage so they are not part of test:harness, but the contract must know they
        # exist or nobody runs them and they rot.
        evals = self.manifest.get("evals", {})
        for key in ("cases", "runner", "readme"):
            rel = evals.get(key)
            if rel and not (self.repo_root / rel).is_file():
                self._error("missing_evals_file", rel, f"evals.{key} is declared but missing")
        cases = evals.get("cases")
        if cases and (self.repo_root / cases).is_file():
            for index, line in enumerate(self._read_text(self.repo_root / cases).splitlines(), start=1):
                if not line.strip():
                    continue
                try:
                    case = json.loads(line)
                except json.JSONDecodeError as exc:
                    self._error("invalid_eval_case", f"{cases}:{index}", f"not valid JSON: {exc}")
                    continue
                if not case.get("id") or not case.get("prompt") or not isinstance(case.get("expect"), dict):
                    self._error("invalid_eval_case", f"{cases}:{index}", "case needs id, prompt, and an expect object")

    # ----------------------------------------------------------- repo scans
    def _check_repo_wide_terms(self) -> None:
        layout = self.manifest.get("documentation_layout", {})
        # Only path-shaped retired roots are scanned; bare names ("plans", "feedback")
        # are ordinary words and would produce noise.
        retired_terms = [t for t in layout.get("retired_roots", []) if isinstance(t, str) and t.startswith("docs")]
        stale_names = [t for t in self.manifest.get("stale_project_names", []) if isinstance(t, str)]
        stale_surface = ("AGENTS.md", "CLAUDE.md", "docs/standards")

        for rel, text in self._scan_files():
            if rel in (MANIFEST_REL, SELF_REL):
                continue
            for term in retired_terms:
                if term in text:
                    self._error("retired_root_reference", rel, f"references retired documentation root `{term}`")
            for term in REMOVED_SCRIPT_REFS:
                if term in text:
                    self._error("removed_script_reference", rel, f"references removed harness path `{term}`")
            if rel.startswith(stale_surface):
                for term in stale_names:
                    if term in text:
                        self._error("stale_project_name", rel, f"uses stale project name `{term}`")

    def _scan_files(self) -> Iterable[tuple[str, str]]:
        excluded = self.manifest.get("local_artifacts", {}).get("scan_excluded_paths", [])
        excluded_prefixes = tuple(item.split("**")[0] for item in excluded if isinstance(item, str))
        # Per-app AGENTS.md files are the most-read layer; the artifact chain and
        # tracker config are agent-facing too. Scan them along with the static set.
        per_app = tuple(p for p in self.manifest.get("layers", {}).get("per_app", []) if isinstance(p, str))
        for target in REPO_WIDE_SCAN_TARGETS + per_app + ("docs/agents", "docs/changes"):
            base = self.repo_root / target
            if base.is_file():
                yield target, self._read_text(base)
                continue
            if not base.is_dir():
                continue
            for path in sorted(base.rglob("*")):
                if path.is_symlink() or not path.is_file():
                    continue
                if any(part in EXCLUDED_DIRS for part in path.parts):
                    continue
                if path.suffix not in TEXT_SUFFIXES:
                    continue
                rel = self._rel(path)
                if rel.startswith(excluded_prefixes):
                    continue
                yield rel, self._read_text(path)

    # ------------------------------------------------------------------- ci
    def _check_ci(self) -> None:
        ci = self.manifest.get("ci", {})
        package_path = self.repo_root / "package.json"
        if not package_path.is_file():
            self._error("missing_package_json", "package.json", "package.json is missing")
        else:
            try:
                scripts = json.loads(package_path.read_text(encoding="utf-8")).get("scripts", {})
            except (OSError, json.JSONDecodeError) as exc:
                self._error("invalid_package_json", "package.json", f"must be valid JSON: {exc}")
                scripts = {}
            for name in ci.get("required_package_scripts", []):
                if name not in scripts:
                    self._error("missing_package_script", "package.json", f"missing required script `{name}`")

        pipeline_rel = ci.get("pipeline_file")
        if not pipeline_rel:
            return
        pipeline = self.repo_root / pipeline_rel
        if not pipeline.is_file():
            self._warn("missing_pipeline", pipeline_rel, "declared CI pipeline definition is missing")
            return
        text = self._read_text(pipeline)
        for needle in ci.get("recommended_pipeline_substrings", []):
            if needle not in text:
                self._warn("pipeline_wiring", pipeline_rel, f"does not reference `{needle}`")

    # -------------------------------------------------------------- helpers
    def _run(self, command: list[str]) -> tuple[int, str]:
        try:
            completed = subprocess.run(
                command, cwd=self.repo_root, check=False, capture_output=True, text=True, errors="replace"
            )
        except OSError as exc:
            return 1, str(exc)
        return completed.returncode, (completed.stdout.strip() or completed.stderr.strip())

    def _read_text(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return ""

    def _rel(self, path: Path) -> str:
        try:
            return path.relative_to(self.repo_root).as_posix()
        except ValueError:
            return path.as_posix()

    def _finding(self, severity: str, code: str, path: str, message: str) -> None:
        finding = Finding(severity=severity, code=code, path=path, message=message)
        (self.errors if severity == "error" else self.warnings).append(finding)

    def _error(self, code: str, path: str, message: str) -> None:
        self._finding("error", code, path, message)

    def _warn(self, code: str, path: str, message: str) -> None:
        self._finding("warning", code, path, message)


def find_repo_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "AGENTS.md").exists() and (candidate / "package.json").exists():
            return candidate
    return start


def print_text(result: HarnessCheck) -> None:
    print(f"{'FAIL' if result.errors else 'PASS'}: agent harness check")
    if result.errors:
        print("\nErrors:")
        for item in result.errors:
            print(f"- [{item.code}] {item.path}: {item.message}")
    if result.warnings:
        print("\nWarnings:")
        for item in result.warnings:
            print(f"- [{item.code}] {item.path}: {item.message}")


def print_json(result: HarnessCheck) -> None:
    payload = {
        "status": "failed" if result.errors else "passed",
        "errors": [asdict(item) for item in result.errors],
        "warnings": [asdict(item) for item in result.warnings],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser(description="Check this repository's agent development harness.")
    parser.add_argument("--repo-root", default=None, help="Repository root. Defaults to auto-detect from cwd.")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve() if args.repo_root else find_repo_root(Path.cwd().resolve())
    result = HarnessCheck(repo_root)
    result.run()

    if args.format == "json":
        print_json(result)
    else:
        print_text(result)
    return 1 if result.errors else 0


if __name__ == "__main__":
    sys.exit(main())
