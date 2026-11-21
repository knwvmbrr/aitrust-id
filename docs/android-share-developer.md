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

- Broader Android WebView/Share compatibility and stability beyond selected synthetic emulator controls.
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


## Configuration handoff and default APK nine-control pass

The finite diagnostic study observed an accepted SEND followed by an Android
configuration rebuild: the old screen consumed its intent to MAIN, cleared on
pause, and the new instance received MAIN with no draft. That positive trace
establishes this particular loss mechanism; other earlier untraced startup
failures remain unexplained. Failed study and candidate reports remain immutable.

The default screen now offers one bounded, one-use in-process draft to Android's
nonconfiguration handoff. It retains current review text only: results, engine
instances and session tickets are invalidated. There is no text Bundle, disk,
static cache or replacement SEND intent. Retention is optional and process death
loses the draft. Fresh/unsupported intents, Clear, Done and real leaving revoke
pending drafts; HOME also clears through the leave hint. The privacy note says
screen changes *can* keep a draft and leaving clears text and results.

[Run44881591785](https://github.com/knwvmbrr/aitrust-id/actions/runs/44881591785)
executed frozen source `3706f99294d4f0872ee87721d1dfbcd8cd965362` using the
**default**, development test-signed API36 APK, with diagnostic instrumentation
disabled. All seven original Share controls and both separate configuration
controls passed. The latter observed the exact edited draft after rotation,
Received with no result, then reasserted that exact draft; a fresh Share was
positively observed before immediate rotation→HOME/refocus, which showed Cleared
and no synthetic marker. The checker still requires an explicit Check. The
report records actual postgesture motion, rather than inferring delivery from
successful shell commands. The prior failed offscreen/setup candidates remain
failed and are not substituted for this execution.

The immutable receipt `runs/2026-11-21-android-default-configuration-nine-pass.json`
binds the downloaded artifact, original ordered seven, separate two, native
sources, current helper/workflow and test APK. The APK's diagnostic probe markers
are absent; its manifest has no Internet permission. The existing license record
was unchanged. Hosted controls also ran 88 focused tests and the existing engine
parity checks. Normal PR/push default-APK jobs now require the same two additional
configuration controls automatically; manual diagnostic variants remain separate.
No unchanged runtime rerun is needed for this selected result.

This is bounded synthetic API36 emulator evidence. It does not establish all
startup paths, external sending-app/chooser compatibility, physical devices,
TalkBack or outside-human acceptance, independent detector accuracy, Play release
readiness, or a full original requirement closure. No original scope percentage
is changed by this record.


## Finite synthetic external-UID ingress controls

The existing original seven and configuration two remain separate, unchanged
controls. With `--configuration-controls`, the verifier now subsequently builds a
**separate synthetic sender APK** using only the existing SDK/JDK, signs that
fixture with its own disposable CI key and installs it on the owned emulator.
No sender class, manifest, asset or probe is added to the default checker APK.
Both apps have zero requested permissions, and their installed UIDs must differ.

The sender accepts only a fixed integer selection, never caller text, URI,
recipient or code. Nine hard-coded invalid forms cover missing/wrong-typed text,
SEND_MULTIPLE, stream/data URI, URI/multiple-item ClipData, over-limit text and
unpaired UTF16. Each must produce the owned unsupported-input message, empty or
exact-hint editor, disabled Check and no result. A fresh exact synthetic valid
Share is required after every refusal. A stale refusal, old marker, arbitrary
editor hint or merely successful shell return cannot count as a pass.

New results live in the separate `intent_controls` object. Only completed
invalid/recovery pairs are counted; fixed diagnostics and closed boolean flags
replace raw errors, app dumps, payload text, URIs, private paths and UID numbers.
The existing40-second per-state UI deadline and original nine acceptance paths
are unchanged. These controls run on ordinary PR/push default-APK jobs because
that existing path enables configuration controls; no workflow or SDK/license
rules change. Sender source/DEX/permission drift, equal UID, wrong orientation,
build/install failures or missing UI assertions fail this extra suite and cannot
turn it into a zero-findings result. The dated execution below records the selected hosted outcome; UI/schema
controls alone are not Android runtime evidence.

Explicit component addressing tests exported Android intent/Parcelable ingress.
It does not test real third-party chooser discovery, every sending app, physical
phones, TalkBack, independent accuracy or full N-014 acceptance. No URI provider
is installed, no caller input is executed or uploaded, and no SDK/terms are
installed or accepted locally. The fixture APK and disposable key use an owned
private temporary directory and normal cleanup; a host cleanup failure remains
a failure rather than a claim that private files were necessarily removed.


The first sender candidate, run44888523549, passed the unchanged original nine
but completed zero new pairs: missing-text refusal was not observed and the old
valid marker remained. That failed report stays failed. It did not capture the
sender callback, so it does not prove either malformed checker acceptance or a
particular task-reuse cause. The corrected test-only sender remains singleTask,
processes the fresh onNewIntent argument explicitly and consumes its incoming
selection. Before every checker assertion, the driver requires the next exact
bounded dispatch counter, requested selection and START_RETURNED from a one-use
closed sender frame. The frame contains no arbitrary intent fields, text, URI,
UID, task ID or paths and clears its pending enums after export. Stale/missing
callback data remains a failed case. A returned start alone still cannot satisfy
the checker refusal or fresh recovery assertions. Default checker/source and
original nine control paths remain unchanged; the selected execution below
measures the corrected sender.


[Run44889760925](https://github.com/knwvmbrr/aitrust-id/actions/runs/44889760925)
at `c5f6204f37bdf94ed7192bddec8428223eed21f0` executed the **default** checker
APK and completed original7 + configuration2 + all9 invalid/refusal/recovery
pairs on the owned API36 emulator. Nineteen exact advancing sender receipts
showed CREATE for the first valid selection, then NEW_INTENT with each requested
selection and returned start. Every malformed form separately reached the
owned unsupported-input state with disabled Check/no result, followed by exact
valid-marker receipt with enabled Check/no result. These UI assertions, rather
than start returns alone, establish the selected parser/refusal outcomes.

The sender had a different installed UID and zero requested permissions. The
actual checker DEX excludes sender and intake-probe markers; all14 native source
hashes are unchanged from published basef5c03183. The method remains pinned,
Internet permission is absent and the existing SDK license record was unchanged.
Hosted88 existing tests and canonical137 +3 invalid parity controls passed. The
new14 focused groups ran locally on existing Python3.12/3.13 with the installed
JDK21; they are not claimed as additional hosted test execution. No local SDK was
installed and no extra terms were accepted.

`runs/2026-11-21-android-malformed-intent-hosted-pass.json` binds all29 source
inputs, the single downloaded artifact, raw reports, default test APK and19
finite dispatch receipts. A different reviewer checked that same retained
artifact without another runtime or download. The first failed producer remains
failed; its task/callback cause is not retroactively proved by this pass.
The separate temporary sender APK is represented by its actual build/source/hash
and runtime report; it is not included in the uploaded checker-APK artifact.

Protected root integration remains separate. These finite synthetic API36
results do not close N-014, arbitrary-app chooser compatibility, physical-device,
TalkBack/outside-human, independent accuracy, broad startup or store-release
acceptance. Do not rerun this unchanged candidate to accumulate passes.

To run the focused fixture/driver controls with an existing JDK selected through
JAVA_HOME: `python3 -B -m unittest discover -s tests -p test_android_intent_controls.py -v`.
The existing licensed hosted verifier path uses `--configuration-controls` to
run the original nine first and then this separately reported finite suite.
