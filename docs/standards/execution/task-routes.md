# Task execution routes

Read the selected branch before making or assigning edits. Use the user's requested result:
correct existing behavior selects Bug fix; add/change behavior selects Feature; preserve behavior
while changing structure selects Refactoring. For a mixed request, separate its criteria and
follow their dependencies. Investigation and review-only requests finish without implementation.

Repository authorization, plan/artifact requirements, file ownership and delegation rules remain
in force. Reuse existing decisions and approved test boundaries; ordinary test selection belongs
to the agent. These routes require no additional document, approval round, skill chain or model.
Record useful notes in the repository's existing plan or conversation.

## Bug fix

1. Reproduce the reported symptom on its matching surface before changing code. Capture the
   trigger, expected/observed result and relevant source state. A browser defect uses the actual
   browser; a CLI defect uses the CLI. Resolve available setup yourself. If reproduction remains
   unavailable, preserve that gap rather than substituting a passing unit test.
2. Trace the observed failure to its cause. Test competing explanations only while needed;
   consult the existing diagnosing-bugs reference for unclear, intermittent or stubborn causes.
   A simple known cause does not need an interview or a fixed hypothesis count.
3. Give the implementer the repro, confirmed cause, affected boundary/callers and permitted
   files. Add a cheap behavioral regression when it exposes the failure; implement the smallest
   justified repair. Keep speculative hardening outside the patch.
4. Rerun the original repro and affected regressions on the final candidate. For visible web
   effects, complete the [browser acceptance branch](../qc/web-acceptance.md). Return a failed
   repro to diagnosis/implementation, with its evidence. Report an unavailable repro as unverified.
   Finish with the original symptom, cause, repair and actual failing/passing evidence.

## Feature

1. Derive observable acceptance criteria from the request and existing decisions, including
   the user's finish and applicable error/recovery paths. Inspect existing interfaces and name
   the data/state shape the change needs. Ask only about unresolved material outcome decisions.
2. Build and verify the smallest vertical slice through the real boundaries first. Reuse its
   result before spreading changes. Use the repository's delegation policy; parallelize only
   independent files/state after their shared dependencies are ready. One cohesive unit is enough.
3. Pass each implementer its criteria, owned files, relevant contracts and proof commands/surface.
   Implement and verify one meaningful boundary at a time. Apply existing TDD guidance at useful
   seams without re-asking about an already approved boundary or requiring a test for a trivial edit.
4. Integrate the slices and account for every criterion against the final candidate, including
   applicable failure, interruption and recovery. Visible web behavior enters browser acceptance;
   internal-only work keeps its CLI/service checks. Return failed criteria to the responsible
   unit and rerun the affected criteria after repair. Missing execution stays unverified.

## Refactoring

1. Name the external behavior/contracts to preserve and the structural improvement sought.
   Before moving code, run existing behavioral coverage or capture a small characterization,
   representative output replay or equivalence check where coverage is missing. Typecheck/lint
   alone does not establish a behavior baseline.
2. Give the implementer the baseline inputs/results, preserved contract, target structure and
   affected callers. Make small behavior-preserving changes; migrate references and callers
   together while retaining required compatibility. Remove only code proved unused.
3. Rerun the same baseline inputs/checks after the change and inspect affected callers. For
   larger reshapes, compare baseline and final outputs directly. Visible web paths also use
   browser acceptance. A newly discovered bug or desired behavior change is a separate criterion
   and route, not an incidental cleanup.
4. Return an equivalence failure to implementation. Finish with the structure changed, preserved
   behavior and before/after evidence. Explain the concrete readability/maintenance benefit;
   a passing build alone does not complete the refactor.

## Handoff and acceptance

Keep the selected route attached to each implementation/review handoff, together with its
baseline or criteria, permitted files, proof commands and user surface. Apply project procedures
over upstream workflow preferences. Never invent a delegation, browser action or successful check.
Inspect the delegate's actual returned status/result before accepting it. A failed startup,
permission denial or missing result is an unsuccessful attempt, not a completed independent
review. Reassign within available tools or report the gap and perform permitted checks explicitly.

The main agent accepts actual edits and executed evidence, then runs the repository's review and
delivery steps. Code checks and browser evidence are separate. On failure, return the failed
criterion/repro/equivalence check to its owning branch and rerun affected evidence on the final
candidate. Verification-only work reports findings without editing. Missing tools, approval or
environment stay explicit; continue independent authorized work and resolve available setup.
