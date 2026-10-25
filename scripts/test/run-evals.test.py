#!/usr/bin/env python3
"""Regression tests for scripts/harness/run-evals.py, without model use.

The runner is copied into a throwaway git repository with its own cases.jsonl, a fake init script and a fake
`claude` first on PATH that prints stream-json events and writes files as an agent would. Checks: the child
gets `--output-format stream-json --verbose --setting-sources project,local`, the `sonnet` alias by default and
the subscription login only (also when a case's `env` names another credential); HARNESS_PLAN_APPROVED reaches
it only when the case sets it. Each copy is HEAD's tracked files minus the cases, past change folders and
reference PDFs, with their runner test replaced by a stub that prints SKIP and exits 0, initialized by the init script (a failing init is an ERROR; no script means an
already initialized project), in a new repository with every hook kept and no trace of the real checkout.
Judging comes from the trace and the copy's git status: a Skill call by the template or the initialized
prefix, a Bash write outside docs/changes/, a test command, plan.md written before code, user paths in
written files, unknown checks. Critical cases WARN at 2/3, others FAIL. `--mutate` prints baseline and mutated
side by side: KILLED, SURVIVED (kept, its instruction marked a removal candidate in the results), ERROR for a
run without an answer or a bad declaration. Each case appends one JSON line to the results file. `--jobs N`
runs copies side by side in case order. The real checkout and the temp directory are left as found.
The model child receives EOF even when the scripted caller supplies nonempty standard input.
Normal and nonzero model completion stops owned children while an independent process survives.
"""

from __future__ import annotations

import importlib.util
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RUNNER = REPO / "scripts/harness/run-evals.py"

