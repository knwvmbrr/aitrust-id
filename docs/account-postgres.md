# PostgreSQL account and private history

This backend runs the **same** reviewed `/v1/account` application and account
domain against PostgreSQL. Signup, password login, rotated sessions, CSRF,
per-owner history and the optional state filter retain the existing contracts.
Free checking is a separate service and never calls this store or entitlement
engine. No price, payment provider, checkout or public signup is activated.

`PostgresAccountStore` uses Psycopg3.3.9 pure Python and the installed Debian
libpq. It binds values separately from a closed list of inherited domain SQL;
it neither interpolates request text nor implements a custom database driver.
The small row adapter returns actual driver values with the index/name interface
the shared domain requires. No SQLite database is opened by this store.

## Source and isolated review

The qualified shared account app/store/core/UI are exact commit
`40fc0ba9142261299c38698786374984503edca9`. The new PostgreSQL files are separately
source-bound in the execution record. Fourteen runtime wheel hashes reuse the
existing gateway lock; the only new driver is Psycopg3.3.9. The closed15-wheel
server set is3437525B. `deploy/accounts/runtime-sources.json` contains exact
publisher URLs, SHA256, sizes, source-archive references and declared license
facts. All15 wheel-carried license texts were retained during the private VPS
review, including the complete7652B LGPL3 text shipped by Psycopg.

These packages are **private server prerequisites**, not an admitted public
account bundle or a new distribution scope. Their open-source facts do not
assert complete native/transitive license clearance, authorize redistribution,
or change any of the existing14 distribution routes. No wheel is installed on
the developer laptop. There is no binary Psycopg extra, compiler or model.

The functioning deployment verifier is deliberately restricted to a fresh owned
nonce under `/var/lib/aitrust-id/account-review/`. It creates a separate Unix-only
PostgreSQL18 cluster and review/restore databases; it never targets the existing
main cluster. Existing OS identities authenticate through the isolated cluster's
peer mapping. Schemaowner is NOLOGIN; the runtime actually connects as the
limited role and cannot CREATE schema/temp objects or SET ROLE to the owner.
There is no superuser connection disguised by SET ROLE.

An authorized operator stages the finite source/manifest and prepared locked
runtime into that new workspace, then invokes the root-only review tool:

```sh
python3 source/scripts/account-postgres-review.py provision --workspace "$REVIEW"
python3 source/scripts/account-postgres-review.py restore --workspace "$REVIEW"
python3 source/scripts/account-postgres-review.py finish --workspace "$REVIEW"
```

`REVIEW` must be the exact owned nonce directory. Provision refuses an existing
cluster/venv; migration refuses an existing schema, unknown target or digest.
Restore accepts only the tool's own review database and freshly generated dump,
never a caller-selected archive or database. An intentional migration failure
was proven to roll back before successful installation. No data is dropped to
make a retry pass. Existing main PostgreSQL, service units, firewall and proxy
configuration remain untouched.

The prepared runtime user can use the existing account app with the new store:

```sh
python -m services.accounts.postgres --review-http \
  --profile "$REVIEW/runtime/profile.json" \
  --entitlements "$REVIEW/runtime/entitlements"
```

Run it from the staged source through the review tool's fixed `user()` launcher,
which clears inherited variables in the child and preserves actual HOME if
present. The runner is loopback-only on127.0.0.1:18791. It rejects public-origin
configuration. The same command with `--retry-entitlement-cleanup` performs a
bounded operator outbox retry without serving HTTP or granting access.

## Security and failure behavior

Every real connection must match the selected Unix socket, database, PostgreSQL
major, cluster, server OS peer and unprivileged runtime identity. ANY inherited
`PG*` environment variable refuses before Psycopg connects; no global environment
is changed in the threaded server. A fixed absent passfile under root-owned
`/run` prevents home/password-file fallback. An existing leaf or writable parent
refuses. No password or token is a database connection parameter.

A transaction holds the singleton clock row before sampling trusted server time;
rollback refuses. Its original8-second finite/nondecreasing budget includes
connection/guards and final close. Statement timeouts are clamped to remaining
budget, at most3s; locks have1s and idle transactions5s. The unchanged app admits
two blocking operations and retains a timed-out worker's slot until completion.
This is a bounded first implementation with serialized transactions, not a
high-throughput performance claim or protection against a frozen/compromised
OS/database owner.

Accounts, sessions, history and cleanup share real atomic transactions, foreign
keys and type/size checks. Indexed expiry covers global history creation time,
session expiry/idle time and rates; an owner/sequence index supports pagination.
Existing4096-account/8192-session, owner1000-event/5MB/30-day domain limits stay
unchanged. There is no silent history eviction. Unknown SQL, invalid values,
profile/schema drift or unavailable storage refuses with fixed diagnostics.

An attempted COMMIT may have completed even when the acknowledgement fails.
`commit_uncertain` is a503; inspect current session/history before retrying.
Cancellation preserves its control-flow class and possible-completion attribute.
There is no automatic retry or false rollback claim. An identical history UUID
can be retried idempotently; a conflicting record refuses.

Entitlements are server-owned optional callbacks, initially operator grants.
A client cannot assert payment. Inactive/unavailable access blocks enable/append,
but reads, export, disabling, deletion and account removal remain available.
Account deletion commits a durable entitlement-cleanup outbox; an outage stays
pending until a bounded trusted retry succeeds. No verified payment or password
recovery is claimed; `recovery_available` remains false.

## Actual qualification and limits

The final current-source review passed11 real PostgreSQL/HTTP groups in4.391s,
including two-account signup/login/isolation, current filtered counts/cursor,
CSRF/Origin/GET binding, access revocation, idempotency/conflict, cancellation,
actual COMMIT followed by injected lost acknowledgement, and account deletion.
A real18158B dump restored a nonempty record and password login. Five further
actual checks passed for restored payload, expiry, rollback-clock refusal,
deletion outbox and recovery through a separate real access engine. Two genuine
concurrent peer transactions also passed. Injected faults are labelled; the SQL,
connections and persisted outcomes in those tests are real.

The observer initially raced an already-exited query backend; its failure is
retained. Shipped `finish()` attempts verified owned stop in `finally` regardless
of diagnostic failures, preserving the original error. Targeted tests cover
observer error/cancellation and real descriptor closure after an identity fault.
Actual final cleanup stopped the owned postmaster/socket and HTTP listener and
matched the main database's original critical snapshot with0 application tables.
The retained workspace is111292416B. Recorded idle PG PSS17816KiB is not a peak
measurement or an enforced whole-runtime RAM limit. No generic recursive cleanup
removes retained private evidence.

This is a working private PostgreSQL component and synthetic restore proof.
Public service/source qualification, production backup encryption/retention,
individual-history deletion recovery, merchant integration and collection
policy remain separate before real signup.
No full-original requirement closure, all-route permission, model/tag accuracy,
legal clearance or production collection is inferred from these checks.

## Later recovery work — November25,2026

Whole-account deletion now has a separately exercised recovery barrier. The
isolated PostgreSQL drill restored an older backup, refused the deleted account
after reconciliation and preserved the other account. Source, privilege,
rollback and cleanup checks received a different review. See the
[actual result](../runs/2026-11-25-account-erasure.json),
[integration review](../runs/2026-11-25-account-erasure-integration.json) and
[operator instructions](account-erasure.md).

That result covers deleting an entire account. Recovery after deleting one
history entry or choosing Clear history is still being qualified. The earlier
dump size, workspace allocation and memory observation above belong to their
original recorded drill; they are not current capacity or peak-memory claims.
Public signup and customer payments remain disabled.
