# Change accountability — implementation result

Recorded 2026-10-09 by Codex. F-150 / WP-RELEASE / WP-SITE.

## What was already documented

The published PS result changes, performance panels and approachable modals were
already in CHANGELOG.md, state.json, architecture notes and runs/ execution/public
verification records. The immediately preceding sentence and centering suggestion
was chat-only: it had not been implemented or logged. This increment applies it.

## What this closes

The human log now has matching structured UTC-attributed events with existing
scope IDs, changed-file hashes and executed/hashed evidence. Missing or stale
entries fail the supported build/deploy paths. Full-history CI checks actual
committed changes; the Git hook checks exactly the staged index. It cannot accept
an unstaged entry for a staged edit. Writer failures create neither a human entry
nor event; exclusive locking and unique IDs prevent concurrent overwrite.

Recent published UI/result/performance changes are linked to the acceptance
ledger and backfilled into change events with their actual source commits.
Retrospective timestamps mean recorded now, not reconstructed historical finish
times. All 202 requirement IDs, 39 packages and 117 subtasks remain. Fourteen
requirements are complete and 188 open; every percentage is unchanged. Evidence
and attribution have changed, not acceptance.

The approved PS introduction is centered with its short availability statement.
Explanations and matched command text stay left aligned. Finding next steps start
with “Review this command before using it.” The existing public reference area
provides a real Changelog download; Git carries subsequent operational entries.
The deployed copy is explicitly a deployment snapshot.

## Review of the draft and remaining work

Claude's changed/evidence/limits format is retained with credit. Its draft gate
was not adequate: an existing entry could cover a new edit, CI did not inspect a
commit range, any unrelated pass could satisfy a release-validation claim, and
contributor default/overwriting weakened attribution. These are replaced by
executable change and evidence checks. Independent-release claims are rejected
by this engineering log rather than accepted from an unrelated passing test.

Other uncommitted contributor work (device-build changes, accessibility fixture
harness, tag bridge and research notes) is outside this increment. Original
shared-file drafts are preserved privately before reconciliation; they are not
reported as shipped. In particular, F-025 is a C2PA manifest signal, not the PS
bundle-build requirement; the draft's bundle attribution to that ID is excluded.
No unpublished research references are introduced into the public progress data.

PS is the one website checker, with 86 development examples and an unmet
independent release gate. Next: freeze the independent review sample, obtain the
two blind reviewers' labels, adjudicate disagreement and run the declared gate.
PII_REDACTED remains a local-service preview with its own coverage/acceptance work.
The other 12 personal tag records and six organization offerings keep their own
jobs and gates; their presence is not runtime implementation. Actual phones,
human screen-reader and outside-user setup/removal checks remain required. The
public research intake and self-hosted community applications are not activated.

## Verification boundaries

The first PS copy assertion failed because it used startsWith against a paragraph
that also contains the label “What to do next:”. The implementation text was
correct; the assertion now checks the text after allowing the label. This failure
and correction are recorded rather than described as a product regression.

The first real pre-commit attempt caught a relative GIT_INDEX_FILE path inherited
from Git; after exporting the staged snapshot the path resolved against the
temporary directory, showing incorrect changes. The index path is now bound
explicitly to the original repository, with a hook-environment regression test.
The commit was blocked, and nothing from that attempt was published.

The change-record tests exercise real temporary Git histories, deleted files,
clean CI, partial staging, evidence changes, failed writes and lock contention.
Automated site checks verify the introduction, downloadable changelog, actual PS
results, escaping and accessibility. Public deployment and observations are
recorded separately under runs/2026-10-09-changelog-*.json; current publication
status and source are in state.json. No engineering check is independent
accuracy or human usability acceptance. Existing bundle-size and dependency
warnings remain visible in build/test output.

## Published observations

Source ec9ac5e6aab6c583973e397086dcd10aab349567 is deployed at
https://aitrustid.com, https://www.aitrustid.com and
https://0de8b6d7.aitrust-id.pages.dev. All 133 artifacts match the verified build
on all three origins (399 hash checks). Public PS and site checks pass, including
the actual changelog download, intro alignment, six result cases, all 20 tag
panels, eight footer routes, 320px/200% reflow and zero automated axe violations.
The final Python suite passes 285 tests, including 24 change-record tests.

The actual Git hook is installed in the owner checkout and passed the commit.
The new source range also passes the committed-range verifier locally. GitHub
Actions run 37964819898 starts no job steps: its annotation says the account is
locked due to a billing issue. Hosted CI is configured but not executed; resolving
that account lock is an owner action. Local checks are not described as hosted CI.

The site's changelog download reflects the deployed source snapshot. Subsequent
publication/CI observations are appended to the Git changelog and state without
pretending that they were included in the earlier deployed artifact.
