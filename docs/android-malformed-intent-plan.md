# Default Android APK — finite malformed Share ingress controls

Base: f5c03183b2e6176cb64a798664a5c7ee7d4a5e5a. Owner: Codex /root/share_debugger.

The selected default APK already executes seven original Share controls and two
configuration/privacy controls. Those exercise shell-created plain-text intents
and a wrong MIME type; they do not exercise Android Parcelable/ClipData transport
from a second application UID. This increment adds that finite runtime evidence,
not physical-device, arbitrary-source-app or TalkBack acceptance.

## Mechanism and owned files

- `tests/android/intent-sender/AndroidManifest.xml` and `SenderActivity.java`: a
  separate test-only, zero-permission application. A finite integer selects one
  hard-coded synthetic intent; no caller-provided text, URI or package is read.
  It explicitly addresses the existing checker, then finishes. No provider,
  upload, storage, credential, implicit recipient or new endpoint is introduced.
- `scripts/android-intent-controls.py`: compile/sign the sender with preinstalled
  SDK36/JDK tools in an owned private temporary directory; validate its zero
  permissions and exact package/component, distinct installed UID, and sources.
  Keep the sender and ephemeral key outside the default APK. Fixed diagnostic
  codes, closed boolean observations and source/artifact identities only.
- `scripts/verify-android-emulator.py`: after the unchanged original seven and
  configuration two, invoke the independent finite suite when the existing
  configuration-controls flag is true. Report under a separate `intent_controls`
  object. Existing PR/push and manual-default-true paths therefore run it without
  changing workflow, SDK/license behavior or any original acceptance predicate.
- `tests/test_android_intent_controls.py`: inert fault/privacy controls, actual
  JDK compilation against bounded Android stubs, and original-nine AST identity.
- This plan, the existing developer guide, new immutable runs and attributed
  change records. No shared state, scope, workflow, package or release edits.

## Predeclared acceptance

Nine finite invalid forms: missing text; wrong-typed text; ACTION_SEND_MULTIPLE;
EXTRA_STREAM; Intent data URI; a ClipData URI; multiple ClipData items; 20,001
BMP codepoints; an unpaired UTF16 surrogate. Every case must reach the owned
unsupported-input message with no old/current text, no tag or details and disabled
Check. The editor's hint is not mistaken for text: only exact empty or the exact
source-bound hint is accepted in the empty editor, plus disabled Check.

A fixed valid synthetic Share from the same sender must then arrive exactly,
show Received with Check enabled and no result, proving later recovery and
preventing a stale refusal from satisfying the next control. Invalid delivery is
also primed by that exact valid marker before each refusal. One original40-second
UI wait per expected state, existing bounded command limits; no retry-until-green.
The owned portrait orientation after the existing two controls is required; this
suite does not add navigation workarounds. Report each invalid/recovery pair only
after all assertions pass. A failed case remains failed with its exact completed
prefix. Original7/config2 never become evidence for unexecuted new cases.

## Risks and limits

Synthetic sending differs from a real outside app's chooser. Explicit component
routing intentionally tests the exported ingress parser, not chooser discovery.
Android may reject an invalid Parcelable before delivery; failure to observe the
expected checker refusal is FAILED, not silently counted as checker rejection.
No input program is executed. No URI provider is created or content dereferenced.
The URI strings use an inert `.invalid` authority. No provider or explicit URI
grant API is installed; Android may add its own transport flags when processing
EXTRA_STREAM. That framework transport must be measured by the actual controls.
An unpaired UTF16 string's Android transport must be measured, not inferred from
JVM tests. Existing lifecycle clearing remains unchanged. Sender compilation or
UID validation failure cannot become health success or a zero-findings result.
No default APK class, manifest, asset, permission or detector bytes are changed.

Before hosted dispatch: meaningful focused controls, exact frozen source hashes,
and distinct source review. Then one ordinary changed-source hosted path with
existing license acceptance rules, retaining all outcomes. No local SDK installs,
local emulator, terms acceptance, new infrastructure or manual unchanged reruns.
