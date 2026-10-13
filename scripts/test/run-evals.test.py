#!/usr/bin/env python3
"""Regression tests for scripts/harness/run-evals.py, without model use.

The runner is copied into a throwaway git repository with its own cases.jsonl, and a fake `claude`
first on PATH stands in for the CLI. Checks: the default model is the `sonnet` alias; a new file in a
new directory is seen by `files_changed_not_matching`; `--runs N` prints k/N and passes a case only
when every run passes; the runner leaves no worktree behind. The child gets the CLI's subscription login
only: the variables that would route it elsewhere are left out, the OAuth token stays, `--login` and
`--api` do not exist, and an authentication failure aborts with a login hint.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RUNNER = REPO / "scripts/harness/run-evals.py"

# Logs its argv and the ANTHROPIC_/CLAUDE_CODE_ variables it received, then acts on the prompt: `auth`
# fails to authenticate, `abs` writes a user path into a new directory, `flaky` answers wrongly on its
# second call only. The user path is split so the fast guard does not read it.
FAKE_CLAUDE = """#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
state = Path(os.environ["FAKE_CLAUDE_STATE"])
with (state / "argv.jsonl").open("a", encoding="utf-8") as log:
    log.write(json.dumps(sys.argv[1:]) + "\\n")
with (state / "env.jsonl").open("a", encoding="utf-8") as log:
    log.write(json.dumps(sorted(k for k in os.environ if k.startswith(("ANTHROPIC_", "CLAUDE_CODE_")))) + "\\n")
prompt = sys.argv[sys.argv.index("-p") + 1]
if prompt == "auth":
    print("Failed to authenticate. Please log in.")
    sys.exit(1)
if prompt == "abs":
    Path("newdir").mkdir()
    Path("newdir/a.md").write_text("see /" + "Users/x/notes\\n", encoding="utf-8")
calls = state / (prompt + ".calls")
count = int(calls.read_text()) + 1 if calls.exists() else 1
calls.write_text(str(count))
print("wrong" if prompt == "flaky" and count == 2 else "done")
"""

CASES = [
    {"id": "plain", "prompt": "plain", "expect": {"output_matches": "^done$"}},
    {"id": "abs", "prompt": "abs", "expect": {"files_changed_not_matching": "/Users/[^/]+/"}},
    {"id": "flaky", "prompt": "flaky", "expect": {"output_matches": "^done$"}},
    {"id": "auth", "prompt": "auth", "expect": {}},
]
# What would take the child off the subscription login, as claude 2.1.296 reads it (key credentials, workload
# identity, an explicit profile, provider switches, endpoint and socket), and the subscription OAuth token that
# must stay. Kept apart from the runner's own list so the test pins it.
OFF_LOGIN = ["ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "CLAUDE_CODE_API_KEY_FILE_DESCRIPTOR",
             "ANTHROPIC_FEDERATION_RULE_ID", "ANTHROPIC_PROFILE", "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX",
             "CLAUDE_CODE_USE_FOUNDRY", "CLAUDE_CODE_USE_ANTHROPIC_AWS", "CLAUDE_CODE_USE_ANTHROPIC_GOOGLE_CLOUD",
             "CLAUDE_CODE_USE_MANTLE", "CLAUDE_CODE_USE_GATEWAY", "ANTHROPIC_BASE_URL", "ANTHROPIC_UNIX_SOCKET"]
KEPT = ["CLAUDE_CODE_OAUTH_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN_FILE_DESCRIPTOR"]


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        repo, bin_dir, state = Path(temp_dir) / "repo", Path(temp_dir) / "bin", Path(temp_dir) / "state"
        (repo / "scripts/harness").mkdir(parents=True)
        (repo / ".claude/evals").mkdir(parents=True)
        bin_dir.mkdir()
        state.mkdir()
        shutil.copy(RUNNER, repo / "scripts/harness/run-evals.py")
        (repo / ".claude/evals/cases.jsonl").write_text("".join(json.dumps(c) + "\n" for c in CASES), encoding="utf-8")
        (bin_dir / "claude").write_text(FAKE_CLAUDE, encoding="utf-8")
        (bin_dir / "claude").chmod(0o755)

        def git(*args: str) -> subprocess.CompletedProcess[str]:
            return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
                                  cwd=repo, capture_output=True, text=True, errors="replace")

        assert git("init", "-q", "-b", "main").returncode == 0
        git("add", "-A")
        assert git("commit", "-q", "-m", "chore: [eval] fixture").returncode == 0
        env = {**os.environ, **{name: "x" for name in OFF_LOGIN + KEPT},
               "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}", "FAKE_CLAUDE_STATE": str(state)}

        def run(*args: str) -> subprocess.CompletedProcess[str]:
            return subprocess.run([sys.executable, "scripts/harness/run-evals.py", *args], cwd=repo, env=env,
                                  capture_output=True, text=True, errors="replace")

        result = run("--only", "plain")
        assert result.returncode == 0, f"plain case must pass: {result.stdout}{result.stderr}"
        argv = json.loads((state / "argv.jsonl").read_text(encoding="utf-8").splitlines()[-1])
        assert argv[argv.index("--model") + 1] == "sonnet", f"default model must be the sonnet alias: {argv}"
        seen = set(json.loads((state / "env.jsonl").read_text(encoding="utf-8").splitlines()[-1]))
        assert not seen & set(OFF_LOGIN) and set(KEPT) <= seen, \
            f"the child must get the subscription login only: {sorted(seen)}"
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
        line = next((l for l in result.stdout.splitlines() if l.startswith("flaky")), "")
        assert result.returncode == 1 and "2/3" in line and "FAIL" in line, \
            f"one failed run of three must fail the case as 2/3: {result.stdout}{result.stderr}"
        assert (state / "flaky.calls").read_text() == "3", "every run must happen even after a failure"

        worktrees = git("worktree", "list", "--porcelain").stdout
        assert worktrees.count("worktree ") == 1, f"the runner must remove its worktrees: {worktrees}"

    print("PASS: run-evals runner (sonnet alias default, files in new directories, --runs k/N, subscription login only)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
