# Next independent component: encrypted synthetic backup retention and recovery

Architecture before implementation, 2026-10-12. Continue past participant and
physical-phone gates without changing production databases, services or secrets.
Use a disposable PostgreSQL cluster and encrypted pgBackRest repository inside
a fresh non-root Linux network namespace; socket-only connections. Generate an
ephemeral repository cipher key only for invented fixtures, never an account or
remote authentication credential. Existing dedicated staging access is sufficient.

Create one invented record, archive a completed full backup, restore that exact
set into a new cluster and verify it. Delete the row, complete a second full
backup and independently restore the new set; verify the row is absent from SQL.
This demonstrates why deleting a current row cannot silently erase a retained
older backup. Explicitly expire the older full set under a test-only retention
policy, show that restore of its exact label refuses, and prove the retained set
still restores. Exercise wrong cipher key and corrupted-copy refusal; no bypass.

Guard ownership, exact private temporary paths, no TCP, separate namespace,
execution timeouts, cluster shutdown and exact staging removal. Bind actual
pgBackRest/PostgreSQL executable versions and source hashes. Logs stay private;
public results contain control statuses and digests only. Reuse existing source
private-file and network guards where their contract applies.

Logical SQL absence and an expired named recovery path do not prove physical
media erasure, deleted-page contents, provider snapshot deletion, every independent
copy, legal retention acceptance or hostile-root safety. Synthetic encryption and
retention controls do not complete a production replacement-host recovery or
a recruited pilot. N-011/F-073 remain subject to their existing full acceptance.

Risks: archive delivery races, recovery parameter inheritance, backup-label time
resolution, mutable working repository and subprocess reaping. Use completed
backup labels, bounded explicit checkpoints, safe independent copies and a
finally cleanup of only owned clusters/directories. Do not install a package or
change host service configuration to make the test pass. Refuse if binaries or
namespace capability are unavailable and move on.

Promotion requires a root preflight using the existing restore namespace guard,
then irreversible drop to an existing ordinary account, no supplemental groups,
no-new-privileges and zero effective/permitted capabilities. Keep only the trusted
preflight namespace identity internally; accept no caller namespace-proof bypass.
All config-consuming pgBackRest commands, including the archive child, use the
explicit private config plus an empty private config-include directory. The version
command accepts neither config option and uses its option-free interface. Child
environment is minimal; psql uses /dev/null as its password file and never prompts.
Register owned clusters before attempting startup so timeout cleanup cannot omit
a server that started just before its launcher failed. Failed cleanup cannot claim
success or remove a running owned database directory. Publish only sanitized
statuses/source hashes; optional raw logs remain private and outside the checkout.

Protected-review correction, before refactor: KeyboardInterrupt/SystemExit
must remain cancellations after owned cleanup, never become a control result or
an unset-variable failure. Remove the return from the cleanup finally block.
Retain the original cancellation if cleanup is interrupted again, attempt the
other owned stops, and leave any unresolved active cluster directory intact.
Test interruptions before startup, after registration/start, repeated cleanup
cancellation and SystemExit; no real or production database in those unit tests.
