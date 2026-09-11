#!/usr/bin/env bash
# ensure-husky.sh 회귀 테스트 — fresh clone(hooksPath unset)과 worktree(hooksPath set,
# .husky/_ 없음) 두 상태 모두에서 shim 이 생기고, husky 를 안 쓰는 repo 는 건드리지 않는다.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$HERE/../harness/ensure-husky.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
fail=0
check() { if [ "$2" = "$3" ]; then echo "ok  $1"; else echo "FAIL $1 — 기대 [$3] 실제 [$2]"; fail=1; fi; }

mk() { # $1 dir, $2 with_husky(yes|no)
  mkdir -p "$1" && git -C "$1" init -q
  if [ "$2" = yes ]; then
    mkdir -p "$1/.husky"; printf '#!/usr/bin/env sh\necho hook-ran\n' > "$1/.husky/pre-commit"
    printf '{"scripts":{"prepare":"husky"}}\n' > "$1/package.json"
  else
    printf '{"scripts":{}}\n' > "$1/package.json"
  fi
}

# 1. fresh clone: hooksPath unset
mk "$TMP/fresh" yes
(cd "$TMP/fresh" && bash "$SCRIPT" --quiet)
check "fresh clone → hooksPath 설정" "$(git -C "$TMP/fresh" config core.hooksPath)" ".husky/_"
check "fresh clone → shim 생성" "$(test -x "$TMP/fresh/.husky/_/pre-commit" && echo yes || echo no)" "yes"
check "fresh clone → shim 이 실제 훅을 실행" "$(cd "$TMP/fresh" && sh .husky/_/pre-commit)" "hook-ran"

# 2. worktree 상태: hooksPath 는 있는데 .husky/_ 없음
mk "$TMP/wt" yes
git -C "$TMP/wt" config core.hooksPath .husky/_
(cd "$TMP/wt" && bash "$SCRIPT" --quiet)
check "worktree → shim 생성" "$(test -x "$TMP/wt/.husky/_/pre-commit" && echo yes || echo no)" "yes"

# 3. 멱등: 두 번 돌려도 같다
(cd "$TMP/wt" && bash "$SCRIPT" --quiet)
check "멱등" "$(ls -A "$TMP/wt/.husky/_" | sort | tr '\n' ' ')" ".gitignore pre-commit "

# 4. husky 를 안 쓰는 repo 는 건드리지 않는다
mk "$TMP/plain" no
(cd "$TMP/plain" && bash "$SCRIPT" --quiet)
check "non-husky repo → 무변경" "$(git -C "$TMP/plain" config core.hooksPath || echo unset)" "unset"

# 5. 절대 경로 hooksPath(메인 체크아웃): 우리 .husky/_ 를 가리키면 상대형으로 정규화하고 shim 을 만든다
mk "$TMP/abs" yes
git -C "$TMP/abs" config core.hooksPath "$TMP/abs/.husky/_"
(cd "$TMP/abs" && bash "$SCRIPT" --quiet)
check "절대 hooksPath → 상대형으로 정규화" "$(git -C "$TMP/abs" config core.hooksPath)" ".husky/_"
check "절대 hooksPath → shim 생성" "$(test -x "$TMP/abs/.husky/_/pre-commit" && echo yes || echo no)" "yes"

# 6. linked worktree + 절대 hooksPath(메인의 .husky/_): 정규화되고 worktree 쪽에 shim 이 생긴다
mk "$TMP/main" yes
git -C "$TMP/main" add -A
git -C "$TMP/main" -c user.name=t -c user.email=t@example.com commit -q -m init
git -C "$TMP/main" worktree add -q "$TMP/wtlink"
git -C "$TMP/main" config core.hooksPath "$TMP/main/.husky/_"
(cd "$TMP/wtlink" && bash "$SCRIPT" --quiet)
check "worktree 절대 hooksPath → 상대형으로 정규화" "$(git -C "$TMP/wtlink" config core.hooksPath)" ".husky/_"
check "worktree 절대 hooksPath → worktree 쪽 shim 생성" "$(test -x "$TMP/wtlink/.husky/_/pre-commit" && echo yes || echo no)" "yes"

# 7. 무관한 절대 경로는 남의 설정이다 — 건드리지 않는다
mk "$TMP/other" yes
mkdir -p "$TMP/elsewhere"
git -C "$TMP/other" config core.hooksPath "$TMP/elsewhere"
(cd "$TMP/other" && bash "$SCRIPT" --quiet)
check "무관한 절대 hooksPath → 무변경" "$(git -C "$TMP/other" config core.hooksPath)" "$TMP/elsewhere"
check "무관한 절대 hooksPath → shim 안 만듦" "$(test -e "$TMP/other/.husky/_/pre-commit" && echo yes || echo no)" "no"

[ $fail -eq 0 ] && echo "PASS: ensure-husky tests" || { echo "FAIL: ensure-husky tests"; exit 1; }
