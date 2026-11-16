# Package the fixed detector as a sealed module archive

**Current status:** actual Apple package validation passed for the sealed
module archive on November 15, 2026, after owner authorization of the existing
key. Both original signatures and 32 resources pass inspection. Current native
Share acceptance remains open: the latest local source passes three host
workflows and fails both Share workflows. N-013 remains 60%; this app is draft
and unreleased. The failures below are preserved history.

## Observed failures

Apple rejected both the original `method.py` resource and its renamed
`method.py.txt` candidate. The repaired candidate is present in CodeResources
with the expected SHA-256 and mode 0644, yet server validation still rejects it.
The exact server classification rule is unknown. Preserve both failures. A
local signature or different filename does not prove Apple acceptance.

The current hosted iOS 27.2 run also passed four native workflows and failed
the first Share workflow while waiting for the finish control. Its logs alone
do not establish the cause. XCTest captured attachments, but the artifact upload
omitted the result bundle. Preserve that failure and retain the existing
synthetic screenshot/hierarchy attachments on the next hosted run; do not
weaken assertions or attribute the problem to timing without evidence.

## Architecture and user protection

Package one public, fixed `method.py` member in a deterministic, uncompressed
`Assets/detector-source.zip`. The existing pinned Python runtime reads this
standard module archive. It already bundles its standard library as an archive.
Keep the original projected detector bytes and their hash unchanged; add a
separate archive hash and version the internal native asset configuration.
The native handler serves only the fixed archive route after its existing
resource hash and path checks. The bridge verifies the member name, count,
uncompressed storage, size bound and original source hash before loading it.
Delete the temporary in-memory archive after loading. User text remains data.

The archive is inspectable source packaging, not an encrypted or mutable code
channel. No network fallback, downloaded detector, signing exclusion, custom
resource rule, extra entitlement, new credential or new dependency is allowed.
The signed application must seal the archive as a resource. Apple must validate
the actual resulting package before acceptance is reported.

## Risks and verification

Risks are mismatched source/archive identities, malformed or oversized archive
members, incomplete runtime modules, startup failure and changed resource
admission. Exercise real loader behavior on valid and malformed archives, exact
source identity, deterministic packaging, tampered resources and current refusal
controls. Run the actual 137-case native detector probe and all five app/Share
workflows. Keep source hashes and failures, including hosted failures, separate.
Inspect a fresh signed archive and run Apple validation. A further rejection
requires diagnosis, never another acceptance claim from local checks alone.

