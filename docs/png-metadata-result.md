# PNG metadata reader: bounded engineering result

The new public CLI runs without the optional C2PA SDK, image packages or Docker.
It gives an explicitly selected local PNG a fixed metadata inventory and checks
its supported compressed scanline structure. Its source and actual execution
were first bound in `runs/2026-11-21-png-metadata-cli.json`. That first candidate is historical; the current corrected runtime is bound in
`runs/2026-11-21-png-metadata-cleanup-corrected-cli.json`.

Thirteen focused synthetic test groups passed. Afterwards, only the unsupported
fixtures were corrected to fully valid 16-bit, palette and 1×1 Adam7 payloads;
that affected group passed again. Runtime code did not change between those
executions. Ten current actual CLI controls then passed with source hashes
unchanged, using `-I -S -B` to disable site packages. They cover default readable
privacy, explicit JSON subject binding, no metadata, those three unsupported
variants, corrupt image zlib, excessive metadata inflation, recovery and
malformed arguments without echo. The focused suite additionally exercised
actual owned-worker timeout/output/nonzero cleanup, file/symlink/FIFO/drift,
closed-result refusals, PNG structure/text limits and the existing PS CLI.

The first separate evidence harness could not import the project's fixture
module because its script directory was `output/verification`. It failed before
invoking the product CLI. Its fixed harness explicitly selected the repository
root. The private diagnostic was retained; no product change or passing test
was inferred from that failure.

This is not a release validation or image-origin detector. File metadata can be
wrong or misleading. EXIF/ICC/Content Credential-shaped payload contents are
opaque here; signatures, trust, revocation, watermarks, authorship and truth are
not established. Raw encoded-file identity is not canonical decoded-pixel
identity. Unsupported variants and unavailable checks never issue tags.

No website, API endpoint, dependency, deployment, global scope/state or existing
credential-inspection contract changed. F-155 and full FA/PA acceptance remain
open, including permitted real watermark verification, explicit evidence/trust
semantics and independent tests. Current supported profile and resource/privacy
limits are in [the user guide](png-metadata.md).

## Cleanup ownership correction

Distinct review reproduced a completed-worker edge case: actual wait reaped the
child, then an injected error left a local completion flag false and cleanup
attempted to signal the old numeric process group. The signal was intercepted.
The original candidate and failed regression are preserved. Cleanup now signals
only if the child is still unreaped (`returncode is None`). The new regression
uses the actual PNG worker, confirms returncode 0 after the injected error, and
requires no signal attempt. Three affected worker groups pass, preserving actual
timeout/output/nonzero cleanup and closed-result refusal checks. Ten fresh
actual CLI controls pass with corrected sources stable. No unchanged full suite
was repeated, and earlier receipts were not rebound to the new runtime.
