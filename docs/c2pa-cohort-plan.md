# Optional C2PA dependency cohort — architecture and risks

This increment extends X-02/F-057 source and notice evidence without changing SDK
activation, parser settings, tag assertions or license-clearance decisions.

Inspect the ten packages pinned by `eval/c2pa-inspection.lock` and fourteen distinct
wheels already selected in the private macOS CPython 3.12 / Linux CPython 3.13
inspection workbenches. These are two finite historical selections, not every
Python version or platform admitted by the lock. Bind the two C2PA wheels to
`eval/dependencies/c2pa-inspection.json` and the existing runtime source/native
hashes. Nothing is installed, imported from a package archive or executed.

Preserve exact notice and distribution-metadata bytes in a dedicated
content-addressed text store. Keep each original archive/member name, artifact
hash, selected official PyPI version/file record and source-archive notice
relationship. Compare shipped Python files to paths in each version-matched
source distribution without treating unmatched files or generated extensions as
reproducibly built. Retain the two missing C2PA wheel notices from its source
distribution; do not pretend those files were bundled in the wheel.

Compare the C2PA native wheel members directly with the upstream 0.91.0 release
ZIP members. Retain a small set of files from the release's exact source commit:
workspace/FFI/SDK Cargo manifests, README and MIT/Apache texts. The full source
archive exceeded the 64 MiB retrieval limit and was not retained. The root
Cargo.lock URL returns HTTP 404; this leaves the resolved native dependency graph
and native/transitive source/notice obligations open. A source release association
and matching native bytes do not prove which source/toolchain produced them.

The offline verifier checks a strict finite inventory, exact current lock/parser
bindings, source-tool fingerprints, every retained text digest, package/version
metadata, complete wheel RECORD digests and sizes, reviewed wrapper/native pins,
source relationships and explicit false clearance/release/build claims. Optional
private caches replay the actual artifacts and source members in memory. Archive
parsers reject traversal, ambiguous paths, duplicate entries, symlinks/devices,
encrypted ZIP entries, unreasonable member counts and declared/actual size excess.
No extraction or package hooks run. Missing caches do not grant replay credit.

Use independent synthetic corruption/refusal controls for archive parsing, RECORD,
foreign packages, changed inputs/notices, missing platforms and permission
promotion. Publish real-cache replay results separately from checkout-only
consistency. All data is public upstream software, not user inputs or credentials.
Do not add a public endpoint, package dependency, auto-downloader or active CI job.

Remaining obligations include resolved Rust/OpenSSL/libffi and other nested native
components, source offers and actual release packaging; publisher signatures,
reproducible builds, vulnerability review and unselected platforms remain unverified.
Neither a passing evidence check nor upstream license metadata closes X-02/F-057.
