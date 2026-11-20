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

## Six executed controls; background failure still unresolved

[Hosted run44776757754](https://github.com/knwvmbrr/aitrust-id/actions/runs/44776757754)
matched both reviewed metadata documents, left the license record unchanged,
installed/booted the owned emulator and ran the development APK. Its first six
original controls passed: explicit-check receipt, an offline PS finding, edit
invalidation, new Share/no finding, unsupported MIME refusal and Clear. The
seventh background-clear control did not complete. The producer remains FAILED;
its generic report does not establish whether task lookup, refocusing or the UI
assertion failed. Six passes do not become seven, a physical-device result or
full runtime acceptance.

The separate diagnostic revision preserves the same seven controls, existing
commands, first task match, assertions and wait deadlines. It extracts only the
background control into a fixed-boundary helper. `control_stage` identifies
receive, HOME, task inventory, task lookup, refocus, cleared view or marker absence;
a failure publishes only its fixed `diagnostic_code`. From data already read,
the report records the task-match count and owned-UI / ready / cleared / synthetic
marker booleans. It publishes no task IDs, hierarchy dump, native error, command
output, path or input text. Those flags describe the observed hierarchy, not
proof that `onStop` completed. License/prerequisite Unavailable handling remains
unchanged. Diagnostics do not fix or claim to fix the unresolved runtime failure.

The reviewed [AOSP Android16 shell implementation](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/android16-release/services/core/java/com/android/server/am/ActivityManagerShellCommand.java)
supports `am task focus`; [ActivityTaskManagerService](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/android16-release/services/core/java/com/android/server/wm/ActivityTaskManagerService.java)
can silently return if no attached task/running activity is found. A successful
shell return alone does not establish that the expected app became visible.
No new Share/launcher intent is substituted: it could clear the editor itself
and mask a lifecycle failure. There is no added SDK retry or license acceptance.

## Earlier privacy clearing candidate

The diagnostic hosted run44778572444 again failed the original seventh fast-return
control after six passes. Task lookup/refocus returned, and its last observed
owned foreground hierarchy still contained the synthetic marker rather than a
ready/cleared message. This proves the failed privacy observation; it does not
prove that Android had delivered `onStop` (or even `onPause`) between HOME and
refocus. The exact FAILED report remains historical evidence.

The next source candidate clears through the same `wipe()` method in `onPause`
as well as `onStop`. This cancels/destroys the owned renderer, invalidates stale
session tickets and clears editor/result state as soon as the activity pauses,
rather than relying solely on a later stop. Repeated clearing is deliberate.
The on-screen privacy note describes pause clearing. Some system dialogs and
multiwindow transitions can pause a screen while it remains visible; its draft
and result will then be lost. This favors dropping private state over preserving
an interrupted draft. Keyboard display and the inline Why-this-tag disclosure
are not separate activities. This is not a promise that every focus loss on
all Android versions dispatches a pause.

The original immediate HOME→task-refocus assertion remains unchanged. No STOPPED
wait, fresh launch/Share intent, delay, assertion removal or positive result
substitution masks it. Local wiring/state controls cannot establish actual
Android lifecycle dispatch: a new source-bound hosted APK run must execute all
seven original controls before a complete runtime pass can be recorded.

## Source-bound API36 seven-control pass

[Run44779986361](https://github.com/knwvmbrr/aitrust-id/actions/runs/44779986361)
executed source `d50793165254fe666a165542624fcdc159d01293` and completed all
seven original controls on the owned API36 emulator, including the unchanged
immediate HOME/refocus check. Its final owned UI showed the cleared message and
no marker; `emulator.json` is EXECUTED / pass:true / case_count7, with no Internet
permission and an unchanged existing license record. Actual hosted JVM controls,
APK compilation, development test-signature verification and pinned-engine parity
also passed. This is a bounded synthetic emulator result, not physical-device,
real sending-app/Share chooser, human TalkBack, independent accuracy or release
acceptance. The two earlier failed runs remain failed; this pass does not retroactively
prove which callbacks they received.

The immutable receipt `runs/2026-11-20-android-pause-hosted-seven.json` binds the
exact downloaded artifact, raw reports, native build sources, current helper and
signed development test APK. Shared protocol/boundary/state integration and review
are still pending in draft PR134. No full N-014 or other original requirement is
closed by this component result. No further unchanged runtime retry is needed.
