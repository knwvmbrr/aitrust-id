# RFC 0002: Authorship receipts and reproducible calibration

- **Author:** Michael Raashad McGuire (knwvmbrr)
- **Date:** 2026-10-06
- **Status:** draft; unadopted. Optional experimental offline integrity receipts exist; no authorship validation
- **Affects:** spec, governance

The [offline component](../docs/offline-receipts.md) implements optional artifact-bound
receipts, pinned-key integrity and expiry. It does not implement this RFC’s
independent timestamps, revocation, recovery, group receipts or provenance claims.
No standard adoption or PA/FA/IV acceptance is implied.

## Summary

Invert the customer. Every product in this category sells *detection* to institutions so they
can accuse people. This one issues **receipts to authors** so they can answer the accusation.

The proposed receipt binds a key-signed statement of observed composition activity to an
artifact. It is held by its issuer and is intended for offline verification without a central
assertion database. A signature or timestamp cannot establish that a human composed the artifact. Paired with a published calibration ledger, it converts "trust our numbers"
into "re-run our numbers."

## Motivation

### Evidence integrity and authorship are separate

A verified signature binds a statement to a key. It does not establish that the
statement is true, that the keyholder is a particular person, or that the
observed activity came from a human. A replayed or fabricated event stream can
be signed and timestamped too. Those risks need their own measured controls.

