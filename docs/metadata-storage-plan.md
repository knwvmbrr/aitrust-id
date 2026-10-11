# Metadata storage controls — architecture before implementation

Build and execute the storage portion of the proposed metadata pilot without
activating its unapproved intake, retention policy or participant permissions.
The current website continues to export local files only. F-044, F-045, F-141,
F-161 and N-011 remain open; database tests are not a running pilot or training.

Use a fresh disposable PostgreSQL cluster, its own private directory and Unix
socket, with TCP listening disabled. Never connect the test harness to the live
database. Verify server data directory, cluster marker, non-root ownership and
listener settings before installing the test schema. Abort on any mismatch.

The schema accepts only a synthetic development envelope around the current
eight-field feedback export. The synthetic flag and permission marker are required;
download permission is never participant submission consent. Reject duplicate or
unknown JSON keys, wrong types/enums, oversized input, methods outside the fixed
allowlist and unapproved formats. Store no prompts, outputs, identity, subject
hashes, spans, free text, user/device identifiers or client timestamps.

Separate non-login owner, intake, reviewer and maintenance roles. Intake executes
bounded functions only; it cannot read or mutate tables directly. Review exposes
only grouped enum counts with a five-record minimum, and maintenance can perform
expiry/restored-copy suppression without reading feedback. This is a private
access boundary, not a mathematical anonymity guarantee or a public dashboard.

Use a separate 32-byte withdrawal digest, not a subject hash. Serialize mutations
for that digest, preserve duplicate identity without overwriting answers, and
prevent withdrawn entries from being reintroduced while deletion instructions
are retained. Exercise wrong-digest isolation, expiry and restoration suppression.
The proposed 30-day record and 7-day deletion-instruction intervals are synthetic
test parameters, not adopted participant terms or proof of backup expiry.

Execute valid insertion, hostile/duplicate JSON, consent/format refusal, grants,
search-path shadowing, idempotency/conflict, deletion, expiry and restoration
controls against the actual Linux PostgreSQL binary. Repeat acceptance using the
published source before crediting integration. Retain failures and source hashes.
No participant invitation, endpoint, database credential, telemetry, policy
adoption, existing production schema or backup configuration is changed.

The design follows PostgreSQL's guidance for a fixed trusted search path and
explicit function grants: [CREATE FUNCTION](https://www.postgresql.org/docs/18/sql-createfunction.html).
Duplicate-key checks use `json` before conversion, as described by the
[JSON functions](https://www.postgresql.org/docs/18/functions-json.html).
