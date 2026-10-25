#!/usr/bin/env python3
"""Run harness evals: each case in .claude/evals/cases.jsonl through `claude -p` inside a throwaway,
initialized copy of HEAD, judged from the run's tool-call trace (`--output-format stream-json --verbose`)
and the copy's git status. Answer wording is never judged.

A case: `id`, `prompt`, `expect` (checks below), optional `env` (variables for this case's child only),
optional `critical` (N/N is PASS, at least two thirds is WARN instead of FAIL), optional `measures` (the
instruction it measures: [{"file", "text"}], each text exactly once in its file as committed).
Checks in `expect`:
  skill:                a Skill tool call names this skill (the template's prefix placeholder also matches
                        the copy's prefix)
  no_edits_outside:     the copy's git status shows no changed path outside this prefix (Bash writes count)
  runs_command:         a Bash tool call's command matches this regex
  plan_before_code:     a Write/Edit of a path matching this glob comes before the first Write/Edit of a
                        repository path outside docs/changes/ (order from the trace; attempts count)
  written_not_matching: at least one file changed in the copy and none contains this regex

Usage: python3 scripts/harness/run-evals.py [--only id,id] [--model sonnet] [--max-turns 20] [--runs 1]
                                            [--jobs 1] [--mutate] [--results PATH]
Requires the `claude` CLI logged in with a subscription; spends model quota, so it is not in test:harness.
`--runs N` runs each case N times. `--jobs N` runs up to N copies at once; output stays in case order.
`--mutate` also runs each case with its `measures` removed and prints baseline and mutated side by side:
KILLED when every mutated run fails, SURVIVED otherwise. A survivor stays as a behavior regression case;
its measured instruction is marked a removal candidate in the results for a human to decide in the PR.
Each case appends one JSON line to the results file (default .claude/evals/results.jsonl).

Each copy is HEAD's tracked files minus EXCLUDE (the runner test replaced by a stub that prints SKIP, since
test:harness names it), initialized with INIT_ARGS when the init script is still
there (a failing init is an ERROR), in a new git repository: no remote and no path back to this checkout,
which is never changed. Every hook stays. The child runs with `--setting-sources project,local`; whether
that keeps the user's own memory file out is unverified and recorded so in each result line.
HARNESS_PLAN_APPROVED reaches the child only when the case's `env` sets it (headless runs have no plan mode
tools, so a post-approval case sets it). The child runs on the CLI's subscription login only: variables
that would route it elsewhere are dropped, also from a case's `env`. An authentication failure aborts.
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
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parents[2]
CASES = ROOT / ".claude" / "evals" / "cases.jsonl"
RESULTS = ROOT / ".claude" / "evals" / "results.jsonl"
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
PLAN_APPROVED_ENV = "HARNESS_PLAN_APPROVED"  # the human-set bypass of the plan-first hook
SETTING_SOURCES = "project,local"
# Not part of what the agent should see: the cases and their runner test, past change folders, reference PDFs.
RUNNER_TEST = "scripts/test/run-evals.test.py"
EXCLUDE = (".claude/evals", RUNNER_TEST, "docs/changes/2*", "docs/references")
# test:harness runs the runner test by path, so the copy gets this stub in its place: it skips and leaks nothing.
RUNNER_TEST_STUB = '#!/usr/bin/env python3\nprint("SKIP: run-evals runner test is not part of an eval copy")\n'
INIT = "scripts/harness/init-template.sh"
INIT_PREFIX = "acme"
INIT_ARGS = ("--project-name", "acme", "--prefix", INIT_PREFIX)  # required options only
CHANGES = "docs/changes/"
WRITE_TOOLS = {"Write": "file_path", "Edit": "file_path", "MultiEdit": "file_path", "NotebookEdit": "notebook_path"}
CHECKS = ("skill", "no_edits_outside", "runs_command", "plan_before_code", "written_not_matching")
# The copy's own commit: no hooks, no signing prompt, no identity taken from the user.
COPY_GIT = ["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false",
            "-c", "user.name=eval", "-c", "user.email=eval@invalid"]


class Run(NamedTuple):
    ok: bool
    problems: list[str]
    words: str
    exit_code: int
    models: set[str]
    cli: str


class AuthFailure(RuntimeError):
    pass


class BadMeasures(ValueError):
    pass


class InitFailure(RuntimeError):
    pass


def sh(cmd: list[str], cwd: Path, check: bool = True, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=check, env=env)


def copy_env() -> dict[str, str]:
    """The environment for anything run in a copy: a GIT_DIR, GIT_WORK_TREE or GIT_INDEX_FILE from the caller (a
    git hook, an exporting shell) would point git back at this checkout."""
    return {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}


def child_env(case: dict) -> dict[str, str]:
    env = {key: value for key, value in copy_env().items() if key != PLAN_APPROVED_ENV}
    env.update(case.get("env", {}))
    return {key: value for key, value in env.items() if key not in OFF_LOGIN_ENV}


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
        if Path(name).is_absolute() or ".." in Path(name).parts:
            problems.append(f"{name}: measures name a file in the repository by a relative path")
            continue
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


def init_copy(copy: Path) -> None:
    """Fill the template's placeholders as a user would. An already initialized project has no init script."""
    if not (copy / INIT).is_file():
        return
    res = sh(["sh", INIT, *INIT_ARGS], copy, check=False, env=copy_env())
    if res.returncode:
        tail = " | ".join(l for l in (res.stdout + res.stderr).strip().splitlines()[-5:])
        raise InitFailure(f"{INIT} exited {res.returncode}: {tail}")