# Logs its argv, environment and what the copy looks like (one line per call), then prints stream-json events
# for the prompt and writes what the events say it wrote. The user path is split so no scanner reads it.
FAKE_CLAUDE = """#!/usr/bin/env python3
import json, os, signal, subprocess, sys, time
from pathlib import Path
state = Path(os.environ["FAKE_CLAUDE_STATE"])
prompt = sys.argv[sys.argv.index("-p") + 1]
settings_file = Path(".claude/settings.json")
settings = json.loads(settings_file.read_text(encoding="utf-8")) if settings_file.is_file() else {}
root = os.environ["FAKE_ROOT"].encode()
dot_git = Path(".git")  # a worktree's .git is a file naming the real checkout
git_files = [dot_git] if dot_git.is_file() else [p for p in dot_git.rglob("*") if p.is_file()]
runner_test = Path("scripts/test/run-evals.test.py")  # test:harness names it: must run, skip, leak nothing
stub = subprocess.run([sys.executable, str(runner_test)], capture_output=True, text=True) if runner_test.is_file() else None
stdin = sys.stdin.read() if os.environ.get("FAKE_READ_STDIN") else None
if os.environ.get("FAKE_CHILD_MARKER"):
    marker = Path(os.environ["FAKE_CHILD_MARKER"])
    child_code = '''import json, os, signal, sys, time
from pathlib import Path
marker = Path(sys.argv[1])
signal.signal(signal.SIGTERM, signal.SIG_IGN)
pending = marker.with_suffix('.pending')
pending.write_text(json.dumps({'pid': os.getpid(), 'pgid': os.getpgrp()}))
pending.replace(marker.with_suffix('.ready'))
deadline = time.monotonic() + 20
while not marker.with_suffix('.release').exists() and time.monotonic() < deadline:
    time.sleep(0.01)
if marker.with_suffix('.release').exists():
    marker.write_text('child write after evaluation returned')
'''
    child_streams = {} if os.environ.get("FAKE_CHILD_KEEP_PIPES") else {
        "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    subprocess.Popen([sys.executable, "-c", child_code, str(marker)], stdin=subprocess.DEVNULL, **child_streams)
    deadline = time.monotonic() + 3
    while not marker.with_suffix('.ready').exists():
        if time.monotonic() > deadline:
            sys.exit('finite child did not start')
        time.sleep(0.01)
with (state / "calls.jsonl").open("a", encoding="utf-8") as log:
    log.write(json.dumps({
        "argv": sys.argv[1:], "prompt": prompt, "cwd": os.getcwd(),
        "stdin": stdin,
        "env": sorted(k for k in os.environ if k.startswith(("ANTHROPIC_", "CLAUDE_CODE_"))),
        "approved": os.environ.get("HARNESS_PLAN_APPROVED"),
        "hooks": sorted(h["command"] for gs in settings.get("hooks", {}).values() for g in gs for h in g["hooks"]),
        "permissions": settings.get("permissions"),
        "present": {p: Path(p).exists() for p in (".claude/evals", "docs/changes/261015_00-old", "docs/references",
                    "docs/changes/README.md")},
        "runner_test": stub and [stub.returncode, stub.stdout, runner_test.read_text(encoding="utf-8")],
        "remotes": subprocess.run(["git", "remote", "-v"], capture_output=True, text=True).stdout,
        "root_trace": any(root in p.read_bytes() for p in git_files),
        "clean": subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout == "",
    }) + "\\n")

def emit(event):
    print(json.dumps(event), flush=True)

def tool(name, **args):
    emit({"type": "assistant", "message": {"content": [{"type": "text", "text": "working"},
                                                        {"type": "tool_use", "id": "t", "name": name, "input": args}]}})

def write(path, text="x\\n", name="Write"):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(text, encoding="utf-8")
    tool(name, file_path=os.path.join(os.getcwd(), path))  # absolute, as the CLI sends it

emit({"type": "system", "subtype": "init", "model": "fake-model-1", "claude_code_version": "0.0.1"})
print("not a json line")
calls = state / (prompt + ".calls")
count = int(calls.read_text()) + 1 if calls.exists() else 1
calls.write_text(str(count))
intent = next(p.name for p in Path(".agents/skills").glob("*-intent"))
if prompt == "auth":
    emit({"type": "result", "is_error": True, "result": "Failed to authenticate. Please log in."})
    sys.exit(1)
if prompt == "crash":
    print("Claude usage limit reached.")
    sys.exit(1)
if prompt == "route" or (prompt.startswith("flaky") and count % 3 != 2):
    tool("Skill", skill=intent)
elif prompt.startswith("flaky"):
    tool("Skill", skill="grilling")
elif prompt == "measured":
    tool("Skill", skill=intent if "Always route." in Path("AGENTS.md").read_text(encoding="utf-8") else "grilling")
elif prompt == "bash-write":
    tool("Bash", command="mkdir -p apps && echo x > apps/a.ts")
    Path("apps").mkdir()
    Path("apps/a.ts").write_text("x\\n", encoding="utf-8")
elif prompt == "changes-only":
    write("docs/changes/261016_00-x/intent.md")
elif prompt == "test":
    tool("Bash", command="pnpm test apps/a.test.ts")
elif prompt == "plan-then-code":
    write("docs/changes/261016_00-x/plan.md")
    write("apps/a.ts", name="Edit")
elif prompt == "code-then-plan":
    write("apps/a.ts", name="Edit")
    write("docs/changes/261016_00-x/plan.md")
elif prompt == "abs":
    write("newdir/a.md", "see /" + "Users/x/notes\\n")
elif prompt == "clean":
    write("newdir/a.md", "see <repo-root>/notes\\n")
elif prompt.startswith("meet-"):
    (state / prompt).touch()
    partner = state / ("meet-b" if prompt == "meet-a" else "meet-a")
    deadline = time.monotonic() + 3
    while not partner.exists() and time.monotonic() < deadline:
        time.sleep(0.05)
    if partner.exists():
        tool("Skill", skill=intent)
emit({"type": "result", "subtype": "success", "is_error": False, "result": "done with " + prompt})
if os.environ.get("FAKE_STDERR"):
    print(os.environ["FAKE_STDERR"], file=sys.stderr)
sys.exit(int(os.environ.get("FAKE_EXIT_CODE", "0")))
"""

