# Experimental adjudication policy — 1.0.1

Reviewed 2026-10-09. A proposed research component, not an adopted tag, complete
C2PA validator, institutional certification or independent accuracy result.

This policy keeps distinct facts about content binding, signer trust, revocation
and conflicting claims. Pure functions interpret **supplied** observations. They
read no media, perform no cryptography, query no OCSP responder and detect no
watermark. A trusted, version-pinned adapter must authenticate observations, bind
them to one subject/revision and claim, establish validity/freshness and publish
its support boundaries. The adapter and selected user route are not implemented.

[Implementation review](competitive-differentiation.md) ·
[Full scope package plan](scope-delivery.md) ·
[Execution evidence](../runs/2026-10-09-scope-completion-checks.json)

## Verdict input and output

`from_status_codes(codes, manifest_present=True, ocsp_checked=None, strict=True)`
accepts full validation-result strings. A failures-only list is insufficient to
establish a positive finding. The returned pair records integrity and revocation,
source codes, uninterpreted-code notes, machine state and a plain explanation.

| Integrity | Meaning of supplied results |
|---|---|
| UNSIGNED | No manifest supplied; absence is not evidence of human or AI origin |
| UNVERIFIED | Required successful verification is missing or unknown |
| VALID | Explicit signature, signer-trust and supported content-binding successes |
| UNRECOGNIZED_SIGNER | Signer not on the configured trust list |
| EXPIRED | Certificate validity issue reported |
| CONFLICTED | A mapped manifest/binding/parent conflict reported |
| REVOKED | Issuer revocation reported; not automatically changed content |
| TAMPERED | Binding/signature failure reported; timing, intent and author are not established |

Revocation is independently NOT_APPLICABLE (only UNSIGNED), NOT_REVOKED, REVOKED,
UNKNOWN_SKIPPED or UNKNOWN_INACCESSIBLE. NOT_REVOKED is the supplied upstream
result, not a guarantee that a certificate remains current forever.

## Verdict constraints

- **V1:** Missing revocation evidence is unknown. `ocsp_checked=True` means an
  attempt; without a result it produces UNKNOWN_INACCESSIBLE, not NOT_REVOKED.
- **V2:** Positive assertion requires signature validation, signer trust, a
  recognized content-binding match, integrity VALID, revocation NOT_REVOKED and
  no unresolved-code notes. Successful OCSP alone is insufficient.
- **V3:** Plain explanations include unknown revocation, including its cause.
- **V4:** Positive revocation wins. Otherwise inaccessible is more conservative
  than skipped, which is more conservative than not-revoked. Input ordering
  cannot choose the optimistic observation.
- **V5:** Direct construction cannot bypass pair consistency or fabricate VALID
  without its required success codes. A revoked credential cannot pair with a
  VALID integrity state. TAMPERED can coexist with REVOKED.
- **V6:** Unknown codes raise in strict mode. Lenient mode preserves a note and
  cannot assert; a future failure code is never quietly treated as success.
- **V7:** Multi-manifest combination preserves adverse integrity, positive
  revocation and unresolved evidence. It does not average uncertainty away.

These constraints protect interpretation at this seam. An upstream adapter that
fabricates a success string can still lie; it needs separate verification.

## Per-claim adjudication input and output

`Signal` identifies a layer, claim, value and attributed source; classifiers need
a bounded confidence. MANIFEST and WATERMARK require explicit `verified=True`
from their trusted adapter. MANIFEST additionally requires `verdict_state='valid'`.
Omitted or invalid verification removes strong standing. The flag and state are
not themselves cryptographic evidence. All signals must describe the same subject
revision; authenticating that binding is a remaining adapter gate.

The proposed policy gives MANIFEST and WATERMARK standing 3, unsigned METADATA 1,
and CLASSIFIER 0. Assertion floor is 2; contest floor is 1. Equal standing is a
policy choice needing acceptance for the specific claim, not proof that all
watermark technologies and manifest assertions are equally reliable. ISCC or a
fingerprint alone does not automatically prove AI generation or human authorship.

| Rule | Condition | Result |
|---|---|---|
| R1 | No observations for the claim | UNSUPPORTED |
| R5 | No verified observation reaches assertion floor | UNSUPPORTED |
| R2 | Eligible contesting observations agree | SUPPORTED, with the value |
| R3 | Highest-standing observations disagree | CONTRADICTED, naming each value/source |
| R4 | Highest-standing observations agree but lower observations disagree | SUPPORTED, with lower observations preserved as overruled |

