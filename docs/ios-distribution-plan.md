# Native iOS distribution preparation

The owner has an active Apple Developer membership and authorizes a separate AI
Trust ID app. The existing developer project is unsigned, uses a preview bundle
identifier, lacks an app icon and does not offer a complete in-app privacy or
license view. App Store preparation must preserve the existing independent PS
checker and its development/accuracy limitations.

Keep the existing developer profile as the default. Add a separate distribution
profile with `com.aitrustid.app` and `com.aitrustid.app.share`, a stable version,
and a packaged icon derived from this project's existing tag artwork. Keep team
identifiers, credentials, private keys and provisioning profiles outside source.
The generator must never create signing credentials or turn signing on merely
because a distribution profile was selected.

Add an offline, accessible privacy/notices view without uploading or retaining
selected text. Preserve edit/cancel/background clearing and never describe the
phone PS preview as PII redaction, independent accuracy or safety clearance.
Keep every runtime request inside the existing local asset scheme. Website
navigation, if offered, must require an explicit action and pass no selected
text, record, hash or query parameters.

Risks are stale native evidence, altered Share lifecycle, accidental signature
sharing with another project, incomplete asset packaging, text leakage, and
misleading release claims. Check both generated profiles, source/runtime hashes,
no-secret packaging and required failure cases. Build an actual device archive
and exercise current native workflows on an owned simulator. Record those results
separately from signed upload, TestFlight installation, physical iPhone 14 Plus,
VoiceOver/outside-user acceptance and independent tag validation.

Create and verify the App Store Connect app record using only this project's
registered bundle. Prepare factual metadata. Skip owner-only legal, signing or
credential decisions and continue other work. Do not select trader status or
accept new agreements on the owner's behalf. Nothing here completes N-013 or
releases a tag without its original acceptance.

## Actual build and first UI attempt

The separate registered-ID archive built and its embedded app/Share resources
match the generated package. The first five-workflow simulator run passed three
cases, including the offline privacy/license view, but failed a text-entry focus
step and a subsequent Share launch. It is retained as a failed attempt, with
owned-simulator cleanup verified. It is not a release or passing workflow proof.

Strengthen existing tests to wait for keyboard readiness and actual Share
dismissal/host hitability before the next operation. Keep every original case
and its existing deadlines. Capture the actual app hierarchy and an invented-text
screenshot if Share admission still fails. Keep desktop browser automation quiet
while the native UI sequence runs, to avoid competing focus operations. No
blanket retry, skipped case or relaxed result assertion is accepted.

The distribution archive check must also be repeatable from current source.
Generate into a new private directory, build only the unsigned registered-ID
profile, and compare both actual bundle identities, versions, executables,
orientations, icon and runtime/privacy/license bytes. Refuse signatures,
provisioning, unexpected links, stale sources and incomplete resources. Keep
diagnostics private; expose only bounded source/resource identities and results.
Execute this device-compilation check in the existing native CI job after its
unchanged five UI workflows. It neither creates credentials nor uploads a build.

## Executed outcome

The second UI attempt passed four cases. Its captured hierarchy showed selected
text and the unchanged "Review the selection" status after the attempted Check
tap; evaluation had not started. Check is now available only after presentation
and valid text delivery, and tests wait for that readiness. All original five
workflows then passed on a new owned simulator, with unchanged source hashes
and verified removal. No result assertion, case or deadline was relaxed.

[Current workflow](../runs/2026-11-09-native-share-distribution-workflow.json) and
[registered-ID archive](../runs/2026-11-09-ios-distribution-final-archive.json)
record the passing software results. The two failed attempts remain preserved.
The archive verifier also has content/refusal controls for wrong identifiers,
simulator output, missing or altered resources, signatures, profiles and links.
App Store signing/upload, actual-phone and human/independent acceptance remain
open. This increment does not close a full scope requirement.
