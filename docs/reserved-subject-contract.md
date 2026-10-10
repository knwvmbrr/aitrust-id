# Reserved decoded-artifact subjects v1

These implementer primitives are complete hashing and coordinate contracts for
prepared artifacts. They are **not file decoders or working tag detectors**, do
not adopt RFC-0003, and do not change the adopted assertion envelope or text-only
gateway. PDF, JPEG, MP3 and other encoded files supplied directly are refused.
A future decoder must publish its exact profile, version, transformations and
vectors before claiming support. Hashes link artifacts; they do not anonymise them.

## Binary encoding shared by all four contracts

Begin with ASCII `reserved-subject-v1`, NUL, the record kind, NUL. Append each
listed field as its unsigned 32-bit big-endian byte length followed by its bytes.
Integers use minimal unsigned ASCII decimal; numeric integral JSON values such as
`1.0` canonicalize to `1`. Text uses strict UTF-8. Hash values used as nested fields
are their 32 binary bytes, not their hexadecimal text. SHA-256 hashes the complete
record. All object keys are specified below; extra or missing fields are errors.
Canonical base64 uses the standard alphabet and required padding; noncanonical
trailing bits, whitespace, URL alphabets and invalid encodings are refused.
No implicit URL fetch, decoding, conversion, disk resolution or execution.

## Image

Input fields: `modality: image`, integer `width`, `height`,
`representation: RGBA8-sRGB-straight-oriented`, `pixels_base64`.
Pixels are tightly packed row-major R, G, B, A unsigned bytes, encoded sRGB color,
straight/unassociated alpha, with orientation already applied. Transparent pixels'
RGB bytes remain significant. No EXIF/ICC/metadata field is admitted. Two images
are equivalent only when these canonical pixels and dimensions match; callers
must use a separately declared decoder/color-conversion profile for encoded files.

Hash kind `image`; fields: width, height, representation, decoded pixel bytes.
At most 262,144 pixels and 1,048,576 bytes; dimensions each positive and bounded.
Output includes dimensions and `offset_unit: pixel_xy_half_open`.
An evidence box is `[x0,y0,x1,y1]`, bounded by dimensions, with x0<x1 and y0<y1.

## Audio

Input fields: `modality: audio`, `sample_rate`, `channels`,
`representation: PCM16LE-interleaved`, `samples_base64`.
Rate is an integer 8,000–192,000 Hz; 1–8 channels. Signed 16-bit little-endian
samples are interleaved in channel order, frame by frame. No implicit resampling,
normalisation, dithering, downmix or loudness transformation. Every channel sample
counts. The nonempty buffer is at most 1,048,576 bytes and ends on a complete frame.

Hash kind `audio`; fields: sample rate, channels, representation, decoded bytes.
Output gives frame count and exact rational `time_base: 1/sample_rate` seconds.
Evidence uses `[start_frame,end_frame)` within frame count. Convert to display
milliseconds using that rational rate; never round and reinterpret offsets.

## Video

Input fields: `modality: video`, `representation: decoded-frames-us-v1`,
`frames`: 1–64 objects with exactly `timestamp_us`, `duration_us`, `image`.
Each image follows the image contract. Timestamp is a nonnegative integer and
duration positive; both and their sum must be at most 2^53−1. Frames are supplied
in order, never overlap, may have gaps, and may have distinct dimensions.
At most 4,194,304 decoded pixel bytes across all frames. No implicit frame-rate
conversion, interpolation or re-encoding equivalence. No audio track is included;
a mixed-media implementation must bind a separate audio subject explicitly.

Each `video-leaf` hashes: zero-based index, timestamp, duration, binary image hash.
Each `video-pair` hashes: binary left hash, binary right hash. Pair adjacent nodes
in their supplied order, promoting the last odd node unchanged at each level.
Final `video` hashes: frame count, representation, binary tree root. Output
publishes the full frame subjects/times and tree rule. Evidence is
`{frame: index, box: [x0,y0,x1,y1]}` in that frame's pixel coordinates. Time uses
integer microseconds. A change to pixels, timing, order or dimensions changes the
subject. Re-encoding is not promised to preserve it.

## Document

Input fields: `modality: document`,
`extraction_profile: supplied-page-text-v1`, `pages`: 1–100 objects with `text`
and `assets`. This profile means explicitly supplied page text, **not a PDF/DOCX
extractor**. It cannot attest completeness, hidden/scanned content or OCR accuracy.
Future file parsers require distinct adopted profiles and their own vectors;
unversioned extraction profiles and paths to files are refused.

At most 200,000 input Unicode code points across pages. Each page text is normalized
with frozen `NFC-Unicode-15.0.0/v1`, strict scalars only, preserving newlines.
At most 64 assets across pages, 1,048,576 decoded bytes total. Each asset has
exactly `media_type` (1–64 ASCII characters, nonempty type/subtype tokens using
letters/digits/dot/plus/hyphen) and `data_base64`. The descriptive media type does
not validate the bytes as that file format. Bytes are hashed exactly, never opened.
Page order, asset order and asset type are significant.

`document-asset` hashes: zero-based asset index within page, media type, raw bytes.
`document-page` hashes: zero-based page index, normalization ID, normalized UTF-8
page text, asset count, each binary asset hash in order.
`document` hashes: extraction profile, normalization ID, page count, each binary
page hash in order. Output includes page code-point lengths and asset identities.
Evidence uses `{page: index, range: [start,end]}`; half-open code-point offsets
within that normalized page, never raw file bytes or UTF-16 indices.

## Use and verification

Run `python3 scripts/hash-reserved-artifact.py < prepared-artifact.json`.
It accepts at most 8 MiB of JSON from stdin, rejects duplicate fields and nonfinite
values, outputs only the derived subject, and never stores or echoes input/errors.
`protocol/reserved_subjects.py` and `protocol/reserved-subjects.cjs` provide the
same subject and `validate_span` / `validateSpan` APIs. Coordinate validation
recomputes the subject from the artifact rather than trusting a claimed size.

Run `python3 scripts/verify-reserved-subjects.py` with Node available for the fixed
vectors, actual CLI and cross-language negative controls. The Python test suite
adds resource ceilings, odd/even Merkle trees, transforms and complete span tests.
This is local conformance between two implementations, not outside-implementer
or independent detector validation. The gateway still refuses all four modalities.
