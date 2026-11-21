# Bounded Share intake investigation

The fixed three-host study executed the original seven controls on two hosts and
failed before the first case on the third. The failed hierarchy showed the owned
Ready screen; its editor nonempty flag may describe the hint, not submitted text.
The event-ring query returned no matching records. This does not establish that
Android did not call the activity.

## Hypothesis and deterministic boundary

`CheckActivity.receive` replaces its consumed SEND intent with MAIN. Android 16's
`ActivityThread.handleRelaunchActivityInner` explicitly preserves `activity.mIntent`
when rebuilding an activity. Replaying that framework handoff against the actual
production receive method can therefore produce Ready after an accepted SEND.
This establishes a possible transition, not the historical failure's cause.
Neither APK installation nor the first explicit driver command launches MAIN.
The reviewed AOSP UI hierarchy dump command contains no rotation operation.

Before changing privacy or lifecycle behavior, collect positive provenance from
the exact owned activity. Keep production intake, renderer and clearing code
unchanged. An explicit diagnostic build compiles the production activity as an
internal base with only its class declaration renamed, and a small subclass under
the original component name. The default build compiles only the original class
and excludes the diagnostic subclass. Record that distinction in the build report.

The subclass keeps at most 32 finite callback observations in process memory:
callback/action/status enums, local instance ordinals, actual editor-nonempty and
configuration-change booleans. It accepts no arbitrary diagnostic values and
records no text, text hashes, extras, URI, external identifiers or paths. One exact
argument to Android's existing activity dump operation emits only a closed frame;
the helper retains only a strictly parsed bounded frame. No logs or storage are
added to the app, and no permissions are added. A process restart loses this trace
and must not be interpreted as evidence that earlier callbacks did not occur.

Read the frame once after the first receive observation, on both success and
failure. Keep all seven original predicates, commands and wait deadlines. A
missing or malformed probe remains explicitly unavailable; it grants no test
acceptance and cannot mask the primary failure.

## Risks and acceptance

The diagnostic subclass and one bounded read add instrumentation overhead, so a
passing trace cannot certify production reliability or explain earlier failures.
The trace can distinguish SEND/MAIN delivery, in-process recreation and actual
editor/status state from an accessibility hierarchy. It cannot reconstruct events
before process restart or prove why a platform configuration change occurred.

Focused controls must verify default/probe source selection, unchanged production
method bodies, bounded/private parser behavior, pass/failure collection and
failure isolation. A JVM execution of the production receive body is explicitly
not an Android-runtime execution. Review the frozen candidate before one changed-
source hosted run; retain its entire outcome and stop if the cause remains unknown.

Do not retain raw SEND extras to replay after leaving the screen, persist input,
skip pause/stop clearing, add blanket configuration handling, wait for STOPPED,
send a replacement intent, or change the immediate background-return assertion.
Any product correction requires positive provenance and a separate bounded plan.

Primary source: [Android 16 ActivityThread](https://android.googlesource.com/platform/frameworks/base/+/refs/heads/android16-release/core/java/android/app/ActivityThread.java),
`handleRelaunchActivityInner`; [Activity.dump](https://developer.android.com/reference/android/app/Activity#dump(java.lang.String,java.io.FileDescriptor,java.io.PrintWriter,java.lang.String%5B%5D)).
