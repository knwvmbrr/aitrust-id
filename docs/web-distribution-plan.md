# Website JavaScript notice delivery

Architecture and risk plan recorded before implementation. Base:
`3a1e63766b9403c575f7e25ae45e65d9bfbb7647`.

The normal website bundles JavaScript dependencies. The source notice store has
complete collected license bytes for all 35 non-development site lock packages,
but the public assets do not carry their selected notice bundle. React's retained
MIT text requires preserving its copyright and permission notice in copies or
substantial portions. This increment repairs carried text, not legal clearance.

## Bounded implementation

`tools/web_distribution.py` selects every non-development package in the exact
site lock, matches its registry origin, version and integrity to the existing
collected observation, and reads every referenced complete notice. Duplicate,
unknown, changed, missing, unsafe or oversized inputs refuse. Unrelated image or
optional model observations are not prerequisites for this selected notice job.

Generate deterministic `site/public/web-licenses/THIRD-PARTY-NOTICES.txt`, an exact
package/archive/notice-span binding index and selected-cohort SPDX JSON. The index
identifies complete original notice byte ranges. SPDX declared licenses are
observations; concluded licenses remain NOASSERTION. The cohort includes all
35 non-development lock entries, including potentially tree-shaken packages. It
is not a proof of the bundle's complete dependency graph, source correspondence
or embedded/native/runtime permission.

The mandatory first normal build step is
`python3 ../scripts/web-distribution.py prepare`. It precedes all existing build
steps without changing their order. No network, installation or package execution
is added. Static files travel with Vite's normal public-directory copy.
`check-built` reconstructs the selected files from trusted source inputs and
compares the actual built artifact. `reviewed-release` invokes that check and the
existing web-checker dependency policy. The latter remains blocked until its
other real obligations are reviewed; an included file cannot approve itself.

Initial replay rehashes only the selected already-cached npm archives against
both lock integrity and observed archive SHA-256, then compares the complete
retained notice members without extracting or executing packages. Acquisition
is not part of a normal build or verification. Archive compressed/expanded,
member, notice and aggregate limits apply before unrestricted parser allocation.

## Safety and evidence

Use descriptor-bound regular reads; refuse symlinks, hardlinks, FIFO/special
files and changed identities. Build outputs are a fixed three-member directory.
Refuse unknown pre-existing members; stage complete outputs first, compare
source stability, and publish through an owned temporary directory. A failed
preparation must not overwrite an earlier good directory. Replacing the directory
is not a claim of filesystem crash transactions or physical erasure.

CLI diagnostics are fixed and do not echo malformed arguments, private cache
paths or raw exceptions. Optional output receipts contain counts and hashes,
not private paths or raw command logs. No credentials, capture permissions,
endpoints or production service changes are involved.

Meaningful controls cover real selected package and notice identity, incomplete
or changed notices/locks, injected unknown packages, unsafe input/output files,
failed preparation preserving prior output, changed built notices, deterministic
reconstruction, fixed private diagnostics and independent PS source operation.
Actual current built-artifact proof is separate from authored negative controls.
F-057 and X-02 remain open: this notice repair does not close the other
13 distribution profiles, source offers, full SBOM or artifact attestation.

## Observed correction before final proof

The initial claim that all35 records had archive-carried notices was wrong.
Preparation refused before archive replay because react-remove-scroll-bar2.3.8
has no matched notice file. The first refusal is retained. The corrected job
carries34 archive-derived notice records and one clearly separated upstream
project supplement. The exact2.3.8 registry gitHead was404; the independently
pinned public project commit carries a full MIT text and package version2.3.7.
This is real project licensing evidence, not exact-release source correspondence.
The notice bundle, index and SPDX limits keep that unresolved distinction.
The actual cached replay subsequently checked all35 tarballs, preserving the
empty archive-notice observation rather than fabricating a member.

## Resource correction after independent review

A reduced1000-byte cap exposed allocation before the original final-size check:
37,003 notice bytes were retained and47,849 bundle bytes were constructed before
refusal. No large hostile allocation was attempted. The corrected selector
reserves a combined logical budget for source bytes, each included notice
occurrence (including duplicates), the planned copies and every header before
reads/retention. The descriptor reader receives the remaining source allowance.
A separate check precedes every bundle extension. This bounds logical byte
processing; it is not an exact process-RSS or filesystem-crash guarantee.
The real notice bundle's bytes remain unchanged.
