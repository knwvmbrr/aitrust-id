# F-160: foreground host-file software

Codex implemented the [bounded file adapter](host-capture.md) and executed
19 actual foreground-terminal controls separately on macOS and non-root Linux.
Linux ran with only loopback in an isolated network namespace. The source-bound
[macOS](../runs/2026-11-06-host-capture-final-macos.json) and
[Linux](../runs/2026-11-06-host-capture-final-linux.json) records cover capture changes,
consent/source/TTY refusal, pause/reset/delete, invalid/private paths, failed or
hung workers, late-result cancellation, ordinary interruption, forced parent
death, source changes and separate checker operation. Two evidence guards reject
stale sources, missing controls and claims of human/accuracy acceptance.

The original [acceptance](../runs/2026-11-06-host-capture-final-acceptance.json) is
preserved. One full software requirement closes: **126 complete / 76 open**,
all 202 IDs intact, 16 closures to reach 60. ORG-HOST remains at 80%: managed
deployment still requires independent security review and actual-user acceptance.
No research collection, raw text storage, background daemon, privileged capture,
new API endpoint, paid service, proposal adoption or tag release is enabled.

The first development run found a missing context-manager interface in two
private-file tests and a macOS process-group cleanup refusal in a worker test.
The interface is implemented; cleanup retains the exact child handle and uses
that handle when group signaling is denied. Subsequent OS runs passed. Draft
cancellation, command buffering and optional-detector coupling were corrected
before accepting the completed implementation.

A final privacy review reproduced a gap in the first PR head: its optional journal
could be created inside another Git checkout. The corrected adapter refuses any
checkout destination before writing. Both 17-control OS runs were repeated on the
corrected source; the earlier receipt remains in history and is superseded.

GitHub review also reproduced foreground capture after a stopped job resumed
with `bg`. The adapter now checks foreground ownership throughout and cancels on
job-control loss, including a pending terminal read. Ctrl-Z deliberately stops
instead of suspending capture. Two actual Bash job-control cases raise the final
control count to 19 per OS. Both OS runs pass on the final corrected source;
initial and intermediate receipts are historical, not current acceptance.
