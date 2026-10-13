#!/usr/bin/env python3
"""Run harness evals: each case in .claude/evals/cases.jsonl through `claude -p`
inside a throwaway git worktree, then evaluate `expect` checks.

Checks supported in `expect`:
  output_matches:               regex must match the agent's final output
  output_not_matches:           regex must NOT match the output
  files_unchanged_glob:         no file matching the glob may differ from HEAD
  files_changed_not_matching:   no changed file may contain the regex
  command_succeeds:             shell command (run in the worktree) must exit 0

Usage: python3 scripts/harness/run-evals.py [--only id,id] [--model sonnet] [--max-turns 20] [--runs 1]
Requires the `claude` CLI logged in with a subscription; not run in the default test:harness lane.
`--model` takes the CLI's alias (default `sonnet`); pin an exact model ID only for comparison runs.
`--runs N` runs each case N times and prints k/N; a case passes only when all N runs pass.
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


def sh(cmd: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=check)


class AuthFailure(RuntimeError):
    pass


def run_case(case: dict, model: str, max_turns: int, env: dict[str, str]) -> tuple[bool, list[str]]:
    wt = Path(tempfile.mkdtemp(prefix="harness-eval-"))
    sh(["git", "worktree", "add", "--detach", "--quiet", str(wt), "HEAD"], ROOT)
    problems: list[str] = []
    try:
        res = subprocess.run(
            ["claude", "-p", case["prompt"], "--model", model, "--max-turns", str(max_turns),
             "--permission-mode", "auto", "--output-format", "text", "--no-session-persistence"],
            cwd=wt, capture_output=True, text=True, env=env,
        )
        output = res.stdout + res.stderr
        if "Failed to authenticate" in output:
            raise AuthFailure(output.strip().splitlines()[-1] if output.strip() else "authentication failed")
        if not wt.is_dir():
            return False, [f"worktree {wt} vanished during the run; cannot evaluate file checks"]
        changed = sh(["git", "status", "--porcelain", "--untracked-files=all"], wt).stdout.splitlines()
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
                p = wt / f
                if p.is_file() and re.search(rx, p.read_text(errors="replace")):
                    problems.append(f"{f} contains forbidden /{rx}/")
        if (cmd := exp.get("command_succeeds")):
            if subprocess.run(cmd, shell=True, cwd=wt).returncode != 0:
                problems.append(f"command failed: {cmd}")
        if problems:
            # A failing case is undiagnosable without the agent's actual words.
            tail = [l for l in output.strip().splitlines() if l.strip()][-12:]
            problems.append("agent output (tail):\n" + "\n".join(f"      | {l}" for l in tail))
    finally:
        sh(["git", "worktree", "remove", "--force", str(wt)], ROOT, check=False)
        shutil.rmtree(wt, ignore_errors=True)
    return (not problems), problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None)
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--max-turns", type=int, default=20)
    ap.add_argument("--runs", type=int, default=1, help="run each case N times; PASS needs N/N")
    args = ap.parse_args()
    if args.runs < 1:
        ap.error("--runs must be at least 1")
    env = {key: value for key, value in os.environ.items() if key not in OFF_LOGIN_ENV}
    only = set(args.only.split(",")) if args.only else None
    cases = [json.loads(l) for l in CASES.read_text(encoding="utf-8").splitlines() if l.strip()]
    failures = 0
    print(f"{'case':<28} result", flush=True)
    for case in cases:
        if only and case["id"] not in only:
            continue
        passed, problems = 0, []
        for run in range(1, args.runs + 1):
            try:
                run_ok, run_problems = run_case(case, args.model, args.max_turns, env)
            except AuthFailure as exc:
                print(f"ABORT: claude could not authenticate — {exc} Check that the `claude` CLI is logged in "
                      "(run `claude`, then /login).", flush=True)
                return 2
            passed += run_ok
            problems.extend(f"run {run}: {p}" for p in run_problems)
        ok = passed == args.runs
        print(f"{case['id']:<28} {'PASS' if ok else 'FAIL'} {passed}/{args.runs}", flush=True)
        for p in problems:
            print(f"    - {p}", flush=True)
        failures += 0 if ok else 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
