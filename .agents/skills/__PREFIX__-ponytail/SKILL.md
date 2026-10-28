---
name: __PREFIX__-ponytail
description: Apply Ponytail's reuse-first simplification to coding, refactoring and dependency choices within the approved plan, keeping this harness's artifacts and verification. Use when the user asks for ponytail, 포니테일, less code or less over-engineering; also when the implement adapter needs a simpler design.
---

Read the available spec and approved plan (conversation/native plan for a routine change) and
affected code, then read `.agents/skills/ponytail/SKILL.md` and
follow it. Use the user's requested lite/full/ultra level; otherwise use its full default. Apply
these project overrides:

- Simplify implementation within the plan's outcomes. Reuse code, standard-library or native
  features before adding abstractions or dependencies. Deliver the full requested feature; a
  material scope change goes back to the user as a new plan before implementation.
- Preserve the artifacts required by `docs/changes/README.md`, ADRs when needed, accessibility,
  security and required checks despite the reference's code-first/three-line output preference.
  A routine change uses its approved conversation/native plan and brief report; it does not
  create a change folder or missing intent/spec/plan/pr.md.
- Follow the repo's existing test tools and verification ladder. Ponytail's minimal runnable check
  supplements missing coverage; it never replaces required tests with an ad hoc self-check.
- This skill grants no write access: plan-first and protected paths still apply.
- When explaining a simplification, name its actual tradeoff. Keep ordinary updates short but
  provide the requested review and decision evidence in full. A Ponytail mode persists only as
  an agent preference; no upstream always-on or mode-tracking hooks are installed here.

If the user says stop ponytail or normal mode, stop applying this optional simplification layer;
the harness's artifact and verification requirements still apply. Leave the vendored body
unedited: record project-specific changes in this adapter and update the pinned source
intentionally.
