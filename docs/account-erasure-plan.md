# Account deletion across older backups

This is a separate recovery increment for F-044/N-010 and the personal-history
enhancement. It does not activate public signup or billing. A failure blocks the
optional account service; free checking and independent tags do not import it.

The bounded mechanism was subsequently executed once against real PostgreSQL18:
[actual source-bound result](../runs/2026-11-25-account-erasure.json). Different
review and owned cleanup passed. This architecture does not imply production
backup-policy acceptance, independent latest-journal custody or public launch.

The existing cleanup outbox is not an erasure journal: successful entitlement
cleanup removes it. Restoring an older database can therefore restore a deleted
account, password, sessions and history. The target software outcome is to remove
those restored records before account access resumes, while preserving another
account and pending entitlement cleanup.

Append migration002; preserve migration001 and its digest. The explicit v2
profile names both identities, the database generation and its source/restored
purpose. Legacy v1 profiles keep the old seven-table contract. They cannot
silently accept the v2 schema. A restored v2 runner also requires a private,
target-bound serving receipt.

The actual current backend's system identifier is read and hashed; a copied
generation/receipt cannot substitute for it. Only the two new review databases
grant the existing runtime role EXECUTE on the read-only built-in
`pg_catalog.pg_control_system()`. No role membership or main-database privilege
changes. Restore explicitly reapplies that narrow grant rather than assuming a
user-data dump carries a modified built-in function ACL.

Two owner-controlled tables hold a minimal journal and its sequence/coverage
state. AFTER INSERT reserves a future deletion slot; AFTER DELETE transfers that
slot into the journal in the same transaction. Locked counters maintain
`reserved_live + retained_rows <= 4096`. A conflicting ignored insert cannot
reserve a phantom slot. Capacity restricts new signups without consuming the
reserved deletion slot of an admitted account. Migration takes the existing
metadata writer lock and exclusive accounts lock before counting existing rows.

Security-definer triggers have a fixed search path and qualified identifiers.
The real runtime role cannot edit/truncate the journal, change counters, execute
its trigger functions directly, disable the triggers or assume their owner.
Recovery is an owner-only transaction that disables only the named deletion
trigger while applying an already validated journal, re-enables it and commits
all changes together. There is no request/session setting that bypasses it.

A coherent backup uses one exported PostgreSQL snapshot for its dump and
generation/sequence manifest. A separately selected operator checkpoint binds
the expected journal bytes and head. Reconciliation refuses missing ranges,
wrong generation, incompatible migration, future/backward time, oversized input
and a backup older than seven days. It atomically removes post-backup deleted
accounts, cascading sessions/history; clears audit references; restores pending
entitlement cleanup; and applies active-history expiry. A failed or uncertain
commit produces no serving receipt.

Checkpointed raw bytes must parse to exactly the validated journal dictionary;
binding an unrelated byte string is insufficient. Restoration records the actual
dump digest in runtime-read-only database state. Readiness requires a non-null
reconciliation SHA and positive time, strict receipt types and actual target
bindings. The operator-owned receipt/current database authorize CONNECT; a
runtime-owned file cannot. Both live-plus-journal capacity and the unchanged
live-plus-pending-cleanup domain capacity must pass before commit. A full outbox
refuses and rolls back, preserving every pending deletion action.

The journal holds only internal account UUIDs, sequence and deletion time. These
are private identifiers. The operator can prune entries strictly older than
seven days while recording the pruning floor; exactly seven days is retained.
This is safe only when all accepted recoverable backups obey the same maximum
age. It does not destroy database pages or independent copies.

The repository's backup generator selects two full backup sets; its schedule
selects weekly full backups and daily differentials. That is **not evidence of
a seven-day expiry**, nor a fresh observation of the server. The existing
metadata pilot has a separate approved 30-day active/seven-day encrypted-backup
contract. This synthetic account drill does not silently reuse that policy or
change production backup configuration. Actual expiry, latest-journal custody,
encryption, source-unavailable recovery and applicable policies remain gates
before public account collection.

A hash establishes exact bytes, not whether an operator selected the latest
complete journal. The synthetic checkpoint comes from the actual quiesced source.
Independent replication/latest-checkpoint custody is not claimed.

The proposed real drill reuses only the existing owned stopped PostgreSQL18
review cluster and installed fifteen-wheel runtime. It clones the qualified001
review database into a new fixed erasure-review database, preserving inherited
synthetic data, then appends002. A second new database receives the actual older
dump. No original review database, migration001, main service/configuration,
dependency, credential or public route is replaced. Exact source and remote
commands require separate review before execution.

Acceptance requires actual missing-metadata and precommit migration rollback;
real runtime privilege refusals; coherent backup before deletion; real account
deletion followed by successful entitlement cleanup; proof that the older dump
contains the password/session/history; failed reconciliation without partial
removal; successful reconciliation with the other account intact; capacity and
expiry controls; and verified owned cleanup with unchanged main PostgreSQL.
Inert parser/process tests do not establish those PostgreSQL outcomes.
