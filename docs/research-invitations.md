# Practice the research capacity controls

This is an offline development check for a future optional research pilot. It uses invented PS feedback in a new private PostgreSQL database, checks the results, then shuts down and removes that database. It accepts no participant input and collects nothing from the website or downloaded checker.

On Debian or Ubuntu with Python 3.12+ and PostgreSQL 18 installed at `/usr/lib/postgresql/18/bin`, run as an ordinary user:

```sh
python3 scripts/metadata-store-sandbox.py --profile invitation \
  --output output/verification/research-invitations.json
```

A successful run exits 0 and produces a source-bound JSON report. Failure exits 1 and never establishes acceptance. A failed shutdown keeps the private directory for operator diagnosis instead of deleting an active database. The original profile remains independent:

```sh
python3 scripts/metadata-store-sandbox.py \
  --output output/verification/metadata-store.json
```

## What the separate profile checks

- An invented invitation permits at most its fixed lifetime capacity: 1–20 submissions, expiry within one day, and at most 100 retained invitation records.
- An exact duplicate keeps its original feedback ID and consumes one slot. It cannot increase capacity, extend expiry or move its withdrawal key to another invitation.
- Unknown, expired or revoked invitations refuse. Invalid/private payloads roll back without consuming capacity. Six simultaneous requests cannot exceed two available slots.
- Withdrawal removes the feedback without refunding its lifetime slot. The remaining private binding prevents that feedback from reappearing through an otherwise valid invitation, including after the original withdrawal tombstone expires.
- Intake cannot issue invitations, read/mutate the private tables or bypass quotas through the original insert function. The maintenance role issues/revokes/prunes; the reviewer retains the existing minimum-five aggregate.

Feedback remains the existing closed PS metadata envelope: result, method version, failure category and one fixed usability answer. No prompts, examples, names, emails, IPs, contact fields or free-form comments are accepted. Only 32-byte invitation/withdrawal digests, feedback IDs and bounded quota/expiry bookkeeping are added. Digests can link records and are sensitive; this is not an anonymity guarantee.

Feedback expires after the existing 30-day development interval; withdrawal instructions use the existing seven-day interval. Invitation capacity/revocation bookkeeping retires after invitation expiry plus 30 days (at most 31 days from issuance). This development behavior is not an adopted participant policy. Database administrators are trusted. The role checks use synthetic NOLOGIN roles under the disposable bootstrap connection; production logins, authentication and externally enforced authorization are not installed.

## What remains before a real pilot

N-011 remains open. An actual service needs the owner-approved endpoint, collection/purpose/permission policy, role/authentication implementation, provider/proxy handling, operational quotas, backup expiry, replacement-host recovery and a consenting human pilot. This tool proves selected database behavior. It does not invite real users, issue live credentials, prove backup deletion or validate PS accuracy. A personal check never needs a research invitation.
