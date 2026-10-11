# Inspect image evidence without inventing an image-origin standard

X-07 preserves the explicit boundary against competing with C2PA on image
provenance. This project does not issue image-origin credentials or a replacement
C2PA credential format in the current release or the next release under this
policy. The runtime gateway refuses all non-text modalities before contacting
its dependencies. Current asserted tags are PS and procedural PII_REDACTED.

The boundary does **not** remove the proposed FA/PA tags, C2PA inspection,
watermark research, conflict adjudication or canonical non-text subject jobs.
Inspecting an external manifest, preparing an image's subject hash, and issuing
an image-origin credential are different jobs. They retain their own acceptance.
An intact signature does not establish the truth of an image's content.

`spec/image-provenance-boundary.json` records the current and next-release
exclusion. `scripts/verify-image-provenance-boundary.py` checks it and the
producer's actual asserted allowlist. Its controls reject a future image-issuance
flag, replacement-credential issuance, removed limits, duplicate fields and
silent exceptions. Runtime tests submit image, audio, video, document and code
requests to the real gateway application and prove refusal before any redaction
or evaluation request. CI executes these controls with the existing full suite.

A future proposal to change this boundary needs an explicit recorded owner
product decision and a versioned review of code, policy, public claims and tests
before activation. Editing a configuration or choosing another tag name alone
is not that decision. This boundary is complete for the declared release routes;
it is not a claim that future software can never violate it or that any image
provenance tag is validated.
