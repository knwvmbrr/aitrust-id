# Synthetic research admission

This developer check connects an invented private request to the existing
PostgreSQL storage rules. It does not collect anyone’s feedback or start a service.
The website’s feedback file still stays on the user’s device.

## Run the complete check

Use an ordinary Linux user with PostgreSQL 18 at
`/usr/lib/postgresql/18/bin`, Python with the repository’s hash-pinned verification
dependencies, and Node 24 for website choice parity. Do not run as root.

```sh
python -m pytest -q tests/test_research_admission.py tests/test_research_invitations.py tests/test_metadata_store.py
python scripts/metadata-store-sandbox.py --profile admission --output output/verification/research-admission.json
```

The second command creates its own private temporary database, applies both
synthetic SQL profiles, invokes the real admission CLI, and shuts down and removes
the database before publishing its receipt. The database listens on an owned Unix
socket only. It never connects to the application’s production database.
A failed check returns nonzero and retains bounded failure evidence.

## What the check demonstrates

- The private request accepts the website’s fixed PS result, method version,
  failure category and usability answers. It rejects prompts, examples, identities,
  event timestamps, subject hashes, duplicate keys and unknown fields.
- Submission requires separate invitation and withdrawal bearer values. Their
  canonical 32-byte values are hashed before SQL. Plaintext values are not written
  to SQL, database rows or public receipts.
- Identical retries return the same record. Conflicting retries, exhausted,
  expired and revoked invitations refuse. Six simultaneous CLI processes cannot
  consume more than a two-record allowance.
- Withdrawal removes the synthetic record. It does not refund a slot or let a
  stale request resurrect the record. Public or linked request files refuse.

For a freshly created synthetic sandbox only, the lower-level command is:

```sh
python scripts/research-admission.py --sandbox-dir /tmp/aitrust-metadata-OWNED --request /private/owner-directory/request.json
```

Those paths describe the required private files; use the complete verifier above
instead of creating a production directory with that name. The request must be a
0600 regular file in a 0700 owner-held directory outside the repository. No token
is passed in command arguments. The command refuses other database paths,
versions, listeners and cluster identities before attempting a write.

## What remains before a real pilot

This uses a trusted peer bootstrap and a NOLOGIN intake role. It is not production
login authentication, protection from a compromised administrator or participant
consent. No endpoint, browser upload, live invitation issuance or training operation
exists. The accepted collection purpose, roles, retention, withdrawal, provider
handling, genuine authentication, encrypted backup expiry, replacement-host
recovery and a consenting participant remain separate acceptance gates.

[Architecture](research-admission-plan.md) · [Execution results](research-admission-result.md)
· [Existing invitation profile](research-invitations.md)
