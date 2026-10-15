# F-161 complete: organization-owned retention and audit

Codex implemented and executed the complete software job on October 15, 2026.
The [scope acceptance record](../runs/2026-10-15-organization-audit-reviewed-acceptance.json)
preserves the original job and previous acceptance text. All 202 IDs remain:
**125 complete / 77 open**, with 17 more full closures needed to reach 60.

The optional tool now supports explicit metadata/retention policies, separate
write/read/review/deletion accounts, tenant isolation, immutable append/retry,
linked corrections and reviews, checkpointed private exports, server-clock expiry,
logical deletion, encrypted physical backups and quarantined recovery using a
current separately pinned recovery authority. Personal checking runs with the
audit database stopped. No automatic upload or company-hosted intake is enabled.

[31 actual Linux controls](../runs/2026-10-15-organization-audit-reviewed-linux.json)
exercise PostgreSQL 18 and pgBackRest 2.59.3, including the documented operator
CLI, concurrent append, direct SQL admission failures, temporary-table spoof
refusal, tenant/role denial, version history, export tampering, encrypted restore,
deletion overlay, expiry, exact-label backup expiration and scratch cleanup.
[44 focused tests](../runs/2026-10-15-organization-audit-reviewed-focused.json) cover
metadata source profiles, unapproved fields, offsets, policy bounds, private-file
refusals, bounded children, CLI output safety and stale execution evidence.

The required CI checks bind these source bytes to the Linux receipt and run the
focused checks. The existing synthetic PostgreSQL workflow also executes the
complete audit drill in its own network namespace. It collects no real records.

The [operator guide](organization-audit.md) explains supported bounds and duties.
This completes F-161's software job, not a hosted business, research pilot,
certification, independent tag accuracy, actual-user acceptance or whole-host
replacement recovery. A database administrator remains trusted. Deletion is
logical; physical erasure, provider copies, WAL and external exports are not
certified erased. Recovery needs the current trusted off-host authority pin;
its timestamp alone cannot prove it is the latest. Missing newer history is
reported, not reconstructed. Other requirements and tag release gates stay open.

Automated review caught two defects before merge: a valid large recovery manifest
exceeded the SQL transport budget, and an event’s visible timestamp could differ
from its hash-protected timestamp. Both are corrected. The Linux drill now sends
a 10,000-ID recovery authority through the actual CLI/PostgreSQL path; offline
verification refuses changed/missing event timestamps even without a checkpoint.
The earlier acceptance record is preserved and superseded by the reviewed one.
