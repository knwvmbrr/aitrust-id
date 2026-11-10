# iPhone distribution readiness

AI Trust ID has a separate App Store Connect record, saved in **Prepare for
Submission**, and registered identifiers `com.aitrustid.app` and
`com.aitrustid.app.share`. Its draft requires no app sign-in and uses manual
release. No build has been uploaded or submitted to Apple.

The saved app-information draft uses **Check shared text offline**, category
**Utilities**, and the existing public privacy-policy URL. Privacy disclosures
remain unpublished. The owner has now signed into the existing developer team
in Xcode. Its local certificate panel is empty and creation actions were disabled
when inspected; that observation does not establish whether cloud signing is
available. Signing and provisioning still need verification. No new external-agent access,
certificate, private key, legal declaration or account permission was granted.

The separate distribution profile now builds an actual unsigned physical-iOS
archive with those identifiers, version 1.0, a compiled app icon and exact bundled
privacy/license/runtime resources. The default developer profile remains
separate. [Archive inspection](../runs/2026-11-09-ios-distribution-final-archive.json)
records this bounded result. Signing remains disabled in both profiles. Private
account identifiers, credentials and other projects remain outside the repo.

## Complete the distribution package

1. Verify the separate app/Share identifiers and saved draft against the
   generated distribution project; keep the preview build separate.
2. Supply the owner-controlled signing identity and provisioning profiles.
   Keep private keys and account credentials outside source and public evidence.
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

Native sharing remains N-013 at 80%. Independent recognition, physical-phone
and human acceptance remain open; membership, bundle registration and a compiled
archive do not complete them. The website and standalone tools remain separate
ways to use the supported checks.

## Current physical target

Apple device status identifies the paired, connected iPhone 14 Plus as running
iOS 27.0.1. Developer Mode is disabled. The existing manual-profile download
produced no AI Trust ID profile, and this Mac still has no valid local signing
identity. Cloud signing remains unverified. No device security setting was
changed, no credential was created or revoked, and no physical app workflow or
upload is credited. See the [read-only observation](../runs/2026-11-09-iphone-target-status.json).

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

No private key was read or exported by Codex, and no signed archive, build upload,
TestFlight distribution, physical acceptance or public app release is credited.
