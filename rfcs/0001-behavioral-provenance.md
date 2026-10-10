# RFC 0001: Behavioral provenance — witnessing human authorship

- **Author:** Michael Raashad McGuire (knwvmbrr)
- **Date:** 2026-10-06
- **Status:** draft; proposed signals, no implemented behavioral capture or provenance-tag issuance
- **Affects:** signals, spec, governance

## Summary

FA and PA are preserved provenance-tag types. This draft proposes bounded
composition observations; it does not register conformant detectors, validate
confidence floors or enable runtime capture. Observing an input event is different
from establishing who caused it. Missing observations must remain unknown and
must never become an AI-origin accusation.

The design adds evidence about the creation process alongside other source
families. Each family still needs its own job, falsifiable measurements,
assistive-input safeguards and challenge path. No one signal supplies the
conclusion for every tag.

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

Signals are computed **in the content script, in the page, on the user's machine.** The proposed capture contract would retain raw events only within a bounded local
window. No event capture or scalar forwarding is currently implemented.

### Proposed signals

| ID | Feeds | Method |
|---|---|---|
| `sig.keystroke_liveness.v1` | PA | Dwell time (keydown→keyup) and flight time (keyup→next keydown) distributions. Humans produce heavy-tailed, context-dependent intervals; synthetic injection produces low-variance or templated ones. Reports a scalar in [0,1]. **Never a per-person template.** |
| `sig.revision_churn.v1` | PA | Ratio of deleted-and-rewritten characters to final length, plus count of non-adjacent edit positions. Humans and automated tools can both revise or proceed monotonically. This statistic does not establish origin. |
| `sig.compose_monotonicity.v1` | PA | Caret-position entropy over the composition window. Caret motion is an observation, not an authorship verdict. |
| `sig.paste_burst.v1` | FA | Insertion of ≥N characters in a single event with no preceding keystroke activity in the target field. Evidence of insertion, not of origin. |
| `sig.c2pa_manifest.v1` | FA | Parses an attached C2PA manifest and reports its assertions. Trust is inherited from the manifest's signer, never asserted by us. |
| `sig.assistive_input.v1` | *routing* | Detects switch access, voice dictation, on-screen keyboard, eye-tracking and IME composition events. **Suppresses the timing signals; it does not score.** See Accessibility. |

### The rule

A behavioral signal may raise `PA` or `FA`. **A behavioral signal may never lower a tag toward a
human-negative verdict.** Absence of human signal produces `UNK`, never `FA`. We are not
licensed to call something machine-made because we failed to see a person. We only report what
we witnessed.

## Privacy

This draft makes no exemption claim under biometric or privacy law. Legal
classification, consent and retention requirements need qualified,
jurisdiction-specific review before behavioral capture can be piloted. Derived
scalars and ephemeral processing do not establish anonymity or compliance.
F-148 remains open; no behavioral capture is implemented in the current extension.

Proposed safeguards require explicit per-origin opt-in, pause, reset and deletion,
bounded local processing and suppression of timing under assistive input. Raw event
streams, per-person templates and identity profiles must not be written or forwarded.
These are future requirements, not executed protections. Their complete data flow
and correlation risks must be tested before any feature is enabled.

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
2. Suppression returns insufficient-evidence status. It must never assign `IV` or
   any provenance tag; IV requires a separate independently accountable human workflow.
3. `ACCESSIBILITY.md` gains a conformance test: a composition produced via dictation and one
   produced via switch access must never receive a lower human-authorship score than one typed
   by hand. This runs in CI alongside the axe gates.

## Dataset

Instrumentation can record observed events but cannot determine who or what
caused them. Ground truth and the mapping to provenance claims require independent
validation, adversarial replay tests and accessibility review. No floor is supported
by instrumentation alone; proposed numeric values below are not accepted gates.

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
evasion, and be honest about the residual.** The cost of forging per-field composition behavior is unmeasured; no superiority
or meaningful increase in attacker effort has been demonstrated. That is the
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
