# Private account recovery safeguard

**Working private PostgreSQL recovery safeguard.** One real synthetic sequence
completed on November25,2026; public signup, subscriptions and production
collection remain disabled or unqualified.

The safeguard prevents an older account backup from bringing a subsequently
deleted account back into the optional account service. Other accounts remain
usable. Free tag checking remains separate.

The [actual execution record](../runs/2026-11-25-account-erasure.json) binds the
source and different review. All18 command phases and12 case groups passed in
11.075 seconds. Two real synthetic accounts had password login, sessions and
nonempty history. The older27074-byte dump demonstrably restored the deleted
account's valid password/session/exact history before reconciliation; afterward
those failed while the other account still logged in and exported the exact
payload. Actual entitlement cleanup completed before the restore, proving that
the separate journal survives the original outbox's removal.

Real controls also passed for missing-metadata/migration rollback, capacity
reservation and the seven-day boundary, NULL-ready forgery, full pending-cleanup
refusal, precommit rollback and runtime privilege refusals. Owner-created filler
and simulated future SQL times were entirely rolled back; these are not4,096
human signups or seven days of elapsed observation. The receipt binds the exact
received dump, checkpointed journal and actual backend system identity.

Owned PostgreSQL was stopped; its socket and the review HTTP listener were absent. New runtime CONNECT was
revoked. Main PostgreSQL's critical snapshot remained unchanged with zero
application tables. Final retained workspace was131043328B, an additional
19554304B. Recorded idle PG PSS42634KiB is not peak usage or an enforced total
memory cap. Original review data/source remain retained; no dependency install,
new administrator credential, public service or customer charge occurred.

`tools/account_erasure.py` implements the bounded journal/checkpoint formats,
coherent snapshot capture, seven-day restore window, transactional reconciliation
and target-bound receipt checks. Migration002 adds the private journal and
reserved deletion capacity. Migration001 remains unchanged. The runtime uses
the same account domain and API, with an explicit v2 profile.

The operator CLI accepts only the approved owned synthetic workspace and two
fixed erasure database names. It cannot target the main database or accept a
caller-selected DSN. It uses the existing installed Psycopg/libpq and binaries;
there is no new package acquisition, password, credential or HTTP route.

The following approved synthetic sequence has already completed in its retained
workspace. Do not rerun it there. For any separately reviewed new run, an operator
performs this sequence
inside the already approved workspace:

1. Start the owned review cluster using its existing identity-bound tool.
2. Run `account-erasure.py bootstrap`: clone the qualified001 database, verify
   migration failure rollback, append002 and prepare private operator/runtime
   profiles. Original databases/data and source evidence remain retained.
3. Temporarily grant the synthetic runtime peer access; run the seed phase as
   `ait-intake`. It creates two accounts and nonempty metadata history through
   the actual account domain. Copy only this synthetic fixture to the operator.
4. Quiesce the source. Run the rolled-back owner SQL capacity drill, then
   `backup` while holding one exported PostgreSQL snapshot.
5. Temporarily grant the source runtime peer again and run the actual deletion
   phase. Successful entitlement cleanup must leave the erasure journal intact.
6. Quiesce the source and `export` its actual journal and selected checkpoint.
   Restore the older coherent dump into the new fixed restore database, with
   runtime CONNECT still revoked.
7. Run the before/rollback phases as `debian`: prove the deleted account's old
   password/session/history really exist in that dump. The explicit
   `probe-unreconciled` negative control temporarily permits only the synthetic
   runtime peer, checks that a forged NULL-ready file is refused, and revokes
   CONNECT in `finally`; no HTTP service runs. Check that full pending-cleanup
   capacity and an injected precommit failure roll back without a receipt.
8. Run `reconcile`. Only after an acknowledged commit is its private receipt
   copied for the runtime guard. `grant-restored` checks the operator-owned
   receipt against non-null reconciliation state, the actual received dump,
   database OID and current backend system identifier. Runtime-owned bytes cannot
   grant access. Temporarily grant synthetic restored access and
   run the after phase: the deleted credentials/data must fail, the other account
   must still log in/export and the cleanup outbox must retry successfully.
9. Run `finish`: revoke synthetic runtime access and attempt the identity-bound
   owned stop even if diagnostics fail. Verify no owned socket/listener remains
   and compare the existing main PostgreSQL fingerprints/identity/table count.

Each command uses the explicit `--workspace` path selected in the private approval.
An existing database/output refuses; no failed candidate is dropped, overwritten
or re-provisioned to obtain a pass. Do not rerun bootstrap on the retained
workspace. The source/manifest/journal/checkpoint/receipt stay private, outside
Git. They can contain synthetic session tokens and internal UUIDs. Public
records contain source digests, aggregate outcomes and limits only.

The capacity drill uses owner-created SQL filler in a rolled-back transaction.
It is not evidence of 4,096 human signups or password derivations. The actual
two-account case is reported separately. The seven-day boundary is tested before
the intentional rollback so no synthetic future clock remains committed.

If a dump, journal, selected checkpoint or receipt is missing, stale relative to
the selected checkpoint, malformed or mismatched, recovery is unavailable.
An uncertain commit may have completed: inspect the bound restored state before
an identical retry. Do not claim rollback or publish a receipt after an uncertain
response. A different checkpoint cannot overwrite an existing reconciliation.

The operator-selected checkpoint is a trust boundary. Its hash does not prove
that no later deletion exists, that an outside copy is current or that the source
is honest. Source-unavailable disaster recovery and independent journal custody
remain separate. Runtime/root/database-owner compromise is not defeated by a
local receipt.

Account deletion is the boundary of this increment. Individual history-event
deletion/clear operations require their own restore suppression before broader
deletion guarantees. No physical-media erasure, real payment, public deployment,
independent accuracy, native acceptance or original-scope closure follows.
