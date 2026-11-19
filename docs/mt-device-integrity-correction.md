# MT preview integrity correction — 1.0.1

The initial `70a38b5` component is held from integration. Independent review found
real defects: a `Buy now.` record could answer an unrelated request with the same
message ID; undeclared raw fields, invalid locations and changed inner authority
source hashes were accepted. The builder followed source/NOTICE links and read
files before checking their size. These are integrity/privacy defects, not copy
issues. The initial receipts remain historical; they do not prove these properties.

The implementation plan was sent to PM before edits: reuse the existing frozen
JavaScript normalizer for the actual request, close original/nested schemas and
source/count/span relationships, keep canonical method fields, and capture/recheck
all source inputs through descriptors before publication. This correction delivers
that bounded plan without changing canonical urgency or authority method semantics.

## Result validation

A private request context derives SHA-256 and normalized codepoint count using
the existing generated `protocol/normalization.mjs`, backed by the same Unicode15
tables as Python. The client compares both against the received envelope and the
original record. A matching message ID alone is insufficient.

Every original record field is retained. Exact envelope, method, measurement,
finding, row, parameter and source-map schemas refuse unknown fields, accessors
and malformed collections. Counts, state/density relationships, paired/unpaired
locations, quote contexts, span bounds and both source maps are checked. The
validator reads only closed data records. Valid records are deeply frozen and
branded before explanations or private detail rendering can use them. No raw
field is merely dropped and no `text_included: false` flag substitutes for checking.

The adapter envelope advances to `mt-device-phrase-explorer/1.0.1` and adds the
normalized subject character count. Original methods/IDs remain urgency 1.1.0 and
authority quotation 1.0.0. This is structural evidence integrity, not independent
recomputation, trusted execution attestation, semantic judgment or accuracy.

## Source build boundary

The builder no longer imports source modules to obtain constants. All selected
method, notice and normalizer files are captured through held no-follow,
nonblocking descriptors. Only single-link regular files up to 200,000 bytes are
read. Ancestor/root mappings, file metadata and descriptor identities are checked
again before publication. All outputs are staged, and all captured inputs are
rechecked before replacing any previous output. Input refusal cleans the staged
files and preserves previous published bytes. The active manifest is replaced
last. No multi-file crash transaction or defense against a compromised owner is
claimed.

The generated JavaScript normalizer is verified against its captured core and
Unicode data. Original LICENSE, NOTICE and Unicode attribution remain intact.
The superseded unmounted source payload is removed from the current public tree;
its original Git commit and run records remain available. No license clearance,
activation, shared catalogue, scope, state or selector change is made.

## Verification and limits

- **13 focused Node groups passed**, including wrong-input canonical replay,
  unknown raw fields, negative/out-of-range spans, inner source mutation, malformed
  counts/relations, accessor refusal and immutable rendering. All 41 existing
  frozen-normalization version witnesses bind correctly.
- **36 focused Python tests passed**, including original record preservation and
  source/parent/root symlinks, FIFO, hardlinks, oversized/nonregular sources,
  generated normalizer drift, file/parent/root replacement and a source change
  after output staging. Previous outputs remain unchanged on refusal; oversized
  descriptors are refused before reading.
- **Chromium and WebKit** each pass 30 full native-Python/validated-browser record
  controls and five malicious-result UI controls. Wrong input, unknown raw data,
  invalid spans, changed authority source and wrong count produce no result or
  private-details display. Existing lifetime, fault isolation, privacy, 320px/200%,
  44px controls and selected-rule axe checks still pass.

[Correction receipt](../runs/2026-11-19-mt-device-correction.json) ·
[Fresh browser evidence](../runs/2026-11-19-mt-device-browser-corrected.json) ·
[Preserved pre-fix counterexample](../runs/2026-11-19-mt-device-integrity-before.json).

The component still requires PM's production mounting/build/deployment checks.
Physical iPhone, human VoiceOver, independent accuracy and full MT release remain
open. On-device computation does not promise offline loading; shared public
module/source/runtime delivery remains a prerequisite. No server endpoint,
account, content upload, application storage or telemetry was added.
