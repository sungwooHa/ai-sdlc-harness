#!/usr/bin/env bash
# Artifact-chain gate: a change that spans more than one app, or touches a shared
# contract in packages/*, must carry a plan. The plan itself lives on the PR (body), not in
# the repo — the evidence a PR carries is a `Plan-Ref: <YYMMDD_NN>-<slug>` commit trailer on at
# least one commit in the range (artifact_chain.plan_gate in .agents/harness.yaml).
#
# Warn-first (exit 0) so the rule can earn trust; PLAN_GATE=enforce turns a missing trailer
# into exit 1. REVIEW.md's own rule applies: promote to enforce after the same gap has been
# caught three times.
#
# Usage: check-plan-artifact.sh [<base-ref>]     default base: origin/__INTEGRATION_BRANCH__
#        PLAN_GATE=enforce|warn|off
set -euo pipefail
[ "${PLAN_GATE:-warn}" = "off" ] && exit 0

# CI may export the PR destination branch here; otherwise pass it as $1.
BASE="${1:-${PR_DESTINATION_BRANCH:+origin/$PR_DESTINATION_BRANCH}}"
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
plan_refs="$(git log --format='%(trailers:key=Plan-Ref,valueonly)' "$BASE"..HEAD | sed '/^$/d' | sort -u)"
has_plan="$(printf '%s\n' "$plan_refs" | sed '/^$/d' | wc -l | tr -d ' ')"

if { [ "$app_count" -ge 2 ] || [ "$touches_packages" -gt 0 ]; } && [ "$has_plan" -eq 0 ]; then
  reason="$([ "$app_count" -ge 2 ] && echo "apps: $(printf '%s ' $apps)" || echo "packages/* contract touched")"
  echo "check-plan-artifact: this change spans ${reason}but no commit carries a Plan-Ref trailer."
  echo "  AGENTS.md: 'Plan | change touches several files | plan mode; commits carry Plan-Ref: <YYMMDD_NN>-<slug>; the plan is pasted into the PR body'."
  echo "  Add the trailer to a commit (git commit --trailer 'Plan-Ref: <YYMMDD_NN>-<slug>') or explain in the PR why no plan is needed."
  if [ "${PLAN_GATE:-warn}" = "enforce" ]; then
    exit 1
  fi
  echo "  (warn mode — set PLAN_GATE=enforce to block)"
  exit 0
fi
[ "$has_plan" -gt 0 ] && echo "check-plan-artifact: ok (Plan-Ref: $(printf '%s ' $plan_refs))" || echo "check-plan-artifact: ok"
