# Android offline PS checker — developer operation

This branch contains the Android source and build path. GitHub Actions compiled
an APK with zero declared permissions and verified the signature on its
development test copy. The first runner lacked the preinstalled emulator
environment. PS remains a development preview. [Hosted build](https://github.com/knwvmbrr/aitrust-id/actions/runs/44169646271)

Android 10/API 29 or newer and a working multiprocess WebView are required. The
app appears in the system Share chooser for one `text/plain` item. It never
scans another app, follows a shared URL or checks automatically. Review/edit,
Check PS, read the short result, optionally open Why this tag, then Clear or Done.
Leaving the screen clears the input/result and terminates the app-owned renderer.
No account, Internet/storage/capture permission, analytics or submission is added.
The keyboard, sending app and OS remain outside this app's control. Clearing drops
references; it is not a promise of forensic erasure. WebView may retain non-content
runtime/cache metadata. The source includes the web brand's tag silhouette,
light/dark palette and subtle camouflage rather than a new mobile identity.

## Build from existing tools

The helper installs nothing. Use an existing JDK 17 or compatible JDK, Android
SDK platform `android-36` and build-tools `36.0.0`. Gradle/Android Studio are not
required. Set a private local SDK path only in your shell, never in source.

```sh
npm ci --ignore-scripts --prefix site
python3 -B scripts/android-share-build.py \
  --runtime-directory site/node_modules/pyodide \
  --compile --sdk-root "$ANDROID_SDK_ROOT" --java-home "$JAVA_HOME"
```

This creates `output/android-share/ai-trust-id-unsigned.apk` and source-bound
preparation/build reports. It refuses an absent SDK, changed runtime/notice,
unlisted output asset or output link. Five Pyodide runtime members must match
retained upstream byte observations; the current evaluator and pinned Unicode
normalizer are projected rather than rewritten. Source APK permissions must be
empty. Generated runtime/APK files stay under ignored `output/`.

For existing-tool component checks:

```sh
python3 -B -m unittest discover -s tests -p test_android_share.py -v
python3 -B scripts/verify-android-session.py --java-home "$JAVA_HOME"
node --experimental-vm-modules scripts/verify-android-engine.mjs
```

The final command requires prepared assets. It runs the actual Android loader
with the actual pinned WebAssembly runtime, adapting the runtime directory only
for Node's filesystem loader. It compares current synthetic development/Unicode
probe summaries. It is not an Android WebView, a real share event, a physical
phone test or independent accuracy measurement.

## Hosted build and emulator evidence

The dedicated `android-share` workflow uses Ubuntu 24.04's installed API 36,
build-tools 36.0.0 and JDK 17; missing tools fail rather than triggering SDK downloads
or license acceptance. It retains the same PR/main/tag trigger policy as other
component workflows, with explicit Android/engine input path filters.

The workflow can produce an **ephemeral CI test-signed APK** after actual compilation.
Its key is created and removed inside the job; it is not a production signing
identity. Do not represent that APK as a maintained Play release or promise stable
signing across builds. The unsigned APK is not directly installable.

The emulator step checks the hosted runner's SDK tools, KVM, recorded Android
SDK license record and disk space. On this disposable hosted runner only, an
ACL grants the current UID access to the existing KVM character device. If
emulator packages are absent, the helper verifies Google's reviewed package and
license-text identities and invokes the existing SDK manager for the emulator
and AOSP API 36 image revisions pinned in `PACKAGES` in
`scripts/verify-android-emulator.py`, with closed stdin. The SDK manager decides
whether its existing acceptance record permits installation; a raw repository
XML-text hash is not substituted for that decision. No license record is created
or changed; its bytes are checked on success and failure. Diagnostics and install
time are bounded; no installer text is published.
A dedicated emulator on port 5580 receives synthetic share intents.
The test checks explicit Check, PS finding, edit invalidation, a new share/No
finding, unsupported MIME refusal, Clear and background cleanup. It never selects
a connected phone. If prerequisites are absent, `emulator.json` records
`UNAVAILABLE`, `pass:false` and the specific missing conditions. A failed SDK
install unrelated to an explicit license refusal, or a failed emulator case,
fails the job. Explicit license refusal is Unavailable even if the SDK wrapper
returns zero. Only synthetic UI data is inspected,
and the app-owned emulator is stopped.

Run 44171007663 rebuilt and signed the test APK. The runner had the SDK tools
and sufficient disk. Its user could not access KVM, and the existing Android
SDK license record did not match the reviewed package license. The emulator
step refused before installation and executed zero Android cases. An emulator
with a working licensed SDK or an authorized test device is still needed.
[Runner inventory and APK evidence](../runs/2026-11-17-android-emulator-host-inventory.json)

## Acceptance still owed

- Android WebView/Share execution against the signed development APK.
- Real Android source-app compatibility and hostile/malformed intent checks.
- TalkBack, large text, contrast and navigation testing by actual users.
- Physical-device install, startup/memory/battery, offline/update/removal evidence.
- Outside-human usability and PS's own independent accuracy/release evidence.

The native UI/schema/resource/lifecycle boundaries are separate from detector
accuracy. Android delivery failure cannot disable iOS, the website or another tag.
No original scope requirement reaches 100% from these local checks.

## Upstream revision drift

The first November 19 hosted candidate stopped in reviewed metadata before
SDK installation or Android execution. KVM access and the existing license
record were present. A separate read of current official metadata reproduced
the old emulator revision guard refusing a newer stable release; the original
generic hosted report does not expose its exact exception. Preserve that failed
run. Updates to the reviewed package selection and fixed diagnostic codes are
engineering changes, not a reason to accept new terms or mark runtime tests
passed. The source constant and dated change records carry the selected revision;
this guide does not duplicate a moving version number.
