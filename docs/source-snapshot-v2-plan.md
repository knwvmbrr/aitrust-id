# Version the larger source-archive serializer without rewriting observations

The current 16,384-file capacity change modified the entire source_snapshot.py
file. Native and nested-runtime inventories legitimately bind the historical
10,000-file module even though they use only its unchanged read_file helper.
Their verification now refuses source drift; silently changing their recorded
observer/time or source hashes would misrepresent an earlier observation.

Restore v1 byte-for-byte to SHA256
24df10061afea39710fb65799d54d386c177caed80629a4f15bc5384fc2c17ee.
Add source_snapshot_v2.py with its own explicit build/inspect implementations and
16,384-file ceiling. It may reuse immutable v1 safety helpers/constants/read_file;
it must never change v1 globals or wrap calls with a temporary global override.
Keep the archive format/profile and all existing byte/path/time limits intact.

Only active source-archive build/authentication entrypoints, their tests and the
artifact graph move to v2. Legacy read_file/unique consumers and historical
inventory manifests remain untouched. The artifact graph binds both modules,
builder and verifier; PM registers the new source path in shared inventories.

Verify exact v1 bytes, small-archive v1/v2 byte parity, no legacy-global mutation,
larger v2 inspection and the 16,385-member refusal before blob reads. Inspect the
retained actual 12,484-file archive at its exact31b source commit, then execute
current native/nested consistency checks without claiming fresh archive replay.
Preserve the original failed protocol execution and every historical observer.
