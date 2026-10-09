# RFC 0001: Behavioral provenance — witnessing human authorship

- **Author:** Michael Raashad McGuire (knwvmbrr)
- **Date:** 2026-10-06
- **Status:** draft
- **Affects:** signals, spec, governance

## Summary

`FA` and `PA` carry the two highest confidence floors in the taxonomy (0.95, 0.85) and are the
only tags whose detection basis is provenance rather than content. Neither has a registered
signal. This RFC registers six, and establishes the rule that separates them from the content
tags: **we do not infer authorship from the artifact. We witness it at the capture point, or we
return `UNK`.**

The inversion is the point. "Is this AI?" is an unbounded negative claim about a string of
bytes. "Was a human present while this was composed?" is a positive claim about an observable
event. We detect the second and report the first only as its complement.

## Motivation

Today the evaluator can only read text. That caps the system at stylometry, and stylometry is
the part of this field that does not work and should not be trusted:

- The same sentence typed by a person and emitted by a model is byte-identical. There is no
  residue *in the artifact*. Residue lives in the process that produced it.
- Stylometric "AI detectors" systematically misfire on non-native English writers, whose prose
  reads as generated. A detector with that bias, deployed where it affects people, is a
  discrimination engine wearing a lab coat. We will not ship one.

Concrete failure under the current taxonomy: a student writes an essay by hand in a browser
textarea over forty minutes, with 300 edit events and twelve revisions. The evaluator sees only
finished prose, finds no content signal, and returns `UNK`. The strongest available evidence —
that a person composed it, observed directly — is thrown away because nothing is watching the
keyboard.

## Detection basis

Signals are computed **in the content script, in the page, on the user's machine.** Raw event
streams never cross a process boundary. Only derived scalars reach the gateway.

### Registered signals

| ID | Feeds | Method |
|---|---|---|
| `sig.keystroke_liveness.v1` | PA | Dwell time (keydown→keyup) and flight time (keyup→next keydown) distributions. Humans produce heavy-tailed, context-dependent intervals; synthetic injection produces low-variance or templated ones. Reports a scalar in [0,1]. **Never a per-person template.** |
| `sig.revision_churn.v1` | PA | Ratio of deleted-and-rewritten characters to final length, plus count of non-adjacent edit positions. Generation is monotonic and forward. Composition is not. |
| `sig.compose_monotonicity.v1` | PA | Caret-position entropy over the composition window. A caret that only advances indicates insertion rather than authorship. |
| `sig.paste_burst.v1` | FA | Insertion of ≥N characters in a single event with no preceding keystroke activity in the target field. Evidence of insertion, not of origin. |
| `sig.c2pa_manifest.v1` | FA | Parses an attached C2PA manifest and reports its assertions. Trust is inherited from the manifest's signer, never asserted by us. |
| `sig.assistive_input.v1` | *routing* | Detects switch access, voice dictation, on-screen keyboard, eye-tracking and IME composition events. **Suppresses the timing signals; it does not score.** See Accessibility. |

### The rule

A behavioral signal may raise `PA` or `FA`. **A behavioral signal may never lower a tag toward a
human-negative verdict.** Absence of human signal produces `UNK`, never `FA`. We are not
licensed to call something machine-made because we failed to see a person. We only report what
we witnessed.

## Privacy

Keystroke dynamics are biometric data. Under Illinois BIPA, Texas CUBI, Washington's HB 1493
and GDPR Article 9, collecting a biometric **identifier** triggers written-consent, retention
and private-right-of-action obligations. BIPA in particular carries statutory damages per
violation and no requirement to show harm.

These statutes attach to the **data subject's** location, not the implementer's. Any
deployment with a single user in a covered jurisdiction is in scope regardless of where the
project is maintained. An implementation that never derives an identifier is out of scope
everywhere, which is why the constraint below is architectural and not a policy promise.

The architecture avoids this entirely by making a weaker claim than fraud-detection systems do:

> Fraud detection asks **who** is typing. We ask only **whether anyone is.**

- No per-person template is computed, stored, or compared. Nothing supports re-identification.
- The raw event stream lives in a bounded ring buffer in the content script and is discarded
  when the composition window closes. It is never written to disk, never sent to the gateway,
  never logged.
