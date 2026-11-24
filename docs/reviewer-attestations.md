# Inspect an explicit reviewer attestation

This local tool checks a signed review declaration against the exact subject revision, review scope and history head **you select independently**. It does not issue IV, identify a human, establish reviewer independence or verify that a reviewed claim is correct. No account, upload, browser, service, key generation, private-key read or file write is involved.

Run with an existing Node installation (the project supports Node22 or newer):

```sh
node scripts/reviewer-attestation.cjs --help
node scripts/reviewer-attestation.cjs verify trusted-policy.json history.json subject.txt
node --test tests/reviewer-attestations.cjs
```

Use a private terminal. The JSON result contains linkable subject hashes, scope statements and reviewer handles; hashes are not anonymization. The subject body and public/private key material are not printed. Do not publish another person's review metadata merely because signature verification succeeds.

Exit0 means an active **signed declaration**,3 means verified but inactive evidence (expired, disclosed conflict, withdrawn or superseded), and2 means Unavailable. Inconclusive/does-not-support decisions remain those attributed decisions even if their declaration is current. No exit code means a claim is true, a reviewer independent, or an IV tag accepted. Malformed/unreadable inputs return a fixed Unavailable JSON; errors never echo input paths or source text. All existing tags remain independent because this is a separate callable tool, with no platform interception or registration.

## Select trust before reading the received history

Obtain the reviewer's canonical public SPKI PEM and handle through your chosen trusted channel. Confirm the exact subject revision, scope/evidence references and latest known history head separately. Save this policy yourself; do not automatically accept a policy supplied alongside an untrusted artifact. A handle is a caller-selected label, not verified legal identity.

`trusted-policy.json` has exactly these fields (replace placeholders; the example is not a valid trust decision):

```json
{
  "profile": "reviewer-attestation-policy/1.0.0",
  "review_id": "selected-review-1",
  "reviewer": {"handle": "selected-reviewer", "public_key": "CANONICAL PUBLIC SPKI PEM"},
  "subject": {"sha256": "64 lowercase hex characters", "bytes": 42, "revision": "revision-1"},
  "scope": {
    "id": "claim-scope-1", "version": "scope-v1",
    "statement": "Exactly which claim and evidence the person says they reviewed.",
    "evidence": [{"id": "evidence-1", "kind": "reference", "sha256": "64 lowercase hex characters", "bytes": 100}]
  },
  "checkpoint": {"head_sha256": "64 lowercase hex characters", "sequence": 1, "observed_at": 1800000000, "valid_until": 1800003600}
}
```

The evidence references are sorted by their unique ASCII ID. They are signed references, not proof that the files were opened, authentic or accurate. Subject bytes are hashed exactly, without normalization. A changed byte count, hash, revision, scope statement, scope version or evidence reference refuses the binding. The subject fields use the existing assertion SHA-256 meaning; this evidence profile does not replace or emit an assertion envelope.

The externally selected checkpoint must specify the complete event count and canonical signed-envelope hash. Its local-clock window is at most seven days, with no automatic renewal. An old head cannot validate a supplied newer chain; a truncated received chain cannot match the selected newer head. This does **not** discover omitted newer withdrawals beyond the checkpoint you selected. Obtain a fresh trusted checkpoint when current lifecycle matters. No public transparency/witness or global key-revocation service is implemented by this tool.

## Signed events and lifecycle

`history.json` is exactly `{"profile":"reviewer-attestation-history/1.0.0","events":[ENVELOPE,...]}`. Every envelope is the existing `detached-record/1.0.0` shape from `protocol/receipts.cjs`, using existing Ed25519 or P-256 support. Received envelopes cannot introduce their own trusted key. Signed payload bytes must use that module's canonical serialization; duplicate JSON fields, unknown fields, noncanonical signed JSON and unsupported algorithms refuse.

The initial signed payload has exactly:

```json
{
  "profile": "explicit-review-event/1.0.0",
  "review_id": "selected-review-1", "reviewer_handle": "selected-reviewer",
  "subject": {"sha256": "64 lowercase hex characters", "bytes": 42, "revision": "revision-1"},
  "scope_sha256": "SHA256 of receipts.bytes(policy.scope)",
  "sequence": 1, "previous_sha256": "64 zero characters", "action": "review",
  "issued_at": 1800000000,
  "review": {
    "consent": true, "human_review_declared": true,
    "decision": "inconclusive", "conflicts": [],
    "reviewed_at": 1799999999, "expires_at": 1800003600
  },
  "replacement": null
}
```

