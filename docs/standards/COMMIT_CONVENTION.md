# Commit message convention

A guide: no hook checks it; the PR reviewer does (`REVIEW.md`, compliance pass). `AGENTS.md` and
the `git-commit` skill point here.

## First line

```
<type>: [<Module>] <summary>
```

For example `feat: [Auth] <summary>`, or `docs: <summary>` when no single module applies.

- `<type>`: one of the types below, lowercase.
- `[<Module>]`: the area the change touches. Leave it out, with the space after it, when the change
  spans several areas or none.
- `<summary>`: what changed, in __HUMAN_DOC_LANG__, clear and short (at most 72 characters).

| Type | Use for |
|---|---|
| `feat` | New behaviour |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Formatting with no behaviour change |
| `refactor` | Code change with no behaviour change |
| `test` | Tests only |
| `chore` | Build, packages, configuration |

First lines git writes itself (merge, revert, `fixup!`, `squash!`) stay as git writes them.

## Body

The first line alone is the default. Add a body only when the reason is not obvious from the first
line: at most three lines, saying why. Implementation notes, test logs and file lists go to the PR,
not the commit.

## Trailers

None are required. Add no `Co-Authored-By`, `Signed-off-by` or tool footers: the agent is the
default author, so marking it is redundant (`PLAYBOOK_MAP.md` C1.1, Deviation).
`.claude/settings.json` `attribution` is empty so Claude Code adds none itself.

## Writing the message as an agent

Agent shells take one command without newlines, so pass each paragraph as its own `-m`:

```sh
git commit -m "<first line>" -m "<why, at most three lines>"
```

One logical change per commit; split unrelated work.
