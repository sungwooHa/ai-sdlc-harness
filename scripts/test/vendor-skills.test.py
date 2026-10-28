#!/usr/bin/env python3
"""Unit tests for scripts/harness/vendor-skills.py::stamp_frontmatter.

A vendored skill's managed role survives updates without changing its body or unrelated
host metadata. Standalone skills keep upstream invocation settings.
"""

from __future__ import annotations

import importlib.util
import base64
import contextlib
import io
import json
import sys
import tempfile
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
    assert lines.count("user-invocable: false") == 1, lines
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

    explicit = stamp(UPSTREAM, "x/y", "0123456789abcdef", "skills/handoff", "handoff", invocation_role="explicit_only")
    assert "user-invocable: true" in frontmatter_lines(explicit)
    assert "disable-model-invocation: true" in frontmatter_lines(explicit)
    assert explicit.endswith("---\n\nBody.\n")

    for key, value, duplicate in (("name", "to-spec", "other"),
                                  ("user-invocable", "false", "true"),
                                  ("disable-model-invocation", "true", "false")):
        bad = f"---\nname: to-spec\n{key}: {value}\n{key} : {duplicate}\n---\nBody.\n"
        if key == "name":
            bad = bad.replace("name: to-spec\n", "", 1)
        try:
            stamp(bad, "x/y", "0123456789abcdef", "skills/to-spec", "to-spec", adapter_target=True)
        except ValueError:
            pass
        else:
            raise AssertionError(f"duplicate upstream managed key accepted: {key}")
        bad = f"---\nname: to-spec\n{key}: {value}\n\n# comment\n  continued\n---\nBody.\n"
        if key == "name":
            bad = bad.replace("name: to-spec\n", "", 1)
        try:
            stamp(bad, "x/y", "0123456789abcdef", "skills/to-spec", "to-spec", adapter_target=True)
        except ValueError:
            pass
        else:
            raise AssertionError(f"upstream scalar continuation left behind: {key}")

    multiline = UPSTREAM.replace('description: "Turn the conversation into a spec."',
                                 'description: |\n  Opaque multiline\n  description.')
    multiline = multiline.replace("name: to-spec", "name : to-spec").replace("user-invocable: false", "user-invocable : true")
    out = stamp(multiline, "x/y", "0123456789abcdef", "skills/to-spec", "local-spec", adapter_target=True)
    assert "description: |\n  Opaque multiline\n  description.\n" in out
    assert "name: local-spec" in frontmatter_lines(out)
    assert "user-invocable : true" not in out
    assert frontmatter_lines(out).count("user-invocable: false") == 1
    assert out.endswith("---\n\nBody.\n")

    host = ('interface:\n  display_name: "Preserved"\n  description: |\n    Multiline interface\n    description.\n'
            'dependencies:\n  tools:\n    - type: "mcp"\n      value: "example"\n      description: |\n        Multiline dependency.\n'
            'policy: # preserved\n  allow_implicit_invocation: true # upstream choice\n'
            '  future_setting: "preserved"\n  future_notes: |\n    Opaque multiline\n    allow_implicit_invocation: text\n')
    expected = host.replace("true # upstream choice", "false # upstream choice")
    assert vendor.stamp_codex_policy(host, False) == expected
    assert vendor.stamp_codex_policy(expected, False) == expected, "overlay must be idempotent"
    assert vendor.stamp_codex_policy('interface:\n  display_name: "Kept"\n', False).startswith(
        'interface:\n  display_name: "Kept"\npolicy:\n')
    for bad in ("policy: {allow_implicit_invocation: true}\n",
                "policy:\n  allow_implicit_invocation: 'false'\n",
                "policy:\n  allow_implicit_invocation: false#comment\n",
                "policy:\n  allow_implicit_invocation: false\n    continued\n",
                "policy:\n  allow_implicit_invocation: false\n\n  # comment\n    continued\n",
                "policy:#comment\n  allow_implicit_invocation: false\n",
                "policy:\n  allow_implicit_invocation: true\n  allow_implicit_invocation: false\n",
                "policy:\n  allow_implicit_invocation: true\npolicy:\n"):
        try:
            vendor.stamp_codex_policy(bad, False)
        except ValueError:
            pass
        else:
            raise AssertionError(f"ambiguous policy accepted: {bad!r}")

    # Exercise the public updater path with an upstream payload. No network or real checkout writes.
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        (root / ".agents").mkdir()
        (root / ".claude/skills").mkdir(parents=True)
        manifest = {"skills": {"vendored": [{"source": "github.com/x/y", "skills": ["grilling"]}],
                              "adapters": {"map": {"demo-intent": ["grilling"]}},
                              "invocation": {"internal": ["grilling"], "explicit_only": [], "entrypoints": ["demo-intent"]}}}
        (root / ".agents/harness.json").write_text(json.dumps(manifest))
        payload = {"skill": NO_FLAG, "host": host}
        def fake_api(path):
            if "/commits/" in path:
                return {"sha": "0123456789abcdef"}
            if "/git/trees/" in path:
                return {"tree": [{"type": "blob", "path": "skills/grilling/SKILL.md", "sha": "skill"},
                                 {"type": "blob", "path": "skills/grilling/agents/openai.yaml", "sha": "host"}]}
            return {"content": base64.b64encode(payload[path.rsplit("/", 1)[1]].encode()).decode()}
        old_args = sys.argv
        try:
            vendor.ROOT, vendor.SKILL_ROOT, vendor.CLAUDE_ROOT = root, root / ".agents/skills", root / ".claude/skills"
            vendor.gh_json = fake_api
            sys.argv = ["vendor-skills.py", "--source", "x/y"]
            for _ in range(2):
                with contextlib.redirect_stdout(io.StringIO()):
                    assert vendor.main() == 0
                skill = (vendor.SKILL_ROOT / "grilling/SKILL.md").read_text()
                assert "user-invocable: false" in frontmatter_lines(skill)
                assert skill.endswith("---\n\nBody.\n")
                assert (vendor.SKILL_ROOT / "grilling/agents/openai.yaml").read_text() == expected
                assert (vendor.CLAUDE_ROOT / "grilling").resolve() == (vendor.SKILL_ROOT / "grilling").resolve()
        finally:
            sys.argv = old_args

    print("PASS: vendor-skills metadata and updater tests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
