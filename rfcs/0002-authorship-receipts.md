# RFC 0002: Authorship receipts and reproducible calibration

- **Author:** Michael Raashad McGuire (knwvmbrr)
- **Date:** 2026-10-06
- **Status:** draft
- **Affects:** spec, governance

## Summary

Invert the customer. Every product in this category sells *detection* to institutions so they
can accuse people. This one issues **receipts to authors** so they can answer the accusation.

An authorship receipt is a signed, timestamped assertion that a human composed a specific
artifact, held by the author, verifiable offline by anyone, with no central database and no
callback to us. Paired with a published calibration ledger, it converts "trust our numbers"
into "re-run our numbers."

## Motivation

### Detection degrades. Attestation does not.

A detector is in a race it eventually loses. Models will be trained to emit human-looking
keystroke cadence — that is a distribution, and distributions can be sampled. Any signal whose
only defence is statistical will be forged on a long enough timeline.

A receipt issued **at composition time** is different in kind. To forge it, an adversary must
produce a signature and timestamp that predate the artifact's existence. A better model in 2029
does not help, because the fraud is not in the text — it is in the clock. **Time is the only
adversarial asymmetry that does not erode.**

This is why the defensive product is also the durable architecture. We are not choosing between
ethics and longevity.

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
a raw event stream. A receipt proves *that* a human composed a thing with a given hash. It does
not reveal what the thing says or who the human is.

### Verification

Offline. A verifier needs the receipt, the artifact and the public key. It recomputes the hash,
checks the signature, checks the timestamp token against the TSA's published chain, and reads
the tags. **No request reaches us.** We cannot see who verified what, and a dead project does
not invalidate existing receipts.

### Independent timestamping

The signature alone proves authorship by keyholder, not time of composition. An RFC 3161
timestamp from an independent authority — or an equivalent transparency log — is what makes
pre-dating infeasible. This is the load-bearing component of the design and **must not be
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

## Signals this RFC registers

| ID | Feeds | Method | Forgery cost |
|---|---|---|---|
| `sig.outside_knowledge.v1` | PA | A revision introduces an entity, figure or claim not derivable from anything in the captured session context. A model's edits can only recombine its own context; a human reaches outside it. Checked locally against the captured window. | `structural` |
| `sig.attention_shape.v1` | PA | Read-pause-write rhythm from `visibilitychange` and focus events. An inserted block has no antecedent attention. **No content access, no biometric.** Survives dictation and switch access, where timing signals must be suppressed. | `behavioral` |

`sig.outside_knowledge.v1` is the most durable behavioral signal in the system. Its barrier is
not statistical — a model cannot inject information it does not have, no matter how well it is
trained to imitate a person.

## Calibration ledger

Every release publishes, in the repository:

1. the fixture corpus (derived features only — no text),
2. the model SHA-256 recorded in the assertion,
3. the harness and gate file at that revision,
4. the resulting precision, recall and ECE per tag.

Anyone may re-run the harness and reproduce the published numbers. A claim that cannot be
reproduced by a third party is marketing. **No release ships a number a reader cannot check.**

## Licensing and tiering

Governing rule, adopted here as policy:

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
| R3 | Author signs a receipt for AI output they pasted | `sig.paste_burst.v1` raises `FA`, not `PA`. The receipt reports what was observed — a receipt that says `FA` is still a true receipt |
| R4 | Key theft | Keys are per-device and revocable; revocation publishes to the transparency log |
| R5 | Coerced attestation — an institution demands receipts for all work | Governance: a conformant implementation may not make receipt issuance non-optional for the author |
| R6 | We become the thing we oppose | No central database. Verification requires no contact with us. The project can die and every issued receipt still verifies |

## Open questions

1. Key custody for a non-technical author who will lose the key. Recovery without reintroducing a central authority is unsolved here.
2. Does a receipt expire? A signature outlives its algorithm; ed25519 will not be safe forever.
3. Group authorship — four people need four receipts, or one with four signers, and the second leaks the collaboration graph.
4. Does `sig.outside_knowledge.v1` require capturing session context broadly enough to become a privacy problem of its own? Scope it before implementing.
