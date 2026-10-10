# Reproducible development measurements and provenance

Architecture: preserve existing fixture bytes and historical label corrections.
Add a versioned sidecar with stable per-row identity, exact source-file/row hashes,
label basis, origin metadata and explicit unknown author/annotation information.
Missing provenance is reported as unknown, never invented or represented as
independent ground truth. Verify every active and historical row against the
sidecar, the existing dataset manifest and declared source references. A changed
example/label/hash needs an explicit new dataset revision.

Compute counts and denominator-aware metrics for each declared category and
source dataset. Publish unknown metrics as unknown, never as zero or perfect
accuracy. Recompute source counts before generating public performance evidence;
a report carrying the right fixture hash but fabricated counts must fail. Bind
evidence to detector, normalization, gates, fixture and report identities.

Risks: development category choices are not a representative population;
maintainer-supplied labels can be wrong; a source hash proves identity rather than
truth; missing historical attribution cannot be reconstructed from an account
name. Keep those limitations visible. Frozen independent held-out review,
accepted claim-specific policy, calibration data, reviewer agreement and physical
phone acceptance remain separately open. These components do not release a tag.

Acceptance: execute all five active sets; account for every row; exercise label,
hash, duplicate/missing ID, category and fabricated-count failures; prove metric
denominators and unavailable results on empty category subsets. Publish only
source-recomputed data and record the full execution identity and current limits.

## Executed measurement contract

The sidecar accounts for all 101 rows and their exact source revision, preserving
unknown original authorship. Five active files contribute 86 development examples;
15 superseded rows remain historical. Six input-form categories are assigned
without reading labels or predictions. Each dataset/category carries confusion
counts, precision, recall, false-positive/negative rates, denominators and Wilson
ranges. Calibration remains explicitly unknown. Category definitions are engineering
strata, not a sampling design or a claim about what real users encounter.

Both browser engines retain 127 input-free warm timing observations, grouped
separately from a recorded cold load. Quantiles and input sizes must recompute
from these rows. A clock-resolution zero is a recorded observation, not proof
of zero execution cost. Physical handset performance remains unmeasured.

`python scripts/verify-measurements.py` recomputes source counts, all category
metrics, 95% intervals, sample-size arithmetic and recorded timing summaries.
The ledger hashes the method, Unicode tables, category rules, gates, fixture files
and reports. Changed sources invalidate the published evidence and block a site
build. `python scripts/verify-dataset-provenance.py --verify-history` additionally
checks exact recorded Git source bytes and commit times in a full clone.

This implements F-107, F-109 and F-118's measurement/provenance jobs. The initial
ledger copied independent holdout and policy-adoption gates into these mechanism
rows. Those gates remain open under T-PS, F-108, F-050 and F-114. Reproducible
measurements cannot turn maintainer labels into independent ground truth.