def make_copy(sha: str, case: dict, mutate: bool) -> Path:
    """HEAD's tracked files minus EXCLUDE, initialized, in a new repository: nothing leads back to this checkout."""
    copy = Path(tempfile.mkdtemp(prefix="harness-eval-"))
    try:
        archive = subprocess.Popen(["git", "archive", "--format=tar", sha], cwd=ROOT, stdout=subprocess.PIPE)
        subprocess.run(["tar", "-x", "-C", str(copy)], stdin=archive.stdout, check=True, capture_output=True)
        archive.stdout.close()
        if archive.wait():
            raise RuntimeError(f"git archive {sha} failed")
        had_runner_test = (copy / RUNNER_TEST).is_file()
        for pattern in EXCLUDE:
            for path in copy.glob(pattern):
                shutil.rmtree(path) if path.is_dir() and not path.is_symlink() else path.unlink()
        if had_runner_test:
            (copy / RUNNER_TEST).write_text(RUNNER_TEST_STUB, encoding="utf-8")
        if mutate:  # before init, so a measure is matched against the file as committed
            texts, problems = mutation(copy, case)
            if problems:
                raise BadMeasures("\n".join(problems))
            for name, text in texts.items():
                (copy / name).write_text(text, encoding="utf-8")
        init_copy(copy)
        sh(["git", "init", "-q"], copy, env=copy_env())
        sh(["git", "add", "--all", "--force"], copy, env=copy_env())
        sh([*COPY_GIT, "commit", "-q", "-m", "eval copy"], copy, env=copy_env())
    except BaseException:
        shutil.rmtree(copy, ignore_errors=True)
        raise
    return copy


def parse_trace(stdout: str) -> tuple[list[tuple[str, dict]], str, set[str], str]:
    """(tool calls in order as (name, input), final result text, models, CLI version) from stream-json lines.
    Subagent calls are in the stream too; lines that are not JSON events are skipped."""
    calls: list[tuple[str, dict]] = []
    final, models, cli = "", set(), ""
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        if event.get("type") == "system" and event.get("subtype") == "init":
            models.add(str(event.get("model", "")))
            cli = str(event.get("claude_code_version", cli))
        elif event.get("type") == "assistant":
            for block in (event.get("message") or {}).get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    calls.append((str(block.get("name", "")), block.get("input") or {}))
        elif event.get("type") == "result":
            final = str(event.get("result", ""))
    return calls, final, models - {""}, cli


def written(calls: list[tuple[str, dict]], copy: Path) -> list[str]:
    """Paths the agent wrote with file tools, in order: relative inside the copy, absolute outside it."""
    root, paths = os.path.realpath(copy), []
    for name, args in calls:
        target = args.get(WRITE_TOOLS.get(name, ""))
        if isinstance(target, str) and target:
            path = os.path.realpath(os.path.join(copy, target))
            rel = os.path.relpath(path, root)
            paths.append(path if rel == ".." or rel.startswith(".." + os.sep) else rel)
    return paths


def changed_paths(copy: Path) -> list[str]:
    """Every path the run added, changed or removed in the copy (any tool, Bash included)."""
    sh(["git", "add", "--all"], copy, env=copy_env())
    out = sh(["git", "diff", "--cached", "--name-only", "--no-renames", "-z"], copy, env=copy_env()).stdout
    return [path for path in out.split("\0") if path]


