#!/usr/bin/env python3
"""Fast changed-file guard for agent harness structure.

This script is intentionally narrower than scripts/check-agent-harness.py.
It runs well in Stop/pre-commit hooks and catches the mistakes agents tend to
make while writing: docs outside the active roots declared in
.agents/harness.yaml, and user-specific absolute paths.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path


EXCLUDED_DIRS = {".git", "node_modules", ".venv", "dist", "build", "target", ".gradle", "__pycache__"}
PATH_SCAN_PREFIXES = (
    "AGENTS.md",
    ".agents/skills/",
    ".claude/",
    ".codex/",
    "docs/",
)
HARNESS_RELEVANT_PREFIXES = (
    ".agents/",
    ".claude/",
    ".codex/",
    ".husky/",
    "docs/",
    "scripts/",
)
HARNESS_RELEVANT_FILES = {
    "AGENTS.md",
    "CLAUDE.md",
    "package.json",
}
USER_PATH_PATTERNS = (
    re.compile(r"/Users/[A-Za-z0-9._-]+/[^'\"\s<>)]+"),
    re.compile(r"/home/[A-Za-z0-9._-]+/[^'\"\s<>)]+"),
    re.compile(r"\b[A-Za-z]:[\\/]+Users[\\/]+[^'\"\s<>)]+"),
)


def find_repo_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "AGENTS.md").exists() and (candidate / "package.json").exists():
            return candidate
    return start


def run_git(repo: Path, args: list[str]) -> set[str]:
    completed = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return set()
    return {line.strip() for line in completed.stdout.splitlines() if line.strip()}


def changed_paths(repo: Path, staged: bool) -> set[str]:
    if staged:
        return run_git(repo, ["diff", "--cached", "--name-only"])
    paths = run_git(repo, ["diff", "--name-only", "HEAD"])
    paths.update(run_git(repo, ["ls-files", "--others", "--exclude-standard"]))
    return paths


def load_manifest(repo: Path) -> dict:
    path = repo / ".agents/harness.yaml"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def is_per_app_policy(rel: str) -> bool:
    """apps/<app>/AGENTS.md (and its CLAUDE.md mirror) are harness policy files."""
    parts = rel.split("/")
    return len(parts) == 3 and parts[0] == "apps" and parts[2] in ("AGENTS.md", "CLAUDE.md")


def is_scannable(rel: str) -> bool:
    if rel in HARNESS_RELEVANT_FILES or is_per_app_policy(rel):
        return True
    return any(rel.startswith(prefix) for prefix in PATH_SCAN_PREFIXES)


def is_harness_relevant(rel: str) -> bool:
    if rel in HARNESS_RELEVANT_FILES or is_per_app_policy(rel):
        return True
    return any(rel.startswith(prefix) for prefix in HARNESS_RELEVANT_PREFIXES)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def run_command(repo: Path, command: list[str]) -> tuple[int, str]:
    completed = subprocess.run(
        command,
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.returncode, (completed.stdout.strip() or completed.stderr.strip())


def check_docs_roots(repo: Path, manifest: dict, paths: set[str]) -> list[str]:
    layout = manifest.get("documentation_layout", {})
    active_roots = tuple(
        rel.rstrip("/") + "/"
        for rel in layout.get("active_roots", [])
        if isinstance(rel, str) and rel.startswith("docs/")
    )
    legacy_paths = {
        rel
        for rel in layout.get("legacy_outside_active_paths", [])
        if isinstance(rel, str) and rel.startswith("docs/")
    }
    errors: list[str] = []
    for rel in sorted(paths):
        if not rel.startswith("docs/") or rel == "docs/":
            continue
        if not (repo / rel).exists():
            continue
        if rel.startswith(active_roots):
            continue
        if rel in legacy_paths:
            continue
        errors.append(
            f"{rel}: docs must live under active roots "
            f"({', '.join(root.rstrip('/') for root in active_roots)})"
        )
    return errors


def check_user_absolute_paths(repo: Path, paths: set[str]) -> list[str]:
    errors: list[str] = []
    for rel in sorted(paths):
        if any(part in EXCLUDED_DIRS for part in Path(rel).parts):
            continue
        if not is_scannable(rel):
            continue
        path = repo / rel
        if not path.is_file():
            continue
        text = read_text(path)
        matches: list[str] = []
        for pattern in USER_PATH_PATTERNS:
            matches.extend(pattern.findall(text))
        if matches:
            examples = ", ".join(sorted(set(matches))[:3])
            errors.append(f"{rel}: replace user-specific absolute paths with <repo-root> placeholders ({examples})")
    return errors


def print_preflight(repo: Path) -> int:
    paths = changed_paths(repo, staged=False)
    print("agent-harness-preflight")
    if paths:
        print("- Changed paths detected; run `pnpm check:harness` before completion when docs/harness files change.")
    print("- Read the AGENTS.md of the app you are touching (apps/<app>/AGENTS.md) before editing.")
    print("- Scope unclear? Run `/__PREFIX__-intent` and leave the artifact under docs/changes/.")
    print("- After harness changes (.agents/, .claude/, .codex/, scripts/), run `pnpm check:harness`.")
    return 0


def _resolved_hooks_dir(repo: Path, hooks_path: str) -> Path | None:
    """core.hooksPath 가 이 저장소의 `.husky/_` 를 가리키면 그 실제 경로, 아니면 None.

    husky 는 상대형 `.husky/_` 를 쓰지만 일부 체크아웃은 절대 경로로 잡혀 있다. 절대 경로도
    이 저장소(worktree 자신 또는 메인 체크아웃)의 `.husky/_` 로 풀리면 배선된 것이다 —
    문자열 비교만 하던 동안 훅이 실제로 도는 worktree 에서 매 Stop 마다 오탐이 났다."""
    if not hooks_path:
        return None
    candidates = [(repo / ".husky" / "_").resolve()]
    try:
        common = subprocess.run(["git", "-C", str(repo), "rev-parse", "--git-common-dir"],
                                capture_output=True, text=True, errors="replace").stdout.strip()
        if common:
            common_dir = Path(common) if Path(common).is_absolute() else repo / common
            candidates.append((common_dir.parent / ".husky" / "_").resolve())
    except Exception:
        pass
    actual = (Path(hooks_path) if Path(hooks_path).is_absolute() else repo / hooks_path).resolve()
    return actual if actual in candidates else None


def check_husky_wiring(repo: Path) -> str | None:
    """husky 가 설치돼 있지 않으면 경고 문구, 정상이면 None.

    `pnpm install` 을 안 한 사람은 core.hooksPath 가 안 잡혀 **커밋 게이트가 통째로
    없는데 아무도 모른다** — 커밋이 그냥 성공한다. 디자인 가드·ledger·이 스크립트의
    --staged 검사가 전부 건너뛰어진다.

    여기(Stop 경로)에 둔 이유: 이 스크립트는 .claude 와 .codex 양쪽 Stop 훅에 이미
    배선돼 있어 호스트 무관 커버리지를 공짜로 얻고, CI 는 Stop 경로를 부르지 않아
    CI 오탐이 원천적으로 불가능하다. CI 에서 잘못 실패하는 검사는 하네스 신뢰를 깎는다."""
    try:
        r = subprocess.run(["git", "-C", str(repo), "config", "core.hooksPath"],
                           capture_output=True, text=True, errors="replace")
        hooks_path = r.stdout.strip()
        hooks_dir = _resolved_hooks_dir(repo, hooks_path)
    except Exception:
        return None  # git 을 못 부르면 판정하지 않는다(fail-open)
    if hooks_dir is not None and (hooks_dir / "pre-commit").is_file():
        return None
    return ("agent-harness-fast-guard: husky pre-commit 미배선 — 이 상태의 커밋은 "
            "디자인 가드·ledger·문서 가드를 전부 건너뜁니다. "
            "`bash scripts/harness/ensure-husky.sh` (worktree·fresh clone) 또는 `pnpm install` 로 복구하세요.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Fast changed-file guard for agent harness work.")
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--staged", action="store_true", help="Check staged files only.")
    parser.add_argument("--preflight", action="store_true", help="Print lightweight pre-edit guidance.")
    parser.add_argument(
        "--quiet-unless-relevant",
        action="store_true",
        help="Exit silently when no changed files touch harness-sensitive paths.",
    )
    args = parser.parse_args()

    repo = Path(args.repo_root).resolve() if args.repo_root else find_repo_root(Path.cwd().resolve())
    if args.preflight:
        return print_preflight(repo)

    # 변경 파일 유무·--quiet-unless-relevant 와 무관하게 항상 낸다 — 변경 경로가 아니라
    # 환경 결함이기 때문이다. 미배선은 경고가 아니라 실패다(exit 1): 경고만 내던 동안
    # worktree 에서 만든 커밋은 전부 게이트 없이 나갔다. exit 1 은 Stop 훅을 막지 않는다
    # (막는 것은 exit 2 만). --staged 경로에서는 검사하지 않는다: 거기까지 왔다면 husky 는
    # 이미 돌고 있다. Claude 세션은 SessionStart 훅의 ensure-husky.sh 가 먼저 복구한다.
    husky_unwired = False
    if not args.staged and not (os.environ.get("CI") or os.environ.get("BITBUCKET_BUILD_NUMBER")):
        husky_warning = check_husky_wiring(repo)
        if husky_warning:
            print(husky_warning, file=sys.stderr)
            husky_unwired = True

    paths = changed_paths(repo, staged=args.staged)
    if not paths:
        if args.quiet_unless_relevant:
            return 1 if husky_unwired else 0
        print("agent-harness-fast-guard: ok (no changed files)")
        return 1 if husky_unwired else 0
    if args.quiet_unless_relevant and not any(is_harness_relevant(rel) for rel in paths):
        return 1 if husky_unwired else 0

    manifest = load_manifest(repo)
    errors: list[str] = []
    errors.extend(check_docs_roots(repo, manifest, paths))
    errors.extend(check_user_absolute_paths(repo, paths))

    if errors:
        print("FAIL: agent harness fast guard")
        for error in errors:
            print(f"- {error}")
        print("Run `pnpm check:harness` for the full structural report.")
        return 1

    print("agent-harness-fast-guard: ok")
    return 1 if husky_unwired else 0


if __name__ == "__main__":
    sys.exit(main())
