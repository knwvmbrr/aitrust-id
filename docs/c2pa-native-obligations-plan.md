# C2PA published native-source obligation graph plan

Recorded before implementation, November21,2026. This isolated lane supports the
existing F-057/X-02 distribution review. It does not change tags, permission gates,
release policy or existing C2PA cohort records.

## Actual missing evidence and discovered source

The existing exact c2pa-python0.38.0/native SDK0.91.0 cohort binds two wheel native
libraries to upstream release ZIP bytes. Its historical source-commit Cargo.lock
HTTP404 and full source-archive retrieval limit remain preserved.

The official crates.io `c2pa-c-ffi`0.91.0 package is106,801bytes, checksum
`612bffa120fdb58b5b6767602b0c0c77a20e139a7102b3e13e85236308ee49f4`.
It contains a108,284byte Cargo.lock with441 packages/1,131 dependency edges,
440 crates.io checksums, and one local root. Its Cargo.toml.orig matches the
retained e7cc666c3409bdaf4cea8e49046dfbf8290dff89 manifest exactly. Its VCS metadata
declares that commit and `c2pa_c_ffi` path. Cargo documentation explicitly says
published Cargo.lock is included and may be generated; it also says VCS metadata
does not guarantee all archive code matches Git. Therefore this is a real exact
published-package lock graph, not an authenticated release-binary build graph.

## Architecture

Own new `tools/c2pa_native_obligations.py`, a small executable verifier/collector,
focused tests, this guide/result and `sbom/c2pa-native/{manifest.json,sources/*}`.
No old cohort/consumer/global state edits. Parse the exact official lock and
resolve every version-qualified edge, rejecting missing/ambiguous nodes rather
than fabricating versions. Preserve normal/build/dev/target/optional declarations
from each normalized package manifest separately from the lock's union graph.

Retrieve each exact checksummed registry archive from official static.crates.io
into an explicitly selected private cache. No Cargo/package code execution,
installation, builds or model downloads. Bound archive bytes/count/expanded
sizes/member names and retained text; retain source manifests, VCS declarations
and applicable shipped license/notice/copyright texts with exact archive/member
identities. Use source-bound machine data with package IDs, exact dependencies,
license declarations, notice paths, conservative obligation facts and unresolved
embedded-code/feature/build relationships. Do not infer permission from an SPDX
expression or a successful parser.

Provide a functioning offline verifier that re-derives the graph and checks all
retained source/notice bindings and fixed false clearance flags. An explicit
private-cache replay rechecks every checksum and reconstructs selected members;
checkout-only consistency receives no fresh archive credit. Refuse substitutions,
missing/extra/ambiguous records, unknown permission promotion, unsafe archives,
limits or source drift. Output bounded public counts/reasons, never private paths.

## Risks and completion evidence

At most256MiB private compressed cache and2GiB disk reserve; bounded in-memory
streaming per archive, no extractall. Cap individual archives16MiB, expanded
128MiB, members20,000 and retained text4MiB; reject links/devices/unsafe/duplicate
names rather than execute them. Unexpected over-bound artifacts remain explicit
blocked nodes, not silently complete coverage.

The published lock includes optional/dev/target alternatives and is not proof
that every node is incorporated in either selected native binary. Conversely it
cannot rule out extra system/embedded code. Preserve this distinction, including
OpenSSL/native build scripts and unselected platform obligations. No blanket
binary reproducibility, source-offer sufficiency, legal judgment, permission
clearance or original completion claim.

Verify actual source collection and offline/cache replay, plus focused malicious
input/graph/source drift controls. Send source-bound machine data to the
14-distribution graph owner, obtain distinct review and let PM integrate policy
consumers/registrations. Historical404 stays valid for its exact URL; newly found
published lock is separate evidence.
