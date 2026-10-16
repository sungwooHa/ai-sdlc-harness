#!/usr/bin/env python3
"""Agent harness structural check; text output, exit 1 on any error. Six checks, one method each:
hook_intents <-> .claude/settings.json / .husky wiring and scripts; .claude/skills symlink mirror;
adapter-map targets carry `disable-model-invocation: true`; AGENTS.md <= always_on_max_lines; every
harness element is named in docs/standards/PLAYBOOK_MAP.md; no Hangul in non-test scripts.
Files come from `git ls-files` (tracked + untracked-not-ignored): ignored .husky/_ shims never count.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

CONFIG = ".agents/harness.json"
SETTINGS = ".claude/settings.json"
MAP = "docs/standards/PLAYBOOK_MAP.md"
SCRIPT_REF = re.compile(r"(?<![\w.-])scripts/[\w./-]*\w")
HANGUL = re.compile("[" + chr(0xAC00) + "-" + chr(0xD7A3) + "]")  # escaped so this file stays Hangul-free


def tokens(text: str | None) -> set[str]:
    return {t for t in (text or "").split("|") if t}


class Check:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.errors: list[str] = []
        git = ["git", "-C", str(root), "ls-files", "-z", "--cached", "--others", "--exclude-standard"]
        listed = subprocess.run(git, capture_output=True, text=True, check=True).stdout
        self.files = {p for p in listed.split("\0") if p and os.path.lexists(root / p)}

    def error(self, code: str, path: str, message: str) -> None:
        self.errors.append(f"- [{code}] {path}: {message}")

    def under(self, prefix: str) -> list[str]:
        return sorted(p for p in self.files if p.startswith(prefix))

    def text(self, rel: str) -> str:
        return (self.root / rel).read_text(encoding="utf-8", errors="replace")

    def runs(self, hook: str) -> set[str]:  # scripts named on a git hook's non-comment lines
        lines = [line for line in self.text(hook).splitlines() if not line.lstrip().startswith("#")]
        return {ref for line in lines for ref in SCRIPT_REF.findall(line)}

    def run(self) -> None:
        if CONFIG not in self.files:
            return self.error("config", CONFIG, "missing")
        cfg = json.loads(self.text(CONFIG))
        skills = cfg.get("skills", {})
        self.skill_root = skills.get("root", ".agents/skills")
        self.local = skills.get("local_prefix", "local-")
        rests = [p[len(self.skill_root) + 1:] for p in self.under(self.skill_root + "/")]
        self.skills = sorted({r.split("/")[0] for r in rests if "/" in r and not r.startswith(self.local)})
        intents = cfg.get("hook_intents", [])
        self.check_hooks(intents)
        self.check_mirror(skills.get("claude_mirror", ".claude/skills"))
        self.check_adapters(skills.get("adapters", {}).get("map", {}))
        self.check_always_on(cfg.get("always_on_max_lines", 60))
        self.check_playbook_map(intents)
        self.check_hangul()

    def check_hooks(self, intents: list[dict]) -> None:
        settings = json.loads(self.text(SETTINGS)) if SETTINGS in self.files else {}
        wired: dict[str, dict[str, set[str]]] = {}  # script -> event -> matcher tokens
        for event, groups in settings.get("hooks", {}).items():
            for group in groups:
                for hook in group.get("hooks", []):
                    for script in SCRIPT_REF.findall(hook.get("command", "")):
                        wired.setdefault(script, {}).setdefault(event, set()).update(tokens(group.get("matcher")))
        for intent in intents:
            iid, script, events = intent["id"], intent["script"], tokens(intent.get("event"))
            if script not in self.files:
                self.error("hook_script", script, f"hook intent {iid} names a script that does not exist")
            for hook in sorted(f".husky/{e}" for e in events if e.islower()):  # git events: pre-commit, ...
                if hook not in self.files:
                    self.error("git_hook", hook, f"missing; hook intent {iid} declares it")
                elif script != hook and script not in self.runs(hook):
                    self.error("git_hook", hook, f"does not run {script} (hook intent {iid})")
            claude_events = sorted(e for e in events if not e.islower())
            for event in claude_events:
                if event not in wired.get(script, {}):
                    self.error("hook_wiring", SETTINGS, f"no {event} hook runs {script} (hook intent {iid})")
            got = set().union(*(wired.get(script, {}).get(e, set()) for e in claude_events))
            if claude_events and got != (want := tokens(intent.get("matcher"))):
                self.error("hook_matcher", SETTINGS, f"{script} wired for {sorted(got)}; {iid} declares {sorted(want)}")
        for script in sorted(set(wired) - {i["script"] for i in intents}):
            self.error("hook_undeclared", SETTINGS, f"{script} is wired but no hook_intents entry declares it")
        git_events = set().union(*(tokens(i.get("event")) for i in intents))
        for hook in self.under(".husky/"):
            if hook.count("/") == 1 and hook[len(".husky/"):] not in git_events:
                self.error("hook_undeclared", hook, "no hook_intents entry declares this git hook")

    def check_mirror(self, mirror: str) -> None:
        entries = {p[len(mirror) + 1:].split("/")[0] for p in self.under(mirror + "/")}
        for name in sorted(set(self.skills) | {e for e in entries if not e.startswith(self.local)}):
            link, target = self.root / mirror / name, self.root / self.skill_root / name
            if not (link.is_symlink() and target.is_dir() and os.path.realpath(link) == os.path.realpath(target)):
                self.error("skill_mirror", f"{mirror}/{name}", f"must be a symlink to {self.skill_root}/{name}/")

    def check_adapters(self, adapter_map: dict[str, list[str]]) -> None:
        for adapter, targets in sorted(adapter_map.items()):
            for target in targets:
                rel = f"{self.skill_root}/{target}/SKILL.md"
                front = re.match(r"---\n(.*?)\n---", self.text(rel), re.S) if rel in self.files else None
                if not (front and re.search(r"^disable-model-invocation:\s*true\s*$", front.group(1), re.M)):
                    self.error("adapter_target", rel, f"mapped by {adapter}: must exist with "
                               "`disable-model-invocation: true` in its frontmatter (the adapter reads it by path)")

    def check_always_on(self, limit: int) -> None:
        if "AGENTS.md" in self.files and (lines := len(self.text("AGENTS.md").splitlines())) > limit:
            self.error("always_on", "AGENTS.md", f"{lines} lines, limit {limit} (always_on_max_lines)")

    def check_playbook_map(self, intents: list[dict]) -> None:
        if MAP not in self.files:
            return self.error("playbook_map", MAP, "missing")
        text = self.text(MAP)
        elements = {i["script"] for i in intents} | {f"{self.skill_root}/{n}/" for n in self.skills}
        elements |= set(self.under("docs/standards/")) | set(self.under(".claude/agents/"))
        elements |= {p for p in self.under(".husky/") if p.count("/") == 1}
        for element in sorted(elements):
            if not re.search(re.escape(element) + ("" if element.endswith("/") else r"(?![\w.-])"), text):
                self.error("playbook_map", element, f"not named in {MAP}; add it to the row of the play it serves")

    def check_hangul(self) -> None:
        for rel in self.under("scripts/"):
            if rel.startswith("scripts/test/") or not (self.root / rel).is_file():
                continue
            hit = next((n for n, line in enumerate(self.text(rel).splitlines(), 1) if HANGUL.search(line)), 0)
            if hit:
                self.error("hangul", f"{rel}:{hit}", "no Hangul in non-test scripts; human text goes in config or docs")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check this repository's agent harness.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    check = Check(parser.parse_args().repo_root.resolve())
    check.run()
    print("\n".join([f"{'FAIL' if check.errors else 'PASS'}: agent harness check", *check.errors]))
    return 1 if check.errors else 0


if __name__ == "__main__":
    sys.exit(main())
