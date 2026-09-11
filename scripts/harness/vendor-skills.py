#!/usr/bin/env python3
"""Vendor selected skills from a GitHub skills repo into .agents/skills.

Reads the `skills.vendored` entries in .agents/harness.yaml, fetches each
listed skill directory from GitHub via `gh api`, writes it under
.agents/skills/<name>/, stamps provenance into SKILL.md frontmatter
(`metadata.source`, `metadata.commit`, `metadata.vendored_at`), and ensures the
.claude/skills/<name> symlink exists.

Usage:
  python3 scripts/harness/vendor-skills.py --source mattpocock/skills [--ref main] [--only grilling,to-spec]
Requires: gh (authenticated), python3.
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL_ROOT = ROOT / ".agents" / "skills"
CLAUDE_ROOT = ROOT / ".claude" / "skills"


def gh_json(path: str):
    out = subprocess.run(["gh", "api", path], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def stamp_frontmatter(
    text: str, source: str, commit: str, path: str, local_name: str, adapter_target: bool = False
) -> str:
    stamp = (
        "metadata:\n"
        f"  source: https://github.com/{source}/tree/{commit[:12]}/{path}\n"
        f"  commit: {commit}\n"
        f"  vendored_at: {dt.date.today().isoformat()}\n"
        "  update: python3 scripts/harness/vendor-skills.py --source " + source + "\n"
    )
    if text.startswith("---\n"):
        head, rest = text[4:].split("\n---", 1)
        # Drop the upstream `metadata:` block whole (header + indented children such as
        # author/version); otherwise the orphaned children fold into the preceding key.
        lines: list[str] = []
        in_metadata = False
        for l in head.splitlines():
            if l.startswith("metadata:"):
                in_metadata = True
                continue
            if in_metadata and (l.startswith(" ") or l.startswith("\t")):
                continue
            in_metadata = False
            lines.append(l)
        # A skill vendored under a different local name (`as`) must carry that name in its
        # frontmatter, otherwise the host registers it under the upstream name and collides.
        lines = [f"name: {local_name}" if l.startswith("name:") else l for l in lines]
        # A skill reached through a project adapter (skills.adapters.map) must stay callable by
        # the Skill tool, or the adapter's call is refused. Upstream ships some of them as
        # `disable-model-invocation: true`; swap that for `user-invocable: false`, which hides the
        # original from the slash menu instead. Skills without the flag are left untouched.
        if adapter_target and any(l.startswith("disable-model-invocation:") for l in lines):
            has_user_invocable = any(l.startswith("user-invocable:") for l in lines)
            lines = [
                ("user-invocable: false" if not has_user_invocable else None)
                if l.startswith("disable-model-invocation:")
                else l
                for l in lines
            ]
            lines = [l for l in lines if l is not None]
        return "---\n" + "\n".join(lines) + "\n" + stamp + "---" + rest
    return "---\n" + f"name: {local_name}\n" + stamp + "---\n\n" + text


def vendored_names(entry: dict) -> dict[str, str]:
    """Upstream skill name -> local directory name. Entries are strings or {name, as}."""
    mapping: dict[str, str] = {}
    for item in entry.get("skills", []):
        if isinstance(item, str):
            mapping[item] = item
        elif isinstance(item, dict) and item.get("name"):
            mapping[item["name"]] = item.get("as") or item["name"]
    return mapping


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, help="owner/repo")
    ap.add_argument("--ref", default="main")
    ap.add_argument("--only", default=None, help="comma-separated skill names")
    args = ap.parse_args()

    manifest = json.loads((ROOT / ".agents" / "harness.yaml").read_text(encoding="utf-8"))
    entry = next((v for v in manifest["skills"]["vendored"] if v["source"].endswith(args.source)), None)
    if not entry:
        print(f"no vendored entry for {args.source} in .agents/harness.yaml", file=sys.stderr)
        return 1
    names = vendored_names(entry)
    wanted = set(args.only.split(",")) if args.only else set(names)
    adapter_targets = set(manifest["skills"].get("adapters", {}).get("map", {}).values())

    commit = gh_json(f"repos/{args.source}/commits/{args.ref}")["sha"]
    tree = gh_json(f"repos/{args.source}/git/trees/{commit}?recursive=1")["tree"]
    skill_dirs: dict[str, str] = {}
    for node in tree:
        p = node["path"]
        if node["type"] == "blob" and p.endswith("/SKILL.md"):
            name = p.split("/")[-2]
            if name in wanted:
                skill_dirs[name] = p[: -len("/SKILL.md")]
    missing = wanted - set(skill_dirs)
    if missing:
        print(f"skills not found upstream: {sorted(missing)}", file=sys.stderr)
        return 1

    for name, base in sorted(skill_dirs.items()):
        local = names.get(name, name)
        dest = SKILL_ROOT / local
        dest.mkdir(parents=True, exist_ok=True)
        files = [n for n in tree if n["type"] == "blob" and n["path"].startswith(base + "/")]
        for node in files:
            rel = node["path"][len(base) + 1 :]
            blob = gh_json(f"repos/{args.source}/git/blobs/{node['sha']}")
            data = base64.b64decode(blob["content"])
            target = dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            if rel == "SKILL.md":
                text = stamp_frontmatter(
                    data.decode("utf-8"), args.source, commit, base, local, adapter_target=local in adapter_targets
                )
                target.write_text(text, encoding="utf-8")
            else:
                target.write_bytes(data)
        link = CLAUDE_ROOT / local
        if not link.exists() and not link.is_symlink():
            link.symlink_to(f"../../.agents/skills/{local}")
        suffix = f" as {local}" if local != name else ""
        print(f"vendored {name}{suffix} <- {base} ({len(files)} files)")
    print(f"source commit: {commit}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
