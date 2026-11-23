# Received source archive binding to trusted Git

Architecture recorded before implementation on 2026-11-22. Parent authorizes a
separate engineering helper, not route admission. The previously reviewed rights
helper at 2932bb420e8a868b057bb31703372e29deaf78b8 stays unchanged.

The caller supplies an already trusted local repository and exact 40-hex commit,
separately from received compressed bytes. Neither an archive commit label nor
its internally consistent SHA-256 inventory establishes that it contains those
Git objects. This helper closes that specific identity boundary; rights policy,
cryptographic signature, production admission and original acceptance remain
separate.

## Architecture and bounds

- New `tools/source_snapshot_binding.py` and
  `tests/test_source_snapshot_binding.py` only, plus this plan and immutable
  execution/review/attribution records. No serializer, graph, signer, shared
  policy, old proof or ledger edits.
- Check immutable v1/v2/v3 source digests. Reuse v3's canonical streaming archive
  inspection (v1 safe paths/profile), including canonical metadata, member
  SHA-256, gzip CRC/end/trailing/concatenation and tar header/padding checks.
  Re-read only its bounded first metadata member after full inspection. Never
  extract, execute, write received members or accept a program from metadata.
- Existing limits stay: compressed 64,000,000 bytes, source 256,000,000 bytes,
  metadata 5,000,000 bytes, 16,384 files, 32,000,000 bytes/file. Git listing gets
  a separate 2,000,000-byte cap. No expanded archive allocation; v3 uses 64KiB
  inflation chunks. The received bytes API requires a bounded immutable `bytes`
  object; source bytes are never returned.
- A literal `/usr/bin/git` is run without shell using a closed environment,
  `--no-replace-objects`, disabled protocols/lazy fetch/global configuration and
  no optional locks. Only exact object IDs from the trusted tree reach
  `cat-file`. The supplied commit must actually be a commit object, not a tree,
  revision expression or archive-selected value.
- Obtain a bounded full `ls-tree -rzl` projection at that commit, validate every
  path, mode, type, size and OID, and compare its exact set and numeric modes to
  the validated received inventory. Links/submodules, missing/extra paths,
  changed modes/sizes, private/unsupported paths and over-budget trees refuse.
- A single bounded, owned `git cat-file --batch` process streams each trusted
  blob in 64KiB chunks. Independently verify its Git SHA-1 object framing/OID,
  length and SHA-256 against the received archive's validated member SHA-256.
  No lazy fetch, replacement refs or received source evaluation. This is byte
  identity with caller-trusted Git, not authentication of that trust decision.
- Whole operation deadline 60s, including archive inspection and Git operations;
  check it at every stream iteration and after archive validation. Owned child
  on a failure is killed/reaped within existing 5s cleanup; never signal an
  already reaped numeric process group. Bound captured listing output before
  allocation; streamed blobs are hashed rather than accumulated. No stderr or
  input/path echo. Refusals have closed fixed codes and a fixed message.

## Risks and controls

The key failure is a self-consistent forged archive with a real commit label.
Actual tiny Git fixtures will prove that v3 accepts coherent forged inventories
while this helper refuses changed bytes, equal-length changed bytes, missing or
extra paths and changed executable modes. Canonical archive passes. Also cover
wrong/noncommit identities, binary/empty blobs, malicious Git environment and
replacement refs, unavailable objects, parser/truncation refusals, listing and
stream budget/deadline faults, child cleanup and fixed diagnostics. Existing
v1/v2/v3 and rights hashes must remain exact. No local full repository archive,
SDK, native runtime, new dependency, download, signing or route admission.

Large real-archive qualification belongs to a later explicitly scheduled Linux
job. Tiny local command proof establishes only the helper's engineering
contract. The root graph/signer must explicitly adopt a reviewed helper before
any release credit; this implementation changes neither consumer.

Implementation detail: the public entrypoint owns a new isolated Python worker
for the entire received archive. The parent streams its already-bounded bytes,
enforces the absolute 60s deadline and a 4KiB closed summary, and reaps the whole
worker group on failure. The inner Git processes inherit that owned group and
have no shell/hooks or separate sessions. This makes the inspection deadline
interruptible without changing any immutable serializer or global signal state.
The in-process streaming Git parser never retains a full blob. Memory includes
the caller's compressed bytes and the worker's bounded compressed input, but no
complete expanded tar/source allocation.

Before final freeze, source loading is tightened to execute only the already
captured, SHA-pinned v1/v3 bytes in private module dictionaries. A fixed import
adapter supplies the captured v1 module to the v3 source's literal import;
standard-library imports remain standard. No repository package initializer or
reopening of a hash-checked source path is needed, and no `sys.modules` or
serializer globals are mutated. This avoids capture-to-import substitution.
