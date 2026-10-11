# Optional offline revocation and freshness — implementation plan

This increment supports F-125 and F-126 without adopting RFC-0002 or claiming
an operating public transparency service. Existing receipt, group and personal
checker workflows remain independent and unchanged. A separate optional CLI
consumes an explicitly selected authority key, signed checkpoint history, and a
verifier-selected freshness policy. It does not create an endpoint or upload.

## Architecture and acceptance

Reuse the bounded canonical detached signature and owner-only file primitives.
A checkpoint binds a monotonic sequence, the prior signed checkpoint digest, an
issuer-local time/window and a sorted cumulative revoked-key set. All checkpoints
must verify under the separately selected authority. Removing a revocation,
skipping history, rollback against a known checkpoint, wrong signatures and
ambiguous records are refused. Bounded complete history starts at sequence one;
rotation, public distribution and independent witness operation are separate.

The verifier chooses its maximum age, permitted snapshot lifetime and an already
trusted minimum checkpoint (sequence and digest). No default age is described as
a standard. Missing, future, expired or stale status cannot clear a key. A fresh
signed snapshot can say only that the selected log had not recorded a revocation
at that checkpoint. It cannot establish global/current non-revocation. A local
clock is not an independent timestamp. Receipt integrity and per-key status are
separate outputs; no result issues a tag or certifies authorship.

Exercise positive and refusal paths, existing single/group receipt integration,
separate selected trust, expiry boundaries, replay/rollback, log extension,
revocation permanence, tampering, malformed/bounded input, file permissions and
no network on Mac and network-isolated Linux. Document friendly CLI steps and
preserve accurate open counts. The F-126 named model can finish when its full
conditional offline status and explicit insufficient-evidence behavior are
exercised; a public transparency service remains the separate F-125 job.

## Risks and limits

A dishonest or compromised authority can sign conflicting histories or omit a
revocation. Hash chaining and a pinned checkpoint detect selected-history changes;
they do not implement independently witnessed transparency or completeness.
Distribution, independent witnesses and per-device recovery remain open F-125/
F-129 acceptance. Revoked fingerprints can correlate records; save/share only by
explicit action. No text, identity, contact information or reason free text belongs
in the log. Private signing keys remain outside the repository with owner-only
permissions. Clock compromise and prolonged disconnection remain visible limits.

No production service, current tag result, taxonomy, intake, signature-rendering
contract or independently validated claim is changed. Full named requirements
remain open until their remaining actual acceptance is evidenced.

Author: Codex. Planned 2026-10-11 UTC before implementation.
