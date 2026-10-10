# Assertion replay — architecture before implementation

F-003 requires more than a list of signal names. Current gateway records identify
the command rules but omit the redactor configuration/model and orchestration
identity. A private original input cannot reliably reproduce a whole record from
those names alone. Historical records cannot be repaired by guessing their setup.

## Implementation

Return a versioned, bounded redactor identity from the existing `/redact` route:
source hashes, installed dependency versions, verified English asset manifest,
explicit English/offline recognizer configuration and recognizer versions. Hash
its canonical metadata. No text, detections, user identifier, paths or secret is
part of this identity. The gateway requires that identity, verifies its digest,
and carries it in a schema-checked optional `evaluator.preprocessing` field with
the normalization and gateway policy identities. Preserve the first detector
model and append the redactor/pipeline identities; do not redefine a digest as
accuracy, signature trust or human provenance.

Build an owner-run replay command for an assertion plus privately supplied source
text. The complete service replay uses only the existing authenticated loopback
`127.0.0.1:8787/v1/evaluate` route, explicitly selected by the owner. Read the
local token from a protected file, never a command argument; disable proxies and
redirects. Compare method/preprocessing identities before findings. Compare
stable subject hash/length, tags and abstentions; exclude UUID, capture time and
latency. Print a small result summary, never input, assertion details, credentials
or exception/path data. Do not retain inputs or create an intake/database path.

Unknown, historical or incomplete preprocessing identities produce an explicit
unavailable result. Source-mismatched input and reproducible finding differences
have separate results. Preserve archived methods and original records; never
load arbitrary source, contact a URL from an assertion, fetch missing models or
claim that signal IDs reconstruct absent private input.

## Verification and risks

Exercise identity tampering, additional fields, missing metadata, finite/size
bounds, credential permissions, unsafe file types, future versions, proxy and
redirect controls, wrong inputs, changed methods and changed findings. Execute a
full replay against the actual isolated Linux service stack using synthetic input,
and show private markers absent from logs and CLI output. Revalidate affected
consumers/schema/routes and publish the exact source-bound evidence.

A matching replay demonstrates repeatability of that implementation, not accuracy
or independent corroboration. The gateway necessarily receives the original
text on this explicitly chosen local-service route. It stays on the owner's
computer; this tool cannot make a compromised local host safe. Historical records
without sufficient identity/input remain unreplayable and keep full historical
reproduction acceptance open. No new endpoint, tag adoption, remote collection,
calibration claim or legal assurance is introduced.
