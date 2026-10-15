# Organization-owned audit storage — F-161

Implement the complete original retention/audit software job, including approved
fields, explicit policy acceptance, tenant/role boundaries, immutable record
versions, review/correction events, export, retention/deletion and actual encrypted
backup/restore controls. This is an optional organization-operated tool, not a
company-hosted intake service, research collection, certification or tag release.
Personal checking and personal exports remain free and independent.

## Data and operation

Use a dedicated PostgreSQL 18 database with a separate schema and no application
HTTP endpoint. The operator supplies existing PostgreSQL service credentials;
TCP connections require verified TLS, while a private Unix socket is supported.
Installation never creates passwords or changes a production database implicitly.
The administrator must explicitly select record retention, audit-marker retention,
backup age and the exact metadata profile before enrolling existing database
principals. No historical 30-day default is adopted. Writers/readers/custodians
are separately admitted; the database derives the tenant from authenticated
session identity, never from a caller's claimed tenant identifier.

An offline preparation command accepts supported versioned result exports and
produces a closed metadata record for preview. No answer text, free-form notes,
credentials or arbitrary source attachments enter storage. Retained fields cover
source/result digests, method/normalization identities, result states, tag codes,
reported scores/positions and procedural redaction counts. These are potentially
linkable identifiers, not anonymous data. Source authenticity, accuracy and human
identity are not established by storing metadata. Historical incomplete fields
remain explicitly absent; nothing is reconstructed or silently upgraded.

An append requires the exact current policy fingerprint. Identical retries are
idempotent; conflicting content cannot replace a record. Supersession links a new
record to the previous retained record while preserving it. Reviews append a
fixed-choice decision/reason with the authenticated database principal, without
rewriting detector output or asserting that the principal is an independent
person. Each tenant has its own ordered hash chain and exportable checkpoint.
A separately retained checkpoint can detect later changes; a database admin can
rewrite local history, so an unchecked checkpoint is not independent witnessing.

Retention uses server time. Removal deletes retained metadata and leaves only
the declared audit marker until its separately selected audit retention expires.
Exports distinguish retained, superseded and unavailable predecessors. Backup
retention is disclosed separately: deleting a current SQL row does not erase old
encrypted backups. Restore must use the current retained deletion/expiry controls
and refuse stale/missing controls rather than resurrect a withdrawn record.
Full replacement-host recovery remains its separate operating requirement.

## Risks and acceptance

Use closed input grammars, bounded reads/output, fixed SQL function names, no shell
execution, fixed search paths, revoked public privileges, least-privilege roles,
forced row isolation and per-tenant serialization. Do not expose SQL diagnostics
or reflect refused input. Read-only verification/export cannot grant tag accuracy,
certification, identity, permission or independent transparency. No real records
are collected by development verification.

Execute the actual CLI and PostgreSQL functions on an isolated Linux development
cluster with invented records plus a real checker-produced development record.
Exercise policy refusal, direct SQL validation bypass attempts, cross-tenant and
cross-role denial, retry/conflict, concurrency, version lineage, review, export,
external-checkpoint tampering, expiry, deletion, encrypted backup/restore and
cleanup. Stop the optional store and prove standalone personal checking still
runs. Bind the results to executed source bytes. Only a complete demonstrated
workflow earns F-161 completion; document or component success is insufficient.
Do not silently close F-044/F-045, N-005, research, operating governance or any tag.
