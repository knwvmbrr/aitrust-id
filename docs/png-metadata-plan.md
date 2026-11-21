# Offline PNG metadata/preflight plan

Base: abe7d64. Existing C2PA inspection reads attached credentials, while reserved
image subjects accept already-decoded pixels. Neither exposes ordinary PNG text
sections without the optional native SDK. This reader provides dimensions and
fixed stored-metadata categories for an explicitly selected local PNG, and
separates unsupported variants, damaged structure/data and resource refusal.

Only still, noninterlaced 8-bit grayscale/RGB/gray-alpha/RGBA PNG is supported.
PNG signature, critical order, chunk CRCs, bounded zlib scanline length/filter
bytes and supported text chunk syntax are checked. This is not a renderer,
color converter, universal PNG validator, watermark verifier or AI-origin
classifier. EXIF/ICC/C2PA-shaped sections are counted, not interpreted or trusted.
Unknown critical chunks, palette/16-bit/interlaced/animated variants are
Unsupported, not malicious or AI-generated. Their absence proves no authorship.

Limits: 10 MiB encoded, 4 million pixels, 32 MiB expanded image scanlines, 4096 chunks,
256KiB stored/expanded metadata, 64 KiB per text value,128 text sections. The CLI
uses one isolated fixed worker with a 4 second wall/2second CPU limits, bounded
stdout and Linux 256 MiB address space; byte/iteration limits apply on every
platform. No new dependency, SDK, model, URL fetch, shell or uploaded image.

Default readable output has no filename, hash, raw text, GPS or URL. Explicit
JSON exposes the exact captured-file SHA256, byte length and fixed categories;
hashes can link private files. Metadata contents remain untrusted and omitted.
No automatic export/storage is added. The input is opened once with no-follow,
regular-file/size/identity checks; the same descriptor feeds the worker. Worker
records use a closed schema and exact captured subject binding. Failure cannot
turn into zero findings or an origin verdict.

Owned files: tools/png_metadata.py, scripts/inspect-png-metadata.py,
tests/test_png_metadata.py, this plan and its guide/result/evidence. Existing
C2PA/default JSON, text tags, website/API, deployment, scopes and taxonomy remain
unchanged. F-155/vendor verification and full FA/PA acceptance remain open.

Verification: synthetic PNGs only; actual CLI without c2pa installed; valid
plain/compressed/international text, chunk/data corruption, supported filters,
unsupported variants, decompression/output/time/file/refusal/privacy controls
and recovery. No unchanged broad suite or private photographs.

Normative primary source: W3C PNG3 Recommendation, 24 June 2025,
https://www.w3.org/TR/2025/REC-png-3-20250624/ (sections 5, 10, 11.2, 11.3.3).