Rules execute R1, R5, then comparison. SUPPORTED means the input supports a claim
**under this proposed policy**; it is not independently verified factual truth.
Absent signals never yield a human-negative finding. Classifier confidence cannot
silently acquire authentication authority. Claim groups are evaluated separately;
several methods reading one source are not independent confirmations.

## Measurement and missing observations

`eval/measure.py` computes Wilson intervals over integer success/trial counts,
conditional accuracy on answered graded fixtures, pairwise disagreement and
manifest/soft-binding survival separately. Summaries expose answer coverage and
missing counts. Conditional accuracy is not overall correctness when validators
fail to answer. No expected state means agreement measurement, not accuracy.

A requested 95% interval **total width** of 0.20 near p=0.5 yields 93 trials,
approximately ±0.10, not ±0.20. This is a design calculation, not a guarantee of
representative independent samples or platform coverage. No upload/download
collection harness, real platform study or independent dataset is supplied here.

## Executable checks and demonstration

```sh
python3 scripts/demo-adjudication.py
python3 -m pytest tests/test_adjudicator.py tests/test_adjudicator_boundaries.py -q
```

Runtime modules use stdlib; the test suite needs the documented pytest environment.
The demo prominently identifies simulated inputs. The Nikon-shaped scenario uses
constructed codes, not a retrieved signed Nikon asset or current competitor runs.
Tests cover the mapped policy and adversarial seam. They are not C2PA program
conformance or complete SDK interoperability vectors.

## Before integrating any released tag

Accept claim-specific policy through the appropriate decision/RFC process. Build
and threat-review the bounded real adapter; verify actual signed, revoked,
malformed and missing-evidence assets; test subject identity, stale/replayed
revocation, transformations and disagreement. Measure independent ground truth
and subgroup/error costs. Complete the selected route's privacy, accessible
explanation, installation/removal and correction gates. Publish versions and
limits. None of these remaining gates may be inferred from a green unit suite.

## Change and challenge

Cite a rule number, exact method/source version and a privacy-safe reproducible
input when challenging a result. Changes preserve previous record identity and
reopen affected acceptance. Published research is motivation, not a substitute
for our evidence. The [latest Nemecek paper](https://arxiv.org/abs/2603.02378)
already reports its own cross-layer protocol; this project does not claim that
conflict adjudication is an unoccupied category.

## Experimental provenance-to-tag bridge — 0.2.0 research

`services/adjudicator/tag_bridge.py` consumes typed, **supplied** credential results
and optional explicit subject-bound authorship claims. Credential validity by
itself yields neutral UNK; it must not turn an ordinary signed human document
into PA. This bridge does not verify media, claims, signatures or revocation.
It is not wired into the gateway, extension, site checker or production allowlist.

Proposed adapter semantics (not general C2PA value aliases):

| Explicit supplied claim | Research candidate | Missing requirement |
|---|---|---|
| `ai_generated_then_human_reworked` | PA | Authenticated, accepted upstream evidence of both stages |
| `ai_generated_without_human_intervention` | FA | Authenticated, accepted evidence covering the full claimed workflow |
| `human_origin_claim` | neutral UNK | No human-authenticity clearance is offered by this bridge |
| No decoded claim, unbound claim or non-assertable credential | neutral UNK | Cannot infer authorship from credential quality or missing human evidence |

The values are deliberately narrower than “AI present” or “AI generated”:
neither of those proves whether a human later edited the output. PA and FA keep
their individual jobs. F-083 permits evidence in support of their jobs; it never
permits an inference from the absence of human evidence. A valid signer can still
make a false statement, so signatures and these mappings are not truth guarantees.

Each supplied claim needs an exact lowercase SHA-256 subject match, an opaque
evidence reference and an explicit upstream binding-verification observation.
A boolean is an adapter observation, not proof. Release requires real adapters,
accepted policy and independent verification beyond this pure function.
Only PA/FA/UNK research candidates are reachable. Candidate records always carry
`production_assertion: false` and `independent_release_validated: false`.

Rollup rejects mixed subjects, malformed objects and inconsistent observations
under the same evidence reference. It deduplicates repeated evidence. Different
supported authorship claims, including a human claim opposed to AI claims, return
CONFLICTED/UNK with every source retained. A conflicted credential cannot be
hidden by another candidate. No count of duplicate or weak observations becomes
independent corroboration; `independent_source_count` remains null. “research
eligible” is eligibility under this experimental mapping, not a live tag.

Run `python3 scripts/demo-tag-bridge.py` for synthetic credential-only, PA, FA,
conflict and missing-evidence examples. Tests are in `tests/test_tag_bridge.py`.
No actual content is read or uploaded. X-07 remains a recorded scope boundary
with deferred/candidate disposition; these internal functions do not adopt a
media product or create an additional user-facing surface.
