# iPhone distribution readiness

AI Trust ID has a separate App Store Connect record, saved in **Prepare for
Submission**, and registered identifiers `com.aitrustid.app` and
`com.aitrustid.app.share`. Its draft requires no app sign-in and uses manual
release. The App Store version has not been submitted for public review.

The saved app-information draft uses **Check shared text offline**, category
**Utilities**, and the existing public privacy-policy URL. Privacy declarations
and review contact are pending.

## November 17 candidate

The current app opens bundled privacy and license notices as separate
documents with up to 3,000 characters per page. The Python standard-library
notice remains complete. [Exact reconstruction](../runs/2026-11-17-ios-notice-page-reconstruction.json)
verified all seven documents. All
[five workflows](../runs/2026-11-17-paged-notices-native-share-workflow.json)
passed on iOS 26.2 Simulator. The new
[unsigned device archive](../runs/2026-11-17-paged-notices-ios-archive.json)
verified the bundle identifiers, compiled icon and all 36 runtime and notice
resources. The hosted iOS 27.2 run of the previous reader reached its UI deadline
while querying the combined notice view. The paginated reader
[passed all five UI workflows on hosted iOS 27.2](../runs/2026-11-17-paged-notices-ios27-ui-and-cleanup.json).
The hosted job failed afterward because simulator shutdown and deletion timed out.
The local simulator run completed cleanup.

The existing Apple Distribution identity matches the current app and Share
provisioning profiles. A bounded signing attempt on a private copy timed out
at the Share extension before producing a signature. The unsigned archive was
preserved. macOS logs show a protected Keychain authorization request immediately
before the signing operation stopped making progress. The developer team and distribution certificate are visible in Xcode. The
[current signing preflight](../runs/2026-11-17-paged-notice-signing-preflight.json)
verified Release signing settings for both targets and matched the installed
profiles to the existing certificate. See the
[signing attempt](../runs/2026-11-17-current-ios-signing-attempt.json) and
[Keychain diagnosis](../runs/2026-11-17-ios-signing-keychain-diagnosis.json).
An [earlier package](../runs/2026-11-15-validated-ipa-inspection.json) passed
[Apple validation on November 15](../runs/2026-11-15-apple-package-validation-passed.json).
The November 17 signing result was provisional. Keys, profiles and build
artifacts stay private.

### Subsequent signing and simulator check

The [Xcode archive retry](../runs/2026-11-17-share-manual-signing-retry.json)
matched both profiles and requested protected Keychain access at the Share
extension. It reached the 120-second deadline before producing a signed archive.
The [fresh unsigned archive](../runs/2026-11-17-owned-cleanup-ios-archive.json)
verified both bundle identifiers and all 36 runtime and notice resources.

The [cleanup candidate](https://github.com/knwvmbrr/aitrust-id/tree/codex/ios-owned-cleanup)
deleted its own simulator and verified the registry no longer contained it in
three local runs and on [hosted iOS 27.2](../runs/2026-11-17-hosted-ios27-owned-cleanup.json).
That hosted run completed notice navigation, then hit the case deadline
while waiting for a second PS result.

The current suite runs notice navigation separately. All six named workflows
and simulator removal passed together on local iOS 26.2.
[Local proof](../runs/2026-11-17-split-native-share-workflow.json) ·
[Hosted iOS 27.2 proof](../runs/2026-11-17-hosted-split-ios27-pass.json)

## November 18 distribution

The current app and Share extension were signed with the existing profiles.
The exported build **1.0 (1)** preserves all 36 expected runtime and notice
resources and passed all Apple Organizer validation checks. See the
[signed build and validation receipt](../runs/2026-11-18-ios-signed-archive-and-apple-validation.json).
Xcode confirmed that [the internal TestFlight upload completed](../runs/2026-11-18-ios-testflight-internal-upload.json).
Signed-in Chrome now shows internal build **1.0 (1)** with **Missing
Compliance**. **iPhone Owner Test** has the account holder as its sole tester
and manual build assignment. Apple disables build 1 in that group’s picker
until compliance is resolved. [Group enrollment evidence](../runs/2026-11-18-testflight-owner-group.json). The [dashboard observation](../runs/2026-11-18-testflight-missing-compliance.json)
is separate from the upload receipt.

The [signed-package audit](../runs/2026-11-18-ios-testflight-compliance-inputs.json)
verified both targets, all five runtime files in each, and the bridge source.
The checker uses SHA-256 for package integrity. The bundled WASM provides a
Python hashing implementation and reports `OpenSSL (stub)` with zero cipher
suites when probed in Node. Neither target declares `ITSAppUsesNonExemptEncryption`.
This is evidence for reviewing the questionnaire, not an export determination
or a physical-device measurement. Apple describes [how to clear Missing
Compliance](https://developer.apple.com/help/app-store-connect/test-a-beta-version/provide-export-compliance-information-for-beta-builds/).

### First iPhone 14 Plus check

1. In [App Store Connect](https://appstoreconnect.apple.com/apps), open
   **AI Trust ID → TestFlight → iOS**, choose **Manage** next to **1.0 (1)**
   and review and submit the export compliance information. When Apple makes
   the build available, add it to **iPhone Owner Test** using the
   [internal tester instructions](https://developer.apple.com/help/app-store-connect/test-a-beta-version/add-internal-testers/).
2. Open **TestFlight** on the iPhone and install **1.0 (1)**. Then open AI Trust
   ID and try **Practice sharing**. In the share sheet, select **AI Trust ID**.
   Confirm the text appears for review and the app waits for **Check with PS**.
3. Turn on **VoiceOver** under **Settings → Accessibility → VoiceOver**. Confirm
   it can reach **Check with PS**, announces the result, reaches **Why PS?** and
   can dismiss the sheet. Check from a second source app using invented text,
   and confirm editing or clearing removes the old result.
4. After installation, repeat the synthetic check with Wi-Fi and cellular
   disabled. Record the iOS and app versions and which steps passed; do not
   include private shared text in feedback.

This is a physical acceptance checklist; it is not a test result.

The [listing draft record](../runs/2026-11-17-ios-listing-drafts.json) covers four
actual screenshots of the initial checker in Light and Dark mode. The simulator
captures use iPhone 14 Pro (1179 × 2556) and 13-inch iPad Pro (2064 × 2752).
The JPEGs remain private for review. Apple lists these dimensions in its
[screenshot specifications](https://developer.apple.com/help/app-store-connect/reference/app-information/screenshot-specifications/).
Store asset upload and physical acceptance are pending.

## Complete the distribution package

1. Verify the separate app/Share identifiers and saved draft against the
   generated distribution project; keep the preview build separate.
2. Sign with the matched distribution identity and provisioning profiles.
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
iOS 27.0.1. Developer Mode is disabled. The November 9 read-only check predates the current signing identity and profiles.
The device setting was left as observed and physical app workflows remain pending.
See the [read-only observation](../runs/2026-11-09-iphone-target-status.json).

## November 10 listing draft

The owner reopened the signed-in App Store session. A short promotional line
now explicitly describes the offline PS development preview; a reload confirmed
it persisted alongside the existing description, keywords and support/marketing
links. The version remains Prepare for Submission. The review-contact section
requires an owner-supplied phone number; its other contact fields remain blank.
Screenshots, copyright/provider review, final declarations and signed build
upload remain unfinished. Nothing was added for review. See the
[saved draft observation](../runs/2026-11-10-app-store-draft-reopened.json).
