# Reserved subject contracts: architecture before implementation

Add separate, versioned Python and Node primitives for four reserved modalities.
Keep the adopted 0.1 assertion schema and text-only evaluator unchanged. These
are implementer subject contracts, not image/audio/video/document detectors,
file decoders, RFC adoption or an accuracy claim. The command accepts explicitly
prepared, canonical decoded artifacts, refuses encoded files and unknown fields,
and returns a hash plus exact coordinate units without storing input.

Use domain-separated SHA-256 over length-delimited, typed binary records:
image RGBA8/sRGB/straight alpha with orientation already applied; audio interleaved
signed PCM16 little endian at the declared rate with no implicit resampling;
video ordered frame subjects with integer microsecond timing and an explicit
Merkle-tree rule; document supplied normalized page text plus exact asset bytes.
For documents, the supplied extraction profile and page/asset order are hashed.
A later PDF/DOCX/OCR decoder needs its own versioned extraction profile and
conformance vectors; this contract makes no equivalence claim across decoders.

Validate exact keys, integers (never booleans or fractional values), scalar text,
canonical base64, dimensions, sample alignment, page ordering, timestamps and
resource bounds before allocating additional buffers. No external fetch, disk
input resolution, URL, decompression or executable content handling. Never
silently reinterpret coordinates or convert sample/pixel representations.

Risks: two decoders can produce different pixels/text; metadata stripping can
change orientation; sample conversion can alter audio; video re-encoding can
alter every leaf; supplied extraction can omit document content. Return the
contract identity and units, publish these limitations, refuse implicit
conversions. A fingerprint remains a correlation identifier, not anonymisation,
authorship or a truth verdict. Preserve future parser/detector jobs and human
acceptance under their own packages.

Acceptance: fixed expected vectors in both independent language implementations;
actual CLI stdin/stdout; metadata/field rejection; dimensions/alignment/timing,
wrong-type/base64/surrogate and size failures; transform sensitivity and explicit
preservation rules; odd/even video Merkle cases; independent document page/asset
ordering; text normalization identity; gateway still refuses all reserved inputs.

## Executed acceptance

Sixteen fixed subjects, 37 compact invalid artifacts, four valid coordinate and
eleven invalid coordinate cases execute in both Python and Node. Four actual CLI
checks use prepared artifacts. The 80-test suite additionally exercises resource
ceilings, transformations, duplicate JSON fields, malformed files and unsafe
spans. F-006 and F-060 through F-063 are the full reserved subject-definition jobs:
explicit contracts before support is claimed, not implemented media detectors.
The ledger preserves separate modality support, parser, release/RFC adoption and
outside-implementer work; no detector, decoder or adopted wire change is asserted.
