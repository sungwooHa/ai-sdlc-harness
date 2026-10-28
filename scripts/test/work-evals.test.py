#!/usr/bin/env python3
"""Exercise work-trial preparation and grading without invoking a model."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

TOOL = Path(__file__).resolve().parents[1] / "harness/work-evals.py"
SPEC = importlib.util.spec_from_file_location("work_evals", TOOL)
work = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(work)


def put(root, name, value):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


class WorkTrials(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.source = self.directory / "source"
        self.source.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        put(self.source, "AGENTS.md", "Preserve the project policy.\n")
        put(self.source, "package.json", '{"scripts":{"prepare":"husky"}}\n')
        put(self.source, ".gitignore", ".husky/_/\nnode_modules/\n__pycache__/\n*.py[co]\n")
        put(self.source, ".husky/pre-commit", "#!/bin/sh\ntest ! -f forbidden.txt\n")
        ensure = TOOL.parent / "ensure-husky.sh"
        put(self.source, "scripts/harness/ensure-husky.sh", ensure.read_text())
        put(self.source, "scripts/test/run-evals.test.py", "raise RuntimeError('hidden oracle')\n")
        put(self.source, "scripts/test/work-evals.test.py", "raise RuntimeError('hidden oracle')\n")
        put(self.source, "scripts/test/work-cases.test.py", "raise RuntimeError('hidden oracle')\n")
        put(self.source, ".claude/evals/work/cases.json", json.dumps({
            "version": 1, "cases": [{
                "id": "sample", "prompt": "Repair the command.",
                "fixture": "sample", "allowed_paths": ["apps/app/value.txt", "docs/changes/**"],
                "requires_browser": True,
            }],
        }))
        put(self.source, ".claude/evals/work/fixtures/sample/value.txt", "broken\n")
        put(self.source, ".claude/evals/work/rubric.md", "Verify the actual result independently.\n")
        put(self.source, ".claude/evals/work/externalgrade.py",
            "import argparse,json\nfrom pathlib import Path\n"
            "p=argparse.ArgumentParser();p.add_argument('--case');p.add_argument('--workspace');a=p.parse_args()\n"
            "ok=(Path(a.workspace)/'apps/app/value.txt').read_text()=='fixed\\n'\n"
            "print(json.dumps({'status':'PASS' if ok else 'FAIL','checks':[{'id':'value','status':'PASS' if ok else 'FAIL','detail':'observed command result'}]}))\n"
            "raise SystemExit(0 if ok else 1)\n")
        self.git("add", "--all")
        self.git("commit", "-qm", "Fixture")
        self.revision = self.git("rev-parse", "HEAD")
        self.trial = self.directory / "trial"

    def tearDown(self):
        self.temp.cleanup()

    def git(self, *args, cwd=None, check=True):
        result = subprocess.run(["git", *args], cwd=cwd or self.source, env=work.clean_env(),
                                capture_output=True, text=True, check=check)
        return result.stdout.strip() if check else result

    def prepare(self):
        return work.prepare(self.source, "sample", self.revision, self.trial)

    def test_source_is_preserved_and_frozen_oracle_stays_outside_worker(self):
        put(self.source, "AGENTS.md", "Uncommitted policy is not the selected candidate.\n")
        self.git("add", "AGENTS.md")
        put(self.source, "untracked.txt", "keep me\n")
        before = work.source_snapshot(self.source)
        result = self.prepare()
        worker = self.trial / "worker"
        self.assertEqual(work.source_snapshot(self.source), before)
        self.assertEqual((worker / "AGENTS.md").read_text(), "Preserve the project policy.\n")
        self.assertFalse((worker / ".claude/evals").exists())
        self.assertFalse((worker / "untracked.txt").exists())
        self.assertEqual(self.git("remote", cwd=worker), "")
        self.assertEqual(self.git("config", "core.hooksPath", cwd=worker), ".husky/_")
        self.assertIn("SKIP", (worker / "scripts/test/work-evals.test.py").read_text())
        self.assertEqual(result["status"], "PREPARED")
        put(self.source, ".claude/evals/work/externalgrade.py", "raise RuntimeError('dirty replacement')\n")
        # A changed source is rejected rather than executing either grader.
        self.assertEqual(work.grade(self.source, self.trial)["integrity"]["status"], "FAIL")

    def test_inherited_git_routing_never_targets_the_original(self):
        before = work.source_snapshot(self.source)
        with patch.dict(os.environ, {
            "GIT_DIR": str(self.source / ".git"), "GIT_WORK_TREE": str(self.source),
            "GIT_INDEX_FILE": str(self.source / ".git/index"),
            "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "user.name", "GIT_CONFIG_VALUE_0": "Injected",
        }):
            self.prepare()
            result = work.inspect(self.source, self.trial, "codex")
        self.assertEqual(work.source_snapshot(self.source), before)
        self.assertEqual(result["integrity"]["status"], "PASS")
        self.assertEqual(result["native"]["status"], "unverified")
        self.assertEqual(result["status"], "NEEDS_REVIEW")

    def test_old_harness_without_catalog_uses_the_same_frozen_task_commit(self):
        assets = self.revision
        self.git("rm", "-qr", ".claude/evals/work")
        self.git("commit", "-qm", "Older harness without work trials")
        old_harness = self.git("rev-parse", "HEAD")
        self.git("restore", "--source=" + assets, "--staged", "--worktree", "--", ".claude/evals/work")
        put(self.source, "AGENTS.md", "Candidate policy.\n")
        self.git("add", "--all")
        self.git("commit", "-qm", "Candidate with identical task assets")
        candidate = self.git("rev-parse", "HEAD")
        before = work.source_snapshot(self.source)
        first = work.prepare(self.source, "sample", old_harness, self.trial, candidate)
        second_trial = self.directory / "candidate"
        second = work.prepare(self.source, "sample", candidate, second_trial, candidate)
        baseline = json.loads((self.trial / "receipt/manifest.json").read_text())
        current = json.loads((second_trial / "receipt/manifest.json").read_text())
        self.assertNotEqual(first["source_revision"], second["source_revision"])
        self.assertEqual(first["task_revision"], second["task_revision"])
        self.assertEqual(baseline["fixture_sha256"], current["fixture_sha256"])
        self.assertEqual(baseline["oracle_sha256"], current["oracle_sha256"])
        self.assertNotEqual((self.trial / "worker/AGENTS.md").read_text(),
                            (second_trial / "worker/AGENTS.md").read_text())
        self.assertEqual(work.source_snapshot(self.source), before)
        self.assertEqual(work.grade(self.source, self.trial)["behavioral"]["status"], "FAIL")

    def test_correct_artifact_never_grants_browser_or_native_success(self):
        self.prepare()
        first = work.grade(self.source, self.trial)
        self.assertEqual(first["behavioral"]["status"], "FAIL")
        put(self.trial / "worker", "apps/app/value.txt", "fixed\n")
        second = work.grade(self.source, self.trial)
        self.assertEqual(second["behavioral"]["status"], "PASS")
        self.assertEqual(second["status"], "NEEDS_REVIEW")
        self.assertEqual(second["browser"], "unverified")
        self.assertEqual(second["independent_review"], "unverified")
        self.assertNotEqual(first["receipt"], second["receipt"])
        self.assertTrue((self.trial / "receipt" / first["receipt"]).is_file())

    def test_committed_policy_edits_are_still_forbidden(self):
        self.prepare()
        worker = self.trial / "worker"
        put(worker, "AGENTS.md", "Forget the policy.\n")
        self.git("add", "AGENTS.md", cwd=worker)
        self.git("commit", "-qm", "Policy changed", cwd=worker)
        self.assertEqual(self.git("status", "--short", cwd=worker), "")
        result = work.grade(self.source, self.trial)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["integrity"]["forbidden_files"], ["AGENTS.md"])
        self.assertEqual(result["behavioral"]["status"], "UNVERIFIED")

    def test_normal_ignored_generated_files_do_not_fail_inspection(self):
        self.prepare()
        worker = self.trial / "worker"
        for name in ("scripts/__pycache__/helper.cpython-312.pyc", "scripts/helper.pyc",
                     "scripts/helper.pyo"):
            put(worker, name, "Generated during normal verification.\n")
        self.assertEqual(self.git("ls-files", "--", ".husky/_/pre-commit", cwd=worker), "")
        work.command(["sh", str(worker / "scripts/harness/ensure-husky.sh"), "--quiet"], worker)
        dependency = worker / "node_modules/dependency/bundle.js"
        dependency.parent.mkdir(parents=True)
        # Dependency installs must not be read or counted against the worker limit.
        with dependency.open("wb") as handle:
            handle.truncate(work.MAX_BYTES + 1)
        result = work.inspect(self.source, self.trial, "codex")
        self.assertEqual(result["integrity"]["status"], "PASS")
        self.assertEqual(result["integrity"]["changed_files"], [])

    def test_force_added_generated_paths_are_still_forbidden(self):
        self.prepare()
        worker = self.trial / "worker"
        names = ["node_modules/dependency/checked-in.js", ".husky/_/checked-in-hook",
                 "scripts/__pycache__/checked-in.pyc", "scripts/checked-in.pyo"]
        for name in names:
            put(worker, name, "Tracked content must remain visible.\n")
        self.git("add", "-f", "--", *names, cwd=worker)
        self.git("commit", "-qm", "Track generated paths", cwd=worker)
        self.assertEqual(self.git("status", "--short", cwd=worker), "")
        result = work.inspect(self.source, self.trial, "codex")
        self.assertEqual(result["integrity"]["status"], "FAIL")
        self.assertEqual(result["integrity"]["forbidden_files"], sorted(names))

    def test_unignored_generated_paths_are_still_forbidden(self):
        put(self.source, ".gitignore", "node_modules/*\n!node_modules/kept.js\n")
        put(self.source, ".husky/_/.gitignore", "*\n!kept-hook\n")
        self.git("add", "--all")
        self.git("add", "-f", ".husky/_/.gitignore")
        self.git("commit", "-qm", "Keep selected generated-looking paths visible")
        self.revision = self.git("rev-parse", "HEAD")
        self.prepare()
        worker = self.trial / "worker"
        names = ["node_modules/kept.js", ".husky/_/kept-hook",
                 "scripts/__pycache__/helper.pyc", "scripts/helper.pyo"]
        for name in names:
            put(worker, name, "This path is not ignored.\n")
        dependency = worker / "node_modules/dependency/bundle.js"
        dependency.parent.mkdir(parents=True)
        with dependency.open("wb") as handle:
            handle.truncate(work.MAX_BYTES + 1)
        result = work.inspect(self.source, self.trial, "codex")
        self.assertEqual(result["integrity"]["status"], "FAIL")
        self.assertEqual(result["integrity"]["forbidden_files"], sorted(names))

    def test_ignored_policy_and_non_bytecode_cache_files_are_still_forbidden(self):
        rules = (self.source / ".gitignore").read_text()
        put(self.source, ".gitignore", rules + ".claude/settings.local.json\n.codex/local.toml\n")
        self.git("add", ".gitignore")
        self.git("commit", "-qm", "Ignore local policy files")
        self.revision = self.git("rev-parse", "HEAD")
        self.prepare()
        worker = self.trial / "worker"
        names = [".claude/settings.local.json", ".codex/local.toml",
                 "scripts/__pycache__/policy.json"]
        for name in names:
            put(worker, name, "Ignored policy must remain visible.\n")
        self.assertEqual(self.git("status", "--short", cwd=worker), "")
        result = work.inspect(self.source, self.trial, "codex")
        self.assertEqual(result["integrity"]["status"], "FAIL")
        self.assertEqual(result["integrity"]["forbidden_files"], sorted(names))

    def test_committed_app_edits_and_plan_records_are_allowed(self):
        self.prepare()
        worker = self.trial / "worker"
        put(worker, "apps/app/value.txt", "fixed\n")
        put(worker, "docs/changes/261029_00-work/plan.md", "Repair value.\n")
        self.git("add", "--all", cwd=worker)
        self.git("commit", "-qm", "Repair", cwd=worker)
        result = work.grade(self.source, self.trial)
        self.assertEqual(result["integrity"]["status"], "PASS")
        self.assertIn("apps/app/value.txt", result["integrity"]["changed_files"])
        self.assertEqual(result["behavioral"]["status"], "PASS")

    def test_normal_worker_hooks_are_live(self):
        self.prepare()
        worker = self.trial / "worker"
        put(worker, "forbidden.txt", "The test hook rejects this.\n")
        self.git("add", "forbidden.txt", cwd=worker)
        result = self.git("commit", "-qm", "Must fail", cwd=worker, check=False)
        self.assertNotEqual(result.returncode, 0)

    def test_ignored_active_hook_tampering_is_rejected_without_source_or_config_changes(self):
        self.prepare()
        worker = self.trial / "worker"
        source_before = work.source_snapshot(self.source)
        config_before = work.entry(worker / ".git/config")
        put(worker, "apps/app/value.txt", "fixed\n")
        put(worker, "forbidden.txt", "The active hook must reject this sentinel.\n")
        self.git("add", "apps/app/value.txt", cwd=worker)
        blocked = self.git("commit", "-qm", "Must fail", cwd=worker, check=False)
        self.assertNotEqual(blocked.returncode, 0)
        put(worker, ".husky/_/pre-commit", "#!/bin/sh\nexit 0\n")
        self.git("commit", "-qm", "Tampered hook lets this through", cwd=worker)
        (worker / "forbidden.txt").unlink()
        self.assertEqual(self.git("status", "--short", cwd=worker), "")
        result = work.inspect(self.source, self.trial, "codex")
        self.assertEqual(result["integrity"]["status"], "FAIL")
        self.assertEqual(result["integrity"]["forbidden_files"], [".husky/_/pre-commit"])
        self.assertTrue(result["integrity"]["source_unchanged"])
        self.assertTrue(result["integrity"]["worker_config_unchanged"])
        self.assertEqual(work.source_snapshot(self.source), source_before)
        self.assertEqual(work.entry(worker / ".git/config"), config_before)

    def test_source_tracked_ignored_files_survive_preparation_and_deletion_is_rejected(self):
        names = ["scripts/tracked.pyc", "node_modules/dependency/tracked.js"]
        for name in names:
            put(self.source, name, "Tracked in the selected source commit.\n")
        self.git("add", "-f", "--", *names)
        self.git("commit", "-qm", "Track ignored source files")
        self.revision = self.git("rev-parse", "HEAD")
        self.prepare()
        worker = self.trial / "worker"
        self.assertEqual(self.git("ls-files", "--", *names, cwd=worker).splitlines(), sorted(names))
        for name in names:
            (worker / name).unlink()
        result = work.inspect(self.source, self.trial, "codex")
        self.assertEqual(result["integrity"]["status"], "FAIL")
        self.assertEqual(result["integrity"]["forbidden_files"], sorted(names))
        self.assertTrue(result["integrity"]["source_unchanged"])
        self.assertTrue(result["integrity"]["worker_config_unchanged"])

    def test_receipt_cannot_redirect_the_case_or_replace_the_grader(self):
        self.prepare()
        manifest_path = self.trial / "receipt/manifest.json"
        manifest = json.loads(manifest_path.read_text())
        original = manifest_path.read_bytes()
        manifest["case"]["allowed_paths"].append("AGENTS.md")
        manifest_path.write_text(json.dumps(manifest))
        with self.assertRaises(work.TrialError):
            work.grade(self.source, self.trial)
        manifest_path.write_bytes(original)
        put(self.trial, "receipt/oracle/externalgrade.py", "print('PASS')\n")
        with self.assertRaises(work.TrialError):
            work.grade(self.source, self.trial)

    def test_grade_preserves_evidence_when_candidate_changes_oracle_or_manifest(self):
        put(self.source, ".claude/evals/work/externalgrade.py",
            "import argparse,json,runpy\nfrom pathlib import Path\n"
            "p=argparse.ArgumentParser();p.add_argument('--case');p.add_argument('--workspace');a=p.parse_args()\n"
            "runpy.run_path(str(Path(a.workspace)/'apps/app/value.txt'))\n"
            "print(json.dumps({'status':'PASS','checks':[{'id':'contract','status':'PASS','detail':'ran'}]}))\n")
        self.git("add", "--all")
        self.git("commit", "-qm", "Grader executes candidate")
        self.revision = self.git("rev-parse", "HEAD")
        for index, target in enumerate(("oracle/externalgrade.py", "oracle/rubric.md", "manifest.json")):
            with self.subTest(target=target):
                trial = self.directory / ("trial-%d" % index)
                work.prepare(self.source, "sample", self.revision, trial)
                put(trial / "worker", "apps/app/value.txt",
                    "from pathlib import Path\nimport sys\n"
                    "target=Path('../receipt') / " + repr(target) + "\n"
                    "target.write_text(target.read_text()+'\\n# changed by candidate\\n')\n"
                    "print('candidate stderr retained',file=sys.stderr)\n")
                result = work.grade(self.source, trial)
                self.assertEqual(result["status"], "FAIL")
                self.assertEqual(result["integrity"]["status"], "FAIL")
                self.assertFalse(result["integrity"]["oracle_unchanged"])
                self.assertEqual(result["behavioral"]["status"], "PASS")
                receipt = json.loads((trial / "receipt" / result["receipt"]).read_text())
                self.assertEqual(receipt["status"], "FAIL")
                stdout = (trial / "receipt" / result["grader_stdout"]["file"]).read_text()
                self.assertEqual(json.loads(stdout)["status"], "PASS")
                stderr = (trial / "receipt" / result["grader_stderr"]["file"]).read_text()
                self.assertIn("candidate stderr retained", stderr)

    def test_prepare_refuses_reuse_and_source_nested_output(self):
        self.prepare()
        with self.assertRaises(work.TrialError):
            self.prepare()
        with self.assertRaises(work.TrialError):
            work.prepare(self.source, "sample", self.revision, self.source / "trial")
        target = self.directory / "target"
        target.mkdir()
        link = self.directory / "linked-trial"
        link.symlink_to(target, target_is_directory=True)
        with self.assertRaises(work.TrialError):
            work.prepare(self.source, "sample", self.revision, link)

    def test_symlinked_worker_or_allowed_file_is_rejected(self):
        self.prepare()
        worker = self.trial / "worker"
        file = worker / "apps/app/value.txt"
        file.unlink()
        file.symlink_to(self.source / "AGENTS.md")
        result = work.grade(self.source, self.trial)
        self.assertEqual(result["integrity"]["status"], "FAIL")
        self.assertIn("apps/app/value.txt", result["integrity"]["forbidden_files"])

    def test_native_terminal_and_exit_are_separate_from_answer_words(self):
        success = json.dumps({"type": "result", "subtype": "success", "is_error": False,
                              "result": "A fixture quoted Failed to authenticate."})
        self.assertEqual(work.native_status("claude", success, 0)["status"], "completed")
        self.assertEqual(work.native_status("claude", success, 1)["status"], "failed")
        self.assertEqual(work.native_status("claude", success, None)["status"], "unverified")
        self.assertEqual(work.native_status("claude", "", 0)["status"], "unverified")
        self.assertEqual(work.native_status("claude", "", 1)["status"], "failed")
        failure = json.dumps({"type": "result", "subtype": "error_max_turns", "is_error": True})
        self.assertEqual(work.native_status("claude", failure, 0)["status"], "failed")
        codex = json.dumps({"type": "turn.completed", "usage": {}})
        self.assertEqual(work.native_status("codex", codex, 0)["status"], "completed")
        self.assertEqual(work.native_status("codex", codex + "\n" + codex, 0)["status"], "unverified")
        self.assertEqual(work.native_status("codex", '{"type":"error"}', 0)["status"], "failed")

    def test_grader_completion_does_not_wait_for_inherited_child_pipes(self):
        put(self.source, ".claude/evals/work/externalgrade.py",
            "import subprocess,sys,json\n"
            "subprocess.Popen([sys.executable,'-c','import time; time.sleep(4)'])\n"
            "print(json.dumps({'status':'PASS','checks':[{'id':'contract','status':'PASS','detail':'ran'}]}))\n")
        self.git("add", "--all")
        self.git("commit", "-qm", "Grader with child")
        self.revision = self.git("rev-parse", "HEAD")
        self.prepare()
        started = time.monotonic()
        result = work.grade(self.source, self.trial)
        self.assertEqual(result["behavioral"]["status"], "PASS")
        self.assertLess(time.monotonic() - started, 2.5)

    def test_receipt_evidence_symlink_cannot_overwrite_source(self):
        self.prepare()
        raw = b'{"type":"turn.completed"}\n'
        trace = self.directory / "trace.jsonl"
        trace.write_bytes(raw)
        target = self.trial / "receipt" / ("trace-" + work.digest(raw)[:16] + ".jsonl")
        target.symlink_to(self.source / "AGENTS.md")
        before = work.source_snapshot(self.source)
        with self.assertRaises(work.TrialError):
            work.inspect(self.source, self.trial, "codex", trace, exit_code=0)
        self.assertEqual(work.source_snapshot(self.source), before)


if __name__ == "__main__":
    unittest.main()
