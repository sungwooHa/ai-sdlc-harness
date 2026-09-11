#!/usr/bin/env sh
# Fill this template's __PLACEHOLDERS__ in place, once, right after "Use this template".
# Usage: sh scripts/harness/init-template.sh --project-name acme --prefix acme [--app web] ...
# Values must not contain the `|` character (it is the sed delimiter).
set -eu

PROJECT_NAME=""; PREFIX=""; APP="app"; APPS_OVERVIEW="Monorepo. Describe the apps and stack here."
PACKAGE_MANAGER="pnpm"; NODE_VERSION="22.12.0"; COMMIT_FORMAT="{type}: [{모듈명}] {변경 내용}"
DEFAULT_BRANCH="main"; INTEGRATION_BRANCH="develop"; HUMAN_DOC_LANG="Korean"
UI_SOURCE_GLOB="apps/*/src/**/ui/**"; CI_FILE=".github/workflows/harness.yml"

while [ $# -gt 0 ]; do
  case "$1" in
    --project-name) PROJECT_NAME="$2"; shift 2 ;;
    --prefix) PREFIX="$2"; shift 2 ;;
    --app) APP="$2"; shift 2 ;;
    --apps-overview) APPS_OVERVIEW="$2"; shift 2 ;;
    --package-manager) PACKAGE_MANAGER="$2"; shift 2 ;;
    --node-version) NODE_VERSION="$2"; shift 2 ;;
    --commit-format) COMMIT_FORMAT="$2"; shift 2 ;;
    --default-branch) DEFAULT_BRANCH="$2"; shift 2 ;;
    --integration-branch) INTEGRATION_BRANCH="$2"; shift 2 ;;
    --ui-source-glob) UI_SOURCE_GLOB="$2"; shift 2 ;;
    --human-doc-lang) HUMAN_DOC_LANG="$2"; shift 2 ;;
    --ci-file) CI_FILE="$2"; shift 2 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done
[ -n "$PROJECT_NAME" ] && [ -n "$PREFIX" ] || { echo "--project-name and --prefix are required" >&2; exit 2; }

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

# 1. Rename the placeholder directories, then re-create the .claude/skills symlink mirror.
for d in .agents/skills/__PREFIX__-*; do
  [ -d "$d" ] || continue
  mv "$d" ".agents/skills/${PREFIX}-$(basename "$d" | sed "s|^__PREFIX__-||")"
done
if [ -d "apps/__APP__" ]; then mv "apps/__APP__" "apps/$APP"; fi
rm -f .claude/skills/*
for s in $(ls .agents/skills); do ln -s "../../.agents/skills/$s" ".claude/skills/$s"; done

# 2. Substitute every placeholder in every tracked text file.
subst() {
  files="$(grep -rlI "$1" . --exclude-dir=.git --exclude-dir=node_modules --exclude=TEMPLATE_SETUP.md --exclude=init-template.sh || true)"
  [ -n "$files" ] || return 0
  # shellcheck disable=SC2086
  printf '%s\n' $files | while read -r f; do sed -i.bak "s|$1|$2|g" "$f" && rm -f "$f.bak"; done
}
subst __PROJECT_NAME__ "$PROJECT_NAME"
subst __PREFIX__ "$PREFIX"
subst __APP__ "$APP"
subst __APPS_OVERVIEW__ "$APPS_OVERVIEW"
subst __PACKAGE_MANAGER__ "$PACKAGE_MANAGER"
subst __NODE_VERSION__ "$NODE_VERSION"
subst __COMMIT_FORMAT__ "$COMMIT_FORMAT"
subst __DEFAULT_BRANCH__ "$DEFAULT_BRANCH"
subst __INTEGRATION_BRANCH__ "$INTEGRATION_BRANCH"
subst __UI_SOURCE_GLOB__ "$UI_SOURCE_GLOB"
subst __HUMAN_DOC_LANG__ "$HUMAN_DOC_LANG"
subst __CI_FILE__ "$CI_FILE"

echo "template initialised: $PROJECT_NAME (prefix $PREFIX, app apps/$APP)"
echo "next: $PACKAGE_MANAGER install && $PACKAGE_MANAGER test:harness, then delete this script."
