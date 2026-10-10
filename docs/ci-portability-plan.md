# Hosted engineering checks — portability repair

The live hosted run at `f5186bb` started successfully. The previous billing-lock
state is stale. Release gates correctly refused accessibility/independent accuracy,
but regression, network-isolated and site jobs also failed. Preserve the release
refusals while repairing the engineering defects; do not turn missing evidence
into a green release or drop a failing job.

First reproduce the exact Linux measurement difference. Counts, categories,
provenance, denominators and source identities must compare exactly. If the only
difference is floating-point Wilson arithmetic, allow only a documented tiny
absolute bound for interval endpoints, with finite/type checks and negative tests;
never tolerate changed counts or substantive statistical differences.

The route guard currently fingerprints an ignored raster share image rebuilt by
host-specific font rendering. Bind its versioned generator and template rather
than rendering-dependent pixels; retain exact deployed-byte verification and
explicitly reject symlinks/unexpected executable sources. Add controls proving
pixel changes do not masquerade as processing-source changes, while changed
source, dependencies and routes still fail. Do not weaken the device-method hash.

Run the full bounded checks, refresh source-bound receipts, and demonstrate the
repair in actual hosted CI. The main branch has no protection today; F-054 stays
open until required checks and intentional failure blocking are also exercised.
Record the original failure and correction. F-118's third-party recomputation
needs this repair: previous local execution alone did not prove Linux portability.
No tag accuracy, certification, legal or real-device acceptance follows from CI.

## Diagnosed differences and selected repair

The 86-case Linux run had identical classifications and categories. Only Wilson
endpoints differed, by at most `2.220446049250313e-16`. The verifier accepts an
absolute difference of at most `1e-14` on interval endpoints only, after checking
shape, finite numeric type, [0,1] bounds and order. Everything else, including
counts, points, denominators, hash identities and candidate release thresholds,
remains exact. No statistical threshold comparison is rounded or relaxed.

The ignored `site/public/share-card.png` is the only host-rendered source-inventory
exception. Its versioned `site/scripts/prepare.mjs` template remains bound.
Symlinks are rejected before the exception; unexpected scripts still enter the
inventory and fail review. Actual publication verification still checks image
bytes against that deployment's build. The device bundle remains hash-bound.

Negative controls cover non-finite/wrong-type/out-of-range/reversed intervals,
changed counts/points/denominators/gates/source identities, missing/extra fields,
substantive interval changes, changed templates and excluded-asset symlinks.

The hosted rerun at `ef13126` confirmed network-isolated checks but exposed the
regression artifact path under `eval/`, which the common atomic report writer
refuses. Both CI producer and upload now use the approved `output/verification/`
scratch path. A test executes the exact configured command and checks its actual
86-case report. The writer policy and missing-artifact upload refusal are retained.
