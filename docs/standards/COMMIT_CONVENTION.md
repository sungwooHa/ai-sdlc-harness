# Commit message convention

The single source for commit messages. `AGENTS.md` and the `git-commit` skill point here;
`.husky/commit-msg` checks the first line and the trailers with the values in
`.agents/harness.yaml` `commit_message`.

## First line

```
__COMMIT_FORMAT__
```

- `{type}`: one of the types below, lowercase.
- A field written in brackets or parentheses (a module or scope) is optional. Leave it out, with
  the space after it, when the change spans several areas or none.
- The summary says what changed, in __HUMAN_DOC_LANG__, clear and short (50–72 characters).

| Type | Use for |
|---|---|
| `feat` | New behaviour |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Formatting with no behaviour change |
| `refactor` | Code change with no behaviour change |
| `test` | Tests only |
| `chore` | Build, packages, configuration |

`commit_message.types` in the manifest is the list the hook checks; change both together.

## Body

The first line alone is the default. Add a body only when the reason is not obvious from the
first line: at most three lines, saying why. Implementation notes, test logs and file lists go to
the PR description, not the commit.

## Trailers

`Plan-Ref: <YYMMDD_NN>-<slug>` is the only trailer. It links commits to the local change folder;
a PR that touches more than one app or any shared contract needs it on at least one commit
(`check:plan`). No other trailer: no `Co-Authored-By`, `Signed-off-by` or tool footers.
The hook refuses them while `commit_message.forbid_other_trailers` is true (the default), and
`.claude/settings.json` `attribution` keeps Claude Code from adding its own.

## Writing the message as an agent

Agent shells take one direct command without newlines, so pass each paragraph as its own `-m`:

```sh
git commit -m "<first line>" -m "<why, at most three lines>" -m "Plan-Ref: <YYMMDD_NN>-<slug>"
```

One logical change per commit; split unrelated work.

## What the hook checks

`.husky/commit-msg` runs `scripts/commit-msg-gate.py`:

- The first line against the format above. `{type}` is one of `commit_message.types`, any other
  field is nonempty text. Skipped while the format is still the template placeholder.
- First lines git writes itself pass: `Merge`, `Revert "`, `fixup!`, `squash!`.
- Trailers as git reads them (the last paragraph of `Key: value` lines), on every commit.

`git commit --no-verify` skips it. Use it only in an emergency and say so in the PR; agents
cannot run it.
