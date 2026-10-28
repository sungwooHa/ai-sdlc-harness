@AGENTS.md

## Claude Code

- Plan-first applies even to a one-line fix: call EnterPlanMode before the first repo edit instead of
  waiting for the hook to refuse it.
- When presenting a plan with ExitPlanMode, explain the approval and editing options the current
  dialog offers; the human chooses the editing consent. Reuse granted consent within its scope.
- Agent calls run in the background: never predict their results; synthesize only after the
  completion notifications arrive.
