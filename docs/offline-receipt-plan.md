# Optional offline receipt and signing increment

Scope: F-008, F-121, F-122, F-123, F-127 and F-131. Implement an experimental
versioned receipt binding exact artifact bytes to the editing observation, and
an optional detached signature profile for schema-valid assertions. Neither
changes the adopted tag taxonomy or the production gateway/extension.

Architecture: dependency-free Node 24 cryptography, strict bounded JSON parsing,
declared sorted-key JSON canonicalization, SHA-256 artifact identity, and pinned
public-key verification. Local CLI generation/issuance/inspection; no endpoint,
network, authority account, payment or automatic issuance. Private key material
must remain in new owner-only files outside the repository. The signature proves
record integrity under the explicitly selected key, not identity or truth.

Use both Ed25519 and ECDSA P-256 profiles to test algorithm dispatch, explicit
algorithm identifiers and unsupported-algorithm refusal. Default expiry is one
day; maximum lifetime seven days. Verification separately reports mathematical
signature integrity, artifact binding, expiry and **unchecked key revocation**.
No `VALID` authorship or certification verdict is permitted without the missing
trust/status evidence. Clock is local and not an independent timestamp.

Risk gates: no embedded-key auto-trust; duplicate fields, unsafe numbers,
noncanonical payloads, excessive nesting/size, unknown fields/versions/algorithms,
tampering, mismatched artifacts/keys, expiry and malformed signatures fail.
Observation forgery cost is explicitly `unvalidated`, because a valid signature
can cover invented events. No crypto-strength claim about composition evidence.

Acceptance: both algorithms sign and verify actual local files; replays against
another artifact, key or payload fail; canonical encoding has published vectors;
private-file permissions and overwrite/symlink refusal are executed; assertion
schema validation is required before signing and after verification. CLI tests
use disposable synthetic keys and inputs only. No production key is created.

Keep F-124 independent RFC 3161 timestamps, F-125 revocation transparency, F-126
offline freshness, F-128 institutional anti-coercion conformance, F-129 friendly
key recovery, F-130 group authorship and all PA/FA/IV releases open. This is a
complete optional receipt component, not adoption or completion of RFC-0002.
