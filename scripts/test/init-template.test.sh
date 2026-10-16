#!/usr/bin/env bash
# Regression test for scripts/harness/init-template.sh on temporary copies of this template.
# After init: .agents/harness.json parses, the template's own change folders and eval results are gone,
# ADR-0000 and docs/references/ stay, the Branches line follows the branch options, the harness check
# passes, and with husky active the first commit succeeds while a staged fake secret is refused and
# pre-push runs the tests without the GIT_* variables git exports to hooks. An initialized project
# (prefix acme, the eval runner's own) passes every scripts/test/*.test.py and *.test.sh.
# Placeholders are written split ('__X''__') so init never substitutes them in this file.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
# Runs only in the template original: an initialized project (placeholders filled, init script
# usually deleted) has nothing to test. Original = the init script exists and one of its subst
# placeholders is still in AGENTS.md or package.json.
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
  echo "FAIL: init-template tests — template original (init script and placeholders present) but AGENTS.md lacks the default-branch placeholder. Restore the Branches line init rewrites with sed."
  exit 1
fi
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
fail=0
check() { if [ "$2" = "$3" ]; then echo "ok  $1"; else echo "FAIL $1 — expected [$3] got [$2]"; fail=1; fi; }

copy() { # $1 name; prints the directory of a copy of the tracked and untracked-not-ignored files
  local d="$TMP/$1"
  mkdir -p "$d"
  git -C "$REPO" ls-files -z --cached --others --exclude-standard | (cd "$REPO" &&
    while IFS= read -r -d '' f; do if [ -e "$f" ] || [ -L "$f" ]; then printf '%s\0' "$f"; fi; done |
    tar --null -T - -cf -) | tar -xf - -C "$d"
  echo "$d"
}
init() { # $1 name, rest: init options; prints the copy's directory
  local d; d="$(copy "$1")"; shift
  sh "$d/scripts/harness/init-template.sh" --project-name demo --prefix demo "$@" >/dev/null
  echo "$d"
}
branches() { grep -m1 -- '- Branches:' "$1/AGENTS.md" | sed 's/^ *//'; }
exists() { if [ -e "$1" ]; then echo yes; else echo no; fi; }

# Default init, seeded with a change folder and eval results so their removal is always exercised.
d="$(copy default)"
mkdir -p "$d/docs/changes/000000_00-seeded"; echo "# seeded" > "$d/docs/changes/000000_00-seeded/intent.md"
echo '{"case":"seeded"}' > "$d/.claude/evals/results.jsonl"
sh "$d/scripts/harness/init-template.sh" --project-name demo --prefix demo >/dev/null
check "harness.json parses" "$(python3 -c 'import json,sys; json.load(open(sys.argv[1])); print("ok")' "$d/.agents/harness.json" 2>&1)" "ok"
check "change folders removed, README and _templates kept" "$(ls "$d/docs/changes" | LC_ALL=C sort | tr '\n' ' ')" "README.md _templates "
check "eval results removed" "$(exists "$d/.claude/evals/results.jsonl")" "no"
check "ADR-0000 kept" "$(exists "$d/docs/decisions/0000-harness-decisions.md")" "yes"
check "docs/references kept" "$(ls "$d/docs/references")" "$(ls "$REPO/docs/references")"
check "default → main trunk" "$(branches "$d")" '- Branches: `main` (trunk), `feature/*`.'