def judge(expect: dict, calls: list[tuple[str, dict]], changed: list[str], copy: Path) -> list[str]:
    problems = [f"unknown check {key!r} (known: {', '.join(CHECKS)})" for key in expect if key not in CHECKS]
    if (skill := expect.get("skill")):
        used = [str(args.get("skill") or args.get("command") or "").lstrip("/") for name, args in calls if name == "Skill"]
        if not {skill, skill.replace("__PRE" "FIX__", INIT_PREFIX)} & set(used):  # split: init must not fill it
            problems.append(f"no Skill call to {skill} (skills called: {used or 'none'})")
    if (prefix := expect.get("no_edits_outside")):
        if (outside := [path for path in changed if not path.startswith(prefix)]):
            problems.append(f"changed outside {prefix}: {outside}")
    if (rx := expect.get("runs_command")):
        commands = [str(args.get("command", "")) for name, args in calls if name == "Bash"]
        if not any(re.search(rx, command) for command in commands):
            problems.append(f"no Bash command matched /{rx}/ (ran: {commands[:6]})")
    if (glob := expect.get("plan_before_code")):
        writes = written(calls, copy)
        plan = next((i for i, path in enumerate(writes) if fnmatch.fnmatch(path, glob)), None)
        code = next((i for i, path in enumerate(writes) if not os.path.isabs(path) and not path.startswith(CHANGES)), None)
        if plan is None:
            problems.append(f"no write to {glob} (writes: {writes})")
        elif code is not None and code < plan:
            problems.append(f"{writes[code]} edited before {writes[plan]}")
    if (rx := expect.get("written_not_matching")):
        files = [path for path in changed if (copy / path).is_file()]
        if not files:
            problems.append("nothing written: the check needs at least one changed file")
        problems += [f"{path} contains forbidden /{rx}/" for path in files
                     if re.search(rx, (copy / path).read_text(encoding="utf-8", errors="replace"))]
    return problems


def describe(calls: list[tuple[str, dict]], final: str, output: str, copy: Path) -> str:
    """The trace and the agent's last words: a result is undiagnosable without them."""
    roots = (os.path.realpath(copy) + os.sep, str(copy) + os.sep)

    def brief(args: dict) -> str:
        value = str(next((args[k] for k in ("skill", "command", "file_path", "notebook_path", "pattern") if args.get(k)), ""))
        for root in roots:
            value = value.replace(root, "")
        return value.splitlines()[0][:60] if value.strip() else ""
    trace = " ".join(f"{name}({brief(args)})" for name, args in calls)[:500] or "no tool calls"
    tail = [l for l in (final or output).strip().splitlines() if l.strip()][-8:]
    return f"trace: {trace}\n" + "\n".join(f"      | {l}" for l in tail)


def run_case(sha: str, case: dict, model: str, max_turns: int, mutate: bool) -> Run:
    copy = make_copy(sha, case, mutate)
    try:
        res = subprocess.run(
            ["claude", "-p", case["prompt"], "--model", model, "--max-turns", str(max_turns),
             "--permission-mode", "auto", "--output-format", "stream-json", "--verbose",
             "--setting-sources", SETTING_SOURCES, "--no-session-persistence"],
            cwd=copy, stdin=subprocess.DEVNULL, capture_output=True, text=True, env=child_env(case),
        )
        output = res.stdout + res.stderr
        if "Failed to authenticate" in output:
            raise AuthFailure(output.strip().splitlines()[-1][:300] if output.strip() else "authentication failed")
        calls, final, models, cli = parse_trace(res.stdout)
        problems = judge(case.get("expect", {}), calls, changed_paths(copy), copy)
        if res.returncode != 0:
            problems.insert(0, f"claude exited {res.returncode}")
        words = describe(calls, final, output, copy)
    finally:
        shutil.rmtree(copy, ignore_errors=True)
    return Run(not problems, problems, words, res.returncode, models, cli)


def collect(futures: list) -> tuple[list[Run], str]:
    """The runs, or the reason none could be judged (a bad `measures` declaration, a failing init)."""
    runs = []
    for future in futures:
        try:
            runs.append(future.result())
        except (BadMeasures, InitFailure) as exc:
            return runs, str(exc)
    return runs, ""


def baseline_verdict(runs: list[Run], n: int, critical: bool) -> tuple[str, bool]:
    passed = sum(run.ok for run in runs)
    if passed == n:
        return f"PASS {passed}/{n}", True
    if critical and 3 * passed >= 2 * n:
        return f"WARN {passed}/{n}", True  # flaky: a critical case passing at least two thirds
    return f"FAIL {passed}/{n}", False


