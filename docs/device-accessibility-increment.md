# Device build and accessibility increment

Plan recorded 2026-10-09. Implementation/review owner: Codex. Initial device and
fixture drafts: Claude. Scope: T-PS, F-116, F-150, F-055, F-092, F-093, F-094,
F-139; no new tag or detector claim.

## Architecture before changes

Normalize only AST-identified tuple assignment/iteration targets, not arbitrary
source text. Assert AST identity and idempotence. Preserve the current PS source
hash and projected bundle bytes; check actual installed Python builder versions,
not a promise about all future interpreters. Make bundle and manifest writes
atomic and unchanged-content writes a no-op. Keep builder provenance outside the
runtime manifest so artifacts can be reproduced across builder versions. An
undeletable stale public bundle is a build failure, not a warning that publishes
unreferenced obsolete methods. Unit tests use isolated temporary output, including
fresh-checkout behavior, so they don't depend on an earlier site build.

Review the accessibility fixture as a fixture. Its .pv selectors and intermediate
verdict states do not describe the actual site. Add targeted checks to the real
catalogue, PS checker and independent footer workflows for keyboard operation,
text spacing, target size, focus obstruction, forced colors and reduced motion.
Use deliberate injected defects to show the checks can fail. Correct any actual
site defects with small changes and retain the existing design and tag scope.
Do not turn these automated observations into a complete VPAT/ACR, human
screen-reader approval or procurement eligibility claim.

## Risks and exit evidence

Semantic code changes fail AST comparison. Incomplete/stale artifact cleanup
blocks build before publication. Run builder matrix plus unit and source-parity
checks; run unchanged PS method on Chromium and WebKit development examples.
Keep private input off all reports. Accessibility overrides are test-only; actual
production CSP is still exercised by the existing site check. Cite W3C's official
text-spacing, target-size and focus-obstruction criteria; record precisely which
surfaces, modes and behaviors were tested. Preserve all scope IDs and broad
acceptance percentages unless full named acceptance is independently complete.
Write attributed changelog events before build/commit, then publish the reviewed
source/build and record public observations separately. Unrelated contributor
drafts remain preserved outside this change.
