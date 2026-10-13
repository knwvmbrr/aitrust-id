# Metadata pilot — owner-approved operating contract

Prepared by Codex on 2026-10-11 for F-044, F-045, F-141 and N-011.
Michael approved this additional contract on the recorded owner reply: see
[runs/2026-10-13-metadata-pilot-owner-decision.json](../runs/2026-10-13-metadata-pilot-owner-decision.json).
**Collection is not deployed or enabled.** Approval authorizes engineering of the
listed route; real intake requires the security, withdrawal and recovery gates.

## What a participant would do

Use PS without an account or contribution requirement. Separately choose three
listed feedback answers, preview the exact record, then choose whether to submit
it to a private, invited pilot. Checking an answer, downloading a record and
posting publicly never count as research consent. Evaluation must continue to
work when submission is disabled or unavailable. No background submission,
tracking pixels, cross-site identifier or silent retry queue is permitted.

The submitted record would contain only the existing feedback builder's schema
version, purpose, PS tag, method version, reported result, failure category and
structured usability answer. Its current `sharing: local_file_not_submitted`
marker must not be reused for a submission: an accepted versioned submission
contract must distinguish a local download from a consented server receipt.
Unknown fields and free text are refused. No answer, prompt, example, hash,
span, device identity, client timestamp or claimed independent label is accepted.
Method-version matching must be checked against a published supported list.

## Accepted storage and access

Use the dedicated AI Trust ID Linux/PostgreSQL environment, separate from THT.
The approved HTTPS intake is
`https://research.aitrustid.com/v1/feedback`; implementation is authorized, but it must not accept real submissions before
the security, withdrawal, recovery and privacy gates below pass.
Database credentials stay server-side. PostgreSQL remains private; separate
migration, runtime, expiration and read-only review roles receive only the
permissions they need. Administration is private and key authenticated.

Start with invitations, not a general signup gate. A revocable, short-lived
invitation capability permits a bounded number of submissions, without naming a
participant in the feedback row. Store only a digest of that capability; never
put it in a URL, public page, log or client bundle. Return a separate random
withdrawal capability once, and store its digest. Neither capability is an
identity or independent accuracy label. A lost withdrawal capability cannot be
recovered by asking the person for content or a new identity dossier.

Michael is the accepted accountable pilot operator and access approver. This is
not a claim of a staffed review team. Reviewers
receive read-only metadata access only after assignment. Agents do not acquire
standing administrator access by being listed as implementation contributors.
Access grants, revocations, schema changes and expiration-job failures produce
private operational audit events containing no feedback values or capabilities.

## Accepted retention and withdrawal

Keep individual feedback for **30 days from server receipt**. Keep the server
receipt/expiry time privately for enforcement, not as a public participant
timeline. Withdrawal deletes the active feedback promptly and records a minimal
deletion instruction for recovery. Encrypted backup copies expire within **7
days**; they are inaccessible through the application. Do not promise immediate
erasure from an immutable backup. Do not reuse the infrastructure's existing
backup schedule without checking its actual retention.

Every restoration must apply deletion instructions and expiry before application
access or analysis resumes. Retain those instructions through the last affected
backup's expiry, then remove them. A successful restore alone does not establish
deletion. If backup expiry or restore suppression cannot be demonstrated, real
submissions stay disabled. The pilot does not retain participant-level training
datasets indefinitely. Public aggregate publication, example sharing, model
training and anomaly experiments each need a separate accepted purpose and
release review; these three answers cannot become ground-truth accuracy labels.

## Security and failure gates before a pilot opens

Implement bounded requests, strict types/enums, exact allowed origin, capability
validation, quotas, cancellation and per-capability duplicate handling. Refuse
arbitrary URLs, files and example fields. Prevent reflected values, SQL injection,
token leakage, content-bearing exception logs and cross-participant withdrawal.
Reverse-proxy access logs and provider handling must be reviewed: omitting an IP
from PostgreSQL does not prove it was never processed elsewhere. Publish the
actual processors and limits before inviting participants.

Execute synthetic submit/duplicate/invalid-capability/revoked-capability tests;
unknown-field and oversized-record refusals; withdrawal authorization;
expiration; restored-copy deletion; outage isolation; and a replacement-host
restore. Check the deployed route, firewall, HTTPS and effective database grants.
Have the owner operate the invite, review, withdrawal and recovery controls.
Do not accept real data before these gates pass and the privacy policy describes
the observed workflow. A successful metadata pilot does not release PS, start a
certification program or complete the wider training/anomaly requirement.

## Approval boundary

The exact approved contract and reply are preserved in the dated owner decision
above. The legacy hash-only registry has not been adopted. No example collection,
training, public participant metadata, indefinite retention, mandatory account
or additional purpose is authorized. Changes to the agreed purpose or retention
need a separate owner decision and participant notice; approval never substitutes
for executed deployment and recovery gates.
