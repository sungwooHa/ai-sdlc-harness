#!/usr/bin/env python3
"""Prepare, inspect and externally grade real work without launching a model.

Native hosts retain their normal tools, settings and human approval. Receipts live outside
the worker; this is context separation and post-run integrity checking, not an OS sandbox.
Behavioral grading does not certify browser execution, independent review or productivity.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import signal
import stat
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
WORK = ".claude/evals/work"
CATALOG = WORK + "/cases.json"
GRADER = WORK + "/externalgrade.py"
RUBRIC = WORK + "/rubric.md"
STUBS = ("scripts/test/run-evals.test.py", "scripts/test/work-evals.test.py",
         "scripts/test/work-cases.test.py")
MAX_BYTES = 128 * 1024 * 1024
MAX_FILES = 20000


class TrialError(ValueError):
    pass


def clean_env():
    env = {key: value for key, value in os.environ.items()
           if not key.startswith("GIT_") and key != "HARNESS_PLAN_APPROVED"}
    env.update(GIT_OPTIONAL_LOCKS="0", PYTHONDONTWRITEBYTECODE="1")
    return env


def command(args, cwd, timeout=30):
    result = subprocess.run(args, cwd=cwd, env=clean_env(), capture_output=True, timeout=timeout)
    if result.returncode:
        raise TrialError(f"{args[0]} failed (exit {result.returncode}); inspect the operation separately")
    return result.stdout


def git(root, *args):
    return command(["git", *args], root).decode("utf-8", errors="surrogateescape").strip()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def fingerprint(value):
    return digest(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def inside(path, parent):
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def relative(name):
    if not isinstance(name, str) or not name or "\\" in name:
        raise TrialError("expected a nonempty relative POSIX path")
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in ("", ".", "..") for part in name.split("/")):
        raise TrialError("path must stay within its declared directory")
    return path


def entry(path):
    try:
        info = path.lstat()
    except FileNotFoundError:
        return {"type": "missing"}
    mode = stat.S_IMODE(info.st_mode)
    if stat.S_ISLNK(info.st_mode):
        return {"type": "link", "target": os.readlink(path), "mode": mode}
    if not stat.S_ISREG(info.st_mode):
        raise TrialError("unsupported entry in a file inventory")
    if info.st_size > MAX_BYTES:
        raise TrialError("inventory file exceeds the size limit")
    return {"type": "file", "sha256": digest(path.read_bytes()), "mode": mode}


def source_snapshot(root):
    names = command(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], root)
    paths = sorted(set(names.decode("utf-8", errors="surrogateescape").split("\0")) - {""})
    if len(paths) > MAX_FILES:
        raise TrialError("source inventory exceeds the file limit")
    files = {}
    for name in paths:
        relative(name)
        files[name] = entry(root / name)
    metadata = {}
    for name in ("HEAD", "index", "config"):
        path = Path(git(root, "rev-parse", "--git-path", name))
        metadata[name] = entry(path if path.is_absolute() else root / path)
    return {"head": git(root, "rev-parse", "HEAD"), "metadata": metadata, "files": files}


def inventory(root):
    result, size = {}, 0
    for directory, folders, files in os.walk(root, followlinks=False):
        base = Path(directory)
        if base == root:
            folders[:] = [name for name in folders if name != ".git"]
        for name in list(folders):
            if (base / name).is_symlink():
                files.append(name)
                folders.remove(name)
        for name in files:
            path = base / name
            key = path.relative_to(root).as_posix()
            result[key] = entry(path)
            if result[key]["type"] == "file":
                size += path.stat().st_size
            if len(result) > MAX_FILES or size > MAX_BYTES:
                raise TrialError("worker inventory exceeds its size limit")
    return result


def changed(before, after):
    return sorted(path for path in set(before) | set(after) if before.get(path) != after.get(path))


def revision(root, ref):
    if not ref or ref.startswith("-"):
        raise TrialError("invalid source revision")
    value = git(root, "rev-parse", "--verify", ref + "^{commit}")
    if not re.fullmatch(r"[0-9a-f]{40,64}", value):
        raise TrialError("source revision did not resolve to a commit")
    return value


def source_file(root, sha, name):
    relative(name)
    return command(["git", "show", sha + ":" + name], root)


def case_at(root, sha, case_id):
    catalog = json.loads(source_file(root, sha, CATALOG))
    if catalog.get("version") != 1 or not isinstance(catalog.get("cases"), list):
        raise TrialError("unsupported work-case catalog")
    matches = [item for item in catalog["cases"] if item.get("id") == case_id]
    if len(matches) != 1:
        raise TrialError("case must occur exactly once in the selected revision")
    case = matches[0]
    if not isinstance(case.get("prompt"), str) or not case["prompt"].strip():
        raise TrialError("case requires an ordinary user prompt")
    relative(case["fixture"])
    allowed = case.get("allowed_paths")
    if not isinstance(allowed, list) or not allowed:
        raise TrialError("case requires allowed_paths")
    for name in allowed:
        relative(name)
        if not name.startswith(("apps/app/", "docs/changes/")):
            raise TrialError("work cases may modify only their app and change records")
    if type(case.get("requires_browser")) is not bool:
        raise TrialError("case requires a boolean requires_browser")
    return case


def omitted(name):
    return name == ".claude/evals" or name.startswith(".claude/evals/") or (
        name.startswith("docs/changes/") and name.split("/")[2][:1].isdigit())


def export(root, sha, destination):
    archive = command(["git", "archive", "--format=tar", sha], root)
    if len(archive) > MAX_BYTES:
        raise TrialError("source export exceeds the size limit")
    links = []
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as bundle:
        for item in bundle.getmembers():
            name = item.name.rstrip("/")
            relative(name)
            if omitted(name):
                continue
            if ".git" in PurePosixPath(name).parts:
                raise TrialError("Git metadata cannot be exported into a worker")
            path = destination / name
            if item.isdir():
                path.mkdir(parents=True, exist_ok=True)
            elif item.isfile():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(bundle.extractfile(item).read())
                path.chmod(item.mode & 0o777)
            elif item.issym():
                links.append((path, item.linkname))
            else:
                raise TrialError("source export contains an unsupported entry")
    for path, target in links:
        resolved = (path.parent / target).resolve()
        if (Path(target).is_absolute() or not inside(resolved, destination)
                or ".git" in resolved.relative_to(destination).parts):
            raise TrialError("source symlink escapes the worker")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.symlink_to(target)
    for name in STUBS:
        if (destination / name).exists():
            (destination / name).write_text(
                '#!/usr/bin/env python3\nprint("SKIP: external work-trial oracle is not part of the worker")\n',
                encoding="utf-8")


def write_private(path, data):
    if path.is_symlink():
        raise TrialError("receipt output may not be a symlink")
    if path.exists():
        if not path.is_file() or path.read_bytes() != data:
            raise TrialError("receipt output already exists with different contents")
        return
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as error:
        raise TrialError("receipt output was created concurrently") from error
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(data)


def write_json(path, data):
    write_private(path, (json.dumps(data, ensure_ascii=True, indent=2) + "\n").encode("utf-8"))


def save_receipt(trial, kind, data):
    receipts = trial / "receipt"
    index = len(list(receipts.glob("*-" + kind + ".json"))) + 1
    path = receipts / f"{index:04d}-{kind}.json"
    while path.exists() or path.is_symlink():
        index += 1
        path = receipts / f"{index:04d}-{kind}.json"
    write_json(path, data)
    return path.name


def prepare(root, case_id, ref, output, task_ref=None):
    root = root.resolve(strict=True)
    if output.exists() or output.is_symlink():
        raise TrialError("output must be a new directory")
    output = output.parent.resolve(strict=True) / output.name
    if inside(output, root) or inside(root, output):
        raise TrialError("output must be outside the source repository")
    sha = revision(root, ref)
    task_sha = revision(root, task_ref) if task_ref else sha
    case = case_at(root, task_sha, case_id)
    before = source_snapshot(root)
    output.mkdir(mode=0o700, parents=False)
    worker, receipts = output / "worker", output / "receipt"
    worker.mkdir(mode=0o700)
    receipts.mkdir(mode=0o700)
    try:
        export(root, sha, worker)
        init = worker / "scripts/harness/init-template.sh"
        if init.is_file():
            command(["sh", str(init), "--project-name", "worktrial", "--prefix", "trial",
                     "--app", "app"], worker)
        fixture_prefix = WORK + "/fixtures/" + case["fixture"] + "/"
        names = git(root, "ls-tree", "-r", "--name-only", task_sha, "--", fixture_prefix).splitlines()
        if not names:
            raise TrialError("selected fixture has no committed files")
        fixture_files = {}
        for name in names:
            target = worker / "apps/app" / name[len(fixture_prefix):]
            relative(target.relative_to(worker).as_posix())
            mode = git(root, "ls-tree", task_sha, "--", name).split()[0]
            if mode not in ("100644", "100755"):
                raise TrialError("fixture must contain regular files only")
            target.parent.mkdir(parents=True, exist_ok=True)
            content = source_file(root, task_sha, name)
            target.write_bytes(content)
            fixture_files[name[len(fixture_prefix):]] = digest(content)
            target.chmod(0o755 if mode == "100755" else 0o644)
        oracle = receipts / "oracle"
        oracle.mkdir(mode=0o700)
        grader = source_file(root, task_sha, GRADER)
        rubric = source_file(root, task_sha, RUBRIC)
        (oracle / "externalgrade.py").write_bytes(grader)
        (oracle / "externalgrade.py").chmod(0o600)
        write_private(oracle / "rubric.md", rubric)
        command(["git", "init", "-q", "--template=", "--initial-branch=main"], worker)
        for key, value in (("user.name", "Work trial"), ("user.email", "trial@example.invalid"),
                           ("commit.gpgsign", "false"), ("core.hooksPath", ".husky/_")):
            git(worker, "config", key, value)
        bootstrap = worker / "scripts/harness/ensure-husky.sh"
        if not bootstrap.is_file():
            raise TrialError("selected source lacks the normal Husky bootstrap")
        command(["sh", str(bootstrap), "--quiet"], worker)
        git(worker, "add", "--all")
        git(worker, "commit", "-qm", "Initialize work trial")
        after = source_snapshot(root)
        if before != after:
            raise TrialError("source changed during preparation")
        manifest = {
            "version": 1, "source": str(root), "source_revision": sha, "task_revision": task_sha,
            "case": case, "task_catalog_sha256": digest(source_file(root, task_sha, CATALOG)),
            "fixture_sha256": fingerprint(fixture_files), "fixture_files": fixture_files,
            "source_baseline": before, "worker_baseline": inventory(worker),
            "worker_config": entry(worker / ".git/config"), "oracle_sha256": digest(grader),
            "rubric_sha256": digest(rubric),
            "prepared_head": git(worker, "rev-parse", "HEAD"),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "exclusions": [".claude/evals/**", "docs/changes/<dated folders>"],
            "stubbed_tests": [name for name in STUBS if (worker / name).exists()],
            "limits": ["No model, approval, server or grader is run by prepare.",
                       "Independent Git and post-run checks are not an OS sandbox.",
                       "Existing host settings may reveal evaluation context; this is not perfect blinding."],
        }
        write_json(receipts / "manifest.json", manifest)
        (output / "prompt.txt").write_text(case["prompt"] + "\n", encoding="utf-8")
        (output / "prompt.txt").chmod(0o600)
        return {"status": "PREPARED", "trial": str(output), "workspace": str(worker),
                "prompt": str(output / "prompt.txt"), "source_revision": sha,
                "task_revision": task_sha, "case": case_id}
    except BaseException:
        # Keep failed setup for diagnosis; never overwrite or erase a trial on retry.
        write_json(receipts / "preparation-error.json", {"status": "ERROR",
                   "source_unchanged": source_snapshot(root) == before})
        raise


def load_trial(root, trial):
    if trial.is_symlink():
        raise TrialError("trial itself may not be a symlink")
    root, trial = root.resolve(strict=True), trial.resolve(strict=True)
    if inside(trial, root):
        raise TrialError("trial must be an external directory")
    for name in ("worker", "receipt", "receipt/manifest.json", "receipt/oracle",
                 "receipt/oracle/externalgrade.py", "receipt/oracle/rubric.md", "worker/.git"):
        if (trial / name).is_symlink():
            raise TrialError("trial control paths may not be symlinks")
    manifest = json.loads((trial / "receipt/manifest.json").read_text())
    if manifest.get("version") != 1 or manifest.get("source") != str(root):
        raise TrialError("trial does not belong to this source repository")
    sha, task_sha = manifest.get("source_revision", ""), manifest.get("task_revision", "")
    if not all(re.fullmatch(r"[0-9a-f]{40,64}", value) for value in (sha, task_sha)):
        raise TrialError("trial has an invalid committed source")
    if revision(root, sha) != sha:
        raise TrialError("trial source revision is unavailable")
    case = case_at(root, task_sha, manifest["case"]["id"])
    expected = source_file(root, task_sha, GRADER)
    rubric = source_file(root, task_sha, RUBRIC)
    if (case != manifest["case"] or digest(expected) != manifest["oracle_sha256"]
            or digest(source_file(root, task_sha, CATALOG)) != manifest["task_catalog_sha256"]
            or digest(rubric) != manifest["rubric_sha256"]):
        raise TrialError("trial case or oracle declaration differs from its committed source")
    if ((trial / "receipt/oracle/externalgrade.py").read_bytes() != expected
            or (trial / "receipt/oracle/rubric.md").read_bytes() != rubric):
        raise TrialError("frozen external grader was changed")
    return manifest


def integrity(root, trial, manifest):
    worker = trial / "worker"
    after = inventory(worker)
    differences = changed(manifest["worker_baseline"], after)
    allowed = manifest["case"]["allowed_paths"] + ["docs/changes/**"]
    forbidden = [name for name in differences
                 if not any(fnmatch.fnmatchcase(name, pattern) for pattern in allowed)
                 or after.get(name, {}).get("type") == "link"]
    config_same = entry(worker / ".git/config") == manifest["worker_config"]
    source_same = source_snapshot(root) == manifest["source_baseline"]
    return {"status": "PASS" if not forbidden and config_same and source_same else "FAIL",
            "source_unchanged": source_same, "worker_config_unchanged": config_same,
            "changed_files": differences, "forbidden_files": forbidden,
            "worker_fingerprint": fingerprint(after),
            "note": "Checks include committed edits; Git status alone is not used."}


def native_status(host, trace, exit_code):
    if not trace:
        return {"status": "failed" if exit_code not in (None, 0) else "unverified",
                "reason": "no native trace supplied", "exit_code": exit_code}
    events, malformed = [], 0
    for line in trace.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
            if isinstance(event, dict):
                events.append(event)
            else:
                malformed += 1
        except ValueError:
            malformed += 1
    if host == "claude":
        terminals = [event for event in events if event.get("type") == "result"]
        failure = any(event.get("is_error") or event.get("subtype") != "success" for event in terminals)
    else:
        terminals = [event for event in events if event.get("type") in ("turn.completed", "turn.failed")]
        failure = any(event.get("type") in ("turn.failed", "error") for event in events)
    if exit_code not in (None, 0) or failure:
        state = "failed"
    elif len(terminals) == 1 and not malformed and exit_code == 0:
        state = "completed"
    else:
        state = "unverified"
    return {"status": state, "event_count": len(events), "terminal_count": len(terminals),
            "malformed_lines": malformed, "exit_code": exit_code,
            "note": "Native completion does not establish task correctness or browser execution."}


def inspect(root, trial, host, trace=None, stderr=None, exit_code=None):
    manifest = load_trial(root, trial)
    trial = trial.resolve(strict=True)
    raw = b""
    evidence = {}
    for label, path in (("trace", trace), ("stderr", stderr)):
        if path is None:
            continue
        if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
            raise TrialError("evidence must be a bounded regular file")
        data = path.read_bytes()
        name = label + "-" + digest(data)[:16] + (".jsonl" if label == "trace" else ".txt")
        target = trial / "receipt" / name
        write_private(target, data)
        evidence[label] = {"file": name, "sha256": digest(data)}
        if label == "trace":
            raw = data
    native = native_status(host, raw.decode("utf-8", errors="replace"), exit_code)
    verified = integrity(root, trial, manifest)
    result = {"status": "FAIL" if verified["status"] == "FAIL" or native["status"] == "failed"
              else "NEEDS_REVIEW", "host": host, "native": native, "integrity": verified,
              "evidence": evidence, "behavioral": "unverified", "independent_review": "unverified",
              "browser": "unverified" if manifest["case"]["requires_browser"] else "not_applicable"}
    result["receipt"] = save_receipt(trial, "inspect", result)
    return result


def grade(root, trial):
    manifest = load_trial(root, trial)
    trial = trial.resolve(strict=True)
    verified = integrity(root, trial, manifest)
    result = {"status": "FAIL", "integrity": verified, "behavioral": {"status": "UNVERIFIED"},
              "independent_review": "unverified",
              "browser": "unverified" if manifest["case"]["requires_browser"] else "not_applicable"}
    if verified["status"] == "PASS":
        # The grader is committed and frozen outside the worker. It executes candidate code,
        # so this still requires the operator's normal permissions; it is not containment.
        timed_out = False
        with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
            process = subprocess.Popen([sys.executable, str(trial / "receipt/oracle/externalgrade.py"),
                                        "--case", manifest["case"]["id"], "--workspace", str(trial / "worker")],
                                       cwd=trial / "worker", env=clean_env(), stdin=subprocess.DEVNULL,
                                       stdout=stdout_file, stderr=stderr_file, start_new_session=True)
            try:
                process.wait(timeout=60)
            except subprocess.TimeoutExpired:
                timed_out = True
            finally:
                # A completed grader can leave a child holding stdout open. Reap our process
                # group without waiting for pipe EOF; deliberately detached children are not covered.
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
            stdout_file.seek(0)
            stderr_file.seek(0)
            stdout, stderr = stdout_file.read(MAX_BYTES + 1), stderr_file.read(MAX_BYTES + 1)
        if timed_out:
            result["behavioral"] = {"status": "ERROR", "reason": "external grader timed out"}
        elif len(stdout) > MAX_BYTES or len(stderr) > MAX_BYTES:
            result["behavioral"] = {"status": "ERROR", "reason": "external grader output exceeded limit"}
        else:
            try:
                verdict = json.loads(stdout)
                valid = (isinstance(verdict, dict) and verdict.get("status") in ("PASS", "FAIL")
                         and isinstance(verdict.get("checks"), list) and bool(verdict["checks"])
                         and all(isinstance(item, dict) and item.get("status") in ("PASS", "FAIL")
                                 and isinstance(item.get("id"), str) and item["id"]
                                 and isinstance(item.get("detail"), str) for item in verdict["checks"]))
                if not valid:
                    raise ValueError("invalid external grader schema")
                expected = 0 if verdict.get("status") == "PASS" else 1
                if process.returncode != expected or (
                        verdict["status"] == "PASS" and any(item["status"] != "PASS" for item in verdict["checks"])):
                    raise ValueError("grader result and exit code disagree")
                result["behavioral"] = verdict
            except (ValueError, TypeError, AttributeError):
                result["behavioral"] = {"status": "ERROR", "reason": "invalid external grader result"}
        for label, data in (("stdout", stdout), ("stderr", stderr)):
            name = "grader-" + label + "-" + digest(data)[:16] + ".txt"
            target = trial / "receipt" / name
            write_private(target, data)
            result["grader_" + label] = {"file": name, "sha256": digest(data)}
        result["integrity"] = integrity(root, trial, manifest)
        try:
            if load_trial(root, trial) != manifest:
                raise TrialError("trial manifest changed during grading")
            result["integrity"]["oracle_unchanged"] = True
        except (TrialError, OSError, ValueError, TypeError, KeyError, AttributeError,
                subprocess.SubprocessError) as error:
            # Retain the observed verdict and raw output even if candidate execution changed
            # the oracle or its declaration; those results cannot establish an intact trial.
            result["integrity"].update(status="FAIL", oracle_unchanged=False,
                                       oracle_error=str(error))
        if result["behavioral"]["status"] == "PASS" and result["integrity"]["status"] == "PASS":
            result["status"] = "NEEDS_REVIEW"
    result["receipt"] = save_receipt(trial, "grade", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    setup = commands.add_parser("prepare")
    setup.add_argument("--case", required=True)
    setup.add_argument("--ref", default="HEAD")
    setup.add_argument("--task-ref", help="task asset commit; defaults to --ref")
    setup.add_argument("--output", type=Path, required=True)
    check = commands.add_parser("inspect")
    check.add_argument("--trial", type=Path, required=True)
    check.add_argument("--host", choices=("claude", "codex"), required=True)
    check.add_argument("--trace", type=Path)
    check.add_argument("--stderr", type=Path)
    check.add_argument("--exit-code", type=int)
    grading = commands.add_parser("grade")
    grading.add_argument("--trial", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.action == "prepare":
            result = prepare(ROOT, args.case, args.ref, args.output, args.task_ref)
        elif args.action == "inspect":
            result = inspect(ROOT, args.trial, args.host, args.trace, args.stderr, args.exit_code)
        else:
            result = grade(ROOT, args.trial)
    except (TrialError, OSError, ValueError, subprocess.SubprocessError) as error:
        print(json.dumps({"status": "ERROR", "reason": str(error)}))
        return 2
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return {"PREPARED": 0, "NEEDS_REVIEW": 3, "FAIL": 1}[result["status"]]


if __name__ == "__main__":
    sys.exit(main())
