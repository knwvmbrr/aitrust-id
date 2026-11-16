# iPhone distribution readiness

AI Trust ID has a separate App Store Connect record, saved in **Prepare for
Submission**, and registered identifiers `com.aitrustid.app` and
`com.aitrustid.app.share`. Its draft requires no app sign-in and uses manual
release. No build is available in App Store Connect or submitted for App Review.
Earlier package-validation attempts failed; the sealed module archive passed actual Apple validation on November 15, 2026.

**Latest release gates:** actual Apple package validation **passed** for
AITrustID 1.0 (1) on November 15, 2026, after owner authorization of the existing
signing key. Xcode and the distribution log both confirm success for the sealed
module archive. The original archive also passes both strict signatures,
expected entitlements and all 32 resource comparisons. Prior local signing and
standalone-source rejection failures are preserved as history.

This is package acceptance, not App Review approval, a TestFlight release,
physical-device acceptance or independent tag validation. The final November 16
source repairs activity-readiness queries and actual-failure diagnostics. Its
complete five-workflow hosted acceptance remains pending. A longer-press test
candidate failed both Share cases with captured upstream synthesized-input loss
and was reverted. Earlier local and hosted failures are retained in the
[reliability investigation](share-reliability-plan.md). Current Share integration,
final platform/privacy review and reviewed upload remain open. See
[the successful validation](../runs/2026-11-15-apple-package-validation-passed.json)
and [the repair plan](ios-module-archive-plan.md).

The saved app-information draft uses **Check shared text offline**, category
**Utilities**, and the existing public privacy-policy URL. Privacy disclosures
remain unpublished. The owner is signed into the existing developer team in
Xcode and has created the matching Apple Distribution identity. Two App Store
profiles and the signed Release archive are now inspected, as detailed below.
Earlier empty-certificate-panel observations remain in their dated receipts;
they are not the current signing state. Codex did not create or export a private
key or grant external-agent access. Final platform declarations remain open.

The separate distribution profile now builds an actual unsigned physical-iOS
archive with those identifiers, version 1.0, a compiled app icon and exact bundled
privacy/license/runtime resources. The default developer profile remains
separate. [Archive inspection](../runs/2026-11-09-ios-distribution-final-archive.json)
records this bounded result. The public generator leaves signing disabled in
both profiles; the separate owner-controlled private project is now signed. Private
account identifiers, credentials and other projects remain outside the repo.

## Complete the distribution package

1. Verify the separate app/Share identifiers and saved draft against the
   generated distribution project; keep the preview build separate.
2. Preserve the now-configured owner-controlled identity and two provisioning
   profiles outside source and public evidence; recheck them for every build.
3. Finish the required-reason API, privacy-manifest and final data-use review
   against the actual signed package and its bundled runtime. The icon and
   offline privacy/license view are packaged; this is not redistribution or
   privacy clearance for every transitive component.
4. Inspect an actual signed archive, validate it, and upload the reviewed build
   to App Store Connect for an owner-run TestFlight pilot.
5. Run the existing physical iPhone 14 Plus, Share-source, lifecycle, offline,
   VoiceOver, update/removal and outside-user acceptance tasks. Record the actual
   device OS; simulator and device compilation are different evidence.
6. Review the store metadata, support contact, data-use disclosures, encryption
   answers, seller identity and territory/trader information before submission.
   Explain Apple/TestFlight feedback and diagnostics in the pilot notice; do not
   automatically forward screenshots or text into the optional research pipeline.
7. Complete each offered tag's own validation gates before a public tag release,
   then submit the finished app to Apple for review.

