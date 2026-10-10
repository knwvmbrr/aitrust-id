# RFC 0003: Modality coverage

- **Author:** Michael Raashad McGuire (knwvmbrr)
- **Date:** 2026-10-06
- **Status:** draft
- **Affects:** spec

## Summary

Reserve `text`, `code`, `image`, `audio`, `video` and `document` in the assertion schema's
`modality` field. Define what the subject hash means for each. **Specify text and code subjects; runtime currently evaluates text only.**

This is a draft scoping RFC; its executable reference contracts do not adopt a new wire protocol. It adds no detector and makes no accuracy claim. It exists so that an
image implementation written by someone else in 2029 is conformant without a version break.

## Motivation

The schema reserves six modalities. The gateway currently accepts only `text`; code snippets can be checked as text. This describes what we can
do and a bad description of what the standard is for.

Two costs to leaving it there:

1. **A later rewrite.** Adding modalities after implementations exist means a breaking change to
   every consumer. Standards that survive reserve their extension points early.
2. **A false implicit claim.** A schema that admits only text implies the problem is only text.
   The person being deceived by a cloned voice on the phone is inside our stated mission and
   outside our stated schema. That gap should be *visible and labelled*, not silent.

The honest position is not "we cover everything." It is: **the schema reserves six values; this runtime evaluates text. Code has a
separate tested hash primitive, which is not a code-modality detector.**

## Design

### Reserved modalities and their subject definition

The `subject.sha256` must be unambiguous per modality, or two implementations will hash
different bytes for the same artifact and their assertions will not be comparable.

| Modality | Status | Subject hash is taken over | Spans address |
|---|---|---|---|
| `text` | **implemented** | UTF-8 NFC-normalised redacted text | character offsets |
| `code` | subject primitive specified and tested; detector reserved | raw bytes, no normalisation — whitespace is semantic | byte offsets |
| `image` | reserved | versioned RGBA8/sRGB/oriented pixel contract, excluding metadata | half-open pixel boxes |
| `audio` | reserved | versioned PCM16LE interleaved bytes and declared rate/channels | sample-frame ranges |
| `video` | reserved | ordered domain-separated frame/timing Merkle tree | frame index + pixel box |
| `document` | reserved | versioned supplied-page-text extraction profile plus ordered asset hashes | page + code-point range |

Excluding metadata from the image hash is deliberate: a C2PA manifest lives in metadata, and the
subject hash must stay stable whether or not that manifest is present or stripped.

### Conformance

An implementation declares which modalities it supports. Receiving an assertion for an
unsupported modality is **not an error** — it is rendered as `UNK` with
`reason: "unsupported_modality"`, which already exists in the schema.

### What this RFC does not do

It does not authorise anyone to claim a label on a reserved modality. A tag asserted against
`image` without a published detection basis, dataset and measured agreement fails conformance
exactly as it would for text. Invariant 5 is modality-independent.

## Detection basis

None. No detector is proposed. For the reserved modalities, the honest state of the art is:

- **Image.** A future contract must define decoding, pixel/color representation,
  metadata boundaries, evidence coordinates and reproducible vectors. Consume
  provenance claims with their actual integrity/trust status; a credential is not
  proof of truthful content or generation origin.
- **Audio.** Define sample representation/rate, timing and transforms before a
  detector can claim support. Voice provenance and generation observations need
  their own datasets and accessibility/privacy review.
- **Video.** Define frame/time ordering, canonical decoding and hash-tree rules.
  Local resource budgets and usable playback evidence need measurement.
- **Document.** Define text-layer extraction, layout/assets, page coordinates and
  unsupported-encrypted/scanned-content behavior with their own vectors.

These are preserved independent jobs, not accepted detector implementations or
comparative claims about competing vendors.

RFC-0002's authorship receipts are the more promising direction for all three, and for the same
reason stated there: a verified signed statement can preserve evidence integrity, while authorship,
clock trust, replay resistance, revocation and algorithm aging need separate checks.

## Dataset

Not applicable — no detector proposed. Any future RFC implementing a reserved modality must
supply fixtures and a measured Krippendorff's alpha before it may claim a floor.

## Measured performance

Not applicable. **This RFC must not be cited as evidence that any modality is supported.**

## Failure modes

- **Reservation read as a roadmap promise.** Someone sees `video` in the enum and assumes it is
  coming. Mitigation: the spec and README both carry the implemented/reserved table, and
  `reserved` is stated in the schema description, not only in prose.
- **Hash ambiguity across implementations.** Two implementers normalise differently and produce
  incomparable assertions. Mitigation: the table above is a proposed subject boundary, and each reserved modality
  must ship conformance vectors before it moves to implemented.
- **Scope creep.** Reserving a modality makes it feel cheap to start building it. It is not.
  Nothing moves from reserved to implemented without its own RFC clearing Invariant 5.

## Accessibility impact

Each reserved modality carries an accessibility obligation that must be designed *before*
implementation, not retrofitted:

- **Image** labels must convey the finding in text, not by highlighting a region visually. A
  bounding box is meaningless to a screen-reader user; it needs a described location.
- **Audio** findings must not be announced over playback, and must be reachable without
  scrubbing a timeline.
- **Video** inherits both problems at once.

No reserved modality ships until its announcement pattern passes the same manual screen-reader
pass required of text labels.

## Alternatives considered

- **Leave the enum at text and code.** Honest today, guarantees a breaking change later, and
  implies the mission is narrower than it is.
- **Reserve everything, implement nothing, claim the standard is universal.** Dishonest, and
  exactly the overclaiming the project exists to oppose.
- **Build an image detector now.** Would produce a detector that is wrong about real images and
  burn the credibility the accurate tags are earning.

## Open questions

1. Should `document` (PDF, DOCX) be implemented before image? Its text layer is tractable with
   what we already have, and it may be where harm actually concentrates — contracts, invoices,
   medical letters. **This may deserve to move from reserved to implemented first.**
2. Does consuming a C2PA manifest for an image constitute "supporting" that modality for
   conformance purposes, even with no detector of our own? Leaning yes, as provenance-only.
3. For video, is a frame-hash tree the right subject, or should re-encoded video be expected to
   produce a different subject entirely?

## Executed subject primitive — 2026-10-10

[Subject contract v1](../docs/subject-contract.md) and 19 fixed vectors agree
between independent Python and Node implementations. This does not enable the
gateway code modality or establish outside-implementer acceptance.

## Executed reserved subject reference contracts — 2026-10-10

[Prepared-artifact contracts](../docs/reserved-subject-contract.md) specify the
exact binary encodings, coordinate units, preparation profiles and resource
limits. Sixteen fixed subjects and 37 rejection cases run in both Python and
Node, plus valid/invalid coordinate checks and actual CLI stdin use. The broader
test suite exercises resource ceilings, odd/even frame trees, transforms and
canonical JSON integral numbers. These are hashing contracts, not file decoders,
RFC adoption or tag support. Image/audio/video/document detection and file-parser
acceptance remain separately gated. Encoded-file extraction is not implied.
