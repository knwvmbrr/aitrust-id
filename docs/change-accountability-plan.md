# Change accountability implementation plan

Recorded 2026-10-09. Owner: Codex. Scope: F-150, WP-RELEASE, WP-SITE, F-139.

The existing human changelog and execution reports preserve prior work, but no
check requires a new entry for a new change. Scope progress also lacks links to
recent published presentation work. Claude's draft policy supplies a useful
changed/evidence/limits shape; its working-tree-only check misses clean CI and
accepts unrelated passing reports as release validation.

## Architecture

Keep CHANGELOG.md as the human record. Add append-only structured events under
runs/changes/, with UTC timestamp, actual contributor, existing scope IDs,
explicit changed file hashes, executed check or hashed evidence, and limits.
The writer records the change and human entry together; failures write neither.
The verifier checks new events against the actual Git range in CI, or against
working-tree changes locally. Old entries cannot cover new edits. Historical
entries remain unchanged; retrospective records say when they were recorded.

Require this check before supported build/deploy commands and in a dedicated CI
job with full Git history. A source checksum changed after recording requires a
new event. Operational evidence updates are changes too. Changelog records do
not grant tag release acceptance; independent-validation claims are rejected by
this engineering log until a separate release-evidence contract is implemented.

Reconcile current shipped UI changes into existing scope records with evidence
and contributor attribution, preserving all IDs and acceptance percentages.
Apply the approved PS introduction and center only its short introduction and
availability, leaving explanations and commands left aligned. Publish a readable
changelog download through existing site reference/navigation routes.

## Risks and verification

Concurrent unpublished work remains separate and preserved; no blanket staging.
No private input, credentials or command output enters the public change records.
Record checks by argv and exit code, not shell interpolation. Detect stale entries,
missing evidence, invalid scope, malformed owners/timestamps, failed gates,
changed evidence, deleted files, clean-CI omissions and transaction collisions.
Build the site and exercise PS results, light/dark/reflow, public references and
existing scope checks. Public deployment must match the verified source commit;
record public observations separately. Human usability and independent detector
accuracy remain open and are never inferred from engineering test passes.
