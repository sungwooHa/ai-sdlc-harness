# User journey review

Apply to the affected user-visible behavior before implementation and again before delivery.
Keep the selected cases in the task's existing plan or conversation; this adds no document,
approval round or product-wide audit. The project owns domain policy and its design system.

## Frame the finish

- State the user's task, known volume/device and observable finish. Trace the normal entry
  through completion and a natural stopping point during repeated work. Inspect the current
  rendered product and shared controls; use its theme and action semantics in mockups too.
  A mockup should exercise the decision under review without implying unimplemented persistence.
- Read existing code, APIs and configured defaults. Separate supplied facts from assumptions;
  warnings and validation need the relevant domain facts. Preserve an established contract when
  policy is unclear; ask only about an unresolved outcome or material contract change.
- Give actions a concrete effect and scope: navigate, retain a draft, continue another entry,
  submit the accumulated set or discard. Distinguish draft accumulation from persisted success.
  Add a step or destructive control only for a decision the user needs to make; an internal
  list or state object does not require its own management screen.

## Select applicable boundaries

For each relevant row, identify the action, values to preserve and resulting state. A narrow
fix covers its affected cases and connected callers; a new journey covers its start, finish
and applicable interruption/recovery. Skip unrelated rows and resolve routine controls locally.

| Boundary | What to inspect and exercise |
|---|---|
| One item and repeated items | Can the user finish one item, continue several and stop without inventing another item? Distinguish an untouched next form from a partially entered one; preserve or explicitly resolve unsaved input. |
| Input mechanics | Check this field's length, character set, input mode, leading zeros, insertion/selection, paste and applicable IME composition. Prevent avoidable keystroke errors without silently corrupting legitimate stored/pasted values. Numeric-only or fixed-length constraints belong only to fields whose contracts require them. |
| Conditional fields | Does a selection reveal the correctly labelled independent field? Preserve other fields and values across selection changes, editing and draft restoration. |
| Validation and guidance | Does each warning/block have the required facts and use the actual identity/domain rather than a display fragment? Keep actionable errors; avoid redundant guidance for constraints already enforced by the control. |
| Edit, back, close and resume | Can the user revise, leave, intentionally discard and resume under the existing draft contract? Preserve intended values and coherent focus/scroll; distinguish leaving a view from discarding work. |
| Submit and recover | Is the submitted set/count correct? Distinguish pending, failed, unknown and completed outcomes. Retry and duplicate-submission behavior must follow actual API guarantees, including interrupted responses. |
| Complete and re-enter | Can the user recognize completion, leave and freshly read persisted results? Keep useful next actions and recovery for unfinished results; re-evaluate draft controls after confirmed persistence. |

## Follow feedback to its cause

Reproduce the reported path and trace its shared component or state rule. Inspect connected
create/edit/resume/complete callers for the same cause, then repair authorized instances together.
Keep a focused regression for the demonstrated boundary. A contract conflict returns to its
owner; it does not authorize a policy change or unrelated redesign.

## Hand off and verify

Give the executor the outcome, selected cases, current controls/states and final source/build.
For a new/reworked journey or recurring UX feedback, use an independent journey reviewer when
available to inspect whether the user can finish and recover without lost values or invented
requirements. A code-only or evidence-only review does not establish actual interaction.

Execute web cases under [web acceptance](../../../../docs/standards/qc/web-acceptance.md), which
owns browser assignment, persistence checks, viewports/input coverage, evidence and cleanup.
Native-only changes follow the project's device/emulator procedure. Record failed behavior and
missing execution separately; a passing build or screenshot does not resolve either.
