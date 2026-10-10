# AITrust-ID Taxonomy v0.1.0

Licensed CC BY 4.0.

A tag is a **claim with a published basis and a confidence floor**. Below its floor a tag is
not emitted as a verdict — it is recorded as an abstention. `UNK` is emitted when every
candidate abstains.

| Code | Name | Claim | Detection basis | Floor |
|---|---|---|---|---|
| `NF` | Non-Fiction | Consistent with supplied reference material | Claim extraction + local corpus match. Only assertable when a corpus is attached. | 0.80 |
| `FI` | Fiction / Fabricated | Contradicted by reference material, or cites what does not exist | Corpus contradiction; citation resolves to nothing offline | 0.75 |
| `HP` | Hallucination Possible | Carries structural fingerprints of a model guessing | Self-contradiction across spans, unsourced specificity, duplicate-loop structure, hedging collapse | 0.65 |
| `MT` | Manipulative Tactic | Framing aimed at moving the reader rather than informing them | Urgency framing, false dilemma, authority appeal, pressure lexicon | 0.78 |
| `PS` | Potential Scam / Risk | Emitted code or instructions that could cause harm if followed. **The name overclaims: the detectors support an observation about a command, not a finding about intent. A split is proposed in RFC-0004 and is not yet accepted** | Static analysis: piped installers, obfuscated payloads, credential exfil, typosquats | 0.70 |
| `IV` | Independently Verified | A person checked this and signed for it | Human attestation only. **Never machine-assigned.** | n/a |
| `FA` | Full AI Augmentation | Generated end to end with no human in the loop | Capture-point provenance; consumes C2PA manifests | 0.95 |
| `PA` | Partially Augmented | Machine-generated, then edited by a person | Provenance + observed edit events | 0.85 |
| `UNK` | Unknown | Evaluated; nothing cleared its floor. **Overloaded: it cannot distinguish "we checked and are unsure" from "no valid evaluation was obtained". A six-state replacement is proposed in RFC-0004 and is not yet accepted** | All candidates abstained | — |

| `PII_REDACTED` | Detected redaction | Detected entity values were replaced before evaluation. This does not prove all sensitive information was removed. | Trusted redactor transformation; only categories/counts appear in the assertion | n/a |

## Why MT's floor is set by its annotators

*(Corrected 2026-10-08: this heading previously read "the highest floor". It is not —
`FA` at 0.95 and `PA` at 0.85 are higher. The argument below was always the point.)*

Human annotators disagree about what counts as manipulation. We publish the inter-annotator
agreement (Krippendorff's alpha) for the MT dataset in every release. **A classifier may not
claim more confidence than the humans who labeled its training data.** If alpha is 0.6, MT
does not ship at 0.9.

The alpha gate applies to **MT only**. It does not gate any other tag, and it does not block
`UC` evaluation.

## The floors are editorial until measured

Every floor in the table above is a judgment, not a calibrated value. None has a measured
basis yet. They are published anyway because a stated threshold can be argued with and an
unstated one cannot — but no release may describe a floor as calibrated until a frozen
held-out set says so.

## Proposed, not adopted

**Corrected 2026-10-08.** An earlier edit of this file listed `UC`, `SC` and `BT` as rows in
the table above and marked `PS` and `UNK` deprecated while the decisions authorising them
(D18, D19, D17) were still open. This table carries only what is adopted; proposals live in
their RFC until accepted. The change record is in `DECISIONS.md`.

## Error budgets differ by tag

A single precision-first posture across every tag was wrong. The cost of a false positive
depends on who is reading the label:

- A command-risk finding should be **precision-weighted**. Its audience is technical and can
  disable the tool; a false alarm on a legitimate install command teaches a developer to
  ignore every badge.
- A scam finding should be **recall-weighted**. Its audience includes people being actively
  targeted. A false alarm costs seconds; a miss can cost someone their savings. A
  recall-weighted tag owes the reader hedged wording, every indicator shown, one-action
  dismissal, and a published false-positive rate.
- An automation finding should be **precision-weighted**. A false positive is an accusation
  against a person.

(Stated by finding rather than by code, because the codes are proposals. Posture is a
property of the audience and the cost of error, not of the name.)

See `eval/gates.yaml` and RFC-0004. Trading precision for recall is legitimate; concealing
that you did it is not.

## Changing this document

Taxonomy changes require an RFC (`rfcs/0000-template.md`) containing a detection basis, a
labeled dataset, and measured agreement. Without that, community tagging drifts into noise
inside a year and the labels stop meaning anything.

## Executable vocabulary contract

`spec/vocabulary.json` distinguishes ten adopted schema codes, three proposed
codes, six reserved modalities and current development capabilities.
`python3 scripts/verify-vocabulary.py` rejects consumer drift and accidental
proposal/release promotion. A vocabulary entry is not a working detector.
The current gateway returns tags and explicit abstentions; it does not synthesize
a UNK tag for every no-finding result. The six-state presentation remains distinct
from any future adopted protocol revision.
