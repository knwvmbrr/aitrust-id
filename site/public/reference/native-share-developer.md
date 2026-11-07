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
Per-test deadlines prevent an event-synthesis stall from consuming half an hour.

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
