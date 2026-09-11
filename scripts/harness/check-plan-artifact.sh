#!/usr/bin/env bash
# Artifact-chain gate: a change that spans more than one app, or touches a shared
# contract in packages/*, must carry a committed docs/changes/<YYMMDD_NN>-<slug>/plan.md.
#
# AGENTS.md promises this; nothing enforced it. Warn-first (exit 0) so the rule can
# earn trust; PLAN_GATE=enforce turns a missing plan into exit 1. REVIEW.md's own
# rule applies: promote to enforce after the same gap has been caught three times.
#
# Usage: check-plan-artifact.sh [<base-ref>]     default base: origin/__INTEGRATION_BRANCH__
#        PLAN_GATE=enforce|warn|off
set -euo pipefail
[ "${PLAN_GATE:-warn}" = "off" ] && exit 0

BASE="${1:-${BITBUCKET_PR_DESTINATION_BRANCH:+origin/$BITBUCKET_PR_DESTINATION_BRANCH}}"
BASE="${BASE:-origin/__INTEGRATION_BRANCH__}"
if ! git rev-parse --verify --quiet "$BASE" >/dev/null; then
  echo "check-plan-artifact: base '$BASE' not found; skipping"
  exit 0
fi

changed="$(git diff --name-only "$BASE"...HEAD)"
[ -n "$changed" ] || { echo "check-plan-artifact: no changes vs $BASE"; exit 0; }

apps="$(printf '%s\n' "$changed" | sed -nE 's#^apps/([^/]+)/.*#\1#p' | sort -u)"
app_count="$(printf '%s\n' "$apps" | sed '/^$/d' | wc -l | tr -d ' ')"
touches_packages="$(printf '%s\n' "$changed" | grep -cE '^packages/[^/]+/' || true)"
has_plan="$(printf '%s\n' "$changed" | grep -cE '^docs/changes/[^/]+/plan\.md$' || true)"

if { [ "$app_count" -ge 2 ] || [ "$touches_packages" -gt 0 ]; } && [ "$has_plan" -eq 0 ]; then
  reason="$([ "$app_count" -ge 2 ] && echo "apps: $(printf '%s ' $apps)" || echo "packages/* contract touched")"
  echo "check-plan-artifact: this change spans ${reason}but adds no docs/changes/<YYMMDD_NN>-<slug>/plan.md."
  echo "  AGENTS.md: 'Plan | change touches several files | plan mode, then commit the approved plan'."
  echo "  Add the approved plan (template: docs/changes/_templates/plan.md) or explain in the PR why none is needed."
  if [ "${PLAN_GATE:-warn}" = "enforce" ]; then
    exit 1
  fi
  echo "  (warn mode — set PLAN_GATE=enforce to block)"
  exit 0
fi
echo "check-plan-artifact: ok"
