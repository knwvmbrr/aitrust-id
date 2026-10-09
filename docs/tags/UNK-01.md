# UNK-01 — Insufficient evidence and result states

Planning contract · 2026-10-08. No new runtime support, registration or release is asserted.

## Baseline job and outcome

Represent insufficient evaluated evidence separately from pending, no-finding, unsupported and unavailable results.

A reader can tell what was evaluated and why a tag could not provide its claim.

## Inputs, outputs and boundaries

**Inputs:** A valid evaluation result and its abstentions.

**Outputs:** An explicit result state and reason explaining insufficient evaluated evidence; pending/unsupported/unavailable/no-finding remain distinguishable.

**Limits:** UNK itself is not emitted by the current runtime; An outage must never masquerade as evaluated uncertainty; No finding is not a clearance

## Method and evidence development

- Reconcile existing protocol codes and six-state UI/proposal meanings without silent taxonomy changes.
- Implement explicit state transitions and route-specific reason codes.
- Test empty evidence, rejected candidates, timeouts, unsupported inputs and retries.

## Acceptance and error boundaries

- Unavailable processing cannot appear as evaluated uncertainty or success.
- No-finding never certifies safety.
- Protocol changes require compatibility tests and the established approval process.

Numeric thresholds, supported languages/subjects and hardware/latency requirements are defined and accepted for this claim before independent evaluation; no PS threshold is borrowed by default. Existing editorial floors are not measured accuracy.

## Prerequisites and failure

WP-PROTOCOL, WP-VALIDATION, WP-UX supply only the necessary primitives for this selected claim/route, not completion of unrelated tags.

Withhold or disable only the affected claim/route. Required auth, privacy or integrity failures must not be bypassed. Independent routes stay available where their own prerequisites are met.

## Delivery, owners and maintenance

Choose the supported personal route explicitly. Small code-only tags coexist; in-use explanation stays brief. The site carries method, input/output, privacy, limitations, tests, use/download instructions and evidence. Supported route installation/removal and human accessibility checks are part of release.

Codex implements and records execution; Claude reviews claim/evidence design; Michael accepts scope/release; independent reviewers provide required ground truth or attestation. Reviewer assignments are not presumed. Personal capabilities stay free; organization administration is separate. Revalidate affected methods when sources, capture, parser, model, corpus or claim versions change. Corrections preserve old record identity.

Full work package: [TAG-UNK](../scope-delivery.md#tag-unk). Records: T-UNK, F-004, N-002.