An independently trusted timestamp can establish that the bound datum existed
by the recorded time, subject to the authority's policy, trust chain and status.
It does not validate a self-reported composition window or prove what preceded
that datum. [RFC 3161 sections 1–2.2](https://www.rfc-editor.org/rfc/rfc3161.html)
defines this narrower proof-of-existence and the required imprint/token checks.
Revocation, compromise and algorithm aging remain relevant. This draft does
not claim an eternal or unforgeable human-authorship certificate.

### The accused have no tool

Current failure: a student is flagged by a stylometric detector with no appeal, no evidence and
no way to prove authorship. The institution holds the tool. The person holds nothing.
Journalists, contractors and non-native English writers face the same asymmetry — and
non-native writers are the group stylometric detectors misfire on hardest.

## Design

### The receipt

Issued when a composition window closes. Signed ed25519 with a key the author holds.

```json
{
  "v": "1.0.0",
  "artifact_sha256": "<hash of the final text>",
  "composed_ms": 2140311,
  "window": { "opened": "<RFC3339>", "closed": "<RFC3339>" },
  "tags": [{ "tag": "PA", "confidence": 0.91, "floor": 0.85 }],
  "signals": [
    { "id": "sig.revision_churn.v1",     "score": 0.88, "forgery_cost": "behavioral" },
    { "id": "sig.outside_knowledge.v1",  "score": 0.94, "forgery_cost": "structural" }
  ],
  "calibration_id": "cal-2026-08-a",
  "models": [{ "name": "rules-only", "sha256": "...", "revision": "..." }],
  "tsa": "<RFC 3161 token>",
  "sig": "<ed25519 over the canonical form>"
}
```

**Never in a receipt:** the text, any excerpt of it, a biometric template, a user identifier, or
a raw event stream. Hashes and per-device public keys can still correlate or identify
records. A receipt proves a bound statement was signed only after its cryptographic
checks pass; the statement’s authorship meaning requires separate validated evidence.

### Verification

Offline. A verifier needs the receipt, the artifact and the public key. It recomputes the hash,
checks the signature, checks the timestamp token against the TSA's published chain, and reads
the tags. **No request reaches us.** We cannot see who verified what, and a dead project does
not invalidate existing receipts.

### Independent timestamping

The signature alone supports key-bound statement integrity, not human authorship or time of composition. An RFC 3161
timestamp from an independent authority — or an equivalent transparency log — can establish an independently attested existence time after its own trust and status checks;
it does not establish the truth of earlier self-reported times. This is the load-bearing component of the design and **must not be
operated by us.**

## Forgery cost as a first-class field

Signals are currently ranked by accuracy. Accuracy is the wrong sort order for an adversarial
system. `signals.md` gains a required `forgery_cost` column:

| Class | Meaning | Example |
|---|---|---|
| `statistical` | A distribution an adversary can learn and sample | keystroke cadence |
| `behavioral` | Requires simulating a session, not just an output | attention shape, revision churn |
| `structural` | Requires information the forger does not possess | outside-knowledge import |
| `cryptographic` | Requires breaking a signature or a clock | the receipt itself |

A signal that is 95% accurate today and `statistical` is worth less than one that is 70%
accurate and `structural`. Release notes must state the distribution of forgery classes behind
each tag, so a reader can judge how the label will age.

## Signals this draft proposes

| ID | Feeds | Method | Forgery cost |
|---|---|---|---|
| `sig.outside_knowledge.v1` | PA | A revision introduces an entity, figure or claim not derivable from anything in the captured session context. Absence from captured context does not establish origin; no authorship inference or runtime implementation is accepted. | `unvalidated` |
| `sig.attention_shape.v1` | PA | Read-pause-write rhythm from `visibilitychange` and focus events. An inserted block has no antecedent attention. No content capture is proposed; correlation and legal treatment still require review. Dictation and switch-access support is unmeasured. | `behavioral` |

`sig.outside_knowledge.v1` is an unvalidated proposal. Humans and automated systems can
introduce information absent from the captured window. This indicator must never be
used to establish human authorship or assigned a structural security guarantee.

## Calibration ledger

Every release publishes, in the repository:

1. the fixture corpus (derived features only — no text),
2. the model SHA-256 recorded in the assertion,
3. the harness and gate file at that revision,
4. the resulting precision, recall and ECE per tag.

Anyone may re-run the harness and reproduce the published numbers. A claim that cannot be
reproduced by a third party is marketing. **No release ships a number a reader cannot check.**

## Licensing and tiering

Proposed implementation requirements, consistent with the preserved personal-access scope; this draft does not itself adopt a standard:

> **The specification, the reference implementation, the fixtures and the calibration ledger are
> open and free. Permanently. The only thing that may sit behind a commercial gate is tooling
> that performs capture requiring explicit human consent — and even then, a free path to issue
> and verify a receipt must always exist.**

Free forever: spec, taxonomy, signals registry, evaluator, extension, receipt issuance, receipt
verification, calibration ledger, fixtures.

Commercially gateable: fleet deployment and policy management, host-level capture agents,
long-horizon retention and audit, SSO and directory integration, support.

A person defending their own authorship never pays. An organization administering capture
across other people's machines does. **The direction of the money follows the direction of the
power.**

## Threats

| # | Threat | Control |
|---|---|---|
| R1 | Pre-dating a receipt | Independent RFC 3161 timestamp; we never operate the TSA |
| R2 | Receipt transferred to a different artifact | Receipt binds the artifact hash; verification recomputes it |
| R3 | Author signs a receipt for AI output they pasted | A paste is evidence of insertion, not origin. A signed false inference stays false; no FA/PA issuance is implemented or accepted here |
| R4 | Key theft | Keys are per-device and revocable; revocation publishes to the transparency log |
| R5 | Coerced attestation — an institution demands receipts for all work | Governance: a conformant implementation may not make receipt issuance non-optional for the author |
| R6 | We become the thing we oppose | Proposed offline verification without a central database. The project can stop operating, but verification needs exported trust and status evidence; availability and freshness limits must remain explicit |

## Open questions

1. Key custody for a non-technical author who will lose the key. Recovery without reintroducing a central authority is unsolved here.
2. Does a receipt expire? A signature outlives its algorithm; ed25519 will not be safe forever.
3. Group authorship — four people need four receipts, or one with four signers, and the second leaks the collaboration graph.
4. Does `sig.outside_knowledge.v1` require capturing session context broadly enough to become a privacy problem of its own? Scope it before implementing.
