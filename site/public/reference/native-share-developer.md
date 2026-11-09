# Native iPhone sharing: developer verification

This is an unreleased developer workflow, not a phone app download or an
independently validated tag. The existing website checker remains usable on its
own. No local Docker, account, server or telemetry is needed for this workflow.

The containing app offers **Practice sharing** with invented text. In the Share
sheet choose **AI Trust ID**, review the selected words and press **Check with
PS**. Checking is explicit. **Why PS?** expands the matched words and reason inline; tap **Hide details** to close it.
**Clear** removes the selection and result; **Done / Cancel** closes the sheet
without sending anything. Editing or backgrounding invalidates pending work.
Commands are treated as text and never executed. This route does not redact PII.

## Run the developer workflow

Use macOS, Xcode, an already installed available iOS simulator runtime, Python
3.12 or later and at least 5 GB of free space. Prepare current public assets with
the documented website build and pinned dependencies. Obtain the exact installed
runtime identifier from `xcrun simctl list runtimes`. No SDK/OS download, paid
developer account, phone profile or authentication credential is created.

```sh
practice="$(mktemp -d "${TMPDIR:-/tmp}/aitrust-share.XXXXXXXX")"
python3 scripts/verify-ios-share.py \
  --output "$practice/share-proof" \
  --runtime com.apple.CoreSimulator.SimRuntime.iOS-26-2
```

The command creates its own iPhone 14 Plus simulator, builds the current app and
extension, runs five actual UI workflows and removes only that simulator. It
rejects an existing output path or any output inside a Git checkout. Logs,
generated code, the Xcode result bundle and `proof.json` stay in the private
output directory. They use invented examples only. A boot, timeout, skipped case,
source change, failed workflow or cleanup failure cannot produce a passing proof.
Each workflow has a 120-second automation allowance (150-second Xcode ceiling);
the entire UI phase remains bounded at 600 seconds. All five original scenarios and their acceptance remain required. The first
workflow also opens the offline privacy and license view. Keyboard readiness and
completed Share dismissal are checked before subsequent actions. These are development-runner limits,
not measured or accepted phone performance claims.

For source inspection alone, run:

```sh
python3 scripts/build-ios-project.py --output "$practice/project"
```

This creates a private developer-project ZIP with the exact
current public method/runtime, license notices and source. It is not a signed
physical-phone installer. The resource-only verifier in
[native-engine-checks.md](native-engine-checks.md) remains independent.

## Capture and compatibility boundary

Only one explicitly shared item/provider is accepted. Supported text type
representations become bounded string data; URLs and filenames are never opened.
Empty, malformed, null-containing and oversized selections are refused. The
limit is 20,000 Unicode scalars and 80,000 decoded UTF-8 bytes. UTF-16 data needs
an explicit byte-order mark. These checks occur after the provider allocates its
representation; they are not a hard OS/Share memory ceiling.

The observed generic text provider requires the typed `loadItem` compatibility
API. It is available in the tested SDK but deprecated in iOS 27. Modern string
and raw-data attempts did not establish a working Share handoff. Do not claim
future SDK compatibility. Cancellation invalidates delivery/check generations;
the compatibility API does not physically cancel or erase the provider's memory.
WebKit uses bundled, hash-checked resources and nonpersistent website storage.
No remote request, fallback model or selected-text URL handoff is added.

Physical iPhone 14 Plus installation, actual iOS version, Share from real source
apps, device memory limits, VoiceOver, removal and outside-user acceptance remain
required. A simulator workflow cannot satisfy these tasks or PS's independent
accuracy gate. N-013 stays open until its full acceptance is completed.

## Prepare the separate distribution project

AI Trust ID now has its own App Store Connect record in **Prepare for Submission**.
The app identifier is `com.aitrustid.app`; the separately registered Share
identifier is `com.aitrustid.app.share`. The saved draft requires no app login
and uses manual release. No build has been uploaded or approved.

```sh
python3 scripts/build-ios-project.py --profile distribution \
  --output "$practice/distribution"
```

Build and inspect an actual unsigned iPhoneOS Release archive with:

```sh
python3 scripts/verify-ios-archive.py --output "$practice/device-archive"
```

This checks both registered identifiers, version 1.0, executable presence,
compiled icon, orientations and exact privacy/license/runtime resources. It
refuses signed/provisioned or altered contents and source changes during the
build. Logs and the archive stay private; the proof contains source/resource
identities. This check also runs in native CI. It does not create credentials,
provision a phone or upload anything.

The distribution profile uses version 1.0 and the registered identifiers, and
packages the tag icon, offline privacy explanation and original runtime/code
license notices. The default developer profile retains its preview identifiers
and version 0.1. **Both profiles leave signing disabled.** Neither creates
credentials, selects a developer team, fetches provisioning profiles or uploads
a build. Keep private signing material outside Git and the generated source ZIP.

Unzip the project into a private working folder and inspect it in Xcode. The
owner must supply an appropriate signing identity and profiles for both targets
before a signed archive or TestFlight upload. Selecting a distribution profile
alone does not make an installable phone app. Do not reuse another project's
identifiers or private signing files.

In the containing app, **Privacy & open-source notices** opens bundled text and
licenses. It does not open a browser, detect links or send selected text. This
view and PS's local resources work offline. Apple/TestFlight feedback, device
keyboards and operating-system services have separate privacy behavior.
