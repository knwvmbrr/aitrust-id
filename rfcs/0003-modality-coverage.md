# RFC 0003: Modality coverage

- **Author:** Michael Raashad McGuire (knwvmbrr)
- **Date:** 2026-10-06
- **Status:** draft
- **Affects:** spec

## Summary

Reserve `text`, `code`, `image`, `audio`, `video` and `document` in the assertion schema's
`modality` field. Define what the subject hash means for each. **Specify text and code subjects; runtime currently evaluates text only.**

This is a scoping RFC. It adds no detector and makes no accuracy claim. It exists so that an
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

The honest position is not "we cover everything." It is: **the protocol covers everything; this
implementation covers two, and says so.**

## Design

### Reserved modalities and their subject definition

The `subject.sha256` must be unambiguous per modality, or two implementations will hash
different bytes for the same artifact and their assertions will not be comparable.

| Modality | Status | Subject hash is taken over | Spans address |
|---|---|---|---|
| `text` | **implemented** | UTF-8 NFC-normalised redacted text | character offsets |
| `code` | subject primitive specified and tested; detector reserved | raw bytes, no normalisation — whitespace is semantic | byte offsets |
| `image` | reserved | decoded pixel buffer, excluding metadata | pixel bounding boxes |
| `audio` | reserved | decoded PCM at declared sample rate | millisecond ranges |
| `video` | reserved | per-frame hash tree, root recorded | frame + bounding box |
| `document` | reserved | extracted text layer, plus per-asset hashes | page + character offset |

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

- **Image.** Detecting generation from pixels alone is unreliable and degrades with every model
  release. C2PA manifests and SynthID are substantially better at this and are backed by the
  producers themselves. We should **consume their signals, not compete with their detectors.**
- **Audio.** Voice-clone detection is an active arms race against well-funded specialists. A
  one-person project entering it ships a detector that is wrong about real people's voices.
- **Video.** Hardest and most compute-hungry. Outside any plausible local-CPU constraint, and
  our no-egress invariant forbids shipping the frames somewhere that could afford it.

RFC-0002's authorship receipts are the more promising direction for all three, and for the same
reason stated there: attestation at creation time does not degrade as models improve, because
the asymmetry is the clock rather than the content.

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
  incomparable assertions. Mitigation: the table above is normative, and each reserved modality
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