The prior naming proposal remains historical in `ios-script-resource-plan.md`.
Apple's [bundle guidance](https://developer.apple.com/documentation/bundleresources/placing-content-in-a-bundle)
and [code-signature guidance](https://developer.apple.com/documentation/xcode/using-the-latest-code-signature-format)
are reference material, not evidence this iOS candidate is accepted. macOS-only
layout advice is not applied to the iOS bundle. No scope requirement reaches
100% through this packaging increment; independent and human acceptance remain.

## Share-entry diagnostic and candidate synchronization

The first module-archive workflow also passes four tests and fails the same Share
entry assertion on iOS 26.2. The retained video shows remote placeholder content
around selection; the final screenshot remains on the activity sheet. This does
not prove an extension crash or a complete root cause. Require the named activity
image to be hittable and its cell frame stable for one second before sending the
one tap. Apply the same precondition to both Share tests. The new readiness
condition has a 20-second bound; existing post-selection waits and the overall
120-second per-workflow limit stay unchanged. Preserve every result, input,
privacy and finish assertion, with no retry or swallowed failure. Verify the
complete five-workflow run again and retain the previous failure.

The readiness-aware run passes both Share workflows and fails a keyboard-opening
assertion. Its screenshot contains the fresh simulator notification "Ready for
Apple Intelligence". Preserve that failure. The test harness may dismiss only
that exact observed onboarding banner, then tap the input once after the known
interruption; it must still prove the software keyboard appears. It must not
accept a permission, opt in, change global settings or dismiss unknown alerts.
The complete test remains bounded by its existing workflow deadline. This is a
test-only interruption path, not a production change or a proven full cause.

## Current local execution

The archive loader passes 54 packaging/loader checks and the actual 137-case
native engine probe, including the existing 11 resource and five input refusals.
After the recorded Share-readiness and exact system-banner handling changes, all
five native workflows pass on the owned iPhone 14 Plus simulator with iOS 26.2.
The simulator is removed. The initial failures remain preserved, including the
intermediate test source needed to reproduce the keyboard failure. This is not
a physical phone or current hosted iOS 27.2 acceptance.

The selected native proof now uses the existing fingerprinted workflow location.
An executable website-input check requires the verifier's selected proof to be
included in the website source fingerprint. That new check fails on the prior
unbound selection and passes on the current selection; 63 focused proof,
packaging-verifier and website-input controls pass. The actual new signed archive
and Apple validation remain separate pending gates.

## Hosted simulator setup failure diagnostics

The current 9b03598 hosted run failed before building or executing UI tests,
at owned-simulator setup. Its empty boot/cleanup output does not distinguish
a command deadline, nonzero exit, or capacity refusal. Do not infer an app
failure or pass, extend a deadline, or blindly count a rerun as a fix. Record
each fixed verification command's start, bound, finish and failure class in
the proof, including cleanup, so the next execution can identify the stage.
These are synthetic verifier operations; no user text, credentials, or
application data is logged. Keep existing time, memory, test and cleanup gates.
A failed attempt must retain its source identities and remain failed.

The traced local run completes setup and both Share workflows, but passes only
four of five tests: the keyboard does not appear after the edit test's center
tap, with no onboarding banner visible. Preserve that result and its exact
verifier source. The next test-only candidate sends its single tap inside the
text view's first-line inset, after proving the field is hittable, rather than
the middle of a large empty scrolling region. This is an ordinary text-entry
action, not a retry, synthetic text injection or proven root-cause correction.
Require the same keyboard and stale-result assertions, then run all five tests.

The first-line candidate passes all three host-app workflows, including editing
and stale-result invalidation, but both Share workflows fail. The first opens
and receives the intended text, then never produces a result; the final status
is still the pre-check selection instruction after the attempted check tap. The
second never reaches the extension's finish control. These are different
observations, not evidence of a single established root cause. Both failures and
their attachments are retained. The owned simulator is removed. Do not repeat
the run without a diagnosis, bypass the existing evidence guard, or describe
the earlier five-pass result as current-source acceptance.

## Latest distribution failure: local re-signing

The saved distribution pipeline for the 1:50 PM module-archive candidate fails
at `IDEDistributionCodesignStep` on `AITrustIDShare.appex` with
`errSecInternalComponent`, at 19:36:58 UTC. Reinspection of the original archive
still passes both strict signatures, expected entitlements and all 32 resource
copies. Preserve the local failure separately from the two older server
rejections. Old resource errors also appear in the fetched validation history;
they are not a new rejection of this candidate.

Apple's [signing error guidance](https://developer.apple.com/forums/thread/712005)
explains that this error has multiple causes, including keychain access and
execution context. The missed key authorization and later relock are consistent
with an access failure, but the error alone does not prove the cause. Retry the
existing archive only after owner unlock and with the owner present for the
protected prompt. Do not revoke certificates, change key access policy, export
a private key, change trust settings or repackage source based only on this
error. Actual server validation and current Share workflow repair remain open.

## Owner-present retry passed Apple validation

The same existing archive, certificate and two provisioning profiles were used.
The owner approved the protected signing requests. Xcode reached package review
for both app and Share with the expected identifiers, arm64, version 1.0 (1),
`get-task-allow: false` and no optional symbols. Apple validation then passed;
the distribution log records success at 02:47:37 UTC on November 16, equivalent
to November 15 in the owner's timezone. No key ACL, trust policy, credential or
source package changed. This clears the observed signing/package gate, while
Share behavior, final declarations, reviewed upload and human acceptance remain.

## Controlled Share diagnostic after the signing pause

The two current Share failures occurred while a separate protected signing
authorization was pending. That does not establish causation. Now that signing
and validation have finished, exercise only those two unchanged synthetic Share
workflows on one owned simulator, with no concurrent signing or other builds.
Reuse the exact already-built project only after checking current source and
asset identities. Retain the original per-workflow deadlines and assertions.
A two-test diagnostic cannot replace the required five-workflow proof or restore
selected-integration credit. Preserve either result and remove only its owned
simulator. No further source workaround is justified without the observation.

The controlled diagnostic executes both tests without active codesign or another
Xcode build at its start. Source and generated project identities match the
previous compiled candidate. One Share workflow passes; the first practice-Share
case fails to find the activity. The final screenshot and hierarchy contain only
the host app, not an offscreen activity list or active Share sheet. The owned
simulator is removed. App-only system logs show touch dispatch but no captured
presentation warning; they do not establish whether the target action ran.
Do not attribute this failure to the signing prompt or weaken the five-test gate.
The next investigation should distinguish missing target-action delivery from a
presentation/lifecycle failure, with bounded synthetic-only diagnostics.
