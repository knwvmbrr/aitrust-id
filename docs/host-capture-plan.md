# F-160: explicit foreground host capture

Deliver the existing ORG-HOST software job: a restricted host adapter, visible
consent/pause/stop, safe version transitions, failure containment and removal.
The initial supported surfaces are one explicitly selected private UTF-8 `.txt`
file on macOS/Linux. No recursive scan, screen/keyboard/clipboard interception,
daemon, startup registration, background collection or network listener exists.
Windows and other media remain unsupported. OS coverage is measured separately.

The command requires a foreground terminal, an explicit local-capture consent
flag and an expected source fingerprint obtained from an inspected/verified
installation. It opens a dedicated owner-private directory outside Git trees,
uses descriptor-relative non-following reads, rejects sensitive directories,
links/special files, public permissions, excessive/binary/changing input, and
never prints or stores answer text. Capture-only operation needs no detector;
optional PS analysis uses the existing frozen method in a separate bounded
process. It never executes a captured command or sends data to a service.
Other tag routes remain independently usable.

Pause and reset cancel pending work and invalidate late results. Reset deletes
only owned captured metadata and stays paused. Stop ends capture; delete removes
only this session's verified generated records and stops. Input files are never
changed. Optional detailed metadata retention requires an explicit private output
directory; hashes/positions remain potentially linkable. An existing output
folder is never resumed or overwritten. A crash cannot silently restart capture.

Prepare the frozen worker from inspected current source before reading any input.
Use pipe data, bounded output/time and a dedicated child process group. Source
fingerprints are checked throughout a session. A changed version stops capture;
there is no hot update or automatic fetch. Updates require stopping, authenticating
new source with the existing source-provenance workflow, then explicitly starting
a new session with its new fingerprint/consent. A hash alone is not publisher
authentication, and local administrator compromise is outside this mechanism.

Execute actual foreground-terminal lifecycles on macOS and isolated non-root
Linux: capture/create/change, pause/resume, reset/delete/stop, source change,
permission/link/binary refusals, duplicate suppression, stale/cancelled output,
worker failure, interrupted session and independent personal checking after an
agent failure. Retain immutable source-bound evidence and focused regressions.
There are no real-user samples, company intake, new tag adoption, authorship
verdicts, detector-accuracy claims or hosted-agent service in this increment.
Only the full demonstrated software job may close F-160; security/human pilot
and institutional claims stay in their existing acceptance tracks.

Foreground ownership must remain valid throughout a session, including before
reads/results and when continuing a suspended job. Ctrl-Z stops capture; a job
forced into SIGSTOP and resumed behind the shell must refuse any new capture.
