#!/usr/bin/env python3
"""Unit tests for scripts/harness/vendor-skills.py::stamp_frontmatter.

A vendored skill reached through a project adapter is stamped `disable-model-invocation: true`
and loses any `user-invocable` line; non-adapter targets are left untouched.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "harness" / "vendor-skills.py"


def load_module():
    spec = importlib.util.spec_from_file_location("vendor_skills", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


UPSTREAM = (
    "---\n"
    "name: to-spec\n"
    "description: \"Turn the conversation into a spec.\"\n"
    "user-invocable: false\n"
    "metadata:\n"
    "  author: upstream\n"
    "  version: 1\n"
    "---\n\n"
    "Body.\n"
)

NO_FLAG = "---\nname: grilling\ndescription: Grill.\n---\n\nBody.\n"


def frontmatter_lines(text: str) -> list[str]:
    head = text[4:].split("\n---", 1)[0]
    return head.splitlines()


def main() -> int:
    vendor = load_module()
    stamp = vendor.stamp_frontmatter

    out = stamp(UPSTREAM, "x/y", "0123456789abcdef", "skills/to-spec", "to-spec", adapter_target=True)
    lines = frontmatter_lines(out)
    assert lines.count("disable-model-invocation: true") == 1, lines
    assert not any(l.startswith("user-invocable:") for l in lines), lines
    assert "  author: upstream" not in lines, "upstream metadata block must be dropped"
    assert "metadata:" in lines and any(l.startswith("  source:") for l in lines), lines
    assert out.endswith("---\n\nBody.\n"), "body must be preserved"

    out = stamp(UPSTREAM, "x/y", "0123456789abcdef", "skills/to-spec", "to-spec", adapter_target=False)
    lines = frontmatter_lines(out)
    assert "user-invocable: false" in lines, "non-adapter targets keep upstream lines"
    assert "disable-model-invocation: true" not in lines, lines

    out = stamp(NO_FLAG, "x/y", "0123456789abcdef", "skills/grilling", "grilling", adapter_target=True)
    lines = frontmatter_lines(out)
    assert lines.count("disable-model-invocation: true") == 1, "flag is added when upstream has none"

    out = stamp(NO_FLAG, "x/y", "0123456789abcdef", "skills/code-review", "review-since", adapter_target=False)
    assert "name: review-since" in frontmatter_lines(out), "`as` rename must still apply"

    print("PASS: vendor-skills stamp_frontmatter tests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
