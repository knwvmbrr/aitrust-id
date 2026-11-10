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
