#!/usr/bin/env python3
"""Run harness evals: each case in .claude/evals/cases.jsonl through `claude -p`
inside a throwaway copy of HEAD, then evaluate `expect` checks.

Checks supported in `expect`:
  output_matches:               regex must match the agent's final output
  output_not_matches:           regex must NOT match the output
  files_unchanged_glob:         no file matching the glob may differ from HEAD
  files_changed_not_matching:   no changed file may contain the regex
  command_succeeds:             shell command (run in the copy) must exit 0

Usage: python3 scripts/harness/run-evals.py [--only id,id] [--model sonnet] [--max-turns 20] [--runs 1]
                                            [--jobs 1] [--mutate]
Requires the `claude` CLI logged in with a subscription; not run in the default test:harness lane.
`--model` takes the CLI's alias (default `sonnet`); pin an exact model ID only for comparison runs.
`--runs N` runs each case N times and prints k/N; a case passes only when all N runs pass.
`--jobs N` runs up to N copies at once; output stays in case order.
`--mutate` removes each case's `measures` (the instruction it measures) from the copy and expects the case
to fail: KILLED when every run fails, SURVIVED (with the agent's words) when any run still passes.
Each copy is HEAD's tracked files in a new git repository: no remote and no path back to this checkout. The
agreement gate's hooks are left out of the copy's .claude/settings.json so a case measures the instructions,
not the gate (its unit tests guard it); every other hook stays. This checkout is never changed.
The child `claude -p` runs on that login only: variables that would route it elsewhere are left out of
its environment, also inside a Claude Code session. An authentication failure aborts the run instead of
failing every case.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CASES = ROOT / ".claude" / "evals" / "cases.jsonl"
# What would take `claude -p` off the CLI's subscription login, as claude 2.1.296 reads it: key credentials,
# workload identity, an explicit profile (it outranks a stored login), provider switches, an endpoint override,
# a request socket (without the OAuth token it carries no login) and custom headers (an Authorization header there
# replaces the login). The OAuth token variables are the subscription itself and stay.
OFF_LOGIN_ENV = (
    "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "CLAUDE_CODE_API_KEY_FILE_DESCRIPTOR", "ANTHROPIC_FEDERATION_RULE_ID",
    "ANTHROPIC_PROFILE", "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY",
    "CLAUDE_CODE_USE_ANTHROPIC_AWS", "CLAUDE_CODE_USE_ANTHROPIC_GOOGLE_CLOUD", "CLAUDE_CODE_USE_MANTLE",
    "CLAUDE_CODE_USE_GATEWAY", "ANTHROPIC_BASE_URL", "ANTHROPIC_UNIX_SOCKET", "ANTHROPIC_CUSTOM_HEADERS",
)
# The copy's own commit: no hooks, no signing prompt, no identity taken from the user.
COPY_GIT = ["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false",
            "-c", "user.name=eval", "-c", "user.email=eval@invalid"]


def sh(cmd: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=check)


class AuthFailure(RuntimeError):
    pass


class BadMeasures(ValueError):
    pass


def is_json(text: str) -> bool:
    try:
        json.loads(text)
        return True
    except ValueError:
        return False


def mutation(root: Path, case: dict) -> tuple[dict[str, str], list[str]]:
    """The case's files with its `measures` removed, and why that removal is not clean: a missing declaration, a
    text that does not occur exactly once, or a JSON file that stops being JSON (a broken setting would fail the
    case for another reason)."""
    if not case.get("measures"):
        return {}, ["no measures: declare the instruction this case measures (.claude/evals/README.md)"]
    texts: dict[str, str] = {}
    problems: list[str] = []
    for measure in case["measures"]:
        name, text = measure["file"], measure["text"]
        path = root / name
        if name not in texts:
            if not path.is_file():
                problems.append(f"{name}: no such file")
                continue
            texts[name] = path.read_text(encoding="utf-8")
        count = texts[name].count(text)
        if count != 1:
            problems.append(f"{name}: measured text found {count} times, needs exactly 1: {text[:60]!r}")
            continue
        texts[name] = texts[name].replace(text, "", 1)
    for name, text in texts.items():
        if is_json((root / name).read_text(encoding="utf-8")) and not is_json(text):
            problems.append(f"{name}: removing the measured text leaves invalid JSON")
    return texts, problems


def measure_problems(root: Path, case: dict) -> list[str]:
    return mutation(root, case)[1]


def gate_off(copy: Path) -> None:
    """Leave the agreement gate's hooks out of the copy's Claude settings; other hooks and permissions stay."""
    path = copy / ".claude" / "settings.json"
    if not path.is_file():
        return
    settings = json.loads(path.read_text(encoding="utf-8"))
    hooks = settings.get("hooks", {})
    for event in list(hooks):
        for group in hooks[event]:
            group["hooks"] = [h for h in group.get("hooks", []) if "agreement-gate.py" not in h.get("command", "")]
        hooks[event] = [group for group in hooks[event] if group["hooks"]]
        if not hooks[event]:
            del hooks[event]
    path.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def make_copy(sha: str, case: dict, mutate: bool) -> Path:
    """HEAD's tracked files in a new repository: nothing in it leads back to this checkout."""
    copy = Path(tempfile.mkdtemp(prefix="harness-eval-"))
    try:
        archive = subprocess.Popen(["git", "archive", "--format=tar", sha], cwd=ROOT, stdout=subprocess.PIPE)
        subprocess.run(["tar", "-x", "-C", str(copy)], stdin=archive.stdout, check=True, capture_output=True)
        archive.stdout.close()
        if archive.wait():
            raise RuntimeError(f"git archive {sha} failed")
        if mutate:  # before gate_off, so a measure is matched against the file as committed
            texts, problems = mutation(copy, case)
            if problems:
                raise BadMeasures("\n".join(problems))
            for name, text in texts.items():
                (copy / name).write_text(text, encoding="utf-8")
        gate_off(copy)
        sh(["git", "init", "-q"], copy)
        sh(["git", "add", "--all", "--force"], copy)
        sh([*COPY_GIT, "commit", "-q", "-m", "eval copy"], copy)
    except BaseException:
        shutil.rmtree(copy, ignore_errors=True)
        raise
    return copy


