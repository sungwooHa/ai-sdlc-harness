# apps/__APP__ — Agent Rules

<!-- Per-app layer: loaded when work happens under this directory. Keep it under 80 lines.
     Copy this directory per app, rename it, and delete every line you have not verified. -->

Stack: <language / framework / build tool>. Entry point: `<path>`.

## Layout

| Path | Role |
|---|---|
| `src/<...>` | |
| `tests/<...>` | |

## Commands

```bash
<install>                  # dependency install, if it differs from the repo root
<typecheck>
<test one file>            # the narrow run to use while iterating
<test all>                 # run once before commit
```

Any environment quirk that silently produces wrong results (a virtualenv that must be used, a
port that must be free, a generated file that must be rebuilt first) goes here as one line.

## Rules

- <one rule per line: only the rules an agent would otherwise break>
- <name the seam tests belong at, and where existing tests live>

## Where the detail lives

- Architecture / style / testing standards: `docs/standards/<domain>/`.