# The initialized copy as a fresh project: husky active (core.hooksPath as husky's prepare sets it,
# shims from ensure-husky), harness check green, first commit through pre-commit succeeds.
git -C "$d" init -q
git -C "$d" config user.name test && git -C "$d" config user.email test@example.com
git -C "$d" config commit.gpgsign false && git -C "$d" config core.hooksPath .husky/_
(cd "$d" && bash scripts/harness/ensure-husky.sh --quiet)
check "husky pre-commit shim active" "$(test -x "$d/.husky/_/pre-commit" && echo yes || echo no)" "yes"
check "harness check passes after init" "$(python3 "$d/scripts/check-agent-harness.py" --repo-root "$d" 2>&1 | head -1)" "PASS: agent harness check"
git -C "$d" add -A
code=0; out="$(git -C "$d" commit -q -m "chore: init demo" 2>&1)" || code=$?
check "first commit with husky active succeeds" "$code" "0"
[ "$code" = 0 ] || echo "$out"
# Negative: a fake AWS key assembled at run time (so this file never matches the scan) is refused.
head_before="$(git -C "$d" rev-parse -q --verify HEAD || true)"
printf 'AWS_KEY=%s%s\n' "AKIA" "QQQQQQQQQQQQQQQQ" > "$d/leak.env"
git -C "$d" add leak.env
code=0; out="$(git -C "$d" commit -q -m "chore: add env" 2>&1)" || code=$?
check "staged fake secret → pre-commit refuses" "$code" "1"
check "refusal names file and pattern" "$(printf '%s' "$out" | grep -c 'leak.env:1: aws-access-key' || true)" "1"
check "refused commit leaves HEAD unchanged" "$(git -C "$d" rev-parse -q --verify HEAD || true)" "$head_before"
# git exports GIT_DIR and friends to hooks; the tests pre-push runs make their own repositories.
mkdir -p "$TMP/bin"
printf '#!/bin/sh\necho "${GIT_DIR-unset} ${GIT_WORK_TREE-unset} ${GIT_INDEX_FILE-unset} $*"\n' > "$TMP/bin/pnpm"
chmod +x "$TMP/bin/pnpm"
out="$(cd "$d" && GIT_DIR="$d/.git" GIT_WORK_TREE="$d" GIT_INDEX_FILE="$d/.git/index" PATH="$TMP/bin:$PATH" sh .husky/pre-push)"
check "pre-push runs tests without GIT_DIR/GIT_WORK_TREE/GIT_INDEX_FILE" "$out" "unset unset unset test"

d="$(init master --default-branch master)"
check "default branch master only → master trunk" "$(branches "$d")" '- Branches: `master` (trunk), `feature/*`.'
check "default branch master only → PRs target master" "$(grep -c 'PRs target `master`' "$d/AGENTS.md")" "1"

d="$(init two --integration-branch develop)"
check "integration branch develop → two branches" "$(branches "$d")" '- Branches: `main` (production), `develop` (integration), `feature/*`.'

# A project made from the template filled the placeholders and usually deleted the init script. Its
# test:harness runs this file too, so it must skip, not fail.
skipped() { # $1 copy; prints the copy's own run of this test as test:harness runs it, then its exit code
  local code=0 out
  out="$(cd "$1" && bash scripts/test/init-template.test.sh 2>&1)" || code=$?
  printf '%s exit %s' "$out" "$code"
}
d="$(init project)"
git -C "$d" init -q
check "initialized project → skip" "$(skipped "$d")" "SKIP: init-template tests (already initialized) exit 0"
rm -f "$d/scripts/harness/init-template.sh"
check "init script deleted too → skip" "$(skipped "$d")" "SKIP: init-template tests (already initialized) exit 0"

# The initialized project's own suite passes (this file is covered by the skip checks above). Prefix acme
# is the eval runner's init prefix: the collision that broke a test whose placeholders init had filled.
d="$(init suite --prefix acme)"
git -C "$d" init -q
for t in "$d"/scripts/test/*.test.py "$d"/scripts/test/*.test.sh; do
  name="${t#"$d"/}"
  [ "$name" = scripts/test/init-template.test.sh ] && continue
  case "$name" in *.py) runner=python3 ;; *) runner=bash ;; esac
  code=0; out="$(cd "$d" && "$runner" "$name" 2>&1)" || code=$?
  check "initialized project: $name passes" "$code" "0"
  [ "$code" = 0 ] || printf '%s\n' "$out" | tail -15
done

# Editing only the Branches line in the original must not skip: it fails at detection, before the
# full (recursive) run.
d="$(copy edited)"
sed 's/__DEFAULT_''BRANCH__/main/' "$d/AGENTS.md" > "$d/AGENTS.md.new" && mv "$d/AGENTS.md.new" "$d/AGENTS.md"
git -C "$d" init -q && git -C "$d" add -A
out="$(skipped "$d")"
check "original with Branches line edited → exit 1" "${out##* exit }" "1"
check "original with Branches line edited → no SKIP" "$(printf '%s' "$out" | grep -c SKIP || true)" "0"

[ "$fail" = 0 ] && echo "PASS: init-template tests" || { echo "FAIL: init-template tests"; exit 1; }
