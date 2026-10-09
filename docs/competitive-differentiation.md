# Competitive differentiation — reviewed 2026-10-09

Research input: Claude's October 9 comparison, supplied by the owner. Reviewed by
Codex against current source, executable checks and the primary sources below.
The original pasted research remains the owner's attachment. This revision is a
bounded review, not confirmation of every external statistic in that input.

AITrust-ID's full design remains a multi-tag system: distinct claims, methods,
evidence, modalities, personal routes, organizational policy, receipts and public
correction. An overlapping provenance component does not make that scope identical
to another product. The current functioning PS preview is narrower than the full
planned product. Catalogue panels demonstrate the design, not 14 running methods.

## What the new work actually does

| Component | Demonstrated job | Remaining before user-facing completion |
|---|---|---|
| `services/adjudicator/verdict.py` | Deterministically interprets supplied signature/trust/binding/revocation status codes, including missing verification, unknown codes and conflicting revocation | Real bounded file parser/SDK adapter; authenticated, subject-bound, fresh upstream evidence; real signed/revoked/malformed files; supported formats and route gates |
| `services/adjudicator/adjudicate.py` | Applies a proposed precedence policy to supplied, explicitly verified observations; reports disagreement without picking an arbitrary winner | Accepted per-claim policy, authenticated subject/version binding, actual supported manifest/watermark readers and external validation; a caller flag is not cryptographic verification |
| `eval/measure.py` | Computes Wilson intervals, disagreements, conditional accuracy with answer coverage and supplied survival observations | Real fixtures, adapters, sampling protocol and collection before any market/platform survival claim |
| `scripts/demo-adjudication.py` | Runnable, clearly labeled simulation of supplied status codes and conflicting claims | No actual Nikon media, OCSP responder, competitor client or watermark is exercised |

The initial **188 passing tests** reproduced. Review then found absent verification
could default to VALID, lenient unknown codes could remain assertable, OCSP-attempt
could be confused with a clean result, revocation ordering could choose the first
optimistic answer, and manifest/watermark inputs could assert without verification.
Codex repaired these and added boundary probes. Original simulated cases now supply
explicit verification facts; the acceptance boundary was not relaxed to keep them
green. See [execution evidence](../runs/2026-10-09-scope-completion-checks.json).
This is tested research component work; no new tag is released or registered.

## Corrections and unresolved research claims

| Input claim | Review conclusion / required fix |
|---|---|
| Nobody adjudicates cross-layer conflicts | The latest [Nemecek paper, v2](https://arxiv.org/abs/2603.02378) reports a cross-layer audit protocol and experiments on 3,500 images. Their reported result is research evidence, not proof of every deployed product's behavior. Do not claim universal exclusivity. |
| Our complete local C2PA verification is shipped | False for this checkout. The new modules consume statuses/signals, not media files. Keep the component and finish a separately gated adapter; do not advertise a file validator. |
| Nikon regression / competitor accuracy measured end to end | The test uses constructed status strings and hardcoded competitor verdicts. It is a useful simulation, not a measured competitor run or independently obtained Nikon regression artifact. |
| 49 tests are a conformance target | They test a proposed local mapping/policy. They do not establish C2PA program conformance, cryptographic correctness, accuracy or interoperability. Test execution also requires pytest; runtime modules use stdlib. |
| 93 uploads buys ±20% | The function requests a total width of 20 percentage points at 95% confidence near p=0.5: roughly ±10 points. Sample design, representative assets and dependence between uploads remain separate. |
| Supplemental application/disclaimed words establish a weak harmless conflict | Official case documents, including the cited suspension, remain unverified here. USPTO says [the whole mark, including disclaimed matter, is considered](https://tmep.uspto.gov/RDMS/TMEP/print?href=TMEP-1200d1e11717.html&version=current). A disclaimer or register choice is not clearance or permission to coexist. No filing/name decision follows from this review. |
| A VPAT makes us procurement eligible | [ITI describes an ACR based on VPAT as a reporting tool](https://www.itic.org/policy/accessibility/vpat). It is useful buyer evidence; eligibility depends on procurement requirements and actual conformance. Automated axe passes alone do not complete an ACR. |
| No local watermark detector is possible ever; quotas cannot rise | Universal future claims are unsupported. Distinguish access to current vendor keys/interfaces from an impossibility theorem. Verify the current product and threat model before publishing a comparison. |
| All extensions share one default, revocation codes are all dropped, all 243 conformant records imply no failures | Pin each repository/SDK version and trace full vs failures-only results and adapter behavior. A directory of conforming products is not a census of failed candidates. Counts and code-string searches alone do not prove runtime behavior. |
| 1,400 installs is the entire market; nobody has an ACR; no survival study exists | Unverified exhaustive claims. Store buckets, different browsers, prototypes and unlisted integrations cannot establish the whole market. Keep dated observations with exact search boundaries instead. |
| 61.22% FPR applies to current competitors generally | [Liang et al.](https://arxiv.org/abs/2304.02819) reports a specific evaluated population and detectors. Do not transfer that rate to today's versions, other populations or our methods. |
| TIP licensing, current serial/status, SynthID rollout, CVE and installed-base figures | Not independently verified in this pass. Require primary record retrieval, exact version/date and reproducible observation before promotional use. |

## Keep the value and finish the engineering

1. Preserve orthogonal content-binding, signer trust and revocation observations.
   Required status authenticity, validity time and subject binding are adapter gates.
2. Track disagreements per claim. Manifest/watermark equal standing is a proposed
   policy, not a universal equivalence of reliability or proof of human authorship.
3. Publish uncertainty and error denominators. Missing answers remain visible;
   conditional accuracy is not coverage or overall completion.
4. Prepare an ACR evidence matrix covering the catalogue, checker and extension,
   with real keyboard, screen-reader, phone, contrast, zoom and failure tasks.
5. Scope a privacy-preserving revocation snapshot under existing integrity/receipt
   work. It needs issuer authenticity, freshness, replay/rollback defenses, authority
   and certificate identity, omission semantics, key rotation and conformance review.
   This report does not implement or certify a feed.
6. Scope manifest/soft-binding survival under integrations/validation. Create real
   fixtures, lawful platform tasks and independently reproducible results; the
   statistics module is not an upload/download harness.

NeMo Guardrails can be an adjacent implementation toolkit, but it is not a direct
reader-labeling or provenance standard comparable. Avoid category-wide claims of
superiority. Compare demonstrated jobs, reader friction, licenses, privacy,
limitations and reproducibility on the same stated input/scope.
