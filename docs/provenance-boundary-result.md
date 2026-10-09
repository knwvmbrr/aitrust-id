# Provenance boundary and clean-checkout correction

Recorded 2026-10-09T21:07:46.641291+00:00 by Codex. Initial bridge draft: Claude; corrected code,
contracts, tests and review: Codex. Scope remains F-025/F-083/T-PA/T-FA/F-116/F-150.

The bridge is runnable research code. Credential validity alone is neutral UNK.
Explicit supplied claims of AI generation followed by human rework, or generation
without human intervention, can support PA/FA **research candidates** only when
subject identifiers, typed credential observations and claim bindings match.
Failed, unbound or unchecked evidence cannot promote a candidate. A human claim
is not a human-authenticity clearance. Conflicts retain all sources and choose
no candidate; mixed subjects and inconsistent evidence references are rejected.
Duplicate evidence adds neither standing nor independent validation. All outputs
state production_assertion=false and independent_release_validated=false.
Actual cryptography, media reading, capture adapters and release are not supplied.

`python3 scripts/demo-tag-bridge.py` runs five synthetic cases without network,
commands, a model or raw user text. `tests/test_tag_bridge.py` protects the seam;
the full reviewed suite passes 390 tests, including 89 new bridge/checkout cases.
No live-tag allowlist, evaluator method or extension behavior was changed.

The earlier device verifier read an ignored generated runtime manifest. A fresh
checkout failed with FileNotFoundError; the installed-workspace pass did not
establish the download path. The verifier now uses a committed engineering
reference. A minimal clean checkout passes without site assets; a deliberately
altered reference fails. Four actual Python builders still reproduce identical
bundle/manifest bytes. No future-builder guarantee or hosted-CI pass is claimed.

All 202 requirements, 39 packages and 117 subtasks remain. Scope timestamps,
evidence and partial implementation credit are updated; broad tag acceptance
percentages remain unchanged. Real provenance adapters, accepted claim-specific
policy, human usability and independent validation still have owners/next fixes.
Original overwritten drafts are preserved privately; unsupported draft claims
about a sanctioned production interface were not published.

Changelog events and runs preserve executed evidence. Public site/source
publication observations are recorded separately below.

## Published verification

Source 403a317851a37c21d4e9e724911790eb6d230933 is pushed and deployed at
https://aitrustid.com and https://37967789.aitrust-id.pages.dev. All 134
site files match across the domain, www and deployment origin (402 checks);
declared security headers match and no injected analytics was observed. Public
PS result/escaping/axe checks pass, as do all 20 panels, eight footer routes and
202 preserved scope records. The site's changelog download matches the deployed
source snapshot.

An anonymous commit-pinned ZIP was downloaded. All 612 files match committed
source. Without a generated runtime manifest or prior site build, the device
verifier and synthetic bridge demo run; 89 focused tests pass using the existing
verification environment. This is a tested downloadable developer path, not
independent outside-user install acceptance. No local Docker was started.

The source's hosted CI starts no steps because of the account billing lock;
the actual run and annotation are preserved in
runs/2026-10-09-provenance-boundary-hosted-ci.json. Local checks are not a hosted
CI pass. These post-publication observations remain in Git/state; they are not
retroactively included in the earlier deployment's changelog download.
