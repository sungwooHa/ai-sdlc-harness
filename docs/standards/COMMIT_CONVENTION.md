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
- The summary says what changed, in __HUMAN_DOC_LANG__, clear and short (at most 72 characters).

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

`Plan-Ref: <work-slug>` is the only trailer, the change folder name without `YYMMDD_NN-` (the
branch and the PR share it; the date stays local). A plan split into parts uses
`feature/<work-slug>/<part>` branches, and every part's commits carry the same `Plan-Ref: <work-slug>`,
not a per-part value. It links commits to the local change folder;
a PR that touches more than one app or any shared contract needs it on at least one commit
(`check:plan`). No other trailer: no `Co-Authored-By`, `Signed-off-by` or tool footers.
The hook refuses them while `commit_message.forbid_other_trailers` is true (the default), and
`.claude/settings.json` `attribution` keeps Claude Code from adding its own. It also checks each
Plan-Ref value: a work slug (`^[a-z0-9]+(-[a-z0-9]+)*$`) or the older dated folder name
(`^[0-9]{6}_[0-9]{2}-[a-z0-9-]+$`). A commit without Plan-Ref passes; one commit cannot tell what the PR covers.

## Writing the message as an agent

Agent shells take one direct command without newlines, so pass each paragraph as its own `-m`:

```sh
git commit -m "<first line>" -m "<why, at most three lines>" -m "Plan-Ref: <work-slug>"
```

One logical change per commit; split unrelated work.

## What the hook checks

`.husky/commit-msg` runs `scripts/commit-msg-gate.py`:

- The first line against the format above. `{type}` is one of `commit_message.types`, any other
  field is nonempty text. A field in brackets or parentheses may be left out; left out, the summary
  cannot start with that bracket (`feat: [x]` is a module with no summary). Skipped while the format
  is still the template placeholder.
- First lines git writes itself pass: `Merge branch`, `Merge pull request`,
  `Merge remote-tracking branch`, `Merge tag`, `Merge commit`, `Revert "`, `Reapply "`, `fixup!`,
  `squash!`, `amend!`. Any other first line follows the format.
- A first line that starts with `#` is refused: with `-m`/`-F` git keeps it as the subject, and the
  hook cannot tell that from an editor comment.
- Trailers as git reads them (the last paragraph of `Key: value` lines), on every commit.
  Reading stops only at git's exact scissors line (`# ------------------------ >8 ------------------------`
  at the start or after a line feed, ending in one); a look-alike (other dashes, CRLF, a trailing
  blank) is a comment line and the lines below it are read. A `---` line is text, as in `git log`.
  When that paragraph is prose or a link (`Why: ...`, `Follow-up: ...`, a bare URL), add a sentence
  or end with Plan-Ref. An attribution trailer (a key ending in `-by`) has to be removed: a line
  that starts with `Co-Authored-By:` is refused anywhere in the stored message (the body, or below
  the scissors line, which `-m`/`-F` keep) unless `allowed_trailers` lists it.
  A mid-line mention, a comment line and a `--verbose` diff pass.
- Each `Plan-Ref` trailer git reads (key in any case) has a work-slug value or the older dated
  folder name, also while the format is still the template placeholder. Whether the PR carries one
  at all is for the PR stage (`check:plan`, the PR body gate).

`git commit --no-verify` (or `-n`) skips it. Use it only in an emergency and say so in the PR.
What stops an agent from skipping it, by layer:

- The agreement gate (`scripts/agreement-gate.py`, PreToolUse) refuses `git commit` with `-n` as an
  option, alone or in a short cluster (`-nm`, `-anm`), `--no-verify` or an abbreviation of it, any
  other `--no-*` option except `--no-edit`, an environment prefix (`HUSKY=0 git commit`) or git
  options before the subcommand (`-c`, `-C`, `--git-dir`, ...). It reads every option as git does
  from a table of all `git commit -h` options (its test fails when the installed git lists one the
  table lacks): option values are values (`-m "- note"`, `--trailer "Plan-Ref: <slug>"`, and
  `git commit --amend --no-edit` pass), and abbreviated (`--amen`) or unknown options are refused,
  so no value option can hide a `-n` from it.
- `.claude/settings.json` `permissions.deny` and `.codex/rules/harness.rules` repeat the common
  spellings for when the hook does not run. They match command text, so they miss others
  (`docs/standards/AGREEMENT_REVIEW.md`, "Second fence").
- A human terminal is outside both.
