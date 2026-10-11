# Group receipt architecture and risks

Codex implementation plan, 2026-10-10. Scope F-130 remains open until execution
and acceptance. This optional integrity component does not adopt RFC-0002 or
issue an authorship tag.

The job is to let a group keep one artifact-bound record signed by several keys,
with each participant signing independently. It must never require one organizer
to hold everyone’s private keys. A verifier supplies the artifact and a separately
trusted roster of public keys; keys embedded in a group record cannot create trust.

Use the existing detached-record signature/canonicalization profile and Node’s
built-in Ed25519/P-256 implementation. A group manifest records an exact artifact
hash/length, a random group ID, two to sixteen distinct public-key fingerprints,
and a bounded local-clock window. Each participant explicitly chooses to sign
the same manifest. The assembler verifies every required signature before writing
a group record. The verifier checks the selected roster, all signatures, exact
manifest agreement, artifact bytes and expiry before reporting agreement under
those keys. Missing/extra/duplicate signers, substituted manifests, invalid
versions or algorithms, tampering and unsafe files fail closed.

Privacy risk: the record exposes a collaboration graph of key fingerprints and
an artifact hash that can identify known content. It stays local; there is no
upload, identity claim, participant-name collection or automatic publication.
Participation and receipt creation are optional, and declining them must not
change personal checking. Files are bounded, private-key permissions enforced,
outputs created without overwriting or following links, and private keys remain
outside this repository. No new endpoint or runtime dependency is introduced.

Integrity is not authorship. The tool cannot establish who controls a key,
whether different keys represent different people, whether declarations are true,
or whether a signer was coerced. Revocation remains unchecked and local clocks
unverified. It does not manufacture independent timestamp, trust, human review,
certification or accuracy evidence. Freshness/revocation, non-technical custody,
and institutional anti-coercion remain separate scope jobs.

Acceptance must execute two-, four- and sixteen-key groups, both algorithms,
separate participant signing, assembly and offline verification, refusal controls
and existing personal-route regressions. Record actual Mac/Linux execution and
versions. Synthetic signers test cryptographic workflow, never human authorship.
Only then assess the full F-130 component; no PA/FA/IV tag is credited.
