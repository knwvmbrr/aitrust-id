# Frozen text normalization — implementation plan

The text identity and evidence positions must agree on every supported device.
Runtime-provided NFC is insufficient: the measured Python 15.0 and JavaScript
17.0 Unicode tables disagree on 41 generated combining-mark sequences. F-078
and F-154 are reopened until the correction passes both implementations and the
actual on-device checker. This is an engineering interoperability correction,
not independent detector-accuracy validation or a new tag adoption.

## Architecture and migration

Freeze NFC at Unicode 15.0.0, matching the existing gateway's Python 3.12 baseline.
Generate canonical decomposition, combining-class and composition tables from
that version, retaining the Unicode license. Implement the UAX #15 algorithm in
Python and JavaScript against those tables; include algorithmic Hangul and stable
canonical ordering. Never consult the host's changing Unicode tables at runtime.
All scalar values remain accepted; values unassigned in 15.0 have no decomposition
and class zero. Reject lone surrogates and oversized inputs. Sorting each mark
segment avoids quadratic work on adversarial combining-mark strings.

Keep the original subject-v1 vectors as history. Current text primitives become
subject-v2 with a declared normalization identity; code-byte primitives remain
subject-v1. The website's Python worker embeds the same trusted tables and the
frontend uses the matching JavaScript normalizer before rendering positions.
Device records and the manifest carry the normalization identity. The gateway
uses the shared Python module before and after redaction; its image context is
restricted to required gateway and protocol files. Corpus lookup uses it too.
No uploaded input, new network dependency, endpoint, tag or pricing change.

## Risks and acceptance

A custom normalizer can introduce decomposition, ordering or blocking errors.
Run the complete official Unicode 15.0 NormalizationTest NFC invariants in both
languages, the 41 observed counterexamples, invalid scalars, boundaries, Hangul,
composition exclusions and long combining sequences. Compare actual builder
outputs across supported Python versions, execute the on-device checker in real
browser engines, rerun all 86 development examples, and rebuild/recheck the real
Linux gateway. Runtime/version or bundle mismatches fail closed. Retain the
original gap evidence and mark it corrected only after these checks pass.

New table generations require an explicit version migration and evidence;
normalization identity changes cannot silently reinterpret old hashes. Hashes
identify artifacts and may reveal linkage; they do not certify truth or provide
anonymity. Independent release validation and actual-phone checks remain open.
