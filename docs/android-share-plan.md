# Android text Share to PS — architecture before implementation

Owner: Codex Android lane. PM/integration: Codex. Date: 2026-11-17.
Base: `0ff7a08630e05ab5f08a801a7fd5ad40df896ab7`. Existing requirement: N-014.

## Bounded outcome

Receive one explicitly shared `text/plain` `ACTION_SEND` item, show editable text,
and run PS locally only after Check. Also allow a person to open the app and paste
text. This delivers a separate Android route; it does not release PS, issue other
tags, read other apps, fetch shared URLs or collect examples. No new service,
endpoint, account, upload, overlay, capture or accessibility-service permission.

## Architecture and source identity

Support Android 10/API29 and newer so cancel/background can terminate the
app-owned renderer process. A provider without a separate renderer is
Unavailable rather than accepted without that cancellation boundary. Use a native platform Java Activity and a hidden, locked WebView for the existing
Python-to-WebAssembly engine. Do not translate the detector into another language.
The preparer uses `scripts/build-device-detector.py` to project the exact current
PS evaluator and pinned Unicode normalizer. Verify the five cached Pyodide
314.0.7 files against the retained runtime member hashes and retain notices.
Generate a manifest of every bundled asset; verify each asset before serving it
through one reserved HTTPS app-assets origin. Reject unknown paths, network
requests, navigation and file/content URLs. No INTERNET permission is requested.
No JavaScript-to-native interface is exposed. Only native-initiated evaluations
read the fixed loader state/result. Shared text is a JSON-encoded function argument,
never JavaScript/Python source, an HTML fragment or an executed command.

The renderer returns a bounded summary carrying method/normalization identity.
Native code verifies state, identity, revision and fixed signal vocabulary before
showing one small PS chip and short explanation. No finding is not a safety
clearance. This is a development checker, not independently measured accuracy.

## Lifecycle, privacy and resource contract

- Input: 1–20,000 Unicode codepoints; reject malformed surrogate pairs, empty,
  oversized or unsupported share payloads without truncating a verdict.
- Reject file/stream and multiple-item shares. Never open shared URI content.
- No automatic check: receive/review/edit, then explicit Check. Editing invalidates
  the displayed and pending result immediately.
- One renderer/request; startup budget 30 seconds and check budget 5 seconds.
  Clear, Cancel, a new share, renderer loss and backgrounding invalidate the
  generation token and destroy the engine. A late callback cannot restore a result.
- No participant text/result storage, analytics, clipboard reading, text logs,
  backup or saved editor
  state. The WebView provider may retain non-content runtime/cache metadata. Drop
  intent extras after receiving. Clear editor/results on background;
  exclude the task from Recents and secure the window against capture. Clearing
  drops references; do not promise forensic memory erasure or control over the
  sending app, OS keyboard or device administrator.
- Package only an allowlisted, hash-checked runtime, method, loader and notices.
  No runtime downloads or package installation from the app.

## Product and failure behavior

Native controls keep the web brand's light `#f3f1e7` / dark `#11170f` base,
subtle camouflage background and compact PS chip. Use native text scaling,
left-aligned short descriptions, labeled editor, generous controls and live status.
Unavailable is distinct from No finding; a broken Android renderer cannot affect
other routes or tags. Unsupported sharing is explained without a verdict.

## Build and acceptance plan

Use the official SDK's aapt2, javac, d8 and zipalign directly; no Gradle or Java
library dependency is necessary. A reproducible helper emits an unsigned APK;
installation signing belongs to an explicit development build step, not a public
release credential. Do not publish a store-ready or signed release claim.

Initial tool inventory found a usable existing Homebrew JDK25 but no SDK,
Gradle, emulator or system image in normal locations. Only 8.1 GiB disk was free.
The existing verified Pyodide cache is available outside this isolated checkout.
Do not download Android Studio or a multi-gigabyte emulator without PM scheduling.
Complete software and bounded tests even while actual SDK execution is pending;
record that gap. A hosted SDK build/emulator workflow requires PM ownership approval.

