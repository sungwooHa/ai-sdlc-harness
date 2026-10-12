#!/usr/bin/env bash
# init-template.sh 회귀 테스트 — 통합 브랜치는 따로 주지 않으면 기본 브랜치를 따른다(트렁크).
# 추적 파일을 임시 폴더에 복사해 init 을 돌리고 AGENTS.md 브랜치 줄과 harness.yaml base 를 본다.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
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

[ "$fail" = 0 ] && echo "PASS: init-template tests" || { echo "FAIL: init-template tests"; exit 1; }
