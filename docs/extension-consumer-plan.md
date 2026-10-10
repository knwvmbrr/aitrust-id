# Extension consumer: architecture before refactor

The current consumer reads an unbounded response body and the content script
validates only a subset of the assertion. Tighten both trust boundaries using a
shared bounded current-version contract. Accept unsigned 0.1.0 from the existing
authenticated loopback service only; incompatible versions and signatures with no
configured verifier are unsupported. Unknown/invalid candidates are unavailable,
not abstentions. Preserve six UI states without changing the adopted tag enum.

Read at most 2 MiB of JSON using the fetch stream; cancel on oversized/malformed
responses and keep the existing 15-second timeout. Never redirect the bearer
credential, use browser cache, or accept a non-JSON body. Validate sender, scalar
text and code-point cap before fetching. Share the contract in the isolated world
and service worker; no page-derived configuration or new endpoint/permission.
Validate mandatory fields, UUID/time/hash identity, actual model identity shape,
current tag allowlist, bounded signals/spans, scores/floors, and known abstention
reasons including null floors for disabled candidates. Bound every collection.

Risks: strict profile checks can reject future legitimate extensions; report a
clear unsupported version instead of guessing. The shared validator is a bounded
consumer profile, not a general JSON Schema implementation or signature verifier.
Test it against the full reference schema using real gateway outputs and deliberate
mutations. Keep unknown evidence IDs safe as data; refuse malformed identifiers.
No private token, response text or exception details in reports. Cancelled fetches
release stream resources; stale page results remain discarded by the bridge.

Acceptance: exact response schema/profile mutation suite, unsupported versions,
signed-but-unverified records, below-floor suppression, each abstention reason,
all six result states, invalid token/backend/HTTP/body/content-type faults,
redirect refusal, overflow cancellation, astral/scalar text bounds, and actual
keyboard/recheck/fixture behavior. Live vendor and outside-user/human acceptance
remain separate; do not substitute fixtures for those observations.
