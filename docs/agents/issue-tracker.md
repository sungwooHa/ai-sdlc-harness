# Issue tracker configuration

Consumed by the project adapters `__PREFIX__-intent`, `__PREFIX__-spec`, `__PREFIX__-tickets`,
`__PREFIX__-implement` and, through them, the vendored `to-spec`, `to-tickets`, `implement`, and
`review-since` skills.

## Tracker

**None.** This project uses no external issue tracker in the artifact chain. The change identifier
is the change folder `docs/changes/<YYMMDD_NN>-<slug>/`; the local, uncommitted working documents and preserved agreement revisions are the
planning/review references. History is delivered through the PR body and attachments.

- Folder id: `<YYMMDD>` is the date the change starts (2-digit year, month, day) and `<NN>` is that
  day's sequence starting at `00` — `260910_00-<slug>`, then `260910_01-...`.
  `/__PREFIX__-intent` assigns it by counting the existing folders with today's `YYMMDD_` prefix.
- The id appears in the `Plan-Ref` commit trailer; branches use `feature/<slug>`.
- Commits: `__COMMIT_FORMAT__` — no issue suffix.
- Tickets from `/__PREFIX__-tickets` live in the `## 티켓` section of
  `docs/changes/<YYMMDD_NN>-<slug>/plan.md`.

Skip every publishing step a vendored skill offers: `to-spec`'s publish-to-tracker step,
`to-tickets`' issue creation, triage labels, and the `ready-for-agent` label. Nothing leaves the
machine during planning; after implementation the developer transfers the agreement and actual
results as PR attachments for value review. See `docs/standards/AGREEMENT_REVIEW.md`.

If this project does use a tracker, replace this section with the tracker's name, the id format,
and which publish steps the adapters should run.

## Domain docs

Single context. Glossary lives in `CONTEXT.md` at the repo root (created on first use of
`grill-with-docs`).