- What leaves the page is a scalar and a span set. `{"id":"sig.keystroke_liveness.v1",
  "score":0.88,"spans":[[0,412]]}` — the same shape every other signal emits.
- Default is **off.** Behavioral capture requires explicit per-origin opt-in, surfaced in plain
  language, revocable, and recorded in the assertion so a reader knows it was active.

This extends Threat #7 (*registry becomes a surveillance log*) rather than contradicting it. A
system built to defend people must not become the most invasive thing on their machine.

## Accessibility

**This is the signal's most serious failure mode and it gates the whole RFC.**

A naive liveness model trained on unimpaired typing will score the following as non-human:

- switch access, scanning keyboards, eye-tracking input
- voice dictation and speech-to-text
- motor conditions producing tremor, spasticity, or long dwell
- predictive text, swipe entry, and IME composition for non-Latin scripts

That failure would mean a disabled person's own writing is flagged as machine-generated by a
tool that claims to protect authorship. It is unacceptable and it is also the exact bias this
project exists to refuse.

Controls:

1. `sig.assistive_input.v1` runs **first**. When assistive input is detected, the timing signals
   are suppressed entirely — not down-weighted. They do not contribute, in either direction.
2. The composition then routes to `IV`, the human-attestation path, which was already
   human-only by design.
3. `ACCESSIBILITY.md` gains a conformance test: a composition produced via dictation and one
   produced via switch access must never receive a lower human-authorship score than one typed
   by hand. This runs in CI alongside the axe gates.

## Dataset

Behavioral ground truth is **instrumented, not annotated.** The capture point records what
occurred, so there is no annotator disagreement to measure — the event either happened or it
did not. This removes the Krippendorff constraint that gates `MT`, and it is the reason these
floors can sit high.

What still requires validation is the mapping from signal to tag. Proposed fixture families
under `eval/datasets/provenance/`:

| Split | Contents | n (min) |
|---|---|---|
| `typed_human/` | Compositions recorded live across varied speed, language and device | 500 |
| `assistive/` | Dictation, switch access, on-screen keyboard, IME — **must not be penalized** | 150 |
| `pasted/` | Insertion events with no preceding composition | 300 |
| `replayed/` | Synthetic streams replaying recorded human cadence — the adversarial case | 200 |

Fixtures store derived features and event metadata only. **No fixture may contain the text that
was typed.** The corpus must be releasable.

## Measured performance

Not yet measured. Gates proposed for `eval/gates.yaml`, to be ratified only after the fixtures
exist:

```yaml
  PA: { precision_min: 0.90, recall_min: 0.70, ece_max: 0.05 }
  FA: { precision_min: 0.95, recall_min: 0.80, ece_max: 0.04 }

accessibility:
  assistive_parity_max_delta: 0.0   # assistive input may never score lower than typed input
```

## Adversarial

Cadence can be replayed. A recorded human stream can be played back to synthesize liveness, and
the `replayed/` split exists to measure exactly how well we resist it.

We do not claim this is unforgeable. The claim is the standard IDS bargain: **raise the cost of
evasion, and be honest about the residual.** Forging per-field composition behavior in real
time, per target, at scale is meaningfully more expensive than regenerating text. That is the
whole margin, and overstating it would be the first dishonest thing in this specification.

## Scope

These signals are available only where we own the capture point — a browser surface running the
extension with behavioral capture enabled for that origin.

For text encountered anywhere else, with no manifest and no capture, the correct output is
`UNK`, permanently. This is a boundary of the design, not a gap in it. A system that returns
`UNK` honestly is more useful than one that guesses confidently, and the alternative is the
stylometry we opened this document by refusing.

## Open questions

1. Minimum composition window before `sig.keystroke_liveness.v1` may emit at all. Too short and
   a few keystrokes buy a human label; too long and short legitimate edits never qualify.
2. Does `PA` require *both* a timing signal and a churn signal, or does either suffice?
3. Should a replay-resistance score ship inside the assertion so readers can discount it
   themselves, rather than us deciding for them?
4. Consent UX. The opt-in has to be comprehensible to someone who does not know what keystroke
   dynamics are, without being so alarming that nobody enables it.
