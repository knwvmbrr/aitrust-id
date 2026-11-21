# Native Android OS chooser — bounded continuation

Owner: Codex /root/share_debugger. Isolated base is reviewed PR140 source
3941603265c763de07d9f7d91e465e0832db39d1. The PM owns its merge/publication and
all shared inventories. No root checkout or global scope/state change is owned.
This is further N-014 engineering, not a new original closure or task-count claim.

## Gap and user outcome

All existing seven Share, two configuration and nine malformed/refusal/recovery
controls address the checker component explicitly. They do not operate Android's
actual Sharesheet. Exercise that missing route using a separate fixed synthetic
source UI: tap Share, choose AI Trust ID in the system chooser, receive the exact
sample, explicitly Check, then read the real offline PS finding. Also exercise
cancellation without replacing a checker intent or hiding a retained sample.

## Architecture before edits

- Add `tests/android/intent-sender/ChooserActivity.java` to the separate existing
  zero-permission test APK. It has an isolated singleTask task affinity, a native
  button and a code-owned two-use sample counter. Its UI never accepts caller
  input or editable text. A button click creates an **untargeted** ACTION_SEND
  text/plain Intent and invokes Intent.createChooser. Only fixed synthetic text
  is present. The target Intent uses FLAG_ACTIVITY_NEW_TASK so the checker stays
  in its own task when the source is refocused; no new component is forced.
- The first sample is a fixed download-and-run string to be inspected, never
  executed. The second uses a distinct fixed cancellation marker. No arbitrary
  subject, URI, component, endpoint, file, provider or permission is accepted.
  Source onResume exposes only fixed ready/counter states, including actual
  return from the chooser. No general intent/dump capture is introduced.
- Extend only the existing test-APK builder's finite source list/compilation to
  include this class, and reject its class marker in default-checker DEX. Keep
  SenderActivity and its existing 19-dispatch contract unchanged. The production
  manifest, native classes, runtime assets, signing and permissions stay intact.
- Add `scripts/android-chooser-controls.py`, loaded lazily by the existing emulator
  verifier after the unchanged seven/two/nine groups when configuration controls
  are enabled. Report two separate cases. Existing runner/SDK/license/profile,
  original assertions and deadlines stay unchanged; no workflow edits here.
- Add focused `tests/test_android_chooser_controls.py`; minimally update existing
  test-APK manifest/source-list controls. Guide, immutable receipts and attributed
  events are owned; global build/CI/capability registration remains PM-owned.

## Two mandatory cases

1. Observe the source's fixed native button, press it, then positively observe
   a system chooser and the registered AI Trust ID target. Use actual native
   node bounds to select that target, never launch the checker directly. Require
   the exact first sample, Received, enabled Check and no result before Check.
   Tap Check and require the existing real offline PS result/tag. Capture the
   actual resumed checker task privately using a strictly bounded API36 activity
   schema; ambiguous/missing state refuses, with no task IDs or dumps exported.
2. Refocus the separate source task, observe fixed ready/counter state, press the
   same native button and observe the real system chooser again. Press Android
   Back to cancel. Require source onResume's second ready state with no checker
   UI. Refocus the captured existing checker task directly, without a new MAIN or
   SEND intent, and require Cleared, empty/exact-hint editor, disabled Check and
   no result or cancellation marker. This must not erase input through a verifier
   launch. Selected observations establish the bounded cancellation outcome;
   they do not promise erasure of an OS-held caller Intent or all future events.

All source/checker/system node searches are exact, finite and package-bound.
Unknown chooser layout/target/task/density is Unavailable/FAILED, not a fallback
component launch. Use existing40-second per-state waits and bounded command calls.
Export only fixed stages/booleans/counts and public source identities; never raw
hierarchies, task numbers, sample text or hashes of submitted content.

## Risks, proof and limits

The actual task affinity/NEW_TASK interaction, chooser target accessibility and
Back behavior must be measured on the existing owned API36 hosted emulator, not
inferred from JVM stubs. Preserve all original seven/two/nine checks. Inert models
cover direct-launch bypass, stale/foreign chooser target, missing target, wrong
sample/automatic result, missed source return, ambiguous captured task and marker
revival after cancellation. Existing JDK can compile fixed source/stub controls;
that is not Android runtime evidence. Distinct source review precedes one
changed-source ordinary hosted workflow run; retain every failure, no unchanged
retries or raised deadlines. No local SDK/emulator install or new terms.

This does not establish physical-device, real third-party sending-app, TalkBack,
outside-human, independent detector accuracy, Play signing or full N-014 acceptance.
No original criteria, method bytes, public tag mapping or paid feature is changed.

## API/source review and finite local controls

The official task guide documents taskAffinity selection under NEW_TASK. API36
AOSP Task.dump emits `topResumedActivity=` and ActivityRecord.toString supplies
the owned component/task boundary. ActivityManagerShellCommand.runTaskFocus calls
setFocusedTask without creating a new activity intent. The helper accepts only
one exact owned resumed record; missing/ambiguous/foreign/historical records
refuse. No dump or numeric task identity is retained in a public report.
References are linked in the developer guide. Source/API reasoning supports the
design; the actual OS chooser/task interaction remains a separate hosted gate.
