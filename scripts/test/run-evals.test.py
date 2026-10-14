#!/usr/bin/env python3
"""Regression tests for scripts/harness/run-evals.py, without model use.

The runner is copied into a throwaway git repository with its own cases.jsonl, and a fake `claude`
first on PATH stands in for the CLI. Checks: the default model is the `sonnet` alias; a new file in a
new directory is seen by `files_changed_not_matching`; `--runs N` prints k/N and passes a case only
when every run passes. The child gets the CLI's subscription login only: the variables that would route
it elsewhere are left out, the OAuth token stays, `--login` and `--api` do not exist, and an
authentication failure aborts with a login hint.

Each run gets its own copy: HEAD's tracked files in a new repository with no remote and no trace of the
real checkout, the agreement gate's hooks left out and every other hook kept. `--mutate` removes each
case's declared instruction (`measures`) and expects the case to fail: KILLED, or SURVIVED with the
agent's words; a declaration that is missing or does not match exactly once is an error. `--jobs N` runs
copies side by side and prints in case order. The real checkout and the temp directory are left as found.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RUNNER = REPO / "scripts/harness/run-evals.py"

# Logs its argv, the ANTHROPIC_/CLAUDE_CODE_ variables it received and what the copy looks like (one line per
# call: the gate's hooks, the other hooks and permissions, remotes, any trace of the real checkout under .git),
# then acts on the prompt: `auth` fails to authenticate, `crash` exits non-zero as a usage limit would, `abs`
# writes a user path into a new directory, `flaky` answers wrongly
# on its second call only, `measured` answers right only while AGENTS.md carries its instruction, `meet-*`
# answers right only when its partner runs at the same time. The user path is split so the fast guard does
# not read it.
FAKE_CLAUDE = """#!/usr/bin/env python3
import json, os, subprocess, sys, time
from pathlib import Path
state = Path(os.environ["FAKE_CLAUDE_STATE"])
with (state / "argv.jsonl").open("a", encoding="utf-8") as log:
    log.write(json.dumps(sys.argv[1:]) + "\\n")
with (state / "env.jsonl").open("a", encoding="utf-8") as log:
    log.write(json.dumps(sorted(k for k in os.environ if k.startswith(("ANTHROPIC_", "CLAUDE_CODE_")))) + "\\n")
prompt = sys.argv[sys.argv.index("-p") + 1]
settings_file = Path(".claude/settings.json")
settings = json.loads(settings_file.read_text(encoding="utf-8")) if settings_file.is_file() else {}
commands = [h["command"] for groups in settings.get("hooks", {}).values() for g in groups for h in g["hooks"]]
root = os.environ["FAKE_ROOT"].encode()
dot_git = Path(".git")  # a worktree's .git is a file naming the real checkout
git_files = [dot_git] if dot_git.is_file() else [p for p in dot_git.rglob("*") if p.is_file()]
with (state / "copies.jsonl").open("a", encoding="utf-8") as log:
    log.write(json.dumps({
        "prompt": prompt, "cwd": os.getcwd(),
        "gate_hooks": sum("agreement-gate.py" in c for c in commands),
        "kept": sorted(c for c in commands if "agreement-gate.py" not in c), "permissions": settings.get("permissions"),
        "remotes": subprocess.run(["git", "remote", "-v"], capture_output=True, text=True).stdout,
        "root_trace": any(root in p.read_bytes() for p in git_files),
        "clean": subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout == "",
    }) + "\\n")
if prompt == "auth":
    print("Failed to authenticate. Please log in.")
    sys.exit(1)
if prompt == "crash":
    print("Claude usage limit reached.")
    sys.exit(1)
if prompt == "abs":
    Path("newdir").mkdir()
    Path("newdir/a.md").write_text("see /" + "Users/x/notes\\n", encoding="utf-8")
if prompt == "measured":
    print("done" if "Always answer done." in Path("AGENTS.md").read_text(encoding="utf-8") else "wrong")
    sys.exit(0)
