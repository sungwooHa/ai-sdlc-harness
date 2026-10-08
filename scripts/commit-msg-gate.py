#!/usr/bin/env python3
"""commit-msg gate: the first line follows the project format, and no trailer but the allowed ones.

Wired from .husky/commit-msg (hook intent commit_msg_gate). The rules live in
docs/standards/COMMIT_CONVENTION.md; the values checked here live in .agents/harness.yaml
`commit_message`. Standard library and git only.

Usage: commit-msg-gate.py [--repo-root DIR] <message-file>
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

MANIFEST_REL = ".agents/harness.yaml"
CONVENTION = "docs/standards/COMMIT_CONVENTION.md"
# First lines git writes itself for merges, reverts and autosquash.
GIT_WRITTEN = ("Merge", 'Revert "', "fixup!", "squash!")
PLACEHOLDER = re.compile(r"__[A-Z0-9_]+__")
TEXT = r"\S(?:.*?\S)?"  # nonempty, no surrounding blanks
# `[{field}]` or `({field})` (optional, with the space after it) | `{field}`
TOKEN = re.compile(r"(?P<opt>\[\{[^{}]+\}\] ?|\(\{[^{}]+\}\) ?)|\{(?P<field>[^{}]+)\}")


def subject_pattern(fmt: str, types: list[str]) -> re.Pattern[str]:
    """Read the format as a pattern: `{type}` is one of `types`, any other `{field}` is nonempty
    text, and a field written as `[{field}]` or `({field})` may be left out with the space after it."""
    parts, pos = [], 0
    for match in TOKEN.finditer(fmt):
        parts.append(re.escape(fmt[pos : match.start()]))
        opt = match.group("opt")
        if opt:
            space = " " if opt.endswith(" ") else ""
            parts.append(f"(?:{re.escape(opt[0])}{TEXT}{re.escape(opt.rstrip()[-1])}{space})?")
        elif match.group("field").strip() == "type" and types:
            parts.append("(?:" + "|".join(map(re.escape, types)) + ")")
        else:
            parts.append(TEXT)
        pos = match.end()
    parts.append(re.escape(fmt[pos:]))
    return re.compile("".join(parts))


def stored_text(raw: str) -> str:
    """The message as git will store it: comment lines dropped, nothing below the scissors line."""
    lines = []
    for line in raw.splitlines():
        if line.startswith("# -") and " >8 " in line:
            break
        if not line.startswith("#"):
            lines.append(line)
    return "\n".join(lines).strip("\n") + "\n"


def trailer_keys(text: str) -> list[str]:
    """Trailer keys as git reads them (the last paragraph of `Key: value` lines)."""
    result = subprocess.run(["git", "interpret-trailers", "--parse"], input=text, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"git interpret-trailers failed: {result.stderr.strip()}")
    return [line.split(":", 1)[0].strip() for line in result.stdout.splitlines() if ":" in line]


def problems(message: str, cfg: dict) -> list[str]:
    text = stored_text(message)
    subject = next((line for line in text.splitlines() if line.strip()), "").rstrip()
    found = []
    fmt = cfg.get("format")
    # An unreplaced placeholder (this template repository itself) has no format to check yet.
    if isinstance(fmt, str) and fmt and not PLACEHOLDER.fullmatch(fmt) and not subject.startswith(GIT_WRITTEN):
        types = [t for t in cfg.get("types") or [] if isinstance(t, str)]
        if not subject_pattern(fmt, types).fullmatch(subject):
            found.append(f"first line `{subject}` does not match `{fmt}`" + (f" (type: {' | '.join(types)})" if types else ""))
    if cfg.get("forbid_other_trailers", True):
        allowed = [t for t in cfg.get("allowed_trailers", ["Plan-Ref"]) if isinstance(t, str)]
        for key in trailer_keys(text):
            if key.lower() not in {a.lower() for a in allowed}:
                found.append(f"trailer `{key}` is not allowed (allowed: {', '.join(allowed) or 'none'})")
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("message_file")
    args = parser.parse_args()
    try:
        manifest = json.loads((Path(args.repo_root) / MANIFEST_REL).read_text(encoding="utf-8"))
        cfg = manifest.get("commit_message") or {}
        found = problems(Path(args.message_file).read_text(encoding="utf-8"), cfg)
    except (OSError, ValueError, RuntimeError, AttributeError) as exc:
        found = [f"cannot check the message: {exc}"]
    if not found:
        return 0
    for item in found:
        print(f"commit-msg-gate: {item}", file=sys.stderr)
    print(
        f"commit-msg-gate: see {CONVENTION}. Agents pass one -m per paragraph: "
        'git commit -m "<first line>" -m "<why>" -m "Plan-Ref: <YYMMDD_NN>-<slug>"',
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
