#!/usr/bin/env bash
# check-plan-artifact.sh 회귀 테스트 — 다중 앱·packages 변경에 plan.md 가 없으면 경고/차단,
# 단일 앱 변경이나 plan.md 동반 변경은 통과.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$HERE/../harness/check-plan-artifact.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
fail=0
check() { if [ "$2" = "$3" ]; then echo "ok  $1"; else echo "FAIL $1 — 기대 [$3] 실제 [$2]"; fail=1; fi; }

repo() { # $1 name; creates base commit on branch 'base'
  local d="$TMP/$1"; mkdir -p "$d"; git -C "$d" init -q -b base
  git -C "$d" -c user.name=t -c user.email=t@t commit -q --allow-empty -m base
  git -C "$d" switch -q -c work
  echo "$d"
}
commit_files() { # $1 dir, rest: paths
  local d="$1"; shift
  for p in "$@"; do mkdir -p "$d/$(dirname "$p")"; echo x >> "$d/$p"; done
  git -C "$d" add -A && git -C "$d" -c user.name=t -c user.email=t@t commit -q -m change
}
run() { (cd "$1" && PLAN_GATE="${2:-warn}" bash "$SCRIPT" base 2>&1; echo "exit=$?"); }

d="$(repo one-app)"; commit_files "$d" apps/frontend/src/a.ts apps/frontend/src/b.ts
check "단일 앱 → ok" "$(run "$d" | tail -2 | tr '\n' ' ')" "check-plan-artifact: ok exit=0 "

d="$(repo two-apps-warn)"; commit_files "$d" apps/frontend/src/a.ts apps/backend/src/B.java
out="$(run "$d")"
check "두 앱 + plan 없음 → 경고" "$(echo "$out" | grep -c 'adds no docs/changes')" "1"
check "두 앱 + plan 없음 → warn 모드 exit 0" "$(echo "$out" | tail -1)" "exit=0"

d="$(repo two-apps-enforce)"; commit_files "$d" apps/frontend/src/a.ts apps/backend/src/B.java
check "두 앱 + plan 없음 → enforce exit 1" "$(run "$d" enforce | tail -1)" "exit=1"

d="$(repo packages-enforce)"; commit_files "$d" packages/api-contracts/src/x.ts
check "packages 계약 + plan 없음 → enforce exit 1" "$(run "$d" enforce | tail -1)" "exit=1"

d="$(repo two-apps-with-plan)"; commit_files "$d" apps/frontend/src/a.ts apps/desktop/src/m.ts docs/changes/two-apps/plan.md
check "두 앱 + plan.md → ok" "$(run "$d" enforce | tail -1)" "exit=0"

d="$(repo off)"; commit_files "$d" apps/frontend/src/a.ts apps/backend/src/B.java
check "PLAN_GATE=off → 침묵 exit 0" "$(run "$d" off | tr '\n' ' ')" "exit=0 "

[ $fail -eq 0 ] && echo "PASS: check-plan-artifact tests" || { echo "FAIL: check-plan-artifact tests"; exit 1; }
