# Mobile scope payload plan — 2026-10-11

Codex will keep the complete 202-record scope and every exported catalogue field,
while removing the 591 KB source scope JSON from the initial interactive bundle.
The existing tag catalogue, PS checker, performance summaries and policies keep
working without loading that scope. Opening full details or the Scope workflow
loads the same build-bound JSON through a hashed Vite asset. The initial loader
contains its expected SHA-256, byte length and ordered IDs; it rejects an altered,
truncated, excessive or different-release file before exposing scope or downloads.

The architecture uses one shared async loader with a fulfilled/pending cache and
explicit error/retry state, an eight-second request timeout and bounded body
reading. Asset fetch can retry without a cached failed ES module. Full details mount only when their native disclosure
opens. The existing Radix dialog focus controls and native details keyboard
behavior remain. The Scope workflow consumes the same complete data. Catalogue
exports still carry the full selected records, including their audit and outcome.
No truncated substitute or live unversioned endpoint is used.

User protection: no user text, account or result is sent by this loader. Failure
must appear next to the action with retry and a static reference link; it cannot
look like empty scope or missing evidence. Failed loads are retryable and closing
or switching a tag cannot apply a late update to an unmounted component.

Risks to verify: accidental eager imports, stale/offline chunk mixing, empty or
incomplete exports, lost focus, fetch failure/race behavior and phone overflow.
The offline worker already freezes all generated assets under one content-bound
release; verify the new chunk is in that allowlist and works without network.

Acceptance: measured built initial JavaScript decreases; zero scope-record or
export-field loss; all tag and footer workflows work; load failure/retry and
close/reopen work; keyboard and automated accessibility checks pass. No physical
phone or independent accuracy credit is granted by emulated browser testing.
Existing F-142/N-012 human/device gates and F-113 latency scope remain open.

Verified outcome: initial JavaScript is 539,456 bytes versus the measured
994,375-byte baseline (45.75% reduction). Chromium and WebKit at 390 CSS pixels
exercise deferred loading, full selected-record export and both matching scope
records. Six failed-load controls refuse bad data and recover with complete
exports; an installed offline release loads and exports the frozen full scope.
All 20 catalogue modals, eight footer workflows and 62 automated accessibility
surfaces pass. Existing full requirement gates remain open. The built-browser
controls are integrated into the normal website revalidation/CI pipeline.
