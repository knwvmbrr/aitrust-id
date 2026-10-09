# PII_OUTBOUND-01 — Pre-send personal-information control

Planning contract · 2026-10-08. No new runtime support, registration or release is asserted.

## Baseline job and outcome

Warn about supported personal-information detections before a selected send action and let the user edit or cancel.

The user controls disclosure before sending, without an invisible copy of their prompt.

## Inputs, outputs and boundaries

**Inputs:** User input before submission to a supported service.

**Outputs:** A local pre-send warning plus edit/cancel/proceed controls; no automatic research record or transmission.

**Limits:** Detection can miss information; Must not submit or change content without a clear user action; Site forms are not an implementation of this tag

## Method and evidence development

- Define supported compose/send surfaces and capture permissions.
- Implement local inspection, short warning, edit/cancel and deliberate proceed.
- Test keyboard send, regenerated forms, paste, attachments and unsupported submission paths.

## Acceptance and error boundaries

- Supported send paths cannot transmit before the warning decision.
- Unsupported paths are disclosed; no blanket coverage claim.
- Consent, cancel and reset tests verify no hidden retention or secondary upload.

Numeric thresholds, supported languages/subjects and hardware/latency requirements are defined and accepted for this claim before independent evaluation; no PS threshold is borrowed by default. Existing editorial floors are not measured accuracy.

## Prerequisites and failure

WP-PROTOCOL, WP-VALIDATION, WP-UX, WP-CAPTURE, WP-PRIVACY supply only the necessary primitives for this selected claim/route, not completion of unrelated tags.

Withhold or disable only the affected claim/route. Required auth, privacy or integrity failures must not be bypassed. Independent routes stay available where their own prerequisites are met.

## Delivery, owners and maintenance

Choose the supported personal route explicitly. Small code-only tags coexist; in-use explanation stays brief. The site carries method, input/output, privacy, limitations, tests, use/download instructions and evidence. Supported route installation/removal and human accessibility checks are part of release.

Codex implements and records execution; Claude reviews claim/evidence design; Michael accepts scope/release; independent reviewers provide required ground truth or attestation. Reviewer assignments are not presumed. Personal capabilities stay free; organization administration is separate. Revalidate affected methods when sources, capture, parser, model, corpus or claim versions change. Corrections preserve old record identity.

Full work package: [TAG-PII_OUTBOUND](../scope-delivery.md#tag-pii_outbound). Records: T-OUT, F-024.
