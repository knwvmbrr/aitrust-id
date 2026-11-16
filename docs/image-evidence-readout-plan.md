# Image evidence readout increment

Owner: Codex image-evidence lane. PM: Codex integration lead. Date: 2026-11-16.
Scope: optional attached-PNG method F-025, supporting future T-FA/T-PA work.

## Architecture before implementation

The existing pinned SDK adapter already reads attached PNG manifests and returns
separate asset-binding, claim-signature, signer-trust and revocation observations.
Its command-line result is JSON only. A person currently has to translate those
machine states themselves; a matching signature can be mistaken for a statement
about the image's origin or truth.

Add an opt-in `--format text` to the existing command, leaving JSON as the default
and preserving exit statuses. A separate small presentation module accepts only
the supported minimal result states and emits fixed sentences for each axis.
It never renders SDK assertions, authors, GPS, URLs, filenames, asset hashes or
untrusted strings. AI origin remains **Unknown**, including when no manifest is
found. No additional parse, network request, model, tag or credential is created.

The pinned package/native hashes, input/CPU/output/memory/deadline limits,
per-reader no-fetch settings, private-report boundary and worker transport stay
unchanged. Source inventories and the existing optional real-SDK CI trigger must
include the new formatter and its tests. A text result is a view of existing
observations; it does not add detector accuracy or provenance certification.

## Risks and acceptance

- A readable sentence could merge separate axes into a misleading overall pass.
  Keep binding, signature, trust, revocation and unknown AI origin on separate lines.
- Untrusted embedded metadata could be printed as trusted copy. Use fixed
  mappings and refuse malformed states; test synthetic private and terminal
  control markers even in otherwise plausible summaries.
- Presentation errors must not fall back to a clean finding. Return the existing
  UNAVAILABLE/exit-2 boundary and reveal no raw parser error.
- A new CLI option could break automation or worker protocol. Retain default
  JSON, original exit codes and private export; reject text-mode worker calls.

Exercise real signed, altered and unsigned pinned fixtures, unavailable input and
explicit private export, plus exact-axis, unknown-state and privacy fault tests.
Use the existing optional environment; do not create an image signing credential.
F-025 remains its already completed parser job. T-FA and T-PA remain open at 20%;
X-07's image-origin/replacement-C2PA issuance boundary is unchanged.
