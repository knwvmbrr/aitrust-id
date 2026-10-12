# Backup retention — executed component result

Codex, 2026-10-12. Seven actual encrypted pgBackRest/PostgreSQL control groups
passed on an isolated Linux process using invented records. Four separately
restored clusters verified row presence or absence; wrong-key, damaged-metadata
and expired exact-label restores refused. All owned clusters stopped and their
temporary directory was removed. Staged source hashes stayed unchanged.

The tested environment was PostgreSQL 18.6 and pgBackRest 2.59.3. The process
verified the network boundary as root, then irreversibly ran the database work
as an ordinary existing account, with no-new-privileges, no supplementary groups
and zero effective/permitted capabilities. Both external connection attempts
were refused. This is not an independent attestation against a hostile root user.

Seven separate real command-line controls refused ordinary execution, the host
network namespace, a root target account, an unknown account, optimized checks,
unknown private arguments and an added network interface. No report or project
bytecode cache was created by those refusals. A source-bound repeat covers the
current launcher; the earlier result is retained as earlier evidence.

Failures are preserved. An early namespace probe could not read the initial
process identity after dropping privileges; the trusted root preflight fixed
the ordering. The version command rejected configuration flags before database
startup; its documented option-free interface is now used. A successful first
database drill still failed staging cleanup because root imports had created
bytecode directories. Disabling bytecode writing before imports fixed that
boundary; only the exact owned staging directory was removed. None of these
attempts changed production data or configuration.

The first local combined source-coverage check ran before this result document
existed. It refused the missing required source; the guard tests themselves
passed. The missing document is supplied before the next source-bound run.

Evidence:

- [Actual encrypted controls](../runs/2026-10-12-backup-retention-ordered-linux.json)
- [Current source-bound command-line refusals](../runs/2026-10-12-backup-retention-ordered-refusals.json)
- [Earlier command-line refusals](../runs/2026-10-12-backup-retention-early-refusals.json)
- [Retained cleanup failure](../runs/2026-10-12-backup-retention-cache-failure.json)
- [Retained setup refusals](../runs/2026-10-12-backup-retention-setup-refusals.json)
- [Operator instructions](backup-retention.md)

N-011 and F-073 remain at 60%. Accepted collection terms, real authentication,
consenting pilot, incident response and complete replacement-host recovery
remain separate full-job requirements. Logical SQL absence and an expired
recovery label do not prove physical erasure or deletion of every independent
copy. No participant data, new endpoint, production change or full requirement
closure is credited. All 202 original records remain; 115 complete, 87 open.

The initial full-suite run also caught a test-process side effect: a rejected
namespace check set the process umask before refusing, affecting a later file-mode
test. The namespace guard now runs before changing umask, and its regression
forbids that state change on refusal. The failed run is retained; current-source
Linux controls are rerun after this correction.

Protected review found cancellation could read an unset failure variable, while
a return in finally could suppress the cancellation. The corrected cleanup
preserves the original KeyboardInterrupt/SystemExit, including a second cleanup
interruption, and retains unresolved active directories. All 21 selected safety
tests, including four mocked-process interruption regressions, passed on isolated
Linux; these unit tests start no real database. The four Linux-specific tests are
explicitly skipped on macOS, where 76 other focused checks pass. The corrected
source separately passed all seven actual encrypted controls and seven early
refusals again. Source hashes and staging cleanup passed.

[Current Linux interruption regressions](../runs/2026-10-12-backup-cancellation-linux.json),
[current encrypted controls](../runs/2026-10-12-backup-cancellation-encrypted.json),
[current early refusals](../runs/2026-10-12-backup-cancellation-refusals.json), and
[retained review finding](../runs/2026-10-12-backup-cancellation-review-finding.json).
