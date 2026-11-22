# Bounded source-archive capacity v3

Implementation plan before code. Base: 2f03b9de83daab98ed8633c80c12e9217a822799.
The actual committed tree has 12,817 files and 128,272,227 source bytes. Its
canonical metadata length is 2,347,273 bytes (hash placeholders have exact SHA256
length). V1/v2 permit 128,000,000 decimal bytes, not 128 MiB. V2 inspection also
counts metadata against that limit, so its aggregate is 130,619,500 bytes. No
new archive has passed that old limit; prior 128 MiB budget labels are historical
planning mistakes, not execution. More current receipts and the MCP cohort make
this a real release-source blocker. Do not omit notices or immutable history.

## Contract

Keep source_snapshot.py (24df1006...) and source_snapshot_v2.py (baa1ce4b...)
byte-identical. Add a separate v3 serializer. Preserve the existing wire/profile,
Git identity, ordering, canonical USTAR/gzip headers and small-archive bytes.
Only active builder, authentication reader, source-graph adapter and relevant
tests select v3. Legacy observer imports remain untouched. No legacy globals are
modified or temporarily overridden. The graph binds all three serializers.

V3 raw source limit is 256,000,000 decimal bytes; metadata has a separate
5,000,000-byte ceiling. File count remains 16,384, each source at most 32,000,000
bytes, compressed archive at most 64,000,000 bytes. All names, modes, source
commit, private-template, link, duplicate and exact-manifest restrictions remain.
The decompressed limit is calculated from raw source + metadata + 512-byte
headers and at most 511 padding bytes per member, two end blocks and at most
10,239 record-padding bytes. No generic/unbounded decompression.

Use a bounded gzip output buffer during build, refusing before a write exceeds
64 MB. Inspection incrementally inflates in 64 KiB blocks and hashes source
payloads, retaining metadata and bounded records rather than the entire expanded
tar. Reject compressed truncation/concatenated members/trailing data, unsupported
headers, nonzero padding and extra tar content. Check metadata size before
collecting/parsing it. Compare exact metadata bytes to canonical serialization
from observed source rows and trusted commit/profile, refusing numeric aliases,
whitespace and field-order changes without touching the historical parsers. Current canonical small archives must remain byte-exact
and accepted; stricter rejection of unsupported hidden framing is documented.

The builder's retained source data is bounded by 256 MB plus bounded compressed
output, metadata and tables; inspection avoids an additional 278 MB expansion
copy. Estimate a conservative sub-768 MiB operational envelope rather than claim
an exact Python allocator limit. Read-only Linux qualification enforces a 768 MiB
address-space limit and records actual peak memory. Trusted Git commit/blob reads
remain owner-selected; no received archive is extracted, executed or used to
select a Git repository or trust root.

## Ownership and verification

New scripts/source_snapshot_v3.py; narrow active imports in
scripts/build-source-snapshot.py and scripts/verify-source-provenance.py;
tools/distribution_artifacts.py source-snapshot consumer/evidence selection;
source/provenance/graph tests; this plan; a read-only standard Ubuntu qualification
workflow if needed. Root owns inventory, revalidation, state, scope, publication
and later main signing. Do not change policy/admission or the MCP branch.

Use a sparse new worktree to avoid another 130 MB checkout below the local disk
reserve. Local validation is only syntax and small inert fixtures. Actual current
>128 MB build/inspect, old-reader refusal and larger boundary controls run only
on disposable Linux with sufficient disk, no signing, service, credentials or
package/model downloads. Preserve failed controls and old receipts. Test separate
raw/metadata accounting; per-file/count/compressed/metadata/expanded refusals;
small v1/v2/v3 byte parity; unchanged old globals; active source-graph bindings;
truncated/concatenated/hidden input; no output overwrite.

## Risks and limits

Active CLI/graph hashes necessarily change: old attestation packets and active
capability receipts remain historical until a real new source-bound replay. Old
source observers still bind immutable v1; v2 is preserved too. Same format does
not make old bounded readers accept larger archives. A capacity change does not
clear licenses, attest a release, approve all fourteen routes or finish F057/X02.
No local large archive, install, build, source-cap waiver or production action.


PM selected one scoped same-repository push qualification on the exact
`codex/source-snapshot-v3` branch, avoiding a new draft PR and its unrelated
known-stale whole-inventory checks. The new read-only workflow may also run
from filtered future same-repository PRs; no main signing or dispatch is added.
Its single Ubuntu job uses existing standard Python setup, no project installs,
all 16 focused controls without skips and one actual committed-source artifact.
Only a fixed bounded JSON summary is retained, not the archive, SPDX or source.
