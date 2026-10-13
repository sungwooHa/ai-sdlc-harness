#!/usr/bin/env bash
# init-template.sh 회귀 테스트 — 통합 브랜치는 따로 주지 않으면 기본 브랜치를 따른다(트렁크).
# 추적 파일을 임시 폴더에 복사해 init 을 돌리고 AGENTS.md 브랜치 줄과 harness.yaml base 를 본다.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
# 템플릿 원본에서만 돈다: init 뒤 프로젝트(자리표시자 치환, init 스크립트 삭제)에는 시험할 것이 없다.
# 원본 = init 스크립트가 있고, 그 subst 줄의 자리표시자가 AGENTS.md·package.json 에 하나라도 남음. 원본은
# 건너뛰지 않는다. 자리표시자는 나눠 적어 init 이 이 줄까지 치환하지 않게 한다.
INIT="$REPO/scripts/harness/init-template.sh"
original=0
if [ -f "$INIT" ]; then
  for p in $(sed -n 's/^subst \(__[A-Z0-9_]*__\) .*/\1/p' "$INIT"); do
    if grep -qF -- "$p" "$REPO/AGENTS.md" "$REPO/package.json"; then original=1; fi
  done
fi
if [ "$original" = 0 ]; then
  echo "SKIP: init-template tests (already initialized)"; exit 0
fi
if ! grep -q '__DEFAULT_''BRANCH__' "$REPO/AGENTS.md"; then
  echo "FAIL: init-template tests — 원본 템플릿(init 스크립트와 자리표시자가 남음)인데 AGENTS.md 에 기본 브랜치 자리표시자가 없다. init 이 sed 로 고치는 Branches 줄을 되돌린다"
  exit 1
fi
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
fail=0
check() { if [ "$2" = "$3" ]; then echo "ok  $1"; else echo "FAIL $1 — 기대 [$3] 실제 [$2]"; fail=1; fi; }

copy() { # $1 name; prints the directory of a copy of the tracked files
  local d="$TMP/$1"
  mkdir -p "$d"
  git -C "$REPO" ls-files -z | (cd "$REPO" && tar --null -T - -cf -) | tar -xf - -C "$d"
  echo "$d"
}
init() { # $1 name, rest: init options; prints the copy's directory
  local d; d="$(copy "$1")"; shift
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

# 원본에서 Branches 줄만 고쳐도 건너뛰면 안 된다. 판별 단계에서 실패로 끝나 전체 시험(재귀)까지 가지 않는다.
d="$(copy edited)"
sed 's/__DEFAULT_''BRANCH__/main/' "$d/AGENTS.md" > "$d/AGENTS.md.new" && mv "$d/AGENTS.md.new" "$d/AGENTS.md"
git -C "$d" init -q && git -C "$d" add -A
out="$(skipped "$d")"
check "원본에서 Branches 줄을 고침 → exit 1" "${out##* exit }" "1"
check "원본에서 Branches 줄을 고침 → SKIP 없음" "$(printf '%s' "$out" | grep -c SKIP || true)" "0"

[ "$fail" = 0 ] && echo "PASS: init-template tests" || { echo "FAIL: init-template tests"; exit 1; }
