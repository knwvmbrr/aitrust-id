# Private tools publication verification

The Fleet and hash-inbox CLI proofs remain separate from tag release validation.
The website controller must own one temporary server for the complete build,
catalog, workflow, accessibility, feedback and policy checks. Its final policy
phase must finish before shutdown. A standalone command that assumes an unrelated
server cannot be part of a reproducible release gate.

Add the policy phase to the ordered build controller and its existing failure
controls, remove only the duplicate standalone policy invocation from the
capability manifest, and fingerprint the policy checker explicitly. Keep every
policy assertion and historical failure. Changing the common capability manifest
requires fresh source-bound receipts for all five capabilities. Review the final
boundary inventory before running those checks; freeze source inputs during them.

Risk: an incomplete sequence could appear successful. The aggregate continues to
require every named phase and zero failed/aborted children. Only owned temporary
servers are closed. No production endpoint or tag method changes.

## CI privilege correction

The original no-egress job ran the entire suite as root after namespace setup.
Both new tools intentionally refuse root, so all 62 normal-owner lifecycle
cases failed at setup despite their separate isolated non-root jobs passing.
Keep network namespace creation and loopback setup privileged, then use
`setpriv` to select the existing checkout owner's UID/GID, remove supplemental
groups and capabilities, and set no-new-privileges before Python/pytest.
Run the same full suite and preserve its original exclusions; do not permit
root in either application or skip the lifecycle cases. The actual GitHub job
remains the acceptance for this Linux-only runner change.
