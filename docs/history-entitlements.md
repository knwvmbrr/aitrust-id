# Server-owned access to personal history

Architecture recorded before implementation, November 24, 2026. This is the
access component of the owner's optional paid-history direction. It does not
process money, choose prices, authenticate users or issue detector tags.

The account application supplies an authenticated canonical UUIDv4. It calls
`HistoryEntitlements.assess(account_id, now)` through server configuration only.
The result is the versioned `account-history-entitlement/v1` contract: account ID,
ACTIVE/INACTIVE/UNAVAILABLE, expiry and revision. No browser-provided paid flag is
accepted. ACTIVE permits the separately consented history write; account/history
reading, export, deletion and all free checking must not require this result.

The first adapter is a private operator-managed grant ledger, with an actual
grant/revoke/status/forget command. These are explicitly **operator grants**, not
verified payments or subscriptions purchased by a customer. A real payment
adapter, prices and commercial terms remain necessary before accepting money.
The module has no HTTP routes, provider secrets, network calls or tag imports.

Grant, revoke and exact event replay are serialized under an owner-only lock.
Random event IDs prevent accidental duplicate changes; replay with different
content refuses. Grant leases last at most 31 days; renewal needs a new event.
Expiry is evaluated on each use, and an observed wall-clock rollback refuses
access, including after reopening the ledger. This is not independent time or
protection against an administrator restoring an older ledger and clock.

Service integration selects its trusted clock after acquiring the ledger lock.
The optional constructor `clock` is server configuration, never a request field.
This avoids treating an earlier request timestamp as an OS rollback after a newer
operation commits. Direct integer-time callers keep strict rollback refusal.

The bounded ledger supports 1,024 accounts and 8,192 events, reserving space for
revoking every outstanding grant. Changes use private temporary files, fsync and
atomic replacement. Missing/corrupt/busy storage and write uncertainty produce
UNAVAILABLE, never free access. Account erasure removes that account and its
grant events; retained backups remain a separate operational obligation.

This private JSON adapter is for the isolated working account increment, not a
replacement for the selected self-hosted PostgreSQL production architecture.
Directory ownership protects against other users; it cannot protect a process
already compromised with the same operating-system identity. Production must
separate operator write privileges from the public application and qualify
backup, recovery, transport, abuse controls and deployment before collection.
