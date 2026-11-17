# Android offline PS checker — developer operation

This branch contains the Android source and build path. The local component
checks run; **a compiled APK and actual Android share-flow run are still pending
hosted execution**. It is not a Play Store release. PS remains a development
preview with its independent release gates unchanged.

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

If the runner already has the reviewed API 36 Google APIs x86_64 system image,
emulator and KVM, a dedicated emulator on port 5580 receives synthetic share intents.
The test checks explicit Check, PS finding, edit invalidation, a new share/No
finding, unsupported MIME refusal, Clear and background cleanup. It never selects
a connected phone or downloads an emulator image. If those tools are absent,
`emulator.json` records `UNAVAILABLE`, `pass:false`; a green compilation job does
not turn that into device acceptance. A started emulator failing a case fails the
job. Only synthetic UI data is inspected, and the app-owned emulator is stopped.

## Acceptance still owed

- Actual current-source APK compilation and Android WebView/Share execution.
- Real Android source-app compatibility and hostile/malformed intent checks.
- TalkBack, large text, contrast and navigation testing by actual users.
- Physical-device install, startup/memory/battery, offline/update/removal evidence.
- Outside-human usability and PS's own independent accuracy/release evidence.

The native UI/schema/resource/lifecycle boundaries are separate from detector
accuracy. Android delivery failure cannot disable iOS, the website or another tag.
No original scope requirement reaches 100% from these local checks.
