#!/usr/bin/env python3
"""Unit tests for scripts/harness/vendor-skills.py::stamp_frontmatter.

A vendored skill reached through a project adapter must stay callable by the Skill tool:
an upstream `disable-model-invocation: true` is rewritten to `user-invocable: false` for
adapter targets only, and skills without the flag are left untouched.
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
    "disable-model-invocation: true\n"
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
    assert "user-invocable: false" in lines, lines
    assert not any(l.startswith("disable-model-invocation:") for l in lines), lines
    assert lines.count("user-invocable: false") == 1, lines
    assert "  author: upstream" not in lines, "upstream metadata block must be dropped"
    assert "metadata:" in lines and any(l.startswith("  source:") for l in lines), lines
    assert out.endswith("---\n\nBody.\n"), "body must be preserved"

    out = stamp(UPSTREAM, "x/y", "0123456789abcdef", "skills/to-spec", "to-spec", adapter_target=False)
    lines = frontmatter_lines(out)
    assert "disable-model-invocation: true" in lines, "non-adapter targets keep the upstream flag"
    assert "user-invocable: false" not in lines, lines

    out = stamp(NO_FLAG, "x/y", "0123456789abcdef", "skills/grilling", "grilling", adapter_target=True)
    lines = frontmatter_lines(out)
    assert "user-invocable: false" not in lines, "no flag upstream: nothing is added"
    assert "disable-model-invocation: true" not in lines, lines

    out = stamp(NO_FLAG, "x/y", "0123456789abcdef", "skills/code-review", "review-since", adapter_target=False)
    assert "name: review-since" in frontmatter_lines(out), "`as` rename must still apply"

    print("PASS: vendor-skills stamp_frontmatter tests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