def run_case(sha: str, case: dict, model: str, max_turns: int, env: dict[str, str],
             mutate: bool) -> tuple[bool, list[str], str]:
    """(passed, problems, the agent's last words) for one run in its own copy."""
    copy = make_copy(sha, case, mutate)
    problems: list[str] = []
    try:
        res = subprocess.run(
            ["claude", "-p", case["prompt"], "--model", model, "--max-turns", str(max_turns),
             "--permission-mode", "auto", "--output-format", "text", "--no-session-persistence"],
            cwd=copy, capture_output=True, text=True, env=env,
        )
        output = res.stdout + res.stderr
        if "Failed to authenticate" in output:
            raise AuthFailure(output.strip().splitlines()[-1] if output.strip() else "authentication failed")
        if not copy.is_dir():
            return False, [f"copy {copy} vanished during the run; cannot evaluate file checks"], ""
        changed = sh(["git", "status", "--porcelain", "--untracked-files=all"], copy).stdout.splitlines()
        changed_files = [line[3:] for line in changed]
        exp = case.get("expect", {})
        if res.returncode != 0:
            problems.append(f"claude exited {res.returncode}")
        if (rx := exp.get("output_matches")) and not re.search(rx, output, re.M):
            problems.append(f"output did not match /{rx}/")
        if (rx := exp.get("output_not_matches")) and re.search(rx, output, re.M):
            problems.append(f"output matched forbidden /{rx}/")
        if (g := exp.get("files_unchanged_glob")):
            hits = [f for f in changed_files if fnmatch.fnmatch(f, g)]
            if hits:
                problems.append(f"protected files changed: {hits}")
        if (rx := exp.get("files_changed_not_matching")):
            for f in changed_files:
                p = copy / f
                if p.is_file() and re.search(rx, p.read_text(errors="replace")):
                    problems.append(f"{f} contains forbidden /{rx}/")
        if (cmd := exp.get("command_succeeds")):
            if subprocess.run(cmd, shell=True, cwd=copy).returncode != 0:
                problems.append(f"command failed: {cmd}")
        # A result is undiagnosable without the agent's actual words.
        tail = [l for l in output.strip().splitlines() if l.strip()][-12:]
        words = "agent output (tail):\n" + "\n".join(f"      | {l}" for l in tail)
    finally:
        shutil.rmtree(copy, ignore_errors=True)
    return (not problems), problems, words


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None)
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--max-turns", type=int, default=20)
    ap.add_argument("--runs", type=int, default=1, help="run each case N times; PASS needs N/N")
    ap.add_argument("--jobs", type=int, default=1, help="run up to N copies at once")
    ap.add_argument("--mutate", action="store_true",
                    help="remove each case's measured instruction and expect the case to fail")
    args = ap.parse_args()
    if args.runs < 1:
        ap.error("--runs must be at least 1")
    if args.jobs < 1:
        ap.error("--jobs must be at least 1")
    env = {key: value for key, value in os.environ.items() if key not in OFF_LOGIN_ENV}
    only = set(args.only.split(",")) if args.only else None
    cases = [json.loads(l) for l in CASES.read_text(encoding="utf-8").splitlines() if l.strip()]
    cases = [case for case in cases if not only or case["id"] in only]
    sha = sh(["git", "rev-parse", "HEAD"], ROOT).stdout.strip()  # every run evaluates the same commit
    failures = 0
    print(f"{'case':<28} result", flush=True)
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        runs = [[pool.submit(run_case, sha, case, args.model, args.max_turns, env, args.mutate)
                 for _ in range(args.runs)] for case in cases]
        for case, futures in zip(cases, runs):
            results, notes = [], []
            try:
                for run, future in enumerate(futures, 1):
                    ok, problems, words = future.result()
                    results.append(ok)
                    if args.mutate and ok:
                        notes.append(f"run {run}: passed without the measured instruction\n{words}")
                    elif not args.mutate and not ok:
                        notes.extend(f"run {run}: {p}" for p in problems + [words])
            except AuthFailure as exc:
                pool.shutdown(wait=False, cancel_futures=True)
                print(f"ABORT: claude could not authenticate — {exc} Check that the `claude` CLI is logged in "
                      "(run `claude`, then /login).", flush=True)
                return 2
            except BadMeasures as exc:
                print(f"{case['id']:<28} ERROR", flush=True)
                for problem in str(exc).splitlines():
                    print(f"    - {problem}", flush=True)
                failures += 1
                continue
            passed = sum(results)
            if args.mutate:
                ok = passed == 0
                verdict = f"{'KILLED' if ok else 'SURVIVED'} {args.runs - passed}/{args.runs}"
            else:
                ok = passed == args.runs
                verdict = f"{'PASS' if ok else 'FAIL'} {passed}/{args.runs}"
            print(f"{case['id']:<28} {verdict}", flush=True)
            for note in notes:
                print(f"    - {note}", flush=True)
            failures += 0 if ok else 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