if prompt.startswith("meet-"):
    (state / prompt).touch()
    partner = state / ("meet-b" if prompt == "meet-a" else "meet-a")
    deadline = time.monotonic() + 3
    while not partner.exists() and time.monotonic() < deadline:
        time.sleep(0.05)
    print("done" if partner.exists() else "alone")
    sys.exit(0)
calls = state / (prompt + ".calls")
count = int(calls.read_text()) + 1 if calls.exists() else 1
calls.write_text(str(count))
print("wrong" if prompt == "flaky" and count == 2 else "done")
"""

DONE = {"output_matches": "^done$"}
CASES = [
    {"id": "plain", "prompt": "plain", "expect": DONE},
    {"id": "abs", "prompt": "abs", "expect": {"files_changed_not_matching": "/Users/[^/]+/"}},
    {"id": "flaky", "prompt": "flaky", "expect": DONE},
    {"id": "auth", "prompt": "auth", "expect": {}},
    {"id": "measured", "prompt": "measured", "expect": DONE,
     "measures": [{"file": "AGENTS.md", "text": "Always answer done.\n"}]},
    {"id": "survivor", "prompt": "plain", "expect": DONE,
     "measures": [{"file": "AGENTS.md", "text": "Keep it short.\n"}]},
    {"id": "stale", "prompt": "plain", "expect": DONE,
     "measures": [{"file": "AGENTS.md", "text": "A sentence nobody wrote.\n"}]},
    {"id": "crash", "prompt": "crash", "expect": DONE,
     "measures": [{"file": "AGENTS.md", "text": "Keep it short.\n"}]},
    {"id": "meet-a", "prompt": "meet-a", "expect": DONE},
    {"id": "meet-b", "prompt": "meet-b", "expect": DONE},
]
# What would take the child off the subscription login, as claude 2.1.296 reads it (key credentials, workload
# identity, an explicit profile, provider switches, endpoint, socket and custom headers), and the subscription
# OAuth token that must stay. Kept apart from the runner's own list so the test pins it.
OFF_LOGIN = ["ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "CLAUDE_CODE_API_KEY_FILE_DESCRIPTOR",
             "ANTHROPIC_FEDERATION_RULE_ID", "ANTHROPIC_PROFILE", "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX",
             "CLAUDE_CODE_USE_FOUNDRY", "CLAUDE_CODE_USE_ANTHROPIC_AWS", "CLAUDE_CODE_USE_ANTHROPIC_GOOGLE_CLOUD",
             "CLAUDE_CODE_USE_MANTLE", "CLAUDE_CODE_USE_GATEWAY", "ANTHROPIC_BASE_URL", "ANTHROPIC_UNIX_SOCKET",
             "ANTHROPIC_CUSTOM_HEADERS"]
KEPT = ["CLAUDE_CODE_OAUTH_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN_FILE_DESCRIPTOR"]


def load_runner():
    spec = importlib.util.spec_from_file_location("run_evals", RUNNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    runner = load_runner()
    with tempfile.TemporaryDirectory() as temp_dir:
        repo, bin_dir, state = Path(temp_dir) / "repo", Path(temp_dir) / "bin", Path(temp_dir) / "state"
        copies_tmp = Path(temp_dir) / "tmp"
        (repo / "scripts/harness").mkdir(parents=True)
        (repo / ".claude/evals").mkdir(parents=True)
        for path in (bin_dir, state, copies_tmp):
            path.mkdir()
        shutil.copy(RUNNER, repo / "scripts/harness/run-evals.py")
        shutil.copy(REPO / ".claude/settings.json", repo / ".claude/settings.json")  # the real hook wiring
        (repo / "AGENTS.md").write_text("# Rules\n\nAlways answer done.\nKeep it short.\n", encoding="utf-8")
        (repo / ".claude/evals/cases.jsonl").write_text("".join(json.dumps(c) + "\n" for c in CASES), encoding="utf-8")
        (bin_dir / "claude").write_text(FAKE_CLAUDE, encoding="utf-8")
        (bin_dir / "claude").chmod(0o755)

        def git(*args: str) -> subprocess.CompletedProcess[str]:
            return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
                                  cwd=repo, capture_output=True, text=True, errors="replace")

        assert git("init", "-q", "-b", "main").returncode == 0
        git("add", "-A")
        assert git("commit", "-q", "-m", "chore: [eval] fixture").returncode == 0
        assert git("remote", "add", "origin", "https://example.invalid/harness.git").returncode == 0  # not in copies
        probes = (("status", "--porcelain"), ("worktree", "list"), ("branch",), ("remote", "-v"),
                  ("config", "--local", "--list"), ("rev-parse", "HEAD"))
        before = [git(*args).stdout for args in probes]
        env = {**os.environ, **{name: "x" for name in OFF_LOGIN + KEPT}, "TMPDIR": str(copies_tmp),
               "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}", "FAKE_CLAUDE_STATE": str(state),
               "FAKE_ROOT": str(repo.resolve())}
        real = json.loads((REPO / ".claude/settings.json").read_text(encoding="utf-8"))
        kept = sorted(h["command"] for groups in real["hooks"].values() for g in groups for h in g["hooks"]
                      if "agreement-gate.py" not in h["command"])

        def run(*args: str, **extra: str) -> subprocess.CompletedProcess[str]:
            return subprocess.run([sys.executable, "scripts/harness/run-evals.py", *args], cwd=repo,
                                  env={**env, **extra}, capture_output=True, text=True, errors="replace")

        def line(result: subprocess.CompletedProcess[str], case: str) -> str:
            return next((l for l in result.stdout.splitlines() if l.startswith(case + " ")), "")

        def last_copy() -> dict:
            return json.loads((state / "copies.jsonl").read_text(encoding="utf-8").splitlines()[-1])

        result = run("--only", "plain")
        assert result.returncode == 0, f"plain case must pass: {result.stdout}{result.stderr}"
        argv = json.loads((state / "argv.jsonl").read_text(encoding="utf-8").splitlines()[-1])
        assert argv[argv.index("--model") + 1] == "sonnet", f"default model must be the sonnet alias: {argv}"
        seen = set(json.loads((state / "env.jsonl").read_text(encoding="utf-8").splitlines()[-1]))
        assert not seen & set(OFF_LOGIN) and set(KEPT) <= seen, \
            f"the child must get the subscription login only: {sorted(seen)}"
        copy = last_copy()
        assert copy["gate_hooks"] == 0 and copy["kept"] == kept and copy["permissions"] == real["permissions"], \
            f"only the agreement gate is off: {copy}"
        assert copy["remotes"] == "" and not copy["root_trace"] and copy["clean"], \
            f"the copy is a new repository that does not lead back to the checkout: {copy}"
        assert not Path(copy["cwd"]).resolve().is_relative_to(repo.resolve()), copy
        for flag in ("--login", "--api"):
            result = run("--only", "plain", flag)
            assert result.returncode == 2 and "unrecognized arguments" in result.stderr, \
                f"{flag} must not exist: {result.returncode} {result.stderr}"
        result = run("--only", "auth")
        assert result.returncode == 2 and "/login" in result.stdout and "--login" not in result.stdout + result.stderr, \
            f"an authentication failure must abort with the login hint only: {result.stdout}{result.stderr}"

        result = run("--only", "abs")
        assert result.returncode == 1 and "newdir/a.md contains forbidden" in result.stdout, \
            f"a new file in a new directory must be checked: {result.stdout}{result.stderr}"

        result = run("--only", "flaky", "--runs", "3")
        assert result.returncode == 1 and "FAIL 2/3" in line(result, "flaky"), \
            f"one failed run of three must fail the case as 2/3: {result.stdout}{result.stderr}"
        assert (state / "flaky.calls").read_text() == "3", "every run must happen even after a failure"

        # --mutate: the declared instruction is removed from the copy and the case must fail without it.
        result = run("--only", "measured")
        assert result.returncode == 0 and "PASS 1/1" in line(result, "measured"), result.stdout
        result = run("--only", "measured", "--mutate", "--runs", "2")
        assert result.returncode == 0 and "KILLED 2/2" in line(result, "measured"), result.stdout
        assert "output did not match" in result.stdout, f"a kill says why the case failed: {result.stdout}"
        result = run("--only", "crash", "--mutate")  # a run that never answered proves nothing either way
        assert result.returncode == 1 and "ERROR" in line(result, "crash") and "claude exited 1" in result.stdout, \
            result.stdout
        result = run("--only", "survivor", "--mutate")
        assert result.returncode == 1 and "SURVIVED 0/1" in line(result, "survivor") and "| done" in result.stdout, \
            f"a survivor shows the agent's words: {result.stdout}"
        result = run("--only", "stale,plain", "--mutate")
        assert result.returncode == 1 and "ERROR" in line(result, "stale") and "found 0 times" in result.stdout, \
            result.stdout
        assert "ERROR" in line(result, "plain") and "no measures" in result.stdout, result.stdout
        problems = runner.measure_problems(repo, {"measures": [{"file": ".claude/settings.json", "text": '"hooks": {'}]})
        assert problems and "JSON" in problems[0], f"a removal must leave a JSON file readable: {problems}"
        assert runner.measure_problems(repo, CASES[4]) == [], "a sentence that occurs once can be removed"
        for outside in (str(repo / "AGENTS.md"), "../repo/AGENTS.md"):  # never a file outside the copy
            problems = runner.measure_problems(repo, {"measures": [{"file": outside, "text": "Keep it short.\n"}]})
            assert problems and "relative path" in problems[0], (outside, problems)
        # A GIT_DIR or GIT_WORK_TREE in the caller's environment reaches neither the copy's git nor the agent.
        result = run("--only", "plain", GIT_DIR=str(repo / ".git"), GIT_WORK_TREE=str(repo))
        assert result.returncode == 0 and last_copy()["clean"], f"{result.stdout}{result.stderr}"

        # --jobs: two cases that only pass together pass side by side, printed in case order.
        result = run("--only", "meet-a,meet-b", "--jobs", "2")
        assert result.returncode == 0, f"--jobs must run copies at the same time: {result.stdout}{result.stderr}"
        assert result.stdout.index("meet-a ") < result.stdout.index("meet-b "), result.stdout

        after = [git(*args).stdout for args in probes]
        assert after == before, f"the real checkout must stay as it was: {before} -> {after}"
        assert not list(copies_tmp.iterdir()), f"copies must be removed: {list(copies_tmp.iterdir())}"
        # A repository without Claude settings has no hooks to leave out.
        git("rm", "-q", ".claude/settings.json")
        assert git("commit", "-q", "-m", "chore: [eval] no settings").returncode == 0
        result = run("--only", "plain")
        assert result.returncode == 0 and last_copy()["kept"] == [], f"{result.stdout}{result.stderr}"
        assert not list(copies_tmp.iterdir()), f"copies must be removed: {list(copies_tmp.iterdir())}"

    # This repository's cases: each declares the instruction it measures, removable exactly once. Rewording a
    # measured instruction fails here until the case's `measures` follows it (.claude/evals/README.md).
    real = [json.loads(l) for l in (REPO / ".claude/evals/cases.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    stale = {case["id"]: problems for case in real if (problems := runner.measure_problems(REPO, case))}
    assert not stale, f"every case declares the instruction it measures, each text exactly once: {stale}"

    print("PASS: run-evals runner (sonnet alias default, files in new directories, --runs k/N, subscription login "
          "only, isolated copies without the agreement gate, --mutate, --jobs)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
