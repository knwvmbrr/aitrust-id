# Independent draft privacy check

Architecture before implementation · Codex · 2026-10-13.

Add an explicit `privacy` mode to the existing authenticated `/v1/evaluate`
request, preserving the default complete pipeline and the assertion schema.
Privacy-only work normalizes text and runs the current local redactor; it never
calls the PS evaluator. The result records the actual redactor and gateway
identities, uses `procedural-redaction-v1`, and may contain only the existing
`PII_REDACTED` procedural observation. No PII_OUTBOUND code is adopted or released.

A user-run `aitrust.py privacy draft.txt` command reads only the supplied input,
uses the existing private bearer credential and loopback endpoint, and displays
a short review reminder. It neither edits a file, submits to an AI service,
reads browser drafts automatically nor uploads research data. JSON export remains
explicit and potentially identifying. The default PS checker stays unchanged.

Risks: a no-finding result must not imply that a draft is safe; masking can miss
details or mask ordinary text. The command must reject mismatched pipeline,
redactor, calibration and model identities, arbitrary tags or metadata, and
invalid/private credentials. Privacy mode must still require redaction, auth,
input bounds, cancellation, nonce/signing and concurrency controls. An evaluator
outage may not disable privacy-only work. A redactor failure must withhold it.

Prove request-mode refusal, existing default behavior, schema and identity checks,
brief/no-finding output, private input exclusion, cancellation and actual service
independence with the owned evaluator stopped. Refresh the complete-input Linux
setup and replay evidence when bound sources change. No local Docker is used.
Keep physical/human acceptance and independently labeled PII recognition open;
manual pre-send checking is not browser interception or an outbound-tag release.

## Observed recovery defect and repair plan

The real privacy-only request worked with the owned evaluator stopped. Recovery
then failed. A separate owned-container probe confirmed that Podman's dynamic
private address changes across stop/start, while an explicitly reserved address
does not. The gateway's inspected private URLs must therefore bind reserved
backend addresses. Select two usable IPv4 addresses only from the newly owned
internal subnet, exclude its gateway and broadcast, refuse ambiguous/public or
undersized networks, pass explicit IPs at container creation and verify their
effective values. The gateway's published port and network isolation stay fixed.
This changes the setup input and requires fresh clean-clone acceptance.

Also replace cached engine-health trust after restart with a live health command.
Check address stability and actual privacy/replay behavior after recovery; never
count a cached Healthy flag as successful restoration. The original staging
services stay unchanged; only newly owned synthetic dependencies are disrupted.
