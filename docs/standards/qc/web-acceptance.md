# Web acceptance through the agent browser

Apply this contract to web changes with user-visible effects, including validation, persistence,
API responses, shared helpers and state transitions outside UI file globs. Use it for explicit
web verification too. Documentation, test-only and infrastructure work without visible effects
keep their ordinary checks. Native-only behavior uses the project's device/emulator workflow.

## Assign and prepare

The main agent owns acceptance through delivery. Before coding, identify the affected user
outcome, normal entry point, observable finish and relevant failure/recovery paths. Reuse the
project's design and QC workflow. For a reported browser defect, reproduce the original steps
in the browser when possible; record an unavailable reproduction explicitly.

After implementation and code checks, assign browser acceptance as a distinct execution step.
Use a fresh verifier for a new/reworked journey or repeated UX failures when delegation and
browser tools are available. Hand over the outcome and acceptance criteria, final source/build
identity and URL, authorized synthetic data/account, relevant connected paths and environment
instructions. Let the verifier choose additional cases from those inputs. An implementer's
claim that tests passed is supporting evidence, not the verifier's conclusion.

Assign execution only to an agent with the required browser capabilities. A code reviewer whose
tools are limited to files/shell cannot establish interactive acceptance. If delegation cannot
operate the browser, the main agent performs the browser step and labels any independent
evidence review separately. Use the host's supported agent-browser tools; no named vendor,
personal skill, new installation, approval bypass or extra data permission is assumed.

## Execute the journey

1. Record the actual URL, final source/build, data source and persistence boundary. Resolve
   available local/test setup within authorization; use project runtime registration/cleanup.
   Backend-backed E2E uses the intended test backend. A fixture, mocked response or in-memory
   demo establishes only that boundary; it cannot establish the connected product outcome.
2. Operate visible product controls from the normal entry point through the applicable finish.
   For writes, enter values, submit, observe completion, leave/re-enter or reload, then freshly
   read the persisted result; verify records/values/counts beyond the success toast. For read-only
   outcomes, verify the affected content/state after navigation or reload without inventing writes.
   APIs/CLIs may prepare fixtures or supplement assertions; replacing product UI actions with
   them does not exercise the user journey.
3. Exercise applicable boundaries: invalid/boundary input, repeated actions, partial entry,
   cancel/back/close, interrupted or failed saves and retry/recovery. Choose from the change's
   failure modes and actual API guarantees. Use safe authorized failure injection when needed;
   an unavailable failure path remains unverified. Inspect shared create/edit/resume callers
   for the same cause after feedback, without expanding into unrelated product areas.
4. Run the critical journey in mobile, tablet web and monitor viewports. Use project target sizes
   or defaults of 390 × 844, 1024 × 768 and 1440 × 900 CSS pixels. Confirm actual page dimensions;
   inspect decisive rendered states for clipping, overlays, focus, Korean wrapping and controls.
   Add affected orientations, keyboard/IME or zoom cases when relevant.
5. Record the actual input path separately from viewport size. Mouse at phone size is mouse
   evidence. Touch gestures require a touch-capable browser surface; unavailable touch remains
   unverified. Keep physical-device touch evidence distinct from browser touch emulation.
6. Preserve compact raw evidence per journey/environment: steps, expected/observed result,
   viewport/input, data boundary, fresh-read/recovery result and inspected decisive screenshots.
   Capture relevant console/network failures through supported tools. Restore only task-owned
   test mutations using supported recovery, verify restoration and clean up task-owned runtimes.

## Return to implementation or finish

When implementation is authorized, return a reproduced failure with its steps and evidence to
implementation. Fix confirmed in-scope defects, rerun the failing case and affected connected
journeys/environments on the final candidate. Verification-only work reports failures without
editing. Evidence predating a relevant code/build change does not close that outcome.

Report executed failures as failed and missing/unrun requirements as unverified. Continue
independent checks and resolve available setup; request only genuinely required intervention.
The browser step passes only when the affected critical journeys, all three viewports and
applicable input/persistence/recovery paths pass on the final candidate. Code tests, builds,
screenshots alone and an evidence-format checker cannot grant that result. Keep static review,
browser interaction, connected E2E and physical-device coverage separate in delivery. State
the tested scope and remaining uncertainty; passing scoped E2E is not proof of a defect-free product.
