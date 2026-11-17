# Community workbench — executed result and remaining acceptance

Codex community engineering lane, 2026-11-17. Base `0ff7a08`.

A runnable synthetic moderation engine, private local CLI/store and a separate
PostgreSQL18 development adapter now exist. No public endpoint, posting client,
credentials, actual moderator assignment, real-data collection or training is
activated. This is engineering work toward F-135/F-136/F-137/N-005, not completion
of those full public-service requirements. PM owns the global scope/state ledger.

## Functioning local component

- Two users and an official account can submit public-intended questions/replies;
  separate moderators approve each item. Unapproved text stays private.
- Edits withdraw the prior public view until fresh review. Correction approval
  links a new record while scrubbing the superseded body. Detector assertions
  themselves are never rewritten by this moderation tool.
- A member can file fixed private report metadata; a different moderator records
  a disposition or a proposed correction reference, separately from tag validity.
- Warning/restriction/suspension, retraction and an appeal to a different moderator
  run. Reconsideration does not republish removed text or clear a separate
  restriction from another action.
- Current projections, replay, cache updates and new exports suppress removed
  bodies. Public safe reasons/timestamps/tombstones and private body-free audit
  records remain available. Saved copies cannot be recalled.
- Strict request parsing, public consent, object ownership, typed roles, optimistic
  revisions, idempotent retries, body/rate/capacity bounds, clock rollback,
  safe HTML, private file permissions and transaction/lock failures are exercised.

The fixed synthetic actor registry is an operator rehearsal mechanism. It does
not authenticate people. The PostgreSQL runtime can invoke its synthetic CAS
function with replacement state; it is a trusted application role, not a database
implementation of participant authorization. The public SQL role has only the
fixed-field current snapshot function. Explicit projection masking additionally
protects queued/retracted/private values in the adversarial test contract; a
compromised trusted writer can still fabricate plausible approved state.

## Checks actually executed so far

| Check | Result |
| --- | --- |
| Current focused core/store/CLI/PG-boundary/workflow suite |53 passed on macOS after byte-reserve correction |
| Actual current-source local CLI lifecycle |17 calls across7 groups passed; temporary synthetic SQLite store removed |
| Syntax and whitespace checks |Pass |
| Actual PostgreSQL 18 installation, schema, CAS, grants and lifecycle |12 groups passed on the initial draft; the new saturation control awaits a fresh run |
| Public transport, CSRF/TLS/session/MFA, two real users, actual moderators and phone clients |Not executed or released by this increment |

The initial core run passed26 checks, then the first store/CLI set passed39 and
its expanded PG-boundary set passed49. A later51-test run covered the reviewed adapter and audit/dispute additions.
The final52-test run also proves reserved removal capacity: normal writes stop
with256 audit slots left, preserving a removal slot per possible remaining post
without silently pruning audit history. The current17-call CLI run passes on
that source. [Current capacity receipt](../runs/2026-11-17-community-capacity-correction.json)
retains the earlier local receipts unchanged. These successive runs followed actual source additions, not a claim
of independent accuracy. During an in-flight audit timestamp edit, review caught
an accidental request-validator `at` lookup before the next execution; it was
removed. No runtime pass is claimed for that intermediate edited source.

The initial hosted run passed all 12 PostgreSQL control groups and 17 CLI calls.
Its artifact hashes match the tested commit, and the receipt records verified
shutdown and removal of the isolated test cluster.
[Initial hosted evidence](../runs/2026-11-17-community-hosted-initial.json).

Review found that a retraction of short text could add more audit and request
bytes than it removes. PostgreSQL now reserves 1 KiB per removable post plus
one pause before ordinary writes reach the cap. The core also reserves an
audit slot for that pause. The corrected source passed 53 local tests and 17 CLI
calls. A fresh PostgreSQL run will measure the actual saturated-store behavior.
[Local correction evidence](../runs/2026-11-17-community-byte-reserve-local.json).

The PostgreSQL runner is restricted to a fresh private `/tmp/aitrust-metadata-*`
cluster, the existing fixed PostgreSQL18 binary path and a fresh Linux network
namespace. It drops privileges, installs only separate synthetic NOLOGIN roles,
exercises actual CLI/CAS/retry/grant/correction/retraction controls and confirms
shutdown before cleanup. Its artifact must pass before PostgreSQL execution is
credited. The focused workflow filters main/tag pushes and matching PR changes,
uses existing hash-pinned verification dependencies and the existing official
fingerprint-checked PostgreSQL installation method. No global CI gate or source
inventory was silently changed.

## What remains for the original requirements

F-135/F-136/F-137/N-005 retain their original jobs and current ledger percentages;
this result does not close them. Remaining acceptance includes an approved actual
HTTP/client contract, production identity/session/CSRF/MFA and least-privilege
logins, independent security review, real moderators/appeal owners/inbox delivery,
owner-approved private-content policy and at-rest boundary, retention/withdrawal/
encrypted backup expiry/replacement-host recovery, web/native accessibility and
real multi-user live operation. The PostgreSQL adapter and synthetic tests cannot
substitute for those operating gates.

The independent core/CLI are usable for rehearsing the software now. Personal
checks and existing GitHub community paths remain separate and available. Scope
records are retained; no tag is released and no collection purpose is broadened.

[Usage and exact action fields](community-core.md) · [Architecture](community-core-plan.md)
