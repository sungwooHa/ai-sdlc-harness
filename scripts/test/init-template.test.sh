#!/usr/bin/env bash
# init-template.sh 회귀 테스트 — 통합 브랜치는 따로 주지 않으면 기본 브랜치를 따른다(트렁크).
# 추적 파일을 임시 폴더에 복사해 init 을 돌리고 AGENTS.md 브랜치 줄과 harness.yaml base 를 본다.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
# 템플릿 원본에서만 돈다: init 뒤 프로젝트(자리표시자 치환, init 스크립트 삭제)에는 시험할 것이 없다.
# 자리표시자는 나눠 적어 init 이 이 줄까지 치환하지 않게 한다.
if ! { grep -q '__DEFAULT_''BRANCH__' "$REPO/AGENTS.md" && [ -f "$REPO/scripts/harness/init-template.sh" ]; }; then
  echo "SKIP: init-template tests (already initialized)"; exit 0
fi
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
fail=0
check() { if [ "$2" = "$3" ]; then echo "ok  $1"; else echo "FAIL $1 — 기대 [$3] 실제 [$2]"; fail=1; fi; }

init() { # $1 name, rest: init options; prints the copy's directory
  local d="$TMP/$1"; shift
  mkdir -p "$d"
  git -C "$REPO" ls-files -z | (cd "$REPO" && tar --null -T - -cf -) | tar -xf - -C "$d"
  sh "$d/scripts/harness/init-template.sh" --project-name demo --prefix demo "$@" >/dev/null
  echo "$d"
}
branches() { grep -m1 -- '- Branches:' "$1/AGENTS.md" | sed 's/^ *//'; }
base() { python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["artifact_chain"]["plan_gate"]["base"])' "$1/.agents/harness.yaml"; }

d="$(init default)"
check "기본값 → main 트렁크" "$(branches "$d")" '- Branches: `main` (trunk), `feature/*`.'
check "기본값 → base origin/main" "$(base "$d")" "origin/main"

d="$(init master --default-branch master)"
check "기본 브랜치만 master → master 트렁크" "$(branches "$d")" '- Branches: `master` (trunk), `feature/*`.'
check "기본 브랜치만 master → PR 대상 master" "$(grep -c 'PRs target `master`' "$d/AGENTS.md")" "1"
check "기본 브랜치만 master → base origin/master" "$(base "$d")" "origin/master"

d="$(init two --integration-branch develop)"
check "통합 브랜치 develop → 두 브랜치" "$(branches "$d")" '- Branches: `main` (production), `develop` (integration), `feature/*`.'
check "통합 브랜치 develop → base origin/develop" "$(base "$d")" "origin/develop"

# 템플릿으로 만든 프로젝트는 자리표시자를 채웠고 대개 init 스크립트도 지웠다. 그 프로젝트의 test:harness 도
# 이 파일을 돌리므로 실패하지 않고 건너뛰어야 한다.
skipped() { # $1 copy; prints the copy's own run of this test as test:harness runs it, then its exit code
  local code=0 out
  out="$(cd "$1" && bash scripts/test/init-template.test.sh 2>&1)" || code=$?
  printf '%s exit %s' "$out" "$code"
}
d="$(init project)"
git -C "$d" init -q
check "init 뒤 프로젝트 → 건너뜀" "$(skipped "$d")" "SKIP: init-template tests (already initialized) exit 0"
rm -f "$d/scripts/harness/init-template.sh"
check "init 스크립트까지 지운 프로젝트 → 건너뜀" "$(skipped "$d")" "SKIP: init-template tests (already initialized) exit 0"

[ "$fail" = 0 ] && echo "PASS: init-template tests" || { echo "FAIL: init-template tests"; exit 1; }
