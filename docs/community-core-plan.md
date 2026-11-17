# Community moderation core — architecture before implementation

Codex community lane, 2026-11-17. Base `0ff7a08`.

## Existing authority and scope

F-135/F-136/F-137/N-005 remain40% in the current ledger. Their full acceptance
includes real moderators, protected reporting, object authorization, safe live
updates/reconnect/retraction, public corrections/appeals and human operation.
This increment adds executable software evidence; it does not redefine that job.

`docs/public-community-and-private-data.md` explicitly selects no route name.
The website's Report panel downloads an unsubmitted draft; Townhall links to
GitHub. The approved `POST /v1/feedback` is exclusively a disabled-by-default,
synthetic research transport. It is not community authorization. No endpoint,
posting integration, credentials or collection will be introduced here.

## Complete bounded component

A framework-independent standard-library Python state machine, an owner-private
SQLite transaction adapter and a local synthetic CLI provide a working moderation
workbench. Two distinct users, two moderators, one official account and an
administrator are predeclared synthetic principals; a request cannot choose its
own role. A trusted local operator selects a principal for rehearsal. This is
not remote authentication, identity proof, MFA, credentials or signed posting.

Public-intended text needs an explicit public notice/consent acknowledgement;
initial submissions and edits wait for a separate moderator. Only approved current
text reaches the allowlisted public projection. Private report intake accepts
fixed categories/target identifiers and storage consent, not private message
bodies, examples, research envelopes, contact information or training labels.
Moderation supports warning/restriction/suspension, safe reasons, retraction and
an appeal resolved by a different moderator. Accepted appeals reopen review;
they cannot silently republish scrubbed text. Corrections are fresh reviewed
records linked to the superseded record, never a rewritten detector assertion.

All state changes are atomic and optimistic-versioned. Bounded request IDs make
identical retries idempotent, while conflicting retries refuse. Removal retires
associated request digests so old requests cannot resurrect content. Events store
only IDs/revisions and resolve through CURRENT public eligibility; replay and
export cannot recover old text. Public tombstones retain no removed body, hash,
reporter or private reason. A bounded cache reducer specifies replacement and
reset behavior for future web/native clients, without modifying those clients.

The local adapter checks owner/private permissions, links, namespace, fixed
schema, total size and SQLite transaction locks. Core state is a versioned closed
JSON document, without SQLite-specific business logic. A future PostgreSQL
adapter must enforce the same single-document transaction/row-lock/CAS boundary
with separate runtime roles and the existing private socket deployment. The subsequent PostgreSQL component uses the existing validated disposable
socket cluster, bounded `psql` stdin transport and an atomic JSONB compare-and-
swap with six retries. Separate NOLOGIN development owner/runtime/public roles
restrict the public role to a SECURITY DEFINER fixed-field snapshot; raw state
stays private. The256KiB JSONB cap can refuse admission before the core count
limit. These are synthetic role checks, not production logins. PostgreSQL
execution remains pending until its fresh Linux evidence exists.

The PostgreSQL18 [Read Committed documentation](https://www.postgresql.org/docs/18/transaction-iso.html#XACT-READ-COMMITTED)
describes rechecking an UPDATE predicate after a concurrent committed update;
that supports the equality/revision CAS boundary. Its [SECURITY DEFINER guidance](https://www.postgresql.org/docs/18/sql-createfunction.html#SQL-CREATEFUNCTION-SECURITY)
requires trusted lookup paths, temporary schema last and selective EXECUTE
grants in the creation transaction. This schema uses qualified table names,
`pg_catalog,pg_temp` and explicit PUBLIC revocation. Both sources were read on
2026-11-17. Actual executable controls remain necessary.

## Risks and boundaries

- Public consent is a deliberate choice, not training consent or guaranteed PII
  detection. Human review can miss secrets; retraction cannot recall saved copies.
- Only invented local inputs are authorized for these checks. No production
  at-rest key/recovery policy exists for private community text; none is accepted.
- A local OS owner can alter a synthetic registry/database. The engine separates
  actor permissions, but does not authenticate a person or defend a root attacker.
- Role/membership, moderator staffing, actual appeals, inbox delivery and user
  onboarding remain external gates. HTTPS/session/CSRF/MFA and streaming transport
  need an approved HTTP contract before deployment.
- Fixed capacities/rate limits are engineering bounds, not service SLAs. No outage
  or import failure in this optional workbench may change any tag or gateway.
- Audit records exclude bodies and secrets. Scrubbing is logical deletion, not
  disk/backup erasure. Backups, restoration and retention need operating acceptance.

## Files and verification

Own `tools/community_core.py`, `tools/community_store.py`,
`scripts/community-workbench.py`, `scripts/verify-community-core.py`, focused
`tests/test_community_{core,store,cli}.py`, these component docs and new immutable
run/change records. No global scope/state, website/native or deployment edits.

Execute realistic two-user/moderator/official lifecycle and refusal tests: consent,
ownership, roles, duplicates, stale edits, quotas, independent appeals, correction,
retraction, replay/reset/cache, HTML escaping, private marker absence, damaged
storage and concurrent writes. Exercise the actual CLI in a disposable private
folder, then remove its synthetic store. Source-bind evidence and record failures.
No Docker, live accounts, network listener, production database or actual users.
