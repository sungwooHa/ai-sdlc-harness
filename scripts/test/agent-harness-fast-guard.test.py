#!/usr/bin/env python3
"""agent-harness-fast-guard.test.py — husky 배선 자가 점검 회귀 테스트.

단독 실행:
  python3 scripts/test/agent-harness-fast-guard.test.py

husky 가 설치돼 있지 않으면 커밋 게이트가 통째로 없는데 커밋은 그냥 성공한다.
아무도 모르는 상태가 되므로 Stop 경로에서 알린다. 그 경고가 (1) 실제로 뜨는지
(2) 정상 환경·CI·--staged 에서는 안 뜨는지를 고정한다.

CI 오탐이 특히 위험하다 — CI 에서 잘못 실패하는 검사는 하네스 신뢰를 깎는다.
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
GUARD = REPO / "scripts" / "agent-harness-fast-guard.py"

_failures = []
_passed = 0


def check(name, actual, expected):
    global _passed
    if actual == expected:
        _passed += 1
    else:
        _failures.append(f"{name}\n    기대: {expected!r}\n    실제: {actual!r}")


def run(repo, *args, **env_extra):
    env = dict(os.environ)
    env.pop("CI", None)
    env.pop("BITBUCKET_BUILD_NUMBER", None)
    env.update(env_extra)
    p = subprocess.run([sys.executable, str(GUARD), "--repo-root", str(repo), *args],
                       capture_output=True, text=True, errors="replace", env=env)
    return p.returncode, p.stderr


def make_repo():
    """find_repo_root 가 요구하는 표식(AGENTS.md·package.json)을 갖춘 임시 repo."""
    root = Path(tempfile.mkdtemp(prefix="fastguard-"))
    subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
    (root / "AGENTS.md").write_text("# test\n", encoding="utf-8")
    (root / "package.json").write_text('{"name":"t"}\n', encoding="utf-8")
    return root


WARN = "husky pre-commit 미배선"

_tmp = make_repo()

_code, _err = run(_tmp, "--quiet-unless-relevant")
check("husky 미설치 → 경고한다", WARN in _err, True)
check("미배선은 실패다(exit 1) — 경고만 내던 동안 worktree 커밋이 게이트 없이 나갔다", _code, 1)
check("단 Stop 훅을 막는 exit 2 는 아니다", _code != 2, True)
check("복구 명령을 안내한다", "ensure-husky.sh" in _err, True)

_code, _err = run(_tmp, "--quiet-unless-relevant", CI="1")
check("CI 에서는 침묵한다", WARN in _err, False)
check("CI 에서는 exit 0", _code, 0)

_code, _err = run(_tmp, "--quiet-unless-relevant", BITBUCKET_BUILD_NUMBER="42")
check("Bitbucket 파이프라인에서도 침묵한다", WARN in _err, False)

_code, _err = run(_tmp, "--staged")
check("--staged 경로에서는 검사하지 않는다", WARN in _err, False)

shutil.rmtree(_tmp)

# 배선 정상 케이스. 실제 저장소로 검사하면 안 된다 — `.husky/_/` 는 gitignore 대상이라
# CI 체크아웃에는 없다. 그러면 이 케이스가 CI 에서만 실패하고, 그게 곧 우리가 피하려던
# "CI 오탐"이다. 임시 repo 에 배선을 직접 만들어 환경과 무관하게 만든다.
_wired = make_repo()
(_wired / ".husky" / "_").mkdir(parents=True)
(_wired / ".husky" / "_" / "pre-commit").write_text("#!/usr/bin/env sh\n", encoding="utf-8")
subprocess.run(["git", "-C", str(_wired), "config", "core.hooksPath", ".husky/_"], check=True)

_code, _err = run(_wired, "--quiet-unless-relevant")
check("배선 정상이면 침묵한다", WARN in _err, False)

# 절대 경로 hooksPath 도 우리 .husky/_ 로 풀리면 배선된 것이다 — 문자열 비교만 하던 동안
# 이 저장소(절대 hooksPath)에서 훅이 실제로 도는데도 매 Stop 마다 미배선 경고가 났다.
subprocess.run(["git", "-C", str(_wired), "config", "core.hooksPath", str(_wired / ".husky" / "_")], check=True)
_code, _err = run(_wired, "--quiet-unless-relevant")
check("절대 hooksPath 가 .husky/_ 로 풀리면 침묵한다", WARN in _err, False)

# 절대 경로가 다른 곳을 가리키면 우리 훅이 아니다.
subprocess.run(["git", "-C", str(_wired), "config", "core.hooksPath", str(_wired / "nope")], check=True)
_code, _err = run(_wired, "--quiet-unless-relevant")
check("무관한 절대 hooksPath 는 경고한다", WARN in _err, True)
subprocess.run(["git", "-C", str(_wired), "config", "core.hooksPath", ".husky/_"], check=True)

# hooksPath 는 맞는데 러너 파일이 없으면 — 반쪽 배선도 잡아야 한다.
(_wired / ".husky" / "_" / "pre-commit").unlink()
_code, _err = run(_wired, "--quiet-unless-relevant")
check("hooksPath 만 있고 러너가 없으면 경고한다", WARN in _err, True)

shutil.rmtree(_wired)

if _failures:
    print(f"실패 {len(_failures)}건 / 통과 {_passed}건\n", file=sys.stderr)
    for f in _failures:
        print(f"  - {f}", file=sys.stderr)
    sys.exit(1)
print(f"통과 {_passed}건")
print("agent-harness-fast-guard 회귀 테스트 전부 통과")