Verify input/lifecycle state transitions and exact projection parity, loader
result/schema refusals and cancellation, deterministic asset packaging with
hash/notice refusals, and actual Java/APK compilation when SDK tools are available.
On a real emulator, send supported and refused intents, Check, edit, Clear,
background and new-share flows; retain only synthetic-input evidence. Physical
Android/TalkBack, different source-app compatibility, offline update/removal,
outside-human usability and independent PS accuracy remain separate acceptance.
N-014 cannot reach 100% from source or emulator work alone.

## Primary references inspected

- [Android receive sharing](https://developer.android.com/develop/ui/compose/sharing/receive):
  ACTION_SEND/MIME registration and explicit EXTRA_TEXT receipt.
- [Local WebView content](https://developer.android.com/develop/ui/views/layout/webapps/load-local-content):
  HTTPS-like local origins and file/content access restrictions.
- [WebView APIs](https://developer.android.com/develop/ui/views/layout/webapps/webview):
  JavaScript is enabled only for the controlled local loader.
- [AAPT2](https://developer.android.com/tools/aapt2),
  [D8](https://developer.android.com/tools/d8),
  [APK signing](https://developer.android.com/tools/apksigner): official direct
  compilation, packaging and signing tools.

Security review is required before integration. No physical device, Play Store,
independent validation or full original-scope closure is claimed by this plan.

## Hosted emulator follow-up, after the first APK build

The successful hosted build used Ubuntu image `20261111.370`. Its standard
inventory supplies command-line tools, API 36, build-tools and JDK 17. The image
and emulator are absent from the runner's published package list. Before booting
an emulator, record each prerequisite separately. The Android workflow may
request the two pinned official Linux packages only on a GitHub-hosted runner
with an existing exact `android-sdk-license` record, accessible KVM, the
installed tools and sufficient free space. Read the Google repository metadata
and require the reviewed stable revisions, archive sizes and checksums. Use
closed stdin for `sdkmanager`, check the installed revisions and require license
bytes to remain unchanged. Report drift or a missing prerequisite before boot.

Use the smaller AOSP API 36 x86_64 revision 2 system image with emulator 37.2.13.
Google lists roughly 1.19 GB total compressed. Individual downloads and the job
have deadlines. Scope signing, emulator data and synthetic inputs to the
disposable runner. Failure after starting an agreed test cannot pass as an
emulator result. Physical acceptance remains separate.

- [Exact hosted inventory](https://github.com/actions/runner-images/blob/ubuntu24/20261111.370/images/ubuntu/Ubuntu2404-Readme.md)
- [Google AOSP system image metadata](https://dl.google.com/android/repository/sys-img/android/sys-img2-3.xml)
- [Google Android emulator metadata](https://dl.google.com/android/repository/repository2-3.xml)
- [Android SDK license-record implementation](https://android.googlesource.com/platform/tools/base/+/mirror-goog-studio-master-dev/repository/src/main/java/com/android/repository/api/License.java)

## November 19 prerequisite correction plan

The earlier hosted run never booted Android. It found inaccessible `/dev/kvm`
and no literal match between the repository XML license text hash and the
runner's existing SDK record. The XML hash is useful to detect metadata drift;
it is not a substitute for the SDK manager's actual acceptance check.

Keep the reviewed metadata/license bytes and package identities pinned. Require
an existing regular bounded license-record file and never write to it. Invoke
the existing SDK manager with closed stdin, then verify the original record is
unchanged on success **and failure**. Only the SDK manager may decide whether an
existing record permits installation. A refused license is an unavailable
prerequisite, never a passed runtime check; unrelated installation failure fails.

On the disposable GitHub-hosted Linux runner only, grant its current UID read
and write access to the existing KVM character device using an ACL, not global
device permissions. No local Mac, self-hosted host or phone is changed. Missing
KVM/ACL tools remain explicit unavailable prerequisites. Retain bounded install,
boot, UI and cleanup deadlines and the dedicated emulator serial.

Risks: misclassifying SDK failures, accepting altered license records, broad host
access, and calling an unexecuted emulator a success. Add refusal controls for
missing/link/oversized license records, unchanged and changed failure outcomes,
closed stdin, exact metadata drift, and hosted-only KVM dispatch. Actual hosted
execution is needed after those controls; Android/TalkBack physical acceptance
and N-014 remain open regardless of emulator results.
