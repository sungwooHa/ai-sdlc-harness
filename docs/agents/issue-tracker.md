# Issue tracker configuration

Consumed by the project adapters `__PREFIX__-intent`, `__PREFIX__-spec`, `__PREFIX__-tickets`,
`__PREFIX__-implement` and, through them, the vendored `to-spec`, `to-tickets`, `implement`, and
`review-since` skills.

## Tracker

**None.** This project uses no external issue tracker in the artifact chain. The change identifier
is the change folder `docs/changes/<YYMMDD_NN>-<work-slug>/`; the local, uncommitted working documents and preserved agreement revisions are the
planning/review references. History is delivered through the PR body and attachments.

- Folder id: `<YYMMDD>` is the date the change starts (2-digit year, month, day) and `<NN>` is that
  day's sequence starting at `00` — `260910_00-<work-slug>`, then `260910_01-...`.
  `/__PREFIX__-intent` assigns it by counting the existing folders with today's `YYMMDD_` prefix.
  The date and sequence stay in the local folder name.
- Work slug: the folder name without `YYMMDD_NN-` is the one shared name. The branch
  `feature/<work-slug>`, the `Plan-Ref: <work-slug>` commit trailer and the PR use it. One plan has
  one work slug; pick one that tells the change's purpose apart, and give a different change a
  different one. Example: `260910_00-admin-access/` → `feature/admin-access` → `Plan-Ref: admin-access`.
- Parts of one plan in separate worktrees share the work slug as `feature/<work-slug>/<part>`; see
  them together with `git log --glob='refs/heads/feature/<work-slug>/*'`.
- History with the dated `Plan-Ref` value (`<YYMMDD_NN>-<slug>`) stays valid.
- Commits: follow `docs/standards/COMMIT_CONVENTION.md`; no issue-id suffix.
- Tickets from `/__PREFIX__-tickets` live in the `## 티켓` section of
  `docs/changes/<YYMMDD_NN>-<work-slug>/plan.md`.

Skip every publishing step a vendored skill offers: `to-spec`'s publish-to-tracker step,
`to-tickets`' issue creation, triage labels, and the `ready-for-agent` label. Nothing leaves the
machine during planning; after implementation the developer transfers the agreement and actual
results as PR attachments for value review. See `docs/standards/AGREEMENT_REVIEW.md`.

If this project does use a tracker, replace this section with the tracker's name, the id format,
and which publish steps the adapters should run.

## Domain docs

Single context. Glossary lives in `CONTEXT.md` at the repo root (created on first use of
`grill-with-docs`).
