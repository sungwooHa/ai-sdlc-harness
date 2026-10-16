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

# 8. 훅 파일마다 shim 을 쓴다 — commit-msg 는 메시지 파일 경로($1)를 받아야 한다
mk "$TMP/msg" yes
printf '#!/usr/bin/env sh\necho "msg:$1"\n' > "$TMP/msg/.husky/commit-msg"
(cd "$TMP/msg" && bash "$SCRIPT" --quiet)
check "commit-msg → shim 생성" "$(test -x "$TMP/msg/.husky/_/commit-msg" && echo yes || echo no)" "yes"
check "commit-msg → shim 이 인자를 넘김" "$(cd "$TMP/msg" && sh .husky/_/commit-msg .git/COMMIT_EDITMSG)" "msg:.git/COMMIT_EDITMSG"

# 9. 훅 파일을 지우면 shim 은 건너뛰고(exit 0, 출력 없음), 다음 실행이 stale shim 을 지운다
rm "$TMP/msg/.husky/commit-msg"
check "훅 삭제 → shim 이 조용히 exit 0" "$(cd "$TMP/msg" && sh .husky/_/commit-msg .git/COMMIT_EDITMSG 2>&1; echo "rc=$?")" "rc=0"
(cd "$TMP/msg" && bash "$SCRIPT" --quiet)
check "훅 삭제 → stale shim 삭제" "$(test -e "$TMP/msg/.husky/_/commit-msg" && echo yes || echo no)" "no"
check "훅 삭제 → 남은 훅의 shim 유지" "$(cd "$TMP/msg" && sh .husky/_/pre-commit)" "hook-ran"

# 10. 옛 형식 shim(존재 확인 없음)은 새 형식으로 바뀌고, husky 가 쓴 shim 은 건드리지 않는다
mk "$TMP/old" yes
printf '#!/usr/bin/env sh\necho post\n' > "$TMP/old/.husky/post-merge"
mkdir -p "$TMP/old/.husky/_"
git -C "$TMP/old" config core.hooksPath .husky/_
printf '%s\n' '#!/usr/bin/env sh' '# shim written by scripts/harness/ensure-husky.sh (pnpm install replaces it)' \
  'exec sh "$(dirname "$0")/../pre-commit" "$@"' > "$TMP/old/.husky/_/pre-commit"
printf '%s\n' '#!/usr/bin/env sh' '. "$(dirname "$0")/h"' > "$TMP/old/.husky/_/post-merge"
(cd "$TMP/old" && bash "$SCRIPT" --quiet)
check "옛 shim → 존재 확인 추가" "$(grep -c 'exit 0' "$TMP/old/.husky/_/pre-commit")" "1"
check "husky shim → 무변경" "$(cat "$TMP/old/.husky/_/post-merge")" "$(printf '%s\n' '#!/usr/bin/env sh' '. "$(dirname "$0")/h"')"
rm "$TMP/old/.husky/post-merge"
(cd "$TMP/old" && bash "$SCRIPT" --quiet)
check "husky shim → 훅이 없어도 지우지 않음" "$(test -e "$TMP/old/.husky/_/post-merge" && echo yes || echo no)" "yes"

[ $fail -eq 0 ] && echo "PASS: ensure-husky tests" || { echo "FAIL: ensure-husky tests"; exit 1; }