Decisions are `supports`, `does_not_support` or `inconclusive`. Consent and human-review fields must be explicitly true, but a signature establishes only that the selected key signed those declarations. An empty conflict list means **none declared**, not that independence or absence of conflict was verified. Nonempty conflict IDs are retained and make the review inactive. Do not put unnecessary personal/confidential detail in IDs.

An authorized reviewer can use an existing signer compatible with `protocol/receipts.cjs`; this verifier has no signing command and never opens private keys. For an existing authorized integration, `receipts.sign(payload, existingPrivateKey)` creates the canonical detached envelope; this documentation is not authorization to sign for someone else. Establish real consent and reviewer identity/independence outside this software. There is no automatic translation from detector success to a review.

For each subsequent event increment `sequence`, set `previous_sha256` to `receipts.hash(receipts.bytes(previousEnvelope))`, preserve review ID/handle/subject/scope and use nondecreasing issued times. A subsequent `review` explicitly renews or corrects the declaration before closure and includes its own consent, decision, conflicts and expiry. Review expiry must be after its issue time and within30 days; reviewed time cannot be later than issuance. These are declared times on unverified clocks, not trusted timestamps.

To withdraw, sign `action:"withdraw"`, `review:null`, `replacement:null`. To supersede, sign `action:"supersede"`, `review:null`, `replacement:{"review_id":"a-different-review-id","head_sha256":"replacement envelope hash"}`. Withdrawal and supersession are terminal for this review ID; a later review under that same chain refuses. A replacement is only an attributed pointer: it is never fetched or automatically accepted. Verify a replacement using its separately selected subject, scope and trusted policy. Future events, forks, duplicates, missing links, reordered events or wrong heads refuse rather than return a partial active review.

## Callable result and failure behavior

```js
const {verify} = require('../protocol/reviewer-attestations.cjs');
const result = verify({subject: subjectBuffer, policy: policyBuffer,
                       history: historyBuffer, now: Math.floor(Date.now()/1000)});
```

The function takes exactly those four fields and returns `REVIEW_RECORD_VERIFIED` or `UNAVAILABLE`. Verified states include `ACTIVE_DECLARATION`, `EXPIRED`, `CONFLICT_DISCLOSED`, `WITHDRAWN`, `SUPERSEDED`. The result separates signature integrity, exact byte binding, checked scope, attributed review decision, checkpoint status and the following unchanged limits: human identity/independence/accuracy unestablished, no independent timestamp, no global withdrawal completeness, `tag_issuance:false`, `IV_asserted:false`.

The local evaluation clock is explicit and unverified. For the CLI it is the machine's current clock. The callable API is suitable for a private API/plugin evidence consumer, but no API registration or endpoint is added here. Consumers must preserve these statuses and nonclaims, including on unavailable or expired evidence; they must not turn this result into IV automatically.

## Resource and filesystem limits

Subject8MiB, policy64KiB, complete history256KiB, at most128 events/32 evidence references/one4096-byte public key; existing canonical depth16 and detached signature bounds apply. The verifier checks one five-second monotonic deadline before/after bounded synchronous operations; this is cooperative, not an OS preemption guarantee. The CLI also checks one original five-second capture/verification elapsed window through its final input check. A synchronous operation may finish before the timeout is surfaced, but cannot turn expired budget into a verified result.

The CLI holds at most128 file/directory descriptors, permits at most32 path components and reads in at most64KiB chunks. Symlinks, FIFOs, oversized files, changed files/ancestors and close failures return Unavailable; every acquired descriptor is closed once with all close attempts made even after a failure. It writes nothing and deletes nothing, including on cancellation. No universal defense against a hostile concurrent writer under the same OS identity is claimed; keep inputs in a controlled private directory.

The tests import only the openly published RFC8032 section7.1 test keys. These keys are known to everyone and must **never** be used for real reviews. Synthetic signatures are software evidence, not an independent human review. T-IV final human independence, actual human review/accessibility/route acceptance and accuracy gates remain open. See the [implementation plan](reviewer-attestation-plan.md).