# Fails on FAKE_INIT_FAIL; otherwise renames the prefixed skill and fills one placeholder, as the real one does.
# Placeholders in this file are written split ('__X''__', "__X" "__") so a project's init never substitutes them.
FAKE_INIT = """#!/usr/bin/env sh
set -eu
if [ -n "${FAKE_INIT_FAIL:-}" ]; then echo "init exploded" >&2; exit 3; fi
prefix=""
while [ $# -gt 0 ]; do case "$1" in --prefix) prefix="$2"; shift 2 ;; *) shift ;; esac; done
cd "$(dirname "$0")/../.."
mv .agents/skills/__PRE''FIX__-intent ".agents/skills/$prefix-intent"
sed 's|__PACKAGE_''MANAGER__|pnpm|g' .claude/settings.json > .claude/settings.tmp
mv .claude/settings.tmp .claude/settings.json
"""

SETTINGS = {
    "permissions": {"allow": ["Bash(__PACKAGE_" "MANAGER__ test *)"], "deny": ["Bash(git push)"]},
    "hooks": {"PreToolUse": [{"matcher": "Edit|Write", "hooks": [{"type": "command", "command": "python3 gate.py"}]}],
              "PostToolUse": [{"matcher": "ExitPlanMode", "hooks": [{"type": "command", "command": "python3 mark.py"}]}]},
}
SKILL = {"skill": "__PRE" "FIX__-intent"}
CASES = [
    {"id": "route", "prompt": "route", "critical": True, "expect": SKILL},
    {"id": "flaky-critical", "prompt": "flaky-a", "critical": True, "expect": SKILL},
    {"id": "flaky-plain", "prompt": "flaky-b", "expect": SKILL},
    {"id": "bash-write", "prompt": "bash-write", "expect": {"no_edits_outside": "docs/changes/"}},
    {"id": "changes-only", "prompt": "changes-only", "expect": {"no_edits_outside": "docs/changes/"}},
    {"id": "test", "prompt": "test", "env": {"HARNESS_PLAN_APPROVED": "1", "ANTHROPIC_API_KEY": "x"},
     "expect": {"runs_command": "\\bpnpm\\s+(run\\s+)?test\\b"}},
    {"id": "plan-then-code", "prompt": "plan-then-code", "expect": {"plan_before_code": "docs/changes/*/plan.md"}},
    {"id": "code-then-plan", "prompt": "code-then-plan", "expect": {"plan_before_code": "docs/changes/*/plan.md"}},
    {"id": "abs", "prompt": "abs", "expect": {"written_not_matching": "/Users/[^/]+/"}},
    {"id": "clean", "prompt": "clean", "expect": {"written_not_matching": "/Users/[^/]+/"}},
    {"id": "silent", "prompt": "silent", "expect": {"written_not_matching": "/Users/[^/]+/"}},
    {"id": "typo", "prompt": "route", "expect": {"skil": "x"}},
    {"id": "auth", "prompt": "auth", "expect": SKILL},
    {"id": "measured", "prompt": "measured", "expect": SKILL, "measures": [{"file": "AGENTS.md", "text": "Always route.\n"}]},
    {"id": "survivor", "prompt": "route", "expect": SKILL, "measures": [{"file": "AGENTS.md", "text": "Keep it short.\n"}]},
    {"id": "stale", "prompt": "route", "expect": SKILL,
     "measures": [{"file": "AGENTS.md", "text": "A sentence nobody wrote.\n"}]},
    {"id": "crash", "prompt": "crash", "expect": SKILL, "measures": [{"file": "AGENTS.md", "text": "Keep it short.\n"}]},
    {"id": "meet-a", "prompt": "meet-a", "expect": SKILL},
    {"id": "meet-b", "prompt": "meet-b", "expect": SKILL},
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
        files = {
            "scripts/harness/run-evals.py": RUNNER.read_text(encoding="utf-8"),
            "scripts/harness/init-template.sh": FAKE_INIT,
            "scripts/test/run-evals.test.py": "FIXTURE_ANSWERS = 'replaced by a stub in copies'\n",
            ".claude/settings.json": json.dumps(SETTINGS, indent=2) + "\n",
            ".claude/evals/cases.jsonl": "".join(json.dumps(c) + "\n" for c in CASES),
            ".agents/skills/__PRE" "FIX__-intent/SKILL.md": "---\nname: __PRE" "FIX__-intent\n---\n",
            "AGENTS.md": "# Rules\n\nAlways route.\nKeep it short.\n",
            "docs/changes/README.md": "kept\n",
            "docs/changes/261015_00-old/plan.md": "excluded\n",
            "docs/references/a.pdf": "excluded\n",
        }
        for name, text in files.items():
            (repo / name).parent.mkdir(parents=True, exist_ok=True)
            (repo / name).write_text(text, encoding="utf-8")
        for path in (bin_dir, state, copies_tmp):
            path.mkdir()
        (bin_dir / "claude").write_text(FAKE_CLAUDE, encoding="utf-8")
        (bin_dir / "claude").chmod(0o755)

        def git(*args: str) -> subprocess.CompletedProcess[str]:
            return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
                                  cwd=repo, capture_output=True, text=True, errors="replace")

        assert git("init", "-q", "-b", "main").returncode == 0
        git("add", "-A")
        assert git("commit", "-q", "-m", "chore: [eval] fixture").returncode == 0
        assert git("remote", "add", "origin", "https://example.invalid/harness.git").returncode == 0  # not in copies
        with (repo / ".git/info/exclude").open("a", encoding="utf-8") as exclude:
            exclude.write(".claude/evals/results.jsonl\n")  # the default results file, appended by the runner
        probes = (("status", "--porcelain"), ("worktree", "list"), ("branch",), ("remote", "-v"),
                  ("config", "--local", "--list"), ("rev-parse", "HEAD"))
        before = [git(*args).stdout for args in probes]
        sha = git("rev-parse", "HEAD").stdout.strip()
        env = {**os.environ, **{name: "x" for name in OFF_LOGIN + KEPT}, "TMPDIR": str(copies_tmp),
               "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}", "FAKE_CLAUDE_STATE": str(state),
               "FAKE_ROOT": str(repo.resolve()), "HARNESS_PLAN_APPROVED": "1"}
        results = state / "results.jsonl"

        def run(*args: str, caller_stdin: str | None = None, test_timeout: float | None = None,
                **extra: str) -> subprocess.CompletedProcess[str]:
            return subprocess.run([sys.executable, "scripts/harness/run-evals.py", *args], cwd=repo,
                                  env={**env, **extra}, input=caller_stdin,
                                  capture_output=True, text=True, errors="replace", timeout=test_timeout)

        def line(result: subprocess.CompletedProcess[str], case: str) -> str:
            return next((l for l in result.stdout.splitlines() if l.startswith(case + " ")), "")

        def calls() -> list[dict]:
            return [json.loads(l) for l in (state / "calls.jsonl").read_text(encoding="utf-8").splitlines()]

        def last_result(path: Path = results) -> dict:
            return json.loads(path.read_text(encoding="utf-8").splitlines()[-1])

        # Defaults, the child's command line and environment, the copy, the default results file.
        result = run("--only", "route")
        assert result.returncode == 0 and "PASS 1/1" in line(result, "route"), f"{result.stdout}{result.stderr}"
        call = calls()[-1]
        argv = call["argv"]
        assert argv[argv.index("--model") + 1] == "sonnet", f"default model must be the sonnet alias: {argv}"
        for flag, value in (("--output-format", "stream-json"), ("--setting-sources", "project,local")):
            assert argv[argv.index(flag) + 1] == value, argv
        assert "--verbose" in argv, argv
        assert not set(call["env"]) & set(OFF_LOGIN) and set(KEPT) <= set(call["env"]), \
            f"the child must get the subscription login only: {call['env']}"
        assert call["approved"] is None, "HARNESS_PLAN_APPROVED reaches the child only when the case sets it"
        assert call["hooks"] == ["python3 gate.py", "python3 mark.py"], f"every hook stays: {call}"
        assert call["permissions"]["allow"] == ["Bash(pnpm test *)"], f"the copy must be initialized: {call}"
        assert call["present"] == {".claude/evals": False, "docs/changes/261015_00-old": False, "docs/references": False,
                                   "docs/changes/README.md": True}, f"excluded paths: {call['present']}"
        code, out, text = call["runner_test"] or (None, "", "")
        assert code == 0 and out.startswith("SKIP") and "FIXTURE_ANSWERS" not in text, \
            f"the runner test is a stub in the copy that skips (test:harness names it): {call['runner_test']}"
        assert call["remotes"] == "" and not call["root_trace"] and call["clean"], \
            f"the copy is a new repository that does not lead back to the checkout: {call}"
        assert not Path(call["cwd"]).resolve().is_relative_to(repo.resolve()), call
        record = last_result(repo / ".claude/evals/results.jsonl")
        assert record["sha"] == sha and record["case"] == "route" and record["baseline"] == "PASS 1/1" \
            and record["model"] == "sonnet" and record["model_ids"] == ["fake-model-1"] and record["cli"] == "0.0.1" \
            and record["setting_sources"] == "project,local" and record["user_memory_isolated"] == "unverified" \
            and "mutated" not in record, f"one result line per case: {record}"

        # A scripted caller's stdin (for example a heredoc) must never reach the model process.
        result = run("--only", "route", "--results", str(state / "stdin-results.jsonl"),
                     caller_stdin="SCRIPTED_CALLER_STDIN_NOT_A_PROMPT\n", FAKE_READ_STDIN="1")
        assert result.returncode == 0 and "PASS 1/1" in line(result, "route"), f"{result.stdout}{result.stderr}"
        assert calls()[-1]["stdin"] == "", f"the model child must receive EOF, not caller stdin: {calls()[-1]['stdin']!r}"

        # The CLI can close its pipes and exit while one of its children is still working.
        # It must not write after the evaluation returns, for either success or nonzero exit.
        independent = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(20)"],
                                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL, start_new_session=True)
        cleanup_observations = []
        try:
            for exit_code, keep_pipes in ((0, ""), (7, ""), (0, "1"), (7, "1")):
                marker = state / f"child-{exit_code}-{bool(keep_pipes)}.late"
                try:
                    try:
                        result = run("--only", "route", "--results", str(state / f"{marker.stem}-results.jsonl"),
                                     test_timeout=5, FAKE_CHILD_MARKER=str(marker), FAKE_EXIT_CODE=str(exit_code),
                                     FAKE_CHILD_KEEP_PIPES=keep_pipes)
                    except subprocess.TimeoutExpired:
                        cleanup_observations.append({"cli_exit": exit_code, "keep_pipes": bool(keep_pipes),
                                                     "timed_out": True, "independent_alive": independent.poll() is None})
                        continue
                    expected = "PASS 1/1" if exit_code == 0 else "FAIL 0/1"
                    assert result.returncode == (0 if exit_code == 0 else 1) and expected in line(result, "route"), \
                        f"original exit and trace grading must stay: {result.stdout}{result.stderr}"
                    if exit_code:
                        assert "claude exited 7" in result.stdout, result.stdout
                    marker.with_suffix('.release').touch()  # Only permit the child write after return.
                    time.sleep(0.3)
                    cleanup_observations.append({"cli_exit": exit_code, "late_write": marker.exists(),
                                                 "keep_pipes": bool(keep_pipes), "timed_out": False,
                                                 "independent_alive": independent.poll() is None})
                finally:
                    ready = marker.with_suffix('.ready')
                    if ready.exists():
                        child = json.loads(ready.read_text())
                        try:
                            if os.getpgid(child['pid']) == child['pgid']:
                                os.kill(child['pid'], signal.SIGKILL)
                        except ProcessLookupError:
                            pass
        finally:
            independent.kill()
            independent.wait(timeout=3)
        assert all(not row['timed_out'] and not row['late_write'] and row['independent_alive']
                   for row in cleanup_observations), \
            f"only owned children must stop before evaluation completion: {cleanup_observations}"
        result = run("--only", "route", "--results", str(state / "stderr-results.jsonl"),
                     FAKE_STDERR="Failed to authenticate. stderr 경계")
        assert result.returncode == 2 and "/login" in result.stdout and "stderr 경계" in result.stdout, \
            f"stderr text must still reach authentication handling: {result.stdout}{result.stderr}"
        for flag in ("--login", "--api"):
            result = run("--only", "route", flag)
            assert result.returncode == 2 and "unrecognized arguments" in result.stderr, \
                f"{flag} must not exist: {result.returncode} {result.stderr}"
        result = run("--only", "auth", "--results", str(results))
        assert result.returncode == 2 and "/login" in result.stdout and "--login" not in result.stdout + result.stderr, \
            f"an authentication failure must abort with the login hint only: {result.stdout}{result.stderr}"

        # Judging from the trace and the copy's git status.
        result = run("--only", "bash-write,changes-only,test,plan-then-code,code-then-plan,abs,clean,silent,typo",
                     "--results", str(results))
        expected = {"bash-write": "FAIL", "changes-only": "PASS", "test": "PASS", "plan-then-code": "PASS",
                    "code-then-plan": "FAIL", "abs": "FAIL", "clean": "PASS", "silent": "FAIL", "typo": "FAIL"}
        for case, verdict in expected.items():
            assert line(result, case).split()[1:] == [verdict, "1/1" if verdict == "PASS" else "0/1"], \
                f"{case} must {verdict}: {result.stdout}{result.stderr}"
        assert result.returncode == 1, result.stdout
        for why in ("changed outside docs/changes/: ['apps/a.ts']", "apps/a.ts edited before docs/changes/261016_00-x/plan.md",
                    "newdir/a.md contains forbidden", "nothing written", "unknown check 'skil'", "trace: Edit(apps/a.ts) Write(docs/changes/"):
            assert why in result.stdout, f"{why!r} missing: {result.stdout}"
        test_call = next(c for c in calls() if c["prompt"] == "test")
        assert test_call["approved"] == "1" and "ANTHROPIC_API_KEY" not in test_call["env"], \
            f"a case's env reaches the child, except another login: {test_call}"
        assert [json.loads(l)["case"] for l in results.read_text(encoding="utf-8").splitlines()] == list(expected), \
            "one result line per case, in case order"

        # --runs: a critical case at 2/3 warns and passes the run, any other case fails.
        result = run("--only", "flaky-critical", "--runs", "3", "--results", str(results))
        assert result.returncode == 0 and "WARN 2/3" in line(result, "flaky-critical"), result.stdout
        result = run("--only", "flaky-plain", "--runs", "3", "--results", str(results))
        assert result.returncode == 1 and "FAIL 2/3" in line(result, "flaky-plain"), result.stdout
        assert (state / "flaky-b.calls").read_text() == "3", "every run must happen even after a failure"

        # A failing init is an ERROR and never reaches the model; no init script means an initialized project.
        before_calls = len(calls())
        result = run("--only", "route", "--results", str(results), FAKE_INIT_FAIL="1")
        assert result.returncode == 1 and line(result, "route").split()[1] == "ERROR" and "init exploded" in result.stdout, \
            f"{result.stdout}{result.stderr}"
        assert len(calls()) == before_calls and last_result()["baseline"] == "ERROR", "init failure spends no quota"

        # --mutate: baseline and mutated side by side.
        result = run("--only", "measured", "--mutate", "--runs", "2", "--results", str(results))
        assert result.returncode == 0 and line(result, "measured").split()[1:] == ["PASS", "2/2", "KILLED", "2/2"], \
            result.stdout
        assert "killed - no Skill call" in result.stdout and last_result()["mutated"] == "KILLED 2/2", result.stdout
        result = run("--only", "survivor", "--mutate", "--results", str(results))
        assert result.returncode == 0 and line(result, "survivor").split()[1:] == ["PASS", "1/1", "SURVIVED", "0/1"], \
            result.stdout
        assert "removal candidate" in result.stdout and "Keep it short." in result.stdout, result.stdout
        assert last_result()["removal_candidate"] == CASES[14]["measures"], "a survivor's instruction is marked"
        result = run("--only", "crash", "--mutate", "--results", str(results))  # no answer proves nothing
        assert result.returncode == 1 and "ERROR" in line(result, "crash") and "claude exited 1" in result.stdout, \
            result.stdout
        result = run("--only", "stale,route", "--mutate", "--results", str(results))
        assert result.returncode == 1 and line(result, "stale").split()[1:3] == ["PASS", "1/1"] \
            and line(result, "stale").split()[3] == "ERROR" and "found 0 times" in result.stdout, result.stdout
        assert line(result, "route").split()[1:] == ["PASS", "1/1", "-"], f"no measures, no mutation: {result.stdout}"
        problems = runner.measure_problems(repo, {"measures": [{"file": ".claude/settings.json", "text": '"hooks": {'}]})
        assert problems and "JSON" in problems[0], f"a removal must leave a JSON file readable: {problems}"
        assert runner.measure_problems(repo, CASES[13]) == [], "a sentence that occurs once can be removed"
        for outside in (str(repo / "AGENTS.md"), "../repo/AGENTS.md"):  # never a file outside the copy
            problems = runner.measure_problems(repo, {"measures": [{"file": outside, "text": "Keep it short.\n"}]})
            assert problems and "relative path" in problems[0], (outside, problems)

        # A GIT_DIR or GIT_WORK_TREE in the caller's environment reaches neither the copy's git nor the agent.
        result = run("--only", "route", "--results", str(results), GIT_DIR=str(repo / ".git"), GIT_WORK_TREE=str(repo))
        assert result.returncode == 0 and calls()[-1]["clean"], f"{result.stdout}{result.stderr}"

        # --jobs: two cases that only pass together pass side by side, printed in case order.
        result = run("--only", "meet-a,meet-b", "--jobs", "2", "--results", str(results))
        assert result.returncode == 0, f"--jobs must run copies at the same time: {result.stdout}{result.stderr}"
        assert result.stdout.index("meet-a ") < result.stdout.index("meet-b "), result.stdout

        after = [git(*args).stdout for args in probes]
        assert after == before, f"the real checkout must stay as it was: {before} -> {after}"
        assert not list(copies_tmp.iterdir()), f"copies must be removed: {list(copies_tmp.iterdir())}"
        # An initialized project has no init script and no Claude settings: the template prefix still routes.
        git("rm", "-q", "scripts/harness/init-template.sh", ".claude/settings.json")
        assert git("commit", "-q", "-m", "chore: [eval] initialized").returncode == 0
        result = run("--only", "route", "--results", str(results))
        assert result.returncode == 0 and calls()[-1]["hooks"] == [], f"{result.stdout}{result.stderr}"
        assert not list(copies_tmp.iterdir()), f"copies must be removed: {list(copies_tmp.iterdir())}"

    # This repository's cases use only checks the runner knows; each declared measure is removable exactly once.
    real = [json.loads(l) for l in (REPO / ".claude/evals/cases.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len({case["id"] for case in real}) == len(real), "case ids are unique"
    unknown = {case["id"]: sorted(set(case["expect"]) - set(runner.CHECKS)) for case in real
               if not case.get("expect") or set(case["expect"]) - set(runner.CHECKS)}
    assert not unknown, f"every case has known checks only: {unknown}"
    stale = {case["id"]: problems for case in real if case.get("measures")
             and (problems := runner.measure_problems(REPO, case))}
    assert not stale, f"every declared measure occurs exactly once: {stale}"

    print("PASS: run-evals runner (stream-json trace judging, git-status judging, excluded and initialized copies, "
          "case env and plan-approval drop, subscription login only, critical WARN, --mutate side by side with "
          "removal candidates, results JSONL, --jobs, caller stdin isolation, owned child cleanup)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
