@AGENTS.md

## Claude Code

- Plan-first applies even to a one-line fix: call EnterPlanMode before the first repo edit instead of
  waiting for the hook to refuse it.
- When presenting a plan with ExitPlanMode, tell the human to pick "auto-accept edits", so
  implementer subagents edit without a prompt per file.
- Agent calls run in the background: never predict their results; synthesize only after the
  completion notifications arrive.
