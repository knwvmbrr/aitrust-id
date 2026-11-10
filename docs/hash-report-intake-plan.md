# Private hash-report intake

F-045 names hash-only reporting intake. Keep it separate from the unadopted
public registry, public moderation (F-135/N-005), research collection (N-011)
and organization audit history (F-161). Implement an explicitly operator-owned
local software inbox; add no endpoint, scheduled service or company collection.

Accept only a closed feedback record: format, subject SHA-256, method SHA-256,
implemented tag code and fixed feedback category. A hash is linkable metadata,
not anonymous data or proof of the source. Feedback is always unverified and
never a training label. Reject original/redacted text, arbitrary notes, identity,
credentials, positions, URLs, extra fields and duplicate JSON keys.

Preview without writing. Explicit storage consent is required on each intake.
Use a private new local directory and SQLite transaction for bounded storage,
deduplication, expiry, ticket withdrawal and explicit metadata export. Duplicate
submissions must not refresh retention. Inspect the fixed schema, use parameterized
SQL, disable trusted-schema behavior and disk temporary data, and refuse unsafe
file ownership, links, foreign members and malformed database records.

Expiry is enforced on access and prune; an unused powered-down inbox is not a
wall-clock deletion service. Disclose logical deletion, exported copies and backup
limits. Do not claim that this local utility fulfills a future hosted registry's
retention or moderation promises. No automatic forwarding or background process.

Verify real CLI success/failure, atomic crash recovery, capacity, concurrent
intake, wrong schemas, withdrawal, expiry, metadata leakage and a working personal
checker with the inbox unavailable on macOS and isolated non-root Linux. Preserve
F-045's original acceptance in the packet. Keep public intake, research consent,
moderators, privacy/legal review and real-user acceptance under their existing jobs.