def mutated_verdict(runs: list[Run], n: int) -> tuple[str, bool]:
    crashed = sum(run.exit_code != 0 for run in runs)
    if crashed:  # no answer (a usage limit, a crash) proves nothing either way
        return f"ERROR {crashed}/{n} runs got no answer", False
    killed = sum(not run.ok for run in runs)
    return f"{'KILLED' if killed == n else 'SURVIVED'} {killed}/{n}", True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None)
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--max-turns", type=int, default=20)
    ap.add_argument("--runs", type=int, default=1, help="run each case N times; PASS needs N/N")
    ap.add_argument("--jobs", type=int, default=1, help="run up to N copies at once")
    ap.add_argument("--mutate", action="store_true",
                    help="also run each case without its measured instruction, side by side with the baseline")
    ap.add_argument("--results", type=Path, default=RESULTS, help="JSON lines file to append one line per case to")
    args = ap.parse_args()
    if args.runs < 1:
        ap.error("--runs must be at least 1")
    if args.jobs < 1:
        ap.error("--jobs must be at least 1")
    only = set(args.only.split(",")) if args.only else None
    cases = [json.loads(l) for l in CASES.read_text(encoding="utf-8").splitlines() if l.strip()]
    cases = [case for case in cases if not only or case["id"] in only]
    sha = sh(["git", "rev-parse", "HEAD"], ROOT).stdout.strip()  # every run evaluates the same commit
    n, failures = args.runs, 0
    print(f"{'case':<32} {'baseline':<14} mutated" if args.mutate else f"{'case':<32} result", flush=True)
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        def submit(case: dict, mutate: bool) -> list:
            return [pool.submit(run_case, sha, case, args.model, args.max_turns, mutate) for _ in range(n)]
        planned = [(case, submit(case, False), submit(case, True) if args.mutate and case.get("measures") else [])
                   for case in cases]
        try:
            for case, base_futures, mut_futures in planned:
                notes: list[str] = []
                base, error = collect(base_futures)
                if error:
                    verdict, ok = "ERROR", False
                    notes += error.splitlines()
                else:
                    verdict, ok = baseline_verdict(base, n, case.get("critical", False))
                    notes += [f"run {i}: {p}" for i, run in enumerate(base, 1) if not run.ok
                              for p in run.problems + [run.words]]
                record = {"date": datetime.now(timezone.utc).isoformat(timespec="seconds"), "sha": sha,
                          "model": args.model, "case": case["id"], "critical": case.get("critical", False),
                          "baseline": verdict}
                line = f"{case['id']:<32} {verdict}"
                if args.mutate:
                    mutated, mut_ok = "-", True
                    if not case.get("measures"):
                        notes.append("mutated: no measures")
                    else:
                        mut, mut_error = collect(mut_futures)
                        if mut_error:
                            mutated, mut_ok = "ERROR", False
                            notes += [f"mutated: {p}" for p in mut_error.splitlines()]
                        else:
                            mutated, mut_ok = mutated_verdict(mut, n)
                            base += mut
                            for i, run in enumerate(mut, 1):
                                if run.exit_code != 0:
                                    notes += [f"mutated run {i}: {p}" for p in run.problems + [run.words]]
                                elif run.ok:
                                    notes.append(f"mutated run {i}: passed without the measured instruction\n{run.words}")
                                else:
                                    notes.append(f"mutated run {i}: killed - " + "; ".join(run.problems))
                            if mutated.startswith("SURVIVED"):
                                record["removal_candidate"] = case["measures"]
                                notes += [f"removal candidate (decide in the PR): {m['file']}: {m['text'][:80]!r}"
                                          for m in case["measures"]]
                    record["mutated"] = mutated
                    line = f"{case['id']:<32} {verdict:<14} {mutated}"
                    ok = ok and mut_ok
                record.update({"model_ids": sorted(set().union(*(run.models for run in base))),
                               "cli": next((run.cli for run in base if run.cli), ""),
                               "setting_sources": SETTING_SOURCES, "user_memory_isolated": "unverified"})
                print(line, flush=True)
                for note in notes:
                    print(f"    - {note}", flush=True)
                with args.results.open("a", encoding="utf-8") as results:
                    results.write(json.dumps(record, ensure_ascii=False) + "\n")
                failures += 0 if ok else 1
        except AuthFailure as exc:
            pool.shutdown(wait=False, cancel_futures=True)
            print(f"ABORT: claude could not authenticate - {exc} Check that the `claude` CLI is logged in "
                  "(run `claude`, then /login).", flush=True)
            return 2
        except BaseException:
            pool.shutdown(wait=False, cancel_futures=True)  # do not spend quota on runs nobody will read
            raise
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