Apple's [TestFlight guidance](https://developer.apple.com/help/app-store-connect/test-a-beta-version/testflight-overview)
describes beta distribution before public submission. The current
[App Review Guidelines](https://developer.apple.com/app-store/review/guidelines/)
require completeness and on-device testing (2.1), self-contained software
(2.5.2), useful native functionality (4.2), and accurate accessible privacy
information (5.1). These sources were checked during this readiness review;
this document does not establish Apple's approval.

Native sharing is N-013 at 60%; current selected-integration credit is withheld after the latest Share failures. Independent recognition, physical-phone
and human acceptance remain open; membership, bundle registration and a compiled
archive do not complete them. The website and standalone tools remain separate
ways to use the supported checks.

## Current physical target

Apple device status identifies the paired, connected iPhone 14 Plus as running
iOS 27.0.1. Developer Mode is disabled. The earlier manual-profile download
produced no AI Trust ID profile; that historical observation is retained. The
owner-created local identity and two profiles are now available. Cloud signing
remains unused. No device security setting was changed, and no physical app
workflow or upload is credited. See the
[earlier device observation](../runs/2026-11-09-iphone-target-status.json) and
the current signing inspection below.

## Reopened listing draft

The owner reopened the signed-in App Store session. A short promotional line
now explicitly describes the offline PS development preview; a reload confirmed
it persisted alongside the existing description, keywords and support/marketing
links. The version remains Prepare for Submission. The review-contact section
requires an owner-supplied phone number; its other contact fields remain blank.
Screenshots, copyright/provider review, final declarations and signed build
upload remain unfinished. Nothing was added for review. See the
[saved draft observation](../runs/2026-11-10-app-store-draft-reopened.json).

## Owner-created signing request

The owner's new saved-to-disk CSR has a verified signature and RSA 2048-bit public
key. The public request is selected on Apple's certificate page, with Continue
enabled; final issuance remains the owner's action. The expired 2023 WWDR
intermediate was supplemented with Apple's official G3 intermediate, verified
against existing system trust and displayed valid in login. No custom trust
override was added. These changes do not establish which condition caused the
earlier Certificate Assistant error. See the [prerequisite observation](../runs/2026-11-10-apple-signing-prerequisites.json)
and [verified request handoff](../runs/2026-11-10-owner-csr-ready.json).

That request handoff is preserved as a historical observation. The owner has now
issued and downloaded the matching Apple Distribution certificate. Its public
key matches the CSR and private-key attributes in Keychain, and local code-signing
certificate trust passes. Codex imported the public certificate; the private key
was not read or exported.

Separate App Store profiles now bind the app and Share IDs to that signer, with
debugging disabled and no registered-device distribution. A private copy of the
current generated project was manually configured with those exact profiles and
identity. The signed Release archive passes strict signature verification for
both executables, embeds the expected profiles and preserves all 32 selected
runtime/disclosure resources. The public project generator continues to default
to unsigned output. See the [signed archive inspection](../runs/2026-11-10-ios-signed-archive.json).
Local App Store export now passes. The 13,006,750-byte IPA is version 1.0 (1),
with both strict signatures verified and all 32 runtime/disclosure resources
unchanged after export. See the [signed package inspection](../runs/2026-11-10-ios-signed-package.json).
Apple server validation now returned an error: the Share extension’s bundled
`Assets/method.py` is treated as unsigned code. Local archive and IPA signature
checks passed, but did not detect this server rejection. The failed package is
preserved. Resource packaging needs repair and a new actual Apple validation;
no build upload, TestFlight distribution, physical acceptance or public release
is credited. See the [actual validation failure](../runs/2026-11-12-apple-package-validation-failed.json).

## Renamed resource candidate — rejected

The previous candidate packaged a sealed `method.py.txt` resource, served through
the unchanged `/method.py` logical route with the original bytes and hash. The
candidate passed 137 native detector cases and five app/Share simulator
workflows on iOS 26.2. An earlier two-failure workflow run is preserved; the
repeat does not establish why it failed. Xcode archived the manually provisioned
repair and both signatures and 32 resource copies passed inspection. Apple
revalidation then rejected that renamed file with the same unsigned-code error.
Local resource sealing and mode 0644 were inspected; the server's classification
cause is unproven. The new module archive still requires actual native execution,
signing and Apple acceptance. Upload remains unavailable. See the
[repair plan and execution limits](ios-script-resource-plan.md).

## Preserved validated package

The exact 12,925,499-byte IPA produced by successful validation is preserved
privately. Reinspection of that extracted IPA passes both strict signatures,
expected entitlements, version 1.0 (1), and all 32 resource comparisons against
the generated distribution inputs recorded by that inspection. Its SHA-256 is
`d1d8cc7abb5321865dbc7548014d5771febed4c480fbadf7d52c79df1e995db2`.
See [the IPA inspection](../runs/2026-11-15-validated-ipa-inspection.json).
The binary is not committed or offered as an installation download. App Store
Connect/TestFlight availability, current Share acceptance and final platform
declarations remain separate from this preserved artifact.

The resource comparisons above describe the inputs at the time that IPA was
validated. The current generator additionally packages a source-reviewed
`PrivacyInfo.xcprivacy` in both targets. That changes bundle bytes. The old IPA
remains valid historical evidence; its Apple validation does not apply to a new
archive. [Focused packaging/refusal controls](../runs/2026-11-16-ios-privacy-packaging-controls.json)
pass, and the actual unsigned Release archive passes all 34 resource-copy comparisons,
including both manifest files. A 120-second existing-identity signing attempt
stopped at the first Share CodeSign step without a completed archive or an
established cause. No identity, trust or key-access setting was changed.
Owner-dependent signing remains deferred. See the
[unsigned archive](../runs/2026-11-16-ios-privacy-unsigned-archive.json),
[bounded signing attempt](../runs/2026-11-16-ios-signed-candidate-timeout.json) and the
[privacy manifest plan](ios-privacy-manifest-plan.md). Full dependency/privacy
review and final platform declarations remain open.


## Saved TestFlight pilot information — November 16

The signed-in TestFlight page shows **No Builds**. Beta instructions, explicit
Practice/Check/Clear steps, voluntary-feedback guidance, admin feedback address,
marketing/privacy links and reviewer notes are now saved; Apple displays
**Saved**. The [exact saved copy](testflight-preview-copy.json) and
[observation](../runs/2026-11-16-testflight-information-saved.json) are versioned.
Review contact fields remain blank, sign-in stays unnecessary, and the license
agreement was not edited. No tester was invited or beta review submitted.

The phone's observed Developer Mode setting concerns local Xcode/development
installation. It is not a TestFlight prerequisite: Apple's
[Developer Mode guidance](https://developer.apple.com/documentation/xcode/enabling-developer-mode-on-a-device)
explicitly leaves normal TestFlight installation unaffected. No phone security
setting needs to be weakened for that distribution route. Signing, reviewed
upload and a real TestFlight build are still required.


## Actual five-case UI success; producer acceptance still open

Hosted run 43914592758 completes boot, build and all five original app/Share UI
workflows with no failures or skipped cases. It fails afterward at the existing
30-second result-summary command. Separate inspection of the retained result
bundle confirms 5/5, but cannot create the missing complete source-bound proof.
The [failed producer and recovered summary](../runs/2026-11-16-hosted-five-ui-result-timeout.json)
remain separate evidence.

The lifecycle revision reclaims only the completed owned simulator before
summary parsing, retains immediate post-UI/final source snapshots, and permits
only one strict cleanup attempt. All 130 adjacent controls pass and the current
unsigned archive again matches all 34 resources. A new complete producer run
remains required; signing, Apple revalidation of changed bytes, final platform
declarations and TestFlight upload remain open. N-013 stays 60%.
