#!/usr/bin/env sh
# Make sure git actually runs .husky/pre-commit in THIS checkout.
#
# husky v9 sets `core.hooksPath=.husky/_` (shared by every worktree of the repo)
# but only `pnpm install` creates the gitignored `.husky/_/` shims — so a fresh
# clone or a linked worktree silently runs zero hooks. This script writes a
# minimal shim for each hook file under .husky/ when the husky-generated one is
# missing. `pnpm install` overwrites it with the real husky shim later; both
# behave the same for our hooks (they resolve the repo via git rev-parse).
#
# Idempotent. Writes only inside the gitignored .husky/_/. Usage:
#   bash scripts/harness/ensure-husky.sh [--quiet]
set -eu
QUIET="${1:-}"
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
[ -n "$ROOT" ] || exit 0
HOOKS_PATH="$(git -C "$ROOT" config core.hooksPath 2>/dev/null || true)"
if [ -z "$HOOKS_PATH" ]; then
  # Fresh clone: husky's `prepare` has not run yet, so core.hooksPath is unset too.
  # Only claim the path when the repo is husky-managed (hook files + prepare script).
  if [ -f "$ROOT/.husky/pre-commit" ] && grep -q '"prepare": *"husky"' "$ROOT/package.json" 2>/dev/null; then
    git -C "$ROOT" config core.hooksPath .husky/_
    HOOKS_PATH=".husky/_"
  fi
fi

# Physical path of `<dir>/<name>`, resolving only the parent (the `_` directory itself may not
# exist yet — that is what this script creates). Empty when the parent cannot be resolved.
# `realpath` is missing on older macOS, hence the `cd && pwd -P` fallback; never kill `set -e`.
resolve_dir() {
  parent="$(realpath "$(dirname "$1")" 2>/dev/null || (cd "$(dirname "$1")" 2>/dev/null && pwd -P) || true)"
  [ -n "$parent" ] && echo "$parent/$(basename "$1")" || true
}

case "$HOOKS_PATH" in
  /*)
    # Absolute hooksPath (seen on some checkouts). A relative `.husky/_` is what husky writes and
    # is resolved per worktree, so each worktree runs its own hook files; an absolute one pins
    # every worktree to the main checkout's hooks and makes the string comparison below fail.
    # Normalize it only when it really is this repo's .husky/_ — anything else is someone's
    # deliberate configuration and stays untouched.
    COMMON_DIR="$(git -C "$ROOT" rev-parse --git-common-dir 2>/dev/null || true)"
    case "$COMMON_DIR" in /*) ;; *) COMMON_DIR="$ROOT/$COMMON_DIR" ;; esac
    MAIN_ROOT="$(dirname "$COMMON_DIR")"
    actual="$(resolve_dir "$HOOKS_PATH")"
    if [ -n "$actual" ] && { [ "$actual" = "$(resolve_dir "$MAIN_ROOT/.husky/_")" ] || [ "$actual" = "$(resolve_dir "$ROOT/.husky/_")" ]; }; then
      git -C "$ROOT" config core.hooksPath .husky/_
      HOOKS_PATH=".husky/_"
      [ "$QUIET" = "--quiet" ] || echo "ensure-husky: normalized core.hooksPath to .husky/_ (was $actual)."
    fi
    ;;
esac
[ "$HOOKS_PATH" = ".husky/_" ] || exit 0   # not a husky-managed repo; nothing to do

created=""
for hook in "$ROOT"/.husky/*; do
  [ -f "$hook" ] || continue
  name="$(basename "$hook")"
  case "$name" in _|*.sh|.*) continue ;; esac
  target="$ROOT/.husky/_/$name"
  [ -f "$target" ] && continue
  mkdir -p "$ROOT/.husky/_"
  printf '%s\n' '#!/usr/bin/env sh' \
    '# shim written by scripts/harness/ensure-husky.sh (pnpm install replaces it)' \
    'exec sh "$(dirname "$0")/../'"$name"'" "$@"' > "$target"
  chmod +x "$target"
  created="$created $name"
done
[ -f "$ROOT/.husky/_/.gitignore" ] || { mkdir -p "$ROOT/.husky/_"; printf '*\n' > "$ROOT/.husky/_/.gitignore"; }

if [ -n "$created" ] && [ "$QUIET" != "--quiet" ]; then
  echo "ensure-husky: wrote shim(s) for$created — commit gates are live in this checkout."
fi
exit 0
