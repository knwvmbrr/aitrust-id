# Configuration-only review draft handoff

The final diagnostic wave positively captured one failed first receive: SEND was
accepted, then Android paused/stopped/destroyed the activity with configuration-
changing true. The replacement received consumed MAIN and showed Ready. Two other
hosts passed seven controls. Preserve the failed aggregate and all three outcomes;
this establishes that failure's mechanism, not every older untraced failure.

Use the framework's in-process nonconfiguration instance channel. A bounded,
one-use `ConfigurationDraft` holds only current valid review text. It contains no
result, ticket, renderer or reference to an activity/view, and has no static text
cache or serialization. Keep the launch intent consumed as MAIN. Do not save text
in a Bundle, file or preference, retain caller extras, suppress configuration
changes, delay delivery or weaken any original control.

At configuration pause, capture current text only if changing configuration, not
finishing and not user-leaving. Always wipe old UI/session/result and stop the
renderer. Configuration stop may preserve that pending holder; ordinary stop
discards it. Retention transfers it once, nulling old pending ownership. The
successor consumes/empties it once only for MAIN; a new SEND or unsupported intent
discards the old holder. Repeated recreation captures the current edited text.
There is no automatic Check or restoration of an old finding.

Explicit Clear/Done/new intent and user-leave hints revoke pending or not-yet-
consumed transferred holders. The old instance keeps a revocation reference only
until destroy; destroy clears still-owned pending data but must not clear a
transferred holder or a new session. Early leave hints must clear without touching
unbuilt views. A successor paused/stopped by HOME during transition wipes/discards
before later refocus. If no holder survives process recreation, no draft is
restored by this mechanism. OS-held original caller intents and forensic erasure
remain outside the guarantee; no process-death persistence is introduced.

Android16 ActivityThread sets changing-configuration before relaunch pause, retains
nonconfiguration instances after stop, then destroys the old activity. Its actual
source and the captured trace support this ordering. The system remains responsible
for callback delivery. HOME/configuration ordering and interruption are principal
risks, so a modeled lifecycle pass alone is insufficient.

Before one reviewed hosted candidate, execute exact production method-body JVM
controls for transfer/one-use/current edits/repeated configuration, clear/new SEND,
unsupported replacement, HOME before and after transfer and on a new instance,
no-holder recreation and stale old result refusal. Keep the seven existing real
Android assertions unchanged. The default APK additionally needs two separate
controls: forced display recreation preserves the current edited review text with
no finding; forced configuration immediately followed by HOME and the original
fast task refocus does not revive text. No post-rotation wait may hide that race.
These are separately reported checks, not replacements for the original seven.

Update privacy copy to distinguish a display rebuild from actually leaving the
screen. No startup-reliability, physical-device, human, accuracy or full original
requirement closure follows from a bounded emulator execution.
