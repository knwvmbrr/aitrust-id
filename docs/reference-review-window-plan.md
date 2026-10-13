# Declared reference review windows — architecture before integration

F-020b and the NF/FI tag jobs remain open. Reuse the existing hash-bound
`declared-reference-review-windows/1.0.0` policy and validator rather than inventing
another source-date format. Add an optional `--review-windows` preflight to the
existing local reference research command. Default operation and its successful
observation profile remain unchanged. No tag mapping, endpoint, telemetry, model,
permission or service is added.

An explicitly supplied policy must bind the exact captured corpus manifest and
each attached document's bytes. Require one declared window for every attached
document. Evaluate it using an aware UTC machine clock: start inclusive, expiry
exclusive. Missing, unopened, elapsed, malformed or differently bound windows
refuse before a model worker starts. Check again after a completed comparison,
before writing any details, so a window that expires during the worker cannot
produce a usable guarded result. The same captured policy is used for both checks.

These dates are the caller's declarations. A passing window does not authenticate
its author, prove a reference was reviewed, show a source is current, establish
truth, calibrate the model or provide independent corroboration. Machine-clock
integrity and malicious same-account modification remain outside this control.
Keep `reference_freshness: unestablished` and all existing no-tag/release limits.

Private policy files use the existing bounded owner-held, no-symlink/no-hardlink
input reader. Console output exposes only a small fixed guard status and recovery
action; no document IDs, fingerprints, dates, paths or source text. Separately
requested private details preserve the existing observation and a separate
versioned window-check record. Never overwrite an existing result folder. No
partial result is saved on policy failure or post-worker expiry.

Verify valid and boundary times, corpus/document changes, duplicate/unknown policy
fields, missing/duplicate documents, malformed timestamps, naive clocks, private
file refusals, no worker on preflight refusal, post-worker expiry and unchanged
legacy defaults. Execute invented CLI controls and actual optional model controls
where the existing isolated environment is available; unavailable environments
are retained and skipped. Refresh all fingerprints affected by the shared check
manifest; generate copied guides and scope projections before fingerprinting.
Record implementation, limits and actual runs in state and changelog. This
component does not close full source freshness, independent tag accuracy or human
acceptance requirements.

Before the policy-preparation helper: reuse the same private packet writer to
create a new `review-windows.json` from the captured corpus and caller-supplied
UTC bounds. Bind every document automatically, without calling a preparation
step a review, inventing review dates or overwriting an existing folder. Exercise
that actual command and its refusal path alongside the guarded checker. Keep
the command summary free of fingerprints, dates and document identifiers.
