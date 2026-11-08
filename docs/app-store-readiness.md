# iPhone distribution readiness

AI Trust ID has its own registered bundle identifier, `com.aitrustid.app`.
An unsigned physical-iOS archive of the existing developer prototype also built
successfully. Its bundle identifier is still `com.aitrustid.personal.preview`;
it is not a signed or upload-ready store package.

[Device archive evidence](../runs/2026-11-08-ios-archive-readiness.json) records
the actual result. No App Store record, uploaded binary, TestFlight installation
or public phone release is claimed. Private account identifiers, credentials and
other projects are excluded from this repository.

## Complete the distribution package

1. Create the separate iOS App Store record, then register its Share extension
   identifier and configure the stable bundle identifiers in a store build.
2. Supply the owner-controlled signing identity and provisioning profiles.
   Keep private keys and account credentials outside source and public evidence.
3. Package the current tag method/runtime, required notices, app artwork and
   an accessible in-app privacy explanation with the published privacy URL.
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
