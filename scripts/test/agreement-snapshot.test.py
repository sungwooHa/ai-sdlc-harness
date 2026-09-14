#!/usr/bin/env python3
"""Agreement survives working-result edits; amendments preserve previous revisions."""
import importlib.util
import json
import tempfile
from pathlib import Path

spec = importlib.util.spec_from_file_location("snapshot", Path(__file__).parents[1] / "harness/agreement-snapshot.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def refuses(fn):
    try:
        fn()
    except ValueError:
        return
    raise AssertionError("expected refusal")


with tempfile.TemporaryDirectory() as tmp:
    folder = Path(tmp) / "change"
    folder.mkdir()
    refuses(lambda: module.freeze(folder, "001", "test approval"))
    (folder / "spec.md").write_text("# Expected value\n")
    (folder / "plan.md").write_text("# Approved plan\n")
    (folder / "deliverables").mkdir()
    mockup = folder / "deliverables/mockup.html"
    mockup.write_text("<title>draft</title>")
    refuses(lambda: module.freeze(folder, "001", ""))
    refuses(lambda: module.freeze(folder, "../escape", "test approval"))
    first = module.freeze(folder, "001", "test approval message 1")
    assert module.verify(first) == []
    mockup.write_text("<title>actual result</title>")
    (folder / "plan.md").write_text("# Working progress\n")
    assert module.verify(first) == []
    assert (first / "deliverables/mockup.html").read_text() == "<title>draft</title>"
    refuses(lambda: module.freeze(folder, "001", "another message"))
    second = module.freeze(folder, "002", "test amendment message 2")
    assert module.verify(second) == [] and module.verify(first) == []
    assert (second / "deliverables/mockup.html").read_text() == "<title>actual result</title>"
    (second / "plan.md").write_text("rewritten expectation")
    assert any("plan.md" in p for p in module.verify(second))
    (first / "spec.md").unlink()
    assert any("spec.md" in p for p in module.verify(first))
    data = json.loads((first / "snapshot.json").read_text())
    data["files"]["../../outside"] = "fake"
    (first / "snapshot.json").write_text(json.dumps(data))
    assert module.verify(first)
    mockup.unlink()
    mockup.symlink_to(folder / "spec.md")
    refuses(lambda: module.freeze(folder, "003", "test approval"))
    assert not (folder / "agreements/003").exists()

    (folder / ".agents").mkdir()
    (folder / ".agents/harness.yaml").write_text(json.dumps({
        "artifact_chain": {"deliverables": {"dir": "views/html"}},
    }))
    (folder / "views/html").mkdir(parents=True)
    (folder / "views/html/mockup.html").write_text("<title>configured draft</title>")
    configured = module.freeze(folder, "004", "test configured path approval")
    assert module.verify(configured) == []
    assert (configured / "views/html/mockup.html").read_text() == "<title>configured draft</title>"

print("PASS: agreement snapshot tests")
